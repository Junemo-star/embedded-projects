#!/bin/bash
echo "=== Setup Script for Odroid C4 ==="

# อัปเดตระบบ
sudo apt update && sudo apt upgrade -y

# ติดตั้ง Python และ pip
sudo apt install -y python3 python3-pip python3-venv git

# สร้าง virtual environment
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# เข้า venv
source venv/bin/activate

# อัปเกรด pip
pip install --upgrade pip

# ติดตั้งไลบรารีที่ต้องใช้
pip install pandas gspread oauth2client opencv-python pyzbar

# สร้างไฟล์ .gitignore กัน credentials.json รั่ว
if [ ! -f ".gitignore" ]; then
  echo "venv/" >> .gitignore
  echo "credentials.json" >> .gitignore
  echo "__pycache__/" >> .gitignore
fi

echo "✅ Setup เสร็จสิ้น!"
echo "👉 อย่าลืมวางไฟล์ credentials.json ในโฟลเดอร์โปรเจกต์"
