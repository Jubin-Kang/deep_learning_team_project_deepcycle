import sys
import cv2
import numpy as np
import datetime
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic

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

# UI 파일 로드
from_class = uic.loadUiType("DeepCycle.ui")[0]

# 저장할 폴더 생성
os.makedirs("Capture", exist_ok=True)
os.makedirs("Record", exist_ok=True)

class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("DeepCycle")

        self.isCameraOn = False
        self.isRecStart = False
        self.isVideoPlaying = False
        self.RecordBtn.hide()
        self.CaptureBtn.hide()

        self.pixmap = QPixmap()
        self.camera = Camera(self)
        self.camera.daemon = True

        self.timer = QTimer()  # 동영상 재생용 타이머 추가
        self.timer.timeout.connect(self.playVideo)

        self.OpenBtn.clicked.connect(self.openFile)
        self.CameraBtn.clicked.connect(self.clickCamera)
        self.camera.update.connect(self.updateCamera)
        self.RecordBtn.clicked.connect(self.clickRecord)
        self.CaptureBtn.clicked.connect(self.capture)

    # ✅ 캡처한 이미지를 "Capture" 폴더에 저장
    def capture(self):
        self.now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Capture/{self.now}.png"
        cv2.imwrite(filename, cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR))
        QMessageBox.information(self, "Capture", f"Image saved as {filename}")

    # ✅ 녹화 시작/정지 기능
    def clickRecord(self):
        if not self.isRecStart:
            self.RecordBtn.setText('Rec Stop')
            self.isRecStart = True
            self.recordingStart()
        else:
            self.RecordBtn.setText('Rec Start')
            self.isRecStart = False
            self.recordingStop()

    # ✅ 녹화 시작 (저장 위치: "Record")
    def recordingStart(self):
        self.now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.record_filename = f"Record/{self.now}.avi"
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        w = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        self.writer = cv2.VideoWriter(self.record_filename, self.fourcc, 20.0, (w, h))

    # ✅ 녹화 중지 시 알림 표시
    def recordingStop(self):
        if self.isRecStart:  # ✅ 녹화 중일 때만 실행
            self.writer.release()
            self.isRecStart = False  # ✅ 이제 녹화 상태 변경
            QMessageBox.information(self, "Recording", f"Recording stopped.\nSaved as: {self.record_filename}")  # ✅ 메시지박스 정상 표시

    def updateCamera(self):
        retval, image = self.video.read()
        if retval:
            self.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, c = self.image.shape
            qimage = QImage(self.image.data, w, h, w * c, QImage.Format_RGB888)
            self.pixmap = self.pixmap.fromImage(qimage)
            self.pixmap = self.pixmap.scaled(self.label.width(), self.label.height())
            self.label.setPixmap(self.pixmap)
            
            # ✅ 녹화 중이면 현재 프레임 저장
            if self.isRecStart:
                self.writer.write(cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR))

    def clickCamera(self):
        if not self.isCameraOn:
            self.CameraBtn.setText('Camera off')
            self.isCameraOn = True
            self.RecordBtn.show()
            self.CaptureBtn.show()
            self.cameraStart()
        else:
            self.CameraBtn.setText('Camera on')
            self.isCameraOn = False
            self.RecordBtn.hide()
            self.CaptureBtn.hide()
            self.cameraStop()
            self.recordingStop()

    def cameraStart(self):
        self.camera.running = True
        self.camera.start()
        self.video = cv2.VideoCapture(0)

    def cameraStop(self):
        self.camera.running = False
        self.video.release()

    # ✅ 저장된 동영상/이미지 파일 열기
    def openFile(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File", "Record", "Video Files (*.mp4 *.avi);;Image Files (*.png *.jpg *.jpeg)")
        if file:
            self.cameraStop()  # 카메라 중지
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.isVideoPlaying = False
                self.video.release()
                self.loadImage(file)
            else:
                self.video = cv2.VideoCapture(file)
                self.isVideoPlaying = True
                self.playVideo()

    # ✅ 선택한 이미지 로드
    def loadImage(self, file):
        image = cv2.imread(file)
        self.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, c = self.image.shape
        qimage = QImage(self.image.data, w, h, w * c, QImage.Format_RGB888)
        self.pixmap = self.pixmap.fromImage(qimage)
        self.pixmap = self.pixmap.scaled(self.label.width(), self.label.height())
        self.label.setPixmap(self.pixmap)

    # ✅ 동영상 재생 기능
    def playVideo(self):
        if self.isVideoPlaying and self.video.isOpened():
            retval, frame = self.video.read()
            if retval:
                self.image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, c = self.image.shape
                qimage = QImage(self.image.data, w, h, w * c, QImage.Format_RGB888)
                self.pixmap = self.pixmap.fromImage(qimage)
                self.pixmap = self.pixmap.scaled(self.label.width(), self.label.height())
                self.label.setPixmap(self.pixmap)
                QTimer.singleShot(30, self.playVideo)  # 다음 프레임 요청
            else:
                self.isVideoPlaying = False  # 동영상 끝
                self.video.release()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
