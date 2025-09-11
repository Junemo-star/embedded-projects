#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Keypad.h>
#include <Keypad_I2C.h>
#include <LiquidCrystal_I2C.h>

#define RX_PIN 4   // D4 = RX (รับจาก Odroid TX)
#define TX_PIN 3   // D3 = TX (ส่งไป Odroid RX)
SoftwareSerial mySerial(RX_PIN, TX_PIN);

#define RST_PIN 9
#define SS_PIN 10
#define KEYPAD_ADDR 0x20
#define BUZZER_PIN 2   // buzzer ต่อที่ D2

MFRC522 mfrc522(SS_PIN, RST_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Keypad
const byte ROWS = 4, COLS = 4;
char hexaKeys[ROWS][COLS] = {
  { '1','2','3','A' },
  { '4','5','6','B' },
  { '7','8','9','C' },
  { '*','0','#','D' }
};
byte rowPins[ROWS] = {0,1,2,3};
byte colPins[COLS] = {4,5,6,7};
Keypad_I2C keypad(makeKeymap(hexaKeys), rowPins, colPins, ROWS, COLS, KEYPAD_ADDR);

String inputPassword = "";

// state ของ UID
enum UIDState {
  UID_STATE_WAIT_CARD,
  UID_STATE_WAIT_PASSWORD
};

bool uidMode = false;
UIDState uidState = UID_STATE_WAIT_CARD;

void setup() {
  Serial.begin(9600);
  mySerial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  Wire.begin();
  keypad.begin();
  lcd.init(); 
  lcd.backlight();

  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  lcd.clear();
  lcd.setCursor(0,0);
  lcd.print("Welcome to Shop");
}

void loop() {
  // -------- ฟังจาก Odroid --------
  if (mySerial.available()) {
    String msg = mySerial.readStringUntil('\n');
    msg.trim();

    if (msg.startsWith("ITEM:")) {
      String payload = msg.substring(5);  
      int firstComma = payload.indexOf(',');
      int secondComma = payload.indexOf(',', firstComma+1);

      String product = payload.substring(0, firstComma);
      String price = payload.substring(firstComma+1, secondComma);
      String total = payload.substring(secondComma+1);

      lcd.clear();
      // แถว 0 → แสดง total
      lcd.setCursor(0,0);
      lcd.print("Total:");
      int colTotal = 16 - total.length();
      lcd.setCursor(colTotal,0);
      lcd.print(total);

      // แถว 1 → แสดงสินค้า + ราคา
      lcd.setCursor(0,1);
      lcd.print(product);
      int colPrice = 16 - price.length();
      if (colPrice < product.length() + 1) colPrice = product.length() + 1;
      lcd.setCursor(colPrice,1);
      lcd.print(price);
    }

    else if (msg == "MODE:UID") {
      uidMode = true;
      uidState = UID_STATE_WAIT_CARD;
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Tap your Card");
    }

    else if (msg == "MODE:PRODUCT") {
      uidMode = false;
      uidState = UID_STATE_WAIT_CARD;
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Welcome to Shop");
    }

    else if (msg == "PAYMENT SUCCESS") {
      // ✅ เสียงติ๊ด 2 ครั้ง
      for (int i=0; i<2; i++) {
        tone(BUZZER_PIN, 1200);
        delay(200);
        noTone(BUZZER_PIN);
        delay(150);
      }

      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Payment Success!");
      delay(2000);
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Welcome to Shop");
      uidMode = false;
      uidState = UID_STATE_WAIT_CARD;
    }

    else if (msg == "FAIL") {
      // ❌ Password ผิด หรือ เครดิตไม่พอ
      tone(BUZZER_PIN, 400);   // เสียงผิดพลาด
      delay(1000);
      noTone(BUZZER_PIN);

      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Wrong Password");
      delay(1500);

      if (uidMode) {
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Enter Password:");
        uidState = UID_STATE_WAIT_PASSWORD;
      } else {
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Tap your Card");
        uidState = UID_STATE_WAIT_CARD;
      }
    }
  }

  // -------- โหมด UID --------
  if (uidMode) {
    if (uidState == UID_STATE_WAIT_CARD) {
      if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        // ✅ เจอการ์ด RFID → เสียงติ๊ด
        tone(BUZZER_PIN, 1000);
        delay(500);
        noTone(BUZZER_PIN);
        delay(300);

        mySerial.print("UID:");
        for (byte i=0; i<mfrc522.uid.size; i++) {
          if (mfrc522.uid.uidByte[i] < 0x10) mySerial.print("0");
          mySerial.print(mfrc522.uid.uidByte[i], HEX);
        }
        mySerial.println();

        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Enter Password:");
        uidState = UID_STATE_WAIT_PASSWORD;
      }
    }
    else if (uidState == UID_STATE_WAIT_PASSWORD) {
      char key = keypad.getKey();
      if (key != NO_KEY) {
        if (key == '#') {
          if (inputPassword.length() > 0) {
            mySerial.print("PWD:");
            mySerial.println(inputPassword);
            inputPassword = "";
            lcd.clear();
            lcd.setCursor(0,0);
            lcd.print("Checking...");
          }
        }
        else if (key == '*') {
          inputPassword = "";
          lcd.clear();
          lcd.setCursor(0,0);
          lcd.print("Password Reset");
        }
        else {
          inputPassword += key;
          String masked = "";
          for (unsigned int i=0; i<inputPassword.length(); i++) masked += "*";
          lcd.setCursor(0,1);
          lcd.print(masked);
        }
      }
    }
  }
}
