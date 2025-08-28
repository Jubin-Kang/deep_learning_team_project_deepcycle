import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
import requests
import json
from io import BytesIO

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.pyplot as plt

# UI 파일 로드
from_class = uic.loadUiType("deepcycle_admin.ui")[0]

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)

    def plot_data(self, labels, values):
        print("🔹 그래프 데이터:", labels, values)  # 데이터 출력 확인
        self.ax.clear()
        self.ax.bar(labels, values, color=['blue', 'orange', 'green', 'red', 'purple', 'gray'])
        self.ax.set_xlabel("Categories")
        self.ax.set_ylabel("Values")
        self.ax.set_title("Recycling Statistics")
        self.draw()  # 그래프 다시 그리기



class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("DeepCycle")

        # 기존 테이블 1 관련 페이지 변수
        self.current_page = 1
        self.page_size = 8  # 한 페이지에 보여줄 데이터 개수

        # 🔹 tableWidget_2 관련 페이지 변수
        self.current_page_2 = 1
        self.page_size_2 = 8  # 한 페이지에 보여줄 데이터 개수

        # Matplotlib 그래프 추가
        if self.graphWidget.layout():
            while self.graphWidget.layout().count():
                item = self.graphWidget.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.graphWidget.layout().deleteLater()

        layout = QVBoxLayout(self.graphWidget)
        self.canvas = MplCanvas(self.graphWidget)
        layout.addWidget(self.canvas)
        self.graphWidget.setLayout(layout)

        # QTableWidget 설정
        self.setupTable()

        # 그래프 추가
        self.setupGraph()

        # 서버에서 데이터 가져와서 테이블 업데이트
        self.fetchTableData()

        # 더블 클릭 시 이벤트 처리
        self.tableWidget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tableWidget_2.itemDoubleClicked.connect(self.on_image_double_clicked)

        # 🔹 추가: Statistics 테이블 클릭 시 label_3 업데이트
        self.tableWidget.cellClicked.connect(self.updateLabel)
        # 통계 테이블 클릭 시 그래프 업데이트
        self.tableWidget.cellClicked.connect(self.updateGraph)

        # 다음/이전 페이지 버튼 추가
        self.nextButton.clicked.connect(self.nextPage)
        self.prevButton.clicked.connect(self.prevPage)

        # 🔹 tableWidget_2용 버튼 연결
        self.nextButton_2.clicked.connect(self.nextPage_2)
        self.prevButton_2.clicked.connect(self.prevPage_2)
        
        # 페이지 번호를 표시할 QLabel 업데이트
        self.updatePageLabel()  # tableWidget 페이지 번호 업데이트
        self.updatePageLabel_2()  # tableWidget_2 페이지 번호 업데이트

    def setupTable(self):
        """ QTableWidget 초기 설정 """
        # 통계 테이블 (Statistics)
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(["Date", "Paper", "Can", "Glass", "Plastic", "Vinyl", "General"])
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

    def setupGraph(self):
        """ 그래프 초기화 """
        self.canvas.ax.clear()  # 기존 그래프 초기화
        self.canvas.ax.set_xlabel("Categories")
        self.canvas.ax.set_ylabel("Values")
        self.canvas.ax.set_title("Recycling Statistics")
        self.canvas.draw()


    def fetchTableData(self):
        """ 서버에서 데이터 가져와서 테이블 업데이트 (현재 페이지 반영) """
        print(f"📡 데이터 요청 - 페이지: {self.current_page}")

        url = "http://192.168.0.48:5000/statistics"
        headers = {'Content-Type': 'application/json'}
        data = {
            "deepcycle_center_id": 1,
            "start_date": "2025-03-01",
            "end_date": "2025-03-31",
            "page": self.current_page,  # 🔹 현재 페이지 반영
            "page_size": self.page_size  # 🔹 페이지 크기 유지
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            if 'list' in response_data:
                self.updateTable(response_data['list'])

                # 🔹 첫 번째 행의 데이터를 그래프로 표시
                if len(response_data['list']) > 0:
                    self.updateGraph(0, 1)  # 첫 번째 행 선택

        except requests.exceptions.RequestException as e:
            print(f"❌ 데이터 가져오기 오류: {e}")

    def updatePageLabel(self):
        """현재 페이지를 label_page에 업데이트"""
        self.label_page.setText(f"Page {self.current_page} / {self.page_size}")

    def updatePageLabel_2(self):
        """tableWidget_2의 현재 페이지를 label_page_2에 업데이트"""
        self.label_page_2.setText(f"Page {self.current_page_2} / {self.page_size_2}")

    def nextPage(self):
        """ 다음 페이지로 이동 """
        self.current_page += 1  # 페이지 증가
        print(f"➡️ 다음 페이지: {self.current_page}")
        self.fetchTableData()  # 새로운 데이터 요청
        self.updatePageLabel()  # 페이지 번호 업데이트

    def prevPage(self):
        """ 이전 페이지로 이동 (첫 페이지 이하로 내려가지 않음) """
        if self.current_page > 1:
            self.current_page -= 1  # 페이지 감소
            print(f"⬅️ 이전 페이지: {self.current_page}")
            self.fetchTableData()  # 새로운 데이터 요청
            self.updatePageLabel()  # 페이지 번호 업데이트
        else:
            print("🚫 첫 번째 페이지입니다.")

    def nextPage_2(self):
        """ tableWidget_2의 다음 페이지로 이동 """
        self.current_page_2 += 1  # 페이지 증가
        print(f"➡️ tableWidget_2 다음 페이지: {self.current_page_2}")

        if hasattr(self, 'last_selected_date') and hasattr(self, 'last_selected_code') and hasattr(self, 'last_selected_category'):
            self.fetchAdditionalData(self.last_selected_date, self.last_selected_code, self.last_selected_category)
        else:
            print("🚨 이전에 선택된 데이터가 없습니다.")
        self.updatePageLabel_2()  # 페이지 번호 업데이트


    def prevPage_2(self):
        """ tableWidget_2의 이전 페이지로 이동 (첫 페이지 이하로 내려가지 않음) """
        if self.current_page_2 > 1:
            self.current_page_2 -= 1  # 페이지 감소
            print(f"⬅️ tableWidget_2 이전 페이지: {self.current_page_2}")

            # `last_selected_date`, `last_selected_code`, `last_selected_category`가 존재할 때만 fetchAdditionalData 호출
            if hasattr(self, 'last_selected_date') and hasattr(self, 'last_selected_code') and hasattr(self, 'last_selected_category'):
                self.fetchAdditionalData(self.last_selected_date, self.last_selected_code, self.last_selected_category)
                self.updatePageLabel_2()  # 페이지 번호 업데이트
            else:
                print("🚨 이전에 선택된 데이터가 없습니다.")
        else:
            print("🚫 tableWidget_2 첫 번째 페이지입니다.")




    def updateTable(self, data_list):
        """ 테이블에 서버 데이터 업데이트 """
        self.tableWidget.setRowCount(len(data_list))

        for row, entry in enumerate(data_list):
            date_item = QTableWidgetItem(entry['date'])
            paper_item = QTableWidgetItem(str(entry['paper']))
            can_item = QTableWidgetItem(str(entry['can']))
            glass_item = QTableWidgetItem(str(entry['glass']))
            plastic_item = QTableWidgetItem(str(entry['plastic']))
            vinyl_item = QTableWidgetItem(str(entry['vinyl']))  # 신규 컬럼 추가
            general_item = QTableWidgetItem(str(entry['general']))

            self.tableWidget.setItem(row, 0, date_item)
            self.tableWidget.setItem(row, 1, paper_item)
            self.tableWidget.setItem(row, 2, can_item)
            self.tableWidget.setItem(row, 3, glass_item)
            self.tableWidget.setItem(row, 4, plastic_item)
            self.tableWidget.setItem(row, 5, vinyl_item)  # 새로운 컬럼 반영
            self.tableWidget.setItem(row, 6, general_item)

    def updateGraph(self, row=0, column=1):
        """ 선택한 행의 데이터를 그래프로 표시 + 선택한 행 강조 + 클릭된 날짜를 그래프 제목에 표시 """
        try:
            labels = ["Paper", "Can", "Glass", "Plastic", "Vinyl", "General"]
            values = [int(self.tableWidget.item(row, i + 1).text()) for i in range(6)]
            
            # 선택한 행을 강조 (하이라이트 효과)
            self.tableWidget.selectRow(row)

            # 🔹 클릭된 날짜 가져오기
            date_value = self.tableWidget.item(row, 0).text()  # 첫 번째 열 (Date)

            print(f"✅ 그래프 업데이트 - 날짜: {date_value}, 값: {values}")  # 데이터 확인
            
            # 그래프 업데이트
            self.canvas.ax.clear()  # 기존 그래프 지우기
            self.canvas.ax.bar(labels, values, color=['blue', 'orange', 'green', 'red', 'purple', 'gray'])
            self.canvas.ax.set_xlabel("Categories")
            self.canvas.ax.set_ylabel("Values")

            # 🔹 그래프 제목에 클릭된 날짜 추가
            self.canvas.ax.set_title(f"Recycling Statistics ({date_value})", fontsize=12, fontweight='bold')

            self.canvas.draw()  # 그래프 다시 그리기
        except Exception as e:
            print(f"❌ 그래프 업데이트 오류: {e}")



    def updateLabel(self, row, column):
        """ 클릭한 컬럼 이름을 label_3에 표시 """
        column_names = ["Date", "Paper", "Can", "Glass", "Plastic", "Vinyl", "General"]
        
        if column > 0:  # 첫 번째 컬럼(Date)은 제외
            self.label_3.setText(column_names[column])



    def on_item_double_clicked(self, item):
        """ Statistics 테이블에서 더블 클릭 시 Admin GUI 테이블 업데이트 """
        row = item.row()
        column = item.column()

        if column == 0:  # Date 컬럼 제외
            return

        date = self.tableWidget.item(row, 0).text()
        category_codes = {
            1: "Paper",
            2: "Can",
            3: "Glass",
            4: "Plastic",
            5: "Vinyl",
            6: "General"
        }

        code = column  # 컬럼 순서 변경 반영
        category = category_codes.get(code, "Unknown")

        # 🔹 마지막 선택값 저장 (다음 페이지 요청 시 사용)
        self.last_selected_date = date
        self.last_selected_code = code
        self.last_selected_category = category

        # 서버에서 Time과 Image 관련 데이터 가져오기
        self.fetchAdditionalData(date, code, category)




    def fetchAdditionalData(self, date, code, category):
        print(f"fetchAdditionalData 호출됨 - {category}")
        print(f"📡 tableWidget_2 데이터 요청 - 페이지: {self.current_page_2}")

        url = "http://192.168.0.48:5000/selectImages"
        headers = {'Content-Type': 'application/json'}
        data = {
            "deepcycle_center_id": 1,
            "start_date": date,
            "end_date": date,
            "code": code,  # 선택된 코드 적용
            "page": self.current_page_2,
            "page_size": self.page_size_2
        }
        print(data)

        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            if 'list' in response_data:
                time_list = [entry['save_date'] for entry in response_data['list']]
                image_list = [entry['image_url'] for entry in response_data['list']]
                self.updateAdminTable(time_list, image_list, category)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching additional data: {e}")

    def updateAdminTable(self, time_list, image_list, category):
        print(f"updateAdminTable 실행됨 - {category}, 데이터 개수:", len(time_list))

        self.tableWidget_2.setRowCount(len(time_list))

        for row, (time, image) in enumerate(zip(time_list, image_list)):
            time_item = QTableWidgetItem(time)
            image_item = QTableWidgetItem(image)  # 이미지 URL

            self.tableWidget_2.setItem(row, 0, time_item)
            self.tableWidget_2.setItem(row, 1, image_item)

        # label2 업데이트 (선택한 재활용 품목명 표시)
        self.label2.setText(category)


    def on_image_double_clicked(self, item):
        """ Admin GUI 테이블에서 Image 열을 더블 클릭하면 오른쪽 QLabel에 표시 """
        if item.column() == 1:  # Image 열
            image_url = item.text()
            self.displayImage(image_url)

    def displayImage(self, image_url):
        """ QLabel에 이미지 표시 및 label_3 업데이트 """
        try:
            response = requests.get(image_url)
            response.raise_for_status()

            image_data = BytesIO(response.content)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data.getvalue())

            # QLabel에 이미지 설정
            self.image_label.setPixmap(pixmap)
            self.image_label.setScaledContents(True)  # 이미지 크기 조정

        except requests.exceptions.RequestException as e:
            print(f"Error loading image: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
