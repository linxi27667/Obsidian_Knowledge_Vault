# Python嵌入式开发

## 核心概念

- **MicroPython** - 微控制器Python
- **CircuitPython** - Adafruit的Python
- **嵌入式脚本** - 快速原型开发
- **C扩展** - 性能关键代码

---

## 一、MicroPython

### 1.1 基础语法

```python
# MicroPython基础
import machine
import time

# GPIO控制
led = machine.Pin(2, machine.Pin.OUT)
button = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)

while True():
    if button.value() == 0:
        led.on()
    else:
        led.off()
    time.sleep_ms(100)

# PWM控制
pwm = machine.PWM(machine.Pin(2), freq=1000, duty=512)  # 50%占空比
pwm.duty(1023)  # 100%
pwm.deinit()
```

---

### 1.2 定时器

```python
# 硬件定时器
timer = machine.Timer(0)
timer.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: print("Tick"))

# 软件定时器
from machine import Timer
tim = Timer(-1)
tim.init(period=2000, mode=Timer.ONE_SHOT, callback=lambda t: print("One shot"))

# 回调函数
def timer_callback(timer):
    led.toggle()

timer.init(period=500, mode=machine.Timer.PERIODIC, callback=timer_callback)
```

---

### 1.3 通信接口

```python
# UART
uart = machine.UART(1, baudrate=115200, tx=17, rx=16)
uart.write("Hello")
data = uart.read(10)

# I2C
i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
devices = i2c.scan()
i2c.writeto(0x76, bytes([0xF4, 0x27]))

# SPI
spi = machine.SPI(1, baudrate=1000000, polarity=0, phase=0,
                   sck=machine.Pin(18), mosi=machine.Pin(23), miso=machine.Pin(19))
cs = machine.Pin(5, machine.Pin.OUT)
cs.value(0)
data = spi.read(3)
cs.value(1)
```

---

## 二、网络编程

### 2.1 WiFi

```python
import network

# WiFi STA模式
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID", "password")

while not wlan.isconnected():
    pass

print("Connected:", wlan.ifconfig())

# WiFi AP模式
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32-AP", password="12345678")
```

---

### 2.2 MQTT

```python
from umqtt.simple import MQTTClient

# MQTT客户端
client = MQTTClient("esp32", "broker.hivemq.com")
client.set_callback(lambda t, m: print(t, m))
client.connect()
client.subscribe(b"sensor/temperature")

while True():
    client.check_msg()
    client.publish(b"sensor/temperature", b"25.5")
    time.sleep(1)
```

---

### 2.3 HTTP

```python
import urequests

# GET请求
response = urequests.get("http://httpbin.org/get")
print(response.json())

# POST请求
data = {"temperature": 25.5, "humidity": 60}
response = urequests.post("http://httpbin.org/post", json=data)
print(response.status_code)
```

---

## 三、传感器驱动

### 3.1 DHT11/DHT22

```python
import dht
import machine

d = dht.DHT22(machine.Pin(4))
d.measure()
print("Temperature:", d.temperature())
print("Humidity:", d.humidity())
```

---

### 3.2 BMP280

```python
from machine import I2C
import bmp280

i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21))
sensor = bmp280.BMP280(i2c)

temp = sensor.temperature
pressure = sensor.pressure
print(f"Temp: {temp}°C, Pressure: {pressure}hPa")
```

---

### 3.3 MPU6050

```python
from mpu6050 import MPU6050

mpu = MPU6050(i2c)
accel = mpu.get_accel()
gyro = mpu.get_gyro()

print(f"Accel: X={accel['x']:.2f}, Y={accel['y']:.2f}, Z={accel['z']:.2f}")
print(f"Gyro: X={gyro['x']:.2f}, Y={gyro['y']:.2f}, Z={gyro['z']:.2f}")
```

---

## 四、显示驱动

### 4.1 SSD1306 OLED

```python
from machine import I2C, Pin
import ssd1306

i2c = I2C(scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

oled.fill(0)
oled.text("Hello", 0, 0)
oled.text("MicroPython", 0, 16)
oled.show()
```

---

### 4.2 ST7789 LCD

```python
from machine import SPI, Pin
import st7789

spi = SPI(1, baudrate=40000000, sck=Pin(18), mosi=Pin(23))
cs = Pin(5, Pin.OUT)
dc = Pin(16, Pin.OUT)
rst = Pin(17, Pin.OUT)

lcd = st7789.ST7789(spi, 240, 240, cs=cs, dc=dc, rst=rst)
lcd.fill(st7789.BLACK)
lcd.text("Hello", 100, 120, st7789.WHITE)
lcd.show()
```

---

## 五、文件系统

### 5.1 SPIFFS

```python
import os

# 列出文件
print(os.listdir("/"))

# 读写文件
with open("/data.txt", "w") as f:
    f.write("Hello World")

with open("/data.txt", "r") as f:
    content = f.read()
    print(content)

# 删除文件
os.remove("/data.txt")
```

---

### 5.2 JSON配置

```python
import json

# 保存配置
config = {
    "wifi_ssid": "MyWiFi",
    "wifi_pass": "password",
    "mqtt_broker": "broker.hivemq.com",
    "mqtt_port": 1883
}

with open("/config.json", "w") as f:
    json.dump(config, f)

# 加载配置
with open("/config.json", "r") as f:
    config = json.load(f)
    print(config["wifi_ssid"])
```

---

## 六、异步编程

### 6.1 uasyncio

```python
import uasyncio as asyncio

async def blink_led():
    led = machine.Pin(2, machine.Pin.OUT)
    while True:
        led.toggle()
        await asyncio.sleep_ms(500)

async def read_sensor():
    while True:
        temp = read_temperature()
        print(f"Temp: {temp}")
        await asyncio.sleep(2)

# 运行异步任务
async def main():
    await asyncio.gather(
        blink_led(),
        read_sensor()
    )

asyncio.run(main())
```

---

## 七、C扩展

### 7.1 用户C模块

```c
// 用户C模块
#include "py/runtime.h"

// Python函数实现
static mp_obj_t my_add(mp_obj_t a, mp_obj_t b) {
    int x = mp_obj_get_int(a);
    int y = mp_obj_get_int(b);
    return mp_obj_new_int(x + y);
}
static MP_DEFINE_CONST_FUN_OBJ_2(my_add_obj, my_add);

// 模块定义
static const mp_rom_map_elem_t my_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_my_module) },
    { MP_ROM_QSTR(MP_QSTR_add), MP_ROM_PTR(&my_add_obj) },
};
static MP_DEFINE_CONST_DICT(my_module_globals, my_module_globals_table);

const mp_obj_module_t my_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&my_module_globals,
};
```

---

## 附录：MicroPython vs CircuitPython

| 特性 | MicroPython | CircuitPython |
|------|-------------|---------------|
| 维护 | 社区 | Adafruit |
| 板卡支持 | 广泛 | Adafruit为主 |
| USB支持 | 有限 | 完善 |
| 库管理 | upip | circup |
| 学习资源 | 丰富 | 丰富 |

---

## 相关链接

- [[ESP-IDF开发详解]] - ESP32开发
- [[STM32基础]] - STM32开发
- [[物联网协议]] - 物联网通信
