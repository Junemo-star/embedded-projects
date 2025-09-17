import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg"
PRODUCT_SHEET = "product"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)

def add_or_update_product(barcode, name=None, price=None, qty=None):
    try:
        barcode = str(barcode).strip()
        data = sheet_product.get_all_records()
        for i, row in enumerate(data, start=2):
            if str(row["barcode"]).strip() == barcode:
                if not name:
                    name = row["product name"]
                if price:
                    sheet_product.update_cell(i, 3, int(price))
                if qty:
                    new_qty = int(row["amount"]) + int(qty)
                    sheet_product.update_cell(i, 4, new_qty)
                return True
        if name and price and qty:
            sheet_product.append_row([barcode, name, int(price), int(qty)], value_input_option="RAW")
            return True
        return False
    except Exception as e:
        print("❌ add_or_update_product error:", e)
        return False

def list_products():
    try:
        return sheet_product.get_all_records()
    except Exception as e:
        print("⚠️ โหลดสินค้าไม่สำเร็จ:", e)
        return []
