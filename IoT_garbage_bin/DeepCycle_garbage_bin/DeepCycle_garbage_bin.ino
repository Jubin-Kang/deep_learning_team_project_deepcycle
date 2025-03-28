#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// Wi-Fi 정보
const char* ssid = "AIE_509_2.4G";
const char* password = "addinedu_class1";
const char* serverURL = "http://192.168.0.48:5000/trashStatus";

WebServer server(80);

// 핀 정의
#define SERVO1_PIN 26
#define TRIG1_PIN 23
#define ECHO1_PIN 22

#define SERVO2_PIN 27
#define TRIG2_PIN 18
#define ECHO2_PIN 19

Servo servo1;
Servo servo2;

// 제어용 변수
String image_name = "";
int materialCode = -1;
bool waitingForTrash1 = false;
bool waitingForTrash2 = false;
unsigned long openTime1 = 0;
unsigned long openTime2 = 0;
bool ultrasonicChanged1 = false;
bool ultrasonicChanged2 = false;

// 거리 측정 함수 (핀 지정 가능)
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000); // timeout: 30ms
  return duration * 0.034 / 2.0;
}

// 서버로 처리 결과 전송
void sendTrashStatus(String img, int result) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"image_name\": \"" + img + "\", \"trash_status\": " + String(result) + "}";
    int responseCode = http.POST(payload);

    String responseBody = http.getString();  // ← 응답 본문 받아오기
    Serial.println("📥 서버 응답 내용: " + responseBody);

    if (responseCode > 0) {
      Serial.print("📡 서버 응답 코드: ");
      Serial.println(responseCode);
    } else {
      Serial.print("❌ 서버 전송 실패: ");
      Serial.println(responseCode);
    }

    http.end();
  }
}

// JSON 수신 핸들러
void handleDetectStatus() {
  Serial.println("📡 [서버] /detectResult 요청 수신됨");

  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "No data received");
    return;
  }

  String body = server.arg("plain");
  Serial.println("📥 수신된 JSON 데이터: " + body);

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    Serial.println("❌ JSON 파싱 실패: " + String(error.c_str()));
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  if (doc.containsKey("material_code") && doc.containsKey("image_name")) {
    materialCode = doc["material_code"];
    image_name = doc["image_name"].as<String>();

    Serial.println("🧠 코드: " + String(materialCode) + " / 이미지: " + image_name);

    if (materialCode == 1) {
      Serial.println("⚙️ [1번] 서보모터 90도 열림");
      servo1.write(90);
      openTime1 = millis();
      ultrasonicChanged1 = false;
      waitingForTrash1 = true;
    } else if (materialCode == 2) {
      Serial.println("⚙️ [2번] 서보모터 90도 열림");
      servo2.write(90);
      openTime2 = millis();
      ultrasonicChanged2 = false;
      waitingForTrash2 = true;
    } else {
      Serial.println("🚫 처리하지 않는 코드: " + String(materialCode));
    }

    server.send(200, "text/plain", "OK");
  } else {
    server.send(400, "text/plain", "Missing keys");
  }
}

void setup() {
  Serial.begin(115200);

  // 핀 설정
  pinMode(TRIG1_PIN, OUTPUT);
  pinMode(ECHO1_PIN, INPUT);
  pinMode(TRIG2_PIN, OUTPUT);
  pinMode(ECHO2_PIN, INPUT);

  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  servo1.write(0);
  servo2.write(0);

  // Wi-Fi 연결
  WiFi.begin(ssid, password);
  Serial.print("WiFi 연결 중");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi 연결됨!");
  Serial.println("ESP32 IP 주소: " + WiFi.localIP().toString());

  // 서버 라우팅
  server.on("/", []() {
    server.send(200, "text/plain", "ESP32 is running");
  });

  server.on("/detectResult", HTTP_POST, handleDetectStatus);
  server.begin();
  Serial.println("🚀 HTTP 서버 시작됨");
}

void loop() {
  server.handleClient();
  delay(10);

  // 1번 센서 처리
  if (waitingForTrash1) {
    float dist = getDistance(TRIG1_PIN, ECHO1_PIN);
    unsigned long elapsed = millis() - openTime1;
    Serial.println("📏 [1번] 거리: " + String(dist) + " cm");

    if (elapsed <= 20000) {
      if (dist > 0 && dist <= 8 && !ultrasonicChanged1) {
        ultrasonicChanged1 = true;
        Serial.println("✅ [1번] 감지됨 → 닫고 1 전송");
        servo1.write(0);
        sendTrashStatus(image_name, 1);
        waitingForTrash1 = false;
      }
    } else {
      Serial.println("⏱️ [1번] 20초 초과, 미감지 → 닫고 0 전송");
      servo1.write(0);
      sendTrashStatus(image_name, 0);
      waitingForTrash1 = false;
    }
    delay(500);
  }

  // 2번 센서 처리
  if (waitingForTrash2) {
    float dist = getDistance(TRIG2_PIN, ECHO2_PIN);
    unsigned long elapsed = millis() - openTime2;
    Serial.println("📏 [2번] 거리: " + String(dist) + " cm");

    if (elapsed <= 20000) {
      if (dist > 0 && dist <= 8 && !ultrasonicChanged2) {
        ultrasonicChanged2 = true;
        Serial.println("✅ [2번] 감지됨 → 닫고 1 전송");
        servo2.write(0);
        sendTrashStatus(image_name, 1);
        waitingForTrash2 = false;
      }
    } else {
      Serial.println("⏱️ [2번] 20초 초과, 미감지 → 닫고 0 전송");
      servo2.write(0);
      sendTrashStatus(image_name, 0);
      waitingForTrash2 = false;
    }
    delay(500);
  }
}
