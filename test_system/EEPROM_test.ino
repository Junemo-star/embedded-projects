#include <EEPROM.h>
#include <SoftwareSerial.h>

#define RX_PIN 4   // D4 = RX (รับจาก Odroid TX)
#define TX_PIN 3   // D3 = TX (ส่งไป Odroid RX)

SoftwareSerial odroidSerial(RX_PIN, TX_PIN);

struct Product {
  char barcode[16];   // เก็บบาร์โค้ด
  char name[16];      // ชื่อสินค้า
  int price;          // ราคา
  int qty;            // จำนวน
};

int addr = 0;  // ชี้ตำแหน่งเขียนถัดไป

void setup() {
  Serial.begin(9600);
  odroidSerial.begin(9600);
  Serial.println("✅ Ready: Listening Odroid on D4(RX)/D3(TX)");
}

void loop() {
  // ฟังข้อมูลจาก Odroid
  if (odroidSerial.available()) {
    String line = odroidSerial.readStringUntil('\n');
    line.trim();

    Serial.print("📩 From Python: ");
    Serial.println(line);

    if (line.startsWith("ITEM:")) {
      String payload = line.substring(5); // ตัด "ITEM:"

      int firstComma  = payload.indexOf(',');
      int secondComma = payload.indexOf(',', firstComma + 1);
      int thirdComma  = payload.indexOf(',', secondComma + 1);
      int forthComma  = payload.indexOf(',', thirdComma + 1);

      if (firstComma > 0 && secondComma > 0 && thirdComma > 0 && forthComma > 0) {
        String barcode = payload.substring(0, firstComma);
        String product = payload.substring(firstComma + 1, secondComma);
        String price   = payload.substring(secondComma + 1, thirdComma);
        String total   = payload.substring(thirdComma + 1, forthComma); // เผื่อใช้
        String qtyStr  = payload.substring(forthComma + 1);

        int qtyVal = qtyStr.toInt();
        bool found = false;
        int readAddr = 0;

        // 🔎 เช็คว่าบาร์โค้ดซ้ำมั้ย
        while (readAddr < addr) {
          Product p;
          EEPROM.get(readAddr, p);

          if (String(p.barcode) == barcode) {
            if (qtyVal > 0) {
              // อัปเดต qty ตามที่ส่งมา
              p.qty = qtyVal;
              p.price = price.toInt();
              EEPROM.put(readAddr, p);

              Serial.print("✏️ Update product → ");
              Serial.print(p.barcode);
              Serial.print(" | Name=");
              Serial.print(p.name);
              Serial.print(" | Price=");
              Serial.print(p.price);
              Serial.print(" | Qty=");
              Serial.println(p.qty);
            } else {
              // ถ้า qty = 0 → ลบออก
              Serial.print("🗑️ Remove product → ");
              Serial.println(p.barcode);

              int nextAddr = readAddr + sizeof(Product);
              while (nextAddr < addr) {
                Product nextP;
                EEPROM.get(nextAddr, nextP);
                EEPROM.put(nextAddr - sizeof(Product), nextP);
                nextAddr += sizeof(Product);
              }
              addr -= sizeof(Product);
            }

            found = true;
            break;
          }
          readAddr += sizeof(Product);
        }

        if (!found && qtyVal > 0) {
          // ✅ สินค้าใหม่ → เขียนเพิ่ม (ถ้า qty > 0 เท่านั้น)
          Product p;
          barcode.toCharArray(p.barcode, sizeof(p.barcode));
          product.toCharArray(p.name, sizeof(p.name));
          p.price = price.toInt();
          p.qty   = qtyVal;

          EEPROM.put(addr, p);
          addr += sizeof(Product);

          Serial.print("💾 New product saved → ");
          Serial.print(p.barcode);
          Serial.print(" | Name=");
          Serial.print(p.name);
          Serial.print(" | Price=");
          Serial.print(p.price);
          Serial.print(" | Qty=");
          Serial.println(p.qty);
        }

        odroidSerial.println("OK");
      }
    }
  }

  // ฟังคำสั่งจาก Serial Monitor → dump ข้อมูล
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("DUMP")) {
      Serial.println("📜 EEPROM Dump:");
      int readAddr = 0;
      while (readAddr < addr) {
        Product p;
        EEPROM.get(readAddr, p);
        if (p.barcode[0] != '\0') {
          int totalVal = p.price * p.qty;
          Serial.print("- ");
          Serial.print(p.barcode);
          Serial.print(" | Name=");
          Serial.print(p.name);
          Serial.print(" | Price=");
          Serial.print(p.price);
          Serial.print(" | Qty=");
          Serial.print(p.qty);
          Serial.print(" | Total=");
          Serial.println(totalVal);
        }
        readAddr += sizeof(Product);
      }
      Serial.println("--------------------");
    }
  }
}
