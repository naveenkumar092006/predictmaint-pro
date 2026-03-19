// ============================================================
//  PredictMaint Pro — ESP32 Sensor Firmware
//  Upload this to ESP32 using Arduino IDE
//
//  Libraries to install (Arduino IDE → Library Manager):
//    - OneWire
//    - DallasTemperature
//    - Adafruit MPU6050
//    - Adafruit BMP280
//    - ArduinoJson
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_Sensor.h>

// ── CONFIGURATION — change these ──────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://YOUR_LAPTOP_IP:5000/api/esp32-data";
const char* MACHINE_ID    = "MCH-101";  // change per machine
const char* DEVICE_ID     = "ESP32-001";
const int   SEND_INTERVAL = 2000;       // send every 2 seconds
// ──────────────────────────────────────────────────────────

// DS18B20 temperature — pin GPIO4
#define TEMP_PIN 4
OneWire           oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);

// MPU6050 vibration — I2C (SDA=GPIO21, SCL=GPIO22)
Adafruit_MPU6050  mpu;

// BMP280 pressure — I2C (same bus as MPU6050)
Adafruit_BMP280   bmp;

// Operating hours counter (resets on power cycle — use EEPROM for persistence)
unsigned long startMillis = 0;
float operatingHours = 1200.0;  // starting hours (match your machine in models.py)

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== PredictMaint Pro ESP32 Sensor ===");

  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\n✅ WiFi connected: " + WiFi.localIP().toString());
  Serial.println("Sending to: " + String(SERVER_URL));

  // Init temperature sensor
  tempSensor.begin();
  Serial.println("✅ DS18B20 temperature sensor ready");

  // Init MPU6050 (vibration)
  if (mpu.begin()) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("✅ MPU6050 vibration sensor ready");
  } else {
    Serial.println("⚠️  MPU6050 not found — using simulated vibration");
  }

  // Init BMP280 (pressure)
  if (bmp.begin(0x76)) {
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_500);
    Serial.println("✅ BMP280 pressure sensor ready");
  } else {
    Serial.println("⚠️  BMP280 not found — using simulated pressure");
  }

  startMillis = millis();
  Serial.println("=== Sending data every " + String(SEND_INTERVAL) + "ms ===\n");
}

void loop() {
  // ── Read temperature ────────────────────────────────────
  tempSensor.requestTemperatures();
  float temperature = tempSensor.getTempCByIndex(0);
  if (temperature == DEVICE_DISCONNECTED_C) {
    temperature = 68.0 + random(-5, 5);  // fallback if sensor disconnected
  }

  // ── Read vibration (RMS of acceleration) ───────────────
  float vibration = 1.2;
  sensors_event_t accel, gyro, temp_event;
  if (mpu.getEvent(&accel, &gyro, &temp_event)) {
    float ax = accel.acceleration.x;
    float ay = accel.acceleration.y;
    float az = accel.acceleration.z - 9.81;  // remove gravity
    vibration = sqrt(ax*ax + ay*ay + az*az) * 0.3;  // scale to mm/s
    vibration = constrain(vibration, 0.1, 8.0);
  }

  // ── Read pressure ───────────────────────────────────────
  float pressure = 4.5;
  if (bmp.takeForcedMeasurement()) {
    // BMP280 reads atmospheric pressure — scale to machine pressure range
    float atm = bmp.readPressure() / 100000.0;  // convert Pa to bar
    pressure  = atm * 4.5 + random(-10, 10) * 0.05;  // scale + noise
    pressure  = constrain(pressure, 1.0, 10.0);
  }

  // ── Operating hours ─────────────────────────────────────
  operatingHours += (SEND_INTERVAL / 3600000.0);  // increment by send interval

  // ── Send to Flask server ────────────────────────────────
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000);

    StaticJsonDocument<256> doc;
    doc["machine_id"]      = MACHINE_ID;
    doc["device_id"]       = DEVICE_ID;
    doc["temperature"]     = round(temperature * 10) / 10.0;
    doc["vibration"]       = round(vibration * 100) / 100.0;
    doc["pressure"]        = round(pressure * 10) / 10.0;
    doc["operating_hours"] = round(operatingHours);

    String body;
    serializeJson(doc, body);

    int httpCode = http.POST(body);

    if (httpCode == 200) {
      Serial.printf("✅ Sent → T:%.1f°C V:%.2fmm/s P:%.1fbar H:%.0fh\n",
                    temperature, vibration, pressure, operatingHours);
    } else {
      Serial.printf("❌ HTTP %d — check server URL and WiFi\n", httpCode);
    }
    http.end();
  } else {
    Serial.println("⚠️  WiFi disconnected — reconnecting...");
    WiFi.reconnect();
  }

  delay(SEND_INTERVAL);
}
