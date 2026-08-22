---
title: MQTT 协议学习笔记
tags: [MQTT, IoT, 物联网, ESP32, 协议]
created: 2026-05-04
---

# MQTT 协议学习笔记

## 一、MQTT 是什么

**用生活中的例子理解 MQTT：**

想象你们公司有一个"公告板"（这个公告板就是 **Broker**）。

- 小张（一个**发布者**）写了一张便条贴在公告板的"午餐通知"栏（这个栏就是 **Topic 主题**）
- 小李和小王（两个**订阅者**）每天去看"午餐通知"栏，看到了小张贴的便条
- 小张不知道谁看了便条，小李小王也不知道是谁贴的
- 他们**互不认识，互不直接联系**，全靠公告板中转

这就是 MQTT 的核心思想：**所有人把消息交给中间人，中间人根据分类转发给感兴趣的人**。

### 1.1 关键角色（谁是谁）

| 角色 | 生活中的类比 | 小智项目中的实际设备 |
|------|-------------|-------------------|
| **Broker**（代理） | 公告板 / 邮局 | Mosquitto 服务器（跑在你的电脑上） |
| **Publisher**（发布者） | 写便条的人 | ESP32 主控或从设备发送消息 |
| **Subscriber**（订阅者） | 看便条的人 | ESP32 主控或从设备接收消息 |
| **Topic**（主题） | 便条的分类栏 | 像 `xiaozhi/iot/cmd/1` 这样的路径 |

### 1.2 谁发布？谁订阅？

**在小智项目中：**

```
Mosquitto Broker（邮局/公告板）
    ┌─────────────┬──────────────┬──────────────┐
    │             │              │              │
 ESP32主控      一楼设备        二楼设备       三楼设备
 (在客厅)      (在一楼)        (在二楼)       (在三楼)

主控发布命令：
  主控 → Broker: "一楼设备，请开灯！" (Topic: xiaozhi/iot/cmd/1)
       → 只有订阅了这个主题的一楼设备能收到

一楼设备响应：
  一楼设备 → Broker: "收到，灯已打开" (Topic: xiaozhi/iot/resp/1)
          → 主控订阅了这个主题，所以主控能收到

二楼设备：
  二楼也连接了 Broker，但它没订阅 cmd/1，所以收不到一楼的命令
  它只关心自己的 cmd/2 和广播命令
```

**总结：**
- 主控既能**发布**（发命令）也能**订阅**（收响应）
- 从设备也是既能**发布**（发响应）也能**订阅**（收命令）
- 它们之间**不直接对话**，都通过 Mosquitto Broker 中转
- 每个设备只订阅**自己关心**的主题，不关心的消息收不到

### 1.3 MQTT 核心特点

| 特点 | 说明 | 类比 |
|------|------|------|
| 轻量 | 最小报文仅 **2 字节** | 像发短信，字越少越省流量 |
| 异步 | 发布者和订阅者不需要同时在线 | 像发微信，对方不在也能发 |
| 一对多 | 一条消息可被多个订阅者接收 | 像群发公告 |
| QoS | 三种消息质量等级 | 像快递：普通/挂号/保价 |
| 持久化 | 遗嘱消息 + 保留消息机制 | 像"人不在自动发的自动回复" |

---

## 三、MQTT 报文格式

### 3.1 固定头部（Fixed Header）

```
Byte 1: [消息类型(4bit)] [标志位(4bit)]
Byte 2+: [剩余长度(可变长度编码)]
```

### 3.2 消息类型（15 种）

| 类型 | 值 | 方向 | 说明 |
|------|-----|------|------|
| **CONNECT** | 1 | C → S | 客户端连接请求 |
| **CONNACK** | 2 | S → C | 连接确认 |
| **PUBLISH** | 3 | 双向 | 发布消息 |
| **PUBACK** | 4 | 双向 | QoS 1 确认 |
| **PUBREC** | 5 | 双向 | QoS 2 第一步确认 |
| **PUBREL** | 6 | 双向 | QoS 2 第二步确认 |
| **PUBCOMP** | 7 | 双向 | QoS 2 完成确认 |
| **SUBSCRIBE** | 8 | C → S | 订阅请求 |
| **SUBACK** | 9 | S → C | 订阅确认 |
| **UNSUBSCRIBE** | 10 | C → S | 取消订阅 |
| **UNSUBACK** | 11 | S → C | 取消订阅确认 |
| **PINGREQ** | 12 | C → S | 心跳请求 |
| **PINGRESP** | 13 | S → C | 心跳响应 |
| **DISCONNECT** | 14 | C → S | 断开连接 |

### 3.3 可变长度编码

MQTT 用 1-4 字节表示剩余长度（最大 256MB）：

```
值 0-127：    1 字节   (0xxxxxxx)
值 128-16383：2 字节   (1xxxxxxx 0xxxxxxx)
值 16384-...：3-4 字节
```

每个字节最高位（bit 7）= 1 表示还有后续字节。

---

## 四、MQTT 连接流程

### 4.1 完整连接生命周期

```
客户端                            Broker
  │                                 │
  │── CONNECT ───────────────────→│
  │   Client ID: "xiaozhi_master"  │
  │   Clean Session: true          │
  │   Keep Alive: 240              │
  │   Username/Password (可选)      │
  │                                 │
  │←── CONNACK ──────────────────│
  │   Return Code: 0 (成功)        │
  │                                 │
  │── SUBSCRIBE ─────────────────→│
  │   Topic: "xiaozhi/iot/cmd/#"   │
  │   QoS: 0                       │
  │                                 │
  │←── SUBACK ───────────────────│
  │   Granted QoS: 0               │
  │                                 │
  │── PUBLISH ───────────────────→│
  │   Topic: "xiaozhi/iot/announce"│
  │   Payload: {"online": true}    │
  │                                 │
  │←── PUBLISH ──────────────────│  (收到其他设备消息)
  │   Topic: "xiaozhi/iot/cmd/1"   │
  │   Payload: {"cmd": 0x11}       │
  │                                 │
  │── PINGREQ ───────────────────→│  (Keep Alive 间隔)
  │←── PINGRESP ─────────────────│
  │                                 │
  │── DISCONNECT ────────────────→│
  │                                 │
```

### 4.2 CONNECT 报文参数

| 参数 | 说明 | 小智项目值 |
|------|------|----------|
| Client ID | 客户端唯一标识 | `"xiaozhi_master"` |
| Clean Session | 是否清除旧会话 | `true`（不持久化） |
| Keep Alive | 心跳间隔（秒） | `240` |
| Username | 认证用户名 | 无 |
| Password | 认证密码 | 无 |
| Will Topic | 遗嘱主题 | 可选 |
| Will Message | 遗嘱消息 | 可选 |

### 4.3 CONNACK 返回码

| 返回码 | 含义 | 处理方式 |
|--------|------|----------|
| 0 | 连接成功 | 正常继续 |
| 1 | 协议版本不支持 | 检查 MQTT 版本 |
| 2 | Client ID 被拒绝 | 更换 Client ID |
| 3 | Broker 不可用 | 重试连接 |
| 4 | 用户名/密码错误 | 检查认证信息 |
| 5 | 未授权 | 检查 ACL 权限 |

---

## 五、Topic 主题系统

### 5.1 主题格式

```
xiaozhi/iot/cmd/broadcast     ← 广播命令
xiaozhi/iot/cmd/1             ← 发送给设备 1
xiaozhi/iot/resp/abcdef123    ← 设备 abcdef123 的响应
xiaozhi/iot/heartbeat/1       ← 设备 1 的心跳
xiaozhi/iot/announce          ← 设备上线广播
```

### 5.2 通配符（Wildcard）

MQTT 的 `#` 和 `+` 是 **订阅时的模式匹配**，不是发布时的。

| 通配符 | 含义 | 限制 |
|--------|------|------|
| `+` | 单层通配（匹配一个层级） | 可以用在任意位置 |
| `#` | 多层通配（匹配剩余所有层级） | **只能在末尾** |

#### 5.2.1 核心原理：发布地址 vs 订阅模式

这是最容易混淆的点：

| 动作 | Topic 字段的作用 | 类比 |
|------|-----------------|------|
| **发布（Publish）** | 消息的**目标地址**，精确路径 | 快递包裹上的收件地址 |
| **订阅（Subscribe）** | **匹配规则**，不是地址 | "我要收所有到 XX 区的快递" |

**关键结论：** 发布和订阅是两套独立的逻辑。发布者不需要知道谁在订阅，订阅者也不需要知道谁在发布。

```
发布: xiaozhi/test          ← 这是一条消息的"目的地"
订阅: xiaozhi/#            ← 这是一个"筛选规则"
                                规则含义: "xiaozhi/ 后面无论是什么我都想要"
匹配结果: ✅ 匹配成功
```

#### 5.2.2 `#` 多层通配详解

`#` 匹配从它所在位置开始到末尾的**所有层级**（包括零个层级）。

| 订阅模式 | 匹配 | 不匹配 | 原因 |
|----------|------|--------|------|
| `xiaozhi/#` | `xiaozhi/test` | `other/test` | 必须以 `xiaozhi/` 开头 |
| `xiaozhi/#` | `xiaozhi/iot/cmd/1` | `xiaozhi` | 至少要有一层（带斜杠） |
| `xiaozhi/iot/#` | `xiaozhi/iot/anything/goes` | `xiaozhi/cmd/1` | 必须从 `iot/` 开始 |
| `#` | 任何主题 | 无 | 匹配所有（慎用） |

**注意：** `xiaozhi/#` **不匹配** 纯 `xiaozhi`（没有斜杠后缀）。如果需要包含自身，订阅两个：`xiaozhi` + `xiaozhi/#`。

#### 5.2.3 `+` 单层通配详解

`+` 只匹配**恰好一个层级**（两层之间的一个段）。

| 订阅模式 | 匹配 | 不匹配 | 原因 |
|----------|------|--------|------|
| `xiaozhi/iot/+/1` | `xiaozhi/iot/cmd/1` | `xiaozhi/iot/cmd/b/1` | `+` 只匹配一层 |
| `xiaozhi/iot/+` | `xiaozhi/iot/cmd` | `xiaozhi/iot/cmd/1` | 多了 `/1` |
| `+/iot/#` | `xiaozhi/iot/cmd/1` | `abc/def/iot/cmd` | 第一层必须是 `iot` 前面那段 |
| `xiaozhi/+/cmd/#` | `xiaozhi/iot/cmd/1` | `xiaozhi/cmd/1` | 中间必须有一层 |

#### 5.2.4 通配符匹配规则图解

```
发布主题:  xiaozhi /  iot  /  cmd  /   1
层级:       [0]      [1]     [2]     [3]

订阅 xiaozhi/iot/#       → 从 [2] 开始往后全匹配    ✅
订阅 xiaozhi/iot/cmd/+   → [3] 位置用 + 匹配       ✅
订阅 xiaozhi/+/cmd/1     → [1] 位置用 + 匹配       ✅
订阅 xiaozhi/+/+/1       → [1][2] 各用 + 匹配      ✅
订阅 xiaozhi/+/cmd/#     → [1] 用 +，[2]后 用 #    ✅
订阅 +/+/+/+             → 恰好 4 层               ✅
订阅 xiaozhi/+/1         → 只有 3 层，发布有 4 层  ❌
```

#### 5.2.5 特殊符号规则

| 规则 | 说明 |
|------|------|
| `#` 只能在末尾 | `xiaozhi/#/cmd` ❌ 非法 |
| `+` 必须在层级边界 | `xiaozhi/iot+` ❌ 必须是 `xiaozhi/iot/+` |
| `$` 开头的主题 | `$SYS/` 等系统主题，`#` 不匹配，需显式订阅 |
| `/` 分隔层级 | 连续 `//` 也算一层（空字符串层） |
| 主题大小写敏感 | `Xiaozhi` ≠ `xiaozhi` |

#### 5.2.6 实战对照表（小智项目）

| 设备角色 | 订阅的主题 | 收到的消息示例 | 为什么能收到 |
|----------|-----------|---------------|-------------|
| 中控主机 | `xiaozhi/iot/resp/+` | `xiaozhi/iot/resp/AA1122` | `+` 匹配 MAC 地址那层 |
| 中控主机 | `xiaozhi/iot/heartbeat/+` | `xiaozhi/iot/heartbeat/1` | `+` 匹配设备 ID |
| 中控主机 | `xiaozhi/iot/announce/+` | `xiaozhi/iot/announce/BB2233` | `+` 匹配 MAC 地址 |
| 一楼设备 | `xiaozhi/iot/cmd/1` | `xiaozhi/iot/cmd/1` | 精确匹配 |
| 一楼设备 | `xiaozhi/iot/cmd/broadcast` | `xiaozhi/iot/cmd/broadcast` | 精确匹配 |
| MQTTX 调试 | `xiaozhi/#` | 所有 xiaozhi 开头的消息 | `#` 通配全部 |

### 5.3 主题设计最佳实践

```
/{项目}/{类型}/{动作}/{设备ID}

小智项目：
/xiaozhi/iot/cmd/{device_id}      ← 命令
/xiaozhi/iot/resp/{device_id}     ← 响应
/xiaozhi/iot/heartbeat/{device_id}← 心跳
/xiaozhi/iot/announce/{device_id} ← 上线通知
```

---

## 六、QoS 服务质量等级

### 6.1 三个等级对比

| QoS | 名称 | 保证 | 报文数 | 适用场景 |
|-----|------|------|--------|----------|
| **0** | At Most Once | 最多一次，可能丢失 | 1 (PUBLISH) | 传感器周期数据、心跳 |
| **1** | At Least Once | 至少一次，可能重复 | 2 (PUBLISH + PUBACK) | 开关命令、配置 |
| **2** | Exactly Once | 恰好一次，不丢不重 | 4 (PUBLISH + PUBREC + PUBREL + PUBCOMP) | 关键操作（支付、安全） |

### 6.2 QoS 流程

```
QoS 0 (最多一次):
  发布者 ──PUBLISH──→ Broker ──PUBLISH──→ 订阅者
  (发完就不管了)

QoS 1 (至少一次):
  发布者 ──PUBLISH──→ Broker ──PUBLISH──→ 订阅者
  发布者 ←─PUBACK─── Broker ←─PUBACK─── 订阅者
  (没收到 PUBACK 就重发)

QoS 2 (恰好一次):
  发布者 ──PUBLISH──→ Broker ──PUBLISH──→ 订阅者
  发布者 ←─PUBREC─── Broker ←─PUBREC─── 订阅者
  发布者 ──PUBREL──→ Broker ──PUBREL──→ 订阅者
  发布者 ←─PUBCOMP─ Broker ←─PUBCOMP─ 订阅者
  (四次握手保证不重不漏)
```

### 6.3 小智项目 QoS 选择

```c
// 命令和响应：QoS 0（足够快速，丢了重发机制兜底）
// 心跳：QoS 0（周期发送，丢一条无所谓）
// 上线通知：QoS 1（确保被收到）
// 广播命令：QoS 0（实时性优先）
```

---

## 七、重要特性

### 7.1 保留消息（Retained Message）

```
发布者发送: PUBLISH(topic="sensor/temp", retained=true, payload=25.6)
            ↓
        Broker 保存这条消息
            ↓
新订阅者订阅 → 立即收到 25.6（即使发布者已经离线）
```

**用途**：存储设备最新状态，新设备加入时立即可知当前状态。

```c
// 小智项目中可用于：
// 设备上线时发布保留消息，其他设备立即知道它在线
PUBLISH("xiaozhi/iot/announce/1", retained=true, {"device":"一楼设备","online":true})
```

### 7.2 遗嘱消息（Last Will / LWT）

```
客户端连接时注册:
  Will Topic: "xiaozhi/iot/status/1"
  Will Message: {"online": false}
  Will QoS: 1
  Will Retained: true
```

- 客户端**异常断开**时，Broker 自动发布遗嘱消息
- 正常 DISCONNECT 不会发布
- 用于检测设备离线

```c
// ESP-IDF 配置示例
esp_mqtt_client_config_t mqtt_cfg = {
    .session.last_will.topic = "xiaozhi/iot/status/xiaozhi_master",
    .session.last_will.msg = "{\"online\":false}",
    .session.last_will.qos = 1,
    .session.last_will.retain = true,
};
```

### 7.3 Clean Session vs Persistent Session

| | Clean Session = true | Clean Session = false |
|------|------|------|
| 重连后 | 旧消息全部丢弃 | 保留订阅和未确认消息 |
| Broker 存储 | 不存储 | 存储（占用资源） |
| 适用场景 | 实时控制、不需要历史 | 需要消息不丢失 |
| 小智项目 | ✅ 推荐 | ❌ 不需要 |

---

## 八、MQTT v3.1.1 vs v5.0

| 特性 | v3.1.1 | v5.0 |
|------|--------|------|
| 发布年份 | 2014 | 2019 |
| 原因码 | 单字节返回码 | 详细原因码+字符串 |
| 共享订阅 | ❌ | ✅ `$share/group/topic` |
| 主题别名 | ❌ | ✅（减少带宽） |
| 消息过期 | ❌ | ✅（Message Expiry） |
| 请求/响应 | ❌ | ✅（Response Topic） |
| 用户属性 | ❌ | ✅（自定义 Key-Value） |
| ESP-IDF 支持 | ✅ 默认 | ✅ 需配置 |

**建议**：ESP32 用 v3.1.1 足够，v5.0 的新特性在嵌入式场景下用处不大。

---

## 九、ESP-IDF MQTT 客户端

### 9.1 基本配置

```c
#include "mqtt_client.h"

static esp_mqtt_client_handle_t mqtt_client = NULL;

void mqtt_app_start(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://192.168.1.100:1883",
        .credentials.client_id = "xiaozhi_master",
        .session.keepalive = 240,
        .network.disable_auto_reconnect = false,
        .session.reconnect_timeout_ms = 60000,
    };

    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
}
```

### 9.2 事件处理

```c
static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                                int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT 连接成功");
        // 订阅主题
        esp_mqtt_client_subscribe(mqtt_client, "xiaozhi/iot/cmd/#", 0);
        break;

    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT 断开连接");
        break;

    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "收到消息: topic=%.*s, data=%.*s",
                 event->topic_len, event->topic,
                 event->data_len, event->data);
        // 处理收到的消息
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGD(TAG, "消息发布成功, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGD(TAG, "订阅成功, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_BEFORE_CONNECT:
        ESP_LOGI(TAG, "准备连接...");
        break;

    default:
        break;
    }
}
```

### 9.3 发布和订阅

```c
// 发布消息（QoS 0）
esp_mqtt_client_publish(mqtt_client,
    "xiaozhi/iot/resp/xiaozhi_master",
    "{\"status\":\"ok\"}", 0, 0, 0);

// 发布消息（QoS 1）
esp_mqtt_client_publish(mqtt_client,
    "xiaozhi/iot/announce/xiaozhi_master",
    "{\"device\":\"xiaozhi_master\",\"online\":true}", 0, 1, 1);

// 订阅主题
esp_mqtt_client_subscribe(mqtt_client, "xiaozhi/iot/cmd/#", 0);

// 取消订阅
esp_mqtt_client_unsubscribe(mqtt_client, "xiaozhi/iot/cmd/#");
```

---

## 十、Mosquitto Broker 管理

### 10.1 Docker 部署

```bash
# 启动
docker run -d --name mosquitto -p 1883:1883 -p 9001:9001 eclipse-mosquitto

# 带配置文件启动（推荐）
mkdir -p /mosquitto/config /mosquitto/data /mosquitto/log
# 创建配置文件后：
docker run -d --name mosquitto \
  -p 1883:1883 -p 9001:9001 \
  -v /mosquitto/config:/mosquitto/config \
  -v /mosquitto/data:/mosquitto/data \
  -v /mosquitto/log:/mosquitto/log \
  eclipse-mosquitto

# 停止 / 启动 / 删除
docker stop mosquitto
docker start mosquitto
docker rm mosquitto
```

### 10.2 mosquitto.conf 配置示例

```conf
# 监听端口
listener 1883
protocol mqtt

# WebSocket 端口
listener 9001
protocol websockets

# 允许匿名（开发用，生产环境应该关闭）
allow_anonymous true

# 持久化
persistence true
persistence_location /mosquitto/data/

# 日志
log_dest file /mosquitto/log/mosquitto.log
log_type all
```

### 10.3 命令行工具

```bash
# 订阅
mosquitto_sub -h 127.0.0.1 -p 1883 -t "xiaozhi/iot/#" -v

# 发布
mosquitto_pub -h 127.0.0.1 -p 1883 -t "xiaozhi/iot/cmd/broadcast" -m '{"cmd":0x30}'

# 带用户名密码
mosquitto_sub -h 127.0.0.1 -u admin -P password -t "topic"

# 保留消息
mosquitto_pub -h 127.0.0.1 -t "sensor/temp" -m "25.6" -r

# QoS 1
mosquitto_pub -h 127.0.0.1 -t "cmd/open" -m "1" -q 1

# 查看 Broker 状态
mosquitto_sub -h 127.0.0.1 -t '$SYS/broker/#' -v
```

---

## 十一、小智项目 MQTT 协议设计

### 11.1 主题规划

```
xiaozhi/iot/
├── cmd/                    ← 命令（主控 → 从设备）
│   ├── broadcast           ← 广播命令（所有设备）
│   ├── 1                   ← 发送给一楼设备
│   ├── 2                   ← 发送给二楼设备
│   └── 3                   ← 发送给三楼设备
├── resp/                   ← 响应（从设备 → 主控）
│   ├── {mac地址}           ← 按 MAC 地址区分
├── heartbeat/              ← 心跳
│   ├── 1                   ← 一楼设备心跳
│   ├── 2                   ← 二楼设备心跳
│   └── 3                   ← 三楼设备心跳
├── announce/               ← 上线通知
│   ├── {mac地址}           ← 按 MAC 地址区分
└── status/                 ← 状态（遗嘱消息主题）
```

### 11.2 命令格式

```c
// JSON 格式命令
{
    "cmd": 0x11,            // 命令类型
    "data": {               // 命令参数
        "gpio": 5,
        "level": 1
    }
}

// 命令类型定义
IOT_CMD_SET_GPIO = 0x01           // 设置 GPIO
IOT_CMD_GET_GPIO = 0x02           // 查询 GPIO
IOT_CMD_HEARTBEAT = 0x04          // 心跳
IOT_CMD_DISCOVER = 0x06           // 设备发现
IOT_CMD_ANNOUNCE_V2 = 0x08        // 上线通知 V2
IOT_CMD_SET_SERVO = 0x10          // 舵机控制
IOT_CMD_SET_LIGHT = 0x11          // 灯光控制
IOT_CMD_SET_RELAY = 0x12          // 继电器控制
IOT_CMD_BROADCAST_ALL_OFF = 0x30  // 全关
IOT_CMD_BROADCAST_ALL_ON = 0x31   // 全开
IOT_CMD_EMERGENCY = 0x34          // 紧急模式
```

### 11.3 设备发现流程

```
1. 从设备上电 → 连接 MQTT Broker
2. 从设备发布 ANNOUNCE_V2:
   Topic: xiaozhi/iot/announce/{mac}
   Payload: {"device_id":1, "name":"一楼设备", "gpios":[...]}

3. 主控收到 → 添加到设备列表
4. 主控定时检查心跳，超时标记离线
```

---

## 十二、调试技巧

### 12.1 串口日志分析

```
// 正常连接日志：
I mqtt_client: MQTT_EVENT_CONNECTED
I mqtt_client: MQTT_EVENT_SUBSCRIBED, msg_id=12345
I iot_ctrl: 设备发现: 一楼设备 (ID=1)

// 异常断开：
W mqtt_client: MQTT_EVENT_DISCONNECTED
E mqtt_client: MQTT publish failed

// 连接失败：
E mqtt_client: MQTT_EVENT_ERROR
E mqtt_client: esp_mqtt_client_publish message len=0
```

### 12.2 MQTTX 调试步骤

```
1. 连接到本地 Broker (127.0.0.1:1883)
2. 订阅 xiaozhi/iot/#
3. ESP32 上电 → 看到 ANNOUNCE 消息
4. 手动发布命令测试:
   Topic: xiaozhi/iot/cmd/broadcast
   Payload: {"cmd": 48}  ← 全关命令 (0x30)
5. 观察从设备响应消息
```

### 12.3 Wireshark 抓包

```
1. 选择 WiFi 网卡
2. 过滤: tcp.port == 1883
3. 右键 → Decode As → MQTT
4. 看到 CONNECT、PUBLISH、SUBSCRIBE 等报文
```

---

## 十三、常见问题

### Q: 消息丢了怎么办？

- 提高 QoS 等级（0→1→2）
- 应用层加确认机制（收到命令回复 ACK）
- 小智项目中：从设备收到命令后发布 resp 确认

### Q: 重复消息怎么处理？

- QoS 1 可能重复，需要应用层去重
- 给每条命令加唯一 ID（timestamp 或 UUID）
- 记录最近处理过的命令 ID

### Q: 多个设备用同一个 Client ID 会怎样？

- Broker 会踢掉前一个连接（"Client ID already in use"）
- 每个设备必须有唯一的 Client ID
- 小智项目：主控用 `xiaozhi_master`，从设备用 MAC 地址

### Q: Broker 挂了怎么办？

- ESP32 会自动重连（`reconnect_timeout_ms` 控制间隔）
- 生产环境用高可用 Broker（如 EMQX 集群）
- 开发阶段 Docker 容器挂了解决：`docker start mosquitto`

### Q: 消息太大发不出去？

- MQTT 默认最大消息 256KB（Mosquitto 默认 10MB）
- ESP-IDF 默认 `out_buffer_size` = 1024 字节
- 解决：增大 `mqtt_cfg.network.out_buffer_size`

---

## 十四、MQTTX 实操记录

### 14.1 为什么需要 MQTTX

没有 ESP32 开发板时，用 MQTTX 模拟所有设备角色，验证协议流程。

### 14.2 连接配置

| 连接名称 | Client ID | 用途 |
|----------|-----------|------|
| 中控主机 | `xiaozhi_master` | 模拟主控端 |
| 一楼设备 | `slave_1` | 模拟从设备 |
| 二楼设备 | `slave_2` | 模拟从设备（可选） |
| 三楼设备 | `slave_3` | 模拟从设备（可选） |

全部连接 `127.0.0.1:1883`，无需用户名密码。

### 14.3 订阅策略

**中控主机订阅：**
- `xiaozhi/iot/resp/#` — 接收所有设备响应
- `xiaozhi/iot/heartbeat/#` — 接收所有设备心跳
- `xiaozhi/iot/announce/#` — 接收设备上线通知

**从设备订阅：**
- `xiaozhi/iot/cmd/{设备ID}` — 接收给自己的命令（如 `cmd/1`）
- `xiaozhi/iot/cmd/broadcast` — 接收广播命令

### 14.4 消息格式

**发布文本消息：** 底部格式选 `Plaintext`

**发布二进制命令（Hex 格式）：** 底部格式选 `Hex`，输入空格分隔的十六进制：

```
06 00 00 00 00 00 00 00    ← DISCOVER 命令 (0x06)
04 00 00 00 00 00 00 00    ← HEARTBEAT 命令 (0x04)
01 01 00 01 00 00 00 00    ← SET_GPIO: device=1, gpio=0, level=1
10 01 00 180 00 00 00 00   ← SET_SERVO: device=1, servo=0, angle=180
30 00 00 00 00 00 00 00    ← BROADCAST_ALL_OFF (0x30)
```

### 14.5 完整测试流程

```
步骤1: 创建连接
  → 中控主机 (xiaozhi_master) 连接 ✅
  → 一楼设备 (slave_1) 连接 ✅

步骤2: 配置订阅
  → 中控主机订阅 xiaozhi/iot/resp/#、heartbeat/#、announce/#
  → 一楼设备订阅 xiaozhi/iot/cmd/1、xiaozhi/iot/cmd/broadcast

步骤3: 模拟设备发现
  → 中控主机发布: xiaozhi/iot/cmd/broadcast, Hex: 06 00 00 00...
  → 一楼设备收到发现命令 ✅

步骤4: 模拟设备响应
  → 一楼设备发布: xiaozhi/iot/heartbeat/AA1122334455, Hex: 04 00 00...
  → 中控主机收到心跳 ✅

步骤5: 模拟 GPIO 控制
  → 中控主机发布: xiaozhi/iot/cmd/1, Hex: 01 01 00 01...
  → 一楼设备收到开灯命令 ✅
  → 一楼设备发布: xiaozhi/iot/resp/AA1122334455, Hex: 05 01 00 01...
  → 中控主机收到响应 ✅
```

### 14.6 验证清单

- [ ] 两个连接都显示绿色在线
- [ ] 一楼设备发消息，中控主机能收到
- [ ] 中控主机发消息到 `cmd/1`，一楼设备能收到
- [ ] 一楼设备发消息到 `cmd/2`，一楼设备**收不到**（主题不匹配）
- [ ] Hex 格式能正确收发二进制命令
