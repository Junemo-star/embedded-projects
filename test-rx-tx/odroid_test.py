import serial
import time

ser = serial.Serial("/dev/ttyS1", 9600, timeout=1)
print("Odroid Ready...")

counter = 0
while True:
    try:
        # อ่านจาก Arduino
        if ser.in_waiting > 0:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print("รับจาก Arduino:", line)

        # ส่งข้อความไป Arduino
        msg = f"PING {counter}\n"
        ser.write(msg.encode())
        ser.flush()
        print("ส่งไป:", msg.strip())
        counter += 1

        time.sleep(2)

    except KeyboardInterrupt:
        break
