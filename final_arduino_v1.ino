#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Keypad.h>
#include <Keypad_I2C.h>

#define RST_PIN 9
#define SS_PIN 10
#define KEYPAD_ADDR 0x20

MFRC522 mfrc522(SS_PIN, RST_PIN);

// Keypad config
const byte ROWS = 4;
const byte COLS = 4;
char hexaKeys[ROWS][COLS] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' }
};
byte rowPins[ROWS] = { 0, 1, 2, 3 };
byte colPins[COLS] = { 4, 5, 6, 7 };
Keypad_I2C keypad(makeKeymap(hexaKeys), rowPins, colPins, ROWS, COLS, KEYPAD_ADDR);

String inputPassword = "";

// สถานะการทำงาน
enum State {
  STATE_IDLE,          // รอการ์ด RFID
  STATE_WAIT_PASSWORD  // รอใส่รหัสผ่าน
};

State currentState = STATE_IDLE;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();

  Wire.begin();
  keypad.begin();

  Serial.println("Arduino Ready...");
}

void loop() {
  // ===============================
  // STATE_IDLE → รอสแกนการ์ด RFID
  // ===============================
  if (currentState == STATE_IDLE) {
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
      Serial.print("UID:");
      for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) Serial.print("0");
        Serial.print(mfrc522.uid.uidByte[i], HEX);
      }
      Serial.println();

      currentState = STATE_WAIT_PASSWORD;  // เปลี่ยนไปโหมดรอกรอกรหัส
      inputPassword = "";
      delay(500);
    }
  }

  // ==================================
  // STATE_WAIT_PASSWORD → รอใส่รหัสจาก Keypad
  // ==================================
  else if (currentState == STATE_WAIT_PASSWORD) {
    char key = keypad.getKey();
    if (key != NO_KEY) {
      if (key == '#') {
        if (inputPassword.length() > 0) {
          Serial.print("PWD:");
          Serial.println(inputPassword);
          Serial.flush();
          inputPassword = "";

          // ส่งเสร็จแล้ว กลับไปโหมดรอ RFID ใหม่
          currentState = STATE_IDLE;
        } else {
          Serial.println("PWD:EMPTY");  // debug
        }
      } 
      else if (key == '*') {
        inputPassword = "";       // reset
        Serial.println("RESET");  // debug
      } 
      else {
        inputPassword += key;
        Serial.print("*");  // debug print
      }
    }
  }

  // ===============================
  // ฟังผลลัพธ์จาก Odroid
  // ===============================
  if (Serial.available()) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg == "SUCCESS") {
      Serial.println(">>> Login สำเร็จ ✅");
    } else if (msg == "FAIL") {
      Serial.println(">>> Login ล้มเหลว ❌");
    }
  }
}
