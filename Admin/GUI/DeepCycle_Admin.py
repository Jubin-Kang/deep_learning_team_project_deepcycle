import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import requests
import json
from io import BytesIO

# UI 파일 로드
from_class = uic.loadUiType("DeepCycle_Admin.ui")[0]

class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("DeepCycle")

        # QTableWidget 설정
        self.setupTable()

        # 서버에서 데이터 가져와서 테이블 업데이트
        self.fetchTableData()

        # 더블 클릭 시 이벤트 처리
        self.tableWidget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tableWidget_2.itemDoubleClicked.connect(self.on_image_double_clicked)

        # 🔹 추가: Statistics 테이블 클릭 시 label_3 업데이트
        self.tableWidget.cellClicked.connect(self.updateLabel)

    def setupTable(self):
        """ QTableWidget 초기 설정 """
        # 통계 테이블 (Statistics)
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setHorizontalHeaderLabels(["Date", "Plastic", "Glass", "Can", "Paper", "General"])
        self.tableWidget.setRowCount(7)

        # 관리자 GUI 테이블 (Admin GUI)
        self.tableWidget_2.setColumnCount(2)
        self.tableWidget_2.setHorizontalHeaderLabels(["Time", "Image"])
        self.tableWidget_2.setRowCount(0)

        # 테이블 크기 조정
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        header = self.tableWidget_2.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)

        # 비율 적용 (3:7)
        self.tableWidget_2.setColumnWidth(0, int(self.tableWidget_2.width() * 0.3))
        self.tableWidget_2.setColumnWidth(1, int(self.tableWidget_2.width() * 0.7))

        # 셀 수정 비활성화
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget_2.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def fetchTableData(self):
        """ 서버에서 데이터 가져와서 테이블 업데이트 """
        print("fetchTableData 호출됨")
        url = "http://192.168.0.48:5000/statistics"
        headers = {'Content-Type': 'application/json'}
        data = {
            "deepcycle_center_id": 1,
            "start_date": "2025-03-24",
            "end_date": "2025-03-31",
            "page": 1,
            "page_size": 10
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            if 'list' in response_data:
                self.updateTable(response_data['list'])

        except requests.exceptions.RequestException as e:
            print(f"Error fetching table data: {e}")

    def updateTable(self, data_list):
        """ 테이블에 서버 데이터 업데이트 """
        self.tableWidget.setRowCount(len(data_list))

        for row, entry in enumerate(data_list):
            date_item = QTableWidgetItem(entry['date'])
            plastic_item = QTableWidgetItem(str(entry['plastic']))
            glass_item = QTableWidgetItem(str(entry['glass']))
            can_item = QTableWidgetItem(str(entry['can']))
            paper_item = QTableWidgetItem(str(entry['paper']))
            general_item = QTableWidgetItem(str(entry['general']))

            self.tableWidget.setItem(row, 0, date_item)
            self.tableWidget.setItem(row, 1, plastic_item)
            self.tableWidget.setItem(row, 2, glass_item)
            self.tableWidget.setItem(row, 3, can_item)
            self.tableWidget.setItem(row, 4, paper_item)
            self.tableWidget.setItem(row, 5, general_item)

    def updateLabel(self, row, column):
        """ Statistics 테이블에서 특정 컬럼 클릭 시 label_3 업데이트 """
        if column == 1:  # Plastic 컬럼
            self.label_3.setText("Plastic")

    def on_item_double_clicked(self, item):
        """ Statistics 테이블 항목을 더블 클릭 시 Admin GUI 테이블 업데이트 """
        row = item.row()
        date = self.tableWidget.item(row, 0).text()

        # 서버에서 Time과 Image 관련 데이터를 가져옴
        self.fetchAdditionalData(date)

    def fetchAdditionalData(self, date):
        print("fetchAdditionalData 호출됨")
        """ 추가 데이터를 서버에서 가져와 Admin GUI 테이블에 업데이트 """
        url = "http://192.168.0.48:5000/selectImages"
        headers = {'Content-Type': 'application/json'}
        data = {
            "deepcycle_center_id": 1,
            "start_date": date,
            "end_date": date,
            "code": 3,
            "page": 1,
            "page_size": 10
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            if 'list' in response_data:
                time_list = [entry['save_date'] for entry in response_data['list']]
                image_list = [entry['image_url'] for entry in response_data['list']]
                self.updateAdminTable(time_list, image_list)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching additional data: {e}")

    def updateAdminTable(self, time_list, image_list):
        print("updateAdminTable 실행됨, 데이터 개수:", len(time_list))
        """ Admin GUI 테이블에 Time과 Image 데이터 업데이트 """
        self.tableWidget_2.setRowCount(len(time_list))

        for row, (time, image) in enumerate(zip(time_list, image_list)):
            time_item = QTableWidgetItem(time)
            image_item = QTableWidgetItem(image)  # 이미지 URL

            self.tableWidget_2.setItem(row, 0, time_item)
            self.tableWidget_2.setItem(row, 1, image_item)

    def on_image_double_clicked(self, item):
        """ Admin GUI 테이블에서 Image 열을 더블 클릭하면 오른쪽 QLabel에 표시 """
        if item.column() == 1:  # Image 열
            image_url = item.text()
            self.displayImage(image_url)

    def displayImage(self, image_url):
        """ QLabel에 이미지 표시 및 label_3에 'Plastic' 표시 """
        try:
            response = requests.get(image_url)
            response.raise_for_status()

            image_data = BytesIO(response.content)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data.getvalue())

            # QLabel에 이미지 설정
            self.image_label.setPixmap(pixmap)
            self.image_label.setScaledContents(True)  # 이미지 크기 조정

            # label_3에 "Plastic" 표시
            self.label2.setText("Plastic")

        except requests.exceptions.RequestException as e:
            print(f"Error loading image: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
