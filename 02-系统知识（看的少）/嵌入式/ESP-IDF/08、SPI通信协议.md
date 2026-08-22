# ESP-IDF SPI通信协议 （高速同步串行总线通信）

## 核心概念

- **SPI** - Serial Peripheral Interface，四线同步串行总线（MOSI/MISO/SCLK/CS）
- **全双工通信** - 同时收发，数据传输效率高
- **时钟极性和相位** - CPOL和CPHA决定采样时机
- **多从设备** - 通过多个CS引脚控制不同设备

---

## 一、SPI总线原理

### 1.1 信号定义

```
SPI四线连接：

主设备(ESP32)                    从设备
┌─────────────┐                ┌─────────────┐
│             │── MOSI ───────>│ DI          │
│   SPIn      │                │   Slave     │
│  Controller │<─ MISO ────────│ DO          │
│             │                │             │
│             │── SCLK ───────>│ CLK         │
│             │                │             │
│             │── CS ─────────>│ CS          │
└─────────────┘                └─────────────┘

信号说明：
- MOSI: 主出从入 (Master Out Slave In)
- MISO: 主入从出 (Master In Slave Out)  
- SCLK: 串行时钟 (Serial Clock)
- CS:   片选 (Chip Select)，低电平有效
```

---

### 1.2 时钟模式

```
SPI时钟模式（CPOL=时钟极性，CPHA=时钟相位）：

Mode 0 (CPOL=0, CPHA=0):       Mode 1 (CPOL=0, CPHA=1):

SCLK ─┐   ┌─┐   ┌─┐           SCLK ───┐   ┌─┐   ┌─┐
      └───┘ └───┘ └───┘               └───┘ └───┘ └───┘
      ↑               ↑                 ↑               ↑
   采样             采样              设置            设置

Mode 2 (CPOL=1, CPHA=0):       Mode 3 (CPOL=1, CPHA=1):

SCLK  ┌───┐ ┌───┐ ┌──           SCLK ┌───┐ ┌───┐ ┌──
      └───┘ └───┘ └──               ┘   └───┘ └───┘
      ↑               ↑                 ↑               ↑
   采样             采样              设置            设置

常用设备模式：
- Mode 0: W25Qxx Flash, SSD1309 OLED
- Mode 3: ILI9341 LCD, MCP3008 ADC
```

| 模式 | CPOL | CPHA | 空闲时钟 | 采样边沿 |
|------|------|------|----------|----------|
| Mode 0 | 0 | 0 | 低 | 上升沿 |
| Mode 1 | 0 | 1 | 低 | 下降沿 |
| Mode 2 | 1 | 0 | 高 | 下降沿 |
| Mode 3 | 1 | 1 | 高 | 上升沿 |

---

## 二、SPI主设备配置

### 2.1 总线初始化

```c
#include "driver/spi_master.h"

// SPI总线配置
spi_bus_config_t bus_config = {
    .mosi_io_num = GPIO_NUM_13,     // MOSI引脚
    .miso_io_num = GPIO_NUM_12,     // MISO引脚
    .sclk_io_num = GPIO_NUM_14,     // SCLK引脚
    .quadwp_io_num = -1,            // WP（四线模式，不用设为-1）
    .quadhd_io_num = -1,            // HD（四线模式，不用设为-1）
    .max_transfer_sz = 4094,        // 最大传输大小
};

// 初始化SPI总线
ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_config, SPI_DMA_CH_AUTO));
```

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `mosi_io_num` | MOSI引脚 | 任意GPIO |
| `miso_io_num` | MISO引脚 | 任意GPIO |
| `sclk_io_num` | SCLK引脚 | 任意GPIO |
| `max_transfer_sz` | 最大传输 | 4094字节（DMA） |

---

### 2.2 设备配置

```c
// 设备接口配置
spi_device_interface_config_t dev_config = {
    .clock_speed_hz = 10 * 1000 * 1000,  // 10MHz
    .mode = 0,                            // SPI Mode 0
    .spics_io_num = GPIO_NUM_5,           // CS引脚
    .queue_size = 7,                      // 事务队列大小
    .flags = 0,                           // 标志
    .pre_cb = NULL,                       // 传输前回调
    .post_cb = NULL,                      // 传输后回调
};

// 添加设备到总线
spi_device_handle_t spi_dev;
ESP_ERROR_CHECK(spi_bus_add_device(SPI2_HOST, &dev_config, &spi_dev));
```

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `clock_speed_hz` | 时钟频率 | 最高80MHz |
| `mode` | SPI模式 | 0-3 |
| `spics_io_num` | CS引脚 | 任意GPIO |
| `queue_size` | 队列深度 | 1-7 |
| `cs_ena_pretrans` | CS提前时间 | 0（ns） |
| `cs_ena_posttrans` | CS延后时间 | 0（ns） |

---

## 三、数据传输模式

### 3.1 简单传输

```c
// 发送数据
uint8_t tx_data[] = {0x01, 0x02, 0x03};
spi_transaction_t t = {
    .length = 3 * 8,           // 总位数
    .tx_buffer = tx_data,      // 发送缓冲区
};
ESP_ERROR_CHECK(spi_device_transmit(spi_dev, &t));

// 接收数据
uint8_t rx_data[4];
spi_transaction_t t = {
    .length = 4 * 8,
    .rx_buffer = rx_data,
};
ESP_ERROR_CHECK(spi_device_transmit(spi_dev, &t));

// 同时收发（全双工）
uint8_t tx_rx_data[] = {0xAA, 0xBB, 0xCC};
spi_transaction_t t = {
    .length = 3 * 8,
    .tx_buffer = tx_rx_data,
    .rx_buffer = rx_rx_buf,    // 接收缓冲区
};
ESP_ERROR_CHECK(spi_device_transmit(spi_dev, &t));
```

---

### 3.2 命令+地址+数据格式

```c
// 多段传输：命令+地址+数据
spi_transaction_t t = {
    // 命令阶段
    .cmd = 0x02,               // 8位命令
    
    // 地址阶段  
    .addr = 0x001000,          // 24位地址
    
    // 数据阶段
    .length = 256 * 8,         // 数据长度（位）
    .tx_buffer = data_buffer,
    
    // 标志
    .flags = SPI_TRANS_USE_RXDATA | SPI_TRANS_USE_TXDATA,
};
ESP_ERROR_CHECK(spi_device_transmit(spi_dev, &t));
```

---

### 3.3 异步传输

```c
// 填充多个事务
spi_transaction_t trans[7];
for (int i = 0; i < 7; i++) {
    memset(&trans[i], 0, sizeof(spi_transaction_t));
    trans[i].length = 128 * 8;
    trans[i].tx_buffer = my_data + i * 128;
    trans[i].rx_buffer = my_rxbuf + i * 128;
    
    // 排队传输（非阻塞）
    ESP_ERROR_CHECK(spi_device_queue_trans(spi_dev, &trans[i], portMAX_DELAY));
}

// 稍后获取结果
spi_transaction_t *rtrans;
for (int i = 0; i < 7; i++) {
    ESP_ERROR_CHECK(spi_device_get_trans_result(spi_dev, &rtrans, portMAX_DELAY));
    // rtrans->rx_buffer 包含接收到的数据
}
```

---

## 四、多从设备管理

### 4.1 多个CS引脚

```c
// 设备1: Flash
spi_device_interface_config_t flash_cfg = {
    .clock_speed_hz = 20 * 1000 * 1000,
    .mode = 0,
    .spics_io_num = GPIO_NUM_5,    // CS1
    .queue_size = 1,
};
spi_device_handle_t flash_dev;
spi_bus_add_device(SPI2_HOST, &flash_cfg, &flash_dev);

// 设备2: LCD
spi_device_interface_config_t lcd_cfg = {
    .clock_speed_hz = 40 * 1000 * 1000,
    .mode = 0,
    .spics_io_num = GPIO_NUM_15,   // CS2
    .queue_size = 1,
};
spi_device_handle_t lcd_dev;
spi_bus_add_device(SPI2_HOST, &lcd_cfg, &lcd_dev);

// 设备3: SD卡
spi_device_interface_config_t sd_cfg = {
    .clock_speed_hz = 10 * 1000 * 1000,
    .mode = 0,
    .spics_io_num = GPIO_NUM_16,   // CS3
    .queue_size = 1,
};
spi_device_handle_t sd_dev;
spi_bus_add_device(SPI2_HOST, &sd_cfg, &sd_dev);
```

---

### 4.2 软件CS控制

```c
// 软件控制CS（用于特殊时序）
#define CS_PIN GPIO_NUM_5

gpio_set_direction(CS_PIN, GPIO_MODE_OUTPUT);
gpio_set_level(CS_PIN, 1);

// 手动拉低CS
gpio_set_level(CS_PIN, 0);

// 执行传输
spi_transaction_t t = {
    .length = 8,
    .tx_buffer = &cmd,
    .flags = SPI_TRANS_CS_KEEP_ACTIVE,  // 保持CS有效
};
spi_device_transmit(spi_dev, &t);

// 更多传输...

// 手动拉高CS
gpio_set_level(CS_PIN, 1);
```

---

## 五、SPI事务机制

### 5.1 事务配置结构

```c
typedef struct {
    uint32_t flags;              // 标志位
    uint16_t cmd;                // 命令（最多16位）
    uint64_t addr;               // 地址（最多64位）
    size_t length;               // 总数据长度（位）
    size_t rxlength;             // 接收长度（位）
    void *user;                  // 用户数据
    union {
        const void *tx_buffer;   // 发送缓冲区
        uint8_t tx_data[4];      // 内联发送数据（≤32位）
    };
    union {
        void *rx_buffer;         // 接收缓冲区
        uint8_t rx_data[4];      // 内联接收数据（≤32位）
    };
} spi_transaction_t;
```

| 标志 | 说明 |
|------|------|
| `SPI_TRANS_USE_RXDATA` | 使用rx_data字段 |
| `SPI_TRANS_USE_TXDATA` | 使用tx_data字段 |
| `SPI_TRANS_MODE_DIO` | 双线模式 |
| `SPI_TRANS_MODE_QIO` | 四线模式 |
| `SPI_TRANS_CS_KEEP_ACTIVE` | 传输后保持CS |
| `SPI_TRANS_VARIABLE_CMD` | 可变命令长度 |
| `SPI_TRANS_VARIABLE_ADDR` | 可变地址长度 |

---

### 5.2 批量传输

```c
// 使用DMA进行大容量传输
#define TRANS_SIZE 4094  // 最大DMA传输

uint8_t *tx_buf = heap_caps_malloc(TRANS_SIZE, MALLOC_CAP_DMA);
uint8_t *rx_buf = heap_caps_malloc(TRANS_SIZE, MALLOC_CAP_DMA);

// 填充发送数据
memset(tx_buf, 0xAA, TRANS_SIZE);

// 执行DMA传输
spi_transaction_t t = {
    .length = TRANS_SIZE * 8,
    .tx_buffer = tx_buf,
    .rx_buffer = rx_buf,
};
spi_device_transmit(spi_dev, &t);

// 清理
heap_caps_free(tx_buf);
heap_caps_free(rx_buf);
```

---

## 六、SPI从机模式

### 6.1 从机配置

```c
#include "driver/spi_slave.h"

// 从机总线配置
spi_bus_config_t buscfg = {
    .mosi_io_num = GPIO_NUM_13,
    .miso_io_num = GPIO_NUM_12,
    .sclk_io_num = GPIO_NUM_14,
    .quadwp_io_num = -1,
    .quadhd_io_num = -1,
};

// 从机接口配置
spi_slave_interface_config_t slvcfg = {
    .mode = 0,
    .spics_io_num = GPIO_NUM_15,
    .queue_size = 3,
    .flags = 0,
};

// 初始化从机
ESP_ERROR_CHECK(spi_slave_initialize(VSPI_HOST, &buscfg, &slvcfg, SPI_DMA_CH_AUTO));
```

---

### 6.2 从机数据传输

```c
// 准备接收缓冲区
WORD_ALIGNED_ATTR uint8_t recvbuf[129] = {0};
spi_slave_transaction_t t = {
    .length = 129 * 8,
    .tx_buffer = sendbuf,
    .rx_buffer = recvbuf,
};

// 等待主机传输完成
ESP_ERROR_CHECK(spi_slave_transmit(VSPI_HOST, &t, portMAX_DELAY));

// recvbuf现在包含接收到的数据
```

---

## 七、完整示例

### 示例1：W25Q64 Flash读写

```c
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_master.h"
#include "esp_log.h"

static const char *TAG = "W25Q64";

#define SPI_HOST        SPI2_HOST
#define PIN_MOSI        GPIO_NUM_13
#define PIN_MISO        GPIO_NUM_12
#define PIN_SCLK        GPIO_NUM_14
#define PIN_CS          GPIO_NUM_5

#define W25X_WRITE_ENABLE       0x06
#define W25X_WRITE_DISABLE      0x04
#define W25X_READ_STATUS        0x05
#define W25X_READ_DATA          0x03
#define W25X_PAGE_PROGRAM       0x02
#define W25X_SECTOR_ERASE       0x20
#define W25X_CHIP_ERASE         0xC7

static spi_device_handle_t spi;

// 发送命令
void w25q64_cmd(uint8_t cmd)
{
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &cmd,
    };
    spi_device_transmit(spi, &t);
}

// 读取状态寄存器
uint8_t w25q64_read_status(void)
{
    uint8_t tx_data[2] = {W25X_READ_STATUS, 0xFF};
    uint8_t rx_data[2];
    
    spi_transaction_t t = {
        .length = 16,
        .tx_buffer = tx_data,
        .rx_buffer = rx_data,
    };
    spi_device_transmit(spi, &t);
    
    return rx_data[1];
}

// 等待忙完成
void w25q64_wait_idle(void)
{
    while (w25q64_read_status() & 0x01) {
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// 擦除扇区
void w25q64_sector_erase(uint32_t addr)
{
    uint8_t cmd[4] = {W25X_SECTOR_ERASE, (addr >> 16) & 0xFF, 
                      (addr >> 8) & 0xFF, addr & 0xFF};
    
    w25q64_cmd(W25X_WRITE_ENABLE);
    
    spi_transaction_t t = {
        .length = 32,
        .tx_buffer = cmd,
    };
    spi_device_transmit(spi, &t);
    
    w25q64_wait_idle();
    ESP_LOGI(TAG, "Sector erased at 0x%06X", addr);
}

// 页写入
void w25q64_page_write(uint32_t addr, uint8_t *data, uint16_t len)
{
    if (len > 256) len = 256;
    
    uint8_t cmd[4] = {W25X_PAGE_PROGRAM, (addr >> 16) & 0xFF, 
                      (addr >> 8) & 0xFF, addr & 0xFF};
    
    w25q64_cmd(W25X_WRITE_ENABLE);
    
    // 发送命令
    spi_transaction_t t1 = {
        .length = 32,
        .tx_buffer = cmd,
    };
    spi_device_transmit(spi, &t1);
    
    // 发送数据
    spi_transaction_t t2 = {
        .length = len * 8,
        .tx_buffer = data,
    };
    spi_device_transmit(spi, &t2);
    
    w25q64_wait_idle();
}

// 读取数据
void w25q64_read(uint32_t addr, uint8_t *data, uint16_t len)
{
    uint8_t cmd[4] = {W25X_READ_DATA, (addr >> 16) & 0xFF, 
                      (addr >> 8) & 0xFF, addr & 0xFF};
    
    // 发送读取命令和地址
    spi_transaction_t t1 = {
        .length = 32,
        .tx_buffer = cmd,
    };
    spi_device_transmit(spi, &t1);
    
    // 接收数据
    spi_transaction_t t2 = {
        .length = len * 8,
        .rx_buffer = data,
    };
    spi_device_transmit(spi, &t2);
}

void app_main(void)
{
    // 初始化SPI总线
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_MOSI,
        .miso_io_num = PIN_MISO,
        .sclk_io_num = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI_HOST, &buscfg, SPI_DMA_CH_AUTO));
    
    // 添加Flash设备
    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 20 * 1000 * 1000,  // 20MHz
        .mode = 0,
        .spics_io_num = PIN_CS,
        .queue_size = 7,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI_HOST, &devcfg, &spi));
    
    ESP_LOGI(TAG, "W25Q64 initialized");
    
    // 测试读写
    uint32_t test_addr = 0x001000;
    uint8_t write_data[256];
    uint8_t read_data[256];
    
    for (int i = 0; i < 256; i++) {
        write_data[i] = i;
    }
    
    // 擦除扇区
    w25q64_sector_erase(test_addr);
    
    // 写入数据
    w25q64_page_write(test_addr, write_data, 256);
    ESP_LOGI(TAG, "Data written");
    
    // 读取数据
    w25q64_read(test_addr, read_data, 256);
    
    // 验证
    bool match = true;
    for (int i = 0; i < 256; i++) {
        if (read_data[i] != write_data[i]) {
            match = false;
            break;
        }
    }
    
    ESP_LOGI(TAG, "Verify: %s", match ? "PASS" : "FAIL");
}
```

---

## 附录：SPI API速查表

### 总线管理

| API | 说明 |
|-----|------|
| `spi_bus_initialize()` | 初始化SPI总线 |
| `spi_bus_free()` | 释放SPI总线 |
| `spi_bus_add_device()` | 添加设备 |
| `spi_bus_remove_device()` | 移除设备 |

### 数据传输

| API | 说明 |
|-----|------|
| `spi_device_transmit()` | 同步传输 |
| `spi_device_queue_trans()` | 排队传输（异步） |
| `spi_device_get_trans_result()` | 获取传输结果 |
| `spi_device_polling_transmit()` | 轮询传输 |

### 从机模式

| API | 说明 |
|-----|------|
| `spi_slave_initialize()` | 初始化从机 |
| `spi_slave_free()` | 释放从机 |
| `spi_slave_transmit()` | 从机传输 |

### 配置参数

| 参数 | 说明 |
|------|------|
| `SPI2_HOST/SPI3_HOST` | SPI主机编号 |
| `SPI_DMA_CH_AUTO` | 自动DMA通道选择 |
| `SPI_TRANS_USE_RXDATA` | 使用内联接收数据 |
| `SPI_TRANS_USE_TXDATA` | 使用内联发送数据 |
