import traceback
from flask import jsonify

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
