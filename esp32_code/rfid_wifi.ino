/*
 * ============================================================
 * AttendEase — ESP32 + RC522 RFID Attendance System
 * ============================================================
 *
 * Hardware:
 *   - ESP32 dev board
 *   - MFRC522 RFID reader
 *   - Green LED (GPIO 2)
 *   - Red LED   (GPIO 4)
 *   - Buzzer    (GPIO 15)
 *   - Optional OLED SSD1306 (I2C: SDA=21, SCL=22)
 *
 * RC522 Wiring (SPI):
 *   SDA(SS)  → GPIO 5
 *   SCK      → GPIO 18
 *   MOSI     → GPIO 23
 *   MISO     → GPIO 19
 *   RST      → GPIO 22
 *   3.3V     → 3.3V
 *   GND      → GND
 *
 * Libraries needed (install via Arduino Library Manager):
 *   - MFRC522 by miguelbalboa
 *   - ArduinoJson by Benoit Blanchon
 *   - Adafruit SSD1306 + GFX (optional, for OLED)
 *
 * ============================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// ─── CONFIGURATION — CHANGE THESE ───────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://192.168.1.100:5001/api/scan"; // Your Flask server IP
const char* API_KEY       = "rfid-secret-key-2024";              // Match settings page
// ────────────────────────────────────────────────────────────

// Pin definitions
#define SS_PIN    5
#define RST_PIN   22
#define LED_GREEN 2
#define LED_RED   4
#define BUZZER    15

MFRC522 rfid(SS_PIN, RST_PIN);

// Optional OLED (comment out to disable)
// #define USE_OLED
#ifdef USE_OLED
  #include <Wire.h>
  #include <Adafruit_GFX.h>
  #include <Adafruit_SSD1306.h>
  #define SCREEN_W 128
  #define SCREEN_H 64
  Adafruit_SSD1306 display(SCREEN_W, SCREEN_H, &Wire, -1);
#endif

// Cooldown: prevent same card re-scanning within 5 seconds
String lastUID     = "";
unsigned long lastScanTime = 0;
const unsigned long COOLDOWN_MS = 5000;

// ─── Setup ──────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[AttendEase] RFID Attendance System Starting...");

  // Pins
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED,   OUTPUT);
  pinMode(BUZZER,    OUTPUT);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED,   LOW);

  // SPI + RFID
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("[RFID] RC522 initialised.");

  // OLED
  #ifdef USE_OLED
    Wire.begin(21, 22);
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
      Serial.println("[OLED] Not found — continuing without display");
    } else {
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(0, 0);
      display.println("AttendEase");
      display.println("Connecting WiFi...");
      display.display();
    }
  #endif

  // WiFi
  connectWiFi();

  // Boot signal: 2 beeps
  beep(100); delay(100); beep(100);
  Serial.println("[READY] Waiting for RFID card...");
  oledPrint("Ready", "Scan your card");
}

// ─── Main Loop ──────────────────────────────────────────────
void loop() {
  // Re-connect if WiFi dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Lost connection. Reconnecting...");
    connectWiFi();
  }

  // Wait for card
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Build UID string
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Cooldown check (same card within 5s)
  unsigned long now = millis();
  if (uid == lastUID && (now - lastScanTime) < COOLDOWN_MS) {
    Serial.println("[SCAN] Same card too soon, ignoring.");
    return;
  }
  lastUID      = uid;
  lastScanTime = now;

  Serial.print("[SCAN] UID: ");
  Serial.println(uid);
  oledPrint("Scanning...", uid);

  // Send to server
  sendScan(uid);

  delay(500);
}

// ─── WiFi Connect ───────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.print(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500); Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    oledPrint("WiFi OK", WiFi.localIP().toString());
    flashLED(LED_GREEN, 2);
  } else {
    Serial.println("\n[WiFi] FAILED. Will retry later.");
    flashLED(LED_RED, 3);
  }
}

// ─── Send Scan to Flask ─────────────────────────────────────
void sendScan(String uid) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] WiFi not connected.");
    responseFail("No WiFi");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  // Build JSON payload
  StaticJsonDocument<200> doc;
  doc["uid"] = uid;
  String body;
  serializeJson(doc, body);

  Serial.println("[HTTP] POST → " + String(SERVER_URL));
  Serial.println("[HTTP] Body: " + body);

  int httpCode = http.POST(body);
  Serial.print("[HTTP] Response code: ");
  Serial.println(httpCode);

  if (httpCode == 200 || httpCode == 201) {
    String payload = http.getString();
    Serial.println("[HTTP] Response: " + payload);

    StaticJsonDocument<300> resp;
    DeserializationError err = deserializeJson(resp, payload);

    if (!err) {
      String status  = resp["status"].as<String>();
      String name    = resp["name"].as<String>();
      String message = resp["message"].as<String>();

      if (status == "success") {
        responseSuccess(name, message);
      } else if (status == "duplicate") {
        responseDuplicate(name, message);
      } else {
        responseFail(message);
      }
    }
  } else if (httpCode == 404) {
    responseUnknown();
  } else {
    Serial.println("[HTTP] Error code: " + String(httpCode));
    responseFail("Server error " + String(httpCode));
  }

  http.end();
}

// ─── Feedback Functions ─────────────────────────────────────

void responseSuccess(String name, String msg) {
  Serial.println("[✅] SUCCESS: " + name + " — " + msg);
  oledPrint("PRESENT", name);
  flashLED(LED_GREEN, 1);
  beep(300);
}

void responseDuplicate(String name, String msg) {
  Serial.println("[⏰] DUPLICATE: " + name + " — " + msg);
  oledPrint("Already Marked", name);
  flashLED(LED_GREEN, 2);
  beep(80); delay(80); beep(80);
}

void responseUnknown() {
  Serial.println("[❌] UNKNOWN UID — not registered");
  oledPrint("Unknown Card", "Not registered");
  flashLED(LED_RED, 1);
  beep(800);
}

void responseFail(String msg) {
  Serial.println("[❌] FAIL: " + msg);
  oledPrint("Error", msg);
  flashLED(LED_RED, 2);
  beep(300); delay(100); beep(300);
}

// ─── LED Flash ──────────────────────────────────────────────
void flashLED(int pin, int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(200);
    digitalWrite(pin, LOW);
    delay(150);
  }
}

// ─── Buzzer Beep ────────────────────────────────────────────
void beep(int ms) {
  digitalWrite(BUZZER, HIGH);
  delay(ms);
  digitalWrite(BUZZER, LOW);
}

// ─── OLED Display ───────────────────────────────────────────
void oledPrint(String line1, String line2) {
  #ifdef USE_OLED
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("AttendEase");
    display.drawLine(0, 10, 128, 10, SSD1306_WHITE);
    display.setTextSize(2);
    display.setCursor(0, 16);
    display.println(line1);
    display.setTextSize(1);
    display.setCursor(0, 48);
    display.println(line2);
    display.display();
  #else
    // Serial fallback
    Serial.println("[OLED] " + line1 + " | " + line2);
  #endif
}
