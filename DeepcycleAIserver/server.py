import sys
sys.path.append("/home/lim/dev_ws/deepcycle/yolov5")

import cv2
import torch
import base64
import requests
import time
import socket
import json
from models.common import DetectMultiBackend
from utils.general import non_max_suppression
import numpy as np

# ===============================
# YOLO 및 서버 기본 설정
# ===============================
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"  # 학습된 YOLO 모델 경로
TCP_SERVER_URL = "http://192.168.0.48:5000/upload"     # Flask 서버 URL
RECYCLE_CENTER_ID = 1  # 재활용 센터 ID 값 전송용

# ===============================
# PyQt 클라이언트 통신 설정 (UDP)
# ===============================
PYQT_IP = "192.168.0.100"  # PyQt 클라이언트 IP
PYQT_PORT = 6000  # PyQt가 수신할 포트
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP 소켓 생성

# ===============================
# 모델 로드 및 설정
# ===============================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DetectMultiBackend(MODEL_PATH, device=device)
model.eval()

# ===============================
# 클래스 이름 매핑
# ===============================
CLASS_NAMES = {
    0: "종이", 1: "종이팩", 2: "종이컵", 3: "캔류", 4: "유리병",
    5: "페트", 6: "플라스틱", 7: "비닐", 8: "유리+다중포장재",
    9: "페트+다중포장재", 10: "스티로폼", 11: "건전지"
}

# ===============================
# PyQt로부터 영상 수신 (UDP 스트리밍)
# ===============================
cap = cv2.VideoCapture("udp://0.0.0.0:1234", cv2.CAP_FFMPEG)

# ===============================
# Flask 서버로 전송 함수 정의
# ===============================
def send_results(image_b64, class_name):
    data = {
        "recycle_center_id": RECYCLE_CENTER_ID,
        "image": image_b64,
        "extension": "jpg",
        "class_name": class_name
    }
    try:
        response = requests.post(TCP_SERVER_URL, json=data)
        print(f"🟢 Flask 서버 응답: {response.json()}")
    except Exception as e:
        print(f"❌ Flask 서버 전송 실패: {e}")

# ===============================
# IOU 계산 함수 (객체 동일성 판단용)
# ===============================
def iou(box1, box2):
    xi1 = max(box1[0], box2[0])
    yi1 = max(box1[1], box2[1])
    xi2 = min(box1[2], box2[2])
    yi2 = min(box1[3], box2[3])
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    return inter_area / union_area if union_area else 0

# ===============================
# 메인 루프 (객체 감지/추적 및 통신)
# ===============================
last_sent_time = 0
tracker = None
tracking = False
tracker_box = None
prev_class_id = None
prev_box = None
tracking_start_time = 0
MAX_TRACK_DURATION = 3  # 트래커 유지 시간 (초)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ 프레임 수신 실패")
        continue

    current_time = time.time()
    send_flag = False

    if not tracking or current_time - tracking_start_time > MAX_TRACK_DURATION:
        # ===============================
        # YOLO 객체 탐지 수행
        # ===============================
        resized = cv2.resize(frame, (640, 640))
        img_tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0).to(device) / 255.0

        with torch.no_grad():
            pred = model(img_tensor)
            detections = non_max_suppression(pred)

        best_class_id = None
        max_conf = 0.0
        best_box = None

        for det in detections[0]:
            x1, y1, x2, y2, conf, cls = det.cpu().numpy()
            if conf > max_conf:
                max_conf = conf
                best_class_id = int(cls)
                best_box = [int(x1), int(y1), int(x2), int(y2)]

        # ===============================
        # 객체 변경 감지 및 트래킹 초기화 조건
        # ===============================
        if best_box is not None:
            if prev_box is None or iou(prev_box, best_box) < 0.5 or best_class_id != prev_class_id:
                from opencv_tracker_factory import create_tracker
                tracker = create_tracker("KCF")
                bbox = (best_box[0], best_box[1], best_box[2]-best_box[0], best_box[3]-best_box[1])
                tracker.init(frame, bbox)
                tracking = True
                tracker_box = best_box
                prev_class_id = best_class_id
                prev_box = best_box
                tracking_start_time = current_time
                send_flag = True  # 새로운 객체 감지 → Flask 전송 허용
            else:
                print("🔁 동일 객체로 판단됨 → 전송 생략")
                tracking = False
    else:
        # ===============================
        # 트래커로 객체 위치 추적
        # ===============================
        success, box = tracker.update(frame)
        if success:
            x, y, w, h = map(int, box)
            tracker_box = [x, y, x + w, y + h]
            if current_time - last_sent_time >= 1:
                send_flag = True
        else:
            print("🔁 추적 실패 → 재탐지 예정")
            tracking = False
            continue

    # ===============================
    # PyQt 클라이언트로 실시간 정보 전송 (항상)
    # ===============================
    if tracker_box is not None:
        result_packet_live = {
            "class_name": CLASS_NAMES.get(prev_class_id, "Unknown"),
            "confidence": float(round(max_conf, 2)),
            "box": list(map(int, tracker_box)) 
        }
        try:
            pyqt_sock.sendto(json.dumps(result_packet_live).encode(), (PYQT_IP, PYQT_PORT))
        except Exception as e:
            print(f"⚠️ PyQt 실시간 전송 실패: {e}")

    # ===============================
    # Flask 서버로 전송 (조건 만족 시 1회 또는 주기 전송)
    # ===============================
    if send_flag and tracker_box is not None:
        best_class_name = CLASS_NAMES.get(prev_class_id, "Unknown")
        ret, buffer = cv2.imencode(".jpg", frame)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        send_results(image_b64, best_class_name)
        print(f"📡 Flask로 감지 결과 전송: {best_class_name}")
        last_sent_time = current_time

    # ===============================
    # GUI
    # ===============================
    cv2.imshow("DeepCycle AI - YOLO + Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

