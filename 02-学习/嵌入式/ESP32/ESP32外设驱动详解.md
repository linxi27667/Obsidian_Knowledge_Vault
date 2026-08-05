# ESP32 外设驱动详解

> ESP-IDF 外设驱动全面参考。涵盖 GPIO、ADC、DAC、PWM/LEDC、定时器、RMT、I2S、SD/MMC 八大外设模块。
> 框架：ESP-IDF v5.x | 芯片：ESP32 / ESP32-S3（部分差异单独标注）

---

## 目录

- [[#1. GPIO 通用输入输出]]
- [[#2. ADC 模数转换]]
- [[#3. DAC 数模转换]]
- [[#4. PWM / LEDC]]
- [[#5. 定时器]]
- [[#6. RMT 远程控制]]
- [[#7. I2S 音频接口]]
- [[#8. SD / MMC 存储]]
- [[#附录：API 速查表]]

---

## 1. GPIO 通用输入输出

### 1.1 概述

ESP32 共有 **34 个 GPIO 引脚**（GPIO0 ~ GPIO39），但并非所有引脚都可用作通用 IO：

| 引脚范围 | 说明 |
|---|---|
| GPIO0 ~ GPIO5 | 可用，GPIO0 启动模式选择 |
| GPIO6 ~ GPIO11 | 连接内部 SPI Flash，**禁止使用** |
| GPIO12 ~ GPIO17 | 可用，GPIO12 启动时影响 Flash 电压 |
| GPIO18 ~ GPIO23 | 可用，GPIO20 不存在 |
| GPIO24 ~ GPIO27 | 可用 |
| GPIO28 ~ GPIO31 | 不存在 |
| GPIO32 ~ GPIO39 | 仅输入，GPIO34~39 无内部上拉/下拉 |

> **关键限制**：GPIO34~39 只能配置为输入模式，不支持输出，不支持内部上拉/下拉电阻。

### 1.2 GPIO 模式配置

ESP-IDF 使用 `gpio_config_t` 结构体进行批量配置：

```c
#include "driver/gpio.h"

// 输入模式 - 上拉
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_0),  // 位掩码，可同时配置多个引脚
    .mode         = GPIO_MODE_INPUT,         // 输入模式
    .pull_up_en   = GPIO_PULLUP_ENABLE,      // 使能内部上拉
    .pull_down_en = GPIO_PULLDOWN_DISABLE,   // 禁用内部下拉
    .intr_type    = GPIO_INTR_DISABLE        // 禁用中断
};
gpio_config(&io_conf);
```

常用模式枚举：

| 模式 | 宏 | 说明 |
|---|---|---|
| 仅输入 | `GPIO_MODE_INPUT` | 读取外部信号 |
| 仅输出 | `GPIO_MODE_OUTPUT` | 驱动外部负载 |
| 输入输出 | `GPIO_MODE_INPUT_OUTPUT` | 双向 IO |
| 开漏输出 | `GPIO_MODE_OUTPUT_OD` | 开漏模式，需外部上拉 |
| 输入+开漏 | `GPIO_MODE_INPUT_OUTPUT_OD` | 开漏双向 |

### 1.3 数字读写

```c
// 设置输出电平
gpio_set_level(GPIO_NUM_2, 1);   // 高电平
gpio_set_level(GPIO_NUM_2, 0);   // 低电平

// 读取输入电平
int level = gpio_get_level(GPIO_NUM_4);
if (level == 1) {
    ESP_LOGI("GPIO", "引脚为高电平");
}

// 设置引脚方向（运行时切换）
gpio_set_direction(GPIO_NUM_5, GPIO_MODE_OUTPUT);
gpio_set_direction(GPIO_NUM_5, GPIO_MODE_INPUT);

// 设置上拉/下拉
gpio_set_pull_mode(GPIO_NUM_5, GPIO_PULLUP_ONLY);
```

### 1.4 GPIO 中断

GPIO 支持 6 种中断触发类型：

| 触发类型 | 宏 | 说明 |
|---|---|---|
| 禁用 | `GPIO_INTR_DISABLE` | 不产生中断 |
| 上升沿 | `GPIO_INTR_POSEDGE` | 低变高触发 |
| 下降沿 | `GPIO_INTR_NEGEDGE` | 高变低触发 |
| 双边沿 | `GPIO_INTR_ANYEDGE` | 任意跳变触发 |
| 低电平 | `GPIO_INTR_LOW_LEVEL` | 持续低电平触发 |
| 高电平 | `GPIO_INTR_HIGH_LEVEL` | 持续高电平触发 |

```c
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BUTTON_GPIO  GPIO_NUM_0
#define LED_GPIO     GPIO_NUM_2

// 中断服务程序（ISR）- 必须用 IRAM_ATTR 修饰
static void IRAM_ATTR gpio_isr_handler(void *arg)
{
    uint32_t gpio_num = (uint32_t)arg;
    // ISR 中只允许调用带 FromISR 后缀的 FreeRTOS API
    // 这里仅做标志位翻转等简短操作
}

void gpio_interrupt_init(void)
{
    // 配置按钮引脚
    gpio_config_t btn_conf = {
        .pin_bit_mask = (1ULL << BUTTON_GPIO),
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type    = GPIO_INTR_NEGEDGE       // 按下时下降沿
    };
    gpio_config(&btn_conf);

    // 安装 GPIO 中断服务（只需调用一次）
    gpio_install_isr_service(0);

    // 绑定特定引脚的中断处理函数
    gpio_isr_handler_add(BUTTON_GPIO, gpio_isr_handler, (void *)BUTTON_GPIO);
}

// 在任务中响应中断事件的推荐方式：使用队列
static QueueHandle_t gpio_evt_queue = NULL;

static void IRAM_ATTR gpio_task_isr(void *arg)
{
    uint32_t io_num;
    for (;;) {
        if (xQueueReceive(gpio_evt_queue, &io_num, portMAX_DELAY)) {
            printf("GPIO[%"PRIu32"] 中断触发\n", io_num);
            // 去抖动：短暂延时后确认电平
            vTaskDelay(pdMS_TO_TICKS(50));
            if (gpio_get_level(io_num) == 0) {
                gpio_set_level(LED_GPIO, !gpio_get_level(LED_GPIO));
            }
        }
    }
}
```

### 1.5 电容触摸引脚

ESP32 支持 **10 个电容触摸引脚**（Touch0 ~ Touch9），映射关系：

| Touch 通道 | GPIO |
|---|---|
| Touch0 | GPIO4 |
| Touch1 | GPIO0 |
| Touch2 | GPIO2 |
| Touch3 | GPIO15 |
| Touch4 | GPIO13 |
| Touch5 | GPIO12 |
| Touch6 | GPIO14 |
| Touch7 | GPIO27 |
| Touch8 | GPIO33 |
| Touch9 | GPIO32 |

```c
#include "driver/touch_pad.h"

#define TOUCH_THRESHOLD  400   // 触摸阈值，需根据实际硬件校准

void touch_init(void)
{
    // 初始化触摸外设
    touch_pad_init();
    // 设置测量电压（高参考电压、低参考电压、衰减）
    touch_pad_set_voltage(TOUCH_HVOLT_2V7, TOUCH_LVOLT_0V5, TOUCH_HVOLT_ATTEN_1V);
    // 配置过滤器（消除噪声）
    touch_pad_filter_start(10);  // 10ms 滤波周期

    // 配置单个触摸通道
    touch_pad_config(TOUCH_PAD_NUM4, 0);  // Touch0 = GPIO4

    // 读取基准值（无触摸时的原始值）
    uint16_t touch_value;
    touch_pad_read_filtered(TOUCH_PAD_NUM4, &touch_value);
    ESP_LOGI("TOUCH", "Touch0 基准值: %d", touch_value);
}

void touch_task(void *arg)
{
    uint16_t touch_value;
    while (1) {
        touch_pad_read_filtered(TOUCH_PAD_NUM4, &touch_value);
        if (touch_value < TOUCH_THRESHOLD) {
            ESP_LOGI("TOUCH", "检测到触摸! 值: %d", touch_value);
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
```

> **ESP32-S2/S3 注意**：触摸 API 已重构为 `touch_sensor_new_driver()` 系列，不再使用上述旧 API。

---

## 2. ADC 模数转换

### 2.1 概述

ESP32 有两个 ADC 模块：

| 模块 | 分辨率 | 通道数 | 引脚 |
|---|---|---|---|
| ADC1 | 12-bit (默认) / 9/10/11-bit | 8 通道 | GPIO32~GPIO39 |
| ADC2 | 12-bit (默认) / 9/10/11-bit | 10 通道 | GPIO0, 2, 4, 12~15, 25~27 |

> **重要限制**：ADC2 与 WiFi 驱动冲突，启用 WiFi 后 ADC2 不可用。优先使用 ADC1。

### 2.2 ADC 衰减配置

ADC 输入电压范围通过衰减（attenuation）控制：

| 衰减 | 量程 (dB) | 有效输入范围 | 说明 |
|---|---|---|---|
| `ADC_ATTEN_DB_0` | 0 dB | 0 ~ 1.1V | 不衰减 |
| `ADC_ATTEN_DB_2_5` | 2.5 dB | 0 ~ 1.5V | 轻度衰减 |
| `ADC_ATTEN_DB_6` | 6 dB | 0 ~ 2.2V | 中度衰减 |
| `ADC_ATTEN_DB_11` | 11 dB | 0 ~ 3.3V | 满量程衰减 |

### 2.3 单次采集模式（One-shot）

```c
#include "driver/adc.h"
#include "esp_adc_cal.h"

#define ADC_CHANNEL   ADC1_CHANNEL_6   // GPIO34
#define ADC_ATTEN     ADC_ATTEN_DB_11
#define ADC_UNIT      ADC_UNIT_1

// ADC 校准特征值（用于将原始值转为毫伏）
static esp_adc_cal_characteristics_t adc_chars;

void adc_single_init(void)
{
    // 配置 ADC1 为 12-bit 分辨率
    adc1_config_width(ADC_WIDTH_BIT_12);
    // 配置通道衰减
    adc1_config_channel_atten(ADC_CHANNEL, ADC_ATTEN);

    // 校准：根据芯片特性生成校准表
    esp_adc_cal_characterize(ADC_UNIT, ADC_ATTEN, ADC_WIDTH_BIT_12,
                             1100,  // 默认参考电压 (mV)
                             &adc_chars);
}

void adc_read_task(void *arg)
{
    while (1) {
        // 读取原始值
        int raw = adc1_get_raw(ADC_CHANNEL);
        // 转换为毫伏（校准后）
        uint32_t voltage = esp_adc_cal_raw_to_voltage(raw, &adc_chars);
        ESP_LOGI("ADC", "原始值: %d, 电压: %"PRIu32" mV", raw, voltage);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
```

### 2.4 连续采集模式（DMA）

适用于高速连续采样场景（如音频采集）：

```c
#include "driver/adc.h"
#include "esp_adc_cal.h"

#define ADC_BUF_LEN   256

static TaskHandle_t adc_task_handle;
static uint8_t result[ADC_BUF_LEN] = {0};

static bool IRAM_ATTR adc_done_cb(adc_continuous_handle_t handle,
                                   const adc_continuous_evt_data_t *edata,
                                   void *user_data)
{
    BaseType_t mustYield = pdFALSE;
    vTaskNotifyGiveFromISR(adc_task_handle, &mustYield);
    return (mustYield == pdTRUE);
}

void adc_continuous_init(void)
{
    adc_continuous_handle_t handle = NULL;

    adc_continuous_handle_cfg_t adc_config = {
        .max_store_buf_size = 1024,
        .conv_frame_size    = ADC_BUF_LEN,
    };
    adc_continuous_new_handle(&adc_config, &handle);

    adc_continuous_config_t dig_cfg = {
        .sample_freq_hz = 20000,                     // 20kHz 采样率
        .conv_mode      = ADC_CONV_SINGLE_UNIT_1,    // 仅 ADC1
        .format         = ADC_DIGI_OUTPUT_FORMAT_TYPE1,
    };

    adc_digi_pattern_config_t adc_pattern = {
        .atten     = ADC_ATTEN_DB_11,
        .channel   = ADC1_CHANNEL_6,
        .unit      = ADC_UNIT_1,
        .bit_width = ADC_BITWIDTH_12,
    };
    dig_cfg.pattern_num    = 1;
    dig_cfg.adc_pattern    = &adc_pattern;

    adc_continuous_config(handle, &dig_cfg);

    // 注册完成回调
    adc_continuous_evt_cbs_t cbs = {
        .on_conv_done = adc_done_cb,
    };
    adc_continuous_register_event_callbacks(handle, &cbs, NULL);

    adc_continuous_start(handle);
}
```

### 2.5 多通道扫描

```c
void adc_multi_channel_init(void)
{
    adc1_config_width(ADC_WIDTH_BIT_12);

    // 配置多个通道
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);  // GPIO34
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);  // GPIO35
    adc1_config_channel_atten(ADC1_CHANNEL_4, ADC_ATTEN_DB_6);   // GPIO32
}

void adc_multi_read(void)
{
    int ch6_raw = adc1_get_raw(ADC1_CHANNEL_6);
    int ch7_raw = adc1_get_raw(ADC1_CHANNEL_7);
    int ch4_raw = adc1_get_raw(ADC1_CHANNEL_4);

    ESP_LOGI("ADC", "CH6=%d  CH7=%d  CH4=%d", ch6_raw, ch7_raw, ch4_raw);
}
```

---

## 3. DAC 数模转换

### 3.1 概述

ESP32 内置 **2 通道 8-bit DAC**：

| DAC 通道 | GPIO |
|---|---|
| DAC1 | GPIO25 |
| DAC2 | GPIO26 |

> **注意**：ESP32-S2/S3 不内置 DAC。需要 DAC 功能可使用外置 I2S DAC（如 PCM5102A）。

### 3.2 基本输出

```c
#include "driver/dac.h"

void dac_output_example(void)
{
    // 启用 DAC 通道
    dac_output_enable(DAC_CHANNEL_1);   // GPIO25

    // 输出固定电压 (0~255 对应 0~VDD，约 0~3.3V)
    dac_output_voltage(DAC_CHANNEL_1, 128);  // 约 1.65V

    // 生成锯齿波
    while (1) {
        for (int i = 0; i < 256; i++) {
            dac_output_voltage(DAC_CHANNEL_1, i);
            ets_delay_us(100);   // 微秒级延时
        }
    }
}
```

### 3.3 余弦波发生器

ESP32 DAC 内置硬件余弦波发生器：

```c
#include "driver/dac.h"
#include "driver/dac_cosine.h"

void dac_cosine_wave(void)
{
    dac_cosine_config_t cos_cfg = {
        .chan_id     = DAC_CHANNEL_1,
        .freq_hz    = 1000,                   // 1kHz 频率
        .clk_src    = DAC_COSINE_CLK_SRC_DEFAULT,
        .offset     = 0,                       // 偏移量 (-128 ~ 127)
        .phase      = DAC_COSINE_PHASE_0,      // 初始相位
        .atten      = DAC_COSINE_ATTEN_DB_0,   // 衰减
        .flags      = { .force_set_freq = false },
    };

    dac_cosine_handle_t cos_handle;
    dac_cosine_new_channel(&cos_cfg, &cos_handle);
    dac_cosine_start(cos_handle);

    ESP_LOGI("DAC", "余弦波发生器已启动: %d Hz", cos_cfg.freq_hz);

    // 运行 5 秒后停止
    vTaskDelay(pdMS_TO_TICKS(5000));
    dac_cosine_stop(cos_handle);
    dac_cosine_del_channel(cos_handle);
}
```

### 3.4 DMA 连续输出

用于播放音频波形等高速输出场景：

```c
#include "driver/dac.h"

#define WAVE_LEN    256

static const uint8_t sine_wave[WAVE_LEN] = {
    128, 131, 134, 137, 140, 143, 146, 149, 152, 155, 158, 162, 165, 167,
    170, 173, 176, 179, 182, 185, 187, 190, 193, 195, 198, 200, 203, 205,
    208, 210, 212, 215, 217, 219, 221, 223, 225, 227, 229, 231, 233, 234,
    236, 238, 239, 241, 242, 243, 245, 246, 247, 248, 249, 250, 251, 252,
    252, 253, 254, 254, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    255, 254, 254, 253, 252, 252, 251, 250, 249, 248, 247, 246, 245, 243,
    242, 241, 239, 238, 236, 234, 233, 231, 229, 227, 225, 223, 221, 219,
    217, 215, 212, 210, 208, 205, 203, 200, 198, 195, 193, 190, 187, 185,
    182, 179, 176, 173, 170, 167, 165, 162, 158, 155, 152, 149, 146, 143,
    140, 137, 134, 131, 128, 125, 122, 119, 116, 113, 110, 107, 104, 101,
    98, 94, 91, 89, 86, 83, 80, 77, 74, 71, 69, 66, 63, 61, 58, 56, 53,
    51, 48, 46, 44, 41, 39, 37, 35, 33, 31, 29, 27, 25, 23, 22, 20, 18,
    17, 15, 14, 13, 11, 10, 9, 8, 7, 6, 5, 4, 4, 3, 2, 2, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14,
    15, 17, 18, 20, 22, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 44, 46,
    48, 51, 53, 56, 58, 61, 63, 66, 69, 71, 74, 77, 80, 83, 86, 89, 91,
    94, 98, 101, 104, 107, 110, 113, 116, 119, 122, 125,
};

void dac_dma_sine(void)
{
    dac_output_enable(DAC_CHANNEL_1);

    dac_continuous_handle_t dac_handle;
    dac_continuous_config_t dac_cfg = {
        .chan_mask      = DAC_CHANNEL_MASK_1,
        .desc_num      = 4,
        .buf_size      = WAVE_LEN,
        .freq_hz       = 44100,          // 44.1kHz 采样率
        .offset        = 0,
        .clk_src       = DAC_DIGI_CLK_SRC_DEFAULT,
        .chan_mode      = DAC_CHANNEL_MODE_ALTER,  // 单通道交替
    };
    dac_continuous_new_channels(&dac_cfg, &dac_handle);
    dac_continuous_start(dac_handle, (uint8_t *)sine_wave, WAVE_LEN, true);
}
```

---

## 4. PWM / LEDC

### 4.1 概述

ESP32 的 LEDC（LED Control）外设提供 **16 通道 PWM 输出**，常用于 LED 调光、舵机控制、蜂鸣器驱动。

**LEDC 通道与定时器关系**：每个通道绑定一个定时器，多个通道可共享同一定时器。

### 4.2 基本 PWM 配置

```c
#include "driver/ledc.h"

#define LED_GPIO       GPIO_NUM_2
#define LEDC_CHANNEL   LEDC_CHANNEL_0
#define LEDC_TIMER     LEDC_TIMER_0
#define LEDC_MODE      LEDC_LOW_SPEED_MODE

void pwm_basic_init(void)
{
    // 配置定时器
    ledc_timer_config_t timer_conf = {
        .speed_mode      = LEDC_MODE,
        .duty_resolution = LEDC_TIMER_10_BIT,  // 10-bit 分辨率 (0~1023)
        .timer_num       = LEDC_TIMER,
        .freq_hz         = 5000,                // 5kHz PWM 频率
        .clk_cfg         = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_conf);

    // 配置通道
    ledc_channel_config_t channel_conf = {
        .gpio_num   = LED_GPIO,
        .speed_mode = LEDC_MODE,
        .channel    = LEDC_CHANNEL,
        .timer_sel  = LEDC_TIMER,
        .duty       = 0,              // 初始占空比
        .hpoint     = 0,
        .intr_type  = LEDC_INTR_DISABLE,
    };
    ledc_channel_config(&channel_conf);
}

void pwm_set_duty(uint32_t duty)
{
    ledc_set_duty(LEDC_MODE, LEDC_CHANNEL, duty);
    ledc_update_duty(LEDC_MODE, LEDC_CHANNEL);
}
```

### 4.3 频率与分辨率的关系

频率和分辨率受限于 LEDC 时钟源（默认 80MHz APB 时钟）：

```
分辨率 = log2(时钟频率 / PWM频率)
```

| 分辨率 | 最大频率 | 占空比范围 |
|---|---|---|
| 1-bit | 40 MHz | 0~1 |
| 8-bit | 312.5 kHz | 0~255 |
| 10-bit | 78.125 kHz | 0~1023 |
| 12-bit | 19.53 kHz | 0~4095 |
| 14-bit | 4.88 kHz | 0~16383 |
| 16-bit | 1.22 kHz | 0~65535 |
| 20-bit | 76.3 Hz | 0~1048575 |

> **实践建议**：舵机需要 50Hz / 16-bit，LED 调光 5kHz / 10-bit 足够。

### 4.4 渐变（Fade）功能

LEDC 内置硬件渐变，无需软件循环：

```c
void pwm_fade_init(void)
{
    // 安装渐变服务
    ledc_fade_func_install(0);

    // 方式1：同步阻塞渐变
    ledc_set_fade_with_time(LEDC_MODE, LEDC_CHANNEL, 1023, 3000);  // 3秒内渐亮到最大
    ledc_fade_start(LEDC_MODE, LEDC_CHANNEL, LEDC_FADE_NO_WAIT);

    // 方式2：同步等待渐变完成
    ledc_set_fade_with_time(LEDC_MODE, LEDC_CHANNEL, 0, 3000);     // 3秒渐暗
    ledc_fade_start(LEDC_MODE, LEDC_CHANNEL, LEDC_FADE_WAIT_DONE);
}

// 呼吸灯效果
void breathing_led(void *arg)
{
    while (1) {
        ledc_set_fade_with_time(LEDC_MODE, LEDC_CHANNEL, 1023, 2000);
        ledc_fade_start(LEDC_MODE, LEDC_CHANNEL, LEDC_FADE_WAIT_DONE);
        ledc_set_fade_with_time(LEDC_MODE, LEDC_CHANNEL, 0, 2000);
        ledc_fade_start(LEDC_MODE, LEDC_CHANNEL, LEDC_FADE_WAIT_DONE);
    }
}
```

### 4.5 MCPWM 电机控制

MCPWM（Motor Control PWM）专为电机控制设计，支持互补输出和死区时间：

```c
#include "driver/mcpwm.h"

#define MOTOR_PWM_GPIO    GPIO_NUM_18
#define MOTOR_DIR_GPIO    GPIO_NUM_19

void mcpwm_servo_init(void)
{
    // 初始化 MCPWM
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, MOTOR_PWM_GPIO);

    mcpwm_config_t pwm_config = {
        .frequency    = 50,       // 50Hz（舵机标准频率）
        .cmpr_a       = 7.5,      // 初始占空比 7.5%（舵机中位）
        .cmpr_b       = 0.0,
        .counter_mode = MCPWM_UP_COUNTER,
        .duty_mode    = MCPWM_DUTY_MODE_0,
    };
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
}

// 设置舵机角度 (0~180度)
void mcpwm_set_servo_angle(float angle)
{
    // 舵机脉宽范围：0.5ms(0度) ~ 2.5ms(180度)
    // 50Hz 周期 = 20ms
    // 占空比 = (0.5 + angle/180*2.0) / 20 * 100
    float duty = (0.5 + angle / 180.0 * 2.0) / 20.0 * 100.0;
    mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, duty);
    mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A,
                         MCPWM_DUTY_MODE_0);
}

// 直流电机控制
void dc_motor_init(void)
{
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, MOTOR_PWM_GPIO);

    mcpwm_config_t config = {
        .frequency    = 20000,    // 20kHz（超出人耳范围）
        .cmpr_a       = 0,
        .counter_mode = MCPWM_UP_COUNTER,
        .duty_mode    = MCPWM_DUTY_MODE_0,
    };
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &config);

    gpio_set_direction(MOTOR_DIR_GPIO, GPIO_MODE_OUTPUT);
}

void dc_motor_set_speed(float speed_percent, bool forward)
{
    gpio_set_level(MOTOR_DIR_GPIO, forward ? 1 : 0);
    mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, speed_percent);
}
```

---

## 5. 定时器

### 5.1 Timer Group 硬件定时器

ESP32 有 **2 个 Timer Group**，每组含 **2 个 64-bit 定时器**，共 4 个硬件定时器。

```c
#include "driver/timer.h"

#define TIMER_GROUP   TIMER_GROUP_0
#define TIMER_IDX     TIMER_0

void hw_timer_init(void)
{
    timer_config_t config = {
        .divider     = 80,            // 80分频 -> 1MHz (1us 精度)
        .counter_dir = TIMER_COUNT_UP,
        .counter_en  = TIMER_PAUSE,
        .alarm_en    = TIMER_ALARM_EN,
        .auto_reload = TIMER_AUTORELOAD_EN,  // 自动重载
        .clk_src     = TIMER_SRC_CLK_DEFAULT,
    };
    timer_init(TIMER_GROUP, TIMER_IDX, &config);

    // 设置初始计数值
    timer_set_counter_value(TIMER_GROUP, TIMER_IDX, 0);
    // 设置报警值（1秒 = 1000000us）
    timer_set_alarm_value(TIMER_GROUP, TIMER_IDX, 1000000);
    // 注册中断回调
    timer_isr_callback_add(TIMER_GROUP, TIMER_IDX, timer_isr_cb, NULL, 0);
    // 启动定时器
    timer_start(TIMER_GROUP, TIMER_IDX);
}

// ISR 回调函数
static bool IRAM_ATTR timer_isr_cb(void *arg)
{
    // 高精度时间戳操作
    return true;  // 返回 true 表示任务唤醒
}
```

### 5.2 ESP_TIMER 软件定时器

`esp_timer` 是基于高分辨率定时器（64-bit，1MHz）的软件定时器框架，适合通用定时需求：

```c
#include "esp_timer.h"

static esp_timer_handle_t periodic_timer;
static esp_timer_handle_t oneshot_timer;

// 周期性定时器回调
static void periodic_timer_cb(void *arg)
{
    ESP_LOGI("TIMER", "周期定时器触发，间隔 1 秒");
}

// 单次定时器回调
static void oneshot_timer_cb(void *arg)
{
    ESP_LOGI("TIMER", "单次定时器触发");
}

void esp_timer_example(void)
{
    // 周期性定时器
    esp_timer_create_args_t periodic_args = {
        .callback = periodic_timer_cb,
        .arg      = NULL,
        .name     = "periodic_1s",
    };
    esp_timer_create(&periodic_args, &periodic_timer);
    esp_timer_start_periodic(periodic_timer, 1000000);  // 1秒 (单位 us)

    // 单次定时器
    esp_timer_create_args_t oneshot_args = {
        .callback = oneshot_timer_cb,
        .arg      = NULL,
        .name     = "oneshot_5s",
    };
    esp_timer_create(&oneshot_args, &oneshot_timer);
    esp_timer_start_once(oneshot_timer, 5000000);  // 5秒后触发

    // 获取高精度时间戳
    int64_t us = esp_timer_get_time();  // 系统启动后的微秒数
    ESP_LOGI("TIMER", "当前时间: %"PRId64" us", us);
}

// 停止并删除定时器
void esp_timer_cleanup(void)
{
    esp_timer_stop(periodic_timer);
    esp_timer_delete(periodic_timer);
    esp_timer_delete(oneshot_timer);
}
```

### 5.3 看门狗定时器（WDT）

ESP32 有 3 种看门狗：

| 看门狗 | 说明 |
|---|---|
| MWDT (Main WDT) | Timer Group 硬件看门狗，每组一个 |
| RTC WDT | RTC 域看门狗，深度睡眠期间也能运行 |
| Task WDT | 软件任务看门狗，监控任务是否正常喂狗 |

**Task WDT（推荐使用）**：

```c
#include "esp_task_wdt.h"

void wdt_example(void)
{
    // 初始化 Task WDT，超时时间 5 秒
    esp_task_wdt_config_t wdt_config = {
        .timeout_ms    = 5000,
        .idle_core_mask = (1 << portNUM_PROCESSORS) - 1,  // 监控所有核心的空闲任务
        .trigger_panic  = true,
    };
    esp_task_wdt_reconfigure(&wdt_config);

    // 将当前任务添加到 WDT 监控
    esp_task_wdt_add(NULL);

    while (1) {
        // 执行业务逻辑...
        do_something();

        // 喂狗（必须在超时前调用）
        esp_task_wdt_reset();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## 6. RMT 远程控制

### 6.1 概述

RMT（Remote Control Transceiver）是一个灵活的脉冲收发器，硬件上由 **8 个通道**（TX+RX 各 4 个）组成，每个通道有 64x32-bit 的内存块用于存储脉冲序列。

典型应用：
- 红外遥控（NEC、Sony SIRC 等协议）
- WS2812B / NeoPixel 地址灯带驱动
- 超声波测距（HC-SR04）

### 6.2 红外接收（NEC 协议）

```c
#include "driver/rmt.h"
#include "ir_tools.h"

#define IR_RX_GPIO     GPIO_NUM_4
#define IR_RX_CHANNEL  RMT_CHANNEL_0

void ir_rx_init(void)
{
    rmt_config_t rmt_rx_config = {
        .rmt_mode      = RMT_MODE_RX,
        .channel        = IR_RX_CHANNEL,
        .gpio_num       = IR_RX_GPIO,
        .clk_div        = 80,               // 80分频 -> 1MHz -> 1us 精度
        .mem_block_num  = 1,
        .flags          = 0,
        .rx_config      = {
            .idle_threshold  = 10000,        // 空闲阈值 10ms
            .filter_ticks_thresh = 100,      // 滤波阈值 100us
            .filter_en       = true,
        },
    };
    rmt_config(&rmt_rx_config);
    rmt_driver_install(IR_RX_CHANNEL, 1000, 0);

    // 创建 NEC 解码器
    ir_builder_handle_t ir_builder = ir_builder_rmt_new_nec(&(ir_builder_config_t){
        .buffer_size = 64,
    });

    // 接收并解码
    rmt_item32_t items[64];
    size_t length = 0;
    while (1) {
        rmt_receive(IR_RX_CHANNEL, items, sizeof(items), &rmt_rx_config);
        // 解码 NEC 数据...
        uint32_t addr, cmd;
        if (ir_builder->decode(ir_builder, items, &addr, &cmd) == ESP_OK) {
            ESP_LOGI("IR", "地址: 0x%04X, 命令: 0x%02X", addr, cmd);
        }
    }
}
```

### 6.3 WS2812B 驱动

WS2812B 使用单线归零码编码，RMT 非常适合精确时序控制：

```c
#include "driver/rmt.h"
#include "led_strip.h"

#define WS2812_GPIO    GPIO_NUM_48
#define LED_COUNT      8

void ws2812_init(void)
{
    // 使用 led_strip 库（ESP-IDF v5.x 推荐方式）
    led_strip_config_t strip_config = {
        .strip_gpio_num   = WS2812_GPIO,
        .max_leds         = LED_COUNT,
        .led_pixel_format = LED_PIXEL_FORMAT_GRB,
        .led_model        = LED_MODEL_WS2812,
        .flags.invert_out = false,
    };

    led_strip_rmt_config_t rmt_config = {
        .resolution_hz = 10 * 1000 * 1000,  // 10MHz 分辨率
        .flags.with_dma = false,
    };

    led_strip_handle_t strip;
    led_strip_new_rmt_device(&strip_config, &rmt_config, &strip);

    // 设置颜色
    led_strip_set_pixel(strip, 0, 255, 0, 0);    // 第0颗：红色
    led_strip_set_pixel(strip, 1, 0, 255, 0);    // 第1颗：绿色
    led_strip_set_pixel(strip, 2, 0, 0, 255);    // 第2颗：蓝色
    led_strip_refresh(strip);                      // 刷新显示
}

// 手动 RMT 方式（不使用 led_strip 库）
void ws2812_raw_rmt(void)
{
    rmt_config_t config = RMT_DEFAULT_CONFIG_TX(WS2812_GPIO, RMT_CHANNEL_0);
    config.clk_div = 2;   // 40MHz -> 25ns/tick
    rmt_config(&config);
    rmt_driver_install(config.channel, 0, 0);

    // WS2812B 时序 (T0H=350ns, T0L=800ns, T1H=700ns, T1L=600ns)
    // 40MHz / 2 = 20MHz -> 50ns/tick
    rmt_item32_t bit0 = {{{ 7, 1, 16, 0 }}};   // 350ns H + 800ns L
    rmt_item32_t bit1 = {{{ 14, 1, 10, 0 }}};   // 700ns H + 500ns L

    // 发送 GRB 数据（例如绿色 = 0x00FF00）
    rmt_item32_t data[24];
    uint32_t color = 0x00FF00;  // GRB 绿色
    for (int i = 0; i < 24; i++) {
        data[i] = (color & (1 << (23 - i))) ? bit1 : bit0;
    }

    rmt_write_items(RMT_CHANNEL_0, data, 24, true);
    rmt_wait_tx_done(RMT_CHANNEL_0, pdMS_TO_TICKS(100));
}
```

---

## 7. I2S 音频接口

### 7.1 概述

I2S（Inter-IC Sound）是芯片间数字音频传输标准。ESP32 支持 **2 个 I2S 端口**，每端口可独立配置为 TX 或 RX。

支持模式：
- 标准 I2S（Philips）
- PCM
- TDM（时分复用，多声道）
- PDM（脉冲密度调制，数字麦克风）

### 7.2 I2S 配置（ESP-IDF v5.x 新 API）

```c
#include "driver/i2s_std.h"

static i2s_chan_handle_t tx_handle;
static i2s_chan_handle_t rx_handle;

void i2s_std_init(void)
{
    // 创建通道
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan_cfg.auto_clear = true;

    i2s_new_channel(&chan_cfg, &tx_handle, &rx_handle);

    // 标准模式配置
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(44100),   // 44.1kHz 采样率
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT,                    // 16-bit
            I2S_SLOT_MODE_STEREO                          // 立体声
        ),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = GPIO_NUM_17,    // 位时钟
            .ws   = GPIO_NUM_18,    // 字选择 (LRCK)
            .dout = GPIO_NUM_8,     // 数据输出
            .din  = I2S_GPIO_UNUSED,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv   = false,
            },
        },
    };

    i2s_channel_init_std_mode(tx_handle, &std_cfg);
    i2s_channel_enable(tx_handle);
}

// 写入音频数据
void i2s_write_audio(const int16_t *data, size_t bytes)
{
    size_t bytes_written = 0;
    i2s_channel_write(tx_handle, data, bytes, &bytes_written, portMAX_DELAY);
    ESP_LOGI("I2S", "写入 %"PRIu32" 字节", (uint32_t)bytes_written);
}
```

### 7.3 I2S 接收（麦克风采集）

```c
#include "driver/i2s_std.h"

void i2s_mic_init(void)
{
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    i2s_chan_handle_t mic_rx;

    i2s_new_channel(&chan_cfg, NULL, &mic_rx);  // 仅 RX

    i2s_std_config_t std_cfg = {
        .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(16000),
        .slot_cfg = I2S_STD_MSB_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO
        ),
        .gpio_cfg = {
            .bclk = GPIO_NUM_14,
            .ws   = GPIO_NUM_15,
            .din  = GPIO_NUM_16,
            .dout = I2S_GPIO_UNUSED,
        },
    };

    i2s_channel_init_std_mode(mic_rx, &std_cfg);
    i2s_channel_enable(mic_rx);

    // 采集任务
    int16_t buf[1024];
    size_t bytes_read;
    while (1) {
        i2s_channel_read(mic_rx, buf, sizeof(buf), &bytes_read, portMAX_DELAY);
        // 处理音频数据...
    }
}
```

### 7.4 PDM 模式（数字麦克风）

```c
#include "driver/i2s_pdm.h"

void i2s_pdm_mic_init(void)
{
    i2s_chan_handle_t pdm_rx;
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);

    i2s_new_channel(&chan_cfg, NULL, &pdm_rx);

    i2s_pdm_rx_config_t pdm_cfg = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(16000),
        .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO
        ),
        .gpio_cfg = {
            .clk  = GPIO_NUM_41,
            .din  = GPIO_NUM_42,
        },
    };

    i2s_channel_init_pdm_rx_mode(pdm_rx, &pdm_cfg);
    i2s_channel_enable(pdm_rx);
}
```

---

## 8. SD / MMC 存储

### 8.1 概述

ESP32 支持两种 SD 卡接口：

| 模式 | 引脚数 | 速度 | 说明 |
|---|---|---|---|
| SPI 模式 | 4 (MOSI/MISO/CLK/CS) | 较慢 (~4MHz) | 任意 GPIO，通用性好 |
| SD/MMC 模式 | 6 (CLK/CMD/D0~D3) | 快 (~20MHz) | 固定引脚，ESP32原生支持 |

### 8.2 SPI 模式

```c
#include "driver/sdspi_host.h"
#include "sdmmc_cmd.h"
#include "esp_vfs_fat.h"

#define SD_MOUNT_POINT  "/sdcard"
#define PIN_MOSI        GPIO_NUM_23
#define PIN_MISO        GPIO_NUM_19
#define PIN_CLK         GPIO_NUM_18
#define PIN_CS          GPIO_NUM_5

void sd_spi_init(void)
{
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = false,
        .max_files              = 5,
        .allocation_unit_size   = 16 * 1024,
    };

    sdmmc_card_t *card;
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();

    spi_bus_config_t bus_cfg = {
        .mosi_io_num   = PIN_MOSI,
        .miso_io_num   = PIN_MISO,
        .sclk_io_num   = PIN_CLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4000,
    };
    spi_bus_initialize(host.slot, &bus_cfg, SDSPI_DEFAULT_DMA);

    sdspi_device_config_t slot_config = SDSPI_DEVICE_CONFIG_DEFAULT();
    slot_config.gpio_cs = PIN_CS;
    slot_config.host_id = host.slot;

    esp_err_t ret = esp_vfs_fat_sdspi_mount(SD_MOUNT_POINT, &host,
                                             &slot_config, &mount_config, &card);
    if (ret != ESP_OK) {
        ESP_LOGE("SD", "挂载失败: %s", esp_err_to_name(ret));
        return;
    }

    sdmmc_card_print_info(stdout, card);

    // 读写文件
    FILE *f = fopen(SD_MOUNT_POINT"/hello.txt", "w");
    if (f) {
        fprintf(f, "Hello from ESP32!\n");
        fclose(f);
    }
}
```

### 8.3 SD/MMC 模式

```c
#include "sdmmc_cmd.h"
#include "driver/sdmmc_host.h"
#include "esp_vfs_fat.h"

void sd_mmc_init(void)
{
    esp_vfs_fat_sdmmc_mount_config_t mount_config = {
        .format_if_mount_failed = true,
        .max_files              = 5,
        .allocation_unit_size   = 16 * 1024,
    };

    sdmmc_card_t *card;

    // SD/MMC 主机配置
    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_1;          // 使用 Slot 1 (4-bit)
    host.max_freq_khz = SDMMC_FREQ_HIGHSPEED;

    // 引脚配置（ESP32 固定引脚）
    sdmmc_slot_config_t slot_config = SDMMC_SLOT_CONFIG_DEFAULT();
    slot_config.width = 4;  // 4-bit 数据线

    // ESP32 默认引脚：
    // CLK = GPIO14, CMD = GPIO15, D0 = GPIO2, D1 = GPIO4, D2 = GPIO12, D3 = GPIO13

    esp_err_t ret = esp_vfs_fat_sdmmc_mount(SD_MOUNT_POINT, &host,
                                             &slot_config, &mount_config, &card);
    if (ret != ESP_OK) {
        ESP_LOGE("SD", "MMC 挂载失败: %s", esp_err_to_name(ret));
        return;
    }

    ESP_LOGI("SD", "SD/MMC 卡已挂载");
    sdmmc_card_print_info(stdout, card);
}
```

### 8.4 文件操作示例

```c
#include <sys/stat.h>

void sd_file_operations(void)
{
    // 写文件
    FILE *f = fopen(SD_MOUNT_POINT"/data.csv", "w");
    if (f) {
        fprintf(f, "timestamp,temperature,humidity\n");
        for (int i = 0; i < 100; i++) {
            fprintf(f, "%d,%.1f,%.1f\n", i, 25.0 + i * 0.1, 60.0 + i * 0.05);
        }
        fclose(f);
        ESP_LOGI("SD", "CSV 文件写入完成");
    }

    // 读文件
    f = fopen(SD_MOUNT_POINT"/data.csv", "r");
    if (f) {
        char line[128];
        while (fgets(line, sizeof(line), f)) {
            // 去除换行符
            line[strcspn(line, "\n")] = 0;
            ESP_LOGI("SD", "读取: %s", line);
        }
        fclose(f);
    }

    // 文件信息
    struct stat st;
    if (stat(SD_MOUNT_POINT"/data.csv", &st) == 0) {
        ESP_LOGI("SD", "文件大小: %ld 字节", (long)st.st_size);
    }

    // 删除文件
    unlink(SD_MOUNT_POINT"/hello.txt");

    // 卸载 SD 卡
    esp_vfs_fat_sdcard_unmount(SD_MOUNT_POINT, NULL);
    ESP_LOGI("SD", "SD 卡已卸载");
}
```

---

## 附录：API 速查表

### GPIO

| 函数 | 说明 |
|---|---|
| `gpio_config(&conf)` | 批量配置 GPIO |
| `gpio_set_level(gpio, level)` | 设置输出电平 |
| `gpio_get_level(gpio)` | 读取输入电平 |
| `gpio_set_direction(gpio, mode)` | 设置引脚方向 |
| `gpio_set_pull_mode(gpio, pull)` | 设置上下拉模式 |
| `gpio_install_isr_service(flag)` | 安装 GPIO 中断服务 |
| `gpio_isr_handler_add(gpio, fn, arg)` | 绑定中断处理函数 |
| `gpio_isr_handler_remove(gpio)` | 移除中断处理函数 |
| `gpio_reset_pin(gpio)` | 重置引脚到默认状态 |
| `gpio_hold_en(gpio)` | 锁定引脚电平（睡眠保持） |
| `gpio_deep_sleep_hold_en()` | 使能深度睡眠引脚保持 |
| `touch_pad_init()` | 初始化触摸外设 |
| `touch_pad_config(ch, threshold)` | 配置触摸通道 |
| `touch_pad_read(ch, &value)` | 读取触摸原始值 |

### ADC

| 函数 | 说明 |
|---|---|
| `adc1_config_width(bits)` | 设置 ADC1 分辨率 |
| `adc1_config_channel_atten(ch, atten)` | 设置通道衰减 |
| `adc1_get_raw(ch)` | 单次采集，返回原始值 |
| `adc2_get_raw(ch, bits, &raw)` | ADC2 单次采集 |
| `esp_adc_cal_characterize(unit, atten, bits, vref, &chars)` | ADC 校准 |
| `esp_adc_cal_raw_to_voltage(raw, &chars)` | 原始值转毫伏 |
| `adc_continuous_new_handle(&cfg, &handle)` | 创建连续采集句柄 |
| `adc_continuous_config(handle, &cfg)` | 配置连续采集 |
| `adc_continuous_start(handle)` | 启动连续采集 |
| `adc_continuous_read(handle, buf, len, &ret, timeout)` | 读取连续采集数据 |
| `adc_continuous_stop(handle)` | 停止连续采集 |
| `adc_continuous_deinit(handle)` | 释放连续采集资源 |

### DAC

| 函数 | 说明 |
|---|---|
| `dac_output_enable(ch)` | 使能 DAC 输出 |
| `dac_output_voltage(ch, value)` | 输出指定电压 (0~255) |
| `dac_output_disable(ch)` | 禁用 DAC 输出 |
| `dac_cosine_new_channel(&cfg, &handle)` | 创建余弦波通道 |
| `dac_cosine_start(handle)` | 启动余弦波输出 |
| `dac_cosine_stop(handle)` | 停止余弦波输出 |
| `dac_continuous_new_channels(&cfg, &handle)` | 创建 DMA 连续输出 |
| `dac_continuous_start(handle, buf, len, loop)` | 启动 DMA 连续输出 |

### LEDC / PWM

| 函数 | 说明 |
|---|---|
| `ledc_timer_config(&conf)` | 配置 LEDC 定时器 |
| `ledc_channel_config(&conf)` | 配置 LEDC 通道 |
| `ledc_set_duty(mode, ch, duty)` | 设置占空比 |
| `ledc_update_duty(mode, ch)` | 更新占空比生效 |
| `ledc_get_duty(mode, ch)` | 获取当前占空比 |
| `ledc_set_freq(mode, timer, freq)` | 设置 PWM 频率 |
| `ledc_get_freq(mode, timer)` | 获取 PWM 频率 |
| `ledc_stop(mode, ch, level)` | 停止 PWM 并设固定电平 |
| `ledc_fade_func_install(irq)` | 安装渐变服务 |
| `ledc_set_fade_with_time(mode, ch, duty, time)` | 设置渐变目标和时间 |
| `ledc_fade_start(mode, ch, wait)` | 启动渐变 |
| `ledc_fade_func_uninstall()` | 卸载渐变服务 |
| `mcpwm_gpio_init(unit, signal, gpio)` | 初始化 MCPWM GPIO |
| `mcpwm_init(unit, timer, &conf)` | 初始化 MCPWM |
| `mcpwm_set_duty(unit, timer, op, duty)` | 设置 MCPWM 占空比 |
| `mcpwm_set_frequency(unit, timer, freq)` | 设置 MCPWM 频率 |

### 定时器

| 函数 | 说明 |
|---|---|
| `timer_init(group, timer, &conf)` | 初始化硬件定时器 |
| `timer_set_counter_value(group, timer, val)` | 设置计数值 |
| `timer_set_alarm_value(group, timer, val)` | 设置报警值 |
| `timer_start(group, timer)` | 启动定时器 |
| `timer_pause(group, timer)` | 暂停定时器 |
| `timer_isr_callback_add(group, timer, cb, arg, flags)` | 注册中断回调 |
| `timer_isr_callback_remove(group, timer)` | 移除中断回调 |
| `esp_timer_create(&args, &handle)` | 创建软件定时器 |
| `esp_timer_start_periodic(handle, period_us)` | 启动周期定时器 |
| `esp_timer_start_once(handle, timeout_us)` | 启动单次定时器 |
| `esp_timer_stop(handle)` | 停止定时器 |
| `esp_timer_delete(handle)` | 删除定时器 |
| `esp_timer_get_time()` | 获取当前时间戳 (us) |
| `esp_task_wdt_add(task)` | 添加任务到 WDT |
| `esp_task_wdt_reset()` | 喂狗 |
| `esp_task_wdt_delete(task)` | 从 WDT 移除任务 |

### RMT

| 函数 | 说明 |
|---|---|
| `rmt_config(&conf)` | 配置 RMT 通道 |
| `rmt_driver_install(ch, buf, flags)` | 安装 RMT 驱动 |
| `rmt_write_items(ch, items, num, wait)` | 发送脉冲序列 |
| `rmt_read_items(ch, items, num, timeout)` | 接收脉冲序列 |
| `rmt_wait_tx_done(ch, timeout)` | 等待发送完成 |
| `rmt_set_tx_intr(ch, en)` | 使能/禁用 TX 中断 |
| `rmt_set_rx_intr(ch, en)` | 使能/禁用 RX 中断 |
| `rmt_set_clk_div(ch, div)` | 设置时钟分频 |
| `rmt_driver_uninstall(ch)` | 卸载 RMT 驱动 |
| `led_strip_new_rmt_device(&strip, &rmt, &handle)` | 创建 LED 灯带设备 |
| `led_strip_set_pixel(handle, idx, r, g, b)` | 设置像素颜色 |
| `led_strip_refresh(handle)` | 刷新 LED 显示 |
| `led_strip_clear(handle)` | 清除所有 LED |

### I2S

| 函数 | 说明 |
|---|---|
| `i2s_new_channel(&cfg, &tx, &rx)` | 创建 I2S 通道 |
| `i2s_channel_init_std_mode(ch, &cfg)` | 初始化标准模式 |
| `i2s_channel_init_pdm_tx_mode(ch, &cfg)` | 初始化 PDM 发送 |
| `i2s_channel_init_pdm_rx_mode(ch, &cfg)` | 初始化 PDM 接收 |
| `i2s_channel_enable(ch)` | 使能 I2S 通道 |
| `i2s_channel_disable(ch)` | 禁用 I2S 通道 |
| `i2s_channel_write(ch, src, size, &written, timeout)` | 写入音频数据 |
| `i2s_channel_read(ch, dest, size, &read, timeout)` | 读取音频数据 |
| `i2s_del_channel(ch)` | 删除 I2S 通道 |

### SD / MMC

| 函数 | 说明 |
|---|---|
| `esp_vfs_fat_sdspi_mount(mount, &host, &slot, &cfg, &card)` | SPI 模式挂载 SD 卡 |
| `esp_vfs_fat_sdmmc_mount(mount, &host, &slot, &cfg, &card)` | MMC 模式挂载 SD 卡 |
| `esp_vfs_fat_sdcard_unmount(mount, card)` | 卸载 SD 卡 |
| `sdmmc_card_print_info(stream, card)` | 打印 SD 卡信息 |
| `SDSPI_HOST_DEFAULT()` | SPI 主机默认配置宏 |
| `SDMMC_HOST_DEFAULT()` | MMC 主机默认配置宏 |
| `SDSPI_DEVICE_CONFIG_DEFAULT()` | SPI 设备默认配置宏 |
| `SDMMC_SLOT_CONFIG_DEFAULT()` | MMC 插槽默认配置宏 |
| `spi_bus_initialize(host, &cfg, dma)` | 初始化 SPI 总线 |

---

> **参考文档**：[ESP-IDF 编程指南 - API Reference](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/)
