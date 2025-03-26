import cv2
import base64

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
# 이미지 → base64 인코딩 함수
# ===============================
def encode_image_to_base64(frame):
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return None
    return base64.b64encode(buffer).decode("utf-8")
