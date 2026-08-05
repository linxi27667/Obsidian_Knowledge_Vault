---
title: 小智项目 MQTT 设计架构
tags: [IoT, MQTT, ESP32, 小智, 架构设计]
created: 2026-05-04
---

# 小智项目 MQTT 设计架构

## 一、系统架构总览

### 1.1 拓扑结构

```
                    MQTT Broker (Mosquitto)
                    (公网 broker.emqx.io 或本地 127.0.0.1)
                            ▲
              ┌─────────────┼─────────────┐
              │             │             │
         中控主机        一楼设备       二楼设备       三楼设备
    (xiaozhi_master)  (slave_1)     (slave_2)     (slave_3)
         客厅           一楼          二楼          三楼
         ↓               ↓             ↓             ↓
      接收响应         执行命令       执行命令       执行命令
      发送命令         上报状态       上报状态       上报状态
```

### 1.2 设计原则

| 原则 | 说明 | 实现方式 |
|------|------|---------|
| **去中心化** | 设备不直接通信，全靠 Broker 中转 | 所有消息通过 MQTT Topic 路由 |
| **发布-订阅解耦** | 发布者不知道订阅者是谁 | 通过 Topic 匹配，不依赖设备地址 |
| **幂等性** | 重复操作不影响最终状态 | 命令值即目标状态，非增量操作 |
| **异步容错** | 网络抖动不阻塞系统 | QoS 0 + 应用层心跳兜底 |
| **可扩展性** | 新增设备无需改主控代码 | 设备自宣告 + 别名映射 |

---

## 二、Topic 主题设计

### 2.1 完整主题树

```
xiaozhi/iot/
├── cmd/                          ← 命令通道（主机 → 从机）
│   ├── broadcast                 ← 广播命令（所有设备接收）
│   ├── 1                         ← 定向命令（仅一楼设备）
│   ├── 2                         ← 定向命令（仅二楼设备）
│   └── 3                         ← 定向命令（仅三楼设备）
│
├── resp/                         ← 响应通道（从机 → 主机）
│   ├── {MAC地址}                 ← 按设备 MAC 区分响应来源
│   └── 示例: AA1122334455        ← 一楼设备的响应
│
├── heartbeat/                    ← 心跳通道（从机 → 主机）
│   ├── 1                         ← 一楼设备心跳
│   ├── 2                         ← 二楼设备心跳
│   └── 3                         ← 三楼设备心跳
│
├── announce/                     ← 上线公告（从机 → 主机）
│   ├── {MAC地址}                 ← 设备上线时主动宣告
│   └── 示例: BB2233445566        ← 新设备上线
│
└── status/                       ← 状态通道（遗嘱消息）
    └── {device_id}               ← 设备异常离线时自动发布
```

### 2.2 各角色的订阅策略

**中控主机订阅：**
```c
esp_mqtt_client_subscribe(client, "xiaozhi/iot/resp/+", 0);      // 收所有响应
esp_mqtt_client_subscribe(client, "xiaozhi/iot/heartbeat/+", 0); // 收所有心跳
esp_mqtt_client_subscribe(client, "xiaozhi/iot/announce/+", 1);  // 收上线公告
```

**从设备订阅：**
```c
// 一楼设备
esp_mqtt_client_subscribe(client, "xiaozhi/iot/cmd/1", 0);           // 给自己的命令
esp_mqtt_client_subscribe(client, "xiaozhi/iot/cmd/broadcast", 0);   // 广播命令
```

### 2.3 通配符使用对照

| 订阅主题 | 匹配范围 | 用途 |
|---------|---------|------|
| `xiaozhi/iot/resp/+` | 所有设备的响应 | 主机用 `+` 匹配 MAC 地址层 |
| `xiaozhi/iot/heartbeat/+` | 所有设备的心跳 | 同上 |
| `xiaozhi/iot/announce/+` | 所有设备的上线公告 | 同上 |
| `xiaozhi/iot/cmd/1` | 仅 cmd/1 | 精确匹配，一楼设备专属 |
| `xiaozhi/iot/cmd/broadcast` | 仅广播 | 精确匹配 |
| `xiaozhi/iot/#` | 所有 IoT 消息 | 调试用，生产环境不用 |

---

## 三、命令协议设计

### 3.1 数据包格式（8 字节固定）

```c
typedef struct {
    uint8_t command;     // 命令类型（1 字节）
    uint8_t device_id;   // 目标设备 ID（1 字节）
    uint8_t gpio_index;  // GPIO 索引或子设备号（1 字节）
    uint8_t value;       // 控制值/角度/状态（1 字节）
    uint8_t reserved[4]; // 保留字段（4 字节）
} __attribute__((packed)) iot_command_packet_t;
```

### 3.2 命令码定义

| 命令码 | 值 | 方向 | 说明 |
|--------|----|------|------|
| `IOT_CMD_SET_GPIO` | 0x01 | 主机→从机 | 设置 GPIO 电平 |
| `IOT_CMD_GET_GPIO` | 0x02 | 主机→从机 | 查询 GPIO 状态 |
| `IOT_CMD_GET_ALL_GPIO` | 0x03 | 主机→从机 | 查询全部 GPIO |
| `IOT_CMD_HEARTBEAT` | 0x04 | 从机→主机 | 心跳保活 |
| `IOT_CMD_RESPONSE` | 0x05 | 从机→主机 | 命令响应/ACK |
| `IOT_CMD_DISCOVER` | 0x06 | 主机→从机 | 设备发现广播 |
| `IOT_CMD_ANNOUNCE` | 0x07 | 从机→主机 | 设备上线公告（旧版） |
| `IOT_CMD_ANNOUNCE_V2` | 0x08 | 从机→主机 | 设备上线公告（含设备名） |
| `IOT_CMD_SET_SERVO` | 0x10 | 主机→从机 | 舵机角度控制 |
| `IOT_CMD_SET_LIGHT` | 0x11 | 主机→从机 | 灯光控制 |
| `IOT_CMD_SET_RELAY` | 0x12 | 主机→从机 | 继电器控制 |
| `IOT_CMD_OPEN_MEDICINE_BOX` | 0x20 | 主机→从机 | 药盒开启 |
| `IOT_CMD_BROADCAST_ALL_OFF` | 0x30 | 主机→全部 | 全部关闭 |
| `IOT_CMD_BROADCAST_ALL_ON` | 0x31 | 主机→全部 | 全部开启 |
| `IOT_CMD_BROADCAST_LIGHTS_OFF` | 0x32 | 主机→全部 | 全部关灯 |
| `IOT_CMD_BROADCAST_LIGHTS_ON` | 0x33 | 主机→全部 | 全部开灯 |
| `IOT_CMD_EMERGENCY` | 0x34 | 主机→全部 | 紧急模式 |

### 3.3 命令示例

```
开一楼灯1：
  Topic: xiaozhi/iot/cmd/1
  Hex:   01 01 00 01 00 00 00 00
         ↑  ↑  ↑  ↑
         │  │  │  └─ value=1 (高电平)
         │  │  └──── gpio_index=0 (灯1)
         │  └─────── device_id=1 (一楼)
         └────────── command=0x01 (SET_GPIO)

舵机开到 180 度：
  Topic: xiaozhi/iot/cmd/1
  Hex:   10 01 00 B4 00 00 00 00
         ↑        ↑
         │        └─ value=180 (0xB4)
         ────────── command=0x10 (SET_SERVO)

设备发现广播：
  Topic: xiaozhi/iot/cmd/broadcast
  Hex:   06 00 00 00 00 00 00 00
         ↑
         └─ command=0x06 (DISCOVER)
```

### 3.4 ANNOUNCE_V2 数据包（扩展格式）

```c
typedef struct {
    uint8_t command;        // 0x08
    uint8_t device_id;      // 设备 ID
    uint8_t gpio_index;     // GPIO 数量
    uint8_t value;          // 保留
    char device_name[24];   // 设备名称（如"一楼设备"）
} __attribute__((packed)) iot_announce_v2_packet_t;
```

---

## 四、设备发现机制

### 4.1 三层发现策略

```
                    ┌─────────────────┐
                    │   设备发现流程    │
                    └────────┬────────
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌──────────┐   ──────────┐
        │主动公告  │   │被动发现   │   │手动配置   │
        │ANNOUNCE │   │DISCOVER  │   │硬编码    │
        └────┬────┘   └────┬─────┘   └────┬─────
             │              │              │
       从机上电自动发   主机主动广播    预设 MAC+名称
       ANNOUNCE_V2    所有从机回复    无需网络发现
```

### 4.2 主动公告流程（ANNOUNCE_V2）

```
从机上电：
  1. 连接 MQTT Broker
  2. 获取自身 MAC 地址
  3. 发布 ANNOUNCE_V2:
     Topic: xiaozhi/iot/announce/{MAC}
     Payload: {command:0x08, device_id:1, gpio_count:4, name:"一楼设备"}

主机收到：
  4. 解析 MAC 地址（从 Topic 中提取）
  5. 查找是否已存在该设备（按 MAC 匹配）
  6. 如存在 → 更新设备信息（名称、GPIO 数量）
  7. 如不存在 → 添加新设备到列表
```

### 4.3 被动发现流程（DISCOVER）

```
主机发起：
  1. 发布 DISCOVER 广播:
     Topic: xiaozhi/iot/cmd/broadcast
     Payload: {command:0x06, ...}

从机收到：
  2. 所有订阅了 broadcast 的从机都收到
  3. 每个从机回复 ANNOUNCE（旧版）或 ANNOUNCE_V2
  4. 回复走 resp/ 或 announce/ 通道

主机处理：
  5. 收集所有回复，建立设备列表
  6. 超时未回复的设备标记为离线
```

### 4.4 别名映射表

```c
// 用户说"一楼" → 系统映射到"一楼设备"
static const device_name_alias_t g_device_aliases[] = {
    {"一楼大门", "一楼设备"},
    {"一楼设备", "一楼设备"},
    {"一楼", "一楼设备"},
    {"大厅灯", "一楼设备"},
    {"二楼设备", "二楼设备"},
    {"二楼", "二楼设备"},
    {"主卧", "二楼设备"},
    {"主卧灯", "二楼设备"},
    {"次卧", "二楼设备"},
    {"客厅", "二楼设备"},
    {"二楼风扇", "二楼设备"},
    {"风扇", "二楼设备"},
    {"三楼", "三楼设备"},
    {"三楼设备", "三楼设备"},
    {"阳台灯", "三楼设备"},
    {"次卧灯", "二楼设备"},
    {"客厅灯", "二楼设备"},
    {NULL, NULL}
};
```

**作用：** 用户用自然语言说"把一楼灯打开"，系统通过别名匹配找到对应的设备，无需用户知道设备 ID。

---

## 五、在线状态管理

### 5.1 心跳机制

```
从机定期发送（如每 30 秒）：
  Topic: xiaozhi/iot/heartbeat/{device_id}
  Payload: {command:0x04, device_id:X, ...}

主机收到心跳：
  → 更新该设备的 last_heartbeat_ms = 当前时间
  → 标记 online = true
```

### 5.2 超时检测任务

```c
#define DEVICE_TIMEOUT_MS   60000  // 60 秒超时阈值

// 后台任务每 10 秒执行一次
static void Device_Timeout_Task(void* arg) {
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(10000));
        IOT_Check_Device_Timeout(&g_iot_controller, DEVICE_TIMEOUT_MS);
    }
}

// 超时检测逻辑：
//   if (当前时间 - last_heartbeat_ms > 60000) {
//       online = false;  // 标记离线
//   }
```

### 5.3 状态同步策略

| 场景 | 方案 | 说明 |
|------|------|------|
| 设备正常在线 | 心跳维持 | 每 30 秒心跳，60 秒超时 |
| 设备异常断线 | 遗嘱消息（LWT） | Broker 自动发布离线通知 |
| 主机后启动 | 主动查询 | 发 DISCOVER 让设备重新宣告 |
| 状态不确定 | 主动查询命令 | 发 GET_ALL_GPIO 获取最新状态 |

---

## 六、命令幂等性设计

### 6.1 什么是幂等性

**定义：** 同一个命令执行多次，结果与执行一次相同。

```
开灯命令（SET_GPIO, value=1）:
  执行 1 次 → 灯亮 ✅
  执行 5 次 → 灯还是亮 ✅ （不会闪烁或损坏）
  执行 100 次 → 灯还是亮 ✅

关窗命令（SET_SERVO, angle=0）:
  执行 1 次 → 窗户关闭 ✅
  再执行 1 次 → 窗户已在关闭位置，不动 ✅
```

### 6.2 为什么重要

| 场景 | 问题 | 幂等性解决 |
|------|------|-----------|
| 网络重传 | QoS 1 可能重复投递 | 重复执行结果一致 |
| 用户重复点击 | 小智可能收到重复指令 | 不会执行过度操作 |
| 断线重连 | 重连后补发未确认消息 | 不会造成状态错乱 |

### 6.3 非幂等命令的风险

```
错误设计（增量操作）:
  command: "TOGGLE_LIGHT"  // 切换灯状态
  执行 1 次 → 灯状态翻转
  执行 2 次 → 灯状态又翻转回来（可能不符合预期）
  重复执行 → 状态不确定

正确设计（目标状态）:
  command: "SET_LIGHT", value: 1  // 设置为开
  执行 N 次 → 灯都是开的（确定）
```

---

## 七、GPIO 映射设计

### 7.1 本地 GPIO（主机自身）

```c
#define LOCAL_GPIO_1_PIN    GPIO_NUM_48
#define LOCAL_GPIO_2_PIN    GPIO_NUM_46
#define LOCAL_GPIO_3_PIN    GPIO_NUM_14
#define LOCAL_GPIO_4_PIN    GPIO_NUM_38
```

主机上的 GPIO 直接控制，不走 MQTT。

### 7.2 远程 GPIO 映射（从设备）

| 从设备 | GPIO 索引 | 功能 | 说明 |
|--------|----------|------|------|
| 一楼设备 | 0-3 | LED1-LED4 | 灯光控制 |
| 二楼设备 | 0-3 | LED1-LED4 | 灯光控制 |
| 二楼设备 | 3+ | 继电器 | IOT_Set_Relay 映射到 gpio_index+3 |
| 三楼设备 | 0-2 | 舵机 | 窗户/晾衣架控制 |
| 三楼设备 | 6+ | 舵机 | IOT_Set_Servo 映射到 gpio_index+6 |
| 通用设备 | 0-6 | 药盒 | IOT_Open_Medicine_Box |

### 7.3 场景控制函数

```c
// 回家模式：开门 + 开灯
App_IOT_Scenario_Homecoming("一楼设备", "全部设备");
  → 舵机开到 180 度（开门）
  → 广播开灯

// 离家模式：关门
App_IOT_Scenario_LeaveHome("一楼设备");
  → 舵机关到 0 度（关门）

// 晚安模式：关灯
App_IOT_Scenario_GoodNight("全部设备");
  → 广播关灯

// 下雨收衣
App_IOT_Scenario_Rain_Collect_Clothes("三楼设备");
  → 关闭所有舵机（收衣服）

// 通风模式
App_IOT_Scenario_Ventilate("三楼设备", 90, 1);
  → 窗户开 90 度 + 风扇开
```

---

## 八、ESP-IDF MQTT 配置

### 8.1 当前配置（生产环境 - 公网）

```c
esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = "mqtt://broker.emqx.io",
    .broker.address.port = 1883,
    .credentials.client_id = "xiaozhi_master",
};
```

### 8.2 开发环境配置（本地 Mosquitto）

```c
esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = "mqtt://192.168.1.100",  // 电脑局域网 IP
    .broker.address.port = 1883,
    .credentials.client_id = "xiaozhi_master",
    .network.disable_auto_reconnect = false,       // 允许自动重连
    .session.reconnect_timeout_ms = 60000,         // 重连间隔 60 秒
    .session.keepalive = 240,                      // 心跳间隔 240 秒
};
```

### 8.3 云端部署配置

```c
esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = "mqtt://120.x.x.x",      // 云服务器公网 IP
    .broker.address.port = 1883,
    .credentials.client_id = "xiaozhi_master",
    // 生产环境建议加认证
    .credentials.username = "xiaozhi",
    .credentials.password = "your_password",
};
```

### 8.4 TLS 加密配置（推荐生产使用）

```c
esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = "mqtts://broker.emqx.io:8883",
    .credentials.client_id = "xiaozhi_master",
    .broker.verification.certificate = server_cert_pem_start,
};
```

---

## 九、事件处理流程

### 9.1 主机端事件处理

```c
static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                                int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;
    
    switch (event->event_id) {
        case MQTT_EVENT_CONNECTED:
            // 连接成功后订阅主题
            esp_mqtt_client_subscribe(client, "xiaozhi/iot/resp/+", 0);
            esp_mqtt_client_subscribe(client, "xiaozhi/iot/heartbeat/+", 0);
            esp_mqtt_client_subscribe(client, "xiaozhi/iot/announce/+", 1);
            break;
            
        case MQTT_EVENT_DISCONNECTED:
            // 断线后自动重连（ESP-IDF 默认行为）
            break;
            
        case MQTT_EVENT_DATA:
            // 收到消息 → 解析主题 → 提取 MAC → 处理命令
            HW_MQTT_Recv_Callback(event->topic, event->topic_len, 
                                  event->data, event->data_len);
            break;
            
        case MQTT_EVENT_ERROR:
            // 错误处理
            break;
    }
}
```

### 9.2 消息解析流程

```
收到 MQTT 消息:
  Topic: xiaozhi/iot/heartbeat/AA1122334455
  Data:  [8 字节二进制数据]

解析步骤:
  1. 识别主题前缀:
     - "xiaozhi/iot/heartbeat/" → 心跳消息
     - "xiaozhi/iot/resp/" → 响应消息
     - "xiaozhi/iot/announce/" → 上线公告
     
  2. 提取 MAC 地址:
     mac_str = topic + strlen("xiaozhi/iot/heartbeat/")
     "AA1122334455" → 转换为字节数组 {0xAA, 0x11, 0x22, 0x33, 0x44, 0x55}
     
  3. 解析命令包:
     iot_command_packet_t* cmd = (iot_command_packet_t*)data;
     
  4. 根据 command 字段分发处理:
     - HEARTBEAT → 更新在线状态
     - RESPONSE → 处理命令确认
     - ANNOUNCE_V2 → 注册/更新设备信息
```

---

## 十、常见问题与解决方案

### 10.1 设备离线检测

| 问题 | 原因 | 解决 |
|------|------|------|
| 设备突然离线 | WiFi 断开/断电 | 心跳超时检测（60 秒） |
| 错过上线消息 | 主机后启动 | 主动发 DISCOVER 广播 |
| 误判离线 | 网络抖动 | 超时阈值设大一点（60 秒足够） |

### 10.2 消息丢失处理

| 场景 | 处理 |
|------|------|
| 命令丢失 | 用户重试 / 小智重试 / 定期状态同步 |
| 响应丢失 | 不阻塞，主机不等待响应（异步设计） |
| 心跳丢失 | 下一条心跳恢复即可 |

### 10.3 Client ID 冲突

```
错误：两个设备用相同 Client ID
→ Broker 踢掉旧连接
→ 设备不断重连循环

正确：每个设备唯一 Client ID
→ 主机: "xiaozhi_master"
→ 从机: "slave_1", "slave_2" 或用 MAC 地址
```

### 10.4 主题设计避坑

| 错误做法 | 正确做法 | 原因 |
|----------|---------|------|
| 所有设备订阅 `#` | 精确订阅所需主题 | 减少不必要的消息处理 |
| 用中文做主题 | 用英文/数字 | 编码问题可能导致匹配失败 |
| 主题层级太深 | 控制 4-5 层以内 | 可读性和性能平衡 |
| 发布和订阅用同一连接处理 | 分开处理 | 避免消息循环 |

---

## 十一、协议演进路线

### 11.1 当前状态（v1.0）

- 基于 ESP-NOW 协议改造为 MQTT
- 二进制命令包（8 字节）
- 简单的心跳机制
- 手动别名映射

### 11.2 未来升级方向

| 升级项 | 收益 | 成本 |
|--------|------|------|
| TLS 加密 | 防止窃听 | 需要证书，ESP32 资源占用增加 |
| 用户名密码认证 | 防止未授权接入 | 需要管理凭证 |
| 遗嘱消息（LWT） | 精准检测离线 | 连接时配置，改动小 |
| 保留消息（Retained） | 后启动立即获知状态 | 发布时加标志即可 |
| JSON 替代二进制 | 可读性好，易调试 | 带宽增加，解析变慢 |
| MQTT v5.0 | 共享订阅、消息过期 | ESP-IDF 需配置，收益有限 |

### 11.3 推荐优先实施

1. **遗嘱消息** → 改动最小，效果明显
2. **TLS 加密** → 如果部署到云端，必须做
3. **保留消息** → 上线状态用 Retain，简化发现流程
4. **定期状态同步** → 增加 GET_ALL_GPIO 的定时调用

---

## 十二、调试检查清单

### 12.1 连接问题

- [ ] Broker 地址和端口正确
- [ ] 防火墙/安全组放行 1883 端口
- [ ] Client ID 不冲突
- [ ] WiFi 连接正常（ESP32 端）

### 12.2 通信问题

- [ ] 主题拼写一致（大小写敏感）
- [ ] 从机订阅了正确的 cmd 主题
- [ ] 主机订阅了正确的 resp/heartbeat 主题
- [ ] QoS 设置合理（命令用 0 或 1）

### 12.3 设备发现问题

- [ ] 从机上电后发送了 ANNOUNCE_V2
- [ ] 主机收到后正确解析 MAC 地址
- [ ] 别名映射表包含新设备名称
- [ ] DISCOVER 广播能触发从机响应

### 12.4 MQTTX 调试步骤

```
1. 连接到本地 Broker (127.0.0.1:1883)
2. 创建两个连接: 中控主机 (xiaozhi_master) 和 一楼设备 (slave_1)
3. 主机订阅 xiaozhi/iot/resp/#、heartbeat/#、announce/#
4. 从机订阅 xiaozhi/iot/cmd/1、xiaozhi/iot/cmd/broadcast
5. 从机发布心跳到 xiaozhi/iot/heartbeat/AA1122334455
6. 主机发布命令到 xiaozhi/iot/cmd/1 (Hex: 01 01 00 01 00 00 00 00)
7. 验证双向通信正常
```
