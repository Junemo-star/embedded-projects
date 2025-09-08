import cv2
from pyzbar.pyzbar import decode
import pandas as pd

# === Config Google Sheet ===
SHEET_ID = "15SaQPlVWDZbGQcpk1IvPDMQrq47G59G1ag0NpjE96s8"  # แก้เป็นของคุณ
SHEET_NAME = "Sheet1"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

# โหลดข้อมูลจาก Google Sheet
df = pd.read_csv(URL)

def main():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # อ่านบาร์โค้ด
        barcodes = decode(gray)
        for barcode in barcodes:
            x, y, w, h = barcode.rect
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            barcode_data = barcode.data.decode("utf-8")
            barcode_type = barcode.type
            text = f"{barcode_type}: {barcode_data}"
            cv2.putText(frame, text, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

            print("บาร์โค้ดที่อ่านได้:", barcode_data)

            # filter หาข้อมูลใน Google Sheet
            try:
                barcode_val = int(barcode_data)
            except ValueError:
                barcode_val = barcode_data

            result = df[df["Barcode"] == barcode_val]

            if not result.empty:
                print("ข้อมูลที่เจอใน Google Sheet:")
                print(result)
            else:
                print("ไม่พบข้อมูลใน Google Sheet")

        cv2.imshow("Barcode Scanner", frame)

        if cv2.waitKey(1) & 0xFF == 27:  # ESC เพื่อออก
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
