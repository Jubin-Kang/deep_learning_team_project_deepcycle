import socket
import cv2
import numpy as np
import threading
import queue
import time
import json
import requests
import signal
import sys

from yolo_detector import YoloDetector, CLASS_NAMES
from utils import encode_image_to_base64, iou
from opencv_tracker_factory import create_tracker


# 재학습용 데이터 전송 스위치 
SEND_TRAINING_DATA = True

# YOLO 모델 
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
detector = YoloDetector(MODEL_PATH)
CONF_THRESHOLD = 0.5

# 서버 
TCP_SERVER_URL = "http://192.168.0.56:5000/upload"
RECYCLE_CENTER_ID = 1
PYQT_IP = "192.168.0.31"
PYQT_PORT = 6000
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# queue 사이즈
frame_queue = queue.Queue(maxsize=8)
result_queue = queue.Queue(maxsize=5)

# 재매핑 
YOLO_CLASS_TO_SERVER_ID = {
    "Paper": 1, "Paper Pack": 1, "Paper Cup": 1,
    "Can": 2,
    "Glass Bottle": 3,
    "PET Bottle": 4, "Plastic": 4,
    "Vinyl": 5,
    "Glass & Multi-layer Packaging": 6,
    "PET & Multi-layer Packaging": 6,
    "Styrofoam": 6,
    "Battery": 7
}



# 종료 
shutdown_event = threading.Event()

# ========== Thread 1: 프레임 수신 ==========
class FrameReceiverThread(threading.Thread):
    def __init__(self):
        super().__init__(name="FrameReceiver")

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 1234))
        print("[🔵] FrameReceiver 시작됨")
        while not shutdown_event.is_set():
            try:
                data, _ = sock.recvfrom(65536)
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    try:
                        frame_queue.put(frame, timeout=1)
                    except queue.Full:
                        # print("[⚠️] 프레임 버퍼 가득 참 - 드롭됨")
                        pass
            except Exception as e:
                print(f"[❌] FrameReceiver 오류: {e}")


# ========== Thread 2: YOLO 감지 + Tracker ==========
class InferenceThread(threading.Thread):
    def __init__(self):
        super().__init__(name="InferenceThread")
        self.trackers = {}
        self.buffer = []

        self.next_tracker_id = 0
        self.iou_threshold = 0.5
        
        # YOLO 재검증 주기 / Tracker 유지 시간 
        self.timeout = 10
        self.duration = 10
        
        self.start_time = time.time()


    def aggregate_and_send(self):
        if not self.buffer:
            return
        
        # Step 1: conf >= 0.5 필터링
        filtered = [(cls_id, conf, box, frame) for cls_id, conf, box, frame in self.buffer if conf >= 0.5]
        if not filtered:
            return
        # Step 2: 클래스별로 그룹화
        stat = {}
        for class_id, conf, box, frame in filtered:
            stat.setdefault(class_id, []).append((conf, box, frame))
        # Step 3: 가장 많이 나온 클래스 중 선택
        #  → 빈도수가 같은 경우, 평균 conf 기준으로 선택
        best_class_id = max(
            stat.items(),
            key=lambda x: (len(x[1]), np.mean([conf for conf, _, _ in x[1]]))
        )[0]
        
        # Step 4: 그 클래스 중 conf가 가장 높은 항목 선택
        best_conf, best_box, best_frame = max(stat[best_class_id], key=lambda x: x[0])
        frame_to_send = draw_box_on_frame(
            best_frame, best_box, f"{CLASS_NAMES.get(best_class_id, 'Unknown')} ({best_conf:.2f})"
        ) if SEND_TRAINING_DATA else best_frame

        # Step 5: 전송
        result = {
            "frame": frame_to_send,
            "class_id": best_class_id,
            "box": best_box,
            "conf": best_conf
        }

        try:
            result_queue.put(result, timeout=1)
        except queue.Full:
            print("[⚠️] result_queue 가득 참 - 결과 드롭")

    def run(self):
        print("[🟡] InferenceThread 시작됨")
        while not shutdown_event.is_set():
            try:
                frame = frame_queue.get(timeout=1)
            except queue.Empty:
                continue

            current_time = time.time()
            boxes, class_ids, confs = detector.detect_all(frame)

            for box, class_id, conf in zip(boxes, class_ids, confs):
                if conf < CONF_THRESHOLD:
                    continue

                matched = False
                for tracker_id, (tracker, t_class_id, last_seen) in list(self.trackers.items()):
                    success, tracked_box = tracker.update(frame)
                    if not success or t_class_id != class_id:
                        continue
                    if iou(box, tracked_box) >= self.iou_threshold:
                        self.trackers[tracker_id] = (tracker, class_id, current_time)
                        matched = True
                        break

                if not matched:
                    tracker = create_tracker()
                    tracker.init(frame, tuple(box))
                    self.trackers[self.next_tracker_id] = (tracker, class_id, current_time)
                    self.next_tracker_id += 1
                    self.buffer.append((class_id, conf, box, frame))
                    # print(f"[🟢] 새 객체 감지")

            for tracker_id in list(self.trackers.keys()):
                _, _, last_seen = self.trackers[tracker_id]
                if current_time - last_seen > self.timeout:
                    del self.trackers[tracker_id]

            if time.time() - self.start_time >= self.duration:
                self.aggregate_and_send()
                self.buffer.clear()
                self.start_time = time.time()

# ========== Thread 3: 결과 전송 (Flask + PyQt) ==========
class ResultSenderThread(threading.Thread):
    def __init__(self):
        super().__init__(name="ResultSender")

    def run(self):
        print("[🟢] ResultSenderThread 시작됨")
        while not shutdown_event.is_set():
            try:
                result = result_queue.get(timeout=1)
            except queue.Empty:
                continue

            frame = result["frame"]
            class_id = result["class_id"]
            box = result["box"]
            conf = result["conf"]
            class_name = CLASS_NAMES.get(class_id, "Unknown")

            try:
                packet = {
                    "class_name": class_name,
                    "confidence": float(round(conf, 2)),
                    "box": list(map(int, box)),
                    "timestamp": time.time()
                }
                pyqt_sock.sendto(json.dumps(packet).encode(), (PYQT_IP, PYQT_PORT))
                print(f"[📡] PyQt 전송 → {class_name}")
            except Exception as e:
                print(f"[⚠️] PyQt 전송 실패: {e}")

            frame_to_send = draw_box_on_frame(frame, box, f"{class_name} ({conf:.2f})") if SEND_TRAINING_DATA else frame
            image_b64 = encode_image_to_base64(frame)
            server_class_id = YOLO_CLASS_TO_SERVER_ID.get(class_name, -1)

            if image_b64 and server_class_id != -1:
                data = {
                    "deepcycle_center_id": RECYCLE_CENTER_ID,
                    "image": image_b64,
                    "extension": "jpg",
                    "confidence": conf,
                    "class": server_class_id,
                    "box": list(map(int, box))
                }
                try:
                    response = requests.post(TCP_SERVER_URL, json=data)
                    if response.status_code == 200:
                        print(f"Flask 응답: {response.json()}")
                    else:
                        print(f"⚠️ Flask 오류: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"[❌] Flask 전송 실패: {e}")


def draw_box_on_frame(frame, box, label=None):
    img = frame.copy()
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    if label:
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return img


def signal_handler(sig, frame):
    print("\n🛑프로그램 종료합니다.")
    shutdown_event.set()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ========== 스레드 실행 ==========
if __name__ == "__main__":
    FrameReceiverThread().start()
    InferenceThread().start()
    ResultSenderThread().start()

    while not shutdown_event.is_set():
        time.sleep(1)
