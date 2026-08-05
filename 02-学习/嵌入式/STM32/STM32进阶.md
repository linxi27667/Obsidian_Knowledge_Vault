# STM32进阶

## 核心概念

- **DMA** - 直接内存访问
- **低功耗模式** - 睡眠/停止/待机
- **Bootloader** - 自举加载程序
- **Flash编程** - 片上Flash读写

---

## 一、DMA高级应用

### 1.1 DMA双缓冲

```c
// DMA双缓冲模式
#define BUF_SIZE 1024
uint32_t dma_buf[2][BUF_SIZE];
volatile int active_buf = 0;

void DMA1_Stream0_IRQHandler(void) {
    if (DMA1->LISR & DMA_LISR_TCIF0) {
        DMA1->LIFCR = DMA_LIFCR_CTCIF0;

        // 切换缓冲区
        active_buf = !active_buf;
        DMA1_Stream0->M0AR = (uint32_t)dma_buf[active_buf];

        // 处理另一个缓冲区
        process_data(dma_buf[!active_buf], BUF_SIZE);
    }
}

void adc_dma_init(void) {
    // ADC配置
    ADC1->CR2 |= ADC_CR2_DMA | ADC_CR2_CONT | ADC_CR2_ADON;

    // DMA配置
    DMA1_Stream0->PAR = (uint32_t)&ADC1->DR;
    DMA1_Stream0->M0AR = (uint32_t)dma_buf[0];
    DMA1_Stream0->NDTR = BUF_SIZE;
    DMA1_Stream0->CR = DMA_SxCR_MINC | DMA_SxCR_CIRC |
                       DMA_SxCR_DBM |  // 双缓冲模式
                       DMA_SxCR_TCIE |  // 传输完成中断
                       DMA_SxCR_MSIZE_1 | DMA_SxCR_PSIZE_1;

    DMA1_Stream0->CR |= DMA_SxCR_EN;
}
```

---

### 1.2 DMA+UART

```c
// UART DMA发送
uint8_t tx_buf[256];

void uart_dma_send(uint8_t *data, uint16_t len) {
    memcpy(tx_buf, data, len);

    DMA1_Stream3->PAR = (uint32_t)&USART2->DR;
    DMA1_Stream3->M0AR = (uint32_t)tx_buf;
    DMA1_Stream3->NDTR = len;
    DMA1_Stream3->CR |= DMA_SxCR_EN;

    USART2->CR3 |= USART_CR3_DMAT;  // 使能DMA发送
}

// UART DMA接收(空闲中断+DMA)
uint8_t rx_buf[256];
volatile uint16_t rx_len = 0;

void USART2_IRQHandler(void) {
    if (USART2->SR & USART_SR_IDLE) {
        USART2->SR;  // 清除IDLE标志
        USART2->DR;

        rx_len = 256 - DMA1_Stream5->NDTR;

        // 处理接收到的数据
        process_rx_data(rx_buf, rx_len);

        // 重新启动DMA接收
        DMA1_Stream5->CR &= ~DMA_SxCR_EN;
        DMA1_Stream5->NDTR = 256;
        DMA1_Stream5->CR |= DMA_SxCR_EN;
    }
}

void uart_dma_rx_init(void) {
    DMA1_Stream5->PAR = (uint32_t)&USART2->DR;
    DMA1_Stream5->M0AR = (uint32_t)rx_buf;
    DMA1_Stream5->NDTR = 256;
    DMA1_Stream5->CR = DMA_SxCR_MINC | DMA_SxCR_CIRC | DMA_SxCR_EN;

    USART2->CR3 |= USART_CR3_DMAR;
    USART2->CR1 |= USART_CR1_IDLEIE;  // 空闲中断
}
```

---

## 二、低功耗模式

### 2.1 STM32低功耗模式

| 模式 | 唤醒源 | 功耗 | 唤醒时间 |
|------|--------|------|----------|
| Sleep | 任意中断 | 中 | 0 |
| Stop | EXTI | 低 | μs级 |
| Standby | WKUP/RTC | 极低 | ms级 |

---

### 2.2 Stop模式

```c
void enter_stop_mode(void) {
    // 配置唤醒源(EXTI)
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    SYSCFG->EXTICR[0] = SYSCFG_EXTICR1_EXTI0_PA;  // PA0
    EXTI->IMR |= EXTI_IMR_MR0;
    EXTI->FTSR |= EXTI_FTSR_TR0;  // 下降沿

    // 进入Stop模式
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    PWR->CR |= PWR_CR_LPDS;  // 低功耗深度睡眠
    PWR->CR |= PWR_CR_CWUF;  // 清除唤醒标志

    __WFI();

    // 唤醒后恢复时钟
    SystemClock_Config();
}

void EXTI0_IRQHandler(void) {
    EXTI->PR = EXTI_PR_PR0;  // 清除中断标志
    // 唤醒处理
}
```

---

### 2.3 Standby模式

```c
void enter_standby_mode(void) {
    // 使能WKUP引脚(PA0)
    PWR->CSR |= PWR_CSR_EWUP;

    // 进入Standby模式
    PWR->CR |= PWR_CR_CWUF;
    PWR->CR |= PWR_CR_PDDS;  // 待机模式

    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    __WFI();

    // 这里不会执行，唤醒后从复位开始
}

// 检查唤醒原因
bool is_standby_wakeup(void) {
    if (PWR->CSR & PWR_CSR_SBF) {
        PWR->CR |= PWR_CR_CSBF;  // 清除标志
        return true;
    }
    return false;
}
```

---

### 2.4 低功耗设计技巧

```c
// GPIO低功耗配置
void gpio_low_power_init(void) {
    // 未使用的GPIO配置为模拟输入
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOBEN;

    // 配置为模拟输入(最低功耗)
    GPIOA->MODER = 0xFFFFFFFF;  // 所有引脚模拟模式
    GPIOB->MODER = 0xFFFFFFFF;

    // 关闭未使用外设时钟
    RCC->APB1ENR = 0;
    RCC->APB2ENR = 0;
}

// RTC唤醒
void rtc_wakeup_init(uint32_t seconds) {
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    PWR->CR |= PWR_CR_DBP;  // 允许RTC访问

    RCC->CSR |= RCC_CSR_LSION;
    while (!(RCC->CSR & RCC_CSR_LSIRDY));

    RTC->WPR = 0xCA;
    RTC->WPR = 0x53;

    RTC->CR &= ~RTC_CR_WUTE;
    while (!(RTC->ISR & RTC_ISR_WUTWF));

    RTC->WUTR = seconds * 32768 / 16;  // LSI约32kHz，分频16
    RTC->CR |= RTC_CR_WUTE | RTC_CR_WUTIE;

    EXTI->IMR |= EXTI_IMR_MR22;
    EXTI->RTSR |= EXTI_RTSR_TR22;
    RTC->WPR = 0xFF;
}
```

---

## 三、Flash编程

### 3.1 Flash读写

```c
// STM32F4 Flash写入
#define FLASH_SECTOR_7  ((uint32_t)0x08060000)

void flash_write(uint32_t addr, uint32_t *data, uint32_t len) {
    HAL_FLASH_Unlock();

    // 擦除扇区
    FLASH_EraseInitTypeDef erase;
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.Sector = FLASH_SECTOR_7;
    erase.NbSectors = 1;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    uint32_t error;
    HAL_FLASHEx_Erase(&erase, &error);

    // 写入数据
    for (uint32_t i = 0; i < len; i++) {
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr + i * 4, data[i]);
    }

    HAL_FLASH_Lock();
}

void flash_read(uint32_t addr, uint32_t *data, uint32_t len) {
    for (uint32_t i = 0; i < len; i++) {
        data[i] = *(volatile uint32_t *)(addr + i * 4);
    }
}
```

---

### 3.2 EEPROM模拟

```c
// 使用Flash模拟EEPROM
#define EEPROM_START_ADDR  0x08060000
#define EEPROM_SIZE        128  // 字节

void eeprom_write(uint16_t addr, uint8_t data) {
    uint32_t flash_addr = EEPROM_START_ADDR + addr;

    HAL_FLASH_Unlock();

    // 擦除(如果需要)
    if (addr % 4 == 0) {
        FLASH_EraseInitTypeDef erase;
        erase.TypeErase = FLASH_TYPEERASE_SECTORS;
        erase.Sector = 7;
        erase.NbSectors = 1;
        uint32_t error;
        HAL_FLASHEx_Erase(&erase, &error);
    }

    // 写入
    HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE, flash_addr, data);

    HAL_FLASH_Lock();
}

uint8_t eeprom_read(uint16_t addr) {
    return *(volatile uint8_t *)(EEPROM_START_ADDR + addr);
}
```

---

## 四、Bootloader

### 4.1 Bootloader架构

```
┌─────────────────────────────────┐
│          用户程序               │
│         (0x08010000)            │
├─────────────────────────────────┤
│          Bootloader             │
│         (0x08000000)            │
└─────────────────────────────────┘

Bootloader功能:
1. 检查更新标志
2. 接收新固件(UART/USB/CAN)
3. 写入Flash
4. 跳转到用户程序
```

---

### 4.2 Bootloader实现

```c
#define APP_START_ADDR  0x08010000
#define UPDATE_FLAG_ADDR 0x2000FFF0  // RAM末尾

typedef void (*pFunction)(void);

void jump_to_app(void) {
    uint32_t app_addr = APP_START_ADDR;

    // 检查APP地址是否有效
    if (((*(volatile uint32_t *)app_addr) & 0x2FF00000) == 0x20000000) {
        // 设置主栈指针
        __set_MSP(*(volatile uint32_t *)app_addr);

        // 获取复位处理函数地址
        pFunction app_entry = (pFunction)(*(volatile uint32_t *)(app_addr + 4));

        // 跳转
        app_entry();
    }
}

void bootloader_main(void) {
    // 检查更新标志
    uint32_t *update_flag = (uint32_t *)UPDATE_FLAG_ADDR;

    if (*update_flag == 0x12345678) {
        // 进入更新模式
        *update_flag = 0;
        firmware_update();
    } else {
        // 检查APP是否有效
        if (is_app_valid()) {
            jump_to_app();
        }
    }

    // 如果都没有，进入DFU模式
    enter_dfu_mode();
}

bool is_app_valid(void) {
    uint32_t sp = *(volatile uint32_t *)APP_START_ADDR;
    uint32_t pc = *(volatile uint32_t *)(APP_START_ADDR + 4);

    // 检查SP和PC是否在合理范围
    return (sp >= 0x20000000 && sp <= 0x20020000 &&
            pc >= APP_START_ADDR && pc <= 0x08100000);
}
```

---

### 4.3 串口升级

```c
// Ymodem接收
typedef struct {
    uint8_t header;      // 0x01
    uint8_t seq;         // 序号
    uint8_t seq_inv;     // 序号取反
    uint8_t data[128];   // 数据
    uint16_t crc;        // CRC16
} ymodem_packet_t;

void firmware_update(void) {
    uint32_t flash_addr = APP_START_ADDR;
    uint32_t total_size = 0;

    HAL_FLASH_Unlock();

    // 擦除APP区域
    for (int i = 1; i <= 7; i++) {
        FLASH_EraseInitTypeDef erase = {
            .TypeErase = FLASH_TYPEERASE_SECTORS,
            .Sector = i,
            .NbSectors = 1,
        };
        uint32_t error;
        HAL_FLASHEx_Erase(&erase, &error);
    }

    while (1) {
        ymodem_packet_t packet;
        if (ymodem_receive_packet(&packet) != 0) break;

        if (packet.seq == 0) {
            // 文件名包
            total_size = parse_file_size(packet.data);
            continue;
        }

        // 写入Flash
        for (int i = 0; i < 128; i += 4) {
            uint32_t word = *(uint32_t *)&packet.data[i];
            HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, flash_addr, word);
            flash_addr += 4;
        }

        // ACK
        uart_send_byte(ACK);

        if (flash_addr - APP_START_ADDR >= total_size) break;
    }

    HAL_FLASH_Lock();
}
```

---

## 五、外设高级应用

### 5.1 定时器编码器模式

```c
// 编码器接口
void encoder_init(void) {
    // TIM3编码器模式
    TIM3->SMCR = TIM_SMCR_SMS_0 | TIM_SMCR_SMS_1;  // 编码器模式3
    TIM3->CCMR1 = TIM_CCMR1_CC1S_0 | TIM_CCMR1_CC2S_0;  // IC1->TI1, IC2->TI2
    TIM3->CCER = 0;  // 不反相
    TIM3->ARR = 0xFFFF;
    TIM3->CR1 = TIM_CR1_CEN;
}

int16_t encoder_read(void) {
    return (int16_t)TIM3->CNT;
}

// 编码器速度计算
float encoder_speed(void) {
    static int16_t last_count = 0;
    static uint32_t last_time = 0;

    int16_t count = encoder_read();
    uint32_t time = HAL_GetTick();

    int16_t delta_count = count - last_count;
    uint32_t delta_time = time - last_time;

    float speed = (float)delta_count / (float)delta_time * 1000.0f;  // counts/s

    last_count = count;
    last_time = time;

    return speed;
}
```

---

### 5.2 SPI DMA传输

```c
// SPI DMA发送
uint8_t spi_tx_buf[256];

void spi_dma_send(uint8_t *data, uint16_t len) {
    memcpy(spi_tx_buf, data, len);

    DMA1_Stream4->PAR = (uint32_t)&SPI1->DR;
    DMA1_Stream4->M0AR = (uint32_t)spi_tx_buf;
    DMA1_Stream4->NDTR = len;
    DMA1_Stream4->CR |= DMA_SxCR_EN;

    SPI1->CR2 |= SPI_CR2_TXDMAEN;
}

// SPI DMA全双工
uint8_t spi_rx_buf[256];

void spi_dma_transfer(uint8_t *tx, uint8_t *rx, uint16_t len) {
    // TX DMA
    DMA1_Stream4->PAR = (uint32_t)&SPI1->DR;
    DMA1_Stream4->M0AR = (uint32_t)tx;
    DMA1_Stream4->NDTR = len;
    DMA1_Stream4->CR |= DMA_SxCR_EN;

    // RX DMA
    DMA1_Stream3->PAR = (uint32_t)&SPI1->DR;
    DMA1_Stream3->M0AR = (uint32_t)rx;
    DMA1_Stream3->NDTR = len;
    DMA1_Stream3->CR |= DMA_SxCR_EN;

    SPI1->CR2 |= SPI_CR2_TXDMAEN | SPI_CR2_RXDMAEN;

    // 等待完成
    while (DMA1_Stream4->NDTR > 0);
}
```

---

## 六、时钟配置

### 6.1 时钟树

```
HSE (8MHz)
    ↓
PLL (×168)
    ↓
SYSCLK (168MHz)
    ├── AHB Prescaler (/1) → HCLK (168MHz)
    │   ├── APB1 Prescaler (/4) → PCLK1 (42MHz)
    │   │   └── Timer ×2 → 84MHz
    │   └── APB2 Prescaler (/2) → PCLK2 (84MHz)
    │       └── Timer ×2 → 168MHz
    └── USB Prescaler → 48MHz
```

---

### 6.2 时钟配置代码

```c
void SystemClock_Config(void) {
    // 使能HSE
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));

    // 配置PLL
    RCC->PLLCFGR = RCC_PLLCFGR_PLLSRC_HSE |  // HSE作为PLL源
                    (4 << RCC_PLLCFGR_PLLM_Pos) |  // PLLM = 4
                    (168 << RCC_PLLCFGR_PLLN_Pos) | // PLLN = 168
                    (0 << RCC_PLLCFGR_PLLP_Pos);    // PLLP = 2

    // 使能PLL
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));

    // 配置Flash等待周期
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_PRFTEN |
                 FLASH_ACR_ICEN | FLASH_ACR_DCEN;

    // 配置总线分频
    RCC->CFGR = RCC_CFGR_HPRE_DIV1 |    // AHB = SYSCLK / 1
                RCC_CFGR_PPRE1_DIV4 |    // APB1 = AHB / 4
                RCC_CFGR_PPRE2_DIV2;     // APB2 = AHB / 2

    // 切换到PLL
    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

    // 更新SystemCoreClock
    SystemCoreClock = 168000000;
}
```

---

## 七、电源管理

### 7.1 电源域

| 域 | 电压 | 外设 |
|----|------|------|
| VDD | 1.8-3.6V | 数字IO |
| VDDA | 1.8-3.6V | ADC/DAC |
| VBAT | 1.65-3.6V | RTC/备份 |
| VDD_1 | 1.2V | 内核 |

---

### 7.2 电源配置

```c
void power_init(void) {
    // 使能PWR时钟
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;

    // 配置电压调节器
    PWR->CR |= PWR_CR_VOS;  // 高性能模式

    // 配置备份域
    PWR->CR |= PWR_CR_DBP;  // 允许访问备份寄存器
}
```

---

## 附录：STM32时钟速查

| 时钟 | 频率 | 用途 |
|------|------|------|
| HSI | 16MHz | 内部RC |
| HSE | 8MHz | 外部晶振 |
| LSI | 32kHz | 内部低速 |
| LSE | 32.768kHz | 外部低速 |
| PLL | 最高168MHz | 系统时钟 |

---

## 相关链接

- [[STM32基础]] - 基础入门
- [[GCC与链接脚本]] - 编译工具
- [[调试技术详解]] - 调试方法
