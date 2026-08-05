# STM32深入学习指南

> **核心概念**：STM32架构、时钟树、HAL库、外设驱动、DMA、低功耗、Bootloader、FreeRTOS集成
>
> **适用对象**：有一定STM32基础，希望深入理解底层原理和高级应用的嵌入式开发者
>
> **学习路线**：产品线概览 -> 时钟系统 -> HAL库 -> GPIO -> 定时器 -> ADC/DAC -> 通信接口 -> DMA -> 低功耗 -> Bootloader -> FreeRTOS -> 调试技巧

---

## 1. STM32产品线概览

### 1.1 主流系列对比

STM32是STMicroelectronics推出的基于ARM Cortex-M内核的32位微控制器家族。不同系列针对不同应用场景优化。

| 系列 | 内核 | 主频 | Flash | RAM | 特点 | 典型应用 |
|------|------|------|-------|-----|------|----------|
| STM32F0 | Cortex-M0 | 48MHz | 16-256KB | 4-32KB | 入门级，低成本 | 简单控制、消费电子 |
| STM32F1 | Cortex-M3 | 72MHz | 16-1024KB | 4-96KB | 经典款，生态成熟 | 通用嵌入式、教学 |
| STM32F2 | Cortex-M3 | 120MHz | 128-1024KB | 64-128KB | 性能过渡型 | 中等复杂度应用 |
| STM32F3 | Cortex-M4F | 72MHz | 16-512KB | 12-80KB | 混合信号，ADC强 | 电机控制、电源 |
| STM32F4 | Cortex-M4F | 168-180MHz | 512KB-2MB | 192-384KB | 高性能，DSP指令 | 音视频、工业控制 |
| STM32F7 | Cortex-M7 | 216MHz | 512KB-2MB | 256-512KB | 超高性能，Cache | HMI、网关 |
| STM32G0 | Cortex-M0+ | 64MHz | 16-512KB | 8-144KB | 低功耗入门 | 替代F0，IoT节点 |
| STM32G4 | Cortex-M4F | 170MHz | 32-512KB | 22-128KB | 混合信号增强 | 数字电源、电机 |
| STM32H7 | Cortex-M7 | 480MHz | 1-2MB | 512KB-1MB | 旗舰级，双AXI总线 | 高端HMI、AI推理 |
| STM32L0 | Cortex-M0+ | 32MHz | 8-192KB | 8-20KB | 超低功耗 | 表计、传感器 |
| STM32L4 | Cortex-M4F | 80MHz | 256KB-1MB | 64-320KB | 低功耗+性能 | 可穿戴、医疗 |
| STM32L4+ | Cortex-M4F | 120MHz | 512KB-2MB | 256-640KB | L4增强版 | 复杂低功耗应用 |
| STM32L5 | Cortex-M33 | 110MHz | 256KB-512KB | 256KB | TrustZone安全 | 安全IoT |
| STM32U5 | Cortex-M33 | 160MHz | 256KB-2MB | 768KB | 超低功耗旗舰 | 可穿戴、医疗 |
| STM32WB | M4+M0+ | 64MHz | 256KB-1MB | 128-256KB | 双核，BLE5.0 | 蓝牙产品 |
| STM32WL | Cortex-M4/M0+ | 48MHz | 64-256KB | 8-64KB | LoRa/FSK无线 | LPWAN物联网 |

### 1.2 选型指南

选型时需要综合考虑以下几个维度：

**性能需求决策树：**
```
性能需求
├── 简单控制 (< 50MHz) → F0 / G0 / L0
├── 通用应用 (50-100MHz) → F1 / L4 / G4
├── 高性能 (100-200MHz) → F4 / F7 / L4+
└── 极致性能 (> 200MHz) → H7
```

**外设需求矩阵：**
- 需要高级定时器(TIM1/TIM8)做互补PWM → F1/F4/F7/H7
- 需要USB OTG → F1/F4/F7/H7
- 需要以太网MAC → F2/F4/F7/H7
- 需要CAN → 几乎全系列(部分型号无)
- 需要SDIO → F1/F4/F7/H7
- 需要LTDC(液晶接口) → F4/F7/H7

**功耗需求参考：**
- 运行功耗：L4系列 ~30uA/MHz，F4系列 ~150uA/MHz
- 停机模式：L4系列 ~30nA，F4系列 ~30uA
- 待机模式：L4系列 ~20nA(含RTC)，F4系列 ~2.4uA

**成本敏感场景：**
- 超低成本：STM32F030 (约 $0.5)
- 性价比：STM32G030/G031 (约 $0.8)
- 经典方案：STM32F103C8T6 (约 $1.5，蓝丸板常用)

**引脚数量选择：**
- 最小系统：TSSOP20 / QFN32
- 通用项目：LQFP48 / LQFP64
- 外设丰富：LQFP100 / LQFP144 / BGA

### 1.3 STM32命名规则

以 `STM32F407VGT6` 为例：

| 字段 | 含义 |
|------|------|
| STM32 | 32位ARM微控制器 |
| F | 基础系列(F=基础, L=低功耗, H=高性能, G=通用) |
| 4 | Cortex-M4内核 |
| 07 | 具体产品线(功能子集) |
| V | 引脚数(V=100pin, Z=144pin, C=48pin) |
| G | Flash大小(G=1024KB, C=256KB, E=512KB) |
| T | 封装(T=LQFP, U=QFN, I=BGA) |
| 6 | 温度范围(6=-40~85, 7=-40~105) |

---

## 2. 时钟系统深入

### 2.1 时钟源详解

STM32的时钟系统是整个芯片的"心脏"，理解时钟树是掌握STM32的第一步。

**四种基础时钟源：**

| 时钟源 | 类型 | 频率 | 精度 | 功耗 | 用途 |
|--------|------|------|------|------|------|
| HSI | 内部RC振荡器 | 8MHz(F1)/16MHz(F4) | ±1% | 低 | 启动时钟、备用时钟 |
| HSE | 外部晶振 | 4-26MHz(典型8MHz) | ±20ppm | 中 | 主时钟源 |
| LSI | 内部低速RC | 32kHz(F1)/32kHz(F4) | ±15% | 极低 | 独立看门狗 |
| LSE | 外部32.768kHz晶振 | 32.768kHz | ±20ppm | 极低 | RTC时钟 |

**PLL锁相环：**

PLL的作用是将低频时钟倍频到高频。STM32F4有三个PLL：
- **PLL**：主PLL，产生SYSCLK（最高168/180MHz）
- **PLLI2S**：音频PLL，产生精确的I2S时钟
- **PLLSAI**：专用PLL，产生LCD像素时钟等

**PLL配置公式（以STM32F407为例）：**
```
VCO input = HSE / M          (要求1-2MHz)
VCO output = VCO input × N   (要求100-432MHz)
PLLCLK = VCO output / P      (P可选2/4/6/8)
PLL48CLK = VCO output / Q    (USB/SDIO需要48MHz)
```

**配置实例：8MHz HSE → 168MHz SYSCLK**
```
M = 8   → VCO input = 8/8 = 1MHz
N = 336 → VCO output = 1 × 336 = 336MHz
P = 2   → PLLCLK = 336/2 = 168MHz
Q = 7   → PLL48CLK = 336/7 = 48MHz
```

### 2.2 时钟树详解（以STM32F407为例）

```
                          ┌─────────────┐
         HSE(8MHz) ──────┤   PLL MUX   ├──→ PLLCLK(168MHz)
         HSI(16MHz) ─────┤  (SW选择)    │
                          └──────┬──────┘
                                 ↓
                          ┌──────────────┐
                          │   SYSCLK     │  ← 系统主时钟 168MHz
                          └──────┬──────┘
                                 ↓
                          ┌──────────────┐
                          │  AHB Prescaler│  /1, /2, /4 ... /512
                          └──────┬──────┘
                                 ↓
                              HCLK = 168MHz  ← 总线时钟
                                 ↓
                ┌────────────────┼────────────────┐
                ↓                ↓                ↓
          ┌──────────┐    ┌──────────┐    ┌──────────┐
          │ APB1     │    │ APB2     │    │ Core     │
          │ /4=42MHz │    │ /2=84MHz │    │ DBus/IBus│
          └──────────┘    └──────────┘    └──────────┘
               ↓               ↓
         TIM2-TIM7       TIM1/TIM8
         TIM12-TIM14     TIM9-TIM11
         UART/USART      SPI1
         SPI2/SPI3       ADC1/2/3
         I2C1/I2C2       USART1/USART6
         USB/CAN         SDIO/DAC
```

**关键时钟规则：**

1. **AHB总线**：CPU、DMA、SRAM、Flash都连接在此总线上
2. **APB1总线**：低速外设，最大42MHz
3. **APB2总线**：高速外设，最大84MHz
4. **定时器时钟倍频**：当APB分频系数不为1时，定时器时钟 = APB时钟 × 2
5. **Flash等待周期**：168MHz需要5个等待周期(WS5)

**Flash等待周期对照表（STM32F4）：**

| 电压范围 | 2.7-3.6V | 2.4-2.7V | 2.1-2.4V | 1.8-2.1V |
|----------|----------|----------|----------|----------|
| 0 WS (30MHz) | ≤30MHz | ≤24MHz | ≤22MHz | ≤20MHz |
| 1 WS (60MHz) | ≤60MHz | ≤48MHz | ≤44MHz | ≤40MHz |
| 2 WS (90MHz) | ≤90MHz | ≤72MHz | ≤66MHz | ≤60MHz |
| 3 WS (120MHz) | ≤120MHz | ≤96MHz | ≤88MHz | ≤80MHz |
| 4 WS (150MHz) | ≤150MHz | ≤120MHz | ≤110MHz | ≤100MHz |
| 5 WS (168MHz) | ≤168MHz | ≤144MHz | ≤132MHz | ≤120MHz |

### 2.3 时钟配置代码

**CubeMX生成的SystemClock_Config()详解：**

```c
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    // 1. 配置电源稳压器输出电压
    // 168MHz需要Scale 1模式(高性能)
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    // 2. 配置振荡器
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;           // 使能外部晶振
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;       // 使能PLL
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;    // VCO input = 8/8 = 1MHz
    RCC_OscInitStruct.PLL.PLLN = 336;  // VCO output = 336MHz
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;  // PLLCLK = 168MHz
    RCC_OscInitStruct.PLL.PLLQ = 7;    // PLL48CLK = 48MHz
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    // 3. 配置总线时钟分频
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;  // SYSCLK = PLL
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;    // HCLK = 168MHz
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;     // PCLK1 = 42MHz
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;     // PCLK2 = 84MHz

    // Flash等待周期必须在切换频率前配置
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK) {
        Error_Handler();
    }
}
```

**外设时钟使能与失能：**

```c
// GPIO时钟使能
__HAL_RCC_GPIOA_CLK_ENABLE();
__HAL_RCC_GPIOB_CLK_ENABLE();

// 串口时钟使能
__HAL_RCC_USART1_CLK_ENABLE();
__HAL_RCC_USART2_CLK_ENABLE();

// 定时器时钟使能
__HAL_RCC_TIM2_CLK_ENABLE();

// 时钟失能(低功耗)
__HAL_RCC_GPIOC_CLK_DISABLE();
__HAL_RCC_USART1_CLK_DISABLE();

// 查询外设时钟状态
if (__HAL_RCC_GPIOA_IS_CLK_ENABLED()) {
    // GPIOA时钟已使能
}
```

---

## 3. HAL库详解

### 3.1 HAL库架构

HAL(Hardware Abstraction Layer)库是ST官方推出的硬件抽象层，旨在提供跨STM32系列的统一API。

**HAL库 vs 标准外设库(StdPeriph)：**

| 对比项 | HAL库 | StdPeriph库 |
|--------|-------|-------------|
| 可移植性 | 跨系列统一API | 每个系列独立 |
| 抽象程度 | 高，封装完善 | 中，接近寄存器 |
| 代码体积 | 较大 | 较小 |
| 执行效率 | 略低(多层调用) | 较高 |
| CubeMX支持 | 完全支持 | 不支持 |
| 调试难度 | 回调机制 | 直接中断 |
| 维护状态 | 持续更新 | 已停止维护 |

**HAL库文件结构：**

```
Drivers/
├── CMSIS/                    # ARM Cortex-M核心支持
│   ├── Include/              # core_cm4.h等
│   └── Device/ST/STM32F4xx/  # 系统文件、启动文件
├── STM32F4xx_HAL_Driver/     # HAL库源码
│   ├── Inc/                  # 头文件
│   │   ├── stm32f4xx_hal.h           # 总头文件
│   │   ├── stm32f4xx_hal_gpio.h      # GPIO驱动
│   │   ├── stm32f4xx_hal_uart.h      # UART驱动
│   │   └── ...
│   └── Src/                  # 源文件
│       ├── stm32f4xx_hal.c           # HAL核心
│       ├── stm32f4xx_hal_gpio.c      # GPIO驱动
│       ├── stm32f4xx_hal_uart.c      # UART驱动
│       └── ...
```

**回调函数机制：**

HAL库大量使用回调函数(callback)来处理中断事件：

```c
// HAL库的典型中断处理流程:
// 1. 硬件中断触发
// 2. HAL库的IRQHandler()被调用
// 3. HAL库内部处理状态
// 4. 调用用户重写的回调函数

// UART接收完成回调
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        // USART1接收完成处理
        // 重新开启接收
        HAL_UART_Receive_IT(&huart1, &rx_byte, 1);
    }
}

// GPIO外部中断回调
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_0) {
        // PA0外部中断处理
    }
}

// ADC转换完成回调
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        uint32_t adc_value = HAL_ADC_GetValue(hadc);
    }
}
```

**MSP初始化函数：**

MSP(MCU Support Package)函数用于初始化MCU级硬件资源，如GPIO引脚、DMA通道、时钟等：

```c
// UART MSP初始化 - 在HAL_UART_Init()内部被调用
void HAL_UART_MspInit(UART_HandleTypeDef *huart)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if (huart->Instance == USART1) {
        // 1. 使能时钟
        __HAL_RCC_USART1_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();

        // 2. 配置GPIO复用
        GPIO_InitStruct.Pin = GPIO_PIN_9 | GPIO_PIN_10;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        // 3. 配置中断(如果使用中断模式)
        HAL_NVIC_SetPriority(USART1_IRQn, 6, 0);
        HAL_NVIC_EnableIRQ(USART1_IRQn);
    }
}

// UART MSP反初始化 - 在HAL_UART_DeInit()内部被调用
void HAL_UART_MspDeInit(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        __HAL_RCC_USART1_CLK_DISABLE();
        HAL_GPIO_DeInit(GPIOA, GPIO_PIN_9 | GPIO_PIN_10);
        HAL_NVIC_DisableIRQ(USART1_IRQn);
    }
}
```

### 3.2 HAL库使用模式

**三种传输模式对比：**

| 模式 | API后缀 | 阻塞 | 中断 | DMA | 适用场景 |
|------|---------|------|------|-----|----------|
| 阻塞模式 | `_Polling` | 是 | 否 | 否 | 简单初始化、少量数据 |
| 中断模式 | `_IT` | 否 | 是 | 否 | 中等数据量、实时响应 |
| DMA模式 | `_DMA` | 否 | 是 | 是 | 大量数据、高速传输 |

**阻塞模式示例：**

```c
// 阻塞发送 - CPU等待直到发送完成
HAL_StatusTypeDef status;
status = HAL_UART_Transmit(&huart1, (uint8_t*)"Hello", 5, 1000);  // 超时1000ms
if (status != HAL_OK) {
    // 处理错误
}

// 阻塞接收 - CPU等待直到接收完成
uint8_t rx_buf[10];
status = HAL_UART_Receive(&huart1, rx_buf, 10, 1000);
```

**中断模式示例：**

```c
// 中断发送
HAL_UART_Transmit_IT(&huart1, tx_buf, tx_len);

// 中断接收(每次接收1字节)
uint8_t rx_byte;
HAL_UART_Receive_IT(&huart1, &rx_byte, 1);

// 在回调中处理数据并重新开启接收
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1) {
        process_byte(rx_byte);
        HAL_UART_Receive_IT(&huart1, &rx_byte, 1);  // 重新开启
    }
}
```

**DMA模式示例：**

```c
// DMA发送
HAL_UART_Transmit_DMA(&huart1, tx_buf, tx_len);

// DMA接收
HAL_UART_Receive_DMA(&huart1, rx_buf, rx_len);

// DMA发送完成回调
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    // 发送完成处理
}

// DMA接收完成回调
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    // 接收完成处理
}
```

### 3.3 代码生成工具

**STM32CubeMX配置流程：**

```
1. 选择芯片型号
   ├── 直接搜索型号
   └── 按条件筛选(封装、Flash、外设)

2. Pinout & Configuration
   ├── System Core
   │   ├── SYS: Debug(SWD), Timebase Source(TIM6/SysTick)
   │   ├── RCC: HSE/LSE使能
   │   └── GPIO: 引脚配置
   ├── Connectivity
   │   ├── USART1: 异步模式
   │   └── SPI1: 全双工主模式
   ├── Analog
   │   └── ADC1: 独立模式
   ├── Timers
   │   └── TIM2: PWM Generation
   └── Middleware
       └── FREERTOS: CMSIS_V2

3. Clock Configuration
   ├── 选择HSE频率
   ├── 配置PLL参数
   └── 检查各总线频率是否超限

4. Project Manager
   ├── 项目名称和路径
   ├── IDE选择(Keil/IAR/STM32CubeIDE)
   ├── 固件包版本
   └── 代码生成选项
```

**CubeMX代码生成的自定义区域：**

```c
// CubeMX生成的代码中，用户代码应放在标记区域内
// 这样重新生成代码时不会丢失自定义内容

/* USER CODE BEGIN 0 */
// 用户变量声明
uint8_t custom_flag = 0;
/* USER CODE END 0 */

/* USER CODE BEGIN 1 */
// 用户自定义函数
void custom_function(void) {
    // ...
}
/* USER CODE END 1 */

/* USER CODE BEGIN 2 */
// 初始化代码后追加
custom_init();
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
while (1) {
    // 主循环中添加用户代码
    custom_process();
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
}
/* USER CODE END 3 */
```

---

## 4. GPIO深入

### 4.1 GPIO模式详解

**输入模式：**

| 模式 | 寄存器配置 | 说明 | 典型应用 |
|------|-----------|------|----------|
| 浮空输入 | MODE=00, PUPD=00 | 无上下拉，电平不确定 | 外部已有上下拉的信号 |
| 上拉输入 | MODE=00, PUPD=01 | 默认高电平 | 按键检测(低有效) |
| 下拉输入 | MODE=00, PUPD=10 | 默认低电平 | 按键检测(高有效) |
| 模拟输入 | MODE=11 | 关闭数字功能 | ADC/DAC |

**输出模式：**

| 模式 | 说明 | 典型应用 |
|------|------|----------|
| 推挽输出 | 可输出高/低电平，驱动能力强 | LED、蜂鸣器 |
| 开漏输出 | 只能拉低，需外部上拉 | I2C(SDA/SCL)、电平转换 |
| 复用推挽 | GPIO由外设控制，推挽模式 | UART_TX、SPI_SCK |
| 复用开漏 | GPIO由外设控制，开漏模式 | I2C硬件模式 |

**输出速度选择：**

| 速度等级 | 频率 | 应用场景 |
|----------|------|----------|
| 低速(2MHz) | ≤2MHz | LED、按键 |
| 中速(25MHz) | ≤25MHz | 一般数字信号 |
| 高速(50MHz) | ≤50MHz | SPI、I2C |
| 超高速(100MHz) | ≤100MHz | FSMC、高速SPI |

> **注意**：输出速度越高，功耗和EMI越大。应根据实际需求选择最低够用的速度。

### 4.2 GPIO寄存器

**STM32F4 GPIO寄存器列表：**

| 寄存器 | 位宽 | 说明 |
|--------|------|------|
| MODER | 32bit(每引脚2bit) | 模式选择(输入/输出/复用/模拟) |
| OTYPER | 32bit(每引脚1bit) | 输出类型(0=推挽, 1=开漏) |
| OSPEEDR | 32bit(每引脚2bit) | 输出速度 |
| PUPDR | 32bit(每引脚2bit) | 上拉/下拉 |
| IDR | 32bit(低16bit有效) | 输入数据寄存器(只读) |
| ODR | 32bit(低16bit有效) | 输出数据寄存器(读写) |
| BSRR | 32bit | 位设置/清除寄存器(写1有效) |
| LCKR | 32bit | 配置锁定寄存器 |
| AFR[0]/AFR[1] | 32bit(每引脚4bit) | 复用功能选择(AF0-AF15) |

**直接寄存器操作 vs HAL库：**

```c
// ===== 直接寄存器操作 =====
// 设置PA5高电平
GPIOA->ODR |= (1 << 5);
// 设置PA5低电平
GPIOA->ODR &= ~(1 << 5);
// 使用BSRR(原子操作，推荐)
GPIOA->BSRR = (1 << 5);       // 设置高电平
GPIOA->BSRR = (1 << 21);      // 设置低电平 (5+16=21)
// 读取PA0
uint8_t val = (GPIOA->IDR >> 0) & 0x01;

// ===== HAL库操作 =====
// 设置高电平
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
// 设置低电平
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
// 翻转电平
HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
// 读取引脚
GPIO_PinState val = HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0);
```

> **性能对比**：寄存器操作约1个时钟周期，HAL库操作约5-10个时钟周期。在高频翻转场景(如软件SPI)下，寄存器操作优势明显。

### 4.3 GPIO高级应用

**外部中断(EXTI)配置：**

```c
// CubeMX自动生成的配置
void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // 使能GPIO时钟
    __HAL_RCC_GPIOA_CLK_ENABLE();

    // 配置PA0为外部中断，上升沿触发
    GPIO_InitStruct.Pin = GPIO_PIN_0;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;    // 上升沿触发
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;           // 下拉
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // 配置PA1为外部中断，双边沿触发
    GPIO_InitStruct.Pin = GPIO_PIN_1;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING_FALLING;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // 配置中断优先级
    HAL_NVIC_SetPriority(EXTI0_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);

    HAL_NVIC_SetPriority(EXTI1_IRQn, 2, 1);
    HAL_NVIC_EnableIRQ(EXTI1_IRQn);
}

// 中断服务函数
void EXTI0_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);
}

void EXTI1_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_1);
}

// 回调函数
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_0) {
        // PA0中断处理
        // 建议在此处设置标志位，在主循环中处理
        exti0_flag = 1;
    }
    if (GPIO_Pin == GPIO_PIN_1) {
        exti1_flag = 1;
    }
}
```

**EXTI注意事项：**
- EXTI0-EXTI15分别对应PX0-PX15（同编号不能同时使用）
- 即PA0和PB0不能同时作为EXTI源
- EXTI线16-23用于PVD、RTC等内部事件

---

## 5. 定时器深入

### 5.1 定时器分类

| 类型 | 定时器 | 位宽 | 通道 | 特殊功能 |
|------|--------|------|------|----------|
| 基本定时器 | TIM6, TIM7 | 16bit | 0 | 仅时基，可触发DAC |
| 通用定时器 | TIM2, TIM5 | 32bit | 4 | 输入捕获/输出比较/编码器 |
| 通用定时器 | TIM3, TIM4 | 16bit | 4 | 输入捕获/输出比较/编码器 |
| 通用定时器 | TIM9-TIM14 | 16bit | 1-2 | 简化版通用定时器 |
| 高级定时器 | TIM1, TIM8 | 16bit | 4 | 互补PWM、死区、刹车 |

### 5.2 定时器时基单元

```
时钟源 → PSC(预分频) → 计数器(CNT) → ARR(自动重装载) → 溢出事件
                                      ↓
                                   重复计数器(RCR) → 更新事件(仅高级定时器)
```

**时基参数计算：**

```
定时时间 = (PSC + 1) × (ARR + 1) / Timer_CLK

示例：定时1ms，Timer_CLK = 84MHz
PSC = 84-1 = 83
ARR = 1000-1 = 999
定时时间 = 84 × 1000 / 84,000,000 = 1ms

示例：定时1s，Timer_CLK = 84MHz
PSC = 8400-1 = 8399
ARR = 10000-1 = 9999
定时时间 = 8400 × 10000 / 84,000,000 = 1s
```

**定时器初始化代码：**

```c
TIM_HandleTypeDef htim2;

void TIM2_Init(void)
{
    TIM_ClockConfigTypeDef sClockSourceConfig = {0};
    TIM_MasterConfigTypeDef sMasterConfig = {0};

    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 8400 - 1;          // 84MHz / 8400 = 10kHz
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 10000 - 1;            // 10kHz / 10000 = 1Hz (1s)
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_Base_Init(&htim2);

    sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
    HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig);

    // 使能更新中断
    HAL_TIM_Base_Start_IT(&htim2);
}

// 中断服务函数
void TIM2_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim2);
}

// 更新中断回调
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM2) {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);  // LED闪烁
    }
}
```

### 5.3 PWM详解

**PWM模式：**

- **模式1**：CNT < CCR时输出有效电平(OCxM=110)
- **模式2**：CNT > CCR时输出有效电平(OCxM=111)
- 有效电平由CCxP位决定(0=高有效，1=低有效)

**占空比计算：**

```
占空比 = CCR / (ARR + 1) × 100%

示例：ARR = 999, CCR = 500
占空比 = 500 / 1000 = 50%

示例：ARR = 999, CCR = 750
占空比 = 750 / 1000 = 75%
```

**PWM初始化代码：**

```c
TIM_HandleTypeDef htim3;

void PWM_Init(void)
{
    TIM_OC_InitTypeDef sConfigOC = {0};

    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 84 - 1;         // 84MHz / 84 = 1MHz
    htim3.Init.Period = 1000 - 1;           // 1MHz / 1000 = 1kHz PWM频率
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim3);

    // 配置通道1
    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 500;                  // 初始占空比50%
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1);

    // 启动PWM
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
}

// 动态修改占空比
void Set_PWM_Duty(uint16_t duty)
{
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, duty);
}
```

**中心对齐模式 vs 边沿对齐模式：**

```
边沿对齐(Up Counting):
CNT: 0 → ARR → 0 → ARR → ...
PWM: ___|‾‾‾|___|‾‾‾|___

中心对齐(Up/Down Counting):
CNT: 0 → ARR → 0 → ARR → ...
PWM: ___|‾‾‾‾‾‾‾‾|___
     (减少谐波，电机控制常用)
```

### 5.4 编码器接口

**编码器模式配置：**

```c
TIM_HandleTypeDef htim4;

void Encoder_Init(void)
{
    TIM_Encoder_InitTypeDef sConfig = {0};

    htim4.Instance = TIM4;
    htim4.Init.Prescaler = 0;               // 不分频
    htim4.Init.Period = 65535;              // 最大计数值
    htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim4.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

    sConfig.EncoderMode = TIM_ENCODERMODE_TI12;  // 双通道模式
    sConfig.IC1Polarity = TIM_ICPOLARITY_RISING;
    sConfig.IC1Selection = TIM_ICSELECTION_DIRECTTI;
    sConfig.IC1Prescaler = TIM_ICPSC_DIV1;
    sConfig.IC1Filter = 0x0F;              // 滤波
    sConfig.IC2Polarity = TIM_ICPOLARITY_RISING;
    sConfig.IC2Selection = TIM_ICSELECTION_DIRECTTI;
    sConfig.IC2Prescaler = TIM_ICPSC_DIV1;
    sConfig.IC2Filter = 0x0F;
    HAL_TIM_Encoder_Init(&htim4, &sConfig);

    HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);
}

// 读取编码器值和方向
int16_t Read_Encoder(void)
{
    int16_t count = (int16_t)__HAL_TIM_GET_COUNTER(&htim4);
    __HAL_TIM_SET_COUNTER(&htim4, 0);  // 清零
    return count;  // 正值=正转，负值=反转
}

// 速度计算
// 速度(RPM) = count / (编码器线数 × 4倍频) / 采样时间(s) × 60
float Calculate_Speed(int16_t count, float sample_time_s)
{
    const float encoder_lines = 1000.0f;  // 编码器线数
    float rps = count / (encoder_lines * 4.0f) / sample_time_s;
    return rps * 60.0f;  // RPM
}
```

---

## 6. ADC/DAC深入

### 6.1 ADC详解

**STM32F4 ADC特性：**
- 12位逐次逼近型ADC
- 最大采样率：2.4MSPS(交替模式)或1.2MSPS(独立模式)
- 规则组：最多16个通道
- 注入组：最多4个通道(可打断规则组)
- 支持硬件过采样

**ADC工作模式：**

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 单次转换 | 转换一次后停止 | 低频采样 |
| 连续转换 | 转换完成后自动重新开始 | 连续监测 |
| 扫描模式 | 自动依次转换多个通道 | 多通道采集 |
| 间断模式 | 每次只转换N个通道 | 分组采集 |

**ADC + DMA连续采集：**

```c
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;
uint16_t adc_buffer[4];  // 4个通道

void ADC_DMA_Init(void)
{
    ADC_ChannelConfTypeDef sConfig = {0};

    // ADC配置
    hadc1.Instance = ADC1;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = ENABLE;           // 扫描模式
    hadc1.Init.ContinuousConvMode = ENABLE;     // 连续转换
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 4;             // 4个通道
    hadc1.Init.DMAContinuousRequests = ENABLE;   // DMA连续请求
    HAL_ADC_Init(&hadc1);

    // 通道0: PA0, 采样时间239.5周期
    sConfig.Channel = ADC_CHANNEL_0;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_239CYCLES_5;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    // 通道1: PA1
    sConfig.Channel = ADC_CHANNEL_1;
    sConfig.Rank = 2;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    // 通道2: PA2
    sConfig.Channel = ADC_CHANNEL_2;
    sConfig.Rank = 3;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    // 通道3: PA3
    sConfig.Channel = ADC_CHANNEL_3;
    sConfig.Rank = 4;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    // 启动ADC+DMA
    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buffer, 4);
}

// DMA传输完成回调
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        // adc_buffer[0~3] 包含4个通道的最新数据
        float voltage0 = adc_buffer[0] * 3.3f / 4096.0f;
        float voltage1 = adc_buffer[1] * 3.3f / 4096.0f;
        float voltage2 = adc_buffer[2] * 3.3f / 4096.0f;
        float voltage3 = adc_buffer[3] * 3.3f / 4096.0f;
    }
}
```

**模拟看门狗：**

```c
// 配置模拟看门狗，监控通道0
ADC_AnalogWDGConfTypeDef AnalogWDGConfig = {0};
AnalogWDGConfig.WatchdogMode = ADC_ANALOGWATCHDOG_SINGLE_REG;
AnalogWDGConfig.Channel = ADC_CHANNEL_0;
AnalogWDGConfig.HighThreshold = 3000;   // 上限
AnalogWDGConfig.LowThreshold = 1000;    // 下限
AnalogWDGConfig.ITMode = ENABLE;        // 使能中断
HAL_ADC_AnalogWDGConfig(&hadc1, &AnalogWDGConfig);

// 看门狗中断回调
void HAL_ADC_LevelOutOfWindowCallback(ADC_HandleTypeDef *hadc)
{
    // ADC值超出阈值范围
    alarm_flag = 1;
}
```

### 6.2 DAC详解

**DAC基本输出：**

```c
DAC_HandleTypeDef hdac;

void DAC_Init(void)
{
    DAC_ChannelConfTypeDef sConfig = {0};

    hdac.Instance = DAC;
    HAL_DAC_Init(&hdac);

    sConfig.DAC_Trigger = DAC_TRIGGER_NONE;       // 软件触发
    sConfig.DAC_OutputBuffer = DAC_OUTPUTBUFFER_ENABLE;
    HAL_DAC_ConfigChannel(&hdac, &sConfig, DAC_CHANNEL_1);

    HAL_DAC_Start(&hdac, DAC_CHANNEL_1);
}

// 输出指定电压
void DAC_SetVoltage(float voltage)
{
    uint32_t value = (uint32_t)(voltage / 3.3f * 4095.0f);
    HAL_DAC_SetValue(&hdac, DAC_CHANNEL_1, DAC_ALIGN_12B_R, value);
}
```

**DAC + DMA生成波形：**

```c
// 正弦波查找表(256点)
const uint16_t sine_table[256] = {
    2048, 2098, 2148, 2199, 2249, 2299, 2349, 2399,
    // ... 省略中间值
    1648, 1698, 1748, 1799, 1849, 1899, 1949, 1999
};

void DAC_DMA_SineWave(void)
{
    // TIM6触发DAC，DMA循环传输
    HAL_DAC_Start_DMA(&hdac, DAC_CHANNEL_1,
                      (uint32_t*)sine_table, 256, DAC_ALIGN_12B_R);
}
```

---

## 7. 通信接口深入

### 7.1 UART/USART详解

**波特率计算：**

```
USARTDIV = f_CK / (16 × BaudRate)
或在过采样8模式下:
USARTDIV = f_CK / (8 × BaudRate)

示例：PCLK2=84MHz, BaudRate=115200
USARTDIV = 84000000 / (16 × 115200) = 45.573
DIV_Mantissa = 45 (0x2D)
DIV_Fraction = 0.573 × 16 = 9.17 ≈ 9 (0x9)
BRR = 0x2D9

实际波特率 = 84000000 / (16 × 45.5625) = 115191 (误差0.008%)
```

**UART + DMA接收(空闲中断)：**

这是STM32串口接收的最佳实践方案，结合了DMA的高效性和空闲中断的灵活性：

```c
#define RX_BUF_SIZE 256
uint8_t rx_dma_buf[RX_BUF_SIZE];
volatile uint16_t rx_len = 0;
volatile uint8_t rx_complete = 0;

void UART_DMA_RX_Init(void)
{
    // 开启DMA接收
    HAL_UART_Receive_DMA(&huart1, rx_dma_buf, RX_BUF_SIZE);
    // 使能空闲中断
    __HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE);
}

// 重写USART1中断处理
void USART1_IRQHandler(void)
{
    if (__HAL_UART_GET_FLAG(&huart1, UART_FLAG_IDLE)) {
        __HAL_UART_CLEAR_IDLEFLAG(&huart1);  // 清除空闲标志

        // 计算接收到的数据长度
        uint16_t dma_remain = __HAL_DMA_GET_COUNTER(huart1.hdmarx);
        rx_len = RX_BUF_SIZE - dma_remain;

        if (rx_len > 0) {
            rx_complete = 1;

            // 暂停DMA，处理数据
            HAL_UART_AbortReceive(&huart1);

            // 处理接收到的数据
            process_rx_data(rx_dma_buf, rx_len);

            // 重新开启DMA接收
            HAL_UART_Receive_DMA(&huart1, rx_dma_buf, RX_BUF_SIZE);
        }
    }
    HAL_UART_IRQHandler(&huart1);
}
```

**printf重定向：**

```c
// 方法1：重写fputc(适用于MicroLIB)
#include <stdio.h>
int fputc(int ch, FILE *f)
{
    HAL_UART_Transmit(&huart1, (uint8_t*)&ch, 1, HAL_MAX_DELAY);
    return ch;
}

// 方法2：重写_write(适用于Newlib)
int _write(int file, char *ptr, int len)
{
    HAL_UART_Transmit(&huart1, (uint8_t*)ptr, len, HAL_MAX_DELAY);
    return len;
}

// 方法3：使用GCC的__io_putchar
int __io_putchar(int ch)
{
    HAL_UART_Transmit(&huart1, (uint8_t*)&ch, 1, HAL_MAX_DELAY);
    return ch;
}
```

### 7.2 SPI详解

**SPI四种模式：**

| 模式 | CPOL | CPHA | 时钟空闲 | 数据采样 |
|------|------|------|----------|----------|
| Mode 0 | 0 | 0 | 低 | 上升沿采样 |
| Mode 1 | 0 | 1 | 低 | 下降沿采样 |
| Mode 2 | 1 | 0 | 高 | 下降沿采样 |
| Mode 3 | 1 | 1 | 高 | 上升沿采样 |

**SPI + DMA高速传输：**

```c
SPI_HandleTypeDef hspi1;
DMA_HandleTypeDef hdma_spi1_tx;
DMA_HandleTypeDef hdma_spi1_rx;

void SPI_DMA_Transfer(uint8_t *tx_buf, uint8_t *rx_buf, uint16_t len)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET);  // 拉低CS

    HAL_SPI_TransmitReceive_DMA(&hspi1, tx_buf, rx_buf, len);

    // 等待传输完成(或在回调中处理)
    // 注意：不要在中断中等待
}

void HAL_SPI_TxRxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI1) {
        HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET);  // 拉高CS
        spi_transfer_done = 1;
    }
}
```

### 7.3 I2C详解

**I2C通信时序：**

```
起始条件: SDA从高到低，SCL保持高
数据传输: SCL高电平时SDA必须稳定
停止条件: SDA从低到高，SCL保持高

主机发送: [S][ADDR+W][ACK][DATA][ACK]...[P]
主机接收: [S][ADDR+R][ACK][DATA][ACK]...[P][NACK]
```

**I2C扫描设备地址：**

```c
void I2C_Scan(void)
{
    HAL_StatusTypeDef result;
    printf("I2C设备扫描:\r\n");

    for (uint16_t addr = 1; addr < 128; addr++) {
        result = HAL_I2C_IsDeviceReady(&hi2c1, addr << 1, 2, 10);
        if (result == HAL_OK) {
            printf("  发现设备: 0x%02X\r\n", addr);
        }
    }
    printf("扫描完成\r\n");
}
```

**软件I2C vs 硬件I2C：**

| 对比项 | 硬件I2C | 软件I2C |
|--------|---------|---------|
| 速度 | 最高400kHz(Fast) | 通常100-400kHz |
| CPU占用 | 低(DMA时几乎为0) | 高(全程CPU参与) |
| 引脚限制 | 固定引脚 | 任意GPIO |
| 可靠性 | 可能有硬件bug(F1系列) | 完全可控 |
| 推荐场景 | 高速/多从机 | 调试/引脚受限 |

> **重要提醒**：STM32F1系列的硬件I2C存在已知bug(总线锁死)，建议使用软件I2C或升级到F4/H7系列。

### 7.4 CAN总线

**CAN帧格式：**

```
标准帧(11bit ID):
[SOF][ID(11bit)][RTR][IDE][r0][DLC(4bit)][Data(0-8byte)][CRC][ACK][EOF]

扩展帧(29bit ID):
[SOF][ID(11bit)][SRR][IDE][ID(18bit)][RTR][r1][r0][DLC(4bit)][Data(0-8byte)][CRC][ACK][EOF]
```

**CAN过滤器配置：**

```c
// 过滤器配置 - 只接收ID为0x123的报文
CAN_FilterTypeDef sFilterConfig;

sFilterConfig.FilterBank = 0;
sFilterConfig.FilterMode = CAN_FILTERMODE_IDMASK;  // 标识符掩码模式
sFilterConfig.FilterScale = CAN_FILTERSCALE_32BIT;
sFilterConfig.FilterIdHigh = 0x123 << 5;   // ID左对齐
sFilterConfig.FilterIdLow = 0x0000;
sFilterConfig.FilterMaskIdHigh = 0x7FF << 5;  // 掩码：精确匹配
sFilterConfig.FilterMaskIdLow = 0x0000;
sFilterConfig.FilterFIFOAssignment = CAN_RX_FIFO0;
sFilterConfig.FilterActivation = ENABLE;
HAL_CAN_ConfigFilter(&hcan1, &sFilterConfig);

// 接收回调
void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan)
{
    CAN_RxHeaderTypeDef header;
    uint8_t data[8];
    HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &header, data);

    if (header.StdId == 0x123) {
        // 处理接收到的数据
    }
}
```

---

## 8. DMA深入

### 8.1 DMA架构

**STM32F4 DMA通道映射（部分）：**

| DMA | Stream | Channel | 外设请求 |
|-----|--------|---------|----------|
| DMA1 | Stream 0 | Channel 4 | SPI2_RX |
| DMA1 | Stream 1 | Channel 4 | SPI2_TX |
| DMA1 | Stream 2 | Channel 4 | USART3_RX |
| DMA1 | Stream 3 | Channel 7 | USART3_TX |
| DMA1 | Stream 5 | Channel 4 | USART2_RX |
| DMA1 | Stream 6 | Channel 5 | USART2_TX |
| DMA1 | Stream 7 | Channel 4 | USART1_TX |
| DMA2 | Stream 2 | Channel 4 | USART1_RX |
| DMA2 | Stream 0 | Channel 0 | ADC1 |
| DMA2 | Stream 3 | Channel 0 | ADC2 |
| DMA2 | Stream 5 | Channel 1 | ADC3 |

> **重要**：每个DMA Stream在同一时刻只能映射到一个外设，通过Channel选择。

**DMA优先级仲裁：**

```
软件优先级（配置）:
├── Very High (最高)
├── High
├── Medium
└── Low (最低)

硬件优先级（同软件优先级时）:
Stream 0 > Stream 1 > ... > Stream 7
```

**DMA传输方向：**

| 方向 | 源 → 目标 | 典型应用 |
|------|-----------|----------|
| 外设→内存 | 寄存器 → SRAM | ADC采集、UART接收 |
| 内存→外设 | SRAM → 寄存器 | DAC输出、UART发送 |
| 内存→内存 | SRAM → SRAM | 大块数据拷贝 |
| 外设→外设 | 寄存器 → 寄存器 | 较少使用 |

### 8.2 DMA高级应用

**双缓冲模式(Double Buffer)：**

```c
// 双缓冲模式：一个缓冲区在被CPU处理时，另一个正在被DMA填充
#define BUF_SIZE 1024
uint8_t buf0[BUF_SIZE];
uint8_t buf1[BUF_SIZE];

void DMA_DoubleBuffer_Init(void)
{
    HAL_DMAEx_MultiBufferStart(&hdma_adc1,
                                (uint32_t)&ADC1->DR,   // 源：ADC数据寄存器
                                (uint32_t)buf0,          // 目标缓冲区0
                                (uint32_t)buf1,          // 目标缓冲区1
                                BUF_SIZE);
}

// 缓冲区切换回调
void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
    // buf0满了一半，可以处理buf0的前半部分
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    // buf0满了，DMA切换到buf1，处理buf0
    // 或 buf1满了，DMA切换到buf0，处理buf1
}
```

**内存到内存拷贝：**

```c
// DMA内存拷贝，比memcpy更快（大数据量时）
HAL_StatusTypeDef DMA_MemCopy(uint32_t *src, uint32_t *dst, uint16_t len)
{
    hdma_mem2mem.Instance = DMA2_Stream0;
    hdma_mem2mem.Init.Channel = DMA_CHANNEL_0;
    hdma_mem2mem.Init.Direction = DMA_MEMORY_TO_MEMORY;
    hdma_mem2mem.Init.PeriphInc = DMA_PINC_ENABLE;
    hdma_mem2mem.Init.MemInc = DMA_MINC_ENABLE;
    hdma_mem2mem.Init.PeriphDataAlignment = DMA_PDATAALIGN_WORD;
    hdma_mem2mem.Init.MemDataAlignment = DMA_MDATAALIGN_WORD;
    hdma_mem2mem.Init.Mode = DMA_NORMAL;
    hdma_mem2mem.Init.Priority = DMA_PRIORITY_HIGH;
    HAL_DMA_Init(&hdma_mem2mem);

    return HAL_DMA_Start(&hdma_mem2mem, (uint32_t)src, (uint32_t)dst, len);
}
```

---

## 9. 低功耗设计

### 9.1 低功耗模式

**STM32F4低功耗模式对比：**

| 模式 | 唤醒源 | 唤醒时间 | 功耗 | 保留内容 | 适用场景 |
|------|--------|----------|------|----------|----------|
| Sleep | 任意中断 | 1个周期 | ~15mA@168MHz | 全部 | 短暂空闲 |
| Stop | EXTI | ~5us | ~30uA(典型) | SRAM | 长时间空闲 |
| Standby | WKUP/RTC/IWDG | ~50us | ~2.4uA | 仅备份域 | 极低功耗 |

**Sleep模式：**

```c
// 进入Sleep模式(仅CPU停止，外设继续运行)
HAL_SuspendTick();  // 暂停SysTick避免频繁唤醒
HAL_PWR_EnterSLEEPMode(PWR_MAINREGULATOR_ON, PWR_SLEEPENTRY_WFI);
// 被中断唤醒后继续执行
HAL_ResumeTick();
```

**Stop模式：**

```c
// 进入Stop模式前的准备
void Enter_Stop_Mode(void)
{
    // 1. 配置唤醒源(如外部中断)
    HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN1);  // PA0唤醒

    // 2. 配置电压调节器(低功耗模式)
    HAL_SuspendTick();

    // 3. 进入Stop模式
    HAL_PWR_EnterSTOPMode(PWR_LOWPOWERREGULATOR_ON, PWR_STOPENTRY_WFI);

    // 4. 被唤醒后恢复时钟(Stop模式后PLL关闭)
    SystemClock_Config();
    HAL_ResumeTick();
}
```

**Standby模式：**

```c
void Enter_Standby_Mode(void)
{
    // 1. 清除唤醒标志
    __HAL_PWR_CLEAR_FLAG(PWR_FLAG_WU);
    __HAL_PWR_CLEAR_FLAG(PWR_FLAG_SB);

    // 2. 配置RTC唤醒(可选)
    HAL_RTCEx_SetWakeUpTimer(&hrtc, 60, RTC_WAKEUPCLOCK_CK_SPRE_16BITS);

    // 3. 使能唤醒引脚
    HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN1);

    // 4. 进入Standby模式(此函数不返回)
    HAL_PWR_EnterSTANDBYMode();
}
```

### 9.2 低功耗设计技巧

**降低系统功耗的完整清单：**

```
1. 时钟优化
   ├── 降低系统时钟频率
   ├── 关闭未使用的外设时钟
   ├── 关闭未使用的PLL
   └── 使用HSI代替HSE(精度允许时)

2. GPIO优化
   ├── 未使用引脚设为模拟输入(关闭施密特触发器)
   ├── 输出引脚避免悬空(有确定电平)
   └── 避免输入引脚浮空(上拉或下拉)

3. 外设优化
   ├── ADC/DAC不使用时关闭
   ├── 串口不使用时关闭
   ├── DMA不使用时关闭
   └── 定时器不使用时关闭

4. 电源优化
   ├── 使用内核电压调节器低功耗模式
   ├── 关闭Flash预取(降低性能换取功耗)
   └── 使用独立电源域(如关闭VDDA)
```

**未使用GPIO的处理：**

```c
// 所有未使用的引脚应配置为模拟输入
GPIO_InitTypeDef GPIO_InitStruct = {0};

// 假设PB2未使用
GPIO_InitStruct.Pin = GPIO_PIN_2;
GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;   // 模拟模式，关闭数字输入
GPIO_InitStruct.Pull = GPIO_NOPULL;         // 模拟模式下无效
HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
```

---

## 10. Bootloader设计

### 10.1 串口Bootloader

**Flash布局设计：**

```
┌─────────────────────┐ 0x08000000
│   Bootloader (32KB) │
│   (Sector 0-1)      │
├─────────────────────┤ 0x08008000
│   Application (480KB)│
│   (Sector 2-6)      │
├─────────────────────┤ 0x08080000
│   Backup Area       │
│   (Sector 7)        │
└─────────────────────┘ 0x080FFFFF
```

**升级协议设计：**

```
帧格式:
[起始字节(0xAA)] [命令(1byte)] [数据长度(2byte)] [数据(Nbyte)] [CRC16(2byte)] [结束字节(0x55)]

命令定义:
0x01: 握手(Handshake)
0x02: 擦除Flash
0x03: 写入数据
0x04: 校验数据
0x05: 跳转到APP
0x06: 查询版本

应答格式:
[0xAA] [命令] [状态(0=成功, 1=失败)] [数据...] [CRC16] [0x55]
```

**Bootloader核心代码：**

```c
// Flash操作函数
HAL_StatusTypeDef Flash_Erase(uint32_t start_sector, uint32_t end_sector)
{
    HAL_StatusTypeDef status;
    FLASH_EraseInitTypeDef erase_init;
    uint32_t sector_error;

    erase_init.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase_init.Sector = start_sector;
    erase_init.NbSectors = end_sector - start_sector + 1;
    erase_init.VoltageRange = FLASH_VOLTAGE_RANGE_3;  // 2.7-3.6V

    HAL_FLASH_Unlock();
    status = HAL_FLASHEx_Erase(&erase_init, &sector_error);
    HAL_FLASH_Lock();

    return status;
}

HAL_StatusTypeDef Flash_Write(uint32_t addr, uint8_t *data, uint32_t len)
{
    HAL_FLASH_Unlock();

    // 按字(32bit)写入
    for (uint32_t i = 0; i < len; i += 4) {
        uint32_t word = *(uint32_t*)(data + i);
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr + i, word) != HAL_OK) {
            HAL_FLASH_Lock();
            return HAL_ERROR;
        }
    }

    HAL_FLASH_Lock();
    return HAL_OK;
}

// 跳转到APP
void Jump_To_App(uint32_t app_addr)
{
    // 1. 检查APP地址有效性
    if (((*(__IO uint32_t*)app_addr) & 0x2FF00000) == 0x20000000) {
        // 2. 关闭所有中断
        __disable_irq();

        // 3. 关闭所有外设时钟
        HAL_RCC_DeInit();
        HAL_DeInit();

        // 4. 关闭滴答定时器
        SysTick->CTRL = 0;
        SysTick->LOAD = 0;
        SysTick->VAL = 0;

        // 5. 设置主堆栈指针
        __set_MSP(*(__IO uint32_t*)app_addr);

        // 6. 获取复位向量
        uint32_t jump_addr = *(__IO uint32_t*)(app_addr + 4);
        void (*app_entry)(void) = (void (*)(void))jump_addr;

        // 7. 重新使能中断
        __enable_irq();

        // 8. 跳转
        app_entry();
    }
}
```

### 10.2 IAP升级

**APP链接地址设置：**

```
// Keil MDK: Options for Target -> Linker
// 或在scatter文件中指定
// IROM1起始地址: 0x08008000, 大小: 0x78000

// STM32CubeIDE: STM32F407VGTx_FLASH.ld
/* FLASH (rx) : ORIGIN = 0x08008000, LENGTH = 480K */
```

**中断向量表偏移：**

```c
// 在APP的main()函数开头，SystemClock_Config()之前
void main(void)
{
    // 设置中断向量表偏移
    SCB->VTOR = 0x08008000;  // APP起始地址

    HAL_Init();
    SystemClock_Config();
    // ... 其他初始化
}
```

**CRC校验实现：**

```c
// 使用STM32硬件CRC
uint32_t Calculate_CRC32(uint32_t *data, uint32_t len)
{
    CRC_HandleTypeDef hcrc;
    hcrc.Instance = CRC;
    hcrc.Init.DefaultPolynomialUse = DEFAULT_POLYNOMIAL_ENABLE;
    hcrc.Init.DefaultInitValueUse = DEFAULT_INIT_VALUE_ENABLE;
    hcrc.Init.InputDataInversionMode = CRC_INPUTDATA_INVERSION_NONE;
    hcrc.Init.OutputDataInversionMode = CRC_OUTPUTDATA_INVERSION_DISABLE;
    hcrc.InputDataFormat = CRC_INPUTDATA_FORMAT_WORDS;
    HAL_CRC_Init(&hcrc);

    return HAL_CRC_Calculate(&hcrc, data, len);
}

// 验证APP完整性
uint8_t Verify_App(uint32_t app_addr, uint32_t size, uint32_t expected_crc)
{
    uint32_t crc = Calculate_CRC32((uint32_t*)app_addr, size / 4);
    return (crc == expected_crc) ? 1 : 0;
}
```

---

## 11. FreeRTOS集成

### 11.1 CubeMX配置FreeRTOS

**CMSIS-RTOS v2 API核心函数：**

```c
// 任务管理
osThreadId_t osThreadNew(osThreadFunc_t func, void *arg, const osThreadAttr_t *attr);
osStatus_t osThreadTerminate(osThreadId_t thread_id);
osStatus_t osDelay(uint32_t ticks);
osStatus_t osDelayUntil(uint32_t ticks);

// 信号量
osSemaphoreId_t osSemaphoreNew(uint32_t max_count, uint32_t initial_count, const osSemaphoreAttr_t *attr);
osStatus_t osSemaphoreAcquire(osSemaphoreId_t sem_id, uint32_t timeout);
osStatus_t osSemaphoreRelease(osSemaphoreId_t sem_id);

// 互斥锁
osMutexId_t osMutexNew(const osMutexAttr_t *attr);
osStatus_t osMutexAcquire(osMutexId_t mutex_id, uint32_t timeout);
osStatus_t osMutexRelease(osMutexId_t mutex_id);

// 消息队列
osMessageQueueId_t osMessageQueueNew(uint32_t msg_count, uint32_t msg_size, const osMessageQueueAttr_t *attr);
osStatus_t osMessageQueuePut(osMessageQueueId_t mq_id, const void *msg_ptr, uint8_t msg_prio, uint32_t timeout);
osStatus_t osMessageQueueGet(osMessageQueueId_t mq_id, void *msg_ptr, uint8_t *msg_prio, uint32_t timeout);

// 任务通知(轻量级，替代信号量/邮箱)
osStatus_t osThreadFlagsSet(osThreadId_t thread_id, uint32_t flags);
uint32_t osThreadFlagsWait(uint32_t flags, uint32_t options, uint32_t timeout);
```

**任务创建示例：**

```c
// 任务句柄
osThreadId_t task_led_handle;
osThreadId_t task_uart_handle;
osMessageQueueId_t uart_queue_handle;

// LED任务
void Task_LED(void *argument)
{
    for (;;) {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
        osDelay(500);  // 500ms
    }
}

// UART处理任务
void Task_UART(void *argument)
{
    uint8_t msg[64];
    for (;;) {
        // 从消息队列接收数据
        if (osMessageQueueGet(uart_queue_handle, msg, NULL, osWaitForever) == osOK) {
            // 处理UART数据
            process_uart_data(msg);
        }
    }
}

// 在main中创建任务
void app_init(void)
{
    // 创建LED任务
    const osThreadAttr_t led_attr = {
        .name = "LED_Task",
        .stack_size = 128 * 4,    // 512字节
        .priority = osPriorityNormal,
    };
    task_led_handle = osThreadNew(Task_LED, NULL, &led_attr);

    // 创建UART任务
    const osThreadAttr_t uart_attr = {
        .name = "UART_Task",
        .stack_size = 512 * 4,    // 2048字节
        .priority = osPriorityAboveNormal,
    };
    task_uart_handle = osThreadNew(Task_UART, NULL, &uart_attr);

    // 创建消息队列
    uart_queue_handle = osMessageQueueNew(16, 64, NULL);  // 16条消息，每条64字节
}
```

### 11.2 STM32 HAL与FreeRTOS协作

**中断优先级与FreeRTOS：**

```
FreeRTOS可管理的中断优先级范围:
├── configMAX_SYSCALL_INTERRUPT_PRIORITY = 5 (默认)
├── 优先级 5-15: FreeRTOS可管理(可调用API)
└── 优先级 0-4: FreeRTOS不可管理(禁止调用API)

建议优先级分配:
├── 0: 硬件故障(最高优先级)
├── 1: 电机控制PWM(时间关键)
├── 2: 外部紧急中断
├── 3-4: 高速通信(SPI DMA)
├── 5-7: 一般外设(UART, ADC)
├── 8-10: 低速外设(I2C, 按键)
└── 11-15: 非关键任务
```

**关键配置项（FreeRTOSConfig.h）：**

```c
// 时钟配置
#define configCPU_CLOCK_HZ              (168000000)    // CPU频率
#define configTICK_RATE_HZ              (1000)         // 系统节拍1kHz

// 内存配置
#define configTOTAL_HEAP_SIZE           ((size_t)(32 * 1024))  // 32KB堆
#define configMINIMAL_STACK_SIZE        ((uint16_t)128)        // 最小栈128字

// 任务配置
#define configMAX_PRIORITIES            (56)           // 最大优先级数
#define configMAX_TASK_NAME_LEN         (16)           // 任务名最大长度
#define configUSE_16_BIT_TICKS          0              // 32位节拍计数

// 功能开关
#define configUSE_MUTEXES               1              // 使能互斥锁
#define configUSE_COUNTING_SEMAPHORES   1              // 使能计数信号量
#define configUSE_TASK_NOTIFICATIONS    1              // 使能任务通知
#define configUSE_QUEUE_SETS            0              // 禁用队列集
#define configUSE_TIMERS                1              // 使能软件定时器

// 调试配置
#define configUSE_TRACE_FACILITY        1              // 使能追踪
#define configCHECK_FOR_STACK_OVERFLOW  2              // 栈溢出检测(方法2)
#define configUSE_MALLOC_FAILED_HOOK    1              // 内存分配失败钩子
```

**HAL_Delay vs osDelay：**

```c
// ❌ 错误：在FreeRTOS任务中使用HAL_Delay
// HAL_Delay基于SysTick轮询，会阻塞整个CPU
void Task_Bad(void *argument) {
    for (;;) {
        do_something();
        HAL_Delay(1000);  // 阻塞所有任务！
    }
}

// ✓ 正确：在FreeRTOS任务中使用osDelay
// osDelay会将任务挂起，让出CPU给其他任务
void Task_Good(void *argument) {
    for (;;) {
        do_something();
        osDelay(1000);  // 任务挂起1秒，其他任务可以运行
    }
}
```

**Tickless低功耗模式：**

```c
// 在FreeRTOSConfig.h中使能
#define configUSE_TICKLESS_IDLE         1

// 实现低功耗钩子函数
void PreSleepProcessing(uint32_t *ulExpectedIdleTime)
{
    // 进入低功耗前
    HAL_SuspendTick();
    HAL_PWR_EnterSLEEPMode(PWR_LOWPOWERREGULATOR_ON, PWR_SLEEPENTRY_WFI);
}

void PostSleepProcessing(uint32_t *ulExpectedIdleTime)
{
    // 退出低功耗后
    HAL_ResumeTick();
}
```

---

## 12. 调试技巧

### 12.1 Hard Fault分析

**Hard Fault处理流程：**

```c
// Hard Fault信息捕获
typedef struct {
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r12;
    uint32_t lr;
    uint32_t pc;
    uint32_t psr;
} HardFault_Context_t;

volatile HardFault_Context_t fault_context;

void HardFault_Handler(void)
{
    __asm volatile (
        "TST LR, #4         \n"
        "ITE EQ             \n"
        "MRSEQ R0, MSP      \n"
        "MRSNE R0, PSP      \n"
        "B hard_fault_handler_c \n"
    );
}

void hard_fault_handler_c(uint32_t *stack)
{
    fault_context.r0  = stack[0];
    fault_context.r1  = stack[1];
    fault_context.r2  = stack[2];
    fault_context.r3  = stack[3];
    fault_context.r12 = stack[4];
    fault_context.lr  = stack[5];
    fault_context.pc  = stack[6];   // 故障发生地址
    fault_context.psr = stack[7];

    // 分析故障原因
    uint32_t cfsr = SCB->CFSR;     // 可配置故障状态寄存器
    uint32_t hfsr = SCB->HFSR;     // 硬件故障状态寄存器
    uint32_t bfar = SCB->BFAR;     // 总线故障地址寄存器

    // 死循环，便于调试器查看
    while (1) {
        __NOP();
    }
}
```

**CFSR故障类型解析：**

| 位域 | 名称 | 含义 | 常见原因 |
|------|------|------|----------|
| [0] | IACCVIOL | 指令访问违规 | 执行了无权限的内存区域 |
| [1] | DACCVIOL | 数据访问违规 | 访问了无权限的内存区域 |
| [3] | MUNSTKERR | 出栈错误 | 栈指针损坏 |
| [4] | MSTKERR | 入栈错误 | 栈溢出 |
| [7] | MMARVALID | MMFAR有效 | 存储器管理故障地址有效 |
| [8] | IBUSERR | 指令总线错误 | 从无效地址取指 |
| [9] | PRECISERR | 精确数据总线错误 | 访问了无效地址 |
| [10] | IMPRECISERR | 非精确数据总线错误 | DMA访问了无效地址 |
| [11] | UNSTKERR | 出栈总线错误 | 栈损坏 |
| [12] | STKERR | 入栈总线错误 | 栈溢出 |
| [15] | BFARVALID | BFAR有效 | 总线故障地址有效 |
| [16] | UNDEFINSTR | 未定义指令 | 跳转到了错误地址 |
| [24] | NOCP | 无协处理器 | 访问了FPU但未使能 |
| [25] | INVPC | 非法PC | 非法的EXC_RETURN值 |
| [26] | INVSTATE | 非法状态 | 跳转到非对齐地址 |

### 12.2 栈溢出检测

```c
// 方法1：FreeRTOS栈溢出检测
// 在FreeRTOSConfig.h中:
#define configCHECK_FOR_STACK_OVERFLOW  2

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    // 栈溢出！在此设置断点
    (void)xTask;
    (void)pcTaskName;
    while (1);
}

// 方法2：栈标记检测
// 在任务栈底部填充固定模式
#define STACK_FILL_PATTERN 0xA5A5A5A5

void Fill_Stack_Pattern(uint32_t *stack, uint32_t size)
{
    for (uint32_t i = 0; i < size / 4; i++) {
        stack[i] = STACK_FILL_PATTERN;
    }
}

uint32_t Check_Stack_Usage(uint32_t *stack, uint32_t size)
{
    uint32_t unused = 0;
    for (uint32_t i = 0; i < size / 4; i++) {
        if (stack[i] == STACK_FILL_PATTERN) {
            unused++;
        } else {
            break;
        }
    }
    return (size - unused * 4);  // 返回已使用字节数
}
```

### 12.3 SWD/JTAG调试

**调试接口引脚：**

| 功能 | SWD | JTAG |
|------|-----|------|
| 数据 | SWDIO (PA13) | TDI (PA15) |
| 时钟 | SWCLK (PA14) | TCK (PA14) |
| 复位 | NRST | NRST |
| 其他 | - | TDO (PA3), TMS (PA13), TRST (PB4) |

> **推荐使用SWD**：只需2根线(SWDIO/SWCLK)加GND，节省引脚，功能完整。

**SWO调试输出：**

```c
// 配置SWO输出printf
// 在debug配置中使能SWO，设置CPU频率匹配

// ITM重定向printf
int fputc(int ch, FILE *f)
{
    ITM_SendChar(ch);  // 通过SWO输出
    return ch;
}

// 需要在调试器中开启SWO引脚和设置正确的时钟频率
```

**RTT(Real-Time Transfer)：**

RTT是Segger提供的双向调试通道，比SWO更快更可靠：

```c
// 1. 添加SEGGER_RTT.c和SEGGER_RTT.h到工程
// 2. 在代码中使用
#include "SEGGER_RTT.h"

void main(void)
{
    SEGGER_RTT_Init();

    SEGGER_RTT_printf(0, "Hello RTT!\n");

    // 从RTT读取输入(用于调试命令)
    char buf[32];
    int len = SEGGER_RTT_Read(0, buf, sizeof(buf));
}
```

### 12.4 其他调试技巧

**断言增强：**

```c
// 自定义断言，打印更多信息
#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    printf("Assertion failed: file %s, line %lu\r\n", file, line);
    while (1);
}
#endif

// 使用示例
assert_param(IS_GPIO_PIN(GPIO_PIN_5));
```

**变量监视窗口优化：**

```c
// 将关键变量声明为volatile，防止被优化掉
volatile uint32_t debug_counter = 0;
volatile float debug_value = 0.0f;

// 在关键位置插入观察点
debug_counter++;  // 在此设置数据断点
```

---

## 13. 常见问题与解决方案

### 13.1 晶振不起振

**问题现象**：MCU无法启动，或启动后时钟不正确。

**排查清单**：

```
1. 硬件检查
   ├── 晶振型号是否正确(8MHz HSE, 32.768kHz LSE)
   ├── 负载电容是否匹配(通常6-20pF)
   ├── 晶振是否靠近MCU(走线<5mm)
   ├── 是否有地平面屏蔽
   └── 用示波器测量OSC_IN/OSC_OUT波形

2. 软件检查
   ├── RCC配置是否选择HSE
   ├── 是否使能了HSE旁路模式(使用有源晶振时)
   └── 启动超时设置是否合理

3. 常见错误
   ├── 负载电容过大 → 振幅不足
   ├── 负载电容过小 → 频率偏高
   ├── 走线过长 → 无法起振
   └── 未焊接负载电容 → 无法起振
```

**HSE旁路模式（使用有源晶振或外部时钟源）：**

```c
RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;  // 而非RCC_HSE_ON
```

### 13.2 电源纹波

**问题现象**：ADC采集不稳定，通信偶发错误，系统偶发复位。

**解决方案**：

```
1. PCB设计
   ├── VDD/VSS引脚必须就近放置去耦电容(100nF)
   ├── VDDA/VSSA引脚使用独立LC滤波
   ├── 大容量电容(10uF-47uF)靠近芯片
   └── 电源走线尽量宽

2. 软件补偿
   ├── ADC多次采样取平均
   ├── 使用ADC内部参考电压校准
   └── 数字滤波(中值滤波、滑动平均)
```

**ADC软件滤波实现：**

```c
// 滑动平均滤波
#define FILTER_SIZE 16
uint16_t filter_buf[FILTER_SIZE];
uint8_t filter_index = 0;
uint32_t filter_sum = 0;

uint16_t Moving_Average(uint16_t new_value)
{
    filter_sum -= filter_buf[filter_index];
    filter_buf[filter_index] = new_value;
    filter_sum += new_value;
    filter_index = (filter_index + 1) % FILTER_SIZE;
    return (uint16_t)(filter_sum / FILTER_SIZE);
}

// 中值滤波
uint16_t Median_Filter(uint16_t *buf, uint8_t size)
{
    // 简单冒泡排序
    for (uint8_t i = 0; i < size - 1; i++) {
        for (uint8_t j = 0; j < size - 1 - i; j++) {
            if (buf[j] > buf[j + 1]) {
                uint16_t temp = buf[j];
                buf[j] = buf[j + 1];
                buf[j + 1] = temp;
            }
        }
    }
    return buf[size / 2];  // 返回中值
}
```

### 13.3 Flash读保护

**RDP(Read-Out Protection)等级：**

| 等级 | 说明 | 解除后果 |
|------|------|----------|
| Level 0 | 无保护 | - |
| Level 1 | 读保护 | 会触发全片擦除(Flash mass erase) |
| Level 2 | 永久保护 | 无法解除，JTAG/SWD永久禁用 |

```c
// 读取当前保护等级
uint32_t rdp_level = FLASH_OB_GetRDP();

// 设置Level 1保护(CubeProgrammer中操作更安全)
HAL_FLASH_OB_Unlock();
FLASH_OBProgramInitTypeDef ob_init;
ob_init.OptionType = OPTIONBYTE_RDP;
ob_init.RDPLevel = OB_RDP_LEVEL_1;
HAL_FLASHEx_OBProgram(&ob_init);
HAL_FLASH_OB_Launch();  // 触发选项字节加载(会导致复位)
HAL_FLASH_OB_Lock();
```

> **警告**：不要轻易设置Level 2！一旦设置，芯片将无法再被调试或读取，也无法解除保护。

### 13.4 复位电路设计

**推荐复位电路：**

```
         VDD
          │
         [10K] (上拉电阻)
          │
NRST ─────┤
          │
        [100nF] (滤波电容)
          │
         GND

可选：按键连接NRST到GND(手动复位)
```

**复位源排查：**

```c
// 读取复位标志
if (__HAL_RCC_GET_FLAG(RCC_FLAG_PINRST)) {
    // 外部复位(NRST引脚)
}
if (__HAL_RCC_GET_FLAG(RCC_FLAG_PORRST)) {
    // 上电复位
}
if (__HAL_RCC_GET_FLAG(RCC_FLAG_SFTRST)) {
    // 软件复位(NVIC_SystemReset())
}
if (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST)) {
    // 独立看门狗复位
}
if (__HAL_RCC_GET_FLAG(RCC_FLAG_WWDGRST)) {
    // 窗口看门狗复位
}
if (__HAL_RCC_GET_FLAG(RCC_FLAG_LPWRRST)) {
    // 低功耗复位
}

// 清除所有复位标志
__HAL_RCC_CLEAR_RESET_FLAGS();
```

### 13.5 BOOT引脚配置

**启动模式选择：**

| BOOT1 | BOOT0 | 启动模式 | 说明 |
|-------|-------|----------|------|
| X | 0 | 从Flash启动 | 正常运行模式 |
| 0 | 1 | 从System Memory启动 | 内置Bootloader(串口下载) |
| 1 | 1 | 从SRAM启动 | 调试用，掉电丢失 |

**典型电路设计：**

```
BOOT0 ──── [10K] ──── GND        (默认从Flash启动)
                     │
                   [按键] ──── VDD  (按下时从System Memory启动)

BOOT1(PB2) ──── [10K] ──── GND   (正常情况下拉到GND)
```

---

## 附录A：STM32F407引脚复用表（部分）

| 引脚 | AF0 | AF1 | AF2 | AF3 | AF4 | AF5 | AF6 | AF7 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|
| PA0 | - | TIM2_CH1 | TIM5_CH1 | - | - | SPI1_SCK | - | USART2_CTS |
| PA1 | - | TIM2_CH2 | TIM5_CH2 | - | - | SPI1_MISO | - | USART2_RTS |
| PA2 | - | TIM2_CH3 | TIM5_CH3 | - | - | SPI1_MOSI | - | USART2_TX |
| PA5 | - | TIM2_CH1 | - | - | - | SPI1_SCK | - | - |
| PA9 | - | TIM1_CH2 | - | - | - | SPI2_SCK | - | USART1_TX |
| PA10 | - | TIM1_CH3 | - | - | - | SPI2_MISO | - | USART1_RX |
| PA11 | - | TIM1_CH4 | - | OTG_FS_DM | - | - | - | CAN1_RX |
| PA12 | - | TIM1_ETR | - | OTG_FS_DP | - | - | - | CAN1_TX |
| PB6 | - | TIM4_CH1 | - | - | I2C1_SCL | - | - | USART1_TX |
| PB7 | - | TIM4_CH2 | - | - | I2C1_SDA | - | - | USART1_RX |

## 附录B：常用寄存器速查

### RCC寄存器

| 寄存器 | 说明 |
|--------|------|
| RCC_CR | 时钟控制寄存器(HSE/HSI/PLL使能与状态) |
| RCC_PLLCFGR | PLL配置寄存器(M/N/P/Q) |
| RCC_CFGR | 时钟配置寄存器(SW/HPRE/PPRE1/PPRE2) |
| RCC_AHB1ENR | AHB1外设时钟使能(GPIO/OTG/DMA等) |
| RCC_APB1ENR | APB1外设时钟使能(USART2-5/TIM2-7/I2C等) |
| RCC_APB2ENR | APB2外设时钟使能(USART1/TIM1/SPI1/ADC等) |
| RCC_CSR | 控制/状态寄存器(复位源标志) |

### GPIO寄存器

| 寄存器 | 说明 |
|--------|------|
| GPIOx_MODER | 模式选择(00=输入/01=输出/10=复用/11=模拟) |
| GPIOx_OTYPER | 输出类型(0=推挽/1=开漏) |
| GPIOx_OSPEEDR | 输出速度(00=2MHz/01=25MHz/10=50MHz/11=100MHz) |
| GPIOx_PUPDR | 上拉下拉(00=无/01=上拉/10=下拉) |
| GPIOx_IDR | 输入数据(只读) |
| GPIOx_ODR | 输出数据(读写) |
| GPIOx_BSRR | 位设置/复置(低16bit置位/高16bit清零) |
| GPIOx_LCKR | 配置锁定 |
| GPIOx_AFRL | 复用功能低8引脚(AF0-AF7) |
| GPIOx_AFRH | 复用功能高8引脚(AF8-AF15) |

## 附录C：常用HAL函数速查

### 系统函数

```c
HAL_Init();                        // HAL库初始化
HAL_DeInit();                      // HAL库反初始化
HAL_Delay(ms);                     // 毫秒延时(阻塞)
HAL_GetTick();                     // 获取当前tick
HAL_IncTick();                     // tick递增(在SysTick中断中调用)
HAL_GetUIDw0/1/2();               // 获取唯一ID
```

### GPIO函数

```c
HAL_GPIO_Init(GPIOx, &init);       // 初始化GPIO
HAL_GPIO_DeInit(GPIOx, pin);       // 反初始化GPIO
HAL_GPIO_ReadPin(GPIOx, pin);      // 读取引脚
HAL_GPIO_WritePin(GPIOx, pin, val);// 写入引脚
HAL_GPIO_TogglePin(GPIOx, pin);    // 翻转引脚
HAL_GPIO_LockPin(GPIOx, pin);      // 锁定引脚配置
```

### 定时器函数

```c
HAL_TIM_Base_Init(htim);           // 初始化时基
HAL_TIM_Base_Start(htim);          // 启动定时器
HAL_TIM_Base_Start_IT(htim);       // 启动定时器中断
HAL_TIM_PWM_Init(htim);            // 初始化PWM
HAL_TIM_PWM_Start(htim, channel);  // 启动PWM输出
HAL_TIM_IC_Start(htim, channel);   // 启动输入捕获
HAL_TIM_Encoder_Start(htim, ch);   // 启动编码器模式
__HAL_TIM_SET_COMPARE(htim, ch, val); // 设置比较值
__HAL_TIM_GET_COUNTER(htim);       // 获取计数值
```

### UART函数

```c
HAL_UART_Init(huart);              // 初始化UART
HAL_UART_Transmit(huart, data, len, timeout);  // 阻塞发送
HAL_UART_Receive(huart, data, len, timeout);   // 阻塞接收
HAL_UART_Transmit_IT(huart, data, len);        // 中断发送
HAL_UART_Receive_IT(huart, data, len);         // 中断接收
HAL_UART_Transmit_DMA(huart, data, len);       // DMA发送
HAL_UART_Receive_DMA(huart, data, len);        // DMA接收
```

---

## 附录D：学习资源推荐

### 官方文档

| 文档 | 说明 | 获取方式 |
|------|------|----------|
| Datasheet | 电气特性、引脚定义 | ST官网搜索型号 |
| Reference Manual | 寄存器详解、外设原理 | ST官网搜索型号 |
| Programming Manual | ARM指令集、内核寄存器 | ST官网 |
| Application Notes | 应用笔记 | ST官网 -> Literature |

### 推荐开发板

| 开发板 | 芯片 | 特点 | 价格区间 |
|--------|------|------|----------|
| 正点原子战舰V2 | STM32F103ZET6 | 资源丰富，教程完善 | 150-200元 |
| 正点原子阿波罗 | STM32F429IGT6 | 高性能，带LCD | 200-300元 |
| 野火霸道 | STM32F103ZET6 | 教程详细 | 150-200元 |
| 野火挑战者 | STM32F407IGT6 | F4学习推荐 | 200-300元 |
| NUCLEO-F401RE | STM32F401RE | ST官方板 | 100元 |
| NUCLEO-H743ZI | STM32H743ZI | 旗舰学习板 | 200元 |
| 蓝丸板(BluePill) | STM32F103C8T6 | 极低成本 | 10-15元 |

### 推荐书籍

- 《STM32库开发实战指南》- 野火
- 《精通STM32F4》- 正点原子
- 《The Definitive Guide to ARM Cortex-M3/M4》- Joseph Yiu
- 《FreeRTOS源码详解与应用开发》- 野火

---

> **文档版本**：v1.0
>
> **最后更新**：2026年6月
>
> **适用芯片**：STM32F4系列为主，原理通用全系列
