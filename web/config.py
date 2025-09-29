# config.py
import os

# ---------------- Serial ----------------
SERIAL_PORT = os.getenv("POS_SERIAL_PORT", "/dev/ttyS1")
SERIAL_BAUDRATE = int(os.getenv("POS_SERIAL_BAUDRATE", "9600"))

# ---------------- Google Sheets ----------------
SHEET_ID = os.getenv("POS_SHEET_ID", "1hG39pDzG4SwE7bt25cvD9KzF4K9K4pYq302sGu5eWOg")
PRODUCT_SHEET = "product"
USER_SHEET = "user"
HISTORY_SHEET = "history"

# ---------------- Google API ----------------
SCOPES = [  # สำหรับ app.py
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]


SCOPE = [   # สำหรับ product_component.py
    "https://spreadsheets.google.com/feeds", 
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_FILE = os.getenv("POS_CREDENTIALS", "credentials.json")
TOKEN_FILE = os.getenv("POS_TOKEN", "token.json")

# ---------------- Flask ----------------
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
