from ultralytics import YOLO
import cv2
import base64
import requests
import time
import socket
import json
import numpy as np

# ===============================
# YOLO 및 서버 기본 설정
# ===============================
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
TCP_SERVER_URL = "http://192.168.0.48:5000/upload"
RECYCLE_CENTER_ID = 1

# ===============================
# PyQt 클라이언트 통신 설정 (UDP)
# ===============================
PYQT_IP = "192.168.0.100"
PYQT_PORT = 6000
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===============================
# 모델 로드
# ===============================
model = YOLO(MODEL_PATH)

# ===============================
# 클래스 이름 매핑 (YOLOv8은 자동 추출 불가 시 수동 입력 필요)
# ===============================
CLASS_NAMES = {
    0: "종이", 1: "종이팩", 2: "종이컵", 3: "캔류", 4: "유리병",
    5: "페트", 6: "플라스틱", 7: "비닐", 8: "유리+다중포장재",
    9: "페트+다중포장재", 10: "스티로폼", 11: "건전지"
}

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
# PyQt로부터 영상 수신 (UDP 스트리밍)
# ===============================
cap = cv2.VideoCapture("udp://0.0.0.0:1234", cv2.CAP_FFMPEG)

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
MAX_TRACK_DURATION = 3

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ 프레임 수신 실패")
        continue

    current_time = time.time()
    send_flag = False

    if not tracking or current_time - tracking_start_time > MAX_TRACK_DURATION:
        results = model.predict(frame, imgsz=640, conf=0.25, verbose=False)[0]

        best_class_id = None
        max_conf = 0.0
        best_box = None

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            if conf > max_conf:
                max_conf = conf
                best_class_id = cls
                best_box = [x1, y1, x2, y2]

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
                send_flag = True
            else:
                print("🔁 동일 객체로 판단됨 → 전송 생략")
                tracking = False
    else:
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
    cv2.imshow("DeepCycle AI - YOLOv8 + Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

