# ESP-IDF UART串口通信 （异步串行通信与数据收发）

## 核心概念

- **UART** - 通用异步收发传输器，全双工异步串行通信
- **波特率** - 每秒传输的比特数，常见9600/115200/921600
- **帧格式** - 起始位+数据位+校验位+停止位
- **FIFO** - 硬件缓冲区，减少CPU中断频率

---

## 一、UART基础配置

### 1.1 UART初始化

```c
#include "driver/uart.h"

// UART配置
uart_config_t uart_config = {
    .baud_rate = 115200,                    // 波特率
    .data_bits = UART_DATA_8_BITS,          // 数据位
    .parity = UART_PARITY_DISABLE,          // 校验位
    .stop_bits = UART_STOP_BITS_1,          // 停止位
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,  // 流控
    .source_clk = UART_SCLK_DEFAULT,        // 时钟源
};

// 参数配置
ESP_ERROR_CHECK(uart_param_config(UART_NUM_1, &uart_config));

// 设置引脚
ESP_ERROR_CHECK(uart_set_pin(UART_NUM_1, 
                             GPIO_NUM_10,    // TX
                             GPIO_NUM_9,     // RX
                             UART_PIN_NO_CHANGE,  // RTS
                             UART_PIN_NO_CHANGE)); // CTS

// 安装驱动
const int uart_buffer_size = (1024 * 2);
ESP_ERROR_CHECK(uart_driver_install(UART_NUM_1, 
                                    uart_buffer_size,  // RX缓冲区
                                    uart_buffer_size,  // TX缓冲区
                                    20,                // 队列大小
                                    NULL,              // 队列句柄（可选）
                                    0));               // 中断标志
```

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `baud_rate` | 波特率 | 9600, 115200, 921600 |
| `data_bits` | 数据位 | `UART_DATA_5/6/7/8_BITS` |
| `parity` | 校验 | `DISABLE/EVEN/ODD` |
| `stop_bits` | 停止位 | `UART_STOP_BITS_1/1_5/2` |
| `flow_ctrl` | 流控 | `DISABLE/RTS/CTS/CTS_RTS` |

---

### 1.2 串口参数详解

```
UART帧格式：

起始位    D0    D1    D2    D3    D4    D5    D6    D7    校验   停止
  │      │     │     │     │     │     │     │     │      │      │
  ▼      ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼      ▼      ▼
─┴┬─────┬┴┬───┬┴┬───┬┴┬───┬┴┬───┬┴┬───┬┴┬───┬┴┬───┬┴┬───┬┴┬─────┬┴───
  │  0  │ 1 │ 0 │ 1 │ 0 │ 0 │ 0 │ 1 │ P │  1  │
  └─────┘   └────────── 数据位(8bit) ──────────┘   └─────┘
  起始位(低)                              校验位    停止位(高)

典型配置: 115200, 8, N, 1
- 波特率: 115200 bps
- 数据位: 8 bits
- 校验: None
- 停止位: 1 bit
```

---

## 二、数据发送

### 2.1 阻塞发送

```c
// 阻塞发送（等待发送完成）
const char *data = "Hello ESP32\r\n";
int len = strlen(data);
int txBytes = uart_write_bytes(UART_NUM_1, data, len);

ESP_LOGI(TAG, "Sent %d bytes", txBytes);
```

---

### 2.2 格式化发送

```c
// 使用printf风格发送
uart_write_bytes_with_break(UART_NUM_1, "Data:\r\n", 7, 100);

// 格式化字符串发送
char buffer[128];
int len = snprintf(buffer, sizeof(buffer), 
                   "Temp: %.2f, Hum: %.2f\r\n", temperature, humidity);
uart_write_bytes(UART_NUM_1, buffer, len);
```

---

### 2.3 发送完成检测

```c
// 等待发送完成（FIFO和移位寄存器都空）
ESP_ERROR_CHECK(uart_wait_tx_done(UART_NUM_1, 100));  // 超时100ms

// 检查发送状态
int tx_fifo_len = uart_get_tx_buffer_free_size(UART_NUM_1);
ESP_LOGI(TAG, "TX FIFO free: %d bytes", tx_fifo_len);
```

---

## 三、数据接收

### 3.1 阻塞接收

```c
uint8_t data[128];
int len = uart_read_bytes(UART_NUM_1, 
                          data, 
                          sizeof(data) - 1, 
                          pdMS_TO_TICKS(100));  // 超时100ms

if (len > 0) {
    data[len] = '\0';
    ESP_LOGI(TAG, "Received: %s", data);
}
```

---

### 3.2 查询方式接收

```c
// 检查接收缓冲区数据量
int rx_fifo_len;
ESP_ERROR_CHECK(uart_get_buffered_data_len(UART_NUM_1, (size_t *)&rx_fifo_len));

if (rx_fifo_len > 0) {
    uint8_t data[rx_fifo_len];
    int len = uart_read_bytes(UART_NUM_1, data, rx_fifo_len, 0);
    // 处理数据
}
```

---

### 3.3 事件驱动接收

```c
// 创建事件队列
QueueHandle_t uart_queue;
uart_driver_install(UART_NUM_1, 
                    uart_buffer_size, 
                    uart_buffer_size, 
                    20, 
                    &uart_queue,  // 事件队列
                    0);

// 接收任务
void uart_event_task(void *pvParameters)
{
    uart_event_t event;
    uint8_t *data = (uint8_t *)malloc(BUF_SIZE);
    
    while (1) {
        // 等待UART事件
        if (xQueueReceive(uart_queue, (void *)&event, portMAX_DELAY)) {
            switch (event.type) {
                case UART_DATA:
                    // 接收到数据
                    uart_read_bytes(UART_NUM_1, data, event.size, portMAX_DELAY);
                    ESP_LOGI(TAG, "[DATA]: %d bytes", event.size);
                    break;
                    
                case UART_FIFO_OVF:
                    ESP_LOGW(TAG, "FIFO overflow");
                    uart_flush_input(UART_NUM_1);
                    break;
                    
                case UART_BUFFER_FULL:
                    ESP_LOGW(TAG, "Buffer full");
                    uart_flush_input(UART_NUM_1);
                    break;
                    
                case UART_BREAK:
                    ESP_LOGI(TAG, "UART break detected");
                    break;
                    
                case UART_FRAME_ERR:
                    ESP_LOGE(TAG, "Frame error");
                    break;
                    
                case UART_PARITY_ERR:
                    ESP_LOGE(TAG, "Parity error");
                    break;
                    
                default:
                    break;
            }
        }
    }
    free(data);
    vTaskDelete(NULL);
}
```

---

## 四、事件驱动接收

### 4.1 UART事件类型

| 事件类型 | 说明 | 处理建议 |
|----------|------|----------|
| `UART_DATA` | 接收到数据 | 读取并处理数据 |
| `UART_BREAK` | 检测到Break信号 | 通常表示帧结束 |
| `UART_BUFFER_FULL` | 缓冲区满 | 清空缓冲区 |
| `UART_FIFO_OVF` | FIFO溢出 | 清空FIFO |
| `UART_FRAME_ERR` | 帧错误 | 记录错误 |
| `UART_PARITY_ERR` | 校验错误 | 记录错误 |
| `UART_DATA_BREAK` | 数据后带Break | 特殊协议处理 |

---

### 4.2 事件处理架构

```
UART事件处理流程：

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   数据接收      │     │   错误处理      │     │   状态监控      │
│   UART_DATA     │     │   ERR events    │     │   Pattern检测   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UART事件队列                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     uart_event_task                              │
│              (从队列取出事件并分发处理)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、流控与硬件握手

### 5.1 RTS/CTS流控

```c
// 启用硬件流控
uart_config_t uart_config = {
    .baud_rate = 115200,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_DISABLE,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_CTS_RTS,  // 启用RTS/CTS
    .rx_flow_ctrl_thresh = 122,              // RTS阈值
};

// 设置流控引脚
uart_set_pin(UART_NUM_1, 
             GPIO_NUM_10,    // TX
             GPIO_NUM_9,     // RX
             GPIO_NUM_11,    // RTS
             GPIO_NUM_6);    // CTS
```

**RTS/CTS工作原理：**

```
发送方(ESP32)              接收方(设备)
     │                          │
     │  TX ─────────────────>   │
     │         数据             │
     │                          │
     │ <───────────────── CTS   │
     │    (清除发送=允许发送)    │
     │                          │
     │  RTS ─────────────────>  │
     │    (请求发送=接收就绪)    │
     │                          │

CTS=0: 允许发送
CTS=1: 停止发送
RTS=0: 接收就绪
RTS=1: 接收缓冲区满
```

---

### 5.2 RS485模式

```c
// RS485半双工配置
ESP_ERROR_CHECK(uart_set_mode(UART_NUM_1, UART_MODE_RS485_HALF_DUPLEX));

// 设置RS485引脚
ESP_ERROR_CHECK(uart_set_rs485_pins(UART_NUM_1, 
                                    GPIO_NUM_10,  // TX
                                    GPIO_NUM_9,   // RX
                                    GPIO_NUM_11,  // RTS(DE/RE)
                                    GPIO_NUM_NC)); // CTS

// 配置RTS切换延迟（防止总线冲突）
ESP_ERROR_CHECK(uart_set_rs485_timing(UART_NUM_1, 10, 10));  // 10bit延迟
```

---

## 六、多UART实例

### 6.1 ESP32 UART资源

| UART | 默认引脚 | 用途 |
|------|----------|------|
| UART0 | GPIO1(TX)/GPIO3(RX) | 串口下载、调试输出 |
| UART1 | GPIO10(TX)/GPIO9(RX) | 用户可用 |
| UART2 | GPIO17(TX)/GPIO16(RX) | 用户可用 |

---

### 6.2 多串口配置

```c
// UART0 - 调试输出（使用默认引脚）
uart_config_t uart0_config = {
    .baud_rate = 115200,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_DISABLE,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
};
uart_param_config(UART_NUM_0, &uart0_config);
uart_driver_install(UART_NUM_0, 256, 256, 0, NULL, 0);

// UART1 - 连接传感器
uart_config_t uart1_config = {
    .baud_rate = 9600,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_DISABLE,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
};
uart_param_config(UART_NUM_1, &uart1_config);
uart_set_pin(UART_NUM_1, GPIO_NUM_10, GPIO_NUM_9, 
             UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
uart_driver_install(UART_NUM_1, 1024, 1024, 20, &uart1_queue, 0);

// UART2 - 连接Modbus设备
uart_config_t uart2_config = {
    .baud_rate = 19200,
    .data_bits = UART_DATA_8_BITS,
    .parity = UART_PARITY_EVEN,
    .stop_bits = UART_STOP_BITS_1,
    .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
};
uart_param_config(UART_NUM_2, &uart2_config);
uart_set_pin(UART_NUM_2, GPIO_NUM_17, GPIO_NUM_16, 
             UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
uart_driver_install(UART_NUM_2, 1024, 1024, 20, &uart2_queue, 0);
```

---

## 七、完整示例

### 示例1：串口命令解析器

```c
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"

static const char *TAG = "CMD_PARSER";

#define UART_NUM        UART_NUM_1
#define TX_PIN          GPIO_NUM_10
#define RX_PIN          GPIO_NUM_9
#define BUF_SIZE        256

// 命令表
typedef struct {
    const char *cmd;
    void (*handler)(const char *args);
} cmd_table_t;

void cmd_help(const char *args);
void cmd_led(const char *args);
void cmd_status(const char *args);

cmd_table_t commands[] = {
    {"help", cmd_help},
    {"led", cmd_led},
    {"status", cmd_status},
    {NULL, NULL}
};

void cmd_help(const char *args)
{
    const char *msg = "Commands: help, led on/off, status\r\n";
    uart_write_bytes(UART_NUM, msg, strlen(msg));
}

void cmd_led(const char *args)
{
    if (strstr(args, "on")) {
        // gpio_set_level(LED_GPIO, 1);
        uart_write_bytes(UART_NUM, "LED ON\r\n", 8);
    } else if (strstr(args, "off")) {
        // gpio_set_level(LED_GPIO, 0);
        uart_write_bytes(UART_NUM, "LED OFF\r\n", 9);
    } else {
        uart_write_bytes(UART_NUM, "Usage: led on/off\r\n", 19);
    }
}

void cmd_status(const char *args)
{
    char buf[64];
    snprintf(buf, sizeof(buf), "Uptime: %lu ms\r\n", 
             xTaskGetTickCount() * portTICK_PERIOD_MS);
    uart_write_bytes(UART_NUM, buf, strlen(buf));
}

void parse_command(const char *line)
{
    char cmd[32];
    const char *args = "";
    
    // 提取命令和参数
    sscanf(line, "%31s", cmd);
    args = strchr(line, ' ');
    if (args) args++;  // 跳过空格
    
    // 查找并执行命令
    for (int i = 0; commands[i].cmd != NULL; i++) {
        if (strcasecmp(cmd, commands[i].cmd) == 0) {
            commands[i].handler(args ? args : "");
            return;
        }
    }
    
    uart_write_bytes(UART_NUM, "Unknown command\r\n", 16);
}

void uart_task(void *pvParameters)
{
    uint8_t data[BUF_SIZE];
    char line[BUF_SIZE];
    int line_pos = 0;
    
    while (1) {
        int len = uart_read_bytes(UART_NUM, data, BUF_SIZE - 1, pdMS_TO_TICKS(100));
        
        if (len > 0) {
            for (int i = 0; i < len; i++) {
                char c = data[i];
                
                // 回显
                uart_write_bytes(UART_NUM, &c, 1);
                
                if (c == '\r' || c == '\n') {
                    if (line_pos > 0) {
                        line[line_pos] = '\0';
                        parse_command(line);
                        line_pos = 0;
                    }
                    uart_write_bytes(UART_NUM, "\r\n", 2);
                } else if (line_pos < BUF_SIZE - 1) {
                    line[line_pos++] = c;
                }
            }
        }
    }
}

void uart_init(void)
{
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, TX_PIN, RX_PIN, 
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 0, NULL, 0);
    
    ESP_LOGI(TAG, "UART initialized on GPIO TX=%d RX=%d", TX_PIN, RX_PIN);
}

void app_main(void)
{
    uart_init();
    
    const char *welcome = "\r\nESP32 Command Parser\r\nType 'help' for commands\r\n> ";
    uart_write_bytes(UART_NUM, welcome, strlen(welcome));
    
    xTaskCreate(uart_task, "uart_task", 4096, NULL, 10, NULL);
}
```

---

### 示例2：与PC串口助手通信

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"

static const char *TAG = "PC_COMM";

#define UART_NUM        UART_NUM_1
#define TX_PIN          GPIO_NUM_10
#define RX_PIN          GPIO_NUM_9
#define BUF_SIZE        1024

void pc_comm_task(void *pvParameters)
{
    uint8_t *data = (uint8_t *)malloc(BUF_SIZE);
    
    // 发送启动消息
    const char *msg = "ESP32 Ready\r\n";
    uart_write_bytes(UART_NUM, msg, strlen(msg));
    
    while (1) {
        // 读取数据
        int len = uart_read_bytes(UART_NUM, data, BUF_SIZE - 1, pdMS_TO_TICKS(100));
        
        if (len > 0) {
            data[len] = '\0';
            ESP_LOGI(TAG, "Received %d bytes: %s", len, data);
            
            // 回传接收到的数据（echo）
            uart_write_bytes(UART_NUM, "Echo: ", 6);
            uart_write_bytes(UART_NUM, data, len);
            uart_write_bytes(UART_NUM, "\r\n", 2);
        }
        
        // 定期发送心跳
        static uint32_t last_heartbeat = 0;
        if (xTaskGetTickCount() - last_heartbeat > pdMS_TO_TICKS(5000)) {
            char heartbeat[64];
            snprintf(heartbeat, sizeof(heartbeat), 
                     "[Heartbeat] Uptime: %lu s\r\n",
                     xTaskGetTickCount() * portTICK_PERIOD_MS / 1000);
            uart_write_bytes(UART_NUM, heartbeat, strlen(heartbeat));
            last_heartbeat = xTaskGetTickCount();
        }
    }
    
    free(data);
}

void app_main(void)
{
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, TX_PIN, RX_PIN, 
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 0, NULL, 0);
    
    xTaskCreate(pc_comm_task, "pc_comm", 4096, NULL, 10, NULL);
}
```

---

### 示例3：Modbus RTU从机实现

```c
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_crc.h"

static const char *TAG = "MODBUS_SLAVE";

#define UART_NUM        UART_NUM_2
#define TX_PIN          GPIO_NUM_17
#define RX_PIN          GPIO_NUM_16
#define BUF_SIZE        256
#define SLAVE_ID        0x01

// Modbus功能码
#define FUNC_READ_COILS         0x01
#define FUNC_READ_DISCRETE      0x02
#define FUNC_READ_HOLDING       0x03
#define FUNC_READ_INPUT         0x04
#define FUNC_WRITE_SINGLE_COIL  0x05
#define FUNC_WRITE_SINGLE_REG   0x06

// 模拟寄存器
static uint16_t holding_regs[100] = {0};

// CRC16计算
uint16_t modbus_crc(uint8_t *data, uint16_t len)
{
    return esp_crc16_le(0xFFFF, data, len);
}

// 构建响应
int build_response(uint8_t *req, uint8_t *resp, int req_len)
{
    int resp_len = 0;
    uint8_t slave_id = req[0];
    uint8_t func_code = req[1];
    
    resp[resp_len++] = slave_id;
    resp[resp_len++] = func_code;
    
    switch (func_code) {
        case FUNC_READ_HOLDING: {
            uint16_t addr = (req[2] << 8) | req[3];
            uint16_t qty = (req[4] << 8) | req[5];
            
            resp[resp_len++] = qty * 2;  // 字节数
            
            for (int i = 0; i < qty; i++) {
                uint16_t value = holding_regs[addr + i];
                resp[resp_len++] = value >> 8;
                resp[resp_len++] = value & 0xFF;
            }
            break;
        }
        
        case FUNC_WRITE_SINGLE_REG: {
            uint16_t addr = (req[2] << 8) | req[3];
            uint16_t value = (req[4] << 8) | req[5];
            
            holding_regs[addr] = value;
            
            // 回传请求
            memcpy(&resp[2], &req[2], 4);
            resp_len += 4;
            break;
        }
        
        default:
            // 异常响应
            resp[1] = func_code | 0x80;
            resp[2] = 0x01;  // 非法功能码
            resp_len = 3;
            break;
    }
    
    // 添加CRC
    uint16_t crc = modbus_crc(resp, resp_len);
    resp[resp_len++] = crc & 0xFF;
    resp[resp_len++] = crc >> 8;
    
    return resp_len;
}

void modbus_task(void *pvParameters)
{
    uint8_t rx_buf[BUF_SIZE];
    uint8_t tx_buf[BUF_SIZE];
    
    ESP_LOGI(TAG, "Modbus slave started, ID=0x%02X", SLAVE_ID);
    
    while (1) {
        int len = uart_read_bytes(UART_NUM, rx_buf, BUF_SIZE, 
                                  pdMS_TO_TICKS(100));
        
        if (len >= 4) {  // 最小帧：ID + FUNC + CRC(2)
            // 验证CRC
            uint16_t rx_crc = (rx_buf[len-1] << 8) | rx_buf[len-2];
            uint16_t calc_crc = modbus_crc(rx_buf, len - 2);
            
            if (rx_crc == calc_crc && rx_buf[0] == SLAVE_ID) {
                ESP_LOGI(TAG, "Valid frame received: func=0x%02X", rx_buf[1]);
                
                // 构建响应
                int resp_len = build_response(rx_buf, tx_buf, len);
                
                // 发送响应
                uart_write_bytes(UART_NUM, tx_buf, resp_len);
                uart_wait_tx_done(UART_NUM, 100);
            }
        }
    }
}

void app_main(void)
{
    // Modbus通常用9600,8,E,1或19200,8,E,1
    uart_config_t uart_config = {
        .baud_rate = 19200,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_EVEN,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, TX_PIN, RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 0, NULL, 0);
    
    xTaskCreate(modbus_task, "modbus", 4096, NULL, 10, NULL);
}
```

---

## 附录：UART API速查表

### 配置API

| API | 说明 |
|-----|------|
| `uart_param_config()` | 配置UART参数 |
| `uart_set_pin()` | 设置UART引脚 |
| `uart_set_baudrate()` | 设置波特率 |
| `uart_set_word_length()` | 设置数据位 |
| `uart_set_parity()` | 设置校验位 |
| `uart_set_stop_bits()` | 设置停止位 |
| `uart_driver_install()` | 安装UART驱动 |
| `uart_driver_delete()` | 卸载UART驱动 |

### 数据收发

| API | 说明 |
|-----|------|
| `uart_write_bytes()` | 发送数据 |
| `uart_write_bytes_with_break()` | 发送数据+Break |
| `uart_read_bytes()` | 接收数据 |
| `uart_flush()` | 清空缓冲区 |
| `uart_flush_input()` | 清空输入缓冲区 |
| `uart_wait_tx_done()` | 等待发送完成 |

### 状态查询

| API | 说明 |
|-----|------|
| `uart_get_buffered_data_len()` | 获取接收缓冲区数据量 |
| `uart_get_tx_buffer_free_size()` | 获取TX FIFO空闲空间 |

### 流控与模式

| API | 说明 |
|-----|------|
| `uart_set_hw_flow_ctrl()` | 设置硬件流控 |
| `uart_set_mode()` | 设置UART模式 |
| `uart_set_rs485_pins()` | 设置RS485引脚 |
| `uart_set_line_inverse()` | 设置信号反转 |

### 事件处理

| API | 说明 |
|-----|------|
| `uart_enable_pattern_det_baud_intr()` | 启用模式检测中断 |
| `uart_pattern_get_pos()` | 获取模式位置 |
| `uart_pattern_pop_pos()` | 弹出模式位置 |
