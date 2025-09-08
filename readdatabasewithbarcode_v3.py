import pandas as pd
import urllib.parse  # สำหรับจัดการ URL

# === Config Google Sheet ===
SHEET_ID = "15SaQPlVWDZbGQcpk1IvPDMQrq47G59G1ag0NpjE96s8"  # แก้เป็นของคุณ
SHEET_NAME = "Sheet1"
# คอลัมน์ที่เก็บ Barcode เช่น 'A', 'B', 'C'
BARCODE_COLUMN = "A"


def find_barcode_online(barcode_data):
    """
    ฟังก์ชันสำหรับค้นหา barcode แบบ real-time จาก Google Sheet โดยตรง
    """
    try:
        # สร้าง Query Language เพื่อสั่งให้ Google Sheet ค้นหาข้อมูล
        if barcode_data.isdigit():
            query = f"SELECT * WHERE {BARCODE_COLUMN} = {barcode_data}"
        else:
            query = f"SELECT * WHERE {BARCODE_COLUMN} = '{barcode_data}'"

        # เข้ารหัส Query ให้ใช้ใน URL ได้
        encoded_query = urllib.parse.quote(query)

        # สร้าง URL สำหรับยิง API พร้อม Query
        url = (
            f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
            f"?tqx=out:csv&sheet={SHEET_NAME}&tq={encoded_query}"
        )

        # อ่านข้อมูลจาก URL ที่สร้างขึ้น
        result_df = pd.read_csv(url)

        # ถ้าเจอ NaN ทั้งแถวให้ลบทิ้ง
        result_df.dropna(how="all", inplace=True)

        return result_df

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
        return pd.DataFrame()  # คืน DataFrame ว่างเปล่าถ้ามีปัญหา


def main():
    print("พร้อมสแกนบาร์โค้ดด้วยเครื่องอ่าน (กด Ctrl+C เพื่อออก)")
    print("โหมด: ค้นหาข้อมูลออนไลน์จาก Google Sheet โดยตรง")

    while True:
        try:
            barcode_data = input("Scan Barcode: ").strip()
            if not barcode_data:
                continue

            print("บาร์โค้ดที่อ่านได้:", barcode_data)

            # เรียกฟังก์ชันเพื่อค้นหาข้อมูล
            result = find_barcode_online(barcode_data)

            if not result.empty:
                print("ข้อมูลที่เจอใน Google Sheet:")
                # แสดงผลโดยไม่สนใจ header เดิม
                print(result.to_string(index=False, header=False))
            else:
                print("ไม่พบข้อมูลใน Google Sheet")

            print("-" * 30)

        except KeyboardInterrupt:
            print("\nออกจากโปรแกรมแล้ว")
            break


if __name__ == "__main__":
    main()
