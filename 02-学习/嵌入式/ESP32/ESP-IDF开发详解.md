# ESP-IDF开发详解

## 核心概念

- **ESP-IDF** - Espressif IoT Development Framework
- **组件系统** - 模块化的软件架构
- **FreeRTOS** - ESP-IDF内置的RTOS
- **事件系统** - 统一的事件处理框架

---

## 一、ESP-IDF架构

### 1.1 系统架构

```
┌─────────────────────────────────────────┐
│              应用程序                    │
├─────────────────────────────────────────┤
│   组件层(components)                    │
│   ├── ESP-WiFi    ├── ESP-BLE         │
│   ├── ESP-HTTP    ├── ESP-MQTT        │
│   ├── ESP-DL      ├── ESP-SR          │
│   └── ...         └── ...             │
├─────────────────────────────────────────┤
│   驱动层(drivers)                       │
│   ├── GPIO  ├── UART  ├── SPI         │
│   ├── I2C   ├── ADC   ├── DAC         │
│   └── ...                             │
├─────────────────────────────────────────┤
│   FreeRTOS内核                         │
├─────────────────────────────────────────┤
│   硬件抽象层(HAL)                       │
└─────────────────────────────────────────┘
```

---

### 1.2 支持的芯片

| 芯片 | 核心 | WiFi | BLE | PSRAM |
|------|------|------|-----|-------|
| ESP32 | 双核Xtensa | 2.4G | 4.2 | 4MB |
| ESP32-S2 | 单核Xtensa | 2.4G | 无 | 2MB |
| ESP32-S3 | 双核Xtensa | 2.4G | 5.0 | 8MB |
| ESP32-C3 | 单核RISC-V | 2.4G | 5.0 | 无 |
| ESP32-C6 | 单核RISC-V | 2.4G | 5.0 | 无 |
| ESP32-H2 | 单核RISC-V | 无 | 5.0 | 无 |

---

## 二、项目结构

### 2.1 标准结构

```
my_project/
├── CMakeLists.txt
├── main/
│   ├── CMakeLists.txt
│   └── main.c
├── components/
│   └── my_component/
│       ├── CMakeLists.txt
│       ├── include/
│       │   └── my_component.h
│       └── src/
│           └── my_component.c
└── sdkconfig
```

**顶层CMakeLists.txt：**
```cmake
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(my_project)
```

**main/CMakeLists.txt：**
```cmake
idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       REQUIRES "driver" "esp_wifi")
```

---

### 2.2 组件创建

```bash
# 使用idf.py创建组件
idf.py create-component my_component

# 手动创建
mkdir -p components/my_component/{src,include}
```

**components/my_component/CMakeLists.txt：**
```cmake
idf_component_register(SRCS "src/my_component.c"
                       INCLUDE_DIRS "include"
                       REQUIRES "driver")
```

---

## 三、核心API

### 3.1 GPIO

```c
#include "driver/gpio.h"

#define LED_GPIO    GPIO_NUM_2
#define BUTTON_GPIO GPIO_NUM_0

void gpio_init(void) {
    // 输出配置
    gpio_config_t out_cfg = {
        .pin_bit_mask = (1ULL << LED_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&out_cfg);

    // 输入配置
    gpio_config_t in_cfg = {
        .pin_bit_mask = (1ULL << BUTTON_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_NEGEDGE,
    };
    gpio_config(&in_cfg);
}

// GPIO操作
gpio_set_level(LED_GPIO, 1);      // 高电平
gpio_set_level(LED_GPIO, 0);      // 低电平
int level = gpio_get_level(BUTTON_GPIO);  // 读取
gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);  // 设置方向
```

---

### 3.2 UART

```c
#include "driver/uart.h"

#define UART_NUM    UART_NUM_1
#define TXD_PIN     GPIO_NUM_17
#define RXD_PIN     GPIO_NUM_16
#define BUF_SIZE    1024

void uart_init(void) {
    const uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    uart_driver_install(UART_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, TXD_PIN, RXD_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
}

// 发送
uart_write_bytes(UART_NUM, "Hello", 5);

// 接收
uint8_t data[128];
int len = uart_read_bytes(UART_NUM, data, sizeof(data), pdMS_TO_TICKS(100));
```

---

### 3.3 I2C

```c
#include "driver/i2c_master.h"

#define I2C_FREQ    400000

i2c_master_bus_handle_t bus_handle;
i2c_master_dev_handle_t dev_handle;

void i2c_init(void) {
    // 总线配置
    i2c_master_bus_config_t bus_cfg = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = I2C_NUM_0,
        .scl_io_num = GPIO_NUM_22,
        .sda_io_num = GPIO_NUM_21,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_new_master_bus(&bus_cfg, &bus_handle);

    // 设备配置
    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = 0x68,  // MPU6050
        .scl_speed_hz = I2C_FREQ,
    };
    i2c_master_bus_add_device(bus_handle, &dev_cfg, &dev_handle);
}

// 写寄存器
void i2c_write_reg(uint8_t reg, uint8_t data) {
    uint8_t buf[2] = {reg, data};
    i2c_master_transmit(dev_handle, buf, 2, 100);
}

// 读寄存器
uint8_t i2c_read_reg(uint8_t reg) {
    uint8_t data;
    i2c_master_transmit_receive(dev_handle, &reg, 1, &data, 1, 100);
    return data;
}
```

---

### 3.4 SPI

```c
#include "driver/spi_master.h"

spi_device_handle_t spi;

void spi_init(void) {
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = GPIO_NUM_23,
        .miso_io_num = GPIO_NUM_19,
        .sclk_io_num = GPIO_NUM_18,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };
    spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 10 * 1000 * 1000,  // 10MHz
        .mode = 0,
        .spics_io_num = GPIO_NUM_5,
        .queue_size = 7,
    };
    spi_bus_add_device(SPI2_HOST, &dev_cfg, &spi);
}

// 传输
spi_transaction_t trans = {
    .length = 8 * len,
    .tx_buffer = tx_data,
    .rx_buffer = rx_data,
};
spi_device_polling_transmit(spi, &trans);
```

---

### 3.5 ADC

```c
#include "driver/adc_oneshot.h"
#include "esp_adc/adc_cali.h"

adc_oneshot_unit_handle_t adc1_handle;
adc_cali_handle_t cali_handle;

void adc_init(void) {
    // ADC初始化
    adc_oneshot_unit_init_cfg_t init_cfg = {
        .unit_id = ADC_UNIT_1,
    };
    adc_oneshot_new_unit(&init_cfg, &adc1_handle);

    // 通道配置
    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = ADC_ATTEN_DB_11,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_oneshot_config_channel(adc1_handle, ADC_CHANNEL_0, &chan_cfg);

    // 校准
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN_DB_11,
        .bitwidth = ADC_BITWIDTH_12,
    };
    adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali_handle);
}

// 读取ADC
int adc_read_voltage(void) {
    int raw, voltage;
    adc_oneshot_read(adc1_handle, ADC_CHANNEL_0, &raw);
    adc_cali_raw_to_voltage(cali_handle, raw, &voltage);
    return voltage;  // mV
}
```

---

### 3.6 PWM(LEDC)

```c
#include "driver/ledc.h"

#define LEDC_TIMER      LEDC_TIMER_0
#define LEDC_MODE       LEDC_LOW_SPEED_MODE
#define LEDC_CHANNEL    LEDC_CHANNEL_0
#define LEDC_GPIO       GPIO_NUM_2
#define LEDC_DUTY_RES   LEDC_TIMER_13_BIT
#define LEDC_FREQUENCY  5000

void pwm_init(void) {
    // 定时器配置
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_MODE,
        .duty_resolution = LEDC_DUTY_RES,
        .timer_num = LEDC_TIMER,
        .freq_hz = LEDC_FREQUENCY,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_cfg);

    // 通道配置
    ledc_channel_config_t channel_cfg = {
        .speed_mode = LEDC_MODE,
        .channel = LEDC_CHANNEL,
        .timer_sel = LEDC_TIMER,
        .gpio_num = LEDC_GPIO,
        .duty = 0,
        .hpoint = 0,
    };
    ledc_channel_config(&channel_cfg);
}

// 设置占空比
void pwm_set_duty(uint32_t duty) {
    ledc_set_duty(LEDC_MODE, LEDC_CHANNEL, duty);
    ledc_update_duty(LEDC_MODE, LEDC_CHANNEL);
}

// 渐变
void pwm_fade(uint32_t target_duty, uint32_t time_ms) {
    ledc_set_fade_with_time(LEDC_MODE, LEDC_CHANNEL, target_duty, time_ms);
    ledc_fade_func_install(0);
    ledc_cbs_t cbs = { .fade_cb = NULL };
    ledc_cb_register(LEDC_MODE, LEDC_CHANNEL, &cbs, NULL);
    ledc_fade_start(LEDC_MODE, LEDC_CHANNEL, LEDC_FADE_NO_WAIT);
}
```

---

## 四、WiFi应用

### 4.1 STA模式

```c
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

void wifi_init_sta(void) {
    // NVS初始化
    nvs_flash_init();

    // 网络初始化
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    // WiFi初始化
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    // 注册事件
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, ip_event_handler, NULL);

    // 配置
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "MyWiFi",
            .password = "password123",
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
    esp_wifi_connect();
}

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    if (id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();  // 自动重连
    }
}

static void ip_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    ip_event_got_ip_t *event = (ip_event_got_ip_t *)data;
    printf("IP: " IPSTR "\n", IP2STR(&event->ip_info.ip));
}
```

---

### 4.2 AP模式

```c
void wifi_init_softap(void) {
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "ESP32_AP",
            .ssid_len = strlen("ESP32_AP"),
            .channel = 1,
            .password = "12345678",
            .max_connection = 4,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    esp_wifi_start();
}
```

---

## 五、事件系统

### 5.1 事件循环

```c
#include "esp_event.h"

// 定义事件
ESP_EVENT_DEFINE_BASE(MY_EVENTS);

enum {
    MY_EVENT_SENSOR_DATA,
    MY_EVENT_BUTTON_PRESS,
    MY_EVENT_ERROR,
};

// 事件处理函数
static void sensor_event_handler(void *arg, esp_event_base_t base,
                                  int32_t id, void *data) {
    int sensor_value = *(int *)data;
    printf("Sensor: %d\n", sensor_value);
}

void event_init(void) {
    // 创建默认事件循环
    esp_event_loop_create_default();

    // 注册事件处理
    esp_event_handler_register(MY_EVENTS, MY_EVENT_SENSOR_DATA,
                                sensor_event_handler, NULL);
}

// 发送事件
void send_sensor_event(int value) {
    esp_event_post(MY_EVENTS, MY_EVENT_SENSOR_DATA, &value, sizeof(value), portMAX_DELAY);
}
```

---

## 六、NVS存储

### 6.1 NVS操作

```c
#include "nvs_flash.h"
#include "nvs.h"

void nvs_init(void) {
    nvs_flash_init();
}

// 写入
void nvs_save_int(const char *key, int32_t value) {
    nvs_handle_t handle;
    nvs_open("storage", NVS_READWRITE, &handle);
    nvs_set_i32(handle, key, value);
    nvs_commit(handle);
    nvs_close(handle);
}

// 读取
int32_t nvs_read_int(const char *key, int32_t default_value) {
    nvs_handle_t handle;
    int32_t value = default_value;

    if (nvs_open("storage", NVS_READONLY, &handle) == ESP_OK) {
        nvs_get_i32(handle, key, &value);
        nvs_close(handle);
    }
    return value;
}

// 写入字符串
void nvs_save_string(const char *key, const char *value) {
    nvs_handle_t handle;
    nvs_open("storage", NVS_READWRITE, &handle);
    nvs_set_str(handle, key, value);
    nvs_commit(handle);
    nvs_close(handle);
}
```

---

## 七、定时器

### 7.1 硬件定时器

```c
#include "driver/gptimer.h"

gptimer_handle_t timer;

static bool IRAM_ATTR timer_callback(gptimer_handle_t timer,
                                      const gptimer_alarm_event_data_t *edata,
                                      void *user_data) {
    // ISR中执行
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xTaskNotifyFromISR(task_handle, 0, eNoAction, &xHigherPriorityTaskWoken);
    return xHigherPriorityTaskWoken == pdTRUE;
}

void timer_init(void) {
    gptimer_config_t config = {
        .clk_src = GPTIMER_CLK_SRC_DEFAULT,
        .direction = GPTIMER_COUNT_UP,
        .resolution_hz = 1000000,  // 1MHz
    };
    gptimer_new_timer(&config, &timer);

    gptimer_alarm_config_t alarm_cfg = {
        .reload_count = 0,
        .alarm_count = 1000000,  // 1秒
        .flags.auto_reload_on_alarm = true,
    };
    gptimer_set_alarm_action(timer, &alarm_cfg);

    gptimer_event_callbacks_t cbs = {
        .on_alarm = timer_callback,
    };
    gptimer_register_event_callbacks(timer, &cbs, NULL);

    gptimer_enable(timer);
    gptimer_start(timer);
}
```

---

## 八、低功耗

### 8.1 睡眠模式

```c
#include "esp_sleep.h"

// 深度睡眠
void enter_deep_sleep(uint64_t sleep_time_sec) {
    esp_sleep_enable_timer_wakeup(sleep_time_sec * 1000000ULL);
    esp_deep_sleep_start();
}

// Light Sleep
void enter_light_sleep(uint64_t sleep_time_sec) {
    esp_sleep_enable_timer_wakeup(sleep_time_sec * 1000000ULL);
    esp_light_sleep_start();
}

// 唤醒原因
void check_wakeup_cause(void) {
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();

    switch (cause) {
        case ESP_SLEEP_WAKEUP_TIMER:
            printf("Wakeup by timer\n");
            break;
        case ESP_SLEEP_WAKEUP_GPIO:
            printf("Wakeup by GPIO\n");
            break;
        default:
            printf("Wakeup cause: %d\n", cause);
            break;
    }
}

// GPIO唤醒
void setup_gpio_wakeup(void) {
    esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);  // 低电平唤醒
}
```

---

## 九、OTA升级

### 9.1 OTA配置

```c
#include "esp_ota_ops.h"
#include "esp_http_client.h"

void ota_update(const char *url) {
    esp_http_client_config_t config = {
        .url = url,
    };

    esp_https_ota_config_t ota_config = {
        .http_config = &config,
    };

    esp_https_ota_handle_t ota_handle;
    esp_https_ota_begin(&ota_config, &ota_handle);

    // 下载并写入
    while (1) {
        esp_err_t err = esp_https_ota_perform(ota_handle);
        if (err == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            continue;
        }
        if (err == ESP_OK) {
            break;
        }
    }

    // 完成
    esp_https_ota_finish(ota_handle);

    // 重启
    esp_restart();
}
```

---

## 十、调试工具

### 10.1 日志系统

```c
#include "esp_log.h"

static const char *TAG = "MY_APP";

void app_main(void) {
    ESP_LOGI(TAG, "Info message");
    ESP_LOGW(TAG, "Warning: %d", 42);
    ESP_LOGE(TAG, "Error: %s", "failed");
    ESP_LOGD(TAG, "Debug info");
    ESP_LOGV(TAG, "Verbose");
}
```

---

### 10.2 核心转储

```bash
# 启用核心转储
idf.py menuconfig
# Component config → ESP Core dump → Enable core dump

# 分析核心转储
idf.py coredump
```

---

## 附录：常用命令

| 命令 | 说明 |
|------|------|
| idf.py build | 构建 |
| idf.py flash | 烧录 |
| idf.py monitor | 监控 |
| idf.py menuconfig | 配置 |
| idf.py clean | 清理 |
| idf.py size | 查看大小 |
| idf.py set-target | 设置目标芯片 |

---

## 相关链接

- [[STM32基础]] - STM32对比
- [[FreeRTOS基础]] - FreeRTOS详解
- [[WiFi应用]] - WiFi应用
- [[物联网协议]] - MQTT/CoAP
