import pandas as pd

# === Config Google Sheet ===
SHEET_ID = "15SaQPlVWDZbGQcpk1IvPDMQrq47G59G1ag0NpjE96s8"  # แก้เป็นของคุณ
SHEET_NAME = "Sheet1"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# โหลดข้อมูลจาก Google Sheet
df = pd.read_csv(URL)

def main():
    print("พร้อมสแกนบาร์โค้ดด้วยเครื่องอ่าน (กด Ctrl+C เพื่อออก)")
    while True:
        try:
            barcode_data = input("Scan Barcode: ").strip()
            if not barcode_data:
                continue

            print("บาร์โค้ดที่อ่านได้:", barcode_data)

            # แปลงเป็น int ถ้าเป็นตัวเลข
            try:
                barcode_val = int(barcode_data)
            except ValueError:
                barcode_val = barcode_data

            # filter หาข้อมูลใน Google Sheet
            result = df[df["Barcode"] == barcode_val]

            if not result.empty:
                print("ข้อมูลที่เจอใน Google Sheet:")
                print(result)
            else:
                print("ไม่พบข้อมูลใน Google Sheet")

        except KeyboardInterrupt:
            print("\nออกจากโปรแกรมแล้ว")
            break

if __name__ == "__main__":
    main()
