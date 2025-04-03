import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import os
import cv2

# UI 파일 로드 (DeepCycle_Client.ui 파일을 포함해야 합니다)
from_class = uic.loadUiType("DeepCycle_Client.ui")[0]

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

        # 카메라를 자동으로 시작하도록 설정
        self.cameraStart()

    def updateCamera(self):
        retval, image = self.video.read()  # 카메라로부터 이미지 읽기
        if retval:  # 이미지가 제대로 읽혔으면
            # 이미지 변환 (BGR -> RGB)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 이미지 데이터를 QImage로 변환
            height, width, channel = image_rgb.shape
            bytes_per_line = 3 * width
            qimg = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # QPixmap으로 변환 후 label에 표시
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)  # label 크기에 맞게 크기 조정
            self.label.setPixmap(pixmap)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
