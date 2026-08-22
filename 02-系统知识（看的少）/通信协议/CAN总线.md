# CAN总线 （差分多主 硬件仲裁 错误检测）

## 核心概念

### 基本原理
- ==多主架构== - 所有节点平等，可主动发送
- ==硬件仲裁== - 埧ID优先级自动裁决，不冲突
- ==差分信号== - CAN_H与CAN_L差分传输
- ==错误检测== - 多种错误检测机制

### 信号电平
- ==显性（0）== - CAN_H≈3.5V，CAN_L≈1.5V，差分≈2V
- ==隐性（1）== - CAN_H≈2.5V，CAN_L≈2.5V，差分≈0V

---

## 一、CAN帧格式

### 1.1 标准帧与扩展帧

```
标准帧（11位ID）:
┌────┬────┬────────┬────┬────┬──────────┬────┬────┬────┐
│SOF │ID  │RTR/IDE │r0  │DLC │DATA(0-8) │CRC │ACK │EOF │
│1bit│11bit│2bit   │1bit│4bit│0-64bit   │15bit│2bit│7bit│
└────┴────┴────────┴────┴────┴──────────┴────┴────┴────┘

扩展帧（29位ID）:
┌────┬────┬────┬────┬────┬────┬──────────┬────┬────┬────┐
│SOF │ID  │SRR │IDE │ID18│r1r0│DLC DATA  │CRC │ACK │EOF │
│1bit│11bit│1bit│1bit│18bit│2bit│...      │... │... │... │
└────┴────┴────┴────┴────┴────┴──────────┴────┴────┴────┘
```

### 1.2 帧类型

| 类型 | RTR位 | 说明 |
|------|-------|------|
| 数据帧 | 0 | 发送数据 |
| 远程帧 | 1 | 请求其他节点发送数据 |
| 错误帧 | - | 报告错误 |
| 过载帧 | - | 请求延迟下一帧 |

---

## 二、STM32 bxCAN初始化

### 2.1 CAN配置参数

| 参数 | 说明 |
|------|------|
| Prescaler | 时间份额预分频 |
| SyncJumpWidth (SJW) | 同步跳跃宽度 |
| TimeSeg1 (BS1) | 时间段1（传播段+相位缓冲段1） |
| TimeSeg2 (BS2) | 时间段2（相位缓冲段2） |
| AutoBusOff | 自动恢复总线离线状态 |
| AutoRetransmission | 发送失败自动重传 |

### 2.2 波特率计算

> [!TIP] CAN波特率计算公式
> BaudRate = PCLK / (Prescaler × (SyncSeg + BS1 + BS2))

**示例**（STM32F103，PCLK=36MHz）：

| 目标波特率 | Prescaler | BS1 | BS2 | 计算 |
|-----------|-----------|-----|-----|------|
| 1Mbps | 4 | 6TQ | 2TQ | 36MHz/(4×9) = 1MHz |
| 500kbps | 8 | 6TQ | 2TQ | 36MHz/(8×9) = 500kHz |
| 250kbps | 16 | 6TQ | 2TQ | 36MHz/(16×9) = 250kHz |
| 125kbps | 32 | 6TQ | 2TQ | 36MHz/(32×9) = 125kHz |

### 2.3 GPIO配置

- CAN_RX (PA11)：复用推挽输出
- CAN_TX (PA12)：复用推挽输出

---

## 三、发送数据

### 3.1 发送头配置

| 字段 | 说明 |
|------|------|
| StdId | 标准ID（11位） |
| ExtId | 扩展ID（29位，标准帧不用） |
| RTR | 数据帧(CAN_RTR_DATA) / 远程帧(CAN_RTR_REMOTE) |
| IDE | 标准帧(CAN_ID_STD) / 扩展帧(CAN_ID_EXT) |
| DLC | 数据长度（0-8字节） |

### 3.2 发送流程

1. 配置发送头（ID、帧类型、数据长度）
2. 检查空闲发送邮箱（`HAL_CAN_GetTxMailboxesFreeLevel`）
3. 添加到发送邮箱（`HAL_CAN_AddTxMessage`）
4. 等待发送完成（`HAL_CAN_IsTxMessagePending`）

---

## 四、接收数据

### 4.1 过滤器配置

CAN控制器通过过滤器决定接收哪些消息：

| 过滤模式 | 说明 |
|----------|------|
| 掩码模式（IDMASK） | ID与掩码按位与后匹配 |
| 列表模式（IDLIST） | 精确匹配指定ID列表 |

**过滤器参数**：
- FilterBank：过滤器编号（0~27）
- FilterScale：16位或32位宽度
- FilterFIFOAssignment：分配到FIFO0或FIFO1
- FilterActivation：启用/禁用

### 4.2 接收流程

1. 配置过滤器（决定接收哪些ID）
2. 启动CAN（`HAL_CAN_Start`）
3. 开启接收中断（`CAN_IT_RX_FIFO0_MSG_PENDING`）
4. 在回调 `HAL_CAN_RxFifo0MsgPendingCallback` 中读取消息
5. 通过 `HAL_CAN_GetRxMessage` 获取ID和数据

---

## 五、仲裁机制详解

### 5.1 非破坏性仲裁

> [!NOTE] 仲裁规则
> 显性位（0）覆盖隐性位（1），ID值越小优先级越高

**仲裁过程**：
1. 多个节点同时开始发送ID
2. 每发送一位，节点同时读取总线电平
3. 若发送隐性(1)但读到显性(0)，说明有更高优先级节点在发送
4. 该节点立即停止发送，转为接收
5. 优先级最高的节点（ID最小）继续发送，不受影响

### 5.2 ID优先级设计原则

| 优先级 | ID范围 | 消息类型 |
|--------|--------|----------|
| 最高 | 低ID | 紧急报警、安全控制 |
| 中 | 中ID | 关键传感器数据 |
| 低 | 高ID | 日志记录、状态查询 |

---

## 六、错误处理

### 6.1 错误状态

| 状态 | 条件 | 说明 |
|------|------|------|
| 错误警告（EWG） | TEC或REC > 96 | 总线质量下降 |
| 错误被动（EPV） | TEC或REC > 127 | 只能发送隐性位 |
| 总线关闭（BOF） | TEC > 255 | 节点脱离总线 |

- **TEC**：发送错误计数器
- **REC**：接收错误计数器
- 开启 `AutoBusOff` 可在总线关闭后自动恢复

### 6.2 错误回调

- `HAL_CAN_ErrorCallback` 中获取 `hcan->ErrorCode`
- 根据错误码判断具体错误类型

---

## 七、应用要点

### 7.1 初始化顺序

1. 初始化CAN外设（时钟、GPIO）
2. 配置过滤器
3. 启动CAN（`HAL_CAN_Start`）
4. 开启中断通知
5. 开始发送/接收

### 7.2 多节点通信

- 每个节点配置不同的过滤器接收目标ID
- 发送时根据消息重要性分配ID优先级
- 总线两端需加120Ω终端电阻

### 7.2 多节点通信

```c
// 模拟车辆CAN网络节点定义
#define CAN_ID_ENGINE_STATUS   0x100
#define CAN_ID_SPEED_SENSOR    0x200
#define CAN_ID_BRAKE_CMD       0x010  // 高优先级
#define CAN_ID_LIGHTS_CTRL     0x300

// 发送发动机状态
void Send_Engine_Status(uint8_t rpm, uint8_t temp)
{
    uint8_t data[2] = {rpm, temp};
    CAN_Send_Data(CAN_ID_ENGINE_STATUS, data, 2);
}

// 发送刹车命令（高优先级）
void Send_Brake_Command(uint8_t brake_level)
{
    uint8_t data[1] = {brake_level};
    CAN_Send_Data(CAN_ID_BRAKE_CMD, data, 1);
}

// 处理接收消息
void Process_CAN_Message(uint32_t id, uint8_t *data, uint8_t len)
{
    switch(id)
    {
        case CAN_ID_ENGINE_STATUS:
            printf("RPM: %d, Temp: %d\n", data[0], data[1]);
            break;
        case CAN_ID_BRAKE_CMD:
            printf("Brake Level: %d\n", data[0]);
            break;
    }
}
```

---

## 八、硬件设计要点

### 8.1 CAN收发器芯片

| 芯片 | 速率 | 特点 |
|------|------|------|
| TJA1050 | 1Mbps | 经典，5V |
| TJA1042 | 5Mbps | 高速，3.3V/5V |
| SN65HVD230 | 1Mbps | TI，3.3V兼容STM32 |

### 8.2 终端电阻

```c
// 硬件说明
/*
CAN总线两端各需要120Ω终端电阻
┌─────────┐      ┌─────────┐      ┌─────────┐
│ Node1   │─H─── │ Node2   │─H─── │ Node3   │
│ 120Ω    │─L─── │         │─L─── │ 120Ω    │
└─────────┘      └─────────┘      └─────────┘
*/
```

---

## 附录：CAN常用API速查表

### 发送函数
| 函数 | 说明 |
|------|------|
| `HAL_CAN_AddTxMessage()` | 添加发送消息到邮箱 |
| `HAL_CAN_GetTxMailboxesFreeLevel()` | 获取空闲邮箱数量 |
| `HAL_CAN_IsTxMessagePending()` | 检查发送是否完成 |

### 接收函数
| 函数 | 说明 |
|------|------|
| `HAL_CAN_GetRxMessage()` | 从FIFO获取接收消息 |
| `HAL_CAN_GetRxFifoFillLevel()` | 获取FIFO消息数量 |

### 控制函数
| 函数 | 说明 |
|------|------|
| `HAL_CAN_Start()` | 启动CAN |
| `HAL_CAN_Stop()` | 停止CAN |
| `HAL_CAN_RequestSleep()` | 请求睡眠模式 |
| `HAL_CAN_ActivateNotification()` | 开启中断通知 |

### 过滤器函数
| 函数 | 说明 |
|------|------|
| `HAL_CAN_ConfigFilter()` | 配置过滤器 |

### 回调函数
| 函数 | 说明 |
|------|------|
| `HAL_CAN_RxFifo0MsgPendingCallback()` | FIFO0接收回调 |
| `HAL_CAN_RxFifo1MsgPendingCallback()` | FIFO1接收回调 |
| `HAL_CAN_TxMailbox0CompleteCallback()` | 邮箱0发送完成回调 |
| `HAL_CAN_ErrorCallback()` | 错误回调 |

---