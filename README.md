# deeplearning-repo-5
딥러닝 프로젝트 5조 저장소.

<<<<<<< HEAD
팀명 : 환사모 (환경을 사랑하는 모임)

팀 프로젝트 명 : DeepCycle
=======
팀원: 강주빈, 김규환, 이상윤, 임승연, 권빛

# ♻️ DeepCycle: 딥러닝 기반 스마트 분리수거 시스템
>>>>>>> dev

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/addinedu-ros-8th/deeplearning-repo-5">
    <img src="https://github.com/addinedu-ros-8th/deeplearning-repo-5/blob/main/DeepCycle.png" alt="Logo" width="500px">
  </a>

  <h3 align="center">스마트 분리 수거 시스템</h3>
</p>
<hr>

<<<<<<< HEAD
<!-- ABOUT THE PROJECT -->
## Preview
Deeplearning 기술을 활용하여 스마트 분리 수거 시스템 개발


=======
> **환사모(환경을 사랑하는 모임)** 팀이 개발한, 인공지능을 활용한 스마트 쓰레기 분류 및 관리 시스템입니다.

---

## 📌 프로젝트 개요

DeepCycle은 YOLOv8 기반의 딥러닝 모델과 IoT 기술을 활용하여, 재활용 쓰레기를 실시간으로 분류하고 자동으로 적절한 분리수거통으로 배출하는 스마트 환경 시스템입니다.

- **프로젝트명**: DeepCycle  
- **팀명**: 환사모 (환경을 사랑하는 모임)  
- **주제**: 생활폐기물 스마트 분리수거 시스템  
- **핵심 기술**: YOLOv8, Python, ESP32, OpenCV, TCP/UDP Socket, PyQt5

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
- **클래스 수**: 학습용 12개 → 실시간 분류 6개 그룹 축소  
- **분류 클래스**:

| 최종 그룹 | 포함된 클래스 |
|-----------|----------------|
| 0. 종이 | 종이, 종이팩, 종이컵 |
| 1. 캔 | 캔 |
| 2. 유리 | 재사용 유리, 색깔 유리, 유리+다중포장재 |
| 3. 플라스틱/페트 | 페트, 다중포장재 포함 |
| 4. 비닐 | 비닐 |
| 5. 일반 쓰레기 | 이물질 혼합 항목 전반 |

---

## 🧩 시스템 구성

### 🖼 시스템 아키텍처 구성
>>>>>>> dev

