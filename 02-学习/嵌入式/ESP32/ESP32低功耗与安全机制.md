# ESP32 低功耗与安全机制

> ESP32 的低功耗模式和安全特性是其在 IoT 领域广泛应用的核心竞争力。本文系统梳理各功耗模式、ULP 协处理器、电源管理策略以及 Secure Boot / Flash Encryption 安全机制。

---

## 目录

1. [[#1. 各模式功耗概览]]
2. [[#2. Light Sleep 模式]]
3. [[#3. Deep Sleep 模式]]
4. [[#4. Hibernation 模式]]
5. [[#5. ULP 协处理器]]
6. [[#6. 电源管理最佳实践]]
7. [[#7. Secure Boot V2]]
8. [[#8. Flash Encryption]]
9. [[#9. 低功耗设计案例]]
10. [[#10. 功耗测量方法]]

---

## 1. 各模式功耗概览

ESP32 提供多种功耗模式，从全速运行到深度休眠，适应不同场景需求。

### 1.1 功耗模式对比表

| 模式 | 典型功耗 | CPU 状态 | WiFi/BT | RTC | 唤醒延迟 |
|------|---------|----------|---------|-----|---------|
| **Active** | ~80 mA | 运行 | 开启 | 运行 | 无 |
| **Modem Sleep** | ~15 mA | 运行 | 关闭射频 | 运行 | 无 |
| **Light Sleep** | ~0.8 mA | 暂停 | 关闭 | 运行 | ~0.1 ms |
| **Deep Sleep** | ~10 uA | 关闭 | 关闭 | 运行 | ~0.5 ms |
| **Hibernation** | ~5 uA | 关闭 | 关闭 | 仅 RTC Timer | ~1 ms |

> [!note] 实际功耗
> 上述数值为典型值，实际功耗受外设、GPIO 状态、Flash 状态等因素影响。未正确配置的 GPIO 可能导致漏电，使 Deep Sleep 功耗远高于预期。

### 1.2 模式选择决策树

```
需要持续计算/通信？
├── 是 → Active 模式
│       不需要射频？
│       ├── 是 → Modem Sleep（自动进入）
│       └── 否 → 保持 Active
└── 否 → 可以暂停 CPU？
        ├── 是，需要快速恢复 → Light Sleep
        └── 否，可以长时间休眠？
                ├── 需要 RTC 外设 → Deep Sleep
                └── 仅需定时器 → Hibernation
```

### 1.3 Modem Sleep 详解

Modem Sleep 是 Active 模式的自动子模式。当 CPU 运行但不需要 WiFi/BT 时，射频模块自动关闭。

**触发条件：**
- WiFi 处于省电模式（PSM）
- 无 WiFi/BT 数据传输需求

**ESP-IDF 配置：**

```c
// WiFi 省电模式配置
esp_wifi_set_ps(WIFI_PS_MODEM);  // 启用 Modem Sleep
```

**WiFi 省电模式选项：**

| 模式 | 说明 | 功耗 |
|------|------|------|
| `WIFI_PS_NONE` | 不省电，射频常开 | ~80 mA |
| `WIFI_PS_MODEM` | DTIM 间隔关闭射频 | ~15 mA |
| `WIFI_PS_MIN_MODEM` | 最小化射频活动 | ~10 mA |

---

## 2. Light Sleep 模式

### 2.1 工作原理

Light Sleep 暂停 CPU 和大部分数字外设，但保持 RTC 外设和 RTC Memory 供电。唤醒后 CPU 从暂停点继续执行，**无需重新初始化**。

**电源域状态：**

| 电源域 | Light Sleep 状态 |
|--------|----------------|
| 数字核心 (VDD_CPU) | 关闭 |
| RTC 电源域 (VDD_RTC) | 保持 |
| Flash | 关闭（自动） |
| RTC Memory | 保持 |
| RTC 外设 | 保持 |

### 2.2 唤醒源配置

#### 2.2.1 GPIO 唤醒

```c
#include "esp_sleep.h"
#include "driver/gpio.h"

// 配置 GPIO 唤醒（任意高电平）
#define WAKEUP_GPIO_PIN  GPIO_NUM_0

void configure_gpio_wakeup(void)
{
    // 配置 GPIO 为输入
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << WAKEUP_GPIO_PIN),
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

    // 配置唤醒源：任意高电平唤醒
    esp_deep_sleep_enable_gpio_wakeup(
        (1ULL << WAKEUP_GPIO_PIN),
        ESP_GPIO_WAKEUP_GPIO_HIGH
    );
}
```

> [!warning] GPIO 唤醒限制
> Light Sleep 的 GPIO 唤醒仅支持 RTC GPIO（GPIO 0, 2, 4, 12-15, 25-27, 32-39）。普通 GPIO 不能作为 Deep Sleep/Light Sleep 唤醒源。

#### 2.2.2 定时器唤醒

```c
#include "esp_sleep.h"

void configure_timer_wakeup(uint64_t time_in_us)
{
    // 设置 RTC 定时器唤醒
    esp_sleep_enable_timer_wakeup(time_in_us);
    // 示例：5 秒后唤醒
    // esp_sleep_enable_timer_wakeup(5000000);
}
```

#### 2.2.3 UART 唤醒

```c
#include "esp_sleep.h"

void configure_uart_wakeup(void)
{
    // UART0 唤醒，阈值为 3 个字节的低电平时间
    esp_sleep_enable_uart_wakeup(UART_NUM_0);
    // 唤醒条件：RX 线上出现低脉冲（起始位）
}
```

#### 2.2.4 Touch 唤醒

```c
#include "esp_sleep.h"
#include "driver/touch_pad.h"

void configure_touch_wakeup(void)
{
    // 初始化 touch 子系统
    touch_pad_init();
    touch_pad_set_voltage(
        TOUCH_HVOLT_2V7,   // 高电压
        TOUCH_LVOLT_0V5,   // 低电压
        TOUCH_HVOLT_ATTEN_1V  // 衰减
    );

    // 配置 Touch Pad 0
    touch_pad_config(TOUCH_PAD_NUM0, 0);

    // 设置触摸阈值（需要根据实际硬件校准）
    touch_pad_set_thresh(TOUCH_PAD_NUM0, 400);

    // 启用触摸唤醒
    esp_sleep_enable_touchpad_wakeup();
}
```

### 2.3 Light Sleep 完整示例

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "driver/gpio.h"

static const char *TAG = "light_sleep";

#define WAKEUP_PIN      GPIO_NUM_0
#define SLEEP_DURATION  10000000  // 10 秒

void app_main(void)
{
    // 检查唤醒原因
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

    switch (cause) {
        case ESP_SLEEP_WAKEUP_GPIO:
            ESP_LOGI(TAG, "GPIO 唤醒");
            break;
        case ESP_SLEEP_WAKEUP_TIMER:
            ESP_LOGI(TAG, "定时器唤醒");
            break;
        case ESP_SLEEP_WAKEUP_UART:
            ESP_LOGI(TAG, "UART 唤醒");
            break;
        case ESP_SLEEP_WAKEUP_TOUCHPAD:
            ESP_LOGI(TAG, "触摸唤醒");
            break;
        default:
            ESP_LOGI(TAG, "首次运行或非唤醒启动");
            break;
    }

    // 配置唤醒源
    // GPIO 唤醒
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << WAKEUP_PIN),
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&io_conf);

    // 定时器唤醒
    esp_sleep_enable_timer_wakeup(SLEEP_DURATION);

    // 执行业务逻辑
    ESP_LOGI(TAG, "开始工作...");
    vTaskDelay(pdMS_TO_TICKS(1000));
    ESP_LOGI(TAG, "进入 Light Sleep");

    // 进入 Light Sleep
    esp_light_sleep_start();

    // 唤醒后从此处继续执行
    ESP_LOGI(TAG, "已唤醒");
}
```

### 2.4 Light Sleep 注意事项

- **外设状态保持**：Light Sleep 暂停 CPU 但不复位外设，唤醒后外设寄存器值保持不变
- **Flash 电源**：默认关闭 Flash 电源，如需保持 Flash 可配置 `CONFIG_ESP_SLEEP_FLASH_LEAKAGE_WORKAROUND`
- **中断**：唤醒后不会丢失已挂起的中断
- **DMA**：正在进行的 DMA 传输会被中断，唤醒后需重新配置

---

## 3. Deep Sleep 模式

### 3.1 工作原理

Deep Sleep 关闭 CPU、数字核心和大部分 RTC 外设，仅保留 RTC 控制器、RTC 外设和 RTC Memory。唤醒后 CPU 从 Reset 向量重新启动，**所有 RAM 数据丢失**（RTC Memory 除外）。

**关键区别：Light Sleep vs Deep Sleep**

| 特性 | Light Sleep | Deep Sleep |
|------|------------|------------|
| CPU 恢复 | 继续执行 | 重新启动 |
| 内部 SRAM | 保持 | 丢失 |
| RTC Memory | 保持 | 保持 |
| 外设状态 | 保持 | 复位 |
| 功耗 | ~0.8 mA | ~10 uA |

### 3.2 EXT0 唤醒

EXT0 使用单个 RTC GPIO 唤醒，支持高/低电平触发。

```c
#include "esp_sleep.h"

// EXT0 唤醒：GPIO 33 高电平唤醒
void configure_ext0_wakeup(void)
{
    // 参数：gpio_num, level
    // GPIO 必须是 RTC GPIO
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, 1);  // 1 = 高电平
}
```

**EXT0 支持的 RTC GPIO：**

| GPIO | RTC GPIO 编号 |
|------|--------------|
| 0 | RTC_GPIO0 |
| 2 | RTC_GPIO2 |
| 4 | RTC_GPIO4 |
| 12 | RTC_GPIO12 |
| 13 | RTC_GPIO13 |
| 14 | RTC_GPIO14 |
| 15 | RTC_GPIO15 |
| 25 | RTC_GPIO6 |
| 26 | RTC_GPIO7 |
| 27 | RTC_GPIO8 |
| 32 | RTC_GPIO9 |
| 33 | RTC_GPIO10 |
| 34 | RTC_GPIO11 |
| 35 | RTC_GPIO12 |
| 36 | RTC_GPIO13 |
| 37 | RTC_GPIO14 |
| 38 | RTC_GPIO15 |
| 39 | RTC_GPIO16 |

### 3.3 EXT1 唤醒

EXT1 支持多个 RTC GPIO 组合唤醒，支持任意高电平或任意低电平。

```c
#include "esp_sleep.h"

// EXT1 唤醒：GPIO 33 和 GPIO 34 任意高电平唤醒
void configure_ext1_wakeup(void)
{
    // 创建 GPIO 掩码
    uint64_t pin_mask = (1ULL << GPIO_NUM_33) | (1ULL << GPIO_NUM_34);

    // 参数：mask, level
    // ESP_EXT1_WAKEUP_ANY_HIGH - 任意高电平
    // ESP_EXT1_WAKEUP_ALL_LOW  - 全部低电平
    esp_sleep_enable_ext1_wakeup(pin_mask, ESP_EXT1_WAKEUP_ANY_HIGH);
}
```

> [!tip] EXT0 vs EXT1
> - **EXT0**：单引脚唤醒，可精确控制触发电平（高/低），功耗略低
> - **EXT1**：多引脚唤醒，仅支持"任意高"或"全部低"逻辑，灵活性更高
> - 两者不能同时使用

### 3.4 RTC Memory 用法

RTC Memory 在 Deep Sleep 期间保持数据，可用于保存状态信息。

```c
#include "esp_sleep.h"
#include <string.h>

// RTC Slow Memory 变量声明
// 使用 RTC_DATA_ATTR 宏将变量放入 RTC Memory
RTC_DATA_ATTR static int boot_count = 0;
RTC_DATA_ATTR static char last_state[64] = {0};

// RTC Memory 布局：
// - RTC_SLOW_MEM: 8 KB，用于用户数据
// - RTC_FAST_MEM: 8 KB，通常用于 ULP 协处理器

void app_main(void)
{
    boot_count++;
    printf("启动次数: %d\n", boot_count);

    if (boot_count == 1) {
        strcpy(last_state, "首次启动");
    } else {
        printf("上次状态: %s\n", last_state);
        strcpy(last_state, "从 Deep Sleep 恢复");
    }

    // 配置唤醒源并进入 Deep Sleep
    esp_sleep_enable_timer_wakeup(5000000);  // 5 秒
    esp_deep_sleep_start();
}
```

**RTC Memory 大小限制：**

| 区域 | 大小 | 用途 |
|------|------|------|
| RTC Slow Memory | 8 KB | 用户变量、ULP 程序 |
| RTC Fast Memory | 8 KB | ULP 指令/数据 |
| RTC DATA_ATTR | 共享 8KB Slow | C 变量持久化 |

> [!warning] RTC Memory 注意事项
> - RTC Memory 不是掉电保持的（与 Flash 不同），仅在 Deep Sleep 期间保持
> - 如果发生硬件复位（如看门狗），RTC Memory 内容可能丢失
> - 变量初始化只在冷启动时执行，Deep Sleep 唤醒不会重新初始化 `RTC_DATA_ATTR` 变量

### 3.5 状态保存到 NVS

对于需要长期保存的状态，应使用 NVS（Non-Volatile Storage）。

```c
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_sleep.h"

void save_state_to_nvs(int value)
{
    nvs_handle_t handle;
    esp_err_t err;

    err = nvs_open("storage", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        printf("NVS 打开失败: %s\n", esp_err_to_name(err));
        return;
    }

    err = nvs_set_i32(handle, "sensor_val", value);
    if (err == ESP_OK) {
        nvs_commit(handle);  // 必须提交
    }

    nvs_close(handle);
}

int load_state_from_nvs(void)
{
    nvs_handle_t handle;
    int32_t value = 0;

    esp_err_t err = nvs_open("storage", NVS_READONLY, &handle);
    if (err != ESP_OK) {
        return -1;
    }

    err = nvs_get_i32(handle, "sensor_val", &value);
    nvs_close(handle);

    return (err == ESP_OK) ? value : -1;
}

void app_main(void)
{
    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    int saved = load_state_from_nvs();
    printf("NVS 中保存的值: %d\n", saved);

    // 保存新状态
    save_state_to_nvs(42);

    // 进入 Deep Sleep
    esp_sleep_enable_timer_wakeup(10000000);
    esp_deep_sleep_start();
}
```

### 3.6 Deep Sleep 完整示例

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/rtc_io.h"
#include "nvs_flash.h"
#include "nvs.h"

static const char *TAG = "deep_sleep";

#define BUTTON_PIN      GPIO_NUM_33
#define LED_PIN         GPIO_NUM_2
#define SLEEP_TIME_SEC  30

// RTC Memory 持久变量
RTC_DATA_ATTR static uint32_t wakeup_count = 0;

// 配置 EXT1 唤醒
static void configure_wakeup_sources(void)
{
    // 方式 1：定时器唤醒
    esp_sleep_enable_timer_wakeup(SLEEP_TIME_SEC * 1000000ULL);

    // 方式 2：EXT0 唤醒（按钮，低电平）
    // esp_sleep_enable_ext0_wakeup(BUTTON_PIN, 0);

    // 方式 3：EXT1 唤醒（多引脚）
    uint64_t pin_mask = (1ULL << BUTTON_PIN);
    esp_sleep_enable_ext1_wakeup(pin_mask, ESP_EXT1_WAKEUP_ALL_LOW);
}

// 初始化 NVS
static void init_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
}

void app_main(void)
{
    init_nvs();

    // 递增启动计数
    wakeup_count++;
    ESP_LOGI(TAG, "第 %lu 次唤醒", wakeup_count);

    // 检查唤醒原因
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

    if (cause == ESP_SLEEP_WAKEUP_EXT1) {
        uint64_t wakeup_pin_mask = esp_sleep_get_ext1_wakeup_status();
        int pin = __builtin_ffsll(wakeup_pin_mask) - 1;
        ESP_LOGI(TAG, "EXT1 唤醒，GPIO %d", pin);
    } else if (cause == ESP_SLEEP_WAKEUP_EXT0) {
        ESP_LOGI(TAG, "EXT0 唤醒");
    } else if (cause == ESP_SLEEP_WAKEUP_TIMER) {
        ESP_LOGI(TAG, "定时器唤醒");
    } else {
        ESP_LOGI(TAG, "非 Deep Sleep 唤醒");
    }

    // 执行传感器读取等业务逻辑
    ESP_LOGI(TAG, "执行业务逻辑...");
    vTaskDelay(pdMS_TO_TICKS(100));

    // 配置唤醒源
    configure_wakeup_sources();

    // 确保 RTC GPIO 状态正确（防止漏电）
    rtc_gpio_isolate(GPIO_NUM_12);  // 如果不使用，隔离以降低功耗

    ESP_LOGI(TAG, "进入 Deep Sleep (%d 秒)", SLEEP_TIME_SEC);
    esp_deep_sleep_start();

    // 不会执行到这里
}
```

### 3.7 Deep Sleep 功耗优化要点

- **隔离未使用的 RTC GPIO**：调用 `rtc_gpio_isolate()` 防止浮空引脚漏电
- **关闭 RTC 外设**：不需要 touch/ADC 时关闭对应电源域
- **Flash 关闭**：Deep Sleep 时 Flash 自动进入掉电模式
- **WiFi/BT 断开**：进入 Deep Sleep 前确保已断开连接

---

## 4. Hibernation 模式

### 4.1 工作原理

Hibernation 是 ESP32 最低功耗模式，仅保留 RTC Timer 运行。RTC Memory 和 RTC 外设全部关闭。

**与 Deep Sleep 的区别：**

| 特性 | Deep Sleep | Hibernation |
|------|-----------|-------------|
| RTC Memory | 保持 | **丢失** |
| RTC 外设 | 保持 | **关闭** |
| Touch/ADC | 可用 | **不可用** |
| 功耗 | ~10 uA | ~5 uA |
| 唤醒源 | EXT0/EXT1/Timer | **仅 Timer** |

### 4.2 进入 Hibernation

```c
#include "esp_sleep.h"

void enter_hibernation(uint64_t sleep_time_us)
{
    // 仅设置定时器唤醒（唯一可用唤醒源）
    esp_sleep_enable_timer_wakeup(sleep_time_us);

    // 禁用所有不需要的 RTC 外设
    // 关闭 RTC 外设电源域（如果可用）

    // 进入 Deep Sleep，但不保持 RTC Memory
    // ESP-IDF 中通过配置实现 Hibernation
    // 方法：使用 esp_deep_sleep_start() 配合 rtc_gpio_isolate

    // 隔离所有 RTC GPIO（防止漏电和意外唤醒）
    for (int gpio = 0; gpio < 40; gpio++) {
        if (RTC_GPIO_IS_VALID_GPIO(gpio)) {
            rtc_gpio_isolate(gpio);
        }
    }

    esp_deep_sleep_start();
}
```

> [!info] Hibernation 配置
> 在 ESP-IDF 中，Hibernation 通过 `menuconfig` 配置：
> `Component config` -> `ESP32-specific` -> `Deep Sleep` -> `Enable Hibernation mode`

### 4.3 Hibernation 适用场景

- 长期部署的传感器节点（月/年级别）
- 仅需定时唤醒的设备
- 电池容量极小的设备
- 对唤醒延迟不敏感的场景

---

## 5. ULP 协处理器

### 5.1 ULP 架构概述

ESP32 内置超低功耗 (ULP) 协处理器，基于 RISC-V 架构（ESP32-S 系列）或专有 FSM（ESP32 原版）。ULP 在 Deep Sleep 期间独立运行，可执行 ADC 采样、GPIO 监测等任务，并唤醒主 CPU。

**ULP 核心特性：**

| 特性 | 参数 |
|------|------|
| 架构 | RISC-V（ESP32-S2/S3/C3/C6） |
| 时钟频率 | 8 MHz（RTC 时钟） |
| 可用内存 | 8 KB RTC Slow Memory |
| 指令集 | RV32IMC 子集 |
| 功耗 | ~150 uA（运行时） |
| 唤醒能力 | 可唤醒主 CPU |

### 5.2 ULP 内存布局

```
RTC Slow Memory (8 KB = 8192 bytes)
┌──────────────────────────────────┐
│  ULP 程序代码 (.text)            │  最大 512 条指令
│  (约 2 KB)                       │
├──────────────────────────────────┤
│  ULP 数据 (.data/.bss)           │  变量和常量
│  (约 2 KB)                       │
├──────────────────────────────────┤
│  RTC_DATA_ATTR 用户变量           │  共享区域
│  (约 4 KB)                       │
└──────────────────────────────────┘
```

### 5.3 ULP RISC-V 程序结构

ULP 程序使用 C 语言编写（ESP-IDF 支持），编译为 RISC-V 指令。

#### 5.3.1 项目结构

```
project/
├── main/
│   ├── CMakeLists.txt
│   └── main.c
└── components/
    └── ulp/
        ├── CMakeLists.txt
        └── ulp_main.c          # ULP 程序
```

#### 5.3.2 ULP C 程序示例

```c
// ulp_main.c - ULP 协处理器程序
#include <stdint.h>
#include <stdbool.h>
#include "ulp_riscv.h"
#include "ulp_riscv_utils.h"
#include "ulp_riscv_adc.h"
#include "hal/adc_ll.h"

// 全局变量（RTC Memory，主 CPU 可读取）
uint32_t adc_value = 0;
uint32_t wakeup_threshold = 2000;

// ULP 主循环（每 10ms 执行一次）
int main(void)
{
    // 读取 ADC（通道 0，衰减 11dB）
    ulp_riscv_adc_cfg_t cfg = {
        .adc_unit    = ADC_UNIT_1,
        .adc_channel = ADC_CHANNEL_0,
        .atten       = ADC_ATTEN_DB_11,
        .bit_width   = ADC_BITWIDTH_12,
    };

    ulp_riscv_adc_init(&cfg);
    uint32_t raw = ulp_riscv_adc_read(ADC_UNIT_1, ADC_CHANNEL_0);

    // 保存 ADC 值
    adc_value = raw;

    // 检查是否超过阈值
    if (raw > wakeup_threshold) {
        // 唤醒主 CPU
        ulp_riscv_wakeup_main_processor();
    }

    return 0;
}
```

#### 5.3.3 主 CPU 端代码

```c
// main.c - 主 CPU 程序
#include <stdio.h>
#include "esp_sleep.h"
#include "ulp_riscv.h"
#include "ulp_main.h"
#include "esp_log.h"

// 引用 ULP 变量
extern uint32_t adc_value;
extern uint32_t wakeup_threshold;

static const char *TAG = "main";

void app_main(void)
{
    // 检查唤醒原因
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

    if (cause == ESP_SLEEP_WAKEUP_ULP) {
        ESP_LOGI(TAG, "ULP 唤醒，ADC 值: %lu", adc_value);
    }

    // 加载 ULP 程序
    esp_err_t err = ulp_riscv_load_binary(
        ulp_main_bin_start,
        (const uint8_t *)&ulp_main_bin_end - (const uint8_t *)&ulp_main_bin_start
    );

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "ULP 加载失败: %s", esp_err_to_name(err));
        return;
    }

    // 设置唤醒阈值
    wakeup_threshold = 2000;

    // 启动 ULP
    ulp_riscv_run();

    // 进入 Deep Sleep，ULP 继续运行
    ESP_LOGI(TAG, "进入 Deep Sleep，ULP 运行中");
    esp_deep_sleep_start();
}
```

#### 5.3.4 CMakeLists.txt 配置

```cmake
# components/ulp/CMakeLists.txt
ulp_embed_binary(ulp_main ulp_main.c "")
```

### 5.4 ULP GPIO 监测

```c
// ulp_main.c - GPIO 监测
#include <stdint.h>
#include "ulp_riscv.h"
#include "ulp_riscv_gpio.h"

// 监测 GPIO 4 的状态变化
#define MONITOR_GPIO  4

uint32_t gpio_state = 0;
uint32_t change_count = 0;

int main(void)
{
    // 读取 GPIO 状态
    uint32_t current = ulp_riscv_gpio_get_level(MONITOR_GPIO);

    // 检测边沿变化
    if (current != gpio_state) {
        change_count++;
        gpio_state = current;

        // 检测到上升沿，唤醒主 CPU
        if (current == 1) {
            ulp_riscv_wakeup_main_processor();
        }
    }

    return 0;
}
```

### 5.5 ULP ADC 连续采样

```c
// ulp_main.c - 连续 ADC 采样并计算平均值
#include <stdint.h>
#include "ulp_riscv.h"
#include "ulp_riscv_adc.h"

#define SAMPLE_COUNT  16

uint32_t adc_sum = 0;
uint32_t adc_avg = 0;
uint32_t sample_index = 0;

int main(void)
{
    // 读取 ADC
    uint32_t raw = ulp_riscv_adc_read(ADC_UNIT_1, ADC_CHANNEL_0);

    adc_sum += raw;
    sample_index++;

    // 每 16 次采样计算一次平均值
    if (sample_index >= SAMPLE_COUNT) {
        adc_avg = adc_sum / SAMPLE_COUNT;
        adc_sum = 0;
        sample_index = 0;

        // 检查阈值
        if (adc_avg > 2000) {
            ulp_riscv_wakeup_main_processor();
        }
    }

    return 0;
}
```

### 5.6 ULP 开发注意事项

- **内存限制**：程序 + 数据总共 8 KB，需精简代码
- **无浮点运算**：ULP 不支持硬件浮点，使用整数运算
- **无中断**：ULP 是轮询式执行，不支持中断
- **调试困难**：无法使用 GDB 调试，依赖 RTC Memory 变量输出调试信息
- **时钟精度**：使用 RTC 8M 振荡器，精度约 ±5%

---

## 6. 电源管理最佳实践

### 6.1 硬件层面

#### 6.1.1 外设电源控制

```c
#include "driver/gpio.h"

// 使用 GPIO 控制外设电源（MOS 开关）
#define SENSOR_POWER_PIN  GPIO_NUM_25

void sensor_power_on(void)
{
    gpio_set_direction(SENSOR_POWER_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(SENSOR_POWER_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(10));  // 等待电源稳定
}

void sensor_power_off(void)
{
    gpio_set_level(SENSOR_POWER_PIN, 0);
}

// 传感器读取流程
void read_sensor(void)
{
    sensor_power_on();
    // ... 读取传感器数据 ...
    sensor_power_off();
}
```

#### 6.1.2 电源开关电路设计

**P-MOS 开关电路：**

```
VCC ──┤S
       MOSFET (P-MOS)
GPIO ──┤G    ├─── 外设 VCC
       │D────┘
       │
       R (100K) ── GND
```

**设计要点：**
- 使用 P-MOS 做高边开关，GPIO 控制栅极
- 添加下拉电阻确保默认关闭
- 大电流外设使用专用电源管理 IC

#### 6.1.3 未使用引脚处理

```c
// 将未使用的引脚配置为输出低电平，防止浮空漏电
void configure_unused_pins(void)
{
    const gpio_num_t unused_pins[] = {
        GPIO_NUM_1, GPIO_NUM_3, GPIO_NUM_5,
        GPIO_NUM_6, GPIO_NUM_7, GPIO_NUM_8,
        GPIO_NUM_9, GPIO_NUM_10, GPIO_NUM_11,
        // ... 根据实际硬件配置
    };

    for (int i = 0; i < sizeof(unused_pins)/sizeof(unused_pins[0]); i++) {
        gpio_set_direction(unused_pins[i], GPIO_MODE_OUTPUT);
        gpio_set_level(unused_pins[i], 0);
    }
}
```

### 6.2 软件层面

#### 6.2.1 WiFi 省电策略

```c
#include "esp_wifi.h"

// WiFi 省电配置
void configure_wifi_power_save(void)
{
    // 1. 启用 Modem Sleep
    esp_wifi_set_ps(WIFI_PS_MODEM);

    // 2. 减少 WiFi 扫描频率
    wifi_scan_config_t scan_config = {
        .scan_type = WIFI_SCAN_TYPE_PASSIVE,
        .scan_time = {
            .passive = 100,  // 每通道 100ms
        },
    };

    // 3. 配置 DTIM 间隔
    // 在 menuconfig 中设置:
    // WiFi -> WiFi DTIM interval (1-10)
}
```

#### 6.2.2 批量数据发送

```c
#include "esp_wifi.h"
#include "mqtt_client.h"

// 批量发送策略：缓存数据，定时批量上传
#define BUFFER_SIZE     32
#define SEND_INTERVAL   60000  // 60 秒

typedef struct {
    float temperature;
    float humidity;
    uint32_t timestamp;
} sensor_data_t;

static sensor_data_t data_buffer[BUFFER_SIZE];
static int buffer_index = 0;

void collect_data(float temp, float humidity)
{
    if (buffer_index < BUFFER_SIZE) {
        data_buffer[buffer_index].temperature = temp;
        data_buffer[buffer_index].humidity = humidity;
        data_buffer[buffer_index].timestamp = (uint32_t)time(NULL);
        buffer_index++;
    }
}

void flush_data(void)
{
    if (buffer_index == 0) return;

    // 唤醒 WiFi
    esp_wifi_start();
    esp_wifi_set_ps(WIFI_PS_NONE);

    // 批量发送
    for (int i = 0; i < buffer_index; i++) {
        char payload[128];
        snprintf(payload, sizeof(payload),
                 "{\"temp\":%.1f,\"hum\":%.1f,\"ts\":%lu}",
                 data_buffer[i].temperature,
                 data_buffer[i].humidity,
                 data_buffer[i].timestamp);
        // mqtt_publish(...);
    }

    // 关闭 WiFi
    esp_wifi_stop();
    buffer_index = 0;
}
```

#### 6.2.3 DFS（动态频率调节）

```c
#include "esp_pm.h"

// 动态频率调节配置
void configure_dfs(void)
{
    // 配置电源管理策略
    esp_pm_config_t pm_config = {
        .max_freq_mhz = 240,      // 最大频率
        .min_freq_mhz = 40,       // 最小频率
        .light_sleep_enable = true, // 自动 Light Sleep
    };

    esp_pm_configure(&pm_config);

    // CPU 负载低时自动降频
    // 无任务时自动进入 Light Sleep
}
```

### 6.3 综合功耗优化检查清单

- [ ] WiFi 使用 PS 模式，非必要不常开
- [ ] 批量发送数据，减少射频开启次数
- [ ] 未使用的 GPIO 配置为输出低电平
- [ ] 外设使用电源开关，不用时断电
- [ ] 使用 DFS 动态调整 CPU 频率
- [ ] Flash 使用 DIO 模式（比 QIO 功耗低）
- [ ] 关闭未使用的日志输出（减少 UART 活动）
- [ ] 使用 Hibernation 替代 Deep Sleep（如不需要 RTC Memory）
- [ ] ULP 替代频繁唤醒主 CPU
- [ ] PCB 布局注意漏电路径（特别是高阻抗传感器）

---

## 7. Secure Boot V2

### 7.1 概述

Secure Boot V2 使用 RSA-3072 签名验证固件完整性，防止未授权代码执行。每颗芯片的 eFuse 中烧写唯一密钥摘要，启动时验证固件签名。

**Secure Boot V2 启动流程：**

```
ROM Boot
    │
    ├── 读取 eFuse 中的 Secure Boot 公钥摘要 (SHA-256)
    │
    ├── 加载 bootloader 到 IRAM
    │
    ├── 验证 bootloader 签名
    │   ├── 提取 bootloader 中的 RSA 签名
    │   ├── 计算 bootloader 哈希
    │   └── 用公钥验证签名
    │
    ├── 验证通过 → 执行 bootloader
    │
    └── 验证失败 → 停止启动（永久性）
```

### 7.2 Secure Boot V2 配置

#### 7.2.1 menuconfig 配置

```
Security features →
    [*] Enable hardware Secure Boot in development mode
        ( ) Release mode (recommended for production)
        (X) Development mode (not for production)
    [*] Sign binaries during build
    [*] Verify app signature on update (OTA)
```

#### 7.2.2 生成签名密钥

```bash
# 生成 RSA-3072 私钥（用于签名）
espsecure.py generate_signing_key --version 2 secure-boot-signing-key.pem

# 验证密钥
espsecure.py verify_signature --version 2 \
    --keyfile secure-boot-signing-key.pem bootloader.bin
```

### 7.3 eFuse 烧写

```bash
# 1. 先烧写 Secure Boot 公钥摘要
espefuse.py --port COM3 burn_key secure_boot \
    secure-boot-signing-key.pem SECURE_BOOT_DIGEST0

# 2. 启用 Secure Boot（不可逆！）
espefuse.py --port COM3 burn_efuse SECURE_BOOT_EN

# 3. 验证 eFuse 状态
espefuse.py --port COM3 summary
```

> [!danger] eFuse 烧写不可逆
> Secure Boot eFuse 一旦烧写**无法撤销**。请在开发阶段充分测试后再烧写到生产芯片。建议使用开发板验证全流程后再操作目标设备。

### 7.4 密钥管理最佳实践

- **私钥安全存储**：签名私钥不应存储在开发机器上，使用 HSM 或安全服务器
- **密钥轮换**：Secure Boot V2 支持最多 3 个密钥槽（eFuse 密钥 0/1/2）
- **开发/生产分离**：开发阶段使用 Development 模式，量产使用 Release 模式
- **密钥备份**：私钥丢失 = 无法更新固件 = 设备变砖

### 7.5 签名流程（CI/CD 集成）

```yaml
# .github/workflows/secure-build.yml 示例
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - name: Build firmware
        run: idf.py build
      - name: Sign firmware
        env:
          SIGNING_KEY: ${{ secrets.SECURE_BOOT_KEY }}
        run: |
          echo "$SIGNING_KEY" > key.pem
          espsecure.py sign_data --version 2 \
              --keyfile key.pem \
              --output signed.bin \
              build/project.bin
          rm key.pem
```

---

## 8. Flash Encryption

### 8.1 概述

Flash Encryption 使用 AES-256-XTS 加密整个 Flash 内容，防止固件被提取和逆向。密钥存储在 eFuse 中，无法被外部读取。

**加密算法：AES-256-XTS**
- 使用 256 位密钥（实际 512 位，XTS 模式需要两个 256 位密钥）
- 每个 Flash 扇区使用不同的 tweak 值
- 透明加密/解密，软件无需修改

### 8.2 开发模式 vs 生产模式

| 特性 | 开发模式 | 生产模式 |
|------|---------|---------|
| 加密密钥 | 可重新生成（调试用） | 烧写后不可变 |
| Flash 重写 | 可用 UART 重刷 | 仅通过 OTA |
| 适用场景 | 开发调试 | 量产部署 |
| 安全性 | 中 | 高 |

### 8.3 Flash Encryption 配置

#### 8.3.1 menuconfig 配置

```
Security features →
    [*] Enable Flash Encryption on Boot
        ( ) Development (NOT SECURE)
        (X) Release
    [*] Enable usage mode (USE)
    [*] Use pre-generated encryption key (测试用，生产环境应禁用)
```

#### 8.3.2 首次烧写流程

```bash
# 1. 编译固件
idf.py build

# 2. 烧写（首次，明文）
idf.py -p COM3 flash

# 3. 启用加密（烧写 eFuse）
espefuse.py --port COM3 burn_efuse SPI_BOOT_CRYPT_CNT

# 4. 重启后，ESP32 自动加密 Flash
# 后续烧写必须使用加密方式
```

### 8.4 OTA 加密流程

```c
#include "esp_ota_ops.h"
#include "esp_flash_encrypt.h"

// OTA 更新流程（加密环境）
void perform_encrypted_ota(const char *url)
{
    // 1. 配置 OTA 分区
    const esp_partition_t *update_partition =
        esp_ota_get_next_update_partition(NULL);

    // 2. 下载固件到 OTA 分区（数据自动加密写入 Flash）
    esp_ota_handle_t ota_handle;
    esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &ota_handle);

    // 3. 写入数据
    // ... 网络下载并写入 ...
    // esp_ota_write(ota_handle, data, len);

    // 4. 验证并切换
    esp_ota_end(ota_handle);
    esp_ota_set_boot_partition(update_partition);

    // 5. 重启
    esp_restart();
}
```

> [!important] OTA 注意事项
> - OTA 固件必须签名（配合 Secure Boot V2 使用）
> - 加密环境下的 OTA 使用 `esp_https_ota()` 自动处理签名验证
> - 确保 OTA 分区大小匹配

### 8.5 Flash Encryption 故障排除

```bash
# 检查加密状态
espefuse.py --port COM3 summary

# 如果 Flash 损坏需要重新烧写（仅开发模式）
# 1. 擦除 Flash
esptool.py --port COM3 erase_flash

# 2. 重新烧写
idf.py -p COM3 encrypted-flash

# 3. 检查加密状态
idf.py -p COM3 encrypted-flash --encrypt
```

---

## 9. 低功耗设计案例

### 9.1 案例一：电池供电传感器节点

**需求：**
- 温湿度采集，每 5 分钟上报一次
- 2 节 AA 电池（3000 mAh）供电
- 目标续航 1 年以上

**功耗预算：**

| 阶段 | 电流 | 时间 | 占比 |
|------|------|------|------|
| Deep Sleep | 10 uA | 299.5 s | 99.8% |
| 唤醒 + 采集 | 30 mA | 0.3 s | 0.1% |
| WiFi 连接 | 120 mA | 0.15 s | 0.05% |
| 数据发送 | 80 mA | 0.05 s | 0.02% |

**平均电流计算：**
```
I_avg = (10uA * 299.5 + 30mA * 0.3 + 120mA * 0.15 + 80mA * 0.05) / 300
      = (2995uA*s + 9000uA*s + 18000uA*s + 4000uA*s) / 300s
      = 33995uA*s / 300s
      = 113.3 uA
```

**续航估算：**
```
电池容量 = 3000 mAh
平均电流 = 0.113 mA
续航 = 3000 / 0.113 = 26548 小时 ≈ 3.03 年
```

**代码实现：**

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sleep.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "mqtt_client.h"
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "esp_log.h"

static const char *TAG = "sensor_node";

#define SENSOR_POWER_PIN    GPIO_NUM_25
#define REPORT_INTERVAL_S   300  // 5 分钟
#define WIFI_SSID           "your_ssid"
#define WIFI_PASS           "your_pass"
#define MQTT_BROKER         "mqtt://broker.example.com"

RTC_DATA_ATTR static uint32_t boot_count = 0;

// 传感器电源控制
static void sensor_power(bool on)
{
    gpio_set_direction(SENSOR_POWER_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(SENSOR_POWER_PIN, on ? 1 : 0);
    if (on) vTaskDelay(pdMS_TO_TICKS(10));
}

// 读取温湿度（I2C 传感器示例）
static void read_sensor(float *temp, float *humidity)
{
    sensor_power(true);
    // I2C 读取 SHT30/DHT22 等
    *temp = 25.5;       // 示例值
    *humidity = 60.2;   // 示例值
    sensor_power(false);
}

// WiFi 连接
static void wifi_connect(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
    esp_wifi_connect();

    // 等待连接（带超时）
    int timeout = 100;  // 10 秒
    while (timeout-- > 0) {
        wifi_ap_record_t ap;
        if (esp_wifi_sta_get_ap_info(&ap) == ESP_OK) {
            ESP_LOGI(TAG, "WiFi 已连接");
            return;
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    ESP_LOGW(TAG, "WiFi 连接超时");
}

// MQTT 发送
static void mqtt_send(float temp, float humidity)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = MQTT_BROKER,
    };

    esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_start(client);

    // 等待连接
    vTaskDelay(pdMS_TO_TICKS(1000));

    // 发送数据
    char payload[128];
    snprintf(payload, sizeof(payload),
             "{\"temp\":%.1f,\"hum\":%.1f,\"cnt\":%lu}",
             temp, humidity, boot_count);

    esp_mqtt_client_publish(client, "sensors/node1", payload, 0, 1, 0);
    vTaskDelay(pdMS_TO_TICKS(100));

    esp_mqtt_client_stop(client);
    esp_mqtt_client_destroy(client);
}

void app_main(void)
{
    boot_count++;
    ESP_LOGI(TAG, "启动 #%lu", boot_count);

    // 读取传感器
    float temp, humidity;
    read_sensor(&temp, &humidity);
    ESP_LOGI(TAG, "温度: %.1f, 湿度: %.1f", temp, humidity);

    // 连接 WiFi 并发送
    wifi_connect();
    mqtt_send(temp, humidity);

    // 断开 WiFi
    esp_wifi_stop();
    esp_wifi_deinit();

    // 进入 Deep Sleep
    ESP_LOGI(TAG, "进入 Deep Sleep (%d 秒)", REPORT_INTERVAL_S);
    esp_sleep_enable_timer_wakeup(REPORT_INTERVAL_S * 1000000ULL);
    esp_deep_sleep_start();
}
```

### 9.2 案例二：低功耗 WiFi 门铃

**需求：**
- 按钮触发拍照/通知
- 电池供电，续航 6 个月以上
- 响应延迟 < 1 秒

**设计方案：**

```
电池 ── ESP32 ── 按钮（EXT0 唤醒）
                 │
                 ├── WiFi 模块（按需开启）
                 │
                 └── 摄像头模块（按需供电）
```

**功耗模式选择：**

| 状态 | 模式 | 电流 | 时间 |
|------|------|------|------|
| 待机 | Deep Sleep (EXT0) | 10 uA | 99.99% |
| 按下 | Active + WiFi | 150 mA | 2-5 秒 |

**代码实现：**

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sleep.h"
#include "esp_wifi.h"
#include "esp_camera.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "doorbell";

#define BUTTON_PIN      GPIO_NUM_33  // RTC GPIO
#define CAMERA_PWR_PIN  GPIO_NUM_25
#define LED_PIN         GPIO_NUM_2

// 唤醒原因检查
void app_main(void)
{
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

    if (cause == ESP_SLEEP_WAKEUP_EXT0) {
        ESP_LOGI(TAG, "按钮按下！");

        // 点亮 LED
        gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
        gpio_set_level(LED_PIN, 1);

        // 给摄像头供电
        gpio_set_direction(CAMERA_PWR_PIN, GPIO_MODE_OUTPUT);
        gpio_set_level(CAMERA_PWR_PIN, 1);
        vTaskDelay(pdMS_TO_TICKS(100));  // 等待电源稳定

        // 初始化摄像头
        camera_config_t config = {
            .pin_pwdn  = -1,
            .pin_reset = -1,
            .pin_xclk  = 21,
            .pin_sscb_sda = 26,
            .pin_sscb_scl = 27,
            .pin_d7 = 36,
            .pin_d6 = 39,
            .pin_d5 = 34,
            .pin_d4 = 35,
            .pin_d3 = 32,
            .pin_d2 = 33,  // 注意与按钮引脚冲突，实际需调整
            .pin_d1 = 25,
            .pin_d0 = 12,
            .xclk_freq_hz = 20000000,
            .pixel_format = PIXFORMAT_JPEG,
            .frame_size = FRAMESIZE_VGA,
            .jpeg_quality = 12,
            .fb_count = 1,
        };

        esp_err_t err = esp_camera_init(&config);
        if (err == ESP_OK) {
            // 拍照
            camera_fb_t *fb = esp_camera_fb_get();
            if (fb) {
                ESP_LOGI(TAG, "拍照成功，大小: %zu", fb->len);
                // TODO: 通过 WiFi 发送图片
                esp_camera_fb_return(fb);
            }
            esp_camera_deinit();
        }

        // 关闭摄像头电源
        gpio_set_level(CAMERA_PWR_PIN, 0);
        gpio_set_level(LED_PIN, 0);
    } else {
        ESP_LOGI(TAG, "首次启动或非按钮唤醒");
    }

    // 配置 EXT0 唤醒（按钮低电平）
    esp_sleep_enable_ext0_wakeup(BUTTON_PIN, 0);

    ESP_LOGI(TAG, "进入 Deep Sleep，等待按钮...");
    esp_deep_sleep_start();
}
```

---

## 10. 功耗测量方法

### 10.1 测量工具对比

| 工具 | 精度 | 价格 | 适用场景 |
|------|------|------|---------|
| 万用表 | ~1 mA | 低 | 粗略测量平均电流 |
| 电流探头 (uCurrent) | ~1 uA | 中 | 实时电流波形 |
| Power Profiler Kit II | ~0.2 uA | 中 | Nordic 官方，ESP32 可用 |
| Joulescope | ~0.01 uA | 高 | 专业功耗分析仪 |
| INA219/INA226 | ~0.1 mA | 低 | 嵌入式电流监测 |

### 10.2 ESP32 开发板测量方法

#### 10.2.1 跳线测量法

```
电源 ──→ [电流表] ──→ ESP32 3V3 引脚
GND  ──────────────→ ESP32 GND 引脚

注意：
1. 断开 USB 供电（防止 USB 向芯片供电）
2. 使用外部 3.3V 稳压电源
3. 电流表串联在电源正极
```

#### 10.2.2 使用 INA226 模块

```c
#include "driver/i2c.h"
#include "ina226.h"

// INA226 电流监测
void monitor_current(void)
{
    // 初始化 INA226
    ina226_config_t cfg = {
        .i2c_port = I2C_NUM_0,
        .addr     = INA226_ADDR_GND,
        .shunt    = 0.1,    // 采样电阻 0.1 欧姆
    };

    ina226_init(&cfg);

    // 读取电流和电压
    float current = ina226_read_current();  // mA
    float voltage = ina226_read_bus_voltage();  // V
    float power   = ina226_read_power();  // mW

    printf("电流: %.3f mA, 电压: %.3f V, 功率: %.3f mW\n",
           current, voltage, power);
}
```

### 10.3 Deep Sleep 电流测量技巧

**问题：** Deep Sleep 电流仅 10 uA，普通万用表无法准确测量。

**解决方案：**

1. **串联大电阻法**
```
3.3V ──→ [100Ω 电阻] ──→ ESP32 3V3
                          │
                       [电压表] 测量电阻两端电压
                          │
                          GND

电流 = V / 100Ω
例如：测量 1mV → 电流 = 1mV / 100Ω = 10uA
```

2. **使用专用功耗分析仪**
   - Joulescope：自动量程切换，覆盖 0-200 mA
   - PPK2：Nordic Power Profiler Kit，性价比高

3. **逻辑分析仪辅助**
   - 使用 GPIO 翻转标记功耗状态
   - 结合电流波形分析各阶段功耗

### 10.4 功耗分析脚本

```python
# analyze_power.py - 功耗数据分析
import numpy as np
import matplotlib.pyplot as plt

def analyze_power_log(filename):
    """分析功耗日志文件"""
    data = np.loadtxt(filename, delimiter=',')

    timestamps = data[:, 0]  # 时间 (ms)
    currents = data[:, 1]    # 电流 (mA)

    # 计算统计信息
    avg_current = np.mean(currents)
    max_current = np.max(currents)
    min_current = np.min(currents)
    total_energy = np.trapz(currents, timestamps) / 3600  # mAh

    print(f"平均电流: {avg_current:.3f} mA")
    print(f"最大电流: {max_current:.3f} mA")
    print(f"最小电流: {min_current:.3f} mA")
    print(f"总能耗: {total_energy:.3f} mAh")

    # 绘制电流波形
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps / 1000, currents)
    plt.xlabel('时间 (秒)')
    plt.ylabel('电流 (mA)')
    plt.title('ESP32 功耗分析')
    plt.grid(True)
    plt.savefig('power_analysis.png')
    plt.show()

if __name__ == '__main__':
    analyze_power_log('power_log.csv')
```

### 10.5 常见功耗问题排查

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| Deep Sleep > 100 uA | GPIO 浮空漏电 | 隔离未使用 RTC GPIO |
| Deep Sleep > 1 mA | 外设未断电 | 添加电源开关电路 |
| Light Sleep > 10 mA | WiFi 未关闭 | 确认 `esp_wifi_stop()` |
| Active 电流偏高 | 射频持续活动 | 启用 WiFi PS 模式 |
| 唤醒后电流异常 | 外设初始化失败 | 检查初始化顺序和电源时序 |

---

## 附录

### A. ESP32 低功耗相关 API 速查

| API | 功能 |
|-----|------|
| `esp_light_sleep_start()` | 进入 Light Sleep |
| `esp_deep_sleep_start()` | 进入 Deep Sleep |
| `esp_sleep_enable_timer_wakeup()` | 定时器唤醒 |
| `esp_sleep_enable_ext0_wakeup()` | EXT0 GPIO 唤醒 |
| `esp_sleep_enable_ext1_wakeup()` | EXT1 GPIO 唤醒 |
| `esp_sleep_enable_touchpad_wakeup()` | Touch 唤醒 |
| `esp_sleep_enable_uart_wakeup()` | UART 唤醒 |
| `esp_sleep_get_wakeup_cause()` | 获取唤醒原因 |
| `esp_sleep_get_ext1_wakeup_status()` | EXT1 唤醒引脚状态 |
| `esp_pm_configure()` | 动态频率调节 |
| `esp_wifi_set_ps()` | WiFi 省电模式 |
| `rtc_gpio_isolate()` | 隔离 RTC GPIO |
| `ulp_riscv_load_binary()` | 加载 ULP 程序 |
| `ulp_riscv_run()` | 启动 ULP |
| `ulp_riscv_wakeup_main_processor()` | ULP 唤醒主 CPU |

### B. eFuse 安全相关字段

| 字段 | 说明 |
|------|------|
| `SECURE_BOOT_EN` | 启用 Secure Boot |
| `SPI_BOOT_CRYPT_CNT` | Flash 加密使能计数器 |
| `BLOCK_KEY0` | Secure Boot 公钥摘要 / 加密密钥 |
| `BLOCK_KEY1` | 备用密钥块 |
| `BLOCK_KEY2` | 备用密钥块 |
| `JTAG_DISABLE` | 禁用 JTAG 调试 |
| `UART_DOWNLOAD_DIS` | 禁用 UART 下载模式 |

### C. 参考资源

- [ESP-IDF Power Management 文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/power_management.html)
- [ESP32 Deep Sleep 文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/sleep_modes.html)
- [ULP 协处理器编程指南](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/ulp.html)
- [Secure Boot V2 文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/security/secure-boot-v2.html)
- [Flash Encryption 文档](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/security/flash-encryption.html)

---

> 创建日期：2026-06-21
> 最后更新：2026-06-21
