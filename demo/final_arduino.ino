#include <EEPROM.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <Keypad.h>
#include <Keypad_I2C.h>
#include <LiquidCrystal_I2C.h>

// ---------- Serial ----------
#define RX_PIN 4 // D4 = RX (รับจาก Odroid TX)
#define TX_PIN 3 // D3 = TX (ส่งไป Odroid RX)
SoftwareSerial odroidSerial(RX_PIN, TX_PIN);

// ---------- RFID ----------
#define RST_PIN 9
#define SS_PIN 10
MFRC522 mfrc522(SS_PIN, RST_PIN);

// ---------- Keypad ----------
#define KEYPAD_ADDR 0x20
const byte ROWS = 4, COLS = 4;
char hexaKeys[ROWS][COLS] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}};
byte rowPins[ROWS] = {0, 1, 2, 3};
byte colPins[COLS] = {4, 5, 6, 7};
Keypad_I2C keypad(makeKeymap(hexaKeys), rowPins, colPins, ROWS, COLS, KEYPAD_ADDR);

// ---------- LCD ----------
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ---------- Buzzer ----------
#define BUZZER_PIN 2

// ---------- Struct EEPROM ----------
struct Product
{
  char barcode[16];
  char name[16];
  int price;
  int qty;
};

// address 0–1 : เก็บ addr ล่าสุด
// address 2–  : เก็บสินค้า
int addr = 2;

// ---------- State ----------
String inputPassword = "";
enum UIDState
{
  UID_STATE_WAIT_CARD,
  UID_STATE_WAIT_PASSWORD
};
bool uidMode = false;
UIDState uidState = UID_STATE_WAIT_CARD;

// ---------- Helper EEPROM ----------
void saveAddr()
{
  EEPROM.put(0, addr); // บันทึก pointer ล่าสุดไว้ที่ addr 0
}

void loadAddr()
{
  EEPROM.get(0, addr);
  if (addr < 2 || addr >= EEPROM.length())
  {
    addr = 2; // ป้องกันค่าเพี้ยน
  }
}

void clearEEPROM()
{
  for (int i = 0; i < EEPROM.length(); i++)
  {
    EEPROM.write(i, 0);
  }
  addr = 2;
  saveAddr();
  Serial.println("🧹 EEPROM cleared");
}

// ---------- Save or Update Product ----------
void saveOrUpdateProduct(String barcode, String product, String price, int qtyVal)
{
  bool found = false;
  int readAddr = 2;

  while (readAddr < addr)
  {
    Product p;
    EEPROM.get(readAddr, p);

    if (String(p.barcode) == barcode)
    {
      if (qtyVal > 0)
      {
        p.qty = qtyVal;
        p.price = price.toInt();
        EEPROM.put(readAddr, p);
        Serial.println("✏️ Update " + String(p.barcode) + " | Qty=" + String(p.qty));
      }
      else
      {
        // ลบสินค้า
        int nextAddr = readAddr + sizeof(Product);
        while (nextAddr < addr)
        {
          Product nextP;
          EEPROM.get(nextAddr, nextP);
          EEPROM.put(nextAddr - sizeof(Product), nextP);
          nextAddr += sizeof(Product);
        }
        addr -= sizeof(Product);
        saveAddr();
        Serial.println("🗑️ Remove " + String(p.barcode));
      }
      found = true;
      break;
    }
    readAddr += sizeof(Product);
  }

  if (!found && qtyVal > 0)
  {
    Product p;
    barcode.toCharArray(p.barcode, sizeof(p.barcode));
    product.toCharArray(p.name, sizeof(p.name));
    p.price = price.toInt();
    p.qty = qtyVal;
    EEPROM.put(addr, p);
    addr += sizeof(Product);
    saveAddr();

    Serial.println("💾 New " + String(p.barcode) + " | Qty=" + String(p.qty));
  }
}

// ---------- Setup ----------
void setup()
{
  Serial.begin(9600);
  odroidSerial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  Wire.begin();
  keypad.begin();
  lcd.init();
  lcd.backlight();

  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  loadAddr(); // โหลด pointer addr จาก EEPROM

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Welcome to Shop");
}

// ---------- Loop ----------
void loop()
{
  // -------- ฟังจาก Odroid --------
  if (odroidSerial.available())
  {
    String msg = odroidSerial.readStringUntil('\n');
    msg.trim();

    if (msg == "DUMP_EEPROM")
    {
      bool hasData = false;
      int readAddr = 2;
      while (readAddr < addr)
      {
        Product p;
        EEPROM.get(readAddr, p);
        if (p.barcode[0] != '\0' && p.qty > 0)
        {
          int totalVal = p.price * p.qty;
          odroidSerial.print("ITEM:");
          odroidSerial.print(p.barcode);
          odroidSerial.print(",");
          odroidSerial.print(p.name);
          odroidSerial.print(",");
          odroidSerial.print(p.price);
          odroidSerial.print(",");
          odroidSerial.print(totalVal);
          odroidSerial.print(",");
          odroidSerial.println(p.qty);
          hasData = true;
        }
        readAddr += sizeof(Product);
      }
      if (!hasData)
      {
        odroidSerial.println("EMPTY");
      }
      odroidSerial.println("END");
    }

    Serial.print("📩 From Python: ");
    Serial.println(msg);

    if (msg.startsWith("ITEM:"))
    {
      String payload = msg.substring(5);
      int c1 = payload.indexOf(',');
      int c2 = payload.indexOf(',', c1 + 1);
      int c3 = payload.indexOf(',', c2 + 1);
      int c4 = payload.indexOf(',', c3 + 1);

      if (c1 > 0 && c2 > 0 && c3 > 0 && c4 > 0)
      {
        String barcode = payload.substring(0, c1);
        String product = payload.substring(c1 + 1, c2);
        String price = payload.substring(c2 + 1, c3);
        String total = payload.substring(c3 + 1, c4);
        String qtyStr = payload.substring(c4 + 1);

        int qtyVal = qtyStr.toInt();

        // แสดงบน LCD
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Total:");
        int colTotal = 16 - total.length();
        lcd.setCursor(colTotal, 0);
        lcd.print(total);

        lcd.setCursor(0, 1);
        lcd.print(product);
        int colPrice = 16 - price.length();
        if (colPrice < product.length() + 1)
          colPrice = product.length() + 1;
        lcd.setCursor(colPrice, 1);
        lcd.print(price);

        // บันทึก EEPROM
        saveOrUpdateProduct(barcode, product, price, qtyVal);
      }
    }

    else if (msg == "MODE:UID")
    {
      uidMode = true;
      uidState = UID_STATE_WAIT_CARD;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Tap your Card");
    }

    else if (msg == "MODE:PRODUCT")
    {
      uidMode = false;
      uidState = UID_STATE_WAIT_CARD;
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Welcome to Shop");
    }

    else if (msg == "PAYMENT SUCCESS")
    {
      for (int i = 0; i < 2; i++)
      {
        tone(BUZZER_PIN, 1200);
        delay(200);
        noTone(BUZZER_PIN);
        delay(150);
      }
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Payment Success!");
      delay(2000);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Welcome to Shop");
      uidMode = false;
      uidState = UID_STATE_WAIT_CARD;
      clearEEPROM();
    }

    else if (msg == "FAIL_UID")
    {
      tone(BUZZER_PIN, 400);
      delay(1000);
      noTone(BUZZER_PIN);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Card not found");
      delay(1500);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Tap your Card");
      uidState = UID_STATE_WAIT_CARD;
    }

    else if (msg == "FAIL_PWD")
    {
      tone(BUZZER_PIN, 400);
      delay(1000);
      noTone(BUZZER_PIN);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Wrong Password");
      delay(1500);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Enter Password:");
      uidState = UID_STATE_WAIT_PASSWORD;
    }
  }

  // -------- โหมด UID --------
  if (uidMode)
  {
    if (uidState == UID_STATE_WAIT_CARD)
    {
      if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
      {
        tone(BUZZER_PIN, 1000);
        delay(500);
        noTone(BUZZER_PIN);
        delay(300);

        odroidSerial.print("UID:");
        for (byte i = 0; i < mfrc522.uid.size; i++)
        {
          if (mfrc522.uid.uidByte[i] < 0x10)
            odroidSerial.print("0");
          odroidSerial.print(mfrc522.uid.uidByte[i], HEX);
        }
        odroidSerial.println();

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Enter Password:");
        uidState = UID_STATE_WAIT_PASSWORD;

        mfrc522.PICC_HaltA();
        mfrc522.PCD_StopCrypto1();
      }
    }
    else if (uidState == UID_STATE_WAIT_PASSWORD)
    {
      char key = keypad.getKey();
      if (key != NO_KEY)
      {
        if (key == '#')
        {
          if (inputPassword.length() > 0)
          {
            odroidSerial.print("PWD:");
            odroidSerial.println(inputPassword);
            inputPassword = "";
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Checking...");
          }
        }
        else if (key == '*')
        {
          inputPassword = "";
          lcd.clear();
          lcd.setCursor(0, 0);
          lcd.print("Password Reset");
        }
        else
        {
          inputPassword += key;
          String masked = "";
          for (unsigned int i = 0; i < inputPassword.length(); i++)
            masked += "*";
          lcd.setCursor(0, 1);
          lcd.print(masked);
        }
      }
    }
  }

  // -------- Serial Monitor (debug) --------
  if (Serial.available())
  {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("DUMP"))
    {
      Serial.println("📜 EEPROM Dump:");
      int readAddr = 2;
      while (readAddr < addr)
      {
        Product p;
        EEPROM.get(readAddr, p);
        if (p.barcode[0] != '\0')
        {
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
    else if (cmd.equalsIgnoreCase("CLEAR"))
    {
      clearEEPROM();
    }
  }
}
