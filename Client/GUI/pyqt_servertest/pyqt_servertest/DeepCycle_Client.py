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

from_class = uic.loadUiType("DeepCycle_Client.ui")[0]

class YoloReceiver(QThread):
    result_received = pyqtSignal(dict)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 6000))
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                result = json.loads(data.decode())
                self.result_received.emit(result)
            except Exception as e:
                print(f"[❌] YOLO 수신 오류: {e}")

class Camera(QThread):
    update = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent
        self.running = True
        self.delay = 0.15

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

        # QLabel 크기 고정
        self.label.setFixedSize(640, 480)

        # 상태 텍스트
        self.label2.setText("Camera On")
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.label2.setFont(font)

        # UDP 설정
        self.udp_ip = "192.168.0.28"
        self.udp_port = 1234
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Detection 결과
        self.yolo_result = None

        # Detection hide 타이머
        self.hide_timer = QTimer()
        self.hide_timer.setInterval(2000)  # 2초
        self.hide_timer.timeout.connect(self.clear_detection)

        # 스레드
        self.camera = Camera(self)
        self.camera.update.connect(self.updateCamera)

        self.receiver = YoloReceiver()
        self.receiver.result_received.connect(self.handle_yolo_result)
        self.receiver.start()

        # 카메라 시작
        self.cameraStart()

    def handle_yolo_result(self, result):
        self.yolo_result = result
        self.hide_timer.start()  # 2초 뒤 Detection 자동 삭제
        class_name = result.get('class_name', 'Unknown')
        conf = result.get('confidence', 0)
        box = result.get('box', [])
        log = f"[수신] class: {class_name}, conf: {conf:.2f}, box: {box}"
        print(log)

    def clear_detection(self):
        self.yolo_result = None
        self.hide_timer.stop()

    def updateCamera(self):
        retval, image = self.video.read()
        if retval:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).copy()
            height, width, _ = image_rgb.shape

            # Detection 표시
            if self.yolo_result and 'box' in self.yolo_result:
                x1, y1, x2, y2 = map(int, self.yolo_result['box'])
                scale_x = width / 480
                scale_y = height / 360
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                class_name = self.yolo_result.get('class_name', 'Unknown')
                confidence = self.yolo_result.get('confidence', 0)

                # 부드러운 회색 (200, 200, 200)
                cv2.rectangle(image_rgb, (x1, y1), (x2, y2), (200, 200, 200), 2)
                cv2.putText(image_rgb, f"{class_name} ({confidence:.2f})",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (200, 200, 200), 2)

            # QLabel 표시
            qimg = QImage(image_rgb.data, width, height, 3 * width, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(pixmap)

            # 서버로 전송
            resized = cv2.resize(image, (480, 360))
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
