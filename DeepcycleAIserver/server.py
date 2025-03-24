import sys
sys.path.append("/home/lim/dev_ws/deepcycle/yolov5")
import cv2
import torch
import base64
import requests
from models.common import DetectMultiBackend
from utils.general import non_max_suppression

# YOLO 설정
MODEL_PATH = "/home/lim/dev_ws/deepcycle/12_model.pt"
OUTPUT_IMAGE_PATH = "/home/lim/dev_ws/deepcycle/RecycleAI/receive_data/detected_result.jpeg"
TCP_SERVER_URL = "http://192.168.0.48:5000/upload"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DetectMultiBackend(MODEL_PATH, device=device)
model.eval()

# 스트리밍 수신
cap = cv2.VideoCapture("udp://0.0.0.0:1234", cv2.CAP_FFMPEG)

def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def send_results(image_path, detected_data):
    encoded_image = encode_image(image_path)
    extension = image_path.split(".")[-1]

    data = {
        "image": encoded_image,
        "extension": extension,
        "result": detected_data
    }

    response = requests.post(TCP_SERVER_URL, json=data)
    print(f"🟢 서버 응답: {response.json()}")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ 프레임 수신 실패")
        continue

    # YOLO 입력 준비
    resized = cv2.resize(frame, (640, 640))
    img_tensor = torch.from_numpy(resized).permute(2, 0, 1).float().unsqueeze(0).to(device) / 255.0

    with torch.no_grad():
        pred = model(img_tensor)
        detections = non_max_suppression(pred)

    detected_objects = []
    for det in detections[0]:
        x1, y1, x2, y2, conf, cls = det.cpu().numpy()
        detected_objects.append({
            "confidence": float(conf), "class": int(cls)
        })
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{int(cls)} {conf:.2f}', (int(x1), int(y1)-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 감지된 객체가 있을 때만 처리
    if detected_objects:
        cv2.imwrite(OUTPUT_IMAGE_PATH, frame)
        print(f"📸 감지된 이미지 저장: {OUTPUT_IMAGE_PATH}")
        send_results(OUTPUT_IMAGE_PATH, detected_objects)

    # 결과 출력
    cv2.imshow("DeepCycle AI - YOLO", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()