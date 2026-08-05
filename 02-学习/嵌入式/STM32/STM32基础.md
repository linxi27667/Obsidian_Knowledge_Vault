# STM32基础

## 核心概念

- **STM32** - STMicroelectronics的ARM Cortex-M系列MCU
- **HAL库** - 硬件抽象层库，简化外设操作
- **寄存器** - 直接操作硬件的方式
- **中断** - 异步事件处理机制

---

## 一、STM32概述

### 1.1 STM32系列

| 系列 | 内核 | 特点 | 应用 |
|------|------|------|------|
| F1 | Cortex-M3 | 入门级 | 学习、简单控制 |
| F4 | Cortex-M4F | 高性能、DSP | 音频、电机控制 |
| F7 | Cortex-M7 | 超高性能 | 图形、网络 |
| H7 | Cortex-M7 | 双核、高速 | 复杂应用 |
| G0/G4 | Cortex-M0+/M4 | 低功耗 | 电池供电 |
| L0/L4 | Cortex-M0+/M4 | 超低功耗 | 可穿戴 |
| U5 | Cortex-M33 | 安全、低功耗 | 物联网 |

---

### 1.2 STM32F407参数

| 参数 | 值 |
|------|-----|
| 内核 | Cortex-M4F |
| 主频 | 168MHz |
| Flash | 1MB |
| SRAM | 192KB |
| GPIO | 140个 |
| ADC | 3个12位 |
| DAC | 2个12位 |
| 定时器 | 14个 |
| USART | 6个 |
| SPI | 3个 |
| I2C | 3个 |
| USB | 2个 |
| CAN | 2个 |

---

### 1.3 存储器映射

```
0x0000 0000 ┌─────────────────┐
            │  Flash (1MB)    │
0x0010 0000 ├─────────────────┤
            │  Reserved       │
0x1FFF FFFF ├─────────────────┤
            │  System Memory  │
0x2000 0000 ├─────────────────┤
            │  SRAM1 (112KB)  │
0x2001 C000 ├─────────────────┤
            │  SRAM2 (16KB)   │
0x2002 0000 ├─────────────────┤
            │  SRAM3 (64KB)   │
0x4000 0000 ├─────────────────┤
            │  APB1外设       │
0x4001 0000 ├─────────────────┤
            │  APB2外设       │
0x4002 0000 ├─────────────────┤
            │  AHB1外设       │
0x5000 0000 ├─────────────────┤
            │  AHB2外设       │
0xA000 0000 ├─────────────────┤
            │  FSMC           │
0xE000 0000 ├─────────────────┤
            │  Cortex-M4      │
0xFFFF FFFF └─────────────────┘
```

---

## 二、开发环境

### 2.1 开发工具

| 工具 | 说明 |
|------|------|
| Keil MDK | Windows开发环境 |
| STM32CubeIDE | ST官方IDE |
| PlatformIO | 跨平台开发 |
| STM32CubeMX | 图形化配置 |
| VS Code | 代码编辑 |

---

### 2.2 STM32CubeMX配置

**步骤：**
1. 选择芯片型号
2. 配置时钟树
3. 配置外设
4. 生成代码

**时钟配置：**
```
HSE (8MHz) → PLL → SYSCLK (168MHz)
                → AHB (168MHz)
                → APB1 (42MHz)
                → APB2 (84MHz)
```

---

### 2.3 HAL库结构

```
STM32F4xx_HAL_Driver/
├── Inc/
│   ├── stm32f4xx_hal.h
│   ├── stm32f4xx_hal_gpio.h
│   ├── stm32f4xx_hal_uart.h
│   └── ...
└── Src/
    ├── stm32f4xx_hal.c
    ├── stm32f4xx_hal_gpio.c
    ├── stm32f4xx_hal_uart.c
    └── ...
```

---

## 三、GPIO

### 3.1 GPIO模式

| 模式 | 说明 | 应用 |
|------|------|------|
| 输入浮空 | 无上下拉 | 外部信号输入 |
| 输入上拉 | 内部上拉 | 按键检测 |
| 输入下拉 | 内部下拉 | 按键检测 |
| 模拟输入 | ADC输入 | 模拟信号采集 |
| 推挽输出 | 可输出高低 | LED、继电器 |
| 开漏输出 | 只能拉低 | I2C、电平转换 |
| 复用推挽 | 外设功能 | UART、SPI |
| 复用开漏 | 外设功能 | I2C |

---

### 3.2 GPIO配置

```c
// GPIO初始化
GPIO_InitTypeDef GPIO_InitStruct = {0};

__HAL_RCC_GPIOA_CLK_ENABLE();

GPIO_InitStruct.Pin = GPIO_PIN_5;
GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
GPIO_InitStruct.Pull = GPIO_NOPULL;
GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

// 输出
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);

// 输入
GPIO_PinState state = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0);
```

---

### 3.3 按键检测

```c
// 按键初始化（带上拉）
GPIO_InitStruct.Pin = GPIO_PIN_0;
GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
GPIO_InitStruct.Pull = GPIO_PULLUP;
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

// 按键检测
if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0) == GPIO_PIN_RESET) {
    HAL_Delay(20);  // 消抖
    if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0) == GPIO_PIN_RESET) {
        // 按键按下
        while (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0) == GPIO_PIN_RESET);
    }
}
```

---

## 四、中断

### 4.1 NVIC配置

```c
// 设置优先级分组
HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

// 设置中断优先级
HAL_NVIC_SetPriority(EXTI0_IRQn, 2, 0);

// 使能中断
HAL_NVIC_EnableIRQ(EXTI0_IRQn);
```

**优先级分组：**
| 分组 | 抢占优先级 | 子优先级 |
|------|-----------|---------|
| 0 | 0位 | 4位 |
| 1 | 1位 | 3位 |
| 2 | 2位 | 2位 |
| 3 | 3位 | 1位 |
| 4 | 4位 | 0位 |

---

### 4.2 外部中断

```c
// 配置外部中断
GPIO_InitStruct.Pin = GPIO_PIN_0;
GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
GPIO_InitStruct.Pull = GPIO_PULLUP;
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

// 中断回调函数
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    if (GPIO_Pin == GPIO_PIN_0) {
        // 处理中断
    }
}

// 中断服务函数
void EXTI0_IRQHandler(void) {
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);
}
```

---

## 五、定时器

### 5.1 定时器分类

| 类型 | 定时器 | 特点 |
|------|--------|------|
| 高级 | TIM1, TIM8 | PWM、互补输出 |
| 通用 | TIM2-TIM5 | 计数、捕获、PWM |
| 基本 | TIM6, TIM7 | 基本定时 |
| 通用 | TIM9-TIM14 | 简单定时 |

---

### 5.2 定时器配置

```c
// 定时器句柄
TIM_HandleTypeDef htim2;

// 定时器初始化
htim2.Instance = TIM2;
htim2.Init.Prescaler = 8400 - 1;      // 分频系数
htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
htim2.Init.Period = 10000 - 1;         // 自动重装载值
htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
HAL_TIM_Base_Init(&htim2);

// 启动定时器
HAL_TIM_Base_Start_IT(&htim2);

// 定时器中断回调
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM2) {
        // 定时器中断处理
    }
}
```

**定时时间计算：**
$$T = \frac{(Prescaler + 1) \times (Period + 1)}{TimerClock}$$

---

### 5.3 PWM输出

```c
// PWM配置
TIM_OC_InitTypeDef sConfigOC = {0};

sConfigOC.OCMode = TIM_OCMODE_PWM1;
sConfigOC.Pulse = 500;  // 占空比
sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
HAL_TIM_PWM_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_1);

// 启动PWM
HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1);

// 修改占空比
__HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, 750);
```

---

### 5.4 输入捕获

```c
// 输入捕获配置
TIM_IC_InitTypeDef sConfigIC = {0};

sConfigIC.ICPolarity = TIM_INPUTCHANNELPOLARITY_RISING;
sConfigIC.ICSelection = TIM_ICSELECTION_DIRECTTI;
sConfigIC.ICPrescaler = TIM_ICPSC_DIV1;
sConfigIC.ICFilter = 0;
HAL_TIM_IC_ConfigChannel(&htim2, &sConfigIC, TIM_CHANNEL_1);

// 启动输入捕获
HAL_TIM_IC_Start_IT(&htim2, TIM_CHANNEL_1);

// 捕获回调
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim) {
    if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1) {
        uint32_t capture = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_1);
    }
}
```

---

## 六、UART串口

### 6.1 UART配置

```c
UART_HandleTypeDef huart1;

// UART初始化
huart1.Instance = USART1;
huart1.Init.BaudRate = 115200;
huart1.Init.WordLength = UART_WORDLENGTH_8B;
huart1.Init.StopBits = UART_STOPBITS_1;
huart1.Init.Parity = UART_PARITY_NONE;
huart1.Init.Mode = UART_MODE_TX_RX;
huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
huart1.Init.OverSampling = UART_OVERSAMPLING_16;
HAL_UART_Init(&huart1);
```

---

### 6.2 UART收发

```c
// 发送数据
HAL_UART_Transmit(&huart1, (uint8_t*)"Hello", 5, 1000);

// 接收数据
uint8_t rx_data;
HAL_UART_Receive(&huart1, &rx_data, 1, 1000);

// 中断接收
HAL_UART_Receive_IT(&huart1, &rx_data, 1);

// 接收完成回调
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        // 处理接收数据
        HAL_UART_Receive_IT(&huart1, &rx_data, 1);
    }
}
```

---

### 6.3 printf重定向

```c
#include <stdio.h>

int fputc(int ch, FILE *f) {
    HAL_UART_Transmit(&huart1, (uint8_t*)&ch, 1, 1000);
    return ch;
}

// 使用
printf("Hello %d\n", 123);
```

---

## 七、I2C

### 7.1 I2C配置

```c
I2C_HandleTypeDef hi2c1;

// I2C初始化
hi2c1.Instance = I2C1;
hi2c1.Init.ClockSpeed = 400000;
hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
hi2c1.Init.OwnAddress1 = 0;
hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
HAL_I2C_Init(&hi2c1);
```

---

### 7.2 I2C读写

```c
// 写数据
uint8_t data[] = {0x01, 0x02};
HAL_I2C_Master_Transmit(&hi2c1, 0x68 << 1, data, 2, 1000);

// 读数据
uint8_t rx_data[2];
HAL_I2C_Master_Receive(&hi2c1, 0x68 << 1, rx_data, 2, 1000);

// 写寄存器
uint8_t reg = 0x00;
HAL_I2C_Mem_Write(&hi2c1, 0x68 << 1, reg, I2C_MEMADD_SIZE_8BIT, data, 2, 1000);

// 读寄存器
HAL_I2C_Mem_Read(&hi2c1, 0x68 << 1, reg, I2C_MEMADD_SIZE_8BIT, rx_data, 2, 1000);
```

---

## 八、SPI

### 8.1 SPI配置

```c
SPI_HandleTypeDef hspi1;

// SPI初始化
hspi1.Instance = SPI1;
hspi1.Init.Mode = SPI_MODE_MASTER;
hspi1.Init.Direction = SPI_DIRECTION_2LINES;
hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
hspi1.Init.NSS = SPI_NSS_SOFT;
hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_2;
hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
HAL_SPI_Init(&hspi1);
```

---

### 8.2 SPI读写

```c
// 发送数据
uint8_t tx_data[] = {0x01, 0x02};
HAL_SPI_Transmit(&hspi1, tx_data, 2, 1000);

// 接收数据
uint8_t rx_data[2];
HAL_SPI_Receive(&hspi1, rx_data, 2, 1000);

// 发送接收
uint8_t tx[] = {0x01, 0x02};
uint8_t rx[2];
HAL_SPI_TransmitReceive(&hspi1, tx, rx, 2, 1000);
```

---

## 九、ADC

### 9.1 ADC配置

```c
ADC_HandleTypeDef hadc1;

// ADC初始化
hadc1.Instance = ADC1;
hadc1.Init.Resolution = ADC_RESOLUTION_12B;
hadc1.Init.ScanConvMode = DISABLE;
hadc1.Init.ContinuousConvMode = DISABLE;
hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
hadc1.Init.NbrOfConversion = 1;
HAL_ADC_Init(&hadc1);

// ADC通道配置
ADC_ChannelConfTypeDef sConfig = {0};
sConfig.Channel = ADC_CHANNEL_0;
sConfig.Rank = 1;
sConfig.SamplingTime = ADC_SAMPLETIME_3CYCLES;
HAL_ADC_ConfigChannel(&hadc1, &sConfig);
```

---

### 9.2 ADC读取

```c
// 启动ADC
HAL_ADC_Start(&hadc1);

// 等待转换完成
HAL_ADC_PollForConversion(&hadc1, 1000);

// 读取ADC值
uint32_t adc_value = HAL_ADC_GetValue(&hadc1);

// 转换为电压
float voltage = adc_value * 3.3 / 4096;
```

---

## 十、DMA

### 10.1 DMA配置

```c
DMA_HandleTypeDef hdma_usart1_rx;

// DMA初始化
hdma_usart1_rx.Instance = DMA2_Stream2;
hdma_usart1_rx.Init.Channel = DMA_CHANNEL_4;
hdma_usart1_rx.Init.Direction = DMA_PERIPH_TO_MEMORY;
hdma_usart1_rx.Init.PeriphInc = DMA_PINC_DISABLE;
hdma_usart1_rx.Init.MemInc = DMA_MINC_ENABLE;
hdma_usart1_rx.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
hdma_usart1_rx.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
hdma_usart1_rx.Init.Mode = DMA_NORMAL;
hdma_usart1_rx.Init.Priority = DMA_PRIORITY_LOW;
HAL_DMA_Init(&hdma_usart1_rx);

__HAL_LINKDMA(&huart1, hdmarx, hdma_usart1_rx);
```

---

### 10.2 DMA传输

```c
// UART DMA接收
uint8_t rx_buf[100];
HAL_UART_Receive_DMA(&huart1, rx_buf, 100);

// DMA传输完成回调
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART1) {
        // 处理接收数据
    }
}
```

---

## 十一、低功耗模式

### 11.1 低功耗模式

| 模式 | 电流 | 唤醒源 | 说明 |
|------|------|--------|------|
| Sleep | mA级 | 任意中断 | CPU停止 |
| Stop | μA级 | EXTI | 时钟停止 |
| Standby | μA级 | WKUP/RTC | 最低功耗 |

---

### 11.2 Sleep模式

```c
// 进入Sleep模式
HAL_SuspendTick();
HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);

// 唤醒后恢复
HAL_ResumeTick();
```

---

### 11.3 Stop模式

```c
// 配置唤醒源
HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN1);

// 进入Stop模式
HAL_SuspendTick();
HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

// 唤醒后恢复时钟
SystemClock_Config();
HAL_ResumeTick();
```

---

## 十二、项目结构

### 12.1 标准项目结构

```
project/
├── Core/
│   ├── Inc/
│   │   ├── main.h
│   │   ├── stm32f4xx_hal_conf.h
│   │   └── stm32f4xx_it.h
│   └── Src/
│       ├── main.c
│       ├── stm32f4xx_hal_msp.c
│       ├── stm32f4xx_it.c
│       └── system_stm32f4xx.c
├── Drivers/
│   ├── CMSIS/
│   └── STM32F4xx_HAL_Driver/
├── MDK-ARM/ 或 STM32CubeIDE/
└── Makefile (如使用)
```

---

### 12.2 主程序结构

```c
int main(void) {
    // HAL初始化
    HAL_Init();
    
    // 系统时钟配置
    SystemClock_Config();
    
    // 外设初始化
    MX_GPIO_Init();
    MX_USART1_UART_Init();
    MX_I2C1_Init();
    MX_TIM2_Init();
    
    // 主循环
    while (1) {
        // 应用逻辑
    }
}
```

---

## 附录：常用函数速查表

### GPIO

| 函数 | 说明 |
|------|------|
| HAL_GPIO_Init | 初始化GPIO |
| HAL_GPIO_WritePin | 写引脚 |
| HAL_GPIO_ReadPin | 读引脚 |
| HAL_GPIO_TogglePin | 翻转引脚 |

### 定时器

| 函数 | 说明 |
|------|------|
| HAL_TIM_Base_Start | 启动定时器 |
| HAL_TIM_Base_Start_IT | 中断启动 |
| HAL_TIM_PWM_Start | 启动PWM |
| HAL_TIM_IC_Start_IT | 启动捕获 |

### UART

| 函数 | 说明 |
|------|------|
| HAL_UART_Transmit | 发送数据 |
| HAL_UART_Receive | 接收数据 |
| HAL_UART_Transmit_IT | 中断发送 |
| HAL_UART_Receive_IT | 中断接收 |

### I2C

| 函数 | 说明 |
|------|------|
| HAL_I2C_Master_Transmit | 主机发送 |
| HAL_I2C_Master_Receive | 主机接收 |
| HAL_I2C_Mem_Write | 写寄存器 |
| HAL_I2C_Mem_Read | 读寄存器 |

### SPI

| 函数 | 说明 |
|------|------|
| HAL_SPI_Transmit | 发送数据 |
| HAL_SPI_Receive | 接收数据 |
| HAL_SPI_TransmitReceive | 发送接收 |

---

## 相关链接

- [[C语言深入]] - C语言基础
- [[FreeRTOS]] - RTOS学习
- [[通信协议详解]] - 协议详解
- [[PCB设计基础]] - 硬件设计
