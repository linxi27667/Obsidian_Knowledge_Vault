# CAN总线详解

## 核心概念

- **CAN** - 控制器局域网络
- **帧** - 数据传输单位
- **仲裁** - 总线竞争解决
- **错误处理** - 故障检测与恢复

---

## 一、CAN基础

### 1.1 CAN特点

| 特性 | 说明 |
|------|------|
| 多主通信 | 任意节点可发送 |
| 非破坏性仲裁 | 优先级高的继续发送 |
| 错误检测 | 5种错误检测机制 |
| 错误恢复 | 自动重发 |
| 速率 | 最高1Mbps(经典CAN) |

---

### 1.2 CAN帧格式

```
标准帧(11位ID):
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ SOF │ ID  │ RTR │ IDE │ r0  │ DLC │DATA │ CRC │ EOF │
│ 1bit│11bit│1bit │1bit │1bit │4bit │0-64 │15bit│7bit │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘

扩展帧(29位ID):
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ SOF │ID11│SRR │ IDE │ID18 │ RTR │ r0  │DLC │DATA │CRC│EOF│
│ 1bit│11bit│1bit│1bit │18bit│1bit │1bit │4bit│0-64 │15 │7 │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

### 1.3 波特率计算

```c
// CAN波特率
/*
 * 位时间 = 同步段 + 传播段 + 相位缓冲段1 + 相位缓冲段2
 *
 * 波特率 = 时钟频率 / (预分频器 × 位时间)
 *
 * 例: 时钟=36MHz, 预分频=9
 *   位时间 = 1 + 2 + 3 + 2 = 8 TQ
 *   波特率 = 36MHz / (9 × 8) = 500kbps
 */

// 位时间配置
typedef struct {
    uint8_t sync_seg;      // 固定1 TQ
    uint8_t prop_seg;      // 1-8 TQ
    uint8_t phase_seg1;    // 1-8 TQ
    uint8_t phase_seg2;    // 1-8 TQ
    uint8_t sjw;           // 同步跳转宽度 1-4
} can_timing_t;

can_timing_t can_500k_timing = {
    .sync_seg = 1,
    .prop_seg = 2,
    .phase_seg1 = 3,
    .phase_seg2 = 2,
    .sjw = 1
};
```

---

## 二、CAN协议

### 2.1 帧类型

```c
// 帧类型枚举
typedef enum {
    CAN_FRAME_DATA = 0,    // 数据帧
    CAN_FRAME_REMOTE = 1,  // 远程帧
    CAN_FRAME_ERROR = 2,   // 错误帧
    CAN_FRAME_OVERLOAD = 3 // 过载帧
} can_frame_type_t;

// 数据帧结构
typedef struct {
    uint32_t id;           // 标识符
    uint8_t ide;           // 扩展帧标志
    uint8_t rtr;           // 远程帧标志
    uint8_t dlc;           // 数据长度(0-8)
    uint8_t data[8];       // 数据
} can_frame_t;
```

---

### 2.2 仲裁机制

```c
// 非破坏性仲裁
/*
 * 发送时同时监听总线
 * 发送显性位(0)但读到隐性位(1) → 失去仲裁，退出
 * 发送隐性位(1)但读到显性位(0) → 失去仲裁，退出
 * ID越小，优先级越高(显性位更多)
 *
 * 例:
 *   节点A ID=0x100 (0001 0000 0000)
 *   节点B ID=0x200 (0010 0000 0000)
 *
 *   仲裁过程:
 *   A: 0 0 0 1 ...
 *   B: 0 0 1 0 ...
 *      ↗ ↗ ↗ ↑
 *    相同 相同 A胜出(显性)
 */
```

---

### 2.3 错误检测

```c
// 错误类型
typedef enum {
    CAN_ERR_BIT = 0,       // 位错误
    CAN_ERR_STUFF = 1,     // 填充错误
    CAN_ERR_CRC = 2,       // CRC错误
    CAN_ERR_FORM = 3,      // 格式错误
    CAN_ERR_ACK = 4        // 应答错误
} can_error_type_t;

// 错误计数器
typedef struct {
    uint16_t tec;  // 发送错误计数
    uint16_t rec;  // 接收错误计数
} can_error_counter_t;

// 节点状态
typedef enum {
    CAN_STATE_ERROR_ACTIVE = 0,   // 正常
    CAN_STATE_ERROR_PASSIVE = 1,  // 错误被动
    CAN_STATE_BUS_OFF = 2         // 总线关闭
} can_node_state_t;

can_node_state_t get_node_state(can_error_counter_t *cnt) {
    if (cnt->tec >= 256 || cnt->rec >= 256) {
        return CAN_STATE_BUS_OFF;
    } else if (cnt->tec >= 128 || cnt->rec >= 128) {
        return CAN_STATE_ERROR_PASSIVE;
    }
    return CAN_STATE_ERROR_ACTIVE;
}
```

---

## 三、STM32 CAN驱动

### 3.1 bxCAN配置

```c
// STM32 bxCAN初始化
void can_init(void) {
    // 使能时钟
    RCC->APB1ENR |= RCC_APB1ENR_CAN1EN;

    // 进入初始化模式
    CAN1->MCR = CAN_MCR_INRQ;
    while (!(CAN1->MSR & CAN_MSR_INAK));

    // 配置波特率: 500kbps (APB1=42MHz)
    CAN1->BTR = (9 << CAN_BTR_BRP_Pos) |   // 预分频=10
                (1 << CAN_BTR_TS1_Pos) |    // TS1=2
                (2 << CAN_BTR_TS2_Pos) |    // TS2=3
                (0 << CAN_BTR_SJW_Pos);     // SJW=1

    // 配置模式
    CAN1->MCR = CAN_MCR_ABOM |      // 自动总线关闭管理
                CAN_MCR_AWUM |      // 自动唤醒模式
                CAN_MCR_TXFP;       // 发送FIFO优先级

    // 退出初始化模式
    CAN1->MCR &= ~CAN_MCR_INRQ;
    while (CAN1->MSR & CAN_MSR_INAK);
}
```

---

### 3.2 过滤器配置

```c
// 过滤器配置
void can_filter_init(void) {
    // 过滤器0: 接收所有标准帧
    CAN1->FMR |= CAN_FMR_FINIT;

    // 过滤器配置
    CAN1->FA1R &= ~CAN_FA1R_FACT0;  // 禁用过滤器0
    CAN1->FM1R |= CAN_FM1R_FBM0;    // 列表模式
    CAN1->FS1R |= CAN_FS1R_FSC0;    // 32位尺度

    // ID: 0x100-0x1FF
    CAN1->sFilterRegister[0].FR1 = (0x100 << 5) | (0x100 << 21);
    CAN1->sFilterRegister[0].FR2 = (0x1FF << 5) | (0x1FF << 21);

    // 关联到FIFO0
    CAN1->FFA1R &= ~CAN_FFA1R_FFA0;

    // 使能过滤器
    CAN1->FA1R |= CAN_FA1R_FACT0;
    CAN1->FMR &= ~CAN_FMR_FINIT;
}
```

---

### 3.3 收发实现

```c
// 发送
int can_transmit(can_frame_t *frame) {
    // 选择空邮箱
    uint32_t mailbox;
    if (CAN1->TSR & CAN_TSR_TME0) mailbox = 0;
    else if (CAN1->TSR & CAN_TSR_TME1) mailbox = 1;
    else if (CAN1->TSR & CAN_TSR_TME2) mailbox = 2;
    else return -1;  // 无空邮箱

    // 配置ID
    CAN1->sTxMailBox[mailbox].TIR = (frame->id << 21) |
                                     (frame->rtr << 1) |
                                     (frame->ide << 2);

    // 配置DLC
    CAN1->sTxMailBox[mailbox].TDTR = frame->dlc;

    // 配置数据
    CAN1->sTxMailBox[mailbox].TDLR = *(uint32_t*)&frame->data[0];
    CAN1->sTxMailBox[mailbox].TDHR = *(uint32_t*)&frame->data[4];

    // 请求发送
    CAN1->sTxMailBox[mailbox].TIR |= CAN_TI0R_TXRQ;

    return 0;
}

// 接收
int can_receive(can_frame_t *frame) {
    // 检查FIFO0
    if ((CAN1->RF0R & CAN_RF0R_FMP0) == 0) return -1;

    // 读取ID
    frame->id = (CAN1->sFIFOMailBox[0].RIR >> 21) & 0x7FF;
    frame->ide = (CAN1->sFIFOMailBox[0].RIR >> 2) & 1;
    frame->rtr = (CAN1->sFIFOMailBox[0].RIR >> 1) & 1;

    // 读取DLC
    frame->dlc = CAN1->sFIFOMailBox[0].RDTR & 0x0F;

    // 读取数据
    *(uint32_t*)&frame->data[0] = CAN1->sFIFOMailBox[0].RDLR;
    *(uint32_t*)&frame->data[4] = CAN1->sFIFOMailBox[0].RDHR;

    // 释放FIFO
    CAN1->RF0R |= CAN_RF0R_RFOM0;

    return 0;
}
```

---

## 四、ESP32 TWAI驱动

### 4.1 TWAI配置

```c
// ESP32 TWAI(CAN)驱动
#include "driver/twai.h"

void esp32_can_init(void) {
    twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
        GPIO_NUM_5, GPIO_NUM_4, TWAI_MODE_NORMAL);
    twai_timing_config_t t_config = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

    twai_driver_install(&g_config, &t_config, &f_config);
    twai_start();
}

// 发送
void esp32_can_send(uint32_t id, uint8_t *data, uint8_t len) {
    twai_message_t message = {
        .identifier = id,
        .data_length_code = len,
    };
    memcpy(message.data, data, len);
    twai_transmit(&message, pdMS_TO_TICKS(1000));
}

// 接收
int esp32_can_receive(twai_message_t *message) {
    return twai_receive(message, pdMS_TO_TICKS(100));
}
```

---

## 五、CANopen协议

### 5.1 对象字典

```c
// 对象字典结构
typedef struct {
    uint16_t index;
    uint8_t subindex;
    uint8_t data_type;
    uint32_t value;
} od_entry_t;

// 常用对象字典索引
#define OD_DEVICE_TYPE      0x1000
#define OD_ERROR_REGISTER   0x1001
#define OD_COB_ID_SYNC      0x1005
#define OD_COMMUNICATION    0x1018
#define OD_RPDO1_MAPPING    0x1600
#define OD_TPDO1_MAPPING    0x1A00

// SDO读取
void sdo_read(uint8_t node_id, uint16_t index, uint8_t subindex) {
    can_frame_t frame;
    frame.id = 0x600 + node_id;
    frame.dlc = 8;
    frame.data[0] = 0x40;  // 读请求
    frame.data[1] = index & 0xFF;
    frame.data[2] = (index >> 8) & 0xFF;
    frame.data[3] = subindex;

    can_transmit(&frame);
}

// SDO写入
void sdo_write(uint8_t node_id, uint16_t index, uint8_t subindex,
               uint32_t value, uint8_t size) {
    can_frame_t frame;
    frame.id = 0x600 + node_id;
    frame.dlc = 8;

    // 快速下载
    switch (size) {
        case 1: frame.data[0] = 0x2F; break;  // 1字节
        case 2: frame.data[0] = 0x2B; break;  // 2字节
        case 4: frame.data[0] = 0x23; break;  // 4字节
    }

    frame.data[1] = index & 0xFF;
    frame.data[2] = (index >> 8) & 0xFF;
    frame.data[3] = subindex;
    *(uint32_t*)&frame.data[4] = value;

    can_transmit(&frame);
}
```

---

### 5.2 NMT状态机

```c
// NMT命令
#define NMT_CMD_START       0x01
#define NMT_CMD_STOP        0x02
#define NMT_CMD_PRE_OP      0x80
#define NMT_CMD_RESET       0x81
#define NMT_CMD_RESET_COMM  0x82

// NMT状态
typedef enum {
    NMT_STATE_INIT = 0,
    NMT_STATE_PRE_OP = 127,
    NMT_STATE_OPERATIONAL = 5,
    NMT_STATE_STOPPED = 4
} nmt_state_t;

void nmt_send_command(uint8_t node_id, uint8_t command) {
    can_frame_t frame;
    frame.id = 0x000;  // NMT广播
    frame.dlc = 2;
    frame.data[0] = command;
    frame.data[1] = node_id;  // 0=广播
    can_transmit(&frame);
}
```

---

## 六、CAN FD

### 6.1 CAN FD特点

```c
// CAN FD vs 经典CAN
/*
 * 特性          经典CAN    CAN FD
 * 数据长度      8字节      64字节
 * 最高速率      1Mbps      8Mbps(数据段)
 * 仲裁段速率    1Mbps      1Mbps
 * CRC           15位       17/21位
 */

// CAN FD帧结构
typedef struct {
    uint32_t id;
    uint8_t ide;
    uint8_t rtr;
    uint8_t dlc;       // 0-15
    uint8_t data[64];  // 最大64字节
    uint8_t brs;       // 波特率切换
    uint8_t esi;       // 错误状态指示
} canfd_frame_t;
```

---

## 七、CAN调试

### 7.1 CAN分析

```c
// CAN总线统计
typedef struct {
    uint32_t tx_count;
    uint32_t rx_count;
    uint32_t error_count;
    uint32_t bus_off_count;
    uint32_t arb_lost_count;
} can_stats_t;

// 总线负载计算
float calc_bus_load(uint32_t frames_per_sec, uint8_t avg_dlc) {
    // 每帧位数 = 47(固定) + 8×dlc + CRC
    float bits_per_frame = 47 + 8 * avg_dlc + 15;
    float total_bits = frames_per_sec * bits_per_frame;
    return total_bits / 500000.0f * 100;  // 500kbps时的百分比
}
```

---

## 附录：CAN标准帧ID分配

| 范围 | 用途 |
|------|------|
| 0x000 | NMT |
| 0x080 | SYNC |
| 0x100-0x17F | TIME STAMP |
| 0x180-0x1FF | PDO1(TX) |
| 0x200-0x27F | PDO1(RX) |
| 0x280-0x2FF | PDO2(TX) |
| 0x300-0x37F | PDO2(RX) |
| 0x580-0x5FF | SDO(TX) |
| 0x600-0x67F | SDO(RX) |
| 0x700-0x77F | NMT Error |

---

## 相关链接

- [[工业通信协议]] - 工业协议
- [[STM32基础]] - STM32开发
- [[ESP-IDF开发详解]] - ESP32开发
- [[汽车电子技术]] - 汽车CAN
