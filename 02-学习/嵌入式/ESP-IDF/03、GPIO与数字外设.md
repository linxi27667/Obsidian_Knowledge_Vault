# ESP-IDF GPIO与数字外设 （通用输入输出与数字信号控制）

## 核心概念

- **ESP32有34个GPIO引脚** - 可配置为输入、输出或中断模式
- **内部上拉/下拉电阻** - 无需外部电阻即可稳定输入状态
- **GPIO矩阵** - 允许将外设信号路由到任意GPIO，提供极大灵活性
- **数字外设** - LEDC(PWM)、PCNT(脉冲计数)、RMT(红外)等专用数字外设

---

## 一、GPIO基础配置

### 1.1 GPIO初始化

```c
#include "driver/gpio.h"

// GPIO配置结构体
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_2),    // 要配置的GPIO位图
    .mode = GPIO_MODE_OUTPUT,                 // 模式：输出
    .pull_up_en = GPIO_PULLUP_DISABLE,        // 上拉：禁用
    .pull_down_en = GPIO_PULLDOWN_DISABLE,    // 下拉：禁用
    .intr_type = GPIO_INTR_DISABLE            // 中断：禁用
};

// 应用配置
ESP_ERROR_CHECK(gpio_config(&io_conf));
```

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `pin_bit_mask` | GPIO位图（64位） | `(1ULL << GPIO_NUM_X)` |
| `mode` | 工作模式 | `GPIO_MODE_INPUT/OUTPUT/IO` |
| `pull_up_en` | 上拉使能 | `GPIO_PULLUP_ENABLE/DISABLE` |
| `pull_down_en` | 下拉使能 | `GPIO_PULLDOWN_ENABLE/DISABLE` |
| `intr_type` | 中断类型 | `GPIO_INTR_POSEDGE/NEGEDGE/ANYEDGE/LOW/HIGH` |

---

### 1.2 读写GPIO电平

```c
// 设置输出电平
ESP_ERROR_CHECK(gpio_set_level(GPIO_NUM_2, 1));   // 高电平
ESP_ERROR_CHECK(gpio_set_level(GPIO_NUM_2, 0));   // 低电平

// 读取输入电平
int level = gpio_get_level(GPIO_NUM_4);
if (level == 1) {
    ESP_LOGI(TAG, "GPIO 4 is HIGH");
}
```

---

### 1.3 批量配置多个GPIO

```c
// 同时配置多个GPIO
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_2) | (1ULL << GPIO_NUM_4) | (1ULL << GPIO_NUM_5),
    .mode = GPIO_MODE_OUTPUT,
    .pull_up_en = GPIO_PULLUP_DISABLE,
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE
};
gpio_config(&io_conf);
```

---

## 二、GPIO工作模式

### 2.1 输入模式

```c
// 配置为输入模式（带内部上拉）
gpio_config_t input_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_0),
    .mode = GPIO_MODE_INPUT,
    .pull_up_en = GPIO_PULLUP_ENABLE,      // 启用内部上拉
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE
};
gpio_config(&input_conf);

// 读取输入
int button_state = gpio_get_level(GPIO_NUM_0);
```

**输入模式配置：**

| 模式 | 配置 | 应用场景 |
|------|------|----------|
| 浮空输入 | 上下拉都禁用 | 外部已有上拉/下拉电阻 |
| 上拉输入 | 上拉使能 | 按键默认高电平（按下变低） |
| 下拉输入 | 下拉使能 | 按键默认低电平（按下变高） |

---

### 2.2 输出模式

```c
// 配置为推挽输出
gpio_config_t output_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_2),
    .mode = GPIO_MODE_OUTPUT,
    .pull_up_en = GPIO_PULLUP_DISABLE,
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE
};
gpio_config(&output_conf);

// LED闪烁
gpio_set_level(GPIO_NUM_2, 1);
vTaskDelay(pdMS_TO_TICKS(500));
gpio_set_level(GPIO_NUM_2, 0);
```

---

### 2.3 开漏输出模式

```c
// 开漏输出（用于I2C等总线）
gpio_config_t od_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_21),
    .mode = GPIO_MODE_OUTPUT_OD,           // 开漏输出
    .pull_up_en = GPIO_PULLUP_ENABLE,       // 必须外部或内部上拉
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE
};
gpio_config(&od_conf);
```

**开漏输出特点：**
- 只能输出低电平或高阻态
- 需要上拉电阻才能输出高电平
- 支持"线与"逻辑
- 常用于I2C、1-Wire等总线

---

### 2.4 输入输出模式

```c
// 双向模式（可作为输入或输出）
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_4),
    .mode = GPIO_MODE_INPUT_OUTPUT,        // 输入输出模式
    .pull_up_en = GPIO_PULLUP_DISABLE,
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE
};
gpio_config(&io_conf);

// 使用场景：双向通信引脚
```

---

## 三、中断配置

### 3.1 中断触发类型

```c
// 配置GPIO中断
gpio_config_t intr_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_0),
    .mode = GPIO_MODE_INPUT,
    .pull_up_en = GPIO_PULLUP_ENABLE,       // 按键通常上拉
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_NEGEDGE          // 下降沿触发（按下）
};
gpio_config(&intr_conf);
```

| 中断类型 | 说明 | 应用场景 |
|----------|------|----------|
| `GPIO_INTR_DISABLE` | 禁用中断 | 普通输入 |
| `GPIO_INTR_POSEDGE` | 上升沿触发 | 按键松开 |
| `GPIO_INTR_NEGEDGE` | 下降沿触发 | 按键按下 |
| `GPIO_INTR_ANYEDGE` | 任意边沿触发 | 检测状态变化 |
| `GPIO_INTR_LOW_LEVEL` | 低电平触发 | 持续检测低电平 |
| `GPIO_INTR_HIGH_LEVEL` | 高电平触发 | 持续检测高电平 |

---

### 3.2 中断服务程序(ISR)

```c
// 安装GPIO ISR服务（全局只需一次）
ESP_ERROR_CHECK(gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT));

// 定义ISR
static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    uint32_t gpio_num = (uint32_t)arg;
    // ISR中只做最小操作，如设置标志或发送信号量
    // 不能有延时、printf、复杂计算
}

// 注册ISR
ESP_ERROR_CHECK(gpio_isr_handler_add(
    GPIO_NUM_0,              // GPIO编号
    gpio_isr_handler,        // ISR函数
    (void *)GPIO_NUM_0       // 传递给ISR的参数
));
```

| ISR标志 | 说明 |
|---------|------|
| `ESP_INTR_FLAG_DEFAULT` | 默认标志（Level 1-3） |
| `ESP_INTR_FLAG_IRAM` | ISR位于IRAM（flash操作时仍可用） |
| `ESP_INTR_FLAG_SHARED` | 允许多个GPIO共享中断 |

> ⚠️ **v5.3.5+ SPI中断限制**：从v5.3.5开始，SPI master/slave 初始化不再接受 `ESP_INTR_FLAG_SHARED` 作为中断标志。如果在SPI初始化中使用此标志会导致错误。

---

### 3.3 移除和清理中断

```c
// 移除特定GPIO的中断处理
gpio_isr_handler_remove(GPIO_NUM_0);

// 卸载整个GPIO ISR服务
gpio_uninstall_isr_service();
```

---

## 四、GPIO矩阵与IOMUX

### 4.1 GPIO矩阵原理

```
GPIO矩阵架构：
┌─────────────────────────────────────────────────────────┐
│                      GPIO矩阵                            │
│  ┌─────────────┐         ┌──────────────────────────┐  │
│  │   外设0     │────────>│                         │  │
│  │  (UART0)    │         │                         │  │
│  └─────────────┘         │                         │  │
│  ┌─────────────┐         │      信号路由矩阵        │  │
│  │   外设1     │────────>│    (可任意连接)         │──┼──> GPIO0
│  │  (SPI2)     │         │                         │  │
│  └─────────────┘         │                         │──┼──> GPIO1
│  ┌─────────────┐         │                         │  │
│  │   外设N     │────────>│                         │──┼──> GPIOn
│  │             │         │                         │  │
│  └─────────────┘         └──────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

### 4.2 外设引脚配置

```c
#include "driver/uart.h"

// UART引脚配置示例
uart_config_t uart_config = {
    .baud_rate = 115200,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_DISABLE,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
};
uart_param_config(UART_NUM_1, &uart_config);

// 设置UART引脚（通过GPIO矩阵可任意指定）
uart_set_pin(UART_NUM_1, 
             GPIO_NUM_10,    // TXD
             GPIO_NUM_9,     // RXD
             UART_PIN_NO_CHANGE,  // RTS
             UART_PIN_NO_CHANGE); // CTS
```

---

### 4.3 IOMUX直接连接

```c
// 某些GPIO有专用IOMUX连接（性能更好）
// 如：SPI0/1的引脚通常是固定的，不使用GPIO矩阵

// 检查引脚是否有IOMUX连接
// 通常带"_IOMUX"后缀的宏定义的引脚支持
#define SPI_IOMUX_PIN_NUM_CLK  6   // 专用IOMUX引脚
#define SPI_IOMUX_PIN_NUM_MOSI 7
#define SPI_IOMUX_PIN_NUM_MISO 8
```

---

## 五、数字外设GPIO

### 5.1 LED PWM控制器(LEDC)

```c
#include "driver/ledc.h"

// LEDC配置
ledc_timer_config_t ledc_timer = {
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .duty_resolution = LEDC_TIMER_13_BIT,  // 13位分辨率
    .timer_num = LEDC_TIMER_0,
    .freq_hz = 5000,                        // 5kHz频率
    .clk_cfg = LEDC_AUTO_CLK
};
ledc_timer_config(&ledc_timer);

// 配置通道
ledc_channel_config_t ledc_channel = {
    .gpio_num = GPIO_NUM_2,
    .speed_mode = LEDC_LOW_SPEED_MODE,
    .channel = LEDC_CHANNEL_0,
    .intr_type = LEDC_INTR_DISABLE,
    .timer_sel = LEDC_TIMER_0,
    .duty = 0,                              // 初始占空比
    .hpoint = 0
};
ledc_channel_config(&ledc_channel);

// 设置占空比（呼吸灯）
for (int duty = 0; duty <= 8191; duty += 100) {
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    vTaskDelay(pdMS_TO_TICKS(20));
}
```

**LEDC特性：**

| 特性 | 说明 |
|------|------|
| 通道数 | 8个独立通道 |
| 分辨率 | 最高20位 |
| 频率 | 40MHz（高速模式）或5MHz（低速模式） |
| 渐变 | 硬件支持自动渐变 |

---

### 5.2 脉冲计数器(PCNT)

```c
#include "driver/pulse_cnt.h"

pcnt_unit_config_t unit_config = {
    .high_limit = 10000,
    .low_limit = -10000,
};
pcnt_unit_handle_t pcnt_unit = NULL;
pcnt_new_unit(&unit_config, &pcnt_unit);

// 配置通道
pcnt_chan_config_t chan_config = {
    .edge_gpio_num = GPIO_NUM_4,   // 计数边沿引脚
    .level_gpio_num = -1,           // 无电平控制
};
pcnt_channel_handle_t pcnt_chan = NULL;
pcnt_new_channel(pcnt_unit, &chan_config, &pcnt_chan);

// 设置边沿动作
pcnt_channel_set_edge_action(pcnt_chan, 
                             PCNT_CHANNEL_EDGE_ACTION_INCREASE,  // 上升沿+1
                             PCNT_CHANNEL_EDGE_ACTION_HOLD);      // 下降沿不变

// 启用计数器
pcnt_unit_enable(pcnt_unit);
pcnt_unit_clear_count(pcnt_unit);
pcnt_unit_start(pcnt_unit);

// 读取计数值
int pulse_count = 0;
pcnt_unit_get_count(pcnt_unit, &pulse_count);
```

---

### 5.3 RTC GPIO（低功耗）

```c
#include "driver/rtc_io.h"

// RTC GPIO可以在deep sleep中保持状态
// ESP32的RTC GPIO: 0, 2, 4, 12-15, 25-27, 32-39

// 配置RTC GPIO
rtc_gpio_init(GPIO_NUM_25);
rtc_gpio_set_direction(GPIO_NUM_25, RTC_GPIO_MODE_OUTPUT_ONLY);
rtc_gpio_set_level(GPIO_NUM_25, 1);

// 配置为Deep Sleep唤醒源
esp_sleep_enable_ext0_wakeup(GPIO_NUM_33, 0);  // GPIO33低电平唤醒
```

**RTC GPIO引脚（ESP32）：**

| GPIO | RTC GPIO | 功能 |
|------|----------|------|
| 0 | RTC_GPIO11 | 有内部上拉 |
| 2 | RTC_GPIO12 | 连接板载LED |
| 4 | RTC_GPIO10 | ADC2通道0 |
| 12-15 | RTC_GPIO15-12 | JTAG引脚 |
| 25-27 | RTC_GPIO6-8 | DAC输出 |
| 32-39 | RTC_GPIO9-4 | ADC1通道 |

---

## 六、GPIO电平转换

### 6.1 驱动能力配置

```c
// 设置GPIO驱动能力（输出电流能力）
gpio_set_drive_capability(GPIO_NUM_2, GPIO_DRIVE_CAP_3);
```

| 能力等级 | 最大电流 | 应用场景 |
|----------|----------|----------|
| `GPIO_DRIVE_CAP_0` | ~5mA | 小负载 |
| `GPIO_DRIVE_CAP_1` | ~10mA | LED |
| `GPIO_DRIVE_CAP_2` | ~20mA | 继电器 |
| `GPIO_DRIVE_CAP_3` | ~40mA | 大功率设备 |

**注意：** ESP32单个GPIO最大40mA，但所有GPIO总电流有限制。

---

### 6.2 输入阈值

```c
// ESP32输入阈值：
// Vil(max) = 0.25 * VDD (低电平最大)
// Vih(min) = 0.75 * VDD (高电平最小)
// VDD = 3.3V时：
//   - 低电平: < 0.825V
//   - 高电平: > 2.475V
//   - 不确定区: 0.825V ~ 2.475V
```

---

## 七、完整示例

### 示例1：按键消抖与中断处理

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "BUTTON";

#define BUTTON_GPIO     GPIO_NUM_0
#define DEBOUNCE_MS     50

static QueueHandle_t gpio_evt_queue = NULL;

// GPIO中断处理
static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    uint32_t gpio_num = (uint32_t)arg;
    // 发送GPIO号到队列，避免在ISR中做复杂操作
    xQueueSendFromISR(gpio_evt_queue, &gpio_num, NULL);
}

// 按键处理任务
static void button_task(void *arg)
{
    uint32_t io_num;
    uint32_t last_press_time = 0;
    
    while (1) {
        if (xQueueReceive(gpio_evt_queue, &io_num, portMAX_DELAY)) {
            uint32_t current_time = xTaskGetTickCount() * portTICK_PERIOD_MS;
            
            // 软件消抖
            if ((current_time - last_press_time) > DEBOUNCE_MS) {
                last_press_time = current_time;
                
                // 读取确认按键状态
                if (gpio_get_level(io_num) == 0) {
                    ESP_LOGI(TAG, "Button pressed!");
                    // 执行按键操作
                }
            }
        }
    }
}

void app_main(void)
{
    // 配置GPIO
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << BUTTON_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,       // 按键上拉
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE          // 下降沿触发
    };
    gpio_config(&io_conf);
    
    // 创建队列
    gpio_evt_queue = xQueueCreate(10, sizeof(uint32_t));
    
    // 安装GPIO ISR服务
    gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT);
    
    // 添加中断处理
    gpio_isr_handler_add(BUTTON_GPIO, gpio_isr_handler, (void *)BUTTON_GPIO);
    
    // 创建按键处理任务
    xTaskCreate(button_task, "button_task", 2048, NULL, 10, NULL);
    
    ESP_LOGI(TAG, "Button interrupt initialized");
}
```

---

### 示例2：LED PWM呼吸灯

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/ledc.h"
#include "esp_log.h"

static const char *TAG = "BREATH_LED";

#define LEDC_TIMER          LEDC_TIMER_0
#define LEDC_MODE           LEDC_LOW_SPEED_MODE
#define LEDC_CHANNEL        LEDC_CHANNEL_0
#define LEDC_DUTY_RES       LEDC_TIMER_13_BIT  // 2^13 = 8192
#define LEDC_FREQUENCY      5000
#define LED_GPIO            GPIO_NUM_2

void ledc_init(void)
{
    // 配置定时器
    ledc_timer_config_t ledc_timer = {
        .speed_mode = LEDC_MODE,
        .duty_resolution = LEDC_DUTY_RES,
        .timer_num = LEDC_TIMER,
        .freq_hz = LEDC_FREQUENCY,
        .clk_cfg = LEDC_AUTO_CLK
    };
    ESP_ERROR_CHECK(ledc_timer_config(&ledc_timer));
    
    // 配置通道
    ledc_channel_config_t ledc_channel = {
        .gpio_num = LED_GPIO,
        .speed_mode = LEDC_MODE,
        .channel = LEDC_CHANNEL,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = LEDC_TIMER,
        .duty = 0,
        .hpoint = 0
    };
    ESP_ERROR_CHECK(ledc_channel_config(&ledc_channel));
}

void breath_led_task(void *arg)
{
    uint32_t duty = 0;
    int direction = 1;
    
    while (1) {
        // 设置占空比
        ESP_ERROR_CHECK(ledc_set_duty(LEDC_MODE, LEDC_CHANNEL, duty));
        ESP_ERROR_CHECK(ledc_update_duty(LEDC_MODE, LEDC_CHANNEL));
        
        // 改变占空比方向
        duty += direction * 100;
        if (duty >= 8191) {
            duty = 8191;
            direction = -1;
        } else if (duty <= 0) {
            duty = 0;
            direction = 1;
        }
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void app_main(void)
{
    ledc_init();
    xTaskCreate(breath_led_task, "breath_led", 2048, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "Breath LED started");
}
```

---

### 示例3：多按键矩阵扫描

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "KEY_MATRIX";

// 4x4矩阵键盘定义
#define ROW_NUM     4
#define COL_NUM     4

// 行引脚（输出）
static const gpio_num_t row_pins[ROW_NUM] = {GPIO_NUM_13, GPIO_NUM_12, GPIO_NUM_14, GPIO_NUM_27};
// 列引脚（输入上拉）
static const gpio_num_t col_pins[COL_NUM] = {GPIO_NUM_26, GPIO_NUM_25, GPIO_NUM_33, GPIO_NUM_32};

// 按键映射表
static const char key_map[ROW_NUM][COL_NUM] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}
};

void key_matrix_init(void)
{
    // 配置行（输出）
    for (int i = 0; i < ROW_NUM; i++) {
        gpio_set_direction(row_pins[i], GPIO_MODE_OUTPUT);
        gpio_set_level(row_pins[i], 1);  // 默认高电平
    }
    
    // 配置列（输入上拉）
    for (int j = 0; j < COL_NUM; j++) {
        gpio_set_direction(col_pins[j], GPIO_MODE_INPUT);
        gpio_set_pull_mode(col_pins[j], GPIO_PULLUP_ONLY);
    }
}

char key_scan(void)
{
    for (int row = 0; row < ROW_NUM; row++) {
        // 拉低当前行
        gpio_set_level(row_pins[row], 0);
        vTaskDelay(pdMS_TO_TICKS(1));  // 短暂延时稳定
        
        // 扫描所有列
        for (int col = 0; col < COL_NUM; col++) {
            if (gpio_get_level(col_pins[col]) == 0) {
                // 按键按下
                gpio_set_level(row_pins[row], 1);  // 恢复行电平
                return key_map[row][col];
            }
        }
        
        // 恢复行电平
        gpio_set_level(row_pins[row], 1);
    }
    
    return 0;  // 无按键
}

void key_matrix_task(void *arg)
{
    char last_key = 0;
    
    while (1) {
        char key = key_scan();
        
        // 消抖和检测按键释放
        if (key != 0 && key != last_key) {
            ESP_LOGI(TAG, "Key pressed: %c", key);
        }
        
        last_key = key;
        vTaskDelay(pdMS_TO_TICKS(50));  // 扫描间隔
    }
}

void app_main(void)
{
    key_matrix_init();
    xTaskCreate(key_matrix_task, "key_matrix", 2048, NULL, 5, NULL);
}
```

---

## 附录：GPIO API速查表

### 基础配置

| API | 说明 |
|-----|------|
| `gpio_config()` | 批量配置GPIO |
| `gpio_set_direction()` | 设置方向 |
| `gpio_set_level()` | 设置输出电平 |
| `gpio_get_level()` | 读取输入电平 |
| `gpio_set_pull_mode()` | 设置上下拉 |

### 中断管理

| API | 说明 |
|-----|------|
| `gpio_install_isr_service()` | 安装ISR服务 |
| `gpio_uninstall_isr_service()` | 卸载ISR服务 |
| `gpio_isr_handler_add()` | 添加中断处理 |
| `gpio_isr_handler_remove()` | 移除中断处理 |
| `gpio_wakeup_enable()` | 启用唤醒功能 |

### 高级功能

| API | 说明 |
|-----|------|
| `gpio_set_drive_capability()` | 设置驱动能力 |
| `gpio_deep_sleep_hold_en()` | Deep Sleep保持电平 |
| `rtc_gpio_init()` | 初始化RTC GPIO |
| `rtc_gpio_set_direction()` | 设置RTC GPIO方向 |

### 常用宏定义

| 宏 | 说明 |
|---|------|
| `GPIO_NUM_X` | GPIO编号（X=0-39） |
| `GPIO_MODE_INPUT` | 输入模式 |
| `GPIO_MODE_OUTPUT` | 输出模式 |
| `GPIO_MODE_INPUT_OUTPUT` | 输入输出模式 |
| `GPIO_PULLUP_ENABLE` | 上拉使能 |
| `GPIO_PULLDOWN_ENABLE` | 下拉使能 |
