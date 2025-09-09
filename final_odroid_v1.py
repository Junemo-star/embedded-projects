import serial
import pandas as pd
import urllib.parse
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------- Config -----------------
SERIAL_PORT = "/dev/ttyS1"   # หรือ "/dev/ttyUSB0"
BAUDRATE = 9600
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)

SHEET_ID = "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg"
PRODUCT_SHEET = "product"
USER_SHEET = "user"

# Google Sheets API setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)
sheet_user = client.open_by_key(SHEET_ID).worksheet(USER_SHEET)

# ----------------- Global State -----------------
mode = "product"
total_price = 0.0
expected_password = None
current_user_row = None
current_user_credit = 0.0


# ----------------- Functions -----------------
def find_barcode_online(barcode_data):
    """ค้นหาสินค้าจาก Google Sheet (product)"""
    try:
        query = f"SELECT * WHERE A = '{barcode_data}'"
        encoded_query = urllib.parse.quote(query)
        url = (
            f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
            f"?tqx=out:csv&sheet={PRODUCT_SHEET}&tq={encoded_query}"
        )
        df = pd.read_csv(url)
        df.dropna(how="all", inplace=True)
        return df
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อสินค้า: {e}")
        return pd.DataFrame()


def get_user_by_uid(uid_str):
    """หาผู้ใช้จาก UID ในชีท user"""
    try:
        data = sheet_user.get_all_records()
        for i, row in enumerate(data, start=2):  # row 1 เป็น header
            if str(row["uid"]).replace(" ", "").upper() == uid_str.replace(" ", "").upper():
                return row, i
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ UID: {e}")
    return None, None


def update_credit(row_index, new_credit):
    """อัปเดตเครดิตในชีท user"""
    try:
        sheet_user.update_cell(row_index, 3, new_credit)  # สมมติว่า credit อยู่คอลัมน์ C
        return True
    except Exception as e:
        print(f"อัปเดตเครดิตไม่สำเร็จ: {e}")
        return False


# ----------------- Main Loop -----------------
print("Odroid Ready... โหมดสินค้า")

while True:
    try:
        if mode == "product":
            barcode_data = input("Scan Barcode: ").strip()
            if not barcode_data:
                continue

            if barcode_data == "0000":
                print("=== เปลี่ยนโหมดเป็น UID จาก Arduino ===")
                mode = "uid"
                continue

            result = find_barcode_online(barcode_data)
            if not result.empty:
                try:
                    price = float(result.iloc[0]['price'])
                    total_price += price
                    print(f"สินค้า: {result.iloc[0].to_dict()}")
                    print(f"ราคา: {price} | ยอดรวม: {total_price}")
                except Exception:
                    print("❌ ไม่พบคอลัมน์ราคาใน Google Sheet")
            else:
                print("❌ ไม่พบข้อมูลสินค้า")

        elif mode == "uid":
            if ser.in_waiting > 0:
                line = ser.readline().decode(errors="ignore").strip()

                if line.startswith("UID:"):
                    uid = line[4:]
                    print("Arduino ส่ง UID:", uid)
                    user_row, row_index = get_user_by_uid(uid)
                    if user_row:
                        expected_password = str(user_row["password"])
                        current_user_row = row_index
                        current_user_credit = float(user_row["credit"])
                        print("เจอ User:", user_row)
                    else:
                        print("❌ ไม่เจอ UID ใน Sheet")

                elif line.startswith("PWD:"):
                    pwd = line[4:]
                    print("Arduino ส่ง Password:", pwd)

                    if expected_password and pwd == expected_password:
                        if current_user_credit >= total_price:
                            new_credit = current_user_credit - total_price
                            if update_credit(current_user_row, new_credit):
                                ser.write(b"PAYMENT SUCCESS\n")
                                print(f"✅ หักเงิน {total_price} บาท | เครดิตคงเหลือ: {new_credit}")
                            else:
                                ser.write(b"FAIL\n")
                                print("❌ ไม่สามารถอัปเดตเครดิตได้")
                        else:
                            ser.write(b"FAIL\n")
                            print("❌ เครดิตไม่พอ")

                        # reset กลับไปโหมดสินค้า
                        total_price = 0.0
                        mode = "product"
                        expected_password = None
                        current_user_row = None
                        current_user_credit = 0.0
                        print("=== กลับไปโหมดสินค้า ===")

                    else:
                        ser.write(b"FAIL\n")
                        print("❌ Login ล้มเหลว")

        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nออกจากโปรแกรมแล้ว")
        break
