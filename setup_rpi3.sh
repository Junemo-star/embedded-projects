#!/usr/bin/env bash
set -euo pipefail

# ===== Options =====
HEADLESS=0          # ใช้ opencv-python-headless ถ้า =1
WITH_PICAMERA2=0    # ติดตั้ง python3-picamera2 และ libcamera ถ้า =1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headless) HEADLESS=1; shift ;;
    --with-picamera2) WITH_PICAMERA2=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--headless] [--with-picamera2]"
      echo "  --headless        Install opencv-python-headless (no GUI libs)"
      echo "  --with-picamera2  Install python3-picamera2 and libcamera (Pi Camera Module)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

echo "=== Raspberry Pi 3 setup: venv + OpenCV + pyzbar ==="
echo "Options: HEADLESS=$HEADLESS, WITH_PICAMERA2=$WITH_PICAMERA2"
echo

# ===== 1) System deps =====
echo "==> apt update & install base deps"
sudo apt update
sudo apt install -y \
  python3-venv python3-pip \
  libzbar0 \
  v4l-utils \
  pkg-config

# กล้อง Pi (CSI) — ติดตั้งเครื่องมือ libcamera และไลบรารี picamera2 (optional)
if [[ "$WITH_PICAMERA2" -eq 1 ]]; then
  echo "==> Installing Pi Camera (libcamera & picamera2) packages"
  # บน Raspberry Pi OS Bullseye/Bookworm ควรมีแพ็กเกจเหล่านี้
  sudo apt install -y libcamera-apps python3-picamera2
  echo "   (ถ้าใช้ Pi Camera Module อย่าลืมเปิดใช้งานกล้องใน raspi-config และรีบูต)"
fi

# ===== 2) Python venv =====
if [[ ! -d venv ]]; then
  echo "==> Creating Python virtual environment: ./venv"
  python3 -m venv venv
else
  echo "==> Using existing ./venv"
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# ===== 3) Python pkgs =====
echo "==> Installing Python packages"
if [[ "$HEADLESS" -eq 1 ]]; then
  pip install opencv-python-headless pyzbar
else
  pip install opencv-python pyzbar
fi

# (optional) ถ้าต้องใช้ picamera2 ผ่านโค้ด Python ใน venv (มัก import จากแพ็กเกจระบบได้อยู่แล้ว)
# pip install picamera2  # ปกติไม่จำเป็น เพราะใช้ python3-picamera2 จาก apt

# ===== 4) Quick import test =====
echo "==> Verifying imports (cv2, pyzbar)"
python - <<'PY'
import sys
import cv2
from pyzbar.pyzbar import decode, ZBarSymbol
print("✅ OpenCV:", cv2.__version__)
print("✅ pyzbar import OK; symbols:", [s.name for s in ZBarSymbol])
PY

# ===== 5) Camera quick check =====
echo "==> Quick camera check (USB UVC expected as /dev/video0)"
if v4l2-ctl --list-devices >/dev/null 2>&1; then
  v4l2-ctl --list-devices || true
else
  echo "  (v4l2-ctl not available?)"
fi

echo
echo "=== DONE ==="
echo "Activate venv:  source venv/bin/activate"
echo "Run your script: python your_script.py"
if [[ "$WITH_PICAMERA2" -eq 1 ]]; then
  echo "Note: For Pi Camera Module, enable camera: sudo raspi-config -> Interface Options -> Camera (or legacy), then reboot."
fi
