# ♻️ DeepCycle: 딥러닝 기반 스마트 분리수거 시스템

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/addinedu-ros-8th/deeplearning-repo-5">
    <img src="https://github.com/addinedu-ros-8th/deeplearning-repo-5/blob/main/DeepCycle.png" alt="Logo" width="500px">
  </a>

  <h3 align="center">스마트 분리 수거 시스템</h3>
  <p align="center">
    <a href="https://youtu.be/7Mb05Vj0SKM">Video Demo</a>\\
    <a href="https://www.miricanvas.com/v/14eaoym">Presentation</a>
  </p>
</p>
<hr>

> **환사모(환경을 사랑하는 모임)** 팀이 개발한, 인공지능을 활용한 스마트 쓰레기 분류 및 관리 시스템입니다.

---

## 📌 프로젝트 개요

DeepCycle은 YOLOv8 기반의 딥러닝 모델과 IoT 기술을 활용하여, 재활용 쓰레기를 실시간으로 분류하고 자동으로 적절한 분리수거통으로 배출하는 스마트 환경 시스템입니다.

- **프로젝트명**: DeepCycle  
- **팀명**: 환사모 (환경을 사랑하는 모임)  
- **주제**: 생활폐기물 스마트 분리수거 시스템  
- **핵심 기술**: YOLOv8, Python, ESP32, OpenCV, TCP/UDP Socket, PyQt5

## 팀 구성 및 역할
|        | name | job |
|--------|------|-----|
| leader | 강주빈 |  프로젝트 관리, GUI 설계 및 Server, AI 연동 |   
| worker | 권빛 |  데이터 전처리, 커스텀 AI 모델 개발, PPT 제작 및 README 작성 |   
| worker | 김규환 |  Data Server 구축, DB 및 통신 프로토콜 설계 |    
| worker | 이상윤 |  DB 구축, GUI와 AI 연동, 하드웨어 설계 및 구축 |   
| worker | 임승연 |  AI Server 구축, 통신 프로토콜 연동, GUI와 AI 연동 |   

---

## 🛠 기술 스택 (Tech Stack)

### 🧠 AI / 딥러닝  
![YOLO](https://img.shields.io/badge/YOLOv8n-00FFFF?style=flat&logo=github&logoColor=black)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat&logo=pytorch&logoColor=white)
![Ultralytics](https://img.shields.io/badge/Ultralytics-FFD700?style=flat&logo=python&logoColor=black)

### 📷 컴퓨터 비전  
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white)
![PIL](https://img.shields.io/badge/PIL-3776AB?style=flat&logo=python&logoColor=white)

### 💬 시스템 통신  
![TCP](https://img.shields.io/badge/TCP%2FUDP-005B9A?style=flat&logo=internet-computer&logoColor=white)
![RESTful](https://img.shields.io/badge/REST%20API-4E8EE0?style=flat&logo=fastapi&logoColor=white)
![Postman](https://img.shields.io/badge/Postman-FF6C37?style=flat&logo=postman&logoColor=white)

### 💻 소프트웨어 및 GUI  
![PyQt5](https://img.shields.io/badge/PyQt5-41CD52?style=flat&logo=qt&logoColor=white)
![Web UI](https://img.shields.io/badge/Admin%20Web%20UI-2D2D2D?style=flat&logo=html5&logoColor=white)
![VS Code](https://img.shields.io/badge/VS%20Code-007ACC?style=flat&logo=visual-studio-code&logoColor=white)

### 🖥️ 서버  
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)

### 📡 임베디드 제어  
![ESP32](https://img.shields.io/badge/ESP32-3C3C3C?style=flat&logo=espressif&logoColor=white)
![Ultrasonic Sensor](https://img.shields.io/badge/Ultrasonic%20Sensor-AAAAAA?style=flat&logo=simpleicons&logoColor=white)
![Servo Motor](https://img.shields.io/badge/Servo%20Motor-888888?style=flat&logo=gear&logoColor=white)

### 🗃 데이터베이스 / 로그 관리  
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![DBeaver](https://img.shields.io/badge/DBeaver-372923?style=flat&logo=dbeaver&logoColor=white)
![ERD](https://img.shields.io/badge/ERD%20Design-2B5797?style=flat&logo=diagrams-dot-net&logoColor=white)

### 📦 데이터 관리  
![AIHub](https://img.shields.io/badge/AIHub%20Dataset-00C853?style=flat&logo=databricks&logoColor=white)
![JSON](https://img.shields.io/badge/Bounding%20Box%20JSON-efefef?style=flat&logo=json&logoColor=black)

---

## 📁 데이터 정보

- **총 이미지 수**: 551,562장 (Bounding box 포함)
- **어노테이션 수**: 약 1,600,000개
- **데이터 출처**: [AIHub 생활폐기물 이미지 데이터셋](https://aihub.or.kr)
- **형식**: `.jpg`, `.png` + `.json` 라벨링
- **데이터 수집 출처**:
  - 선별장 촬영 영상 → 이미지 분할
  - 실내형 수거기 직접 촬영
  - 사용자 앱 활용 직접 촬영

---

## 🧠 모델 정보

- **사용 모델**: [YOLOv8n](https://github.com/ultralytics/ultralytics)
- **클래스 수**: YOLO 학습용 12 클래스 → 서버 처리용 7개 그룹으로 매핑

### 📦 YOLO → Server Class 매핑

| YOLO 클래스명 | 서버 전송 클래스 ID |
|---------------|---------------------|
| Paper | 1 |
| Paper Pack | 1 |
| Paper Cup | 1 |
| Can | 2 |
| Glass Bottle | 3 |
| PET Bottle | 4 |
| Plastic | 4 |
| Vinyl | 5 |
| Glass & Multi-layer Packaging | 6 |
| PET & Multi-layer Packaging | 6 |
| Styrofoam | 6 |
| Battery | 7 |

> 위 매핑을 통해 YOLO 탐지 결과를 서버 처리 목적에 맞게 통합 분류함.

---

## 🧩 시스템 구성

### 🖼 시스템 아키텍처 구성

#### HW Architecture
![HW](https://private-user-images.githubusercontent.com/53811474/430792410-40caacb1-2b48-44f7-9412-b26766c4b9a8.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQwMDI1OTQsIm5iZiI6MTc0NDAwMjI5NCwicGF0aCI6Ii81MzgxMTQ3NC80MzA3OTI0MTAtNDBjYWFjYjEtMmI0OC00NGY3LTk0MTItYjI2NzY2YzRiOWE4LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDA3VDA1MDQ1NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTliNWNkNzRkZWY5YTRiNTJhNjEzMmMwOWU5MzRlZWI5ZTIwYmMzNWMxZTYwNjVjZmMxNjI2NTAxODU2MDE1MDMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.9fGk2AlO-KOpu0ShffunHwgE0BnPdsgonaFU-kzByKQ)
<br >

#### SW Architecture
![SW](https://private-user-images.githubusercontent.com/53811474/430792441-8be21f34-c2d3-4dd2-92f0-e763784bc829.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQwMDI1OTQsIm5iZiI6MTc0NDAwMjI5NCwicGF0aCI6Ii81MzgxMTQ3NC80MzA3OTI0NDEtOGJlMjFmMzQtYzJkMy00ZGQyLTkyZjAtZTc2Mzc4NGJjODI5LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDA3VDA1MDQ1NFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPThiOTNlZTc2ODAwMWQ0YzgwNDQzMzIxZDkwOWU2YWE3Mzg0OWQzZmFiOTZmMmU5ZmRkMTVkM2M4MTMxZjI0ODUmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.M-7TNa88SNcPC_DkzBDOhaFlKDxScprakaoB7U7rsJg)
<br >

## ERD
![image](https://github.com/user-attachments/assets/197b5dc9-3cd1-4fd2-ae00-68c5c79903b9)
<br >

## Interface Specification
![image](https://github.com/user-attachments/assets/0ca15dcf-6799-408f-8231-a643f5bcc07a)
<br >

## GUI Specification
### Interface GUI
![image](https://github.com/user-attachments/assets/d70cc1d9-f4c2-4638-b04b-ff557c376e99)
<br >

### Admin GUI
![image](https://github.com/user-attachments/assets/826fcb31-95af-4716-83f4-6cb606fcd42a)
<br >

## Sequence Diagram
![image](https://github.com/user-attachments/assets/1f6bc3c2-01de-4e7a-be3e-7a5e1be77d96)
![image](https://github.com/user-attachments/assets/2f2030c7-5220-4091-964b-3d6d19504789)
<br >

## Implements
### Interface GUI
![image](https://github.com/user-attachments/assets/6ee83925-2547-44d4-8936-76e070e09418)
<br >

### Admin GUI
![image](https://github.com/user-attachments/assets/8c9c1be2-997b-496e-8cba-cacead336cb0)
<br >

### DeepCycle Bin
![image](https://github.com/user-attachments/assets/42121920-5b89-4b1c-80a3-7d6c562714b8)
<br >

## Project Schedule
Project Period: 2025.02.28~2025.04.08
<br >
![image](https://github.com/user-attachments/assets/6c294d85-bd1d-4bbd-aba5-b7dc032fd9ab)

## 작동 영상
![image](https://private-user-images.githubusercontent.com/53811474/430813322-428f8969-38b4-45fc-8c1c-49e2bf0625a3.gif?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQwMDc4ODQsIm5iZiI6MTc0NDAwNzU4NCwicGF0aCI6Ii81MzgxMTQ3NC80MzA4MTMzMjItNDI4Zjg5NjktMzhiNC00NWZjLThjMWMtNDllMmJmMDYyNWEzLmdpZj9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDA3VDA2MzMwNFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTJkMjk5OGQ0YjU1YzgwMDA4MTBjNGNlNWYwZWQ2ODA5MTc4ZDhmZjIxZDczNThmNTVhN2NhYmRmYmYxOTMxNDEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.EzabEd5Cl6dQ_UxBmxV4osmbTWo-QvPle3lUDVwVW1A)


![image](https://private-user-images.githubusercontent.com/53811474/430813390-38724641-1fca-4200-b42b-6461bcd8d517.gif?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQwMDc4ODQsIm5iZiI6MTc0NDAwNzU4NCwicGF0aCI6Ii81MzgxMTQ3NC80MzA4MTMzOTAtMzg3MjQ2NDEtMWZjYS00MjAwLWI0MmItNjQ2MWJjZDhkNTE3LmdpZj9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDA3VDA2MzMwNFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTNmMGFlOTE1ZWZjNzlmZmQ0MDgyNmNiMTFjZjM5Zjk4N2IwNGI3ODEyMTIyYmQwYzQ1Y2ViNjVhMTQ0OGE1ZjUmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.BMJNpkh_vBnWaltM1AA8rRrwZTPNBlWallq4Z-nWPss)


![image](https://private-user-images.githubusercontent.com/53811474/430813227-e23cf1b9-ed18-403d-b0a1-460fb33c2af2.gif?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDQwMDc4ODQsIm5iZiI6MTc0NDAwNzU4NCwicGF0aCI6Ii81MzgxMTQ3NC80MzA4MTMyMjctZTIzY2YxYjktZWQxOC00MDNkLWIwYTEtNDYwZmIzM2MyYWYyLmdpZj9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTA0MDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwNDA3VDA2MzMwNFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPWNmMzlhZTUwYmM3ZmQ2ODM4MWI4M2I1MzVkNWUzZWI5ZGM0NDFhZTYzZDM5MDI5NTc0OTgxYzgxYmZhOWVhNDEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.2Mi5D1MapGknMzg-7Xz9pgm-zOfcM2-wobNj16EzteA)
