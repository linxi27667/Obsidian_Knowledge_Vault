# I2C通信 （同步串行 半双工 两线制 地址寻址）

## 核心概念

### 基本原理
- ==同步通信== - SCL时钟线由主机产生
- ==半双工== - 数据线SDA分时复用
- ==两线制== - SCL时钟、SDA数据
- ==地址寻址== - 7位或10位设备地址

### 信号线定义
| 信号 | 方向 | 说明 |
|------|------|------|
| SCL | 主→从 | 时钟线（开漏输出） |
| SDA | 双向 | 数据线（开漏输出） |

### 电气特性
- ==开漏输出== - 需外部上拉电阻（通常4.7K）
- ==标准模式== - 100kbps
- ==快速模式== - 400kbps
- ==高速模式== - 3.4Mbps

---

## 一、I2C协议时序

### 1.1 基本信号

```
起始信号（START）：
SCL: ────┐__________
SDA: ────┐__________
      ↓
      SDA在SCL高电平期间下降

停止信号（STOP）：
SCL: __________┌────
SDA: ________┌────
            ↑
            SDA在SCL高电平期间上升

数据传输：
SCL: _┌─_┌─_┌─_┌─
SDA: 数据在SCL低电平期间变化
     在SCL高电平期间保持稳定（采样）

应答信号（ACK/NACK）：
每传输8位数据后，接收方发送ACK（SDA低）或NACK（SDA高）
```

### 1.2 数据帧结构

```
┌────┬───────┬────┬───────┬────┬────┐
│START│地址+RW│ACK │数据   │ACK │STOP│
│    │7bit   │    │8bit   │    │    │
└────┴───────┴────┴───────┴────┴────┘

地址帧：7位地址 + 1位读写标志
- RW=0: 写操作
- RW=1: 读操作
```

---

## 二、STM32 I2C初始化

### 2.1 I2C结构体配置

```c
I2C_HandleTypeDef hi2c1;

void MX_I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.ClockSpeed = 100000;          // 100kHz标准模式
    hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_16_9;  // 快速模式占空比
    hi2c1.Init.OwnAddress1 = 0;               // 主机模式下不用
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    
    if (HAL_I2C_Init(&hi2c1) != HAL_OK)
    {
        Error_Handler();
    }
}
```

### 2.2 GPIO配置

```c
void HAL_I2C_MspInit(I2C_HandleTypeDef* hi2c)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    
    if(hi2c->Instance == I2C1)
    {
        __HAL_RCC_I2C1_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();
        
        // PB6: SCL  PB7: SDA
        GPIO_InitStruct.Pin = GPIO_PIN_6 | GPIO_PIN_7;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;    // 开漏输出
        GPIO_InitStruct.Pull = GPIO_PULLUP;        // 上拉（外部也需要）
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF4_I2C1;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    }
}
```

### 2.3 时钟速度配置

```c
// 常用时钟速度
hi2c1.Init.ClockSpeed = 100000;   // 100kHz 标准模式
hi2c1.Init.ClockSpeed = 400000;   // 400kHz 快速模式

// STM32F103 I2C1时钟 = PCLK1 = 36MHz
// 时钟速度通过CR寄存器CCR和TRISE配置
```

---

## 三、主机发送与接收

### 3.1 阻塞式发送

- `HAL_I2C_Master_Transmit`：发送数据到从机
- 从机地址需**左移1位**（HAL库自动处理读写位）
- 超时参数控制最大等待时间

### 3.2 阻塞式接收

- `HAL_I2C_Master_Receive`：从从机读取数据
- 地址同样左移1位

### 3.3 中断方式

- `HAL_I2C_Master_Transmit_IT` / `HAL_I2C_Master_Receive_IT`
- 完成回调：`HAL_I2C_MasterTxCpltCallback` / `HAL_I2C_MasterRxCpltCallback`

### 3.4 DMA方式

- `HAL_I2C_Master_Transmit_DMA` / `HAL_I2C_Master_Receive_DMA`
- 适用于大数据量传输，不占用CPU

---

## 四、寄存器读写操作

### 4.1 写寄存器流程

1. 发送START信号
2. 发送从机地址 + 写标志（0）
3. 发送寄存器地址
4. 发送寄存器数据
5. 发送STOP信号

### 4.2 读寄存器流程

1. 发送START信号
2. 发送从机地址 + 写标志（0）
3. 发送寄存器地址（指定要读的寄存器）
4. 发送RESTART信号（重复起始）
5. 发送从机地址 + 读标志（1）
6. 接收数据
7. 发送NACK + STOP信号

### 4.2 读寄存器

```c
// 读单个寄存器
uint8_t I2C_Read_Register(uint8_t dev_addr, uint8_t reg)
{
    uint8_t value;
    
    // 发送寄存器地址
    HAL_I2C_Master_Transmit(&hi2c1, dev_addr << 1, &reg, 1, 1000);
    
    // 接收数据
    HAL_I2C_Master_Receive(&hi2c1, dev_addr << 1, &value, 1, 1000);
    
    return value;
}

// 读多个寄存器（使用HAL封装函数）
void I2C_Read_Registers(uint8_t dev_addr, uint8_t start_reg, 
                         uint8_t *values, uint16_t count)
{
    HAL_I2C_Mem_Read(&hi2c1, dev_addr << 1, start_reg, 
                     I2C_MEMADD_SIZE_8BIT, values, count, 1000);
}

// 使用HAL封装写寄存器
void I2C_Write_Register_HAL(uint8_t dev_addr, uint8_t reg, uint8_t value)
{
    HAL_I2C_Mem_Write(&hi2c1, dev_addr << 1, reg, 
                      I2C_MEMADD_SIZE_8BIT, &value, 1, 1000);
}
```

---

## 五、设备扫描与检测

### 5.1 I2C总线设备扫描

```c
void I2C_Scan_Bus(void)
{
    printf("I2C Bus Scan:\n");
    
    for(uint8_t addr = 1; addr < 127; addr++)
    {
        // 尝试检测设备（发送空数据）
        if(HAL_I2C_IsDeviceReady(&hi2c1, addr << 1, 3, 100) == HAL_OK)
        {
            printf("Device found at address 0x%02X\n", addr);
        }
    }
    
    printf("Scan complete.\n");
}

// 检测特定设备是否存在
uint8_t I2C_Device_Present(uint8_t dev_addr)
{
    return (HAL_I2C_IsDeviceReady(&hi2c1, dev_addr << 1, 3, 100) == HAL_OK);
}
```

---

## 六、典型应用示例

### 6.1 EEPROM读写（AT24Cxx）

```c
#define EEPROM_ADDR  0x50  // AT24C02地址

// 写入单字节到指定地址
void EEPROM_WriteByte(uint16_t addr, uint8_t data)
{
    uint8_t buffer[3];
    buffer[0] = (addr >> 8) & 0xFF;  // 高地址（AT24C16以上）
    buffer[1] = addr & 0xFF;         // 低地址
    buffer[2] = data;
    
    HAL_I2C_Master_Transmit(&hi2c1, EEPROM_ADDR << 1, buffer, 3, 1000);
    
    // 等待写入完成（EEPROM需要时间）
    HAL_Delay(5);
}

// 读取单字节
uint8_t EEPROM_ReadByte(uint16_t addr)
{
    uint8_t data;
    uint8_t addr_buf[2];
    addr_buf[0] = (addr >> 8) & 0xFF;
    addr_buf[1] = addr & 0xFF;
    
    // 发送地址
    HAL_I2C_Master_Transmit(&hi2c1, EEPROM_ADDR << 1, addr_buf, 2, 1000);
    
    // 接收数据
    HAL_I2C_Master_Receive(&hi2c1, EEPROM_ADDR << 1, &data, 1, 1000);
    
    return data;
}

// 页写入（AT24C02每页8字节）
void EEPROM_Page_Write(uint16_t addr, uint8_t *data, uint8_t len)
{
    uint8_t buffer[10];  // 地址 + 最多8字节
    buffer[0] = (addr >> 8) & 0xFF;
    buffer[1] = addr & 0xFF;
    
    for(uint8_t i = 0; i < len; i++)
    {
        buffer[i + 2] = data[i];
    }
    
    HAL_I2C_Master_Transmit(&hi2c1, EEPROM_ADDR << 1, buffer, len + 2, 1000);
    HAL_Delay(5);
}

// 连续读取
void EEPROM_Read(uint16_t addr, uint8_t *data, uint16_t len)
{
    HAL_I2C_Mem_Read(&hi2c1, EEPROM_ADDR << 1, addr, 
                     I2C_MEMADD_SIZE_16BIT, data, len, 1000);
}
```

### 6.2 温度传感器（LM75）

```c
#define LM75_ADDR  0x48

// 读取温度（16位，0.5°C分辨率）
float LM75_Read_Temperature(void)
{
    uint8_t buffer[2];
    HAL_I2C_Mem_Read(&hi2c1, LM75_ADDR << 1, 0x00, 
                     I2C_MEMADD_SIZE_8BIT, buffer, 2, 1000);
    
    // 温度值在高9位
    int16_t temp_raw = (buffer[0] << 8 | buffer[1]) >> 5;
    
    // 转换为实际温度
    return temp_raw * 0.125f;
}
```

### 6.3 RTC时钟（DS3231）

```c
#define DS3231_ADDR  0x68

// 时间寄存器地址
#define DS3231_REG_SECONDS  0x00
#define DS3231_REG_MINUTES  0x01
#define DS3231_REG_HOURS    0x02

// BCD转换
uint8_t BCD2DEC(uint8_t bcd)
{
    return (bcd >> 4) * 10 + (bcd & 0x0F);
}

uint8_t DEC2BCD(uint8_t dec)
{
    return ((dec / 10) << 4) | (dec % 10);
}

// 读取时间
void DS3231_Read_Time(uint8_t *hour, uint8_t *min, uint8_t *sec)
{
    uint8_t buffer[3];
    HAL_I2C_Mem_Read(&hi2c1, DS3231_ADDR << 1, DS3231_REG_SECONDS,
                     I2C_MEMADD_SIZE_8BIT, buffer, 3, 1000);
    
    *sec = BCD2DEC(buffer[0]);
    *min = BCD2DEC(buffer[1]);
    *hour = BCD2DEC(buffer[2] & 0x3F);  // 24小时模式
}

// 设置时间
void DS3231_Set_Time(uint8_t hour, uint8_t min, uint8_t sec)
{
    uint8_t buffer[3];
    buffer[0] = DEC2BCD(sec);
    buffer[1] = DEC2BCD(min);
    buffer[2] = DEC2BCD(hour);
    
    HAL_I2C_Mem_Write(&hi2c1, DS3231_ADDR << 1, DS3231_REG_SECONDS,
                      I2C_MEMADD_SIZE_8BIT, buffer, 3, 1000);
}
```

---

## 七、常见问题排查

### 7.1 总线挂死

```c
// I2C总线挂死检测与恢复
uint8_t I2C_Check_Bus_State(void)
{
    // 检查SDA和SCL状态
    GPIO_PinState sda = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_7);
    GPIO_PinState scl = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_6);
    
    // 如果SDA为低电平（总线被占用）
    if(sda == GPIO_PIN_RESET)
    {
        return 1;  // 总线忙
    }
    
    return 0;  // 总线空闲
}

// 总线恢复（发送9个时钟脉冲）
void I2C_Bus_Reset(void)
{
    // 临时将GPIO设置为推挽输出
    GPIO_InitTypeDef GPIO_InitStruct;
    GPIO_InitStruct.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    
    // 发送9个时钟脉冲
    for(uint8_t i = 0; i < 9; i++)
    {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_RESET);
        HAL_Delay(1);
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);
        HAL_Delay(1);
        
        // 如果SDA变高，发送STOP
        if(HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_7) == GPIO_PIN_SET)
        {
            // STOP信号
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_7, GPIO_PIN_RESET);
            HAL_Delay(1);
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);
            HAL_Delay(1);
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_7, GPIO_PIN_SET);
            break;
        }
    }
    
    // 重新配置为开漏模式
    GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}
```

### 7.2 上拉电阻选择

```c
// 上拉电阻计算
/*
公式：Rp = (VDD - Vol_min) / Iol

典型值：
- 100kHz：4.7kΩ ~ 10kΩ
- 400kHz：1kΩ ~ 2.2kΩ

考虑因素：
1. 总线电容（不能太大）
2. 设备数量（上拉电流总和）
3. 供电电压
*/
```

---

## 附录：I2C常用API速查表

### 主机发送函数
| 函数 | 说明 |
|------|------|
| `HAL_I2C_Master_Transmit()` | 阻塞发送 |
| `HAL_I2C_Master_Transmit_IT()` | 中断发送 |
| `HAL_I2C_Master_Transmit_DMA()` | DMA发送 |

### 主机接收函数
| 函数 | 说明 |
|------|------|
| `HAL_I2C_Master_Receive()` | 阻塞接收 |
| `HAL_I2C_Master_Receive_IT()` | 中断接收 |
| `HAL_I2C_Master_Receive_DMA()` | DMA接收 |

### 内存读写函数
| 函数 | 说明 |
|------|------|
| `HAL_I2C_Mem_Write()` | 写寄存器/内存 |
| `HAL_I2C_Mem_Read()` | 读寄存器/内存 |
| `HAL_I2C_Mem_Write_IT()` | 中断写内存 |
| `HAL_I2C_Mem_Read_IT()` | 中断读内存 |

### 设备检测函数
| 函数 | 说明 |
|------|------|
| `HAL_I2C_IsDeviceReady()` | 检测设备是否就绪 |

### 回调函数
| 函数 | 说明 |
|------|------|
| `HAL_I2C_MasterTxCpltCallback()` | 主机发送完成回调 |
| `HAL_I2C_MasterRxCpltCallback()` | 主机接收完成回调 |
| `HAL_I2C_MemTxCpltCallback()` | 内存写完成回调 |
| `HAL_I2C_MemRxCpltCallback()` | 内存读完成回调 |
| `HAL_I2C_ErrorCallback()` | 错误回调 |

### 常用设备地址
| 设备 | 地址 | 说明 |
|------|------|------|
| AT24C02 EEPROM | 0x50 | 存储 |
| DS3231 RTC | 0x68 | 时钟 |
| LM75 温度 | 0x48/0x49 | 温度传感器 |
| MPU6050 IMU | 0x68/0x69 | 六轴传感器 |
| OLED SSD1306 | 0x3C/0x3D | 显示屏 |
| BH1750 光照 | 0x23 | 光照传感器 |

---