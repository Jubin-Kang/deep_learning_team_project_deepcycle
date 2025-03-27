from ultralytics import YOLO
import numpy as np
import cv2
import torch 

CLASS_NAMES = {
    0: "종이", 1: "종이팩", 2: "종이컵", 3: "캔류", 4: "유리병",
    5: "페트", 6: "플라스틱", 7: "비닐", 8: "유리+다중포장재",
    9: "페트+다중포장재", 10: "스티로폼", 11: "건전지"
}

class YoloDetector:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.model.to("cuda" if torch.cuda.is_available() else "cpu")


    def detect(self, frame):
        results = self.model.predict(frame, imgsz=640, conf=0.25, verbose=False)[0]
        best_conf = 0
        best_class_id = None
        best_box = None

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = box.conf.item()
            cls = int(box.cls[0])
            print(f"[YOLO] {CLASS_NAMES.get(cls, 'Unknown')} | conf={conf:.4f}")

            if conf > best_conf:
                best_conf = conf
                best_class_id = cls
                best_box = [x1, y1, x2, y2]

        return best_box, best_class_id, best_conf
    
# ===============================
# 디버깅용: 바운딩 박스 그려서 이미지 저장
# ===============================
def save_debug_image(frame, boxes, labels=None, output_path="debug.jpg"):
    img = frame.copy()
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if labels and i < len(labels):
            cv2.putText(img, labels[i], (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite(output_path, img)

# ===============================
# 디버깅용: 바운딩 박스 그려서 이미지 표시
# ===============================
def show_debug_image(frame, boxes, labels=None, window_name="Debug"):
    img = frame.copy()
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        if labels and i < len(labels):
            cv2.putText(img, labels[i], (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    cv2.imshow(window_name, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
