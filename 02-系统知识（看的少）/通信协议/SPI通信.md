# SPI通信 （同步串行 全双工 四线制 主从模式）

## 核心概念

### 基本原理
- ==同步通信== - 有时钟线SCK，主机产生时钟
- ==全双工== - 发送和接收同时进行
- ==四线制== - SCK、MOSI、MISO、CS（片选）
- ==主从模式== - 主机控制时钟和片选

### 信号线定义
| 信号 | 方向 | 说明 |
|------|------|------|
| SCK | 主→从 | 时钟信号 |
| MOSI | 主→从 | 主机输出，从机输入 |
| MISO | 从→主 | 从机输出，主机输入 |
| CS/SS | 主→从 | 片选信号（低有效） |

---

## 一、SPI四种工作模式

### 1.1 CPOL与CPHA定义

| 模式 | CPOL | CPHA | 说明 |
|------|------|------|------|
| Mode 0 | 0 | 0 | SCK空闲低电平，第一个边沿采样 |
| Mode 1 | 0 | 1 | SCK空闲低电平，第二个边沿采样 |
| Mode 2 | 1 | 0 | SCK空闲高电平，第一个边沿采样 |
| Mode 3 | 1 | 1 | SCK空闲高电平，第二个边沿采样 |

### 1.2 时序图示

```
Mode 0 (CPOL=0, CPHA=0):
SCK:  ──┐_┌─_┌─_┌─_┌─
        ↑ ↑ ↑ ↑ ↑ ↑
        第1 第2 第3 第4 第5 第6 边沿
MOSI: 数据在第1边沿采样（上升沿）

Mode 1 (CPOL=0, CPHA=1):
SCK:  ──┐_┌─_┌─_┌─_┌─
          ↓ ↓ ↓ ↓ ↓ ↓
          第2边沿采样（下降沿）
```

> [!TIP] 模式选择
> 大多数SPI设备使用Mode 0或Mode 3，需参考设备数据手册

---

## 二、STM32 SPI初始化

### 2.1 SPI结构体配置

```c
SPI_HandleTypeDef hspi1;

void MX_SPI1_Init(void)
{
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;            // 主机模式
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;  // 全双工
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;      // 8位数据
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;    // CPOL=0
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;        // CPHA=0 (Mode 0)
    hspi1.Init.NSS = SPI_NSS_SOFT;                // 软件片选
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_8;  // 分频
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;       // 高位先发
    hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    hspi1.Init.CRCPolynomial = 10;
    
    if (HAL_SPI_Init(&hspi1) != HAL_OK)
    {
        Error_Handler();
    }
}
```

### 2.2 GPIO配置

```c
void HAL_SPI_MspInit(SPI_HandleTypeDef* hspi)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    
    if(hspi->Instance == SPI1)
    {
        __HAL_RCC_SPI1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        
        // PA5: SCK  PA6: MISO  PA7: MOSI
        GPIO_InitStruct.Pin = GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
        
        // PA4: CS（软件片选）
        GPIO_InitStruct.Pin = GPIO_PIN_4;
        GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
        
        // 默认片选高电平（不选中）
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);
    }
}
```

### 2.3 波特率分频

STM32F103 SPI1时钟 = PCLK2 = 72MHz

| 分频系数 | SPI时钟 | 说明 |
|----------|---------|------|
| 2 | 36MHz | 最高速 |
| 4 | 18MHz | 高速 |
| 8 | 9MHz | 中速 |
| 16 | 4.5MHz | 常用 |
| 32 | 2.25MHz | 低速 |
| 64 | 1.125MHz | 低速 |

---

## 三、SPI发送与接收

### 3.1 传输流程

1. **拉低片选（CS）**：选中目标从机
2. **数据传输**：SPI全双工特性，发送同时接收
3. **拉高片选（CS）**：释放从机

### 3.2 传输方式

| 方式 | 函数 | 特点 |
|------|------|------|
| 阻塞发送 | `HAL_SPI_Transmit` | 等待完成 |
| 阻塞接收 | `HAL_SPI_Receive` | 等待完成 |
| 全双工 | `HAL_SPI_TransmitReceive` | 同时收发 |
| 中断 | `HAL_SPI_Transmit_IT` | 非阻塞 |
| DMA | `HAL_SPI_Transmit_DMA` | 大数据量 |

### 3.3 单字节读写

- SPI是全双工协议，发送一个字节的同时会收到一个字节
- 纯读取时发送Dummy字节（通常0xFF）来产生时钟

### 3.4 DMA方式传输

```c
// DMA发送
void SPI_Transmit_DMA(uint8_t *data, uint16_t len)
{
    CS_SELECT();
    HAL_SPI_Transmit_DMA(&hspi1, data, len);
}

void HAL_SPI_TxCpltCallback(SPI_HandleTypeDef *hspi)
{
    CS_RELEASE();
}

// DMA接收
void SPI_Receive_DMA(uint8_t *data, uint16_t len)
{
    CS_SELECT();
    HAL_SPI_Receive_DMA(&hspi1, data, len);
}

// DMA同时收发
void SPI_TransmitReceive_DMA(uint8_t *tx_data, uint8_t *rx_data, uint16_t len)
{
    CS_SELECT();
    HAL_SPI_TransmitReceive_DMA(&hspi1, tx_data, rx_data, len);
}
```

---

## 四、多从机切换

### 4.1 软件片选多从机

```c
// 多从机片选引脚定义
#define CS1_PIN  GPIO_PIN_4
#define CS2_PIN  GPIO_PIN_5
#define CS3_PIN  GPIO_PIN_6
#define CS_PORT  GPIOA

void SPI_Select_Slave(uint8_t slave_id)
{
    // 先释放所有从机
    HAL_GPIO_WritePin(CS_PORT, CS1_PIN | CS2_PIN | CS3_PIN, GPIO_PIN_SET);
    
    // 选择指定从机
    switch(slave_id)
    {
        case 1:
            HAL_GPIO_WritePin(CS_PORT, CS1_PIN, GPIO_PIN_RESET);
            break;
        case 2:
            HAL_GPIO_WritePin(CS_PORT, CS2_PIN, GPIO_PIN_RESET);
            break;
        case 3:
            HAL_GPIO_WritePin(CS_PORT, CS3_PIN, GPIO_PIN_RESET);
            break;
    }
}

// 使用示例
uint8_t data[10];
SPI_Select_Slave(1);
HAL_SPI_Transmit(&hspi1, data, 10, HAL_MAX_DELAY);
HAL_GPIO_WritePin(CS_PORT, CS1_PIN, GPIO_PIN_SET);
```

### 4.2 不同从机不同参数

```c
// 从机配置结构
typedef struct {
    uint8_t id;
    GPIO_TypeDef *cs_port;
    uint16_t cs_pin;
    uint8_t cpol;
    uint8_t cpha;
    uint32_t baudrate;
} SPI_Slave_t;

SPI_Slave_t slaves[] = {
    {1, GPIOA, GPIO_PIN_4, SPI_POLARITY_LOW, SPI_PHASE_1EDGE, SPI_BAUDRATEPRESCALER_8},
    {2, GPIOA, GPIO_PIN_5, SPI_POLARITY_HIGH, SPI_PHASE_2EDGE, SPI_BAUDRATEPRESCALER_16},
};

void SPI_Reconfig_For_Slave(SPI_Slave_t *slave)
{
    // 重新配置SPI参数
    hspi1.Init.CLKPolarity = slave->cpol;
    hspi1.Init.CLKPhase = slave->cpha;
    hspi1.Init.BaudRatePrescaler = slave->baudrate;
    
    HAL_SPI_DeInit(&hspi1);
    HAL_SPI_Init(&hspi1);
    
    // 选择从机
    HAL_GPIO_WritePin(slave->cs_port, slave->cs_pin, GPIO_PIN_RESET);
}
```

---

## 五、典型应用示例

### 5.1 SPI Flash读写（W25Qxx）

```c
// W25Qxx命令定义
#define W25Q_READ        0x03
#define W25Q_WRITE_ENABLE  0x06
#define W25Q_PAGE_PROGRAM  0x02
#define W25Q_SECTOR_ERASE  0x20
#define W25Q_READ_STATUS   0x05

// 读取Flash ID
uint32_t W25Q_Read_ID(void)
{
    uint8_t cmd = 0x9F;  // Read JEDEC ID
    uint8_t id[3];
    
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, &cmd, 1, HAL_MAX_DELAY);
    HAL_SPI_Receive(&hspi1, id, 3, HAL_MAX_DELAY);
    CS_RELEASE();
    
    return (id[0] << 16) | (id[1] << 8) | id[2];
}

// 读取数据
void W25Q_Read_Data(uint32_t addr, uint8_t *data, uint16_t len)
{
    uint8_t cmd[4];
    cmd[0] = W25Q_READ;
    cmd[1] = (addr >> 16) & 0xFF;
    cmd[2] = (addr >> 8) & 0xFF;
    cmd[3] = addr & 0xFF;
    
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, cmd, 4, HAL_MAX_DELAY);
    HAL_SPI_Receive(&hspi1, data, len, HAL_MAX_DELAY);
    CS_RELEASE();
}

// 写使能
void W25Q_Write_Enable(void)
{
    uint8_t cmd = W25Q_WRITE_ENABLE;
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, &cmd, 1, HAL_MAX_DELAY);
    CS_RELEASE();
}

// 等待写入完成
void W25Q_Wait_Busy(void)
{
    uint8_t cmd = W25Q_READ_STATUS;
    uint8_t status;
    
    do {
        CS_SELECT();
        HAL_SPI_Transmit(&hspi1, &cmd, 1, HAL_MAX_DELAY);
        HAL_SPI_Receive(&hspi1, &status, 1, HAL_MAX_DELAY);
        CS_RELEASE();
    } while(status & 0x01);  // Busy位
}

// 页写入
void W25Q_Page_Write(uint32_t addr, uint8_t *data, uint16_t len)
{
    uint8_t cmd[4];
    cmd[0] = W25Q_PAGE_PROGRAM;
    cmd[1] = (addr >> 16) & 0xFF;
    cmd[2] = (addr >> 8) & 0xFF;
    cmd[3] = addr & 0xFF;
    
    W25Q_Write_Enable();
    
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, cmd, 4, HAL_MAX_DELAY);
    HAL_SPI_Transmit(&hspi1, data, len, HAL_MAX_DELAY);
    CS_RELEASE();
    
    W25Q_Wait_Busy();
}
```

### 5.2 SPI LCD驱动

```c
// LCD命令定义
#define LCD_CMD   0
#define LCD_DATA  1

// 发送命令
void LCD_Write_Cmd(uint8_t cmd)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_RESET);  // DC=0，命令
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, &cmd, 1, HAL_MAX_DELAY);
    CS_RELEASE();
}

// 发送数据
void LCD_Write_Data(uint8_t data)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_3, GPIO_PIN_SET);  // DC=1，数据
    CS_SELECT();
    HAL_SPI_Transmit(&hspi1, &data, 1, HAL_MAX_DELAY);
    CS_RELEASE();
}

// 初始化LCD
void LCD_Init(void)
{
    LCD_Write_Cmd(0x01);  // 复位
    HAL_Delay(100);
    LCD_Write_Cmd(0x11);  // Sleep Out
    HAL_Delay(20);
    LCD_Write_Cmd(0x29);  // Display On
}
```

---

## 六、常见问题排查

### 6.1 模式不匹配

```c
// 检查设备支持的SPI模式
/*
常见设备模式：
- W25Qxx Flash: Mode 0 或 Mode 3
- ADS1292 ADC: Mode 1
- ST7789 LCD: Mode 0

解决方案：参考设备数据手册，配置正确的CPOL和CPHA
*/
```

### 6.2 时钟频率过高

```c
// 检查设备最大时钟频率
/*
W25Q64: 最高104MHz（实际用20-40MHz较稳定）
MPU6050: 最高1MHz
ST7789: 最高数十MHz

STM32F103 SPI1最高18MHz（分频4）
*/
```

### 6.3 片选时序问题

```c
// 正确的片选时序
void Correct_CS_Sequence(void)
{
    // 1. 先拉低CS
    CS_SELECT();
    
    // 2. 等待CS稳定（高速时需要）
    // HAL_Delay(1);  或NOP
    
    // 3. 发送数据
    HAL_SPI_Transmit(&hspi1, data, len, HAL_MAX_DELAY);
    
    // 4. 等待传输完成
    while(__HAL_SPI_GET_FLAG(&hspi1, SPI_FLAG_BSY));
    
    // 5. 拉高CS
    CS_RELEASE();
}
```

---

## 附录：SPI常用API速查表

### 发送函数
| 函数 | 说明 |
|------|------|
| `HAL_SPI_Transmit()` | 阻塞发送 |
| `HAL_SPI_Transmit_IT()` | 中断发送 |
| `HAL_SPI_Transmit_DMA()` | DMA发送 |

### 接收函数
| 函数 | 说明 |
|------|------|
| `HAL_SPI_Receive()` | 阻塞接收 |
| `HAL_SPI_Receive_IT()` | 中断接收 |
| `HAL_SPI_Receive_DMA()` | DMA接收 |

### 收发函数
| 函数 | 说明 |
|------|------|
| `HAL_SPI_TransmitReceive()` | 阻塞收发 |
| `HAL_SPI_TransmitReceive_IT()` | 中断收发 |
| `HAL_SPI_TransmitReceive_DMA()` | DMA收发 |

### 回调函数
| 函数 | 说明 |
|------|------|
| `HAL_SPI_TxCpltCallback()` | 发送完成回调 |
| `HAL_SPI_RxCpltCallback()` | 接收完成回调 |
| `HAL_SPI_TxRxCpltCallback()` | 收发完成回调 |
| `HAL_SPI_ErrorCallback()` | 错误回调 |

### 状态查询
| 函数 | 说明 |
|------|------|
| `__HAL_SPI_GET_FLAG()` | 获取状态标志 |
| `HAL_SPI_GetState()` | 获取SPI状态 |

### 常用配置参数
| 参数 | 选项 | 说明 |
|------|------|------|
| `Mode` | MASTER/SLAVE | 主/从模式 |
| `Direction` | 2LINES/1LINE | 全双工/半双工 |
| `DataSize` | 8BIT/16BIT | 数据位宽 |
| `CLKPolarity` | LOW/HIGH | CPOL |
| `CLKPhase` | 1EDGE/2EDGE | CPHA |

---