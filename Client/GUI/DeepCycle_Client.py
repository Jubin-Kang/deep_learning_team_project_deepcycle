import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import cv2
import socket
import numpy as np
import json
import time
from PIL import ImageFont, ImageDraw, Image

UDP_IP = "192.168.0.31"

from_class = uic.loadUiType("DeepCycle_Client.ui")[0]

name_map = {
    "Paper": "종이",
    "Paper pack": "종이팩",
    "Paper cup": "종이컵",
    "Can": "캔",
    "Glass Bottle": "유리병",
    "PET bottle": "페트병",
    "Plastic": "플라스틱",
    "Vinyl": "비닐",
    "Glass & Multi-layer Packaging": "이물질 유리병",
    "PET & Multi-layer Packaging": "이물질 페트병",
    "Styrofoam": "스티로폼",
    "Battery": "배터리"
}

class YoloReceiver(QThread):
    result_received = pyqtSignal(dict)
    message_received = pyqtSignal(str)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 6000))
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                result = json.loads(data.decode())

                if "message" in result:
                    self.message_received.emit(result["message"])
                else:
                    self.result_received.emit(result)
            except Exception as e:
                print(f"[❌] YOLO 수신 오류: {e}")

class Camera(QThread):
    update = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent
        self.running = True
        self.delay = 0.25

    def run(self):
        while self.running:
            self.update.emit()
            QThread.msleep(int(self.delay * 1000))

    def stop(self):
        self.running = False

class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("DeepCycle")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel("상태: 정상 대기 중", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: lightgray; font-size: 18px; font-weight: bold;")
        self.status_label.setFixedHeight(40)
        main_layout.addWidget(self.status_label)

        self.label = QLabel(self)
        self.label.setMinimumSize(320, 240)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setStyleSheet("background-color: #eeeeee;")
        self.label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.label)

        self.result_label = QLabel("현재 감지 객체: 없음", self)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        main_layout.addWidget(self.result_label)

        self.recent_label = QLabel("최근 감지 객체: 없음", self)
        self.recent_label.setAlignment(Qt.AlignCenter)
        self.recent_label.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(self.recent_label)

        self.udp_ip = UDP_IP
        self.udp_port = 1234
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.yolo_result = None
        self.prev_class_name = "없음"

        self.hide_timer = QTimer()
        self.hide_timer.setInterval(2000)
        self.hide_timer.timeout.connect(self.clear_detection)

        self.message_timer = QTimer()
        self.message_timer.setInterval(2000)
        self.message_timer.timeout.connect(self.clear_message)

        self.camera = Camera(self)
        self.camera.update.connect(self.updateCamera)

        self.receiver = YoloReceiver()
        self.receiver.result_received.connect(self.handle_yolo_result)
        self.receiver.message_received.connect(self.show_message)
        self.receiver.start()

        self.cameraStart()

    def show_message(self, msg):
        self.status_label.setText(f"⚠️ {msg}")
        self.status_label.setStyleSheet("background-color: red; font-size: 18px; font-weight: bold;")
        self.message_timer.start()

    def clear_message(self):
        self.status_label.setText("상태: 정상 대기 중")
        self.status_label.setStyleSheet("background-color: lightgray; font-size: 18px; font-weight: bold;")
        self.message_timer.stop()

    def handle_yolo_result(self, result):
        class_name_en = result.get('class_name', 'Unknown')
        class_name = name_map.get(class_name_en, class_name_en)
        conf = result.get('confidence', 0)

        # 현재 감지를 prev에 저장 후 업데이트
        if self.yolo_result:
            prev_en = self.yolo_result.get('class_name', 'Unknown')
            self.prev_class_name = name_map.get(prev_en, prev_en)

        self.yolo_result = result
        self.hide_timer.start()

        self.result_label.setText(f"현재 감지 객체: {class_name} ({conf:.2f})")
        self.recent_label.setText(f"최근 감지 객체: {self.prev_class_name}")

        if conf >= 0.8:
            self.status_label.setStyleSheet("background-color: green; font-size: 18px; font-weight: bold;")
        elif conf >= 0.5:
            self.status_label.setStyleSheet("background-color: yellow; font-size: 18px; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("background-color: red; font-size: 18px; font-weight: bold;")
            
    def clear_detection(self):
        # 현재 감지 객체를 최근 감지로 저장
        if self.yolo_result:
            class_name_en = self.yolo_result.get('class_name', 'Unknown')
            self.prev_class_name = name_map.get(class_name_en, class_name_en)
            self.recent_label.setText(f"최근 감지 객체: {self.prev_class_name}")
            
        self.yolo_result = None
        self.hide_timer.stop()
        self.result_label.setText("현재 감지 객체: 없음")


    def updateCamera(self):
        retval, image = self.video.read()
        if retval:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width, _ = image_rgb.shape

            if self.yolo_result and 'box' in self.yolo_result:
                x1, y1, x2, y2 = map(int, self.yolo_result['box'])
                scale_x = width / 480
                scale_y = height / 360
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                class_name_en = self.yolo_result.get('class_name', 'Unknown')
                class_name = name_map.get(class_name_en, class_name_en)
                confidence = self.yolo_result.get('confidence', 0)

                color = (0, 255, 0) if confidence >= 0.8 else (0, 255, 255) if confidence >= 0.5 else (0, 0, 255)

                cv2.rectangle(image_rgb, (x1, y1), (x2, y2), color, 2)

                image_pil = Image.fromarray(image_rgb)
                draw = ImageDraw.Draw(image_pil)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 18)
                except:
                    font = ImageFont.load_default()
                draw.text((x1, y1 - 25), f"{class_name} ({confidence:.2f})", font=font, fill=color)
                image_rgb = np.array(image_pil)

            qimg = QImage(image_rgb.data, width, height, 3 * width, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(pixmap)

            resized = cv2.resize(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), (480, 360))
            _, encoded_img = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if encoded_img is not None:
                try:
                    self.sock.sendto(encoded_img.tobytes(), (self.udp_ip, self.udp_port))
                except Exception as e:
                    print(f"[⚠️] UDP 전송 오류: {e}")

    def cameraStart(self):
        self.video = cv2.VideoCapture(0)
        if not self.video.isOpened():
            print("[❌] Camera not found!")
            return
        self.camera.running = True
        self.camera.start()

    def cameraStop(self):
        self.camera.running = False
        self.video.release()
        self.sock.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
