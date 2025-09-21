from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
import serial, pandas as pd, urllib.parse, gspread, os, base64, threading, time, signal, sys
from datetime import datetime
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from product_component import add_or_update_product, list_products

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

# ---------------- Google Auth ----------------
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

client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)
sheet_user = client.open_by_key(SHEET_ID).worksheet(USER_SHEET)
sheet_history = client.open_by_key(SHEET_ID).worksheet(HISTORY_SHEET)

# ---------------- State ----------------
cart = []
total_price = 0.0
current_uid = None
current_user = None
mode = "product"

# ---------------- Flask ----------------
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")  # ✅ ใช้ threading mode

# ---------------- Gmail Func ----------------
def send_email(to, subject, body):
    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
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
    for i, row in enumerate(data, start=2):
        if str(row["uid"]).replace(" ", "").upper() == uid.replace(" ", "").upper():
            row["row"] = i
            return row, i
    return None, None

def update_credit(row, new_credit):
    sheet_user.update_cell(row, 3, new_credit)

def update_product_amount(barcode, qty):
    try:
        data = sheet_product.get_all_records()
        for i, row in enumerate(data, start=2):
            if str(row["barcode"]).strip() == str(barcode).strip():
                old_amount = int(row["amount"])
                new_amount = max(0, old_amount - qty)
                sheet_product.update_cell(i, 4, new_amount)
                return True
    except Exception as e:
        print("Update amount error:", e)
    return False

def save_history(user_uid, user_name, total_price, cart):
    """บันทึกประวัติการขาย (เก็บทั้ง UID และชื่อลูกค้า)"""
    order_list = "; ".join([f"{i['name']}x{i['qty']}" for i in cart])
    total_qty = sum([i['qty'] for i in cart])
    sheet_history.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        order_list,
        user_uid,
        user_name,
        total_price,
        total_qty
    ])

def list_sales():
    """ดึงประวัติการขายจาก Google Sheet"""
    try:
        data = sheet_history.get_all_records()
        sales = []
        for row in data:
            sales.append({
                "time": row.get("time"),
                "order": row.get("order"),
                "uid": row.get("uid"),
                "customer": row.get("customer_name"),
                "price": row.get("price"),
                "total_amount": row.get("total_qty")
            })
        return sales
    except Exception as e:
        print("⚠️ โหลดประวัติการขายไม่สำเร็จ:", e)
        return []

# ---------------- Cart Func ----------------
def add_to_cart(barcode, name, price):
    global cart
    for item in cart:
        if item["barcode"] == barcode:
            item["qty"] += 1
            return
    cart.append({"barcode": barcode, "name": name, "price": price, "qty": 1})

def update_cart_qty(barcode, action):
    global cart, total_price
    for item in cart:
        if item["barcode"] == barcode:
            if action == "add":
                item["qty"] += 1
                total_price += item["price"]
            elif action == "remove":
                item["qty"] -= 1
                total_price -= item["price"]
                if item["qty"] <= 0:
                    cart = [i for i in cart if i["barcode"] != barcode]
            break

# ---------------- Arduino Update ----------------
def send_cart_update():
    if cart:
        last_item = cart[-1]
        ser.write(b"MODE:PRODUCT\n")
        ser.write(f"ITEM:{last_item['name']},{last_item['price']},{total_price}\n".encode())
    else:
        ser.write(b"MODE:PRODUCT\n")
    ser.flush()

# ---------------- Mode Control ----------------
def reset_to_product(clear_cart=True):
    global cart, total_price, current_uid, current_user, mode
    if clear_cart:
        cart.clear()
        total_price = 0
    current_uid = None
    current_user = None
    mode = "product"
    send_cart_update()

@app.route("/mode/<target>", methods=["POST"])
def switch_mode(target):
    global mode, current_uid, current_user
    if target == "product":
        reset_to_product(clear_cart=False)
    elif target == "uid":
        if len(cart) > 0:
            mode = "uid"
            ser.write(b"MODE:UID\n")
            ser.flush()
    elif target == "cancel":
        current_uid = None
        current_user = None
        reset_to_product(clear_cart=False)
    return redirect(url_for("index"))

# ---------------- Serial Reader ----------------
def read_serial_loop():
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("UID:"):
                    uid = line[4:]
                    user, _ = get_user_by_uid(uid)
                    if user:
                        socketio.emit("uid_detected", {"uid": uid, "name": user["name"]})
                    else:
                        socketio.emit("uid_detected", {"uid": uid, "name": None})
                elif line.startswith("PWD:"):
                    pwd = line[4:]
                    socketio.emit("pwd_detected", {"password": pwd})
        except serial.SerialException as e:
            print("⚠️ Serial error:", e)
            time.sleep(1)
        except Exception as e:
            print("⚠️ Unexpected error:", e)
            time.sleep(1)

threading.Thread(target=read_serial_loop, daemon=True).start()

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template("index.html", cart=cart, total=total_price, user=current_user, mode=mode,
                           now=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/scan", methods=["POST"])
def scan():
    global total_price, mode
    if mode != "product":
        return redirect(url_for("index"))
    code = request.form["barcode"]
    result = find_barcode_online(code)
    if not result.empty:
        name = str(result.iloc[0]["product name"])
        price = float(result.iloc[0]["price"])
        add_to_cart(code, name, price)
        total_price += price
        send_cart_update()
    return redirect(url_for("index"))

@app.route("/cart/update/<barcode>/<action>", methods=["POST"])
def update_cart_route(barcode, action):
    update_cart_qty(barcode, action)
    send_cart_update()
    return redirect(url_for("index"))

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        barcode = request.form.get("barcode")
        name = request.form.get("name")
        price = request.form.get("price")
        qty = request.form.get("qty")
        add_or_update_product(barcode, name, price, qty)
        return redirect(url_for("add_product"))
    return render_template("add_product.html", products=list_products(),
                           user=current_user, now=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/sales")
def sales_page():
    sales = list_sales()
    date_filter = request.args.get("date")
    keyword = request.args.get("keyword", "").strip()
    customer = request.args.get("customer", "").strip()

    if date_filter:
        sales = [s for s in sales if s["time"] and s["time"].startswith(date_filter)]
    if keyword:
        sales = [s for s in sales if keyword.lower() in str(s["order"]).lower()]
    if customer:
        sales = [s for s in sales if customer.lower() in str(s["uid"]).lower()
                                   or customer.lower() in str(s["customer"]).lower()]

    return render_template("sales.html", sales=sales, user=current_user,
                           now=datetime.now().strftime("%Y-%m-%d %H:%M"))

# ---------------- Auth / Payment ----------------
@socketio.on("auth_user")
def auth_user(data):
    global current_uid, current_user, cart, total_price, mode
    uid = data.get("uid")
    pwd = data.get("password")

    user, row = get_user_by_uid(uid)
    if not user:
        emit("auth_result", {"success": False, "msg": "❌ ไม่พบผู้ใช้ กรุณาสแกนใหม่"})
        switch_mode("cancel")
        return

    if str(user["password"]) != str(pwd):
        emit("auth_result", {"success": False, "msg": "❌ รหัสผิด กรุณาลองใหม่"})
        ser.write(b"FAIL_PWD\n"); ser.flush()
        mode = "uid"
        return

    if float(user["credit"]) < total_price:
        emit("auth_result", {"success": False, "msg": "❌ เครดิตไม่พอ กรุณาใช้บัตรอื่น"})
        switch_mode("cancel")
        return

    # ✅ กำหนดค่า
    current_uid = uid
    current_user = user
    new_credit = float(current_user["credit"]) - total_price

    # ✅ เตรียมข้อมูลใบเสร็จ
    order_list = "\n".join([f"- {i['name']} x{i['qty']} = {i['price']*i['qty']}" for i in cart])
    receipt = f"""
    🧾 Receipt
    --------------------------
    UID: {current_uid}
    Name: {current_user['name']}
    Items:
    {order_list}

    Total: {total_price}
    Remaining Credit: {new_credit}
    --------------------------
    Thank you for shopping!
    """

    # ✅ ทำ snapshot ก่อน reset (กัน current_user/cart หาย)
    user_snapshot = user.copy()
    cart_snapshot = cart.copy()
    total_price_snapshot = total_price

    # ✅ ตอบกลับลูกค้าทันที
    emit("auth_result", {"success": True, "msg": f"✅ จ่ายเรียบร้อย (คุณ {user['name']})"})
    ser.write(b"PAYMENT SUCCESS\n"); ser.flush()
    reset_to_product(clear_cart=True)

    # ✅ ทำงานช้าใน background
    def finalize_payment(cart_snapshot, user_snapshot, new_credit_value, receipt_text, total_price_snapshot):
        try:
            update_credit(user_snapshot["row"], new_credit_value)
            for item in cart_snapshot:
                update_product_amount(item["barcode"], item["qty"])
            save_history(user_snapshot["uid"], user_snapshot["name"], total_price_snapshot, cart_snapshot)
            send_email(user_snapshot["email"], "Receipt - POS System", receipt_text)
        except Exception as e:
            print("⚠️ Error in finalize_payment:", e)

    threading.Thread(
        target=finalize_payment,
        args=(cart_snapshot, user_snapshot, new_credit, receipt, total_price_snapshot)
    ).start()


# ---------------- Graceful Shutdown ----------------
def shutdown_handler(sig, frame):
    print("\n🛑 Shutting down server...")
    try:
        if ser and ser.is_open:
            ser.close()
            print("🔌 Serial port closed")
    except Exception as e:
        print("⚠️ Error closing serial:", e)
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, shutdown_handler)  # kill

# ---------------- Main ----------------
if __name__ == "__main__":
    print("🚀 Starting Flask-SocketIO server on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000)
