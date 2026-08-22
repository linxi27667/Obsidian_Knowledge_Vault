# FreeRTOS 互斥锁与任务通知

## 概述

FreeRTOS 多任务并发环境下，多个任务访问共享资源时需要互斥锁保护数据一致性；任务通知是轻量级的跨任务信号机制，比队列更高效。

## 核心概念

### 互斥锁（Mutex）

互斥锁保护的不是某个变量，而是**一段代码的执行权**——保证同一时刻只有一个任务能进入"锁住的代码段"。

| 概念 | 说明 |
|------|------|
| 本质 | 保护一段代码不被并发执行 |
| 锁住什么 | 代码段，不是变量本身 |
| 竞争 | 多个任务抢同一把锁，谁抢到谁执行 |
| 阻塞 | 没抢到的任务在 LOCK 处等待 |

### 外卖厨房比喻

- **共享变量** = 厨房白板（点菜单）
- **写任务（MQTT/传感器）** = 前台接单员（往白板写字）
- **读任务（控制）** = 厨师（看单做菜）
- **互斥锁** = 厨师拍照时挡住白板不让别人碰
- **快照** = 厨师拍完照片立刻让开，对着照片做菜

### 快照模式（锁内拷贝，锁外使用）

核心思路：**锁只保护"拷贝那一瞬间"，拷完就放锁，其他任务几乎不用等。**

```c
// ====== 有快照（推荐）======
DEVICE_FLAGS_LOCK();
flags_snapshot = g_device_flags;    // 几微秒，拷贝一份
DEVICE_FLAGS_UNLOCK();              // 立刻释放锁！

// 以下不占锁，用局部副本慢慢操作硬件
HW_Gpio_Write(g_light_gpios[0], flags_snapshot.light[0]);
HW_Gpio_Write(g_relay_gpios[0], flags_snapshot.relay[0]);
HW_Servo_Set_Angle(g_servo_channels[0], flags_snapshot.servo[0]);
```

```c
// ====== 没快照（不推荐）======
DEVICE_FLAGS_LOCK();
// 以下全部持锁，其他任务被阻塞
HW_Gpio_Write(g_light_gpios[0], g_device_flags.light[0]);   // 慢
HW_Gpio_Write(g_relay_gpios[0], g_device_flags.relay[0]);   // 慢
HW_Servo_Set_Angle(...);                                      // 慢
DEVICE_FLAGS_UNLOCK();
```

时间线对比：

```
【没快照】
控制任务: |==== LOCK:写GPIO+舵机+能耗 (几ms) ====|  UNLOCK
MQTT任务:                    | 等...等...等... | 拿到锁 | 改状态 | UNLOCK

【有快照】
控制任务: |LOCK| 拷贝 | UNLOCK | 写GPIO+舵机+能耗（不占锁）
MQTT任务:       | 等1微秒 | 拿到锁 | 改状态 | UNLOCK
```

### 宏定义技巧

```c
#define DEVICE_FLAGS_LOCK()   do { if (!Iot_Device_Flags_Lock(__func__)) { return; } } while(0)
#define DEVICE_FLAGS_UNLOCK() do { Iot_Device_Flags_Unlock(__func__); } while(0)
```

注意 LOCK 失败时直接 `return`，不会继续往下执行，是一种防御性写法。

## 任务通知（Task Notification）

比队列更轻量的跨任务发信号方式。

### 发送端

```c
xTaskNotify(s_iot_ctrl_task_handle,  // 目标任务句柄
            NOTIFY_RAIN_BIT,         // 要设置的 bit
            eSetBits);               // 操作方式：按位或
```

| 参数 | 含义 |
|------|------|
| 目标任务句柄 | 给哪个任务发信号 |
| 通知值 | 一个 bit 标志位 |
| eSetBits | 按位或，不覆盖之前的通知 |

`eSetBits` 的效果：

```
已有 FIRE:   0b0001
或上 RAIN:   0b0010
结果:        0b0011  (两个事件都在，互不覆盖)
```

### 接收端

```c
uint32_t notified_bits = 0;
xTaskNotifyWait(0, NOTIFY_HELP_BIT | NOTIFY_RAIN_BIT, &notified_bits, 0);

if (notified_bits & NOTIFY_HELP_BIT) {
    Iot_Help_Emergency_Response();
}
if (notified_bits & NOTIFY_RAIN_BIT) {
    Iot_Rain_Alert_Response();
}
```

### Bit 标志位定义

```c
#define NOTIFY_RAIN_BIT   (1UL << 1)   // bit1 = 0x02
#define NOTIFY_FIRE_BIT   (1UL << 2)   // bit2 = 0x04
```

`1UL << n` 表示将数字 1 左移 n 位，每个事件占一个独立 bit，互不冲突。`UL` 表示 unsigned long，避免 32 位移位时的符号问题。

## 实践要点

| 要点 | 说明 |
|------|------|
| 锁的粒度 | 锁的时间越短越好，只保护拷贝操作 |
| 快照模式 | 锁内拷贝、锁外使用，是 ESP32 嵌入式常见模式 |
| 任务通知 vs 队列 | 只发信号用通知（更轻量），传数据用队列 |
| LOCK 宏加 return | 锁获取失败直接返回，防止后续代码在无锁状态下执行 |
| eSetBits | 按位或，多个事件可以同时存在不互相覆盖 |

## 相关文件索引

| 文件 | 作用 |
|------|------|
| `slave/gardenslave/main/APP/Src/iot_control_task.c` | 控制任务，快照读取 + 硬件驱动 |
| `slave/gardenslave/main/APP/Src/mqtt_receive.c` | MQTT 任务，接收命令写 g_device_flags |
| `slave/gardenslave/main/APP/Src/sensor_adc_task.c` | 传感器任务，自动逻辑写 g_device_flags |
| `slave/gardenslave/main/APP/Inc/iot_control_task.h` | 锁宏定义、任务通知 bit 定义 |

## 学习日期

2026-06-24

## 项目背景

智慧花园 ESP32 从设备（gardenslave）中，三个 FreeRTOS 任务（MQTT、传感器、控制）通过同一把互斥锁保护共享变量 `g_device_flags`（包含灯、继电器、舵机、火灾状态等设备状态），采用快照模式实现低延迟并发访问。
