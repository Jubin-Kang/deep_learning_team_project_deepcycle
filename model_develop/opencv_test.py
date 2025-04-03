import cv2
import numpy as np
from ultralytics import YOLO
import os
import time

# YOLO 모델 로드
model = YOLO("/home/yun/dev_ws/deeplearning-repo-5/model_develop/12_model.pt")

# YOLO 클래스 ID → 분류 번호 매핑
class_id_to_trash_number = {
    0: (4, "Plastic"),
    1: (3, "Glass"),
    2: (2, "Can"),
    3: (1, "Paper"),
    4: (5, "Vinyl"),
    5: (7, "Battery")
}
GENERAL_TRASH = (6, "General")

# 이물질 판단 함수
def is_contaminated(roi, threshold_std=20):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h_channel = hsv[:, :, 0]
    hist = cv2.calcHist([h_channel], [0], None, [180], [0, 180])
    hist = cv2.normalize(hist, hist).flatten()
    std_dev = np.std(hist)
    return std_dev > threshold_std

# 카메라 열기
cap = cv2.VideoCapture(2)
frame_count = 0
boxes_info = []  # 최근 인식 결과 저장용

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # YOLO 추론: 매 5프레임마다 한 번씩만 실행
    if frame_count % 5 == 0:
        boxes_info.clear()
        results = model(frame)[0]
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0].item())
            roi = frame[y1:y2, x1:x2]
            if is_contaminated(roi):
                trash_num, trash_name = GENERAL_TRASH
                color = (0, 0, 255)
            else:
                trash_num, trash_name = class_id_to_trash_number.get(cls_id, GENERAL_TRASH)
                color = (0, 255, 0)
            boxes_info.append((x1, y1, x2, y2, trash_num, trash_name, color))

    # 최근 YOLO 결과를 프레임에 표시
    for (x1, y1, x2, y2, trash_num, trash_name, color) in boxes_info:
        label = f"{trash_num}: {trash_name}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imshow("Trash Classification", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
