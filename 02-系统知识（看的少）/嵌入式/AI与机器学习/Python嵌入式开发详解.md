---
title: Python嵌入式开发详解
tags:
  - Python
  - 嵌入式
  - MicroPython
  - CircuitPython
  - ESP32
created: 2026-06-21
---

# Python嵌入式开发详解

> Python在嵌入式领域的应用日趋广泛，MicroPython和CircuitPython让开发者用高级语言快速构建物联网原型和产品。本文档系统梳理Python嵌入式开发的核心知识。

---

## 一、MicroPython概述

### 1.1 什么是MicroPython

MicroPython是Python 3的精简实现，专为微控制器和受限环境设计。由Damien George于2013年在Kickstarter众筹项目中创建，目标是在只有256KB Flash和16KB RAM的硬件上运行Python解释器。

**核心特性：**

| 特性 | 说明 |
|------|------|
| Python 3语法 | 支持大部分Python 3.4+语法特性 |
| 内置REPL | 通过串口交互式调试 |
| 硬件API | 直接控制GPIO、I2C、SPI、UART等外设 |
| 文件系统 | 内置小型文件系统，支持SD卡扩展 |
| 事件驱动 | 支持中断和定时器回调 |
| 体积小 | 核心固件约300KB-600KB |

### 1.2 MicroPython vs CPython

| 对比项 | MicroPython | CPython |
|--------|-------------|---------|
| 目标平台 | 微控制器(MCU) | 桌面/服务器 |
| 内存占用 | 16KB-256KB RAM | 数十MB+ |
| 标准库 | 精简子集 | 完整标准库 |
| 浮点运算 | 可选(软浮点) | 硬件浮点 |
| JIT编译 | 不支持 | 不支持(但PyPy支持) |
| C扩展 | 通过C模块 | 通过ctypes/CFFI/C扩展 |
| 执行方式 | 字节码解释器 | 字节码解释器 |
| 多线程 | 不支持(单线程+中断) | 支持(threading) |
| 异步IO | uasyncio(协程) | asyncio |
| 包管理 | upip(受限) | pip |
| 类型系统 | 动态类型 | 动态类型 |

**MicroPython支持的Python特性：**

```python
# 列表推导
squares = [x**2 for x in range(10)]

# 字典操作
config = {"ssid": "MyWiFi", "password": "12345678"}
for key, value in config.items():
    print(f"{key}: {value}")

# 异常处理
try:
    f = open("config.json", "r")
    data = f.read()
except OSError as e:
    print("File not found:", e)
finally:
    f.close()

# 类和继承
class Sensor:
    def __init__(self, name):
        self.name = name

    def read(self):
        raise NotImplementedError

class TemperatureSensor(Sensor):
    def __init__(self, pin):
        super().__init__("Temperature")
        self.pin = pin

    def read(self):
        return 25.0  # placeholder

# 生成器
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b
```

**MicroPython不支持或受限的特性：**

```python
# 以下在MicroPython中不可用或受限
import os
os.fork()              # 不支持多进程

import threading        # 不支持标准threading模块

import numpy            # 不支持第三方C扩展库

from collections import OrderedDict  # 部分版本不支持

# 装饰器部分支持
@staticmethod   # 支持
@classmethod    # 支持
@property       # 支持
```

### 1.3 支持的硬件平台

| 硬件平台 | MCU | RAM | Flash | 特点 |
|----------|-----|-----|-------|------|
| ESP32 | Xtensa双核240MHz | 520KB | 4MB | WiFi+BLE，性价比高 |
| ESP32-S3 | Xtensa双核240MHz | 512KB | 8MB | AI加速，USB OTG |
| ESP32-C3 | RISC-V 160MHz | 400KB | 4MB | 低功耗，BLE5 |
| RP2040 | ARM Cortex-M0+双核133MHz | 264KB | 2MB | PIO状态机，可编程IO |
| STM32系列 | ARM Cortex-M0/M3/M4/M7 | 20KB-1MB | 64KB-2MB | 型号丰富，工业级 |
| Pyboard | STM32F405 | 192KB | 1MB | 官方参考板 |
| nRF52840 | ARM Cortex-M4 64MHz | 256KB | 1MB | BLE5，低功耗 |
| SAMD21/SAMD51 | ARM Cortex-M0+/M4 | 32KB-256KB | 256KB-1MB | Arduino兼容 |
| Teensy 4.0/4.1 | ARM Cortex-M7 600MHz | 1MB/8MB | 2MB/8MB | 高性能 |
| Raspberry Pi Pico | RP2040 | 264KB | 2MB | 官方支持，社区大 |
| Pico W | RP2040+CYW43439 | 264KB | 2MB | 增加WiFi+BLE |

### 1.4 优缺点分析

**优点：**

- **开发效率高**：Python语法简洁，无需编译，修改即运行
- **交互式调试**：REPL实时测试代码片段，快速验证硬件
- **学习门槛低**：Python是最流行的入门语言之一
- **丰富库生态**：社区贡献了大量驱动和库
- **跨平台移植**：同一份代码可在多个支持的MCU上运行
- **快速原型**：从想法到原型的时间远短于C/C++

**缺点：**

- **执行速度慢**：比C/C++慢10-100倍
- **内存占用大**：解释器本身占用大量Flash和RAM
- **实时性差**：垃圾回收导致不可预测的延迟
- **功耗较高**：CPU无法像C那样长时间休眠
- **缺乏类型安全**：运行时才暴露类型错误
- **库生态受限**：无法直接使用CPython的C扩展库
- **不适合安全关键**：不适用于医疗、航空等对确定性要求高的场景

---

## 二、MicroPython基础

### 2.1 REPL交互

REPL(Read-Eval-Print Loop)是MicroPython最强大的调试工具。

**进入REPL的方式：**

```
# 方法1：串口终端（推荐）
# Windows: 使用PuTTY、MobaXterm、Thonny IDE
# macOS/Linux: 使用screen、minicom或picocom
picocom /dev/ttyUSB0 -b 115200

# 方法2：WebREPL（WiFi远程）
# 先在串口REPL中启用WebREPL：
import webrepl
webrepl.start(password="mypassword")
# 然后浏览器访问 http://micropython.org/webrepl
```

**REPL常用快捷键：**

| 快捷键 | 功能 |
|--------|------|
| Ctrl+C | 中断正在运行的程序 |
| Ctrl+D | 软重启(Soft Reset) |
| Ctrl+E | 进入粘贴模式(多行输入) |
| Ctrl+B | 显示版本信息 |
| Tab | 自动补全 |

**REPL使用示例：**

```python
>>> import sys
>>> sys.platform
'esp32'

>>> sys.implementation
(name='micropython', version=(1, 22, 0))

>>> import gc
>>> gc.mem_free()
114864

>>> help('modules')  # 列出所有可用模块

>>> dir()  # 查看当前命名空间
['__name__', 'sys', 'gc']

# 粘贴模式：Ctrl+E进入，粘贴代码，Ctrl+D执行
# 适合测试多行代码块
```

### 2.2 boot.py与main.py

MicroPython启动时按固定顺序执行两个文件：

```
启动流程：
1. 内部初始化
2. 执行 boot.py  -- 系统配置（WiFi、时钟、文件系统等）
3. 执行 main.py  -- 用户应用程序
```

**boot.py 示例：**

```python
# boot.py - 系统启动配置
# 该文件在每次上电或硬重启后执行
import gc
import network
import machine
import json

# 配置时钟频率（降低功耗或提高性能）
# machine.freq(240000000)  # ESP32: 240MHz
# machine.freq(133000000)  # RP2040: 133MHz

# 初始化垃圾回收
gc.collect()

# 加载WiFi配置
def connect_wifi():
    """连接WiFi网络"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except OSError:
        print("[boot] config.json not found, using defaults")
        config = {"ssid": "default", "password": ""}

    sta = network.WLAN(network.STA_IF)
    if not sta.isconnected():
        print("[boot] Connecting to WiFi...")
        sta.active(True)
        sta.connect(config["ssid"], config["password"])
        import time
        timeout = 10
        while not sta.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")

    if sta.isconnected():
        print(f"\n[boot] WiFi connected: {sta.ifconfig()[0]}")
    else:
        print("\n[boot] WiFi connection failed")

    return sta

# 执行WiFi连接
wlan = connect_wifi()

# 打印内存状态
print(f"[boot] Free memory: {gc.mem_free()} bytes")
gc.collect()
```

**main.py 示例：**

```python
# main.py - 主应用程序
import gc
import time
from machine import Pin, Timer

# 初始化LED
led = Pin(2, Pin.OUT)  # ESP32板载LED

# 初始化按钮
button = Pin(0, Pin.IN, Pin.PULL_UP)  # BOOT按钮

# 全局状态
state = {
    "led_toggle": False,
    "button_count": 0,
    "running": True
}

def button_handler(pin):
    """按钮中断回调"""
    state["button_count"] += 1
    state["led_toggle"] = not state["led_toggle"]
    print(f"Button pressed: {state['button_count']}")

def timer_callback(timer):
    """定时器回调 - 心跳LED"""
    led.value(not led.value())

# 配置按钮中断
button.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)

# 配置定时器（每500ms翻转LED）
timer = Timer(0)
timer.init(period=500, mode=Timer.PERIODIC, callback=timer_callback)

print("[main] Application started")
print(f"[main] Free memory: {gc.mem_free()} bytes")

# 主循环
while state["running"]:
    try:
        # 这里可以添加其他任务逻辑
        gc.collect()  # 定期回收内存
        time.sleep(1)
    except KeyboardInterrupt:
        print("[main] Stopped by user")
        state["running"] = False
        timer.deinit()
        break
```

### 2.3 模块导入

MicroPython的模块系统与CPython类似，但有以下特殊之处。

**模块搜索路径：**

```python
import sys
print(sys.path)
# ['']  <- 当前目录（通常是 / 或 /flash）
# 可以手动添加路径：
sys.path.append('/lib')
sys.path.append('/sd/lib')
```

**内置模块（无需安装）：**

| 模块 | 说明 |
|------|------|
| `machine` | 硬件抽象层（Pin、I2C、SPI、UART、Timer等） |
| `network` | 网络接口（WiFi、以太网） |
| `gc` | 垃圾回收控制 |
| `os` | 文件系统操作 |
| `sys` | 系统信息和配置 |
| `time` | 时间相关函数 |
| `json` | JSON编解码 |
| `ustruct` / `struct` | 二进制数据打包/解包 |
| `ubinascii` / `binascii` | 二进制/ASCII转换 |
| `uhashlib` / `hashlib` | 哈希算法 |
| `ussl` / `ssl` | TLS/SSL加密通信 |
| `uasyncio` / `asyncio` | 协程异步IO |
| `micropython` | MicroPython特有功能 |

**安装第三方库（upip）：**

```python
# 通过WebREPL或串口REPL执行
import upip
upip.install("micropython-umqtt.simple")
upip.install("micropython-umqtt.robust")

# 或手动下载 .mpy 文件放入 /lib 目录
# .mpy 是预编译的字节码文件，节省Flash空间
```

**自定义模块示例：**

```python
# 文件：/lib/utils.py
import time
import machine

def millis():
    """返回毫秒级时间戳"""
    return time.ticks_ms()

def uptime():
    """返回系统运行时间（秒）"""
    return time.ticks_ms() // 1000

def reset(reason="manual"):
    """安全重启"""
    print(f"Resetting: {reason}")
    time.sleep(1)
    machine.reset()

def map_value(x, in_min, in_max, out_min, out_max):
    """映射值范围（类似Arduino map）"""
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

# 在main.py中使用：
# from utils import millis, uptime, reset
```

### 2.4 内存管理（gc模块）

嵌入式设备内存有限，内存管理至关重要。

**gc模块API：**

```python
import gc

# 查看可用内存
print(gc.mem_free())   # 返回可用堆内存（字节）

# 查看已分配内存
print(gc.mem_alloc())  # 返回已分配堆内存（字节）

# 手动触发垃圾回收
gc.collect()

# 设置回收阈值（分配量达到阈值时自动回收）
gc.threshold(4096)  # 4KB阈值

# 调试：获取内存分配信息（需要编译时启用）
# gc.enable()   # 启用自动回收
# gc.disable()  # 禁用自动回收（实时场景慎用）
```

**内存优化技巧：**

```python
# 技巧1：使用 __slots__ 减少对象内存开销
class Sensor:
    __slots__ = ('name', 'pin', 'value')  # 固定属性，减少dict开销
    def __init__(self, name, pin):
        self.name = name
        self.pin = pin
        self.value = 0

# 技巧2：避免在循环中创建新对象
# 差：每次循环创建新bytes对象
for i in range(100):
    data = bytes([i, i+1, i+2])

# 好：复用bytearray
buf = bytearray(3)
for i in range(100):
    buf[0] = i
    buf[1] = i + 1
    buf[2] = i + 2

# 技巧3：使用 micropython.mem_info() 查看详细内存
import micropython
micropython.mem_info(True)  # True显示详细信息

# 技巧4：及时释放大对象
large_buffer = bytearray(4096)
# ... 使用完后 ...
del large_buffer
gc.collect()

# 技巧5：使用小整数缓存（-5到256自动缓存）
x = 42    # 使用缓存，不分配新内存
y = 42    # 同一对象
assert x is y  # True

# 技巧6：避免不必要的字符串拼接
# 差：多次拼接
s = ""
for i in range(10):
    s += str(i)  # 每次创建新字符串

# 好：使用join
parts = [str(i) for i in range(10)]
s = "".join(parts)

# 技巧7：合理使用 bytes vs bytearray
# bytes - 不可变，适合常量数据
HEADER = b'\xAA\x55\x03'
# bytearray - 可变，适合缓冲区
rx_buf = bytearray(256)
```

**内存监控示例：**

```python
import gc
import time

class MemoryMonitor:
    """内存使用监控"""
    def __init__(self, threshold_kb=10):
        self.threshold = threshold_kb * 1024
        self.history = []

    def check(self, tag=""):
        gc.collect()
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        total = free + alloc
        usage_pct = alloc / total * 100

        info = {
            "tag": tag,
            "free": free,
            "alloc": alloc,
            "usage": f"{usage_pct:.1f}%"
        }
        self.history.append(info)

        if free < self.threshold:
            print(f"[WARN] Low memory: {free} bytes free ({tag})")

        return info

    def report(self):
        for h in self.history:
            print(f"  [{h['tag']}] free={h['free']}, "
                  f"alloc={h['alloc']}, usage={h['usage']}")

# 使用示例
mon = MemoryMonitor(threshold_kb=8)
mon.check("startup")

data = bytearray(8192)
mon.check("after_alloc")

del data
gc.collect()
mon.check("after_free")

mon.report()
```

---

## 三、GPIO控制

### 3.1 Pin类详解

`machine.Pin` 是MicroPython中最基本的硬件抽象类。

**构造函数：**

```python
from machine import Pin

# 完整参数
pin = Pin(
    id,           # 引脚编号或名称
    mode=Pin.IN,  # 模式：Pin.IN / Pin.OUT / Pin.OPEN_DRAIN
    pull=None,    # 上拉/下拉：Pin.PULL_UP / Pin.PULL_DOWN / None
    value=None,   # 初始电平：0或1
    drive=Pin.DRIVE_1,  # 驱动强度（部分平台支持）
    alt=None      # 复用功能（部分平台支持）
)

# 常见用法
led = Pin(2, Pin.OUT)                          # 输出
btn = Pin(0, Pin.IN, Pin.PULL_UP)              # 输入+上拉
sensor = Pin(4, Pin.IN, Pin.PULL_DOWN)         # 输入+下拉
open_drain = Pin(5, Pin.OPEN_DRAIN)            # 开漏输出
```

**Pin类方法：**

| 方法 | 说明 |
|------|------|
| `pin.value([x])` | 获取/设置引脚电平(0/1) |
| `pin([x])` | 等同于pin.value() |
| `pin.on()` | 设置高电平(1) |
| `pin.off()` | 设置低电平(0) |
| `pin.irq(handler, trigger, priority, wake, hard)` | 配置中断 |

**Pin类常量：**

| 常量 | 说明 |
|------|------|
| `Pin.IN` | 输入模式 |
| `Pin.OUT` | 输出模式 |
| `Pin.OPEN_DRAIN` | 开漏模式 |
| `Pin.PULL_UP` | 内部上拉 |
| `Pin.PULL_DOWN` | 内部下拉 |
| `Pin.IRQ_RISING` | 上升沿触发 |
| `Pin.IRQ_FALLING` | 下降沿触发 |
| `Pin.IRQ_LOW_LEVEL` | 低电平触发 |
| `Pin.IRQ_HIGH_LEVEL` | 高电平触发 |

### 3.2 LED控制示例

```python
from machine import Pin
import time

class LED:
    """LED控制类"""
    def __init__(self, pin_num, active_high=True):
        self.pin = Pin(pin_num, Pin.OUT)
        self.active_high = active_high
        self.off()

    def on(self):
        self.pin.value(1 if self.active_high else 0)

    def off(self):
        self.pin.value(0 if self.active_high else 1)

    def toggle(self):
        self.pin.value(not self.pin.value())

    def blink(self, times=3, interval=0.3):
        """闪烁指定次数"""
        for _ in range(times):
            self.on()
            time.sleep(interval)
            self.off()
            time.sleep(interval)

    def breathe(self, duration=2):
        """呼吸灯效果（需要PWM支持）"""
        from machine import PWM
        pwm = PWM(self.pin, freq=1000, duty=0)
        step = 1024 // 50
        # 渐亮
        for duty in range(0, 1024, step):
            pwm.duty(duty)
            time.sleep_ms(duration * 1000 // 100)
        # 渐暗
        for duty in range(1024, 0, -step):
            pwm.duty(duty)
            time.sleep_ms(duration * 1000 // 100)
        pwm.deinit()

# 使用示例
led_builtin = LED(2)  # ESP32板载LED
led_external = LED(5, active_high=False)  # 外接LED（低电平点亮）

led_builtin.blink(times=5, interval=0.2)
```

**PWM控制LED亮度：**

```python
from machine import Pin, PWM
import time

# 创建PWM对象
led_pwm = PWM(Pin(2), freq=1000, duty=512)  # 50%亮度

# 调整亮度 (duty: 0-1023)
led_pwm.duty(0)       # 熄灭
led_pwm.duty(1023)    # 最亮
led_pwm.duty(256)     # 25%亮度

# 动态调光
def fade_led(pwm_pin, steps=100, delay_ms=20):
    """LED渐变效果"""
    for i in range(steps):
        duty = int(1023 * (i / steps))
        pwm_pin.duty(duty)
        time.sleep_ms(delay_ms)
    for i in range(steps):
        duty = int(1023 * (1 - i / steps))
        pwm_pin.duty(duty)
        time.sleep_ms(delay_ms)

fade_led(led_pwm)

# 清理
led_pwm.deinit()
```

### 3.3 按键输入与中断

```python
from machine import Pin
import time

class Button:
    """按键控制类（含消抖）"""
    def __init__(self, pin_num, pull=Pin.PULL_UP, debounce_ms=200):
        self.pin = Pin(pin_num, Pin.IN, pull)
        self.debounce_ms = debounce_ms
        self.last_press = 0
        self.callbacks = {}
        self._press_count = 0

        # 配置中断
        self.pin.irq(
            trigger=Pin.IRQ_FALLING if pull == Pin.PULL_UP else Pin.IRQ_RISING,
            handler=self._irq_handler
        )

    def _irq_handler(self, pin):
        """中断处理（含消抖）"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_press) > self.debounce_ms:
            self.last_press = now
            self._press_count += 1
            # 执行注册的回调
            for cb in self.callbacks.values():
                cb(self)

    def on_press(self, name, callback):
        """注册按下回调"""
        self.callbacks[name] = callback

    def remove_callback(self, name):
        """移除回调"""
        self.callbacks.pop(name, None)

    def is_pressed(self):
        """检查当前是否按下（电平检测）"""
        return self.pin.value() == 0  # 假设PULL_UP

    @property
    def press_count(self):
        return self._press_count

# 使用示例
def on_btn_press(btn):
    print(f"Button pressed! Total: {btn.press_count}")

button = Button(0)  # ESP32 BOOT按钮
button.on_press("print", on_btn_press)

# 主循环
while True:
    time.sleep(1)
```

### 3.4 按键扫描（轮询方式）

```python
from machine import Pin
import time

class KeyScanner:
    """矩阵键盘扫描器"""
    def __init__(self, row_pins, col_pins):
        self.rows = [Pin(p, Pin.OUT) for p in row_pins]
        self.cols = [Pin(p, Pin.IN, Pin.PULL_UP) for p in col_pins]
        self.keymap = None

    def set_keymap(self, keymap):
        """设置键值映射表"""
        self.keymap = keymap

    def scan(self):
        """扫描键盘，返回按下的键值"""
        for i, row in enumerate(self.rows):
            row.value(0)  # 拉低当前行
            for j, col in enumerate(self.cols):
                if col.value() == 0:  # 检测到低电平
                    time.sleep_ms(20)  # 消抖
                    if col.value() == 0:
                        row.value(1)  # 恢复行电平
                        if self.keymap:
                            return self.keymap[i][j]
                        return (i, j)
            row.value(1)  # 恢复行电平
        return None

# 4x4矩阵键盘示例
scanner = KeyScanner(
    row_pins=[2, 4, 5, 18],
    col_pins=[19, 21, 22, 23]
)
scanner.set_keymap([
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D']
])

while True:
    key = scanner.scan()
    if key:
        print(f"Key: {key}")
    time.sleep_ms(50)
```

---

## 四、通信接口

### 4.1 I2C通信

**I2C类初始化：**

```python
from machine import Pin, I2C

# ESP32 I2C（软件I2C，引脚任意指定）
i2c = I2C(
    scl=Pin(22),     # 时钟线
    sda=Pin(21),     # 数据线
    freq=400000      # 频率400kHz（Fast Mode）
)

# RP2040/Raspberry Pi Pico 硬件I2C
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)  # I2C0
i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)  # I2C1

# STM32 硬件I2C
i2c = I2C(1, scl=Pin('PB6'), sda=Pin('PB7'), freq=400000)
```

**I2C基本操作：**

```python
# 扫描I2C总线上的设备
devices = i2c.scan()
print(f"Found {len(devices)} devices:")
for addr in devices:
    print(f"  0x{addr:02X} ({addr})")

# 读写操作
addr = 0x3C  # 设备地址（如OLED显示屏）

# 写单字节
i2c.writeto(addr, b'\x00\xAF')  # 发送命令

# 写多字节
data = bytes([0x00, 0xAE, 0xD5, 0x80])
i2c.writeto(addr, data)

# 读取数据
buf = bytearray(6)
i2c.readfrom_into(addr, buf)  # 读取到缓冲区

# 从指定寄存器读取
reg = b'\x00'  # 寄存器地址
i2c.writeto(addr, reg)
result = i2c.readfrom(addr, 2)  # 读取2字节

# 写入指定寄存器
i2c.writeto_mem(addr, 0x00, b'\xAF', addrsize=8)
```

**I2C设备驱动示例 - BME280温湿度气压传感器：**

```python
from machine import I2C, Pin
import struct
import time

class BME280:
    """BME280温湿度气压传感器驱动"""
    ADDR = 0x76  # 或 0x77（取决于SDO引脚）
    REG_ID = 0xD0
    REG_CTRL_HUM = 0xF2
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_DATA = 0xF7

    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr
        self._load_calibration()
        self._configure()

    def _read_reg(self, reg, nbytes=1):
        return self.i2c.readfrom_mem(self.addr, reg, nbytes)

    def _write_reg(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _load_calibration(self):
        """加载校准数据"""
        # 温度和压力校准
        data = self.i2c.readfrom_mem(self.addr, 0x88, 26)
        self.dig_T1 = struct.unpack_from('<H', data, 0)[0]
        self.dig_T2 = struct.unpack_from('<h', data, 2)[0]
        self.dig_T3 = struct.unpack_from('<h', data, 4)[0]
        self.dig_P1 = struct.unpack_from('<H', data, 6)[0]
        self.dig_P2 = struct.unpack_from('<h', data, 8)[0]
        # ... 更多校准参数省略

        # 湿度校准
        self.dig_H1 = self._read_reg(0xA1)[0]
        h_data = self.i2c.readfrom_mem(self.addr, 0xE1, 7)
        self.dig_H2 = struct.unpack_from('<h', h_data, 0)[0]
        self.dig_H3 = h_data[2]
        self.dig_H4 = (h_data[3] << 4) | (h_data[4] & 0x0F)
        self.dig_H5 = (h_data[5] << 4) | (h_data[4] >> 4)
        self.dig_H6 = struct.unpack_from('<b', h_data, 6)[0]

    def _configure(self):
        """配置传感器工作模式"""
        # 湿度过采样 x1
        self._write_reg(self.REG_CTRL_HUM, 0x01)
        # 温度过采样 x2, 压力过采样 x16, 正常模式
        self._write_reg(self.REG_CTRL_MEAS, 0x57)
        # 待机时间500ms, 滤波系数16
        self._write_reg(self.REG_CONFIG, 0x90)

    def read(self):
        """读取温湿度气压数据"""
        data = self._read_reg(self.REG_DATA, 8)

        # 解析原始数据
        raw_press = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        raw_hum = (data[6] << 8) | data[7]

        # 温度补偿（简化版）
        var1 = (raw_temp / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        var2 = ((raw_temp / 131072.0 - self.dig_T1 / 8192.0) ** 2) * self.dig_T3
        t_fine = var1 + var2
        temp = t_fine / 5120.0

        # 湿度补偿（简化版）
        h = t_fine - 76800.0
        h = (raw_hum - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * h)) * \
            (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * h *
            (1.0 + self.dig_H3 / 67108864.0 * h)))
        hum = max(0, min(100, h))

        return {"temperature": round(temp, 2), "humidity": round(hum, 2)}

# 使用示例
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
sensor = BME280(i2c)
data = sensor.read()
print(f"Temp: {data['temperature']}°C, Humidity: {data['humidity']}%")
```

### 4.2 SPI通信

**SPI类初始化：**

```python
from machine import Pin, SPI

# ESP32 HSPI
spi = SPI(
    1,                    # SPI总线编号
    baudrate=10000000,    # 10MHz
    polarity=0,           # 时钟空闲电平
    phase=0,              # 时钟相位
    bits=8,               # 数据位数
    firstbit=SPI.MSB,    # 高位先发
    sck=Pin(14),          # 时钟引脚
    mosi=Pin(13),         # 主出从入
    miso=Pin(12)          # 主入从出
)

# Raspberry Pi Pico 硬件SPI
spi = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))

# STM32 硬件SPI
spi = SPI(1, baudrate=8000000, polarity=0, phase=0,
          sck=Pin('PB3'), mosi=Pin('PB5'), miso=Pin('PB4'))
```

**SPI基本操作：**

```python
cs = Pin(15, Pin.OUT)  # 片选引脚

# 发送数据
cs.value(0)  # 选中设备
spi.write(b'\x9F')  # 发送命令
cs.value(1)  # 释放设备

# 读取数据
cs.value(0)
data = spi.read(3)  # 读取3字节
cs.value(1)

# 同时读写
cs.value(0)
rx_buf = spi.readwrite(bytearray([0x9F, 0x00, 0x00, 0x00]))
cs.value(1)

# 使用SPI写入内存缓冲区
tx_buf = bytearray(b'\x01\x02\x03')
rx_buf = bytearray(3)
spi.write_readinto(tx_buf, rx_buf)
```

### 4.3 UART通信

**UART类初始化：**

```python
from machine import UART, Pin

# ESP32 UART
uart = UART(
    1,                    # UART编号
    baudrate=115200,      # 波特率
    tx=Pin(17),           # 发送引脚
    rx=Pin(16),           # 接收引脚
    bits=8,               # 数据位
    parity=None,          # 校验位：None/0(Even)/1(Odd)
    stop=1,               # 停止位
    rxbuf=256,            # 接收缓冲区大小
    timeout=1000          # 超时（毫秒）
)

# Raspberry Pi Pico UART
uart = UART(1, baudrate=9600, tx=Pin(8), rx=Pin(9))
```

**UART基本操作：**

```python
# 发送数据
uart.write(b'Hello\r\n')
uart.write('Hello\r\n')        # 字符串自动编码
uart.write(bytearray(10))      # 字节数组

# 接收数据
data = uart.read()              # 读取所有可用数据
data = uart.read(10)            # 读取最多10字节
line = uart.readline()          # 读取一行（到\n）

# 检查可用数据量
n = uart.any()  # 返回接收缓冲区中的字节数

# 读取到指定缓冲区
buf = bytearray(64)
n = uart.readinto(buf)
n = uart.readinto(buf, 10)     # 最多读取10字节
```

**GPS模块驱动示例：**

```python
from machine import UART, Pin
import time

class GPS:
    """NMEA GPS模块驱动"""
    def __init__(self, uart):
        self.uart = uart
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.speed = 0.0
        self.satellites = 0
        self.fix = False
        self.timestamp = ""

    def _parse_gpgga(self, parts):
        """解析GPGGA语句（定位信息）"""
        if len(parts) < 15:
            return
        self.timestamp = parts[1]
        lat = parts[2]
        lon = parts[4]
        if lat and lon:
            self.latitude = float(lat[:2]) + float(lat[2:]) / 60
            if parts[3] == 'S':
                self.latitude = -self.latitude
            self.longitude = float(lon[:3]) + float(lon[3:]) / 60
            if parts[4] == 'W':
                self.longitude = -self.longitude
        self.fix = int(parts[6]) > 0
        self.satellites = int(parts[7])
        if parts[9]:
            self.altitude = float(parts[9])

    def _parse_gprmc(self, parts):
        """解析GPRMC语句（推荐最小定位信息）"""
        if len(parts) < 8:
            return
        if parts[7]:
            self.speed = float(parts[7]) * 1.852  # 节->km/h

    def update(self):
        """从UART读取并解析NMEA数据"""
        line = self.uart.readline()
        if not line:
            return False

        try:
            line = line.decode('ascii').strip()
        except (UnicodeError, AttributeError):
            return False

        if not line.startswith('$'):
            return False

        # 校验和验证
        if '*' in line:
            data, checksum = line[1:].split('*', 1)
            calc = 0
            for c in data:
                calc ^= ord(c)
            if int(checksum, 16) != calc:
                return False

        parts = line.split(',')
        cmd = parts[0]

        if cmd == '$GPGGA' or cmd == '$GNGGA':
            self._parse_gpgga(parts)
        elif cmd == '$GPRMC' or cmd == '$GNRMC':
            self._parse_gprmc(parts)

        return True

    def __str__(self):
        return (f"GPS(lat={self.latitude:.6f}, lon={self.longitude:.6f}, "
                f"alt={self.altitude:.1f}m, sats={self.satellites})")

# 使用示例
gps_uart = UART(2, baudrate=9600, tx=Pin(17), rx=Pin(16))
gps = GPS(gps_uart)

while True:
    if gps.update():
        print(gps)
    time.sleep_ms(100)
```

---

## 五、网络功能

### 5.1 WiFi连接

**Station模式（客户端）：**

```python
import network
import time

def connect_wifi(ssid, password, timeout=15):
    """连接WiFi热点"""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    if sta.isconnected():
        print(f"Already connected: {sta.ifconfig()[0]}")
        return sta

    print(f"Connecting to {ssid}...")
    sta.connect(ssid, password)

    start = time.time()
    while not sta.isconnected():
        if time.time() - start > timeout:
            print("Connection timeout!")
            sta.active(False)
            return None
        time.sleep(0.5)
        print(".", end="")

    print(f"\nConnected! IP: {sta.ifconfig()[0]}")
    print(f"  Netmask: {sta.ifconfig()[1]}")
    print(f"  Gateway: {sta.ifconfig()[2]}")
    print(f"  DNS:     {sta.ifconfig()[3]}")
    return sta

# 使用
wlan = connect_wifi("MySSID", "MyPassword")
```

**AP模式（热点）：**

```python
import network

def start_ap(ssid, password=None, channel=1):
    """创建WiFi热点"""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    if password:
        ap.config(essid=ssid, password=password, authmode=network.AUTH_WPA_WPA2_PSK)
    else:
        ap.config(essid=ssid, authmode=network.AUTH_OPEN)

    ap.config(channel=channel)

    print(f"AP '{ssid}' started")
    print(f"  IP: {ap.ifconfig()[0]}")
    print(f"  Clients: {ap.status('stations')}")
    return ap

# 同时启用Station和AP模式
sta = network.WLAN(network.STA_IF)
sta.active(True)
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid="ESP32-Config", password="12345678")
```

### 5.2 MQTT客户端

**umqtt.simple 基础用法：**

```python
from umqtt.simple import MQTTClient
import json
import time

class MQTTHandler:
    """MQTT客户端封装"""
    def __init__(self, client_id, broker, port=1883, user=None, password=None):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.client = None
        self.user = user
        self.password = password
        self.subscriptions = {}
        self.connected = False

    def connect(self):
        """连接MQTT服务器"""
        self.client = MQTTClient(
            self.client_id,
            self.broker,
            port=self.port,
            user=self.user,
            password=self.password,
            keepalive=60
        )
        self.client.set_callback(self._on_message)
        self.client.connect()
        self.connected = True
        print(f"MQTT connected to {self.broker}")

    def _on_message(self, topic, msg):
        """内部消息回调"""
        topic = topic.decode()
        msg = msg.decode()
        if topic in self.subscriptions:
            self.subscriptions[topic](topic, msg)

    def subscribe(self, topic, callback):
        """订阅主题"""
        self.subscriptions[topic] = callback
        if self.connected:
            self.client.subscribe(topic)

    def publish(self, topic, payload, qos=0, retain=False):
        """发布消息"""
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        if isinstance(payload, str):
            payload = payload.encode()
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def check_msg(self):
        """检查新消息（非阻塞）"""
        try:
            self.client.check_msg()
        except OSError:
            self.connected = False
            self.reconnect()

    def reconnect(self):
        """重新连接"""
        try:
            self.connect()
            for topic in self.subscriptions:
                self.client.subscribe(topic)
        except Exception as e:
            print(f"MQTT reconnect failed: {e}")

# 使用示例
def on_led_control(topic, msg):
    print(f"LED command: {msg}")
    led.value(1 if msg == "ON" else 0)

def on_config(topic, msg):
    print(f"Config update: {msg}")
    config = json.loads(msg)
    # 应用配置...

mqtt = MQTTHandler("esp32-01", "192.168.1.100", user="user", password="pass")
mqtt.connect()
mqtt.subscribe("home/esp32/led", on_led_control)
mqtt.subscribe("home/esp32/config", on_config)

# 主循环
while True:
    mqtt.check_msg()
    # 定时上报传感器数据
    sensor_data = {"temp": 25.5, "hum": 60}
    mqtt.publish("home/esp32/sensor", sensor_data)
    time.sleep(5)
```

**umqtt.robust 自动重连：**

```python
from umqtt.robust import MQTTClient

client = MQTTClient("esp32", "192.168.1.100")
client.DEBUG = True  # 启用调试输出
client.set_last_will("home/esp32/status", "offline", retain=True)

# 自动重连 - 首次连接
client.connect()

# 发布消息（自动重连）
while True:
    try:
        client.publish("home/esp32/data", '{"temp":25}')
        client.wait_msg()  # 阻塞等待消息
    except OSError:
        print("Connection lost, reconnecting...")
        client.connect()
```

### 5.3 HTTP请求

**urequests 库：**

```python
import urequests
import json

# GET请求
response = urequests.get("http://httpbin.org/get")
print(response.status_code)  # 200
print(response.headers)      # 响应头
data = response.json()       # 解析JSON
response.close()             # 重要：释放连接

# POST请求
payload = {"sensor": "temp", "value": 25.5}
response = urequests.post(
    "http://api.example.com/data",
    json=payload,
    headers={"Content-Type": "application/json", "Authorization": "Bearer token123"}
)
print(response.text)
response.close()

# HTTPS请求（需要SSL）
import ssl
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.verify_mode = ssl.CERT_NONE  # 生产环境应验证证书
response = urequests.get("https://api.example.com/data", ssl=ctx)
```

**简易HTTP客户端封装：**

```python
import socket
import json

class SimpleHTTP:
    """轻量级HTTP客户端（不依赖urequests）"""
    @staticmethod
    def parse_url(url):
        """解析URL"""
        proto, _, host_path = url.partition("://")
        host, _, path = host_path.partition("/")
        port = 80 if proto == "http" else 443
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        return proto, host, port, "/" + path

    @staticmethod
    def get(url, headers=None):
        """发送GET请求"""
        proto, host, port, path = SimpleHTTP.parse_url(url)

        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket()
        sock.connect(addr)

        if proto == "https":
            import ssl
            sock = ssl.wrap_socket(sock)

        request = f"GET {path} HTTP/1.0\r\nHost: {host}\r\n"
        if headers:
            for k, v in headers.items():
                request += f"{k}: {v}\r\n"
        request += "\r\n"
        sock.send(request.encode())

        response = b""
        while True:
            chunk = sock.recv(512)
            if not chunk:
                break
            response += chunk

        sock.close()

        # 解析响应
        header_end = response.find(b"\r\n\r\n")
        headers_raw = response[:header_end].decode()
        body = response[header_end + 4:]
        status = int(headers_raw.split("\r\n")[0].split(" ")[1])

        return status, headers_raw, body

# 使用
status, headers, body = SimpleHTTP.get("http://httpbin.org/ip")
print(f"Status: {status}")
print(f"Body: {body.decode()}")
```

### 5.4 Socket编程

**TCP服务器：**

```python
import socket
import network

# 获取IP地址
sta = network.WLAN(network.STA_IF)
ip = sta.ifconfig()[0]

# 创建TCP服务器
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8080))
server.listen(3)  # 最大等待连接数

print(f"TCP Server listening on {ip}:8080")

while True:
    try:
        client, addr = server.accept()
        print(f"Client connected: {addr}")

        # 读取数据
        data = client.recv(1024)
        if data:
            print(f"Received: {data.decode()}")
            # 回显
            client.send(b"Echo: " + data)

        client.close()
    except OSError as e:
        print(f"Error: {e}")
```

**简易Web服务器：**

```python
import socket
import json
import os

class WebServer:
    """简易HTTP Web服务器"""
    def __init__(self, port=80):
        self.port = port
        self.routes = {}
        self.server = None

    def route(self, path):
        """路由装饰器"""
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator

    def _send_response(self, client, status, content_type, body):
        """发送HTTP响应"""
        if isinstance(body, str):
            body = body.encode()
        header = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        )
        client.send(header.encode())
        client.send(body)

    def start(self):
        """启动服务器"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('0.0.0.0', self.port))
        self.server.listen(3)
        print(f"Web server on port {self.port}")

        while True:
            try:
                client, addr = self.server.accept()
                request = client.recv(1024).decode()

                # 解析请求
                first_line = request.split('\r\n')[0]
                method, path, _ = first_line.split(' ', 2)

                # 路由匹配
                if path in self.routes:
                    result = self.routes[path](request)
                    if isinstance(result, dict):
                        body = json.dumps(result)
                        self._send_response(client, "200 OK",
                                           "application/json", body)
                    else:
                        self._send_response(client, "200 OK",
                                           "text/html", str(result))
                else:
                    self._send_response(client, "404 Not Found",
                                       "text/html", "<h1>404</h1>")

                client.close()
            except Exception as e:
                print(f"Error: {e}")

# 使用示例
web = WebServer(port=80)

@web.route("/")
def index(request):
    return "<h1>ESP32 Web Server</h1><p><a href='/status'>Status</a></p>"

@web.route("/status")
def status(request):
    import gc
    import machine
    return {
        "free_memory": gc.mem_free(),
        "freq": machine.freq(),
        "platform": sys.platform
    }

web.start()
```

**UDP通信：**

```python
import socket

# UDP发送
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(b"Hello UDP", ("192.168.1.100", 9999))

# UDP接收
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 9999))
sock.settimeout(5)  # 5秒超时

while True:
    try:
        data, addr = sock.recvfrom(1024)
        print(f"From {addr}: {data.decode()}")
        sock.sendto(b"ACK", addr)
    except OSError:
        pass  # 超时，继续循环
```

---

## 六、文件系统

### 6.1 文件读写

**基本文件操作：**

```python
import os

# 写入文件
with open("data.txt", "w") as f:
    f.write("Hello, MicroPython!\n")
    f.write("Line 2\n")

# 读取文件
with open("data.txt", "r") as f:
    content = f.read()
    print(content)

# 逐行读取
with open("data.txt", "r") as f:
    for line in f:
        print(line.strip())

# 追加写入
with open("log.txt", "a") as f:
    f.write("New log entry\n")

# 写入二进制数据
with open("data.bin", "wb") as f:
    f.write(bytes([0x01, 0x02, 0x03, 0xFF]))

# 读取二进制数据
with open("data.bin", "rb") as f:
    data = f.read()
    print(data)  # b'\x01\x02\x03\xff'

# 列出文件
print(os.listdir())        # 当前目录
print(os.listdir("/lib"))  # /lib目录

# 文件信息
stat = os.stat("data.txt")
print(f"Size: {stat[6]} bytes")

# 删除文件
os.remove("data.txt")

# 创建目录
os.mkdir("logs")

# 删除目录
os.rmdir("logs")

# 重命名
os.rename("old.txt", "new.txt")

# 检查文件是否存在
try:
    os.stat("config.json")
    exists = True
except OSError:
    exists = False
```

### 6.2 SD卡挂载

```python
import machine
import os
from machine import SD, Pin, SPI

# 方法1：ESP32内置SD卡接口
sd = SD(slot=2)  # slot 2是ESP32的SD卡接口
os.mount(sd, "/sd")

# 方法2：SPI SD卡
spi = SPI(1, baudrate=1000000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
cs = Pin(15, Pin.OUT)
sd = SD(spi=spi, cs=cs)
os.mount(sd, "/sd")

# 方法3：RP2040/Pico
import sdcard
spi = machine.SPI(1, sck=machine.Pin(10), mosi=machine.Pin(11), miso=machine.Pin(12))
cs = machine.Pin(13, machine.Pin.OUT)
sd = sdcard.SDCard(spi, cs)
os.mount(sd, "/sd")

# 使用SD卡
print(os.listdir("/sd"))
with open("/sd/data.txt", "w") as f:
    f.write("Hello SD card!")

# 添加SD卡路径到模块搜索路径
import sys
sys.path.append("/sd/lib")

# 卸载SD卡（安全移除）
os.umount("/sd")
```

### 6.3 配置文件（JSON）

```python
import json
import os

class Config:
    """JSON配置文件管理"""
    def __init__(self, filepath="config.json", defaults=None):
        self.filepath = filepath
        self.data = defaults or {}
        self.load()

    def load(self):
        """从文件加载配置"""
        try:
            with open(self.filepath, "r") as f:
                saved = json.load(f)
                self.data.update(saved)
        except (OSError, ValueError):
            print(f"Config: using defaults")

    def save(self):
        """保存配置到文件"""
        with open(self.filepath, "w") as f:
            json.dump(self.data, f)

    def get(self, key, default=None):
        """获取配置项"""
        return self.data.get(key, default)

    def set(self, key, value):
        """设置配置项并保存"""
        self.data[key] = value
        self.save()

    def update(self, updates: dict):
        """批量更新配置"""
        self.data.update(updates)
        self.save()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def __repr__(self):
        return f"Config({json.dumps(self.data, indent=2)})"

# 使用示例
config = Config("config.json", defaults={
    "wifi_ssid": "default",
    "wifi_password": "",
    "mqtt_broker": "192.168.1.100",
    "mqtt_port": 1883,
    "sensor_interval": 5000,
    "led_brightness": 50,
    "device_name": "esp32-01"
})

# 读取配置
ssid = config.get("wifi_ssid")
interval = config["sensor_interval"]

# 修改配置
config.set("led_brightness", 75)

# 批量更新
config.update({
    "wifi_ssid": "NewNetwork",
    "wifi_password": "newpassword"
})

print(config)
```

---

## 七、定时器与中断

### 7.1 Timer类

```python
from machine import Timer

# ESP32定时器（硬件定时器）
# Timer ID: 0-3（ESP32有4个硬件定时器）

# 单次定时
timer = Timer(0)
timer.init(
    mode=Timer.ONE_SHOT,
    period=2000,        # 2000ms后触发
    callback=lambda t: print("One-shot fired!")
)

# 周期定时
timer = Timer(1)
timer.init(
    mode=Timer.PERIODIC,
    period=1000,        # 每1000ms触发
    callback=lambda t: print("Periodic tick")
)

# 停止定时器
timer.deinit()

# RP2040/Pico 定时器
timer = Timer(-1)  # 虚拟定时器
timer.init(
    mode=Timer.PERIODIC,
    period=500,
    callback=lambda t: print("Pico tick")
)
```

### 7.2 回调函数设计

```python
from machine import Timer, Pin, ADC
import time

class SensorSampler:
    """基于定时器的传感器采样器"""
    def __init__(self, adc_pin, sample_period_ms=100, buffer_size=100):
        self.adc = ADC(Pin(adc_pin))
        self.adc.atten(ADC.ATTN_11DB)  # 0-3.3V
        self.buffer = [0] * buffer_size
        self.buffer_idx = 0
        self.buffer_size = buffer_size
        self.sample_count = 0
        self.timer = Timer(0)
        self.callbacks = []

        # 启动采样定时器
        self.timer.init(
            mode=Timer.PERIODIC,
            period=sample_period_ms,
            callback=self._sample_isr
        )

    def _sample_isr(self, timer):
        """定时器中断回调（必须快速执行）"""
        value = self.adc.read()
        self.buffer[self.buffer_idx] = value
        self.buffer_idx = (self.buffer_idx + 1) % self.buffer_size
        self.sample_count += 1

    def get_latest(self, n=1):
        """获取最近n个采样值"""
        if n > self.buffer_size:
            n = self.buffer_size
        idx = (self.buffer_idx - n) % self.buffer_size
        return [self.buffer[(idx + i) % self.buffer_size] for i in range(n)]

    def get_average(self, n=10):
        """获取最近n个采样的平均值"""
        samples = self.get_latest(n)
        return sum(samples) / len(samples)

    def get_min_max(self, n=10):
        """获取最近n个采样的最小/最大值"""
        samples = self.get_latest(n)
        return min(samples), max(samples)

    def stop(self):
        """停止采样"""
        self.timer.deinit()

# 使用示例
sampler = SensorSampler(adc_pin=34, sample_period_ms=50)

while True:
    avg = sampler.get_average(20)
    voltage = avg / 4095 * 3.3
    print(f"ADC: {avg:.0f}, Voltage: {voltage:.2f}V")
    time.sleep(1)
```

### 7.3 定时采集系统

```python
import time
from machine import Timer, Pin, I2C, ADC
import json

class DataCollector:
    """多通道数据定时采集系统"""
    def __init__(self):
        self.channels = {}
        self.log_timer = Timer(0)
        self.collect_timer = Timer(1)
        self.running = False

    def add_channel(self, name, read_func, unit=""):
        """添加采集通道"""
        self.channels[name] = {
            "read": read_func,
            "unit": unit,
            "last_value": None,
            "history": [],
            "max_history": 60
        }

    def start(self, collect_interval_ms=1000, log_interval_ms=10000):
        """启动采集"""
        self.running = True
        self.collect_timer.init(
            mode=Timer.PERIODIC,
            period=collect_interval_ms,
            callback=self._collect
        )
        self.log_timer.init(
            mode=Timer.PERIODIC,
            period=log_interval_ms,
            callback=self._log
        )
        print(f"Collector started: collect={collect_interval_ms}ms, log={log_interval_ms}ms")

    def stop(self):
        """停止采集"""
        self.running = False
        self.collect_timer.deinit()
        self.log_timer.deinit()

    def _collect(self, timer):
        """采集回调"""
        for name, ch in self.channels.items():
            try:
                value = ch["read"]()
                ch["last_value"] = value
                ch["history"].append(value)
                if len(ch["history"]) > ch["max_history"]:
                    ch["history"].pop(0)
            except Exception as e:
                ch["last_value"] = None

    def _log(self, timer):
        """日志回调"""
        data = {}
        for name, ch in self.channels.items():
            data[name] = {
                "value": ch["last_value"],
                "unit": ch["unit"]
            }
        # 写入SD卡或上传
        print(json.dumps(data))

    def get_stats(self, name):
        """获取通道统计信息"""
        ch = self.channels.get(name)
        if not ch or not ch["history"]:
            return None
        history = ch["history"]
        return {
            "min": min(history),
            "max": max(history),
            "avg": sum(history) / len(history),
            "count": len(history)
        }

# 使用示例
collector = DataCollector()

# 添加温度通道
temp_sensor = ADC(Pin(34))
temp_sensor.atten(ADC.ATTN_11DB)
collector.add_channel("temperature",
    lambda: (temp_sensor.read() / 4095 * 3.3 - 0.5) * 100,
    unit="°C"
)

# 添加光照通道
light_sensor = ADC(Pin(35))
light_sensor.atten(ADC.ATTN_11DB)
collector.add_channel("light",
    lambda: light_sensor.read(),
    unit="raw"
)

collector.start(collect_interval_ms=500, log_interval_ms=5000)

# 主循环
try:
    while True:
        time.sleep(10)
        # 打印统计信息
        for name in collector.channels:
            stats = collector.get_stats(name)
            if stats:
                print(f"{name}: avg={stats['avg']:.1f}, "
                      f"min={stats['min']:.1f}, max={stats['max']:.1f}")
except KeyboardInterrupt:
    collector.stop()
    print("Collector stopped")
```

---

## 八、显示驱动

### 8.1 SPI屏幕驱动（SSD1306 OLED）

```python
from machine import Pin, SPI, I2C
import framebuf

class SSD1306_I2C:
    """SSD1306 OLED I2C驱动"""
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.buffer = bytearray(self.height * self.width // 8)
        self.fb = framebuf.FrameBuffer(self.buffer, self.width, self.height,
                                        framebuf.MONO_VLSB)
        self.init_display()

    def _write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x80, cmd]))

    def _write_data(self, data):
        # 分块写入（避免I2C缓冲区溢出）
        chunk_size = 16
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            buf = bytearray(len(chunk) + 1)
            buf[0] = 0x40
            buf[1:] = chunk
            self.i2c.writeto(self.addr, buf)

    def init_display(self):
        """初始化显示参数"""
        init_cmds = [
            0xAE,  # Display OFF
            0xD5, 0x80,  # Clock div
            0xA8, self.height - 1,  # Multiplex
            0xD3, 0x00,  # Display offset
            0x40,  # Start line
            0x8D, 0x14,  # Charge pump
            0x20, 0x00,  # Memory mode: horizontal
            0xA1,  # Segment remap
            0xC8,  # COM scan direction
            0xDA, 0x12,  # COM pins
            0x81, 0xCF,  # Contrast
            0xD9, 0xF1,  # Pre-charge
            0xDB, 0x40,  # VCOMH
            0xA4,  # Display from RAM
            0xA6,  # Normal display (not inverted)
            0xAF,  # Display ON
        ]
        for cmd in init_cmds:
            self._write_cmd(cmd)

    def show(self):
        """将缓冲区内容发送到屏幕"""
        self._write_cmd(0x21)  # Column address
        self._write_cmd(0)
        self._write_cmd(self.width - 1)
        self._write_cmd(0x22)  # Page address
        self._write_cmd(0)
        self._write_cmd(self.height // 8 - 1)
        self._write_data(self.buffer)

    def fill(self, color):
        self.fb.fill(color)

    def pixel(self, x, y, color=1):
        self.fb.pixel(x, y, color)

    def text(self, s, x, y, color=1):
        self.fb.text(s, x, y, color)

    def hline(self, x, y, w, color=1):
        self.fb.hline(x, y, w, color)

    def vline(self, x, y, h, color=1):
        self.fb.vline(x, y, h, color)

    def rect(self, x, y, w, h, color=1):
        self.fb.rect(x, y, w, h, color)

    def fill_rect(self, x, y, w, h, color=1):
        self.fb.fill_rect(x, y, w, h, color)

    def scroll(self, dx, dy):
        self.fb.scroll(dx, dy)

    def invert(self, invert):
        self._write_cmd(0xA7 if invert else 0xA6)

    def contrast(self, value):
        self._write_cmd(0x81)
        self._write_cmd(value)

    def poweroff(self):
        self._write_cmd(0xAE)

    def poweron(self):
        self._write_cmd(0xAF)

# 使用示例
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

oled.fill(0)
oled.text("MicroPython", 0, 0)
oled.text("OLED Display", 0, 16)
oled.rect(0, 32, 128, 32, 1)
oled.text("Hello World!", 8, 44)
oled.show()
```

### 8.2 framebuf帧缓冲

**framebuf支持的格式：**

| 格式 | 说明 | 每像素位数 |
|------|------|-----------|
| `MONO_VLSB` | 单色，垂直LSB | 1 |
| `MONO_HLSB` | 单色，水平LSB | 1 |
| `MONO_HMSB` | 单色，水平MSB | 1 |
| `GS2_HMSB` | 2级灰度 | 2 |
| `GS4_HMSB` | 4级灰度 | 4 |
| `GS8` | 8级灰度 | 8 |
| `RGB565` | 16位彩色 | 16 |

**framebuf绘图示例：**

```python
import framebuf

# 创建帧缓冲区
width, height = 128, 64
buffer = bytearray(width * height // 8)  # 单色，每字节8像素
fb = framebuf.FrameBuffer(buffer, width, height, framebuf.MONO_VLSB)

# 基本绘图
fb.fill(0)                          # 清屏（黑色）
fb.pixel(64, 32, 1)                 # 画点
fb.text("Hello", 10, 10)            # 文字（8x8像素字体）
fb.hline(0, 30, 128, 1)            # 水平线
fb.vline(64, 0, 64, 1)             # 垂直线
fb.rect(10, 10, 50, 30, 1)         # 矩形框
fb.fill_rect(70, 10, 50, 30, 1)    # 填充矩形

# 绘制简单图表
def draw_bar_chart(fb, data, x, y, w, h):
    """绘制柱状图"""
    fb.rect(x, y, w, h, 1)
    max_val = max(data) if data else 1
    bar_w = (w - 2) // len(data)
    for i, val in enumerate(data):
        bar_h = int((val / max_val) * (h - 4))
        bar_x = x + 1 + i * bar_w
        bar_y = y + h - 2 - bar_h
        fb.fill_rect(bar_x, bar_y, bar_w - 1, bar_h, 1)

# 自定义字体（放大显示）
def draw_big_text(fb, text, x, y, scale=2):
    """放大显示文字"""
    for i, char in enumerate(text):
        char_x = x + i * 8 * scale
        # 创建临时小缓冲区
        tmp_buf = bytearray(8)
        tmp_fb = framebuf.FrameBuffer(tmp_buf, 8, 8, framebuf.MONO_VLSB)
        tmp_fb.text(char, 0, 0)
        # 逐像素放大
        for py in range(8):
            for px in range(8):
                if tmp_fb.pixel(px, py):
                    for sy in range(scale):
                        for sx in range(scale):
                            fb.pixel(char_x + px * scale + sx,
                                    y + py * scale + sy, 1)
```

### 8.3 LVGL移植概述

LVGL(Light and Versatile Graphics Library)可以移植到MicroPython上。

**LVGL-MicroPython集成：**

```python
# LVGL在MicroPython中的使用（需要固件支持LVGL绑定）
import lvgl as lv
import lv_utils

# 初始化LVGL
lv.init()

# 创建显示驱动
disp_buf = lv.disp_draw_buf_t()
buf1 = bytearray(240 * 10 * 2)  # 10行缓冲区
disp_buf.init(buf1, None, len(buf1) // 4)

disp_drv = lv.disp_drv_t()
disp_drv.init()
disp_drv.draw_buf = disp_buf
disp_drv.flush_cb = flush_cb  # 需要实现的刷新回调
disp_drv.hor_res = 240
disp_drv.ver_res = 320
disp_drv.register()

# 创建UI元素
scr = lv.scr_act()

# 创建标签
label = lv.label(scr)
label.set_text("Hello LVGL!")
label.align(lv.ALIGN.CENTER, 0, 0)

# 创建按钮
btn = lv.btn(scr)
btn.align(lv.ALIGN.CENTER, 0, 40)
btn_label = lv.label(btn)
btn_label.set_text("Click Me")

def btn_cb(event):
    print("Button clicked!")

btn.add_event_cb(btn_cb, lv.EVENT.CLICKED, None)

# 创建滑块
slider = lv.slider(scr)
slider.align(lv.ALIGN.CENTER, 0, 80)
slider.set_range(0, 100)

# 创建进度条
bar = lv.bar(scr)
bar.align(lv.ALIGN.CENTER, 0, 120)
bar.set_value(75, lv.ANIM.ON)

# LVGL任务处理循环
while True:
    lv.task_handler()
    time.sleep_ms(5)
```

**LVGL移植要点：**

- 需要为目标平台编译LVGL C库并绑定到MicroPython
- ESP32-S3推荐使用，因其有PSRAM支持大型帧缓冲
- 显示刷新回调(`flush_cb`)需要使用DMA或SPI批量传输
- 触摸屏需要注册`indev_drv`输入设备驱动
- 建议至少2MB PSRAM用于复杂UI

---

## 九、低功耗

### 9.1 Deep Sleep

```python
import machine
from machine import Pin, RTC
import esp32  # ESP32特有模块

# 基本Deep Sleep
print("Going to deep sleep for 30 seconds...")
machine.deepsleep(30000)  # 30秒后唤醒

# 无限深度睡眠（只能通过外部唤醒）
machine.deepsleep()

# 检查唤醒原因
wake_reason = machine.wake_reason()
print(f"Wake reason: {wake_reason}")
# machine.PIN_WAKE    - GPIO唤醒
# machine.RTC_WAKE    - 定时器唤醒
# machine.EXT0_WAKE   - 外部唤醒0
# machine.EXT1_WAKE   - 外部唤醒1
# machine.TOUCHPAD_WAKE - 触摸唤醒
```

### 9.2 唤醒源配置

**定时器唤醒：**

```python
import machine

# RTC定时器唤醒（最常用）
sleep_seconds = 60
print(f"Deep sleep {sleep_seconds}s...")
machine.deepsleep(sleep_seconds * 1000)
```

**GPIO唤醒：**

```python
import machine
from machine import Pin
import esp32

# EXT0唤醒：单个引脚唤醒
# 参数：Pin对象, 电平（0=低电平, 1=高电平）
wake_pin = Pin(4, Pin.IN, Pin.PULL_DOWN)
esp32.wake_on_ext0(wake_pin, level=esp32.WAKEUP_ANY_HIGH)

# EXT1唤醒：多个引脚，任一触发
# 参数：Pin列表, 逻辑（0=任一低电平, 1=任一高电平）
pins = [Pin(2, Pin.IN), Pin(4, Pin.IN), Pin(15, Pin.IN)]
esp32.wake_on_ext1(pins, level=esp32.WAKEUP_ANY_HIGH)

# 触摸唤醒（ESP32）
touch_pin = Pin(4)
touch_pin.config()
esp32.wake_on_touch(True)

print("Entering deep sleep (touch or pin to wake)...")
machine.deepsleep()
```

### 9.3 低功耗应用设计

```python
import machine
from machine import Pin, ADC, I2C, deepsleep
import esp32
import time
import json

class LowPowerSensor:
    """低功耗传感器节点"""
    def __init__(self, config_file="config.json"):
        self.wake_count = 0
        self.config_file = config_file
        self._load_config()

    def _load_config(self):
        """加载配置"""
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
        except OSError:
            self.config = {
                "sleep_seconds": 60,
                "report_interval": 5,  # 每5次唤醒上报一次
                "wifi_ssid": "default",
                "wifi_password": ""
            }

    def _save_wake_count(self):
        """保存唤醒计数到RTC内存"""
        rtc = machine.RTC()
        rtc.memory(json.dumps({"wake_count": self.wake_count}).encode())

    def _load_wake_count(self):
        """从RTC内存恢复唤醒计数"""
        rtc = machine.RTC()
        data = rtc.memory()
        if data:
            try:
                return json.loads(data.decode()).get("wake_count", 0)
            except:
                pass
        return 0

    def read_sensors(self):
        """读取所有传感器"""
        data = {}
        # 温度（使用内部温度传感器或外接）
        temp_adc = ADC(Pin(34))
        temp_adc.atten(ADC.ATTN_11DB)
        raw = temp_adc.read()
        data["temperature"] = round((raw / 4095 * 3.3 - 0.5) * 100, 1)
        data["battery"] = round(raw / 4095 * 3.3 * 2, 2)  # 假设分压电阻
        return data

    def report_data(self, data):
        """通过WiFi上报数据"""
        import network
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        sta.connect(self.config["wifi_ssid"], self.config["wifi_password"])

        timeout = 10
        while not sta.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1

        if sta.isconnected():
            import urequests
            try:
                urequests.post("http://server/api/data", json=data)
                print("Data reported")
            except Exception as e:
                print(f"Report failed: {e}")

        sta.active(False)  # 关闭WiFi省电

    def run(self):
        """主运行流程"""
        self.wake_count = self._load_wake_count() + 1
        print(f"Wake #{self.wake_count}")

        # 读取传感器
        sensor_data = self.read_sensors()
        sensor_data["wake_count"] = self.wake_count
        print(f"Sensor data: {sensor_data}")

        # 判断是否需要上报
        if self.wake_count >= self.config["report_interval"]:
            self.report_data(sensor_data)
            self.wake_count = 0

        # 保存状态
        self._save_wake_count()

        # 配置唤醒源并进入深度睡眠
        wake_pin = Pin(4, Pin.IN, Pin.PULL_DOWN)
        esp32.wake_on_ext0(wake_pin, level=esp32.WAKEUP_ANY_HIGH)

        sleep_ms = self.config["sleep_seconds"] * 1000
        print(f"Deep sleep {self.config['sleep_seconds']}s...")
        machine.deepsleep(sleep_ms)

# 启动
node = LowPowerSensor()
node.run()
```

**功耗优化技巧：**

| 操作 | 功耗影响 |
|------|---------|
| WiFi关闭 | 从约80mA降到约15mA |
| CPU降频80MHz | 约降低30% |
| 关闭蓝牙 | 降低约10mA |
| 关闭ADC | 微小降低 |
| Deep Sleep | 约10uA（ESP32） |
| 关闭内部温度传感器 | 微小降低 |
| 使用EXT0唤醒而非定时器 | 定时器保持RTC运行 |

---

## 十、CircuitPython

### 10.1 Adafruit生态系统

CircuitPython是Adafruit Industries维护的MicroPython分支，专注于易用性和教育。

**CircuitPython特性：**

- **USB存储模式**：代码直接拖入U盘，无需烧录工具
- **自动重载**：保存代码后自动运行
- **统一API**：所有支持板子使用相同接口(busanio)
- **大量驱动库**：Adafruit维护的传感器/显示器驱动库
- **Bundle机制**：方便安装驱动库

**CircuitPython基本用法：**

```python
# code.py - CircuitPython入口文件（不是main.py）
import board
import digitalio
import time

# LED控制
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

while True:
    led.value = not led.value
    time.sleep(0.5)

# 按键输入
button = digitalio.DigitalInOut(board.BUTTON)
button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

while True:
    if not button.value:  # 按下时为False
        print("Button pressed!")
    time.sleep(0.1)
```

### 10.2 busanio统一接口

```python
# CircuitPython使用busanio作为统一硬件抽象层
import board
import busio
import digitalio

# I2C（统一接口）
i2c = busio.I2C(board.SCL, board.SDA)
while not i2c.try_lock():
    pass
devices = i2c.scan()
print(f"I2C devices: {[hex(d) for d in devices]}")
i2c.unlock()

# SPI
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)
cs.direction = digitalio.Direction.OUTPUT

# UART
uart = busio.UART(board.TX, board.RX, baudrate=115200)
uart.write(b"Hello\r\n")
data = uart.read(32)
```

**CircuitPython传感器示例：**

```python
import board
import busio
import adafruit_bme280.advanced as adafruit_bme280

# 初始化I2C和传感器
i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)

# 配置传感器
bme280.mode = adafruit_bme280.MODE_NORMAL
bme280.standby_period = adafruit_bme280.STANDBY_TC_500
bme280.iir_filter = adafruit_bme280.IIR_FILTER_X16
bme280.overscan_pressure = adafruit_bme280.OVERSCAN_X16
bme280.overscan_humidity = adafruit_bme280.OVERSCAN_X1
bme280.overscan_temperature = adafruit_bme280.OVERSCAN_X2

while True:
    print(f"Temperature: {bme280.temperature:.1f} C")
    print(f"Humidity: {bme280.relative_humidity:.1f} %")
    print(f"Pressure: {bme280.pressure:.1f} hPa")
    time.sleep(2)
```

### 10.3 MicroPython vs CircuitPython对比

| 对比项 | MicroPython | CircuitPython |
|--------|-------------|---------------|
| 维护者 | Damien George | Adafruit Industries |
| 入口文件 | `main.py` | `code.py` |
| 系统文件 | `boot.py` | 无（使用`settings.toml`） |
| 代码部署 | 串口/WebREPL/IDE | USB U盘拖拽 |
| 硬件抽象 | `machine`模块 | `board`/`digitalio`/`analogio` |
| 支持平台 | ESP32/RP2040/STM32等 | Adafruit板为主 |
| 库管理 | upip手动安装 | Adafruit Bundle自动加载 |
| 在线编辑 | WebREPL | CircUp / Mu Editor |
| 社区 | 偏工程/嵌入式 | 偏教育/创客 |
| 性能 | 略快 | 略慢（额外抽象层） |
| USB功能 | USB HID/Serial | USB HID/Serial/MIDI/Mass Storage |
| BLE支持 | bluetooth模块 | adafruit_ble库 |
| 显示 | framebuf/LVGL | displayio |
| 音频 | 内置 | audiobusio/audiomp3 |
| 文件系统 | 内置小文件系统 | FAT USB大容量存储 |
| 双核支持 | ESP32可选 | ESP32-S3支持 |
| 更新频率 | 稳定，按需更新 | 频繁，每数周更新 |

### 10.4 Blinka兼容层

Blinka让CircuitPython库运行在Linux SBC(如Raspberry Pi)和MicroPython设备上。

**在Raspberry Pi上使用：**

```bash
# 安装Blinka
pip3 install Adafruit-Blinka

# 安装传感器库
pip3 install adafruit-circuitpython-bme280
pip3 install adafruit-circuitpython-ssd1306
```

```python
# 使用与CircuitPython相同的代码
import board
import busio
import adafruit_bme280

i2c = busio.I2C(board.SCL, board.SDA)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

print(f"Temperature: {bme280.temperature:.1f} C")
```

**Blinka在ESP32上的使用：**

```python
# 需要特殊固件支持Blinka
# 或使用 Adafruit CircuitPython on ESP32
import board
import digitalio

led = digitalio.DigitalInOut(board.IO2)
led.direction = digitalio.Direction.OUTPUT

while True:
    led.value = not led.value
    time.sleep(0.5)
```

---

## 十一、Python在嵌入式中的定位

### 11.1 原型验证 vs 产品开发

**原型验证阶段（推荐Python）：**

```
优势：
- 快速迭代：修改代码立即运行，无需编译
- 交互调试：REPL实时测试硬件
- 简洁语法：减少样板代码
- 丰富库：社区驱动可直接使用

典型场景：
- 传感器数据采集原型
- IoT概念验证(PoC)
- 教学演示
- Hackathon项目
- 硬件功能验证
```

**产品开发阶段（需要权衡）：**

```
需要考虑的因素：
- 性能瓶颈：高频数据采集、实时控制
- 内存限制：Flash/RAM不足
- 功耗要求：电池供电场景
- 确定性：实时性要求高的场景
- 认证要求：安全关键系统

Python仍适合的场景：
- 配网和配置界面（WebREPL/Web配置）
- OTA固件更新管理
- 数据预处理和边缘计算
- 人机交互界面（LVGL）
- 非实时的后台任务

不适合的场景：
- 电机FOC控制
- 高速ADC采样（>100kHz）
- 硬实时控制回路
- 飞控/导航系统
- 医疗/安全关键系统
```

### 11.2 性能优化

**纯Python优化：**

```python
# 优化1：避免频繁的内存分配
# 差
def read_sensor():
    data = {}  # 每次调用都创建新dict
    data["temp"] = adc.read()
    return data

# 好 - 复用对象
_sensor_data = {}
def read_sensor():
    _sensor_data["temp"] = adc.read()
    return _sensor_data

# 优化2：使用const()避免运行时查找
from micropython import const
LED_PIN = const(2)
BTN_PIN = const(0)
MAX_RETRY = const(3)
TIMEOUT_MS = const(5000)

# 优化3：使用@micropython.native装饰器（加速约2倍）
@micropython.native
def fast_function(x, y):
    return x * y + x // y

# 优化4：使用@micropython.viper装饰器（加速约10倍）
@micropython.viper
def very_fast_function(x: int, y: int) -> int:
    return x * y + x // y

# 优化5：使用@micropython.asm_thumb（ARM汇编，最大加速）
@micropython.asm_thumb
def asm_add(r0, r1):
    add(r0, r0, r1)

# 优化6：减少函数调用开销
# 差
for i in range(1000):
    result = math.sqrt(i)

# 好 - 内联计算
for i in range(1000):
    result = i ** 0.5

# 优化7：使用memoryview避免拷贝
buf = bytearray(256)
mv = memoryview(buf)
# 子切片不分配新内存
chunk = mv[10:20]
```

**内存优化：**

```python
import gc
import micropython

# 编译时优化：冻结模块（frozen modules）
# 在固件编译时将.py编译为.mpy并冻结到Flash中
# 优点：减少RAM占用，加快导入速度

# 使用 .mpy 文件替代 .py 文件
# 编译：mpy-cross my_module.py
# 将 my_module.mpy 放入 /lib/

# 使用 bytearray 替代 bytes（可复用内存）
# 使用 array.array 替代 list（数值类型更紧凑）
import array
values = array.array('f', [0.0] * 100)  # float32数组，比list节省内存
values = array.array('h', [0] * 100)     # int16数组

# 字符串驻留（intern）
import micropython
micropython.alloc_emergency_exception_buf(100)
```

### 11.3 C扩展模块

当Python性能不足时，可以用C编写扩展模块。

**C模块结构：**

```c
// mymodule.c - MicroPython C扩展模块示例
#include "py/dynruntime.h"

// 导出的C函数：快速数组求和
STATIC mp_obj_t fast_sum(mp_obj_t arr_in) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(arr_in, &bufinfo, MP_BUFFER_READ);

    int32_t *data = (int32_t *)bufinfo.buf;
    size_t len = bufinfo.len / sizeof(int32_t);

    int64_t sum = 0;
    for (size_t i = 0; i < len; i++) {
        sum += data[i];
    }

    return mp_obj_new_int(sum);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(fast_sum_obj, fast_sum);

// 模块定义
STATIC const mp_rom_map_elem_t mymodule_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mymodule) },
    { MP_ROM_QSTR(MP_QSTR_fast_sum), MP_ROM_PTR(&fast_sum_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mymodule_globals, mymodule_globals_table);

const mp_obj_module_t mymodule_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mymodule_globals,
};

MP_REGISTER_MODULE(MP_QSTR_mymodule, mymodule_cmodule);
```

**在MicroPython中使用C模块：**

```python
# 方法1：编译进固件（推荐生产环境）
# 将C文件加入micropython/ports/esp32/Makefile的SRC_C列表

# 方法2：动态加载（需要MICROPY_MODULE_BUILTIN_DYNAMIC）
import mymodule
result = mymodule.fast_sum(bytearray(b'\x01\x00\x00\x00\x02\x00\x00\x00'))
print(result)  # 3

# 方法3：使用MicroPython的FFI（Foreign Function Interface）
# 仅在Unix/Windows版本可用
import ffi
libc = ffi.open("libc.so.6")
sqrt = libc.func("d", "sqrt", "d")
print(sqrt(2.0))  # 1.41421...
```

---

## 十二、常见开发板

### 12.1 ESP32系列

**ESP32基础信息：**

| 型号 | CPU | RAM | Flash | WiFi | BLE | USB | 特点 |
|------|-----|-----|-------|------|-----|-----|------|
| ESP32 | 双核Xtensa 240MHz | 520KB | 4MB | WiFi4 | BLE4.2 | 无 | 经典款，外设丰富 |
| ESP32-S2 | 单核Xtensa 240MHz | 320KB | 4MB | WiFi4 | 无 | USB OTG | 低功耗，USB |
| ESP32-S3 | 双核Xtensa 240MHz | 512KB | 8MB | WiFi4 | BLE5.0 | USB OTG | AI加速，PSRAM |
| ESP32-C3 | 单核RISC-V 160MHz | 400KB | 4MB | WiFi4 | BLE5.0 | 无 | 超低成本 |
| ESP32-C6 | 单核RISC-V 160MHz | 512KB | 4MB | WiFi6 | BLE5.0 | 无 | WiFi6，Thread |
| ESP32-H2 | 单核RISC-V 96MHz | 320KB | 4MB | 无 | BLE5.0 | 无 | Zigbee/Thread |

**ESP32 MicroPython快速上手：**

```bash
# 1. 下载固件
# https://micropython.org/download/ESP32_GENERIC/

# 2. 烧录固件（使用esptool）
pip install esptool
esptool.py --chip esp32 --port COM3 erase_flash
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 firmware.bin

# 3. 连接REPL
# 使用Thonny IDE或picocom
picocom /dev/ttyUSB0 -b 115200
```

**ESP32特有功能：**

```python
import esp32

# 内置温度传感器
temp = esp32.raw_temperature()  # 华氏度

# Hall传感器（磁场强度）
hall = esp32.hall_sensor()

# NVS（非易失性存储）
import esp32
nvs = esp32.NVS("storage")
nvs.set_blob("key", b"hello")
buf = bytearray(5)
nvs.get_blob("key", buf)

# Deep Sleep唤醒配置
esp32.wake_on_ext0(Pin(4), esp32.WAKEUP_ANY_HIGH)
esp32.wake_on_ext1([Pin(2), Pin(15)], esp32.WAKEUP_ALL_LOW)

# ULP协处理器（超低功耗处理）
# 需要编写ULP汇编代码
```

### 12.2 Pyboard

**Pyboard规格：**

| 参数 | Pyboard v1.1 | Pyboard D (SF2W) |
|------|-------------|-------------------|
| MCU | STM32F405RG | STM32F722IE |
| CPU | Cortex-M4 168MHz | Cortex-M7 216MHz |
| RAM | 192KB + 4KB备份 | 256KB + 16KB备份 |
| Flash | 1MB | 2MB |
| 存储 | microSD | microSD + 2MB QSPI Flash |
| WiFi | 无 | 有(WL430L) |
| GPIO | 30 | 30 |
| ADC | 2x12bit | 2x12bit |
| DAC | 2x12bit | 2x12bit |
| USB | Micro USB | Micro USB |

**Pyboard特有功能：**

```python
import pyb

# 板载LED控制
led_red = pyb.LED(1)
led_green = pyb.LED(2)
led_yellow = pyb.LED(3)
led_blue = pyb.LED(4)

led_red.on()
led_red.off()
led_red.intensity(128)  # PWM调光（0-255）

# 加速度计
accel = pyb.Accel()
print(f"x={accel.x()}, y={accel.y()}, z={accel.z()}")

# 用户按钮
sw = pyb.Switch()
sw.callback(lambda: print("User switch pressed!"))

# 电源控制
pyb.standby()        # 进入待机模式
pyb.stop()           # 进入停止模式
pyb.info()           # 打印系统信息

# 内置RTC
rtc = pyb.RTC()
rtc.datetime((2026, 6, 21, 6, 12, 0, 0, 0))  # 设置时间
print(rtc.datetime())

# 音频播放
dac = pyb.DAC(1)
# 播放正弦波
import math
buf = bytearray(100)
for i in range(100):
    buf[i] = 128 + int(127 * math.sin(2 * math.pi * i / 100))
dac.write_timed(buf, pyb.Timer(6, freq=8000), mode=pyb.DAC.CIRCULAR)

# SD卡
sd = pyb.SD()
sd.power(True)  # 开启SD卡电源
```

### 12.3 Raspberry Pi Pico / RP2040

**Pico规格：**

| 参数 | Pico | Pico W | Pico 2 | Pico 2W |
|------|------|--------|--------|---------|
| MCU | RP2040 | RP2040 | RP2350 | RP2350 |
| CPU | Cortex-M0+ 133MHz | Cortex-M0+ 133MHz | Cortex-M33 150MHz | Cortex-M33 150MHz |
| RAM | 264KB | 264KB | 520KB | 520KB |
| Flash | 2MB | 2MB | 4MB | 4MB |
| GPIO | 26 | 26 | 26 | 26 |
| ADC | 3x12bit | 3x12bit | 4x12bit | 4x12bit |
| WiFi | 无 | CYW43439 | 无 | CYW43439 |
| BLE | 无 | BLE5.0 | 无 | BLE5.0 |
| PIO | 2x4状态机 | 2x4状态机 | 3x4状态机 | 3x4状态机 |
| USB | Micro USB | Micro USB | USB-C | USB-C |

**Pico MicroPython用法：**

```python
from machine import Pin, PWM, ADC, I2C, SPI, Timer, UART
import time

# GPIO
led = Pin(25, Pin.OUT)  # Pico板载LED
led.toggle()

# PWM
pwm = PWM(Pin(15))  # GP15
pwm.freq(1000)
pwm.duty_u16(32768)  # 50% (0-65535)

# ADC
adc = ADC(Pin(26))  # GP26 = ADC0
value = adc.read_u16()  # 0-65535

# 硬件I2C（两组I2C总线）
i2c0 = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
i2c1 = I2C(1, scl=Pin(7), sda=Pin(6), freq=400000)
print(i2c0.scan())

# 硬件SPI（两组SPI总线）
spi0 = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
spi1 = SPI(1, baudrate=10000000, sck=Pin(10), mosi=Pin(11), miso=Pin(12))

# UART
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))
```

**PIO（可编程IO）示例：**

```python
from machine import Pin
import rp2

# PIO程序：WS2812 LED驱动
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT,
             autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0) [T3 - 1]
    jmp(not_x, "do_zero")   .side(1) [T1 - 1]
    jmp("bitloop")           .side(1) [T2 - 1]
    label("do_zero")
    nop()                    .side(0) [T2 - 1]
    wrap()

# 创建PIO状态机
sm = rp2.StateMachine(0, ws2812, freq=8000000, sideset_base=Pin(16))
sm.active(1)

# 发送RGB数据
import array
# GRB格式，每色8位
colors = array.array("I", [0x00FF0000, 0x0000FF00, 0x000000FF])  # 红、绿、蓝
sm.write(colors)

# 更实用的WS2812类
class WS2812:
    def __init__(self, pin_num, num_leds):
        self.pin = Pin(pin_num)
        self.num_leds = num_leds
        self.leds = array.array("I", [0] * num_leds)
        self.sm = rp2.StateMachine(0, ws2812, freq=8000000,
                                    sideset_base=self.pin)
        self.sm.active(1)

    def set_pixel(self, n, r, g, b):
        """设置单个LED颜色"""
        if 0 <= n < self.num_leds:
            self.leds[n] = (g << 16) | (r << 8) | b

    def fill(self, r, g, b):
        """设置所有LED颜色"""
        color = (g << 16) | (r << 8) | b
        for i in range(self.num_leds):
            self.leds[i] = color

    def show(self):
        """刷新LED"""
        self.sm.write(self.leds)

    def rainbow(self, offset=0):
        """彩虹效果"""
        for i in range(self.num_leds):
            pos = (i + offset) % 256
            if pos < 85:
                self.set_pixel(i, 255 - pos * 3, pos * 3, 0)
            elif pos < 170:
                pos -= 85
                self.set_pixel(i, 0, 255 - pos * 3, pos * 3)
            else:
                pos -= 170
                self.set_pixel(i, pos * 3, 0, 255 - pos * 3)

# 使用示例
strip = WS2812(pin_num=16, num_leds=8)
strip.fill(255, 0, 0)  # 全红
strip.show()
```

### 12.4 开发板选型指南

**按应用场景选型：**

| 场景 | 推荐板 | 理由 |
|------|--------|------|
| IoT原型 | ESP32 | WiFi+BLE，性价比高 |
| 低功耗传感器 | ESP32-C3 | RISC-V低成本，BLE5 |
| USB项目 | ESP32-S3 | USB OTG，PSRAM |
| 教学入门 | Raspberry Pi Pico | 价格低，社区大 |
| 高级UI | ESP32-S3+PSRAM | 大RAM支持LVGL |
| 工业应用 | Pyboard D | STM32工业级 |
| BLE可穿戴 | ESP32-C3/nRF52840 | 超低功耗BLE |
| 音频处理 | ESP32-S3 | I2S接口丰富 |
| 多IO控制 | RP2040/Pico | PIO可编程IO |
| 学习MicroPython | Pyboard | 官方参考设计 |

**性能对比：**

| 开发板 | Dhrystone MIPS | 堆内存可用 | 启动时间 |
|--------|---------------|-----------|---------|
| ESP32 | ~600 | ~100KB | ~2s |
| ESP32-S3 | ~600 | ~300KB(PSRAM) | ~2s |
| RP2040/Pico | ~250 | ~190KB | ~1s |
| Pyboard v1.1 | ~400 | ~100KB | ~1s |
| Pyboard D | ~500 | ~120KB | ~1s |
| ESP32-C3 | ~350 | ~200KB | ~2s |

---

## 附录A：常用API速查表

### machine模块

```python
from machine import Pin, I2C, SPI, UART, ADC, PWM, Timer

# Pin
p = Pin(id, mode, pull, value)
p.value([x])  p.on()  p.off()  p.irq(handler, trigger)

# ADC
adc = ADC(Pin(n))
adc.read()         # 12bit (0-4095)
adc.read_u16()     # 16bit (0-65535) - RP2040
adc.atten(ADC.ATTN_11DB)  # 0-3.3V (ESP32)

# PWM
pwm = PWM(Pin(n), freq=1000, duty=512)
pwm.freq([f])  pwm.duty([d])  pwm.duty_u16([d])  pwm.deinit()

# Timer
t = Timer(id)
t.init(mode, period, callback)
t.deinit()

# I2C
i2c = I2C(id, scl, sda, freq)
i2c.scan()  i2c.readfrom(addr, n)  i2c.writeto(addr, data)
i2c.readfrom_mem(addr, memaddr, n)  i2c.writeto_mem(addr, memaddr, data)

# SPI
spi = SPI(id, baudrate, polarity, phase, sck, mosi, miso)
spi.read(n)  spi.write(data)  spi.readinto(buf)  spi.write_readinto(tx, rx)

# UART
uart = UART(id, baudrate, tx, rx, bits, parity, stop, rxbuf)
uart.read(n)  uart.readline()  uart.write(data)  uart.any()

# 系统
import machine
machine.freq([hz])   # CPU频率
machine.reset()       # 硬重启
machine.deepsleep(ms) # 深度睡眠
machine.unique_id()   # 唯一ID
machine.mem32[addr]   # 直接内存访问
```

### 网络模块

```python
import network

# WiFi Station
sta = network.WLAN(network.STA_IF)
sta.active(True/False)
sta.connect(ssid, password)
sta.disconnect()
sta.isconnected()
sta.ifconfig()         # (ip, subnet, gateway, dns)
sta.scan()             # 扫描热点
sta.status()           # 连接状态

# WiFi AP
ap = network.WLAN(network.AP_IF)
ap.active(True/False)
ap.config(essid, password, channel, authmode)

# MQTT
from umqtt.simple import MQTTClient
c = MQTTClient(id, server, port, user, password)
c.connect()  c.disconnect()  c.publish(topic, msg)
c.subscribe(topic)  c.set_callback(cb)  c.check_msg()  c.wait_msg()
```

### os/sys模块

```python
import os, sys

os.listdir([dir])     os.mkdir(dir)     os.remove(file)
os.rename(old, new)   os.stat(file)     os.mount(block, mountpoint)
os.umount(mountpoint) os.getcwd()       os.chdir(dir)

sys.platform          sys.version       sys.implementation
sys.path              sys.modules       sys.exit()
sys.print_exception(exc)
```

### 时间模块

```python
import time

time.time()           # Unix时间戳（秒）
time.localtime()      # 本地时间元组
time.mktime(tuple)    # 元组转时间戳
time.sleep(seconds)   sleep_ms(ms)  sleep_us(us)
time.ticks_ms()       ticks_us()  ticks_cpu()
time.ticks_diff(t1, t2)  # 计算时间差（处理溢出）
```

---

## 附录B：常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| REPL无响应 | 波特率不匹配/固件损坏 | 检查波特率115200，重新烧录 |
| 内存不足(MemoryError) | 对象泄漏/缓冲区过大 | gc.collect()，减小缓冲区 |
| import失败 | 文件路径错误/语法错误 | 检查sys.path，验证.py语法 |
| WiFi连不上 | SSID/密码错误/信号弱 | 检查配置，靠近路由器 |
| SPI设备不响应 | 接线错误/时序不对 | 检查MISO/MOSI/SCK/CS接线 |
| I2C扫描无设备 | 地址错误/上拉缺失 | 检查地址，加4.7K上拉电阻 |
| 定时器回调阻塞 | 回调中执行耗时操作 | 回调中只设标志位，主循环处理 |
| Deep Sleep不唤醒 | 唤醒源配置错误 | 检查EXT0/EXT1配置和引脚 |
| 文件系统损坏 | 异常断电 | 使用os.fsformat()格式化 |
| 代码不执行 | main.py不存在/语法错误 | 检查main.py，查看REPL错误信息 |
| WebREPL连不上 | 未启用/密码错误 | REPL中执行import webrepl; webrepl.start() |
| 安装库失败 | 网络问题/内存不足 | 手动下载.mpy文件放入/lib/ |

---

## 附录C：学习资源

**官方资源：**

- MicroPython官方文档：https://docs.micropython.org
- MicroPython GitHub：https://github.com/micropython/micropython
- CircuitPython文档：https://docs.circuitpython.org
- Adafruit Learn：https://learn.adafruit.com

**推荐开发工具：**

| 工具 | 平台 | 特点 |
|------|------|------|
| Thonny IDE | 全平台 | 内置MicroPython支持，适合初学者 |
| VS Code + Pymakr | 全平台 | 功能强大，代码补全 |
| Mu Editor | 全平台 | 简洁，同时支持MicroPython和CircuitPython |
| uPyCraft | 全平台 | 专用MicroPython IDE |
| WebREPL | 浏览器 | 无线调试 |

**推荐学习路径：**

1. 选择一块ESP32或Pico开发板
2. 烧录MicroPython固件
3. 通过Thonny连接REPL
4. 学习GPIO控制（LED、按键）
5. 学习I2C/SPI通信（传感器、显示屏）
6. 学习WiFi和MQTT（IoT联网）
7. 学习文件系统和配置管理
8. 学习低功耗模式
9. 了解CircuitPython生态
10. 探索LVGL图形界面

---

> **笔记创建时间**：2026-06-21
> **最后更新**：2026-06-21
