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
import psutil

from yolo_detector import YoloDetector, CLASS_NAMES
from utils import encode_image_to_base64, iou
from opencv_tracker_factory import create_tracker

SEND_TRAINING_DATA = True
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
detector = YoloDetector(MODEL_PATH)
CONF_THRESHOLD = 0.5

TCP_SERVER_URL = "http://192.168.0.56:5000/upload"
RECYCLE_CENTER_ID = 1
PYQT_IP = "192.168.0.42"
PYQT_PORT = 6000
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

frame_queue = queue.Queue(maxsize=8)
result_queue = queue.Queue(maxsize=5)

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

shutdown_event = threading.Event()

stats = {
    "start_time": time.time(),
    "dropped_frames": 0,
    "result_count": 0
}

class FrameReceiverThread(threading.Thread):
    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 1234))
        print("[🔵] FrameReceiver 시작")
        while not shutdown_event.is_set():
            try:
                data, _ = sock.recvfrom(65536)
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    try:
                        frame_queue.put(frame, timeout=1)
                    except queue.Full:
                        stats["dropped_frames"] += 1
            except Exception:
                continue

class InferenceThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.trackers = {}
        self.next_tracker_id = 0
        self.iou_threshold = 0.5
        self.timeout = 10
        self.buffer = []
        self.start_time = time.time()
        self.duration = 10

    def aggregate_and_send(self):
        if not self.buffer:
            return
        filtered = [(cls_id, conf, box, frame) for cls_id, conf, box, frame in self.buffer if conf >= 0.5]
        if not filtered:
            return
        stat = {}
        for class_id, conf, box, frame in filtered:
            stat.setdefault(class_id, []).append((conf, box, frame))
        best_class_id = max(
            stat.items(),
            key=lambda x: (len(x[1]), np.mean([conf for conf, _, _ in x[1]]))
        )[0]
        best_conf, best_box, best_frame = max(stat[best_class_id], key=lambda x: x[0])

        # 바운딩 박스 여부 결정
        frame_to_send = draw_box_on_frame(best_frame, best_box, f"{CLASS_NAMES.get(best_class_id, 'Unknown')} ({best_conf:.2f})") if SEND_TRAINING_DATA else best_frame

        result = {
            "frame": frame_to_send,
            "class_id": best_class_id,
            "box": best_box,
            "conf": best_conf
        }
        try:
            result_queue.put(result, timeout=1)
            stats["result_count"] += 1
        except queue.Full:
            pass

    def run(self):
        print("[🟡] InferenceThread 시작")
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
            for tracker_id in list(self.trackers.keys()):
                _, _, last_seen = self.trackers[tracker_id]
                if current_time - last_seen > self.timeout:
                    del self.trackers[tracker_id]
            if time.time() - self.start_time >= self.duration:
                self.aggregate_and_send()
                self.buffer.clear()
                self.start_time = time.time()

class ResultSenderThread(threading.Thread):
    def run(self):
        print("[🟢] ResultSenderThread 시작")
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
            except:
                pass
            # Flask 서버 전송
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
                    requests.post(TCP_SERVER_URL, json=data, timeout=2)
                except:
                    pass

def draw_box_on_frame(frame, box, label=None):
    img = frame.copy()
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    if label:
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return img

def signal_handler(sig, frame):
    print("\n🛑 프로그램 종료합니다.")
    shutdown_event.set()
    duration = time.time() - stats["start_time"]
    print(f"\n📄 테스트 리포트")
    print(f"- 실행 시간: {duration:.1f}초")
    print(f"- Dropped Frames: {stats['dropped_frames']}")
    print(f"- 전송된 Result 개수: {stats['result_count']}")
    print(f"- CPU 사용률: {psutil.cpu_percent()}%")
    print(f"- 메모리 사용률: {psutil.virtual_memory().percent}%")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    FrameReceiverThread().start()
    InferenceThread().start()
    ResultSenderThread().start()
    while not shutdown_event.is_set():
        time.sleep(1)
