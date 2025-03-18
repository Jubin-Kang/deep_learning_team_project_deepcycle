from flask import Flask, request, jsonify, send_from_directory
import os
import base64
import datetime

app = Flask(__name__)

# 이미지 저장 폴더 설정
UPLOAD_FOLDER = os.path.abspath("./data")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 이미지 업로드 API
@app.route('/upload', methods=['POST'])
def upload_image():
    data = request.json  # JSON 데이터 받기

    if 'image' not in data or 'extension' not in data:
        return jsonify({'error': 'Missing image data or extension'}), 400

    try:
        # Base64 디코딩
        image_data = base64.b64decode(data['image'])
        ext = data['extension']  # 확장자 (예: jpg, png)

        # 파일명: 현재 PC 시간 기준
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # 파일 저장
        with open(filepath, "wb") as f:
            f.write(image_data)

        image_url = f"http://192.168.0.48:5000/images/{filename}"

        return jsonify({'status': 'success', 'image_url': image_url})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 타입 조회 API (GET)
@app.route('/type/<type>', methods=['GET'])
def get_type(type):
    type_list = ["plastic", "glass", "can", "paper", "butangas"]
    if type in type_list:
        return jsonify({'status': 'success', 'type': type})
    else:
        return jsonify({'error': 'Invalid type'}), 400


# 타입 저장 API (POST)
@app.route('/type', methods=['POST'])
def save_type():
    data = request.json

    if not data:
        return jsonify({'error': 'Missing type data'}), 400

    return jsonify({'status': 'success', **data})


# ✅ 통계 데이터 조회 API (POST)
@app.route('/statistics', methods=['POST'])
def get_statistics():
    # 요청의 Content-Type이 JSON이 아닌 경우 처리
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    data = request.get_json()  # JSON 데이터 가져오기

    if not data or "start_date" not in data or "end_date" not in data:
        return jsonify({'error': 'Missing start_date or end_date'}), 400

    # 샘플 데이터 반환
    stats = {
        "status": "success",
        "plastic": 1,
        "glass": 1,
        "can": 4,
        "paper": 2,
        "butangas": 4
    }
    return jsonify(stats)


# 특정 기간의 이미지 리스트 조회 API (POST)
@app.route('/selectImages', methods=['POST'])
def select_images():
    data = request.json
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not start_date or not end_date:
        return jsonify({'error': 'Missing start_date or end_date'}), 400

    # 샘플 이미지 리스트 반환
    image_list = [
        {"image_url": "https://example.com/uploads/image123.jpg"},
        {"image_url": "https://example.com/uploads/image124.jpg"}
    ]

    return jsonify({"status": "success", "list": image_list})

# 저장된 이미지 접근 API
@app.route('/images/<filename>')
def get_image(filename):
    print(UPLOAD_FOLDER,filename)
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    print(f"Server running... Images will be saved in: {UPLOAD_FOLDER}")
    app.run(debug=True, host='0.0.0.0', port=5000)
