import requests
import base64
import os

url = 'http://192.168.0.48:5000/upload'  # 서버 주소
image_path = 'test.jpg'  # 업로드할 이미지 파일

# 파일 확장자 가져오기
ext = os.path.splitext(image_path)[1].replace(".", "")

# 이미지 파일을 Base64로 변환
with open(image_path, "rb") as img_file:
    encoded_string = base64.b64encode(img_file.read()).decode('utf-8')

# 서버로 전송할 데이터
data = {
    "image": encoded_string,
    "extension": ext  # 파일 확장자 전달
}

# POST 요청
response = requests.post(url, json=data)

# 응답 출력
print(response.json())
