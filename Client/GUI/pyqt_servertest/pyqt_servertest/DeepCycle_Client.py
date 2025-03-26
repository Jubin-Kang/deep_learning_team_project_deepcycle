import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import os
import cv2
import socket
import numpy as np
from PyQt5.QtGui import QPainter, QPen, QColor
import json  

# UI 파일 로드 (DeepCycle_Client.ui 파일을 포함해야 합니다)
from_class = uic.loadUiType("DeepCycle_Client.ui")[0]

class YoloReceiver(QThread):
    result_received = pyqtSignal(dict)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 6000))  # YOLO 서버가 보내주는 포트
        while True:
            try:
                data, _ = sock.recvfrom(4096)
                result = json.loads(data.decode())
                self.result_received.emit(result)
            except Exception as e:
                print(f"YOLO 수신 오류: {e}")

class Camera(QThread):
    update = pyqtSignal()

    def __init__(self, sec=0, parent=None):
        super().__init__()
        self.main = parent
        self.running = True
        self.delay = 0.05 

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

        # label2에 "Camera ON" 초기 텍스트 설정
        self.label2.setText("Camera On")
        font = QFont()
        font.setPointSize(20)  # 글자 크기 설정
        font.setBold(True)  # 글자를 굵게 설정
        self.label2.setFont(font)

        self.isCameraOn = True  # 기본적으로 카메라는 켜짐 상태로 설정
        self.camera = Camera(self)
        self.camera.daemon = True

        self.camera.update.connect(self.updateCamera)

        # UDP 소켓 설정
        self.udp_ip = "192.168.0.28"  # 서버와 같은 네트워크 IP 사용

        self.udp_port =1234     # DeepCycle AI 서버 포트
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 카메라를 자동으로 시작하도록 설정
        self.cameraStart()

        self.yolo_result = None  # 수신된 YOLO 결과 저장
        
        # YOLO 결과 수신 스레드 연결
        self.receiver = YoloReceiver()
        self.receiver.result_received.connect(self.handle_yolo_result)
        self.receiver.start()
    
    def updateCamera(self):
        retval, image = self.video.read()
        if retval:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            if self.yolo_result and 'box' in self.yolo_result:
                x1, y1, x2, y2 = map(int, self.yolo_result['box'])
                class_name = self.yolo_result.get('class_name', 'Unknown')
                confidence = self.yolo_result.get('confidence', 0)
                
                cv2.rectangle(image_rgb, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(image_rgb, f"{class_name} ({confidence:.2f})",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            height, width, channel = image_rgb.shape
            bytes_per_line = 3 * width
            qimg = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(pixmap)
            
            # 🟡 이미지 전송 전에 해상도를 줄여서 패킷 크기 감소
            resized = cv2.resize(image, (320, 240))  # 또는 (480, 360)
            _, encoded_img = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if encoded_img is not None:
                try:
                    self.sock.sendto(encoded_img.tobytes(), (self.udp_ip, self.udp_port))
                    # print(f"📤 전송 크기: {len(encoded_img)} bytes")  # 디버깅용
                except Exception as e:
                    print(f"UDP 전송 오류: {e}")

    def cameraStart(self):
        # 카메라 초기화
        self.video = cv2.VideoCapture(0)  # 기본 카메라 열기
        if not self.video.isOpened():
            print("Camera not found!")
            return

        # 카메라 캡처를 위한 스레드 시작
        self.camera.running = True
        self.camera.start()

    def cameraStop(self):
        # 카메라 중지
        self.camera.running = False
        self.video.release()
        self.sock.close()
    
    def handle_yolo_result(self, result):
        self.yolo_result = result

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
