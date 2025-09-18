#!/bin/bash
echo "🚀 Setup script for POS System on Odroid"

# อัปเดตระบบ
# sudo apt update && sudo apt upgrade -y

# ติดตั้ง Python3 และ pip (ถ้ายังไม่มี)
sudo apt install -y python3 python3-pip python3-venv git

# สร้าง venv
if [ ! -d "venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv venv
fi

# เข้า venv
source venv/bin/activate

# อัปเดต pip
pip install --upgrade pip

# ติดตั้ง dependencies
echo "📦 Installing Python libraries..."
pip install flask flask-socketio eventlet \
            pandas gspread oauth2client \
            google-api-python-client google-auth google-auth-oauthlib \
            pyserial

echo "✅ Setup completed!"
echo "👉 Run app with: source venv/bin/activate && python3 app.py"
