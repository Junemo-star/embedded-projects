#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10   // SDA
#define RST_PIN 9   // RST
MFRC522 mfrc522(SS_PIN, RST_PIN);

bool rfid_ok = false;  // สถานะการเชื่อมต่อ RFID

void setup() {
  Serial.begin(9600);
  SPI.begin();
}

void loop() {
  // ------------------ เช็คการเชื่อมต่อ RC522 ------------------
  if (!rfid_ok) {
    mfrc522.PCD_Init(); // เริ่มต้น RC522
    byte version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
    if (version == 0x00 || version == 0xFF) {
      Serial.println("❌ RFID ไม่พบ! ตรวจสอบการต่อสาย...");
      delay(1000); // รอ 1 วิ ก่อนเช็คใหม่
      return;      // ยังไม่สามารถอ่าน RFID
    } else {
      Serial.print("✅ RFID detected, version: 0x");
      Serial.println(version, HEX);
      Serial.println("📡 สแกนบัตร RFID/Tag...");
      rfid_ok = true; // เชื่อมต่อสำเร็จ
    }
  }

  // ------------------ อ่าน UID ของบัตร ------------------
  byte version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
  if (version == 0x00 || version == 0xFF) rfid_ok = false;
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  Serial.print("UID: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println();

  mfrc522.PICC_HaltA(); // หยุดการอ่านบัตร
}
