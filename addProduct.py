import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Config Google Sheet ===
SHEET_ID = "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg"
SHEET_NAME = "product"  # ชื่อชีท
# คอลัมน์: A=barcode, B=product name, C=price, D=amount

# === Setup Google Sheets API ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def add_new_product(barcode, name, price, qty):
    """เพิ่มสินค้าใหม่ลง Google Sheet"""
    try:
        # เก็บ barcode เป็น string, ส่วน price/qty เป็น int
        barcode = str(barcode)
        price = int(price)
        qty = int(qty)

        sheet.append_row([barcode, name, price, qty], value_input_option="RAW")
        print(f"✅ เพิ่มสินค้า: {barcode} | {name} | {price} | {qty}")
    except ValueError:
        print("❌ Barcode/ราคา/จำนวน ต้องเป็นตัวเลขเท่านั้น")
    except Exception as e:
        print(f"❌ เพิ่มสินค้าไม่สำเร็จ: {e}")


def main():
    print("=== ระบบเพิ่มสินค้าเข้า Google Sheet ===")
    print("กด Ctrl+C เพื่อออก")

    while True:
        try:
            barcode = input("Scan Barcode (ตัวเลข): ").strip()
            if not barcode:
                continue

            name = input("ชื่อสินค้า: ").strip()
            price = input("ราคา (ตัวเลข): ").strip()
            qty = input("จำนวน (ตัวเลข): ").strip()

            add_new_product(barcode, name, price, qty)
            print("-" * 40)

        except KeyboardInterrupt:
            print("\nออกจากโปรแกรมแล้ว")
            break


if __name__ == "__main__":
    main()
