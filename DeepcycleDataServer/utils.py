import traceback
from flask import jsonify
import subprocess
import requests

def handle_exception(location: str, user_message="서버 오류가 발생했습니다. 다시 시도해주세요.", status_code=500):
    """
    공통 예외 처리 템플릿
    :param location: 예외 발생 함수나 API 이름
    :param user_message: 사용자에게 보여줄 메시지
    :param status_code: HTTP 상태 코드 (기본값 500)
    :return: Flask JSON 응답
    """
    def inner(e):
        print(f"[{location}] ❌ 예외 발생: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": user_message,
            "detail": str(e)
        }), status_code
    return inner

def get_ip_from_ifconfig():
    result = subprocess.run("hostname -I", shell=True, stdout=subprocess.PIPE)
    return result.stdout.decode().strip().split()[0] 


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}

def is_allowed_extension(ext):
    return ext.lower() in ALLOWED_EXTENSIONS

def notify_esp32(deepcycle_center_id, material_code, image_name, center_ip_map):
    try:
        esp32_ip = center_ip_map.get(deepcycle_center_id)
        payload = {"material_code": material_code, "image_name": image_name}
        response = requests.post(f"http://{esp32_ip}:80/detectResult", json=payload, timeout=3)

        if response.status_code == 200:
            print(f"[ESP32] - 응답: {response.text}")
        else:
            print(f"[ESP32] - 상태코드: {response.status_code}, 응답: {response.text}")
    except Exception as e:        
        print(f"[ESP32] - 통신 오류: {e}")