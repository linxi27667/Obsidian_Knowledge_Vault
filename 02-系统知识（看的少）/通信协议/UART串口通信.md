# UART串口通信 （异步串行 全双工 点对点）

## 核心概念

### 基本原理
- ==异步通信== - 无时钟线，靠波特率约定同步
- ==全双工== - TX发送、RX接收同时进行
- ==点对点== - 一对一通信，不支持多设备

### 关键参数
- ==波特率== - 每秒传输位数，常用 9600/115200
- ==数据位== - 通常 8位
- ==停止位== - 1位或2位
- ==校验位== - None/Even/Odd

---

## 一、STM32 HAL库初始化

### 1.1 基础配置

```c
// UART_HandleTypeDef 结构体
UART_HandleTypeDef huart1;

void MX_USART1_UART_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    
    if (HAL_UART_Init(&huart1) != HAL_OK)
    {
        Error_Handler();
    }
}
```

| 参数 | 常用值 | 说明 |
|------|--------|------|
| `BaudRate` | 9600/115200 | 波特率 |
| `WordLength` | 8B | 数据位长度 |
| `StopBits` | 1 | 停止位 |
| `Parity` | NONE | 校验位 |

### 1.2 GPIO配置（CubeMX生成）

```c
void HAL_UART_MspInit(UART_HandleTypeDef* huart)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    
    if(huart->Instance == USART1)
    {
        __HAL_RCC_USART1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        
        // PA9: TX  PA10: RX
        GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
    }
}
```

---

## 二、发送与接收

### 2.1 阻塞式发送

```c
// 发送数据
HAL_UART_Transmit(&huart1, (uint8_t*)"Hello", 5, 1000);

// 发送单个字节
uint8_t data = 0x55;
HAL_UART_Transmit(&huart1, &data, 1, HAL_MAX_DELAY);
```

### 2.2 阻塞式接收

```c
uint8_t rx_buffer[10];
HAL_UART_Receive(&huart1, rx_buffer, 10, 1000);  // 超时1000ms
```

### 2.3 非阻塞（中断）方式

- **开启接收中断**：`HAL_UART_Receive_IT` 逐字节接收
- **接收完成回调**：`HAL_UART_RxCpltCallback` 中处理数据并重新开启中断
- 适用于低数据量、实时性要求不高的场景

### 2.4 DMA方式

- **DMA发送**：`HAL_UART_Transmit_DMA` 硬件DMA搬运，不占用CPU
- **DMA接收**：`HAL_UART_Receive_DMA` 配合空闲中断实现不定长接收
- **完成回调**：`HAL_UART_TxCpltCallback` / `HAL_UART_RxCpltCallback`
- 适用于大数据量、高速率传输场景

---

## 三、空闲中断接收（不定长数据）

### 3.1 空闲中断原理

> [!TIP] 空闲中断（IDLE）
> 当RX线检测到空闲状态时触发，适用于接收不定长数据包

### 3.2 实现流程

1. 开启DMA接收 + IDLE中断
2. 数据到达时DMA自动搬运到缓冲区
3. 发送方停止发送后，RX线进入空闲状态触发IDLE中断
4. 在中断中停止DMA，读取已接收数据长度
5. 处理数据后重新开启DMA接收

### 3.3 数据长度获取

- 通过DMA剩余计数器计算：`已接收长度 = 缓冲区总长度 - DMA剩余计数`

---

## 四、printf重定向

### 4.1 实现方法

- 重写 `fputc` 函数，内部调用 `HAL_UART_Transmit` 发送单字节
- 可选重写 `fgetc` 实现输入重定向
- Keil工程需勾选 `Use MicroLIB`
- GCC/Clang需使用 `_write` 代替 `fputc`

---

## 五、环形缓冲区

### 5.1 结构

- **缓冲区数组**：固定大小的循环数组
- **head指针**：写入位置（中断中更新）
- **tail指针**：读取位置（主循环中更新）
- **判满**：`(head + 1) % SIZE == tail`
- **判空**：`head == tail`
- **可用数据量**：`(head - tail + SIZE) % SIZE`

### 5.2 应用场景

- UART中断接收中，每收到一字节写入环形缓冲区
- 主循环从缓冲区读取并解析数据
- 避免数据丢失，解耦收发速率差异

### 5.2 配合中断使用

```c
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if(huart->Instance == USART1)
    {
        RingBuffer_Write(&uart_rx_buffer, rx_data);
        HAL_UART_Receive_IT(&huart1, &rx_data, 1);
    }
}

// 主循环中处理
void Process_UART_Data(void)
{
    while(RingBuffer_GetCount(&uart_rx_buffer) > 0)
    {
        uint8_t data = RingBuffer_Read(&uart_rx_buffer);
        // 处理数据...
    }
}
```

---

## 附录：UART常用API速查表

### 发送函数
| 函数 | 说明 |
|------|------|
| `HAL_UART_Transmit()` | 阻塞发送 |
| `HAL_UART_Transmit_IT()` | 中断发送 |
| `HAL_UART_Transmit_DMA()` | DMA发送 |

### 接收函数
| 函数 | 说明 |
|------|------|
| `HAL_UART_Receive()` | 阻塞接收 |
| `HAL_UART_Receive_IT()` | 中断接收 |
| `HAL_UART_Receive_DMA()` | DMA接收 |

### 控制函数
| 函数 | 说明 |
|------|------|
| `HAL_UART_Abort()` | 中止传输 |
| `HAL_UART_Abort_IT()` | 中止中断传输 |
| `HAL_UART_AbortReceive()` | 中止接收 |

### 回调函数
| 函数 | 说明 |
|------|------|
| `HAL_UART_TxCpltCallback()` | 发送完成回调 |
| `HAL_UART_RxCpltCallback()` | 接收完成回调 |
| `HAL_UART_ErrorCallback()` | 错误回调 |

### 状态查询
| 函数 | 说明 |
|------|------|
| `__HAL_UART_GET_FLAG()` | 获取状态标志 |
| `__HAL_UART_CLEAR_FLAG()` | 清除状态标志 |
| `HAL_UART_GetState()` | 获取UART状态 |

---