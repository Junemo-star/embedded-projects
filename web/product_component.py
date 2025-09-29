import gspread
from oauth2client.service_account import ServiceAccountCredentials
import config  

# ---------------- Config ----------------
SHEET_ID = config.SHEET_ID
PRODUCT_SHEET = config.PRODUCT_SHEET
SCOPE = config.SCOPE  

# ---------------- Google Auth ----------------
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
client = gspread.authorize(creds)
sheet_product = client.open_by_key(SHEET_ID).worksheet(PRODUCT_SHEET)

# ---------------- Product Functions ----------------
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
            sheet_product.append_row(
                [barcode, name, int(price), int(qty)],
                value_input_option="RAW"
            )
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
