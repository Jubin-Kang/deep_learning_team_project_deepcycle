from flask import Flask, request, jsonify, send_from_directory
from flask_restx import Api, Resource, fields, Namespace
from db import insert_image_result, get_image_list_with_pagination, get_statistics, select_esp32_ip, update_trash_status
from utils import handle_exception

from dotenv import load_dotenv
import os
import base64
import datetime
import requests
import threading
import subprocess

app = Flask(__name__)
api = Api(app, version='1.0', title='DeepCycle API',
          description='재활용 이미지 업로드 및 통계 API 문서',
          doc='/docs')

ns = Namespace('/', description='DeepCycle 기능 API')
api.add_namespace(ns)

center_ip_map = {}

load_dotenv()

def get_ip_from_ifconfig():
    result = subprocess.run("hostname -I", shell=True, stdout=subprocess.PIPE)
    return result.stdout.decode().strip().split()[0]  # 첫 번째 IP만 반환

DATA_SERVER_URL = get_ip_from_ifconfig()
UPLOAD_FOLDER = os.path.abspath("./data")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}

def is_allowed_extension(ext):
    return ext.lower() in ALLOWED_EXTENSIONS

def notify_esp32(deepcycle_center_id, material_code, image_name):
    try:
        esp32_ip = center_ip_map.get(deepcycle_center_id)
        payload = {"material_code": material_code, "image_name": image_name}
        response = requests.post(f"http://{esp32_ip}:80/detectResult", json=payload, timeout=3)

        if response.status_code == 200:
            print(f"[ESP32] - 응답: {response.text}")
        else:
            print(f"[ESP32] - 상태코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:
        # return handle_exception("notify_esp32", "ESP32 통신 에러.", status_code=500)(e)
        print(f"[ESP32] - 통신 오류: {e}")

upload_model = ns.model('UploadModel', {
    'image': fields.String(required=True, description='Base64 인코딩된 이미지'),
    'extension': fields.String(required=True, description='파일 확장자 (jpg, png 등)'),
    'box': fields.List(fields.Integer, required=True, description='탐지된 박스 좌표 [x1, y1, x2, y2]'),
    'deepcycle_center_id': fields.Integer(required=True, description='deepcycle center id'),
    'confidence': fields.Float(required=True, description='탐지 신뢰도'),
    'class': fields.Integer(required=True, description='재질 클래스 1: paper 2: can 3: glass 4: plastic 5: vinyl 6: general 7: battery')
})

upload_response_model = ns.model('UploadResponse', {
    'status': fields.String(description='처리 결과 상태'),
    'image_url': fields.String(description='저장된 이미지 접근 URL')
})

@ns.route('/upload')
class Upload(Resource):
    @ns.expect(upload_model)
    @ns.marshal_with(upload_response_model)
    def post(self):
        """
        이미지 업로드 및 저장 API
        - 이미지 Base64 데이터와 메타 정보를 받아 DB에 저장하고 ESP32에 알림
        """
        try:
            data = request.get_json(force=True)
            required_fields = ['image', 'extension', 'box', 'deepcycle_center_id', 'confidence', 'class']
            for field in required_fields:
                if field not in data:
                    return handle_exception("upload_image", f'{field}가 없습니다.', status_code=400)(Exception(f"Missing field: {field}"))

            ext = data['extension']
            if not is_allowed_extension(ext):
                return handle_exception("upload_image", f"지원하지 않는 파일 확장자: {ext}", status_code=400)(Exception(f"Unsupported extension: {ext}"))

            image_data = base64.b64decode(data['image'])
            detect_box_str = ','.join(map(str, data['box']))
            deepcycle_center_id = data["deepcycle_center_id"]
            result_confidence = data["confidence"]
            material_code = data["class"]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_name = f"{deepcycle_center_id}_{material_code}_{timestamp}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, image_name)
            
            threading.Thread(target=notify_esp32, args=(deepcycle_center_id, material_code, image_name)).start()
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            file_size = os.path.getsize(filepath)
            insert_image_result(image_name, deepcycle_center_id, file_size, material_code, result_confidence, detect_box_str)
            image_url = f"{DATA_SERVER_URL}/images/{image_name}"
            return {'status': 'success', 'image_url': image_url}
        except Exception as e:            
            return handle_exception("upload_image", "이미지 업로드 중 오류가 발생했습니다.", status_code=500)(e)

statistics_model = ns.model('StatisticsRequest', {
    'start_date': fields.String(required=True, description='조회 시작일 (YYYY-MM-DD)'),
    'end_date': fields.String(required=True, description='조회 종료일 (YYYY-MM-DD)'),
    'deepcycle_center_id': fields.Integer(required=True, description='deepcycle center id'),
    'page': fields.Integer(required=False, description='페이지 번호', default=1),
    'page_size': fields.Integer(required=False, description='페이지당 항목 수', default=10)
})

statistics_response_model = ns.model('StatisticsResponse', {
    'status': fields.String(description='처리 결과 상태'),
    'list': fields.List(fields.Raw, description='통계 데이터 리스트'),
    'total_count': fields.Integer(description='총 항목 수'),
    'total_pages': fields.Integer(description='총 페이지'),
    'page': fields.Integer(description='페이지 번호'),
    'page_size': fields.Integer(description='페이지당 항목 수')
})

@ns.route('/statistics')
class Statistics(Resource):
    @ns.expect(statistics_model)
    @ns.marshal_with(statistics_response_model)
    def post(self):
        """
        통계 조회 API
        - 날짜 범위 및 센터 ID 기준으로 분류별 통계 데이터를 반환합니다.
        """
        if not request.is_json:
            return handle_exception("Statistics", "Content-Type must be application/json", status_code=415)(Exception("Invalid Content-Type"))

        data = request.get_json()
        required_fields = ["start_date", "end_date", "deepcycle_center_id", "page", "page_size"]
        for field in required_fields:
            if field not in data:
                return handle_exception("Statistics", f'{field}가 없습니다.', status_code=400)(Exception(f"Missing field: {field}"))

        try:
            stats = get_statistics(
                start_date=data["start_date"],
                end_date=data["end_date"],
                deepcycle_center_id=data["deepcycle_center_id"],
                page=int(data.get("page", 1)),
                page_size=int(data.get("page_size", 10))
            )
            return {
                "status": "success",
                "list": stats["list"],
                "total_count": stats["total_count"],
                "total_pages": stats["total_pages"],
                "page": stats["page"],
                "page_size": stats["page_size"]
            }
        except Exception as e:
            return handle_exception("Statistics", "조회 중 오류 발생", status_code=500)(e)

select_images_model = ns.model('SelectImagesRequest', {
    'start_date': fields.String(required=True, description='조회 시작일 (YYYY-MM-DD)'),
    'end_date': fields.String(required=True, description='조회 종료일 (YYYY-MM-DD)'),
    'deepcycle_center_id': fields.Integer(required=True, description='deepcycle center id'),
    'code': fields.Integer(required=True, description='재질 코드'),
    'page': fields.Integer(required=False, description='페이지 번호', default=1),
    'page_size': fields.Integer(required=False, description='페이지당 항목 수', default=10)
})

select_images_response_model = ns.model('SelectImagesResponse', {
    'status': fields.String(description='처리 결과 상태'),
    'total_count': fields.Integer(description='총 항목 수'),
    'total_pages': fields.Integer(description='총 페이지'),
    'page': fields.Integer(description='페이지 번호'),
    'page_size': fields.Integer(description='페이지당 항목 수'),    
    'list': fields.List(fields.Raw, description='이미지 항목 리스트')
})

@ns.route('/selectImages')
class SelectImages(Resource):
    @ns.expect(select_images_model)
    @ns.marshal_with(select_images_response_model)
    def post(self):
        """
        이미지 조회 API
        - 날짜, 센터 ID, 재질 코드로 필터링된 이미지 리스트를 반환합니다.
        """
        if not request.is_json:
            return handle_exception("SelectImages", "Content-Type must be application/json", status_code=415)(Exception("Invalid Content-Type"))

        data = request.get_json()
        required_fields = ["start_date", "end_date", "deepcycle_center_id", "code"]
        for field in required_fields:
            if field not in data:
                return handle_exception("SelectImages", f'{field}가 없습니다.', status_code=400)(Exception(f"Missing field: {field}"))

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
            return {
                "status": "success",
                "page": page,
                "page_size": page_size,
                "total_count": result["total_count"],
                "total_pages": result["total_pages"],
                "list": result["list"]
            }
        except Exception as e:
            return handle_exception("SelectImages", "조회 중 오류 발생", status_code=500)(e)

trash_status_model = ns.model('TrashStatusRequest', {
    'image_name': fields.String(required=True, description='업데이트할 이미지 파일 이름'),
    'trash_status': fields.Integer(required=True, description='쓰레기 상태 값')
})


trash_status_response_model = ns.model('TrashStatusResponse', {
    'status': fields.String(description='처리 결과')
})

@ns.route('/trashStatus')            
class TrashStatus(Resource):
    @ns.expect(trash_status_model)
    @ns.marshal_with(trash_status_response_model)
    def post(self):
        """
        쓰레기통 상태 수신 API
        - 센서에서 수신한 쓰레기통 상태 데이터를 처리합니다.
        """
        try:
            data = request.get_json()
            
            image_name = data["image_name"]
            trash_status = data["trash_status"]

            result = update_trash_status(image_name, trash_status)

            if result.get("success"):
                return {"status": f"success {trash_status}"}
            else:
                return handle_exception("TrashStatus", "DB 업데이트 실패", status_code=500)(Exception(result.get("error")))
            
        except Exception as e:
            return handle_exception("TrashStatus", "수정 중 오류 발생", status_code=500)(e)

@app.route('/images/<image_name>', methods=['GET'])
def get_image(image_name):
    try:
        return send_from_directory(UPLOAD_FOLDER, image_name)
    except Exception as e:
        return handle_exception("get_image", "이미지가 없습니다.", status_code=404)(e)

if __name__ == '__main__':
    results = select_esp32_ip()
    center_ip_map = {row[0]: row[1] for row in results}
    print(f"[INFO] ESP32 센터 맵 로딩 완료: {center_ip_map}")
    print(f"Server running... Images will be saved in: {UPLOAD_FOLDER}")
    app.run(debug=True, host='0.0.0.0', port=5000)
