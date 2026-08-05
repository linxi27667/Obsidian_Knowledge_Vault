# FreeRTOS 快照模式与双核调度

## 快照模式（锁内拷贝，锁外使用）

核心思路：**锁只保护"拷贝那一瞬间"，拷完就放锁，其他任务几乎不用等。**

### 外卖厨房比喻

- **g_device_flags** = 厨房白板（点菜单）
- **写任务（MQTT/传感器）** = 前台接单员（往白板写字）
- **读任务（控制）** = 厨师（看单做菜）
- **互斥锁** = 厨师拍照时挡住白板不让别人碰
- **快照** = 厨师拍完照片立刻让开，对着照片做菜

### 代码对比

```c
// ====== 有快照（推荐）======
DEVICE_FLAGS_LOCK();
flags_snapshot = g_device_flags;    // 几微秒
DEVICE_FLAGS_UNLOCK();              // 立刻释放！

// 不占锁，用副本慢慢操作硬件
HW_Gpio_Write(g_light_gpios[0], flags_snapshot.light[0]);
HW_Servo_Set_Angle(...);
```

```c
// ====== 没快照（不推荐）======
DEVICE_FLAGS_LOCK();
// 全部持锁，其他任务被阻塞
HW_Gpio_Write(g_light_gpios[0], g_device_flags.light[0]);  // 慢
HW_Servo_Set_Angle(...);                                     // 慢
DEVICE_FLAGS_UNLOCK();
```

### 时间线

```
【没快照】
控制任务: |==== LOCK:写硬件 (几ms) ====|  UNLOCK
MQTT任务:              | 等...等... | 拿到锁 | 改状态

【有快照】
控制任务: |LOCK| 拷贝 | UNLOCK | 写硬件（不占锁）
MQTT任务:     | 等1μs | 拿到锁 | 改状态
```

## xTaskCreatePinnedToCore（绑核）

ESP32 有双核（Core 0 和 Core 1），`xTaskCreatePinnedToCore` 最后一个参数指定绑到哪个核。

```c
xTaskCreatePinnedToCore(
    Sensor_ADC_Task,   // 任务函数
    "Sensor_ADC",      // 名字
    4096,              // 栈大小
    NULL,              // 参数
    4,                 // 优先级
    NULL,              // 任务句柄
    1                  // ← 绑定到 Core 1
);
```

### 为什么绑核

```
Core 0 ─── WiFi、蓝牙协议栈、MQTT 任务、控制任务、心跳任务
Core 1 ─── 传感器任务（独占）
```

传感器任务对时序敏感（ADC 采样、DHT11 读取），绑到 Core 1 避免被 WiFi/蓝牙抢占。

普通 `xTaskCreate` 不绑核，系统自由调度，任务可能在两核间跳来跳去。

## 学习日期

2026-06-24
