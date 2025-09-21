## คำสั่งเข้า/ออก venv
เข้า venv
```
source venv/bin/activate
```

ออก venv
```
deactivate
```

## คำสั่งรัน file
```
sudo ./venv/bin/python <ชื่อ file>
```

## คำสั่งเข้า ssh ใน odroid
```
ssh -o ExitOnForwardFailure=no -o LogLevel=ERROR -L 8080:127.0.0.1:5000 odroid@<ip odroid>
ssh -o ExitOnForwardFailure=no -o LogLevel=ERROR -L 8080:127.0.0.1:5000 odroid@odroid

```

## คำสั่ง shutdown odroid
```
sudo shutdown -h now
```

## คำสั่ง check port
```
lsof /dev/ttyS1
```