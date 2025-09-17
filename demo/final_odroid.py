import serial, time, pandas as pd, urllib.parse, gspread, sys, select, os, base64
from datetime import datetime
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# ---------------- Config ----------------
ser = serial.Serial("/dev/ttyS1", 9600, timeout=1)
SHEET_ID = "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg"
PRODUCT_SHEET = "product"
USER_SHEET = "user"
HISTORY_SHEET = "history"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send"
]

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())

# Google Sheets
client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)
sheet_user = client.open_by_key(SHEET_ID).worksheet(USER_SHEET)
sheet_history = client.open_by_key(SHEET_ID).worksheet(HISTORY_SHEET)

# ---------------- State ----------------
mode = "product"
total_price = 0.0
expected_password = None
current_user_row = None
current_user_credit = 0.0
cart = []
current_uid = None

# ---------------- Gmail Func ----------------
def send_email(to, subject, body):
    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        send_message = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print("📧 Email sent:", send_message["id"])
        return True
    except Exception as e:
        print("⚠️ Email send error:", e)
        return False

# ---------------- Sheets Func ----------------
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
        for i,row in enumerate(data,start=2):
            if str(row["barcode"]).strip() == str(barcode).strip():
                old_amount = int(row["amount"])
                new_amount = max(0, old_amount - qty)
                sheet_product.update_cell(i,4,new_amount)
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
    global total_price, expected_password, current_user_row, current_user_credit, cart, mode, current_uid
    if clear_cart:
        total_price = 0
        cart.clear()
    expected_password = None
    current_user_row = None
    current_user_credit = 0
    current_uid = None
    mode = "product"
    ser.write(b"MODE:PRODUCT\n")
    ser.flush()
    print(">> Back to Product Mode")

def back_to_product_keep_cart():
    global expected_password, current_user_row, current_user_credit, mode, cart, total_price
    expected_password = None
    current_user_row = None
    current_user_credit = 0
    mode = "product"

    if cart:
        last_item = cart[-1]
        name = last_item["name"]
        price = last_item["price"]
        ser.write(b"MODE:PRODUCT\n")
        ser.write(f"ITEM:{name},{price},{total_price}\n".encode())
    else:
        ser.write(b"MODE:PRODUCT\n")

    ser.flush()
    print(">> Back to Product Mode (keep cart)")
    print(f"Cart still has {len(cart)} items, Total = {total_price}")

def save_history(user_uid, total_price, cart):
    try:
        order_list = "; ".join([f"{item['name']}x{item['qty']}" for item in cart])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet_history.append_row([now, order_list, user_uid, total_price])
        print("📝 History saved:", now, order_list, user_uid, total_price)
    except Exception as e:
        print("⚠️ Save history error:", e)

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
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                cmd = sys.stdin.readline().strip()
                if cmd == "0000":
                    back_to_product_keep_cart()
                    continue

            if ser.in_waiting>0:
                line=ser.readline().decode(errors="ignore").strip()

                if line == "0000":
                    back_to_product_keep_cart()
                    continue

                if line.startswith("UID:"):
                    uid=line[4:]
                    user,row=get_user_by_uid(uid)
                    if user:
                        expected_password=str(user["password"])
                        current_user_row=row
                        current_user_credit=float(user["credit"])
                        current_uid=uid
                        print("เจอ User:",user)
                    else:
                        ser.write(b"FAIL_UID\n")
                        ser.flush()
                        print("❌ ไม่เจอ UID")

                elif line.startswith("PWD:"):
                    pwd=line[4:]
                    if expected_password and pwd==expected_password:
                        if current_user_credit>=total_price:
                            new_credit=current_user_credit-total_price
                            if update_credit(current_user_row,new_credit):
                                for item in cart:
                                    update_product_amount(item["barcode"], item["qty"])
                                save_history(current_uid,total_price,cart)

                                # ✅ ส่ง Gmail ใบเสร็จ
                                order_list = "\n".join([f"- {item['name']} x{item['qty']} = {item['price']*item['qty']}" for item in cart])
                                receipt = f"""
🧾 Receipt
--------------------------
UID: {current_uid}
Name: {user['name']}
Items:
{order_list}

Total: {total_price}
Remaining Credit: {new_credit}
--------------------------
Thank you for shopping!
"""
                                send_email(user["email"], "Receipt - POS System", receipt)

                                cart.clear()
                                ser.write(b"PAYMENT SUCCESS\n")
                                ser.flush()
                                print(f"✅ จ่าย {total_price} เหลือ {new_credit}")
                            else:
                                ser.write(b"FAIL_UID\n")
                                ser.flush()
                        else:
                            ser.write(b"FAIL_UID\n")
                            ser.flush()

                        reset_to_product(clear_cart=True)
                    else:
                        ser.write(b"FAIL_PWD\n")
                        ser.flush()
                        print("❌ Password ผิด")

        time.sleep(0.05)
    except KeyboardInterrupt:
        break
