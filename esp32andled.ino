#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "Ajil";
const char* password = "ajil2511";

const int lampuMerah1 = 25;
const int lampuKuning1 = 33;
const int lampuHijau1 = 32;

const int lampuMerah2 = 26;
const int lampuKuning2 = 27;
const int lampuHijau2 = 14;

const int DURASI_HIJAU = 10000;
const int DURASI_KUNING = 2000;
const int DURASI_MERAH = 10000;
const int MASA_BERLAKU_PERMINTAAN = 5000;

enum State {
  STATE_MERAH,
  STATE_KUNING_MENUJU_HIJAU,
  STATE_HIJAU
};
State currentState = STATE_MERAH;
unsigned long stateChangeMillis = 0;

volatile unsigned long waktuPermintaanBelok = 0;

WebServer server(80);

void handleTriggerBelok() {
  waktuPermintaanBelok = millis();
  Serial.println("-> Permintaan belok diterima!");
  server.send(200, "text/plain", "OK, Permintaan Belok Dicatat");
}

void setup() {
  pinMode(lampuMerah1, OUTPUT);
  pinMode(lampuKuning1, OUTPUT);
  pinMode(lampuHijau1, OUTPUT);
  pinMode(lampuMerah2, OUTPUT);
  pinMode(lampuKuning2, OUTPUT);
  pinMode(lampuHijau2, OUTPUT);
  Serial.begin(115200);

  digitalWrite(lampuHijau1, LOW);
  digitalWrite(lampuKuning1, LOW);
  digitalWrite(lampuMerah1, HIGH);
  digitalWrite(lampuHijau2, LOW);
  digitalWrite(lampuKuning2, LOW);
  digitalWrite(lampuMerah2, HIGH);
  stateChangeMillis = millis();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nTerhubung ke WiFi!");
  Serial.print("Alamat IP ESP32: ");
  Serial.println(WiFi.localIP());

  server.on("/triggerBelok", HTTP_GET, handleTriggerBelok);
  server.begin();
}

void loop() {
  server.handleClient();
  unsigned long currentMillis = millis();

  bool permintaanValid = (waktuPermintaanBelok > 0 && (currentMillis - waktuPermintaanBelok < MASA_BERLAKU_PERMINTAAN));

  switch (currentState) {
    case STATE_MERAH:
      digitalWrite(lampuHijau1, LOW);
      digitalWrite(lampuKuning1, LOW);
      digitalWrite(lampuMerah1, HIGH);
      digitalWrite(lampuHijau2, LOW);
      digitalWrite(lampuKuning2, LOW);
      digitalWrite(lampuMerah2, HIGH);

      if (currentMillis - stateChangeMillis >= DURASI_MERAH) {
        currentState = STATE_KUNING_MENUJU_HIJAU;
        stateChangeMillis = currentMillis;
      }
      break;

    case STATE_KUNING_MENUJU_HIJAU:
      digitalWrite(lampuMerah2, LOW);
      digitalWrite(lampuKuning2, HIGH);

      if (permintaanValid) {
        digitalWrite(lampuMerah1, LOW);
        digitalWrite(lampuKuning1, HIGH);
      }

      if (currentMillis - stateChangeMillis >= DURASI_KUNING) {
        currentState = STATE_HIJAU;
        stateChangeMillis = currentMillis;
      }
      break;

    case STATE_HIJAU:
      digitalWrite(lampuKuning2, LOW);
      digitalWrite(lampuHijau2, HIGH);
      digitalWrite(lampuKuning1, LOW);

      if (permintaanValid) {
        digitalWrite(lampuMerah1, LOW);
        digitalWrite(lampuHijau1, HIGH);
      } else {
        digitalWrite(lampuHijau1, LOW);
        digitalWrite(lampuMerah1, HIGH);
      }

      if (currentMillis - stateChangeMillis >= DURASI_HIJAU) {
        currentState = STATE_MERAH;
        stateChangeMillis = currentMillis;
        waktuPermintaanBelok = 0;
        Serial.println("Siklus hijau selesai. Kembali ke merah.");
      }
      break;
  }
}