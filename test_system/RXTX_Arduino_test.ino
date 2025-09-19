#include <SoftwareSerial.h>

#define RX_PIN 4   // รับจาก Odroid TX
#define TX_PIN 3   // ส่งไป Odroid RX

SoftwareSerial mySerial(RX_PIN, TX_PIN);

int counter = 0;

void setup() {
  Serial.begin(9600);       // Debug ผ่าน USB
  mySerial.begin(9600);     // UART คุยกับ Odroid
  Serial.println("Arduino Ready...");
}

void loop() {
  // อ่านข้อมูลจาก Odroid
  if (mySerial.available()) {
    String line = mySerial.readStringUntil('\n');  // อ่านทีละบรรทัด
    line.trim();
    if (line.length() > 0) {
      Serial.print("รับจาก Odroid: ");
      Serial.println(line);
    }
  }

  // ส่งข้อความไป Odroid
  String msg = "PONG " + String(counter++);
  mySerial.println(msg);
  Serial.print("ส่งไป: ");
  Serial.println(msg);

  delay(2000); // ส่งทุก 2 วินาที
}
