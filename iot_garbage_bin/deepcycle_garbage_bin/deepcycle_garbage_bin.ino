#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// Wi-Fi 정보
const char* ssid = "AIE_509_2.4G";
const char* password = "addinedu_class1";
const char* serverURL = "http://192.168.0.56:5000/trashStatus";

WebServer server(80);

// 핀 정의
#define SERVO1_PIN 15
#define TRIG1_PIN 17
#define ECHO1_PIN 16

#define SERVO2_PIN 26
#define TRIG2_PIN 22
#define ECHO2_PIN 23

#define SERVO3_PIN 27
#define TRIG3_PIN 33
#define ECHO3_PIN 32

Servo servo1, servo2, servo3;

String image_name = "";
int materialCode = -1;

bool waiting[3] = {false, false, false};
unsigned long openTime[3] = {0, 0, 0};
bool ultrasonicChanged[3] = {false, false, false};

// 거리 측정 함수
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
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
    Serial.println("📥 서버 응답 내용: " + http.getString());

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

// JSON 수신 처리
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

    int index = -1;
    if (materialCode == 2) index = 0;
    else if (materialCode == 4) index = 1;
    else if (materialCode == 6) index = 2;

    if (index != -1) {
      Servo* servos[] = {&servo1, &servo2, &servo3};
      servos[index]->write(90);
      openTime[index] = millis();
      ultrasonicChanged[index] = false;
      waiting[index] = true;
      Serial.printf("⚙️ [%d번 상자] 서보모터 90도 열림\n", index + 1);
      server.send(200, "text/plain", "OK");
    } else {
      Serial.println("🚫 처리하지 않는 코드");
      server.send(400, "text/plain", "Unsupported material code");
    }
  } else {
    server.send(400, "text/plain", "Missing keys");
  }
}

void setup() {
  Serial.begin(115200);

  // 핀 설정
  pinMode(TRIG1_PIN, OUTPUT); pinMode(ECHO1_PIN, INPUT);
  pinMode(TRIG2_PIN, OUTPUT); pinMode(ECHO2_PIN, INPUT);
  pinMode(TRIG3_PIN, OUTPUT); pinMode(ECHO3_PIN, INPUT);

  servo1.attach(SERVO1_PIN); servo1.write(0);
  servo2.attach(SERVO2_PIN); servo2.write(0);
  servo3.attach(SERVO3_PIN); servo3.write(0);

  WiFi.begin(ssid, password);
  Serial.print("WiFi 연결 중");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi 연결됨!");
  Serial.println("ESP32 IP 주소: " + WiFi.localIP().toString());

  server.on("/", []() {
    server.send(200, "text/plain", "ESP32 is running");
  });

  server.on("/detectResult", HTTP_POST, handleDetectStatus);
  server.begin();
  Serial.println("🚀 HTTP 서버 시작됨");
}

void loop() {
  server.handleClient();

  int trigPins[3] = {TRIG1_PIN, TRIG2_PIN, TRIG3_PIN};
  int echoPins[3] = {ECHO1_PIN, ECHO2_PIN, ECHO3_PIN};
  Servo* servos[] = {&servo1, &servo2, &servo3};

  for (int i = 0; i < 3; i++) {
    if (waiting[i]) {
      float dist = getDistance(trigPins[i], echoPins[i]);
      unsigned long elapsed = millis() - openTime[i];
      Serial.printf("📏 [%d번] 거리: %.2f cm\n", i + 1, dist);

      if (elapsed <= 10000) {
        if (dist > 0 && dist <= 9 && !ultrasonicChanged[i]) {
          ultrasonicChanged[i] = true;

          Serial.printf("⏱️ [%d번] 감지됨 → 200ms 대기 중...\n", i + 1);
          delay(400); // 짧은 딜레이

          servos[i]->write(0);
          Serial.printf("✅ [%d번] 닫고 1 전송\n", i + 1);
          sendTrashStatus(image_name, 1);
          waiting[i] = false;
        }
      } else {
        servos[i]->write(0);
        Serial.printf("⏱️ [%d번] 10초 초과 → 닫고 0 전송\n", i + 1);
        sendTrashStatus(image_name, 0);
        waiting[i] = false;
      }

      delay(50); // 센서 측정 주기
    }
  }
}
