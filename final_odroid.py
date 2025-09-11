import serial, time, pandas as pd, urllib.parse, gspread, sys, select
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- Config ----------------
ser = serial.Serial("/dev/ttyS1", 9600, timeout=1)
SHEET_ID = "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg"
PRODUCT_SHEET = "product"
USER_SHEET = "user"

scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)
sheet_user = client.open_by_key(SHEET_ID).worksheet(USER_SHEET)

# ---------------- State ----------------
mode = "product"
total_price = 0.0
expected_password = None
current_user_row = None
current_user_credit = 0.0
cart = []   # [{"barcode":..,"name":..,"price":..,"qty":..}]

# ---------------- Func ----------------
def find_barcode_online(barcode):
    try:
        query = f"SELECT * WHERE A = '{barcode}'"
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={PRODUCT_SHEET}&tq={urllib.parse.quote(query)}"
        df = pd.read_csv(url)
        df.dropna(how="all", inplace=True)
        return df
    except:
        return pd.DataFrame()

def get_user_by_uid(uid):
    data = sheet_user.get_all_records()
    for i,row in enumerate(data,start=2):
        if str(row["uid"]).replace(" ","").upper() == uid.replace(" ","").upper():
            return row,i
    return None,None

def update_credit(row,new_credit):
    try:
        sheet_user.update_cell(row,3,new_credit)
        return True
    except:
        return False

def update_product_amount(barcode, qty):
    try:
        data = sheet_product.get_all_records()
        for i,row in enumerate(data,start=2):  # row 1 header
            if str(row["barcode"]).strip() == str(barcode).strip():
                old_amount = int(row["amount"])
                new_amount = max(0, old_amount - qty)
                sheet_product.update_cell(i,4,new_amount)  # amount = column D
                return True
    except Exception as e:
        print("Update amount error:", e)
    return False

def add_to_cart(barcode, name, price):
    global cart
    for item in cart:
        if item["barcode"] == barcode:
            item["qty"] += 1
            return
    cart.append({"barcode": barcode, "name": name, "price": price, "qty": 1})

def reset_to_product(clear_cart=True):
    global total_price, expected_password, current_user_row, current_user_credit, cart, mode
    if clear_cart:
        total_price = 0
        cart.clear()
    expected_password = None
    current_user_row = None
    current_user_credit = 0
    mode = "product"
    ser.write(b"MODE:PRODUCT\n")
    print(">> Back to Product Mode")

def back_to_product_keep_cart():
    global expected_password, current_user_row, current_user_credit, mode
    expected_password = None
    current_user_row = None
    current_user_credit = 0
    mode = "product"
    ser.write(b"MODE:PRODUCT\n")
    ser.write(f"ITEM:{name},{price},{total_price}\n".encode())
    ser.flush()
    print(">> Back to Product Mode (keep cart)")
    print(f"Cart still has {len(cart)} items, Total = {total_price}")

# ---------------- Main ----------------
print("Odroid Ready... Mode Product")
while True:
    try:
        # ------------ PRODUCT MODE ------------
        if mode=="product":
            code=input("Scan Barcode: ").strip()
            if not code: continue
            if code=="0000":
                ser.write(b"MODE:UID\n")
                mode="uid"
                print(">> UID Mode")
                continue

            result=find_barcode_online(code)
            if not result.empty:
                name=str(result.iloc[0]['product name'])
                price=float(result.iloc[0]['price'])
                total_price+=price
                add_to_cart(code, name, price)
                ser.write(f"ITEM:{name},{price},{total_price}\n".encode())
                ser.flush()
                print(f"สินค้า:{name} ราคา:{price} รวม:{total_price}")
                print("Cart:", cart)
            else:
                print("❌ ไม่พบสินค้า")

        # ------------ UID MODE ------------
        elif mode=="uid":
            # ✅ Check command line (input) non-blocking
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                cmd = sys.stdin.readline().strip()
                if cmd == "0000":
                    back_to_product_keep_cart()
                    continue

            # ✅ Check serial from Arduino
            if ser.in_waiting>0:
                line=ser.readline().decode(errors="ignore").strip()

                if line == "0000":  # Arduino ส่ง 0000 มา → กลับ product โดยไม่ล้าง cart
                    back_to_product_keep_cart()
                    continue

                if line.startswith("UID:"):
                    uid=line[4:]
                    user,row=get_user_by_uid(uid)
                    if user:
                        expected_password=str(user["password"])
                        current_user_row=row
                        current_user_credit=float(user["credit"])
                        print("เจอ User:",user)
                    else:
                        print("❌ ไม่เจอ UID")

                elif line.startswith("PWD:"):
                    pwd=line[4:]
                    if expected_password and pwd==expected_password:
                        if current_user_credit>=total_price:
                            new_credit=current_user_credit-total_price
                            if update_credit(current_user_row,new_credit):
                                for item in cart:
                                    update_product_amount(item["barcode"], item["qty"])
                                cart.clear()

                                ser.write(b"PAYMENT SUCCESS\n")
                                print(f"✅ จ่าย {total_price} เหลือ {new_credit}")
                            else:
                                ser.write(b"FAIL\n")
                        else:
                            ser.write(b"FAIL\n")

                        reset_to_product(clear_cart=True)  # ✅ จ่ายเงินหรือ fail → ล้างตะกร้า
                    else:
                        ser.write(b"FAIL\n")
                        print("❌ Password ผิด")

        time.sleep(0.05)
    except KeyboardInterrupt:
        break
