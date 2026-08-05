# 外部Flash(W25Q)与SPI总线 （STM32F407 三层架构 + 双扇区持久化方案）

> 基于 `f407vet6` 项目的实际实现，从硬件协议到应用层完整梳理 SPI 总线与 NOR Flash 的知识体系。

## 核心概念

### SPI 总线
- ==四线制全双工== - SCK(时钟)、MOSI(主出从入)、MISO(主入从出)、CS(片选)
- ==一主多从== - 每个从设备独立 CS 引脚，SCK/MOSI/MISO 共享
- ==CPOL/CPHA 决定模式== - CPOL 决定时钟空闲电平，CPHA 决定数据采样沿

### NOR Flash (W25Qxx)
- ==扇区擦除(4KB)是写入前提== - Flash 不能位覆盖，只能先擦除(全变1)再编程(写0)
- ==页编程(256B)的边界限制== - 编程不能跨页，长度不超过 256 字节
- ==擦写寿命 10 万次== - 扇区擦除有寿命限制，项目用双扇区轮转延长寿命

### 项目架构
- ==三层分离== - APP(存储调度) → BSP(SPI命令) → Driver(硬件调试)
- ==双扇区轮转== - Slot A(0x0000) / Slot B(0x1000)，Load 选最新，Save 写最旧

---

## 一、SPI 总线协议详解

### 1.1 物理层与四线制

SPI（Serial Peripheral Interface）是一种 ==同步、全双工、主从== 的串行通信协议。

| 信号线 | 方向 | 说明 |
|--------|------|------|
| SCK | 主→从 | 时钟信号，由 Master 产生 |
| MOSI | 主→从 | Master Out Slave In |
| MISO | 从→主 | Master In Slave Out |
| CS | 主→从 | 片选，低电平有效，选中从设备 |

**通信原理**: Master 在 SCK 每个时钟周期同时发送和接收 1 bit。发送数据从 MOSI 线输出，接收数据从 MISO 线采样。

### 1.2 CPOL / CPHA — 时钟极性与相位

SPI 有 4 种工作模式，由 CPOL (Clock Polarity) 和 CPHA (Clock Phase) 决定：

| 模式 | CPOL | CPHA | 空闲时钟 | 采样沿 | 发送沿 |
|------|------|------|----------|--------|--------|
| 0 | 0 | 0 | 低电平 | 上升沿 | 下降沿 |
| 1 | 0 | 1 | 低电平 | 下降沿 | 上升沿 |
| 2 | 1 | 0 | 高电平 | 上升沿 | 下降沿 |
| 3 | 1 | 1 | 高电平 | 下降沿 | 上升沿 |

> [!NOTE] W25Qxx 支持模式 0 和模式 3。本项目中 `HAL_SPI_Init` 使用 CubeMX 默认配置（通常为模式 0），确保与 W25Q 匹配即可。

### 1.3 全双工通信时序

```
     ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐
SCK  │   │   │   │   │   │   │   │   │   │   │   │
   ──┘   └───┘   └───┘   └───┘   └───┘   └───┘   └──
     ┌───┬───┬───┬───┬───┬───┬───┬───┐
MOSI │   │ b7│ b6│ b5│ b4│ b3│ b2│ b1│ b0│
     └───┴───┴───┴───┴───┴───┴───┴───┘
     ┌───┬───┬───┬───┬───┬───┬───┬───┐
MISO │   │ b7│ b6│ b5│ b4│ b3│ b2│ b1│ b0│
     └───┴───┴───┴───┴───┴───┴───┴───┘
CS   ──────────────────────────────────────
```

SPI 的"全双工"指每发送 1 字节的同时必定收到 1 字节。这就是为什么 ==读操作也需要发送数据来产生时钟==。

---

## 二、STM32 HAL 的 SPI 操作

### 2.1 三个核心 API

| 函数 | 用途 | TX 数据 | RX 数据 |
|------|------|---------|---------|
| `HAL_SPI_Transmit()` | 只发送 | 提供 | NULL |
| `HAL_SPI_Receive()` | 只接收 | 内部发0xFF | 提供 |
| `HAL_SPI_TransmitReceive()` | 同时收发 | 提供 | 提供 |

### 2.2 项目中的硬件绑定（app_spi.c）

```c
// SPI 数据发送
static uint8_t HW_SPI_Transmit(void *hspi, const uint8_t *tx_data, uint16_t size, uint32_t timeout)
{
    SPI_HandleTypeDef *handle = (SPI_HandleTypeDef *)hspi;
    // 恢复卡住的 SPI 句柄状态（防故障）
    if (handle->State != HAL_SPI_STATE_READY)
    {
        handle->State = HAL_SPI_STATE_READY;
        handle->ErrorCode = HAL_SPI_ERROR_NONE;
    }
    return HAL_SPI_Transmit(handle, (uint8_t *)tx_data, size, timeout) == HAL_OK ? 0 : 1;
}

// SPI 数据收发（tx_data==NULL 时为纯接收）
static uint8_t HW_SPI_Transmit_Receive(void *hspi, const uint8_t *tx_data, uint8_t *rx_data, 
                                        uint16_t size, uint32_t timeout)
{
    SPI_HandleTypeDef *handle = (SPI_HandleTypeDef *)hspi;
    if (handle->State != HAL_SPI_STATE_READY)
    {
        handle->State = HAL_SPI_STATE_READY;
        handle->ErrorCode = HAL_SPI_ERROR_NONE;
    }
    if (!tx_data)  // 纯接收：HAL_SPI_Receive 内部自动发 0xFF 做时钟
    {
        return HAL_SPI_Receive(handle, rx_data, size, timeout) == HAL_OK ? 0 : 1;
    }
    return HAL_SPI_TransmitReceive(handle, (uint8_t *)tx_data, rx_data, size, timeout) == HAL_OK ? 0 : 1;
}
```

**关键知识点**:

- SPI 是全双工的，=="读"操作也必须发送数据来产生 SCK 时钟==。接收时发送 0xFF dummy 字节是标准做法。
- HAL 句柄状态恢复：当 SPI 通信异常时，HAL 会将 `State` 设为非 `READY` 状态。手动恢复可以防止错误"卡死"后续通信。
- `HAL_SPI_TransmitReceive` 的 TX 缓冲区必须 >= `size` 字节，不能只传 1 字节的 dummy。

### 2.3 SPI 句柄卡死恢复的原因

```c
if (handle->State != HAL_SPI_STATE_READY)
{
    handle->State = HAL_SPI_STATE_READY;
    handle->ErrorCode = HAL_SPI_ERROR_NONE;
}
```

**触发场景**: 上一次 SPI 通信超时或出错后，HAL 将 State 设为 `HAL_SPI_STATE_BUSY` 或 `HAL_SPI_STATE_ERROR`，导致后续所有 HAL 调用直接返回 `HAL_BUSY`。手动恢复是嵌入式项目中常见的防故障模式。

---

## 三、项目中 SPI 总线抽象层设计

### 3.1 结构体封装（bsp_spi.h）

```c
// 抽象 GPIO 泛型结构体
typedef struct
{
    void *port;
    uint16_t pin;
} spi_gpio_t;

// SPI 总线对象结构体
typedef struct spi_bus_dev
{
    void *handle;                           // SPI 外设句柄（STM32 下为 SPI_HandleTypeDef *）
    spi_gpio_t cs;                          // 片选引脚

    // 硬件底层操作方法指针（函数指针封装，便于替换硬件平台）
    void    (*Init)(void);
    void    (*CS_Write)(void *port, uint16_t pin, uint8_t level);
    uint8_t (*Transmit)(void *hspi, const uint8_t *tx_data, uint16_t size, uint32_t timeout);
    uint8_t (*Transmit_Receive)(void *hspi, const uint8_t *tx_data, uint8_t *rx_data, 
                                uint16_t size, uint32_t timeout);
} spi_bus_t;
```

### 3.2 函数指针的意义

| 设计考量 | 说明 |
|----------|------|
| ==解耦硬件== | BSP 层通过函数指针调用 SPI 操作，不直接依赖 HAL |
| ==便于移植== | 换平台只需替换 app_spi.c 中的实现函数，BSP 层代码不变 |
| ==可测试== | 可以注入 mock 函数进行单元测试 |

### 3.3 实例化（app_spi.c）

```c
spi_bus_t SPI_Bus = {
    .handle = &hspi1,
    .cs     = {SPI_CS_PORT, SPI_CS_PIN},
    .Init             = HW_SPI_Init,
    .CS_Write         = HW_CS_Write,
    .Transmit         = HW_SPI_Transmit,
    .Transmit_Receive = HW_SPI_Transmit_Receive
};
```

### 3.4 CS 控制实现

```c
void SPI_Bus_Select(spi_bus_t *bus)
{
    bus->CS_Write(bus->cs.port, bus->cs.pin, 0);  // 拉低 CS
}

void SPI_Bus_Deselect(spi_bus_t *bus)
{
    bus->CS_Write(bus->cs.port, bus->cs.pin, 1);  // 拉高 CS
}
```

### 3.5 W25Q 设备对象

```c
typedef struct w25q_dev
{
    spi_bus_t *bus;   // 指向 SPI 总线对象的指针
} w25q_t;

#define W25Q_OK     0    // 操作成功
#define W25Q_ERR    1    // 操作失败
```

| API | 说明 |
|-----|------|
| `W25Q_Init_Device()` | 初始化设备，验证通信 |
| `W25Q_Read_JEDEC_ID()` | 读取 JEDEC ID 识别芯片 |
| `W25Q_Read_Buffer()` | 读取数据块 |
| `W25Q_Sector_Erase()` | 扇区擦除（4KB） |
| `W25Q_Page_Program()` | 页编程（≤256字节） |
| `W25Q_Write_MultiPage()` | 多页连续写入 |

---

## 四、NOR Flash 基础与 W25Qxx 命令集

### 4.1 Flash 存储原理

NOR Flash 的核心特性：

==写入只能将 1 变为 0，擦除将整个扇区恢复为全 1 (0xFF)==。因此：

1. **写前必须擦除** — 不能像 RAM 那样直接覆盖旧数据
2. **以扇区为擦除单位** — W25Qxx 最小擦除单位是 4KB
3. **以页为编程单位** — 单次最多写 256 字节，且不能跨页

### 4.2 W25Qxx 命令集

| 命令 | 字节码 | 功能 |
|------|--------|------|
| `W25Q_CMD_READ_DATA` | `0x03` | 读数据，发送 24 位地址后接收数据 |
| `W25Q_CMD_PAGE_PROGRAM` | `0x02` | 页编程，发送 24 位地址 + 数据 |
| `W25Q_CMD_SECTOR_ERASE` | `0x20` | 扇区擦除，发送 24 位地址（4KB 对齐） |
| `W25Q_CMD_WRITE_ENABLE` | `0x06` | 写使能，擦除/编程前必须先调用 |
| `W25Q_CMD_STATUS_REG` | `0x05` | 读状态寄存器，bit0=1 表示忙 |
| `W25Q_CMD_READ_JEDEC_ID` | `0x9F` | 读 JEDEC ID（3 字节：厂商+容量+版本） |
| `W25Q_CMD_CHIP_ERASE` | `0xC7` | 整片擦除 |

### 4.3 命令实现代码

```c
// ==== 读 JEDEC ID ====
uint32_t W25Q_Read_JEDEC_ID(w25q_t *flash)
{
    spi_bus_t *bus = flash->bus;
    uint8_t tx[4] = {W25Q_CMD_READ_JEDEC_ID, 0xFF, 0xFF, 0xFF};
    uint8_t rx[4];
    SPI_Bus_Select(bus);
    bus->Transmit_Receive(bus->handle, tx, rx, 4, 100);
    SPI_Bus_Deselect(bus);
    return (uint32_t)(rx[1] << 16) | (uint32_t)(rx[2] << 8) | rx[3];
}

// ==== 读数据块 ====
uint8_t W25Q_Read_Buffer(w25q_t *flash, uint32_t addr, uint8_t *buf, uint16_t len)
{
    spi_bus_t *bus = flash->bus;
    uint8_t cmd[4] = {W25Q_CMD_READ_DATA, 
                       (addr >> 16) & 0xFF, 
                       (addr >> 8) & 0xFF, 
                       addr & 0xFF};

    SPI_Bus_Select(bus);
    bus->Transmit(bus->handle, cmd, 4, 100);           // 发送命令+地址
    bus->Transmit_Receive(bus->handle, NULL, buf, len, 1000);  // 接收数据
    SPI_Bus_Deselect(bus);
    return W25Q_OK;
}

// ==== 扇区擦除 ====
uint8_t W25Q_Sector_Erase(w25q_t *flash, uint32_t addr)
{
    if (addr % 4096 != 0) return W25Q_ERR;  // 必须4KB对齐

    uint8_t cmd[4] = {W25Q_CMD_SECTOR_ERASE,
                       (addr >> 16) & 0xFF,
                       (addr >> 8) & 0xFF,
                       addr & 0xFF};

    W25Q_Write_Enable(flash);
    SPI_Bus_Select(bus);
    bus->Transmit(bus->handle, cmd, 4, 100);
    SPI_Bus_Deselect(bus);
    return W25Q_Wait_Busy(flash);
}

// ==== 页编程 ====
uint8_t W25Q_Page_Program(w25q_t *flash, uint32_t addr, const uint8_t *data, uint16_t len)
{
    if (len == 0 || len > 256) return W25Q_ERR;
    if (addr + len > (addr & ~0xFF) + 256) return W25Q_ERR;  // 不能跨页

    uint8_t cmd[4] = {W25Q_CMD_PAGE_PROGRAM,
                       (addr >> 16) & 0xFF,
                       (addr >> 8) & 0xFF,
                       addr & 0xFF};

    W25Q_Write_Enable(flash);
    SPI_Bus_Select(bus);
    bus->Transmit(bus->handle, cmd, 4, 100);
    bus->Transmit(bus->handle, data, len, 1000);
    SPI_Bus_Deselect(bus);
    return W25Q_Wait_Busy(flash);
}
```

### 4.4 写使能与忙检查

```c
static uint8_t W25Q_Write_Enable(w25q_t *flash)
{
    W25Q_Wait_Busy(flash);          // 先等上次操作完成
    uint8_t cmd = W25Q_CMD_WRITE_ENABLE;
    SPI_Bus_Select(bus);
    bus->Transmit(bus->handle, &cmd, 1, 100);
    SPI_Bus_Deselect(bus);
    return W25Q_OK;
}

// 忙检查：轮询状态寄存器的 BUSY 位
static uint8_t W25Q_Wait_Busy(w25q_t *flash)
{
    uint8_t tx[2] = {W25Q_CMD_STATUS_REG, 0xFF};
    uint8_t rx[2];
    uint32_t timeout = 100000;
    while (timeout--)
    {
        SPI_Bus_Select(bus);
        bus->Transmit_Receive(bus->handle, tx, rx, 2, 100);
        SPI_Bus_Deselect(bus);
        if ((rx[1] & 0x01) == 0) return W25Q_OK;  // bit0=0 表示空闲
    }
    return W25Q_ERR;  // 超时
}
```

**操作流程图**:
```
写操作流程:
  Write Enable (0x06) → [擦除/编程命令+地址+数据] → Wait Busy (轮询0x05)

读操作流程:
  Read Command (0x03) + 24-bit Address → 读取数据字节...
```

---

## 五、项目中的三层架构

### 5.1 层次关系

```
┌─────────────────────────────────────────────────────────┐
│  APP 层 (app_w25qxx.c)                                  │
│  ┌─────────────────────────────────────────────────────┐│
│  │  • 存储调度：Load / Save / CRC 校验                  ││
│  │  • 双扇区仲裁：选最新的加载，写最旧的备份             ││
│  │  • 数据校验：magic + CRC 双重验证                   ││
│  └─────────────────────────────────────────────────────┘│
                           ↓
│  BSP 层 (bsp_w25qxx.c + bsp_spi.c)                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │  • W25Q 命令集：Read/Erase/Program/WaitBusy         ││
│  │  • SPI 总线操作：Select/Deselect                    ││
│  └─────────────────────────────────────────────────────┘│
                           ↓
│  APP 层 (app_spi.c — 硬件绑定)                           │
│  ┌─────────────────────────────────────────────────────┐│
│  │  • HAL 驱动：hspi1 + GPIOA.4 (CS)                   ││
│  │  • 函数指针实现：Transmit / Transmit_Receive        ││
│  └─────────────────────────────────────────────────────┘│
                           ↓
│  Driver 层 (dri_debug.c — 调试任务)                      │
│  ┌─────────────────────────────────────────────────────┐│
│  │  • FreeRTOS Task：LED闪烁 + 计数存储                ││
│  │  • 持久化入口：每次闪烁调用 Storage_Save()          ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 5.2 各层职责与依赖

| 层 | 文件 | 职责 | 依赖 |
|----|------|------|------|
| **Driver** | `dri_debug.c` | 业务调试任务，调用 APP 层 API | APP 层 |
| **APP** | `app_w25qxx.c` | 存储调度、CRC校验、双扇区逻辑 | BSP 层 SPI 命令 |
| **BSP** | `bsp_w25qxx.c` | W25Q 命令层（读/写/擦除/忙检查） | BSP 层 SPI 总线 |
| **BSP** | `bsp_spi.c` | SPI 总线操作（Select/Deselect） | APP 层 SPI 绑定 |
| **APP** | `app_spi.c` | HAL 硬件绑定、函数指针实现 | CubeMX HAL 库 |

---

## 六、双扇区轮转持久化方案

### 6.1 存储数据结构

```c
typedef struct
{
    uint32_t magic;          // 魔数 0x53544F52 ("STOR")
    uint32_t debug_counter;  // 持久化的计数值
    uint32_t crc;            // 校验和 = magic ^ debug_counter
} w25q_storage_t;            // 共 12 字节
```

### 6.2 扇区布局

| Slot | 地址 | 用途 |
|------|------|------|
| Slot A | `0x00000000` (Sector 0, 4KB) | 数据存储位 A |
| Slot B | `0x00001000` (Sector 1, 4KB) | 数据存储位 B |

### 6.3 Load 逻辑

```c
void App_W25Qxx_Storage_Load(void)
{
    w25q_storage_t slot_a, slot_b;
    uint8_t a_ok = storage_read_slot(&slot_a, W25Q_SLOT_A_ADDR);
    uint8_t b_ok = storage_read_slot(&slot_b, W25Q_SLOT_B_ADDR);

    if (a_ok == W25Q_OK && b_ok == W25Q_OK)
    {
        // 两个都有效 → 选 counter 更大的（最新的）
        if (slot_b.debug_counter > slot_a.debug_counter)
            g_w25q_storage = slot_b;
        else
            g_w25q_storage = slot_a;
    }
    else if (a_ok == W25Q_OK)
        g_w25q_storage = slot_a;  // 只有 A 有效
    else if (b_ok == W25Q_OK)
        g_w25q_storage = slot_b;  // 只有 B 有效
    else
    {
        // 都无效 → 初始化默认值
        g_w25q_storage.magic = W25Q_STORAGE_MAGIC;
        g_w25q_storage.debug_counter = 0;
        g_w25q_storage.crc = storage_crc(&g_w25q_storage);
    }
}
```

### 6.4 Save 逻辑

```c
uint8_t App_W25Qxx_Storage_Save(void)
{
    storage_set_crc(&g_w25q_storage);  // 1. 更新 CRC

    // 2. 读两个 slot 状态，决定写入目标
    w25q_storage_t slot_a, slot_b;
    uint8_t a_ok = storage_read_slot(&slot_a, W25Q_SLOT_A_ADDR);
    uint8_t b_ok = storage_read_slot(&slot_b, W25Q_SLOT_B_ADDR);

    uint32_t target_addr;
    if (a_ok != W25Q_OK && b_ok != W25Q_OK)
        target_addr = W25Q_SLOT_A_ADDR;               // 都无效 → 写 A
    else if (a_ok != W25Q_OK)
        target_addr = W25Q_SLOT_A_ADDR;               // A 无效 → 覆盖 A
    else if (b_ok != W25Q_OK)
        target_addr = W25Q_SLOT_B_ADDR;               // B 无效 → 覆盖 B
    else if (slot_a.debug_counter <= slot_b.debug_counter)
        target_addr = W25Q_SLOT_A_ADDR;               // 写 counter 更小的
    else
        target_addr = W25Q_SLOT_B_ADDR;

    // 3. Sector Erase → 4. Page Program
    W25Q_Sector_Erase(&W25Q_Flash, target_addr);
    W25Q_Page_Program(&W25Q_Flash, target_addr,
                       (uint8_t *)&g_w25q_storage, W25Q_STORAGE_SIZE);
}
```

### 6.7 魔数（Magic Number）详解

**魔数是什么？**

魔数是一个**精心挑选的固定常量值**，存储在数据块的开头，用来回答一个核心问题：

> "这块 Flash 里的数据，是我期望的那种格式吗？"

==魔数不是密码，不是校验，而是一个"身份标识符"==。它的作用类似于文件头 — 就像 PNG 文件以 `89 50 4E 47` 开头、ZIP 文件以 `50 4B 03 04` 开头一样，软件通过读取这几个字节就能快速判断"这是不是我要的文件"。

#### 项目中的魔数

```c
#define W25Q_STORAGE_MAGIC      0x53544F52U   // ASCII: "STOR"
```

`0x53544F52` 是 `STOR` 四个 ASCII 字符的十六进制编码：

| 字节 | 0x53 | 0x54 | 0x4F | 0x52 |
|------|------|------|------|------|
| ASCII | `S` | `T` | `O` | `R` |

选这个值的原因：==可读、好记、调试时一眼能认出来==。如果 Flash 里出现 `53 54 4F 52` 这串字节，说明有人用我们的格式写过数据。

#### 魔数在验证中的作用

```c
static uint8_t storage_validate(const w25q_storage_t *s)
{
    return (s->magic == W25Q_STORAGE_MAGIC)    // 第一关：身份对不对
        && (s->crc == storage_crc(s));         // 第二关：数据坏没坏
}
```

两步验证缺一不可：

| 检查 | 作用 | 防什么 |
|------|------|--------|
| **magic** | 确认这块数据是我们写的 | 全新未擦写的 Flash（全 0xFF）、其他程序写的垃圾数据 |
| **CRC** | 确认数据完整性 | 写入不完整、Flash 比特翻转、断电损坏 |

#### 魔数是怎么工作的

假设一块全新的 Flash，上电后每个字节都是 `0xFF`：

```
地址:     00  01  02  03  04  05  06  07  08  09  0A  0B
内容:    FF  FF  FF  FF  FF  FF  FF  FF  FF  FF  FF  FF
```

第一次 `storage_validate()` 检查：
- `magic` = `0xFFFFFFFF` ≠ `0x53544F52` → **直接判定无效**

写入一次有效数据后：
```
地址:     00  01  02  03  04  05  06  07  08  09  0A  0B
内容:    52  4F  54  53  01  00  00  00  53  54  4F  53
          ↑ "STOR"     ↑counter=1     ↑crc = magic^counter
```

- `magic` = `0x53544F52` → 匹配
- `crc` = `0x53544F52 ^ 0x00000001 = 0x53544F53` → 匹配
- **判定有效**

#### 为什么不用 0 或 1 做魔数？

| 值 | 问题 |
|----|------|
| `0x00000000` | 擦除后的 Flash 是全 `0xFF` 不是 `0x00`，但有些旧芯片或未初始化区域可能是全 0 |
| `0xFFFFFFFF` | 擦除态就是全 0xFF，会误判为有效 |
| `0x00000001` | 太普通，其他程序也可能碰巧用这个值 |
| `0x53544F52` | ==有含义（"STOR"），不会碰巧出现，调试时可读== |

#### 工业界常见的魔数

| 系统/格式 | 魔数 | 含义 |
|-----------|------|------|
| PNG 图片 | `89 50 4E 47` | `.PNG` |
| ZIP 文件 | `50 4B 03 04` | `.PK` (Phil Katz) |
| Linux ext4 超级块 | `0xEF53` | — |
| u-boot 环境变量 | `0x0055AA55` | — |
| LittleFS 文件系统 | `0x65736C66` | `lfs` (littlefs 反过来) |
| 本项目 | `0x53544F52` | `STOR` |

#### 魔数的选择原则

1. **不能是擦除态** — 不能选 `0xFFFFFFFF`，否则全空 Flash 会被误判为有效
2. **有辨识度** — 最好能拼出有意义的 ASCII，调试时方便肉眼确认
3. **足够随机** — 32-bit 魔数碰巧匹配的概率 ≈ 1/43 亿
4. **稳定不变** — 一旦确定就不能改，否则旧数据全部无法识别

---

### 6.8 为什么双扇区能防断电丢失

假设正在写 Slot A 时断电：

| 场景 | Slot A | Slot B | 下次上电 Load 结果 |
|------|--------|--------|-------------------|
| 擦除中断电 | 全 0xFF（无效） | 旧数据有效 | 选 Slot B，恢复旧数据 |
| 编程中断电 | 数据不完整（CRC错） | 旧数据有效 | 选 Slot B，恢复旧数据 |
| 写完成后断电 | 新数据有效 | 旧数据有效 | 选 counter 更大的 |

**关键思想**: 每次只操作一个 slot，另一个 slot 始终有完整的有效数据。Load 总是选择 counter 更大的（更新的）有效数据。

### 6.6 CRC 校验机制

```c
// CRC = magic ^ debug_counter（简化校验，非标准 CRC32）
static uint32_t storage_crc(const w25q_storage_t *s)
{
    return s->magic ^ s->debug_counter;
}

// 验证：magic 匹配 + CRC 匹配
static uint8_t storage_validate(const w25q_storage_t *s)
{
    return (s->magic == W25Q_STORAGE_MAGIC) && (s->crc == storage_crc(s));
}
```

**为什么用 XOR 而非标准 CRC？**
- XOR 足够检测 ==意外写入不完整== 或 ==数据损坏==
- 计算快，代码简单
- 配合 magic 魔数，能排除擦除态(全0xFF)和未初始化数据

---

## 七、Flash 擦写寿命与注意事项

### 7.1 "擦写寿命 10 万次" 到底是什么？

**不是"擦一次坏一点"**，而是 ==出厂时在芯片内部埋了测试结构，保证每个扇区至少能可靠擦写 10 万次==。

#### 物理原理：电子被"困住"了

NOR Flash 的存储单元是一个 **浮栅晶体管 (Floating Gate Transistor)**：

```
        Control Gate
            │
        ┌───┴───┐
        │  Oxide │  ← 绝缘层
        │ ┌───┐ │
        │ │ FG │ │  ← 浮栅（存储电荷的地方）
        │ └───┘ │
        │  Oxide │  ← 绝缘层
        └───┬───┘
            │
     Source ─┴─ Drain
```

- **编程 (写0)**: 向浮栅注入高能电子（FN隧穿效应）。电子穿过氧化层进入浮栅，改变晶体管的阈值电压。
- **擦除 (恢复1)**: 施加反向电压把电子从浮栅拉出来。

每次擦写，电子穿过氧化层时，会有**极少量电子被"困"在氧化层中**，就像鞋底带进地毯的泥土一样越积越多。==随着被困电子增多，浮栅的充电/放电效率下降==，最终导致无法可靠区分 0 和 1。

**这不意味着芯片坏了**，而是这个扇区变得不可靠了。芯片上其他没用到的扇区还是好的。

#### 这是物理寿命，但不是"用完就炸"

| 误解 | 事实 |
|------|------|
| ❌ 10万次一到立刻坏 | ✅ 10万次后只是**可能开始出比特错误**，不是瞬间报废 |
| ❌ 整个芯片只能擦10万次 | ✅ **每个扇区独立计算**，不同扇区可各自擦10万次 |
| ❌ 超过10万次就不能用了 | ✅ 10万次是**厂家保证值**，实测通常能到几十万次才出问题 |

#### 举个例子理解

> 一张白纸每次用橡皮擦掉字再重写。100000 次后纸会磨薄到可能破洞。但你不是整本笔记本只能用 10 万次，而是**这一页**能擦 10 万次。你只用了第 1 页，第 2~1000 页还是全新的。

#### 对本项目的影响

- Slot A 和 Slot B 只有**两个扇区**在轮转，每次 LED 翻转（~250ms）就擦写一次
- **一个扇区连续用**：10 万次 ÷ (4次/秒) ≈ 25000 秒 ≈ **7 小时**就到寿命
- **双扇区轮转**：两个扇区换着写，把同扇区的擦写间隔拉长一倍，约 **14 小时**
- **实际项目中不应频繁擦写**：正式产品应把保存间隔拉长到分钟级或只在变化时保存

### 7.2 量化指标

| 指标 | 值 | 说明 |
|------|----|------|
| 扇区擦除寿命 | **10 万次** | 每个扇区独立计算，厂家质保值 |
| 数据保持 | **20 年** | 常温断电下数据不丢失 |
| 页编程时间 | 典型 0.5ms | 写 256 字节的典型耗时 |
| 扇区擦除时间 | 典型 30ms | 不同型号有差异 |

### 7.3 本项目中的注意事项

1. **双扇区轮转延长寿命**: 项目用两个扇区交替写入，debug_task 每次 LED 翻转都保存一次，单扇区擦写寿命 10 万次，双扇区轮转可延长约一倍。

2. **调试模式下频繁写入注意**: `W25Qxx_DEBUG_MODE = 1` 时，每次 LED 闪烁（约 250ms）都会擦写一次 Flash。长时间运行可能快速消耗寿命。

3. **写前必须擦除**: `App_W25Qxx_Storage_Save` 先 `Sector_Erase` 再 `Page_Program`，顺序不可颠倒。

4. **页边界限制**: `W25Q_Page_Program` 中检查了跨页：
   ```c
   uint32_t page_end = (addr + 256) & ~0xFF;
   if (addr + len > page_end) return W25Q_ERR;
   ```

5. **扇区对齐检查**: `W25Q_Sector_Erase` 检查地址必须是 4KB 对齐：
   ```c
   if (addr % 4096 != 0) return W25Q_ERR;
   ```

---

## 八、完整示例：LED 计数持久化

### 数据流

```c
// dri_debug.c — LED 闪烁计数 + Flash 持久化

static uint32_t g_blink_counter = 0;

void Debug_Task(void *pvParameters)
{
    // === 上电恢复：从 Flash 加载上次的计数值 ===
    g_blink_counter = g_w25q_storage.debug_counter;
    elog_i("DBG", "Counter restored: %lu", g_blink_counter);

    while (1)
    {
        HAL_GPIO_TogglePin(LED_DEBUG_PORT, LED_DEBUG_PIN);

        if (HAL_GPIO_ReadPin(LED_DEBUG_PORT, LED_DEBUG_PIN) == GPIO_PIN_SET)
        {
            g_blink_counter++;  // 递增计数

            // === 保存到 Flash ===
            g_w25q_storage.debug_counter = g_blink_counter;
            if (App_W25Qxx_Storage_Save() != W25Q_OK) {
                elog_e("DBG", "Save to W25Q FAILED");
            }
            elog_i("DBG", "Blink count: %lu", g_blink_counter);
        }
        osDelay(250);
    }
}
```

**完整数据流**:

```
上电:
  App_W25Qxx_System_Init()
    → App_SPI_System_Init()              SPI 硬件初始化
    → W25Q_Init_Device()                 验证 Flash 通信
    → App_W25Qxx_Storage_Load()          从 Flash 恢复
      → 读 Slot A, Slot B
      → 验证 magic + CRC
      → 选 counter 最大的有效数据
    → Debug_Task 读取 g_w25q_storage.debug_counter

运行:
  LED 翻转 → counter++ → Storage_Save()
    → storage_set_crc()
    → 读两个 slot 状态
    → 选 counter 较小的 slot 写入
    → Sector Erase (4KB, ~30ms)
    → Page Program (12 bytes, ~0.5ms)
    → Wait Busy

断电再上电:
  Load 恢复上次保存的 counter，继续从断点计数
```

---

## 附录：SPI 与 W25Q API 速查表

### SPI 总线 API

| 函数 | 参数 | 说明 |
|------|------|------|
| `SPI_Bus_Init(bus)` | `spi_bus_t *bus` | 初始化 SPI 总线（拉高 CS） |
| `SPI_Bus_Select(bus)` | `spi_bus_t *bus` | 选中从设备（CS 拉低） |
| `SPI_Bus_Deselect(bus)` | `spi_bus_t *bus` | 取消选中（CS 拉高） |

### W25Qxx 底层命令 API

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `W25Q_Init_Device(flash)` | 初始化，验证通信 | `W25Q_OK(0)` / `W25Q_ERR(1)` |
| `W25Q_Read_JEDEC_ID(flash)` | 读取 JEDEC ID | 24-bit ID (如 0xEF4014) |
| `W25Q_Read_Buffer(flash, addr, buf, len)` | 读取数据块 | `W25Q_OK` / `W25Q_ERR` |
| `W25Q_Sector_Erase(flash, addr)` | 扇区擦除（4KB对齐） | `W25Q_OK` / `W25Q_ERR` |
| `W25Q_Page_Program(flash, addr, data, len)` | 页编程（≤256B，不跨页） | `W25Q_OK` / `W25Q_ERR` |
| `W25Q_Write_MultiPage(flash, addr, data, len)` | 多页连续写入 | `W25Q_OK` / `W25Q_ERR` |
| `W25Q_Chip_Erase(flash)` | 整片擦除 | `W25Q_OK` / `W25Q_ERR` |

### APP 层存储 API

| 函数                          | 说明                           | 返回值                    |
| --------------------------- | ---------------------------- | ---------------------- |
| `App_W25Qxx_System_Init()`  | 系统初始化（SPI + Flash + Load）    | void                   |
| `App_W25Qxx_Storage_Load()` | 从 Flash 加载数据到 g_w25q_storage | void                   |
| `App_W25Qxx_Storage_Save()` | 将 g_w25q_storage 保存到 Flash   | `W25Q_OK` / `W25Q_ERR` |
| `App_W25Qxx_Get_JEDEC_ID()` | 获取 JEDEC ID                  | 24-bit ID              |

### W25Qxx 命令字节速查

| 命令名 | 字节码 | 用途 |
|--------|--------|------|
| `W25Q_CMD_READ_DATA` | `0x03` | 读数据 (4 字节命令后面跟 N 字节数据) |
| `W25Q_CMD_PAGE_PROGRAM` | `0x02` | 页编程 (4 字节命令 + ≤256 字节数据) |
| `W25Q_CMD_SECTOR_ERASE` | `0x20` | 扇区擦除 (4 字节命令) |
| `W25Q_CMD_WRITE_ENABLE` | `0x06` | 写使能 (1 字节命令) |
| `W25Q_CMD_STATUS_REG` | `0x05` | 读状态寄存器 (1 字节命令 + 1 字节数据) |
| `W25Q_CMD_READ_JEDEC_ID` | `0x9F` | 读 JEDEC ID (1 字节命令 + 3 字节数据) |
| `W25Q_CMD_CHIP_ERASE` | `0xC7` | 整片擦除 (1 字节命令) |

---

### 相关笔记
- [[高昌/项目交接日志]]
