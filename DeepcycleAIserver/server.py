import cv2
import base64
import requests
import time
import socket
import json
import numpy as np

from yolo_detector import YoloDetector, CLASS_NAMES
from utils import iou, encode_image_to_base64
from opencv_tracker_factory import create_tracker

# ===============================
# 재매핑
# ===============================

YOLO_CLASS_TO_SERVER_ID = {
    "종이": 0, "종이팩": 0, "종이컵": 0,
    "캔류": 1,
    "유리병": 2,
    "페트": 3, "플라스틱": 3,
    "비닐": 4, "건전지": 4,
    "유리+다중포장재": 5,
    "페트+다중포장재": 5,
    "스티로폼": 5
}

# ===============================
# 기본 설정
# ===============================
VERBOSE = False # 디버깅 메세지 제어 

MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
TCP_SERVER_URL = "http://192.168.0.48:5000/upload"
RECYCLE_CENTER_ID = 1

PYQT_IP = "192.168.0.100"
PYQT_PORT = 6000
pyqt_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# YOLO 객체 생성
detector = YoloDetector(MODEL_PATH)

CONF_THRESHOLD = 0.5  # 최소 신뢰도 설정

last_class_sent_time = {} # 클래스별 마지막 전송 시각
skip_count = {} # 클래스별 건너뛴 횟수 지정
MIN_SEND_INTERVAL = 2  # 동일 클래스 최소 전송 간격 (초)

# ===============================
# Flask 서버로 전송 함수
# ===============================
def send_results(image_b64, class_name, confidence, box):    
    mapped_id = YOLO_CLASS_TO_SERVER_ID.get(class_name, -1)
    
    if mapped_id == -1:
        print(f"⚠️ 서버로 전송 불가능한 클래스: {class_name}")
        return

    data = {
        "deepcycle_center_id": RECYCLE_CENTER_ID,
        "image": image_b64,
        "extension": "jpg",
        "confidence": confidence,
        "class": mapped_id,
        "box": list(map(int, box))
    }
    try:
        response = requests.post(TCP_SERVER_URL, json=data)
        if response.status_code == 200:
            print(f"🟢 Flask 응답: {response.json()}")
        else:
            print(f"⚠️ Flask 응답 오류: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Flask 서버 전송 실패: {e}")

# ===============================
# 영상 수신 (PyQt UDP 스트리밍)
# ===============================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 1234))
print("📡 UDP 수신 대기 중...")

# ===============================
# 메인 루프
# ===============================
tracker = None
tracking = False
tracker_box = None
prev_class_id = None
prev_box = None
tracking_start_time = 0
last_sent_time = 0
MAX_TRACK_DURATION = 3

while True:
    try:
        data, _ = sock.recvfrom(65536)
        np_data = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
        if frame is None:
            print("❌ 디코딩 실패")
            continue
    except Exception as e:
        print(f"❌ 수신 오류: {e}")
        continue

    current_time = time.time()
    send_flag = False

    # === 객체 감지 ===
    if not tracking or current_time - tracking_start_time > MAX_TRACK_DURATION:
        best_box, best_class_id, max_conf = detector.detect(frame)
        class_name = CLASS_NAMES.get(best_class_id, "Unknown")

        if best_box:
            x1, y1, x2, y2 = map(int, best_box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{class_name} ({max_conf:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if max_conf < CONF_THRESHOLD:
            if VERBOSE:
                print(f"⚠️ 낮은 conf={max_conf:.2f} → {class_name} 생략")
            continue

        if best_box is not None:
            if prev_box is None or iou(prev_box, best_box) < 0.5 or best_class_id != prev_class_id:
                bbox = (best_box[0], best_box[1], best_box[2] - best_box[0], best_box[3] - best_box[1])
                tracker = create_tracker("KCF")
                tracker.init(frame, bbox)

                tracker_box = best_box
                prev_class_id = best_class_id
                prev_box = best_box
                tracking_start_time = current_time
                tracking = True
                send_flag = True
            else:
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

    # === PyQt로 실시간 결과 전송 ===
    if tracker_box is not None:
        result_packet_live = {
            "class_name": CLASS_NAMES.get(prev_class_id, "Unknown"),
            "confidence": float(round(max_conf, 2)),
            "box": list(map(int, tracker_box))
        }
        try:
            pyqt_sock.sendto(json.dumps(result_packet_live).encode(), (PYQT_IP, PYQT_PORT))
        except Exception as e:
            print(f"⚠️ PyQt 전송 실패: {e}")

    # === Flask로 1회 전송 ===
    if send_flag and tracker_box is not None:
        class_name = CLASS_NAMES.get(prev_class_id, "Unknown")
        now = time.time()
        last_time = last_class_sent_time.get(prev_class_id, 0)
        skip_count[class_name] = skip_count.get(class_name, 0) + 1

        if skip_count[class_name] % 10 == 0:
            print(f"⏸️ {class_name} 최근 전송됨 → {skip_count[class_name]}회 누적 생략")

        image_b64 = encode_image_to_base64(frame)
        if image_b64:
            send_results(image_b64, class_name, max_conf, tracker_box)
            print(f"📡 Flask 전송: {class_name}")
            last_sent_time = current_time
            last_class_sent_time[prev_class_id] = now

    # === GUI 디버깅 확인용 ===
    cv2.imshow("DeepCycle AI - YOLOv8 + Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

sock.close()
cv2.destroyAllWindows()
