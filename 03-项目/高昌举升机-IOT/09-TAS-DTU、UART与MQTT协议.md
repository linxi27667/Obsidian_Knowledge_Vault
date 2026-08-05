---
created: 2026-07-15 00:00
updated: 2026-07-17 12:30
tags: [TAS, DTU, UART, DMA, MQTT, 协议]
project_root: E:/MCU/gaochang/Gc_Iot_Lift
---

# TAS DTU、UART 与 MQTT 协议（设备联网的完整闭环）

## 核心概念

- ==TAS DTU 是蜂窝通信终端，不运行举升机控制逻辑==。
- ==STM32 先用 AT 指令配置 DTU，再进入 MQTT 透传态==。
- ==协议可靠性由 QoS 1、msg_id、回执、超时和重试共同完成==。

## 一、链路

```text
STM32F407
↕ USART3（PB10 TX / PB11 RX，DMA）
TAS-LTE-892D_s4
↕ 4G
MQTT Broker 8.134.167.240:1883
↕ mqtt.js
Node.js 管理平台
```

## 二、主题与身份（以源码为准）

| 项 | 真实字符串 |
|---|---|
| Broker | `8.134.167.240:1883` |
| ClientID | `gc-lift-{chip_uid}` |
| **上行** | `gaochang/lift/v1/devices/{chip_uid}/up` |
| **下行** | `gaochang/lift/v1/devices/{chip_uid}/down` |
| 波特率 | 主 9600 / 备 115200 |

> [!IMPORTANT]
> README 中可能出现旧主题。设备端 v1 只配置上述 up/down 字符串。Web 仍兼容订阅旧 `gaochang/lift/+/telemetry` 等。

## 三、UART 接收流水线

1. USART3 RX 使用 DMA 循环模式。
2. `HAL_UARTEx_ReceiveToIdle_DMA()` 接收至 512 字节 DMA 缓冲。
3. HAL 接收事件调用 `BSP_UART_OnHalRxEvent()`。
4. BSP 计算 DMA 新增区间并写入 RX FIFO。
5. `TasDtu_Task` 调用 `App_TasDtu_ProcessRx()` 从 FIFO 逐字节读取。
6. 解析器按换行和 JSON 花括号深度组装完整消息。

关键文件：`usart.c`、`bsp_uart.c`、`app_tas_dtu.c`

## 四、DTU 状态机

```text
OFF → UART_READY → CMD_MODE → CONFIGURED → TRANSPARENT
                                           ↘ ERROR
```

只有 `transparent_ready` 为真时，业务 JSON 才能可靠发送。

## 五、启动策略

1. 等待 DTU 自启动 MQTT URC。
2. 在 9600 波特率探测已保存链路。
3. 必要时兼容探测 115200。
4. 验证 Broker、Client ID、发布/订阅主题。
5. 保存配置无效时才进入命令模式重新配置。
6. 重启 DTU，等待 MQTT CONNECTED，再进入透传。

## 六、进入命令模式

```text
MCU → +++
DTU → a
MCU → a
DTU → +ok
```

DTU 上电后可能已在透传态，直接发 `AT` 会被当作 MQTT 业务数据。

## 七、关键 AT 配置

| AT 指令 | 作用 |
|---|---|
| `AT+DTUMODE=2,1` | MQTT DTU 模式 |
| `AT+IPPORT=...` | Broker 地址和端口 |
| `AT+CLIENTID="gc-lift-<uid>",1` | 客户端 ID |
| `AT+USERPWD="","",1` | MQTT 账号密码（当前默认空） |
| `AT+MQTTSUB=1,".../down",0,1,1` | 下行订阅 |
| `AT+MQTTPUB=1,".../up",0,0,1,1` | 上行发布 |
| `AT+MQTTKEEP=30,1` | 30 s Keep Alive |
| `AT+CLEANSESSION=1,1` | 清洁会话 |
| `AT+DTUPACKET=0,1024` | 数据包大小 |
| `AT+RELINKTIME=30` | 重连间隔 |
| `ATO` | 进入透传 |
| `+++` | 退出透传 |

来源：`App_TasDtu_ConfigMqttChannel()`

## 八、上行 type 分流

一个上行主题通过 JSON 的 `type` 分流：

- `telemetry`
- `event`
- `operation_log`
- `command_response`
- `offline_batch`

## 九、命令与回执

下行示例：

```json
{
  "v": 1,
  "type": "command",
  "cmd": "lock",
  "chip_uid": "设备UID",
  "msg_id": "唯一命令ID"
}
```

上行回执示例：

```json
{
  "v": 1,
  "type": "command_response",
  "chip_uid": "设备UID",
  "cmd": "lock",
  "msg_id": "同一个唯一命令ID",
  "result": "succeeded",
  "reason": "lock_ok"
}
```

### 设备端支持的 cmd

| cmd | 动作 |
|---|---|
| `ping` | 回 pong |
| `get_status` | 上报 telemetry + completed |
| `lock` / `unlock` | `LiftIot_SetLocked` |
| `buzzer_on` / `buzzer_off` | 蜂鸣 |
| `admin_enter` / `admin_exit` | 密码 `123456` |
| `fault_clear` | 需 admin |
| `clear_alarm` | 光电报警解除 |
| `set_config` / `get_config` | 配置 |
| `maintenance_done` | 维保完成 |
| `reset_usage` | 清使用计数 |
| `reboot_dtu` | 重启模块 |
| `admin_jog` | 大剪返回 denied |

固件入口：`App_TasDtu_HandleJsonCommand()`。

## 十、msg_id 幂等

- 设备端：`TAS_DTU_MSG_ID_CACHE_SIZE=16` 环形缓存；相同 msg_id 直接重放结果
- 云端：`mqtt-bridge.js` 5 分钟窗口、最多 1000 条 msg_id 去重
- Web 校验：主题 UID = JSON UID、回执 cmd 匹配、仅 pending/sent 可转终态

## 十一、上报策略

| 场景 | 周期 |
|---|---|
| 静止遥测 | 约 5 s |
| 运动中 | 约 1 s |
| 事件 | 优先，仍受最小间隔限制 |
| 错误重试 | 60 s / 300 s 节流 |

## 十二、调试三段证据

1. Web/MQTT：是否向正确 `{uid}/down` 发布正确 JSON
2. MCU：RTT 是否出现 `CMD RX cmd=... msg_id=...`
3. 回执：是否从 `{uid}/up` 收到匹配 `command_response`

若第 1 段有、第 2 段无，查 Broker、订阅、DTU 透传和 UART；若第 2 段有、第 3 段无，查命令执行、发送缓冲和上行链路。

## 十三、答辩表达

> TAS DTU 负责 4G 和 MQTT，STM32 通过 USART3 DMA/FIFO 与它通信。设备上电先验证 DTU 已保存的 MQTT 配置，必要时通过逃逸序列进入 AT 模式重配，成功后转为透明传输。协议使用按芯片 UID 隔离的 up/down 主题、QoS 1、msg_id 去重以及 command_response 回执，实现可确认的远程控制。
