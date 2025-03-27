import socket
import cv2
import numpy as np
import threading
import queue
import time
import json
import requests
from flask import request
from yolo_detector import YoloDetector, CLASS_NAMES
from utils import encode_image_to_base64, iou

# 디버깅
SEND_TRAINING_DATA = True

# YOLO 모델 로드
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
detector = YoloDetector(MODEL_PATH)

# Flask + PyQt 설정
TCP_SERVER_URL = "http://192.168.0.48:5000/upload"
RECYCLE_CENTER_ID = 1
PYQT_IP = "192.168.0.100"
PYQT_PORT = 6000
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Queue 생성
frame_queue = queue.Queue(maxsize=3)
result_queue = queue.Queue(maxsize=3)

CONF_THRESHOLD = 0.5
DURATION = 5  # seconds for batching detections

YOLO_CLASS_TO_SERVER_ID = {
    "종이": 1, "종이팩": 1, "종이컵": 1,
    "캔류": 2,
    "유리병": 3,
    "페트": 4, "플라스틱": 4,
    "비닐": 5,
    "유리+다중포장재": 6,
    "페트+다중포장재": 6,
    "스티로폼": 6,
    "건전지": 7
}

# ========== Thread 1: 프레임 수신 ==========
class FrameReceiverThread(threading.Thread):
    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 1234))
        print("[🔵] FrameReceiver 시작됨")
        while True:
            try:
                data, _ = sock.recvfrom(65536)
                frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    frame_queue.put(frame)
            except Exception as e:
                print(f"[❌] FrameReceiver 오류: {e}")

# ========== Thread 2: YOLO 감지 + Tracker ==========
class InferenceThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.buffer = []
        self.start_time = time.time()

    def run(self):
        print("[🟡] InferenceThread 시작됨")
        while True:
            frame = frame_queue.get()
            boxes, class_ids, confs = detector.detect_all(frame)  # <- detect_all() needs to return multiple detections

            for box, class_id, conf in zip(boxes, class_ids, confs):
                if conf >= CONF_THRESHOLD:
                    self.buffer.append((class_id, conf, box, frame))

            if time.time() - self.start_time >= DURATION:
                self.aggregate_and_send()
                self.buffer.clear()
                self.start_time = time.time()
                
    def aggregate_and_send(self):
        if not self.buffer:
            return
        # Step 1: conf >= 0.5 필터링
        filtered = [(cls_id, conf, box, frame) for cls_id, conf, box, frame in self.buffer if conf >= 0.5]
        if not filtered:
            return  # 아무것도 없으면 전송 안 함
        
        # Step 2: 클래스별로 그룹화
        stat = {}
        for class_id, conf, box, frame in filtered:
            stat.setdefault(class_id, []).append((conf, box, frame))
        
        # Step 3: 가장 많이 나온 클래스 중 선택
        # # → 빈도수가 같은 경우, 평균 conf 기준으로 선택
        best_class_id = max(
            stat.items(),
            key=lambda x: (len(x[1]), np.mean([conf for conf, _, _ in x[1]]))
        )[0]
        
        # Step 4: 그 클래스 중 conf가 가장 높은 항목 선택
        best_conf, best_box, best_frame = max(stat[best_class_id], key=lambda x: x[0])
        
        # Step 5: 전송
        result = {
            "frame": best_frame,
            "class_id": best_class_id,
            "box": best_box,
            "conf": best_conf
        }
        
        result_queue.put(result)

# ========== Thread 3: 결과 전송 (Flask + PyQt) ==========
def draw_box_on_frame(frame, box, label=None):
    img = frame.copy()
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    if label:
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return img

class ResultSenderThread(threading.Thread):
    def run(self):
        print("[🟢] ResultSenderThread 시작됨")
        while True:
            result = result_queue.get()
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
                print("[⚠️] PyQt 전송 실패")

            frame_to_send = draw_box_on_frame(frame, box, f"{class_name} ({conf:.2f})") if SEND_TRAINING_DATA else frame
            image_b64 = encode_image_to_base64(frame_to_send)
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
                    print(f"[📡] Flask 전송됨 → {class_name}")
                    if response.status_code == 200:
                        print(f"🟢 Flask 응답: {response.json()}")
                    else:
                        print(f"⚠️ Flask 응답 오류: {response.status_code} - {response.text}")
                except:
                    print("[❌] Flask 전송 실패")

# ========== 스레드 실행 ==========
FrameReceiverThread().start()
InferenceThread().start()
ResultSenderThread().start()

# 메인 스레드 : 대기 

while True:
    time.sleep(1)
