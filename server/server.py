from flask import Flask, request, jsonify, send_from_directory
from db import insert_image_result, get_image_list_with_pagination, get_statistics, select_esp32_ip
import os
import base64
import datetime
import json
import random
import string
import requests

import threading

app = Flask(__name__)

center_ip_map = {}

# 이미지 저장 폴더 설정
UPLOAD_FOLDER = os.path.abspath("./data")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 허용된 이미지 확장자
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}

def is_allowed_extension(ext):
    return ext.lower() in ALLOWED_EXTENSIONS

def notify_esp32(deepcycle_center_id, material_code, filename):
    try:

        esp32_ip = center_ip_map.get(deepcycle_center_id)

        payload = {
            "material_code": material_code,
            "filename": filename
        }
        response = requests.post(f"http://{esp32_ip}:80/detectResult", json=payload, timeout=3)

        if response.status_code == 200:
            print(f"[ESP32] LED ON 성공 - 응답: {response.text}")
        else:
            print(f"[ESP32] LED 제어 실패 - 상태코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:
        print(f"[ESP32 통신 에러] {e}")

# 이미지 업로드 API
@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json(force=True)

        required_fields = ['image', 'extension', 'box', 'deepcycle_center_id', 'confidence', 'class']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400

        ext = data['extension']
        if not is_allowed_extension(ext):
            return jsonify({'error': f'Unsupported file extension: {ext}'}), 400

        image_data = base64.b64decode(data['image'])
        detect_box_str = ','.join(map(str, data['box']))

        deepcycle_center_id = data["deepcycle_center_id"]
        result_confidence = data["confidence"]
        material_code = data["class"]
        
        # 파일명 생성 (타임스탬프 + 랜덤문자)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{deepcycle_center_id}_{material_code}_{timestamp}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        threading.Thread(target=notify_esp32(deepcycle_center_id, material_code, filename)).start()
        
        # 파일 저장
        with open(filepath, "wb") as f:
            f.write(image_data)

        file_size = os.path.getsize(filepath)

        insert_image_result(filename, deepcycle_center_id, file_size, material_code, result_confidence, detect_box_str)

        image_url = f"http://192.168.0.48:5000/images/{filename}"

        return jsonify({'status': 'success', 'image_url': image_url})

    except Exception as e:
        print(f"[Upload Error] {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/statistics', methods=['POST'])
def get_statistics_api():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()
    required_fields = ["start_date", "end_date", "deepcycle_center_id", "page", "page_size"]

    print(data)

    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        stats = get_statistics(
            start_date=data["start_date"],
            end_date=data["end_date"],
            deepcycle_center_id=data["deepcycle_center_id"],
            page=int(data["page"]),
            page_size=int(data["page_size"])
        )

        return jsonify({
            "status": "success",
            "list": stats["list"],
            "total_count": stats["total_count"],
            "total_pages": stats["total_pages"],
            "page": stats["page"],
            "page_size": stats["page_size"]
        })
    except Exception as e:
        print(f"[Statistics Error] {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/selectImages', methods=['POST'])
def select_images():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()

    required_fields = ["start_date", "end_date", "deepcycle_center_id", "code"]
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        page = int(data.get("page", 1))
        page_size = int(data.get("page_size", 10))

        result = get_image_list_with_pagination(
            start_date=data["start_date"],
            end_date=data["end_date"],
            page=page,
            page_size=page_size,
            deepcycle_center_id=data["deepcycle_center_id"],
            code=data["code"]
        )

        return jsonify({
            "status": "success",
            "page": page,
            "page_size": page_size,
            "total_count": result["total_count"],
            "total_pages": result["total_pages"],
            "list": result["list"]
        })
    except Exception as e:
        print(f"[SelectImages Error] {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        print(f"[GetImage Error] {e}")
        return jsonify({'error': 'Image not found'}), 404


@app.route('/trashStatus', methods=['POST'])
def trash_status():
    try:
        data = request.get_json()
        print(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"[GetImage Error] {e}")
        return jsonify({'error': 'Image not found'}), 404
    
if __name__ == '__main__':
    results = select_esp32_ip()
    center_ip_map = {row[0]: row[1] for row in results}

    print(f"[INFO] ESP32 센터 맵 로딩 완료: {center_ip_map}")
    print(f"Server running... Images will be saved in: {UPLOAD_FOLDER}")
    app.run(debug=True, host='0.0.0.0', port=5000)
