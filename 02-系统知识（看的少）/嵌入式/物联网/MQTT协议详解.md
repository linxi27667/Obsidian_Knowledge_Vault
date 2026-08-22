# MQTT协议详解

## 核心概念

- **MQTT** - 消息队列遥测传输协议
- **QoS** - 服务质量等级
- **Topic** - 消息主题(通配符匹配)
- **Broker** - 消息代理服务器

---

## 一、协议基础

### 1.1 MQTT报文类型

```c
// MQTT控制报文类型
#define MQTT_CONNECT      1   // 客户端连接请求
#define MQTT_CONNACK      2   // 连接确认
#define MQTT_PUBLISH      3   // 发布消息
#define MQTT_PUBACK       4   // QoS1发布确认
#define MQTT_PUBREC       5   // QoS2发布收到(step1)
#define MQTT_PUBREL       6   // QoS2发布释放(step2)
#define MQTT_PUBCOMP      7   // QoS2发布完成(step3)
#define MQTT_SUBSCRIBE    8   // 订阅主题
#define MQTT_SUBACK       9   // 订阅确认
#define MQTT_UNSUBSCRIBE  10  // 取消订阅
#define MQTT_UNSUBACK     11  // 取消订阅确认
#define MQTT_PINGREQ      12  // PING请求
#define MQTT_PINGRESP     13  // PING响应
#define MQTT_DISCONNECT   14  // 断开连接

// 固定头
typedef struct {
    uint8_t type_flags;       // 类型(4位) + 标志(4位)
    uint8_t remaining_len[];  // 剩余长度(可变长度编码)
} mqtt_fixed_header_t;

// 剩余长度编码(1-4字节)
int encode_remaining_length(uint8_t *buf, int length) {
    int i = 0;
    do {
        uint8_t byte = length % 128;
        length /= 128;
        if (length > 0) byte |= 0x80;
        buf[i++] = byte;
    } while (length > 0);
    return i;
}

int decode_remaining_length(const uint8_t *buf, int *bytes_read) {
    int multiplier = 1;
    int value = 0;
    int i = 0;
    uint8_t byte;
    do {
        byte = buf[i++];
        value += (byte & 0x7F) * multiplier;
        multiplier *= 128;
    } while (byte & 0x80);
    *bytes_read = i;
    return value;
}
```

---

### 1.2 CONNECT报文

```c
// CONNECT报文构建
typedef struct {
    char client_id[64];
    char username[64];
    char password[64];
    char will_topic[128];
    uint8_t *will_message;
    int will_message_len;
    uint8_t will_qos;
    bool will_retain;
    bool clean_session;
    uint16_t keep_alive;
} mqtt_connect_config_t;

int mqtt_build_connect(uint8_t *buf, mqtt_connect_config_t *config) {
    int offset = 0;

    // 可变头: 协议名 "MQTT"
    buf[offset++] = 0; buf[offset++] = 4;  // 长度
    buf[offset++] = 'M'; buf[offset++] = 'Q';
    buf[offset++] = 'T'; buf[offset++] = 'T';

    // 协议级别
    buf[offset++] = 4;  // MQTT 3.1.1

    // 连接标志
    uint8_t flags = 0;
    if (config->clean_session) flags |= 0x02;
    if (config->will_topic[0]) {
        flags |= 0x04;
        flags |= (config->will_qos & 0x03) << 3;
        if (config->will_retain) flags |= 0x20;
    }
    if (config->password[0]) flags |= 0x40;
    if (config->username[0]) flags |= 0x80;
    buf[offset++] = flags;

    // 保活时间
    buf[offset++] = config->keep_alive >> 8;
    buf[offset++] = config->keep_alive & 0xFF;

    // 载荷: Client ID
    int len = strlen(config->client_id);
    buf[offset++] = len >> 8;
    buf[offset++] = len & 0xFF;
    memcpy(buf + offset, config->client_id, len);
    offset += len;

    // 遗嘱
    if (config->will_topic[0]) {
        len = strlen(config->will_topic);
        buf[offset++] = len >> 8;
        buf[offset++] = len & 0xFF;
        memcpy(buf + offset, config->will_topic, len);
        offset += len;

        buf[offset++] = config->will_message_len >> 8;
        buf[offset++] = config->will_message_len & 0xFF;
        memcpy(buf + offset, config->will_message, config->will_message_len);
        offset += config->will_message_len;
    }

    // 用户名
    if (config->username[0]) {
        len = strlen(config->username);
        buf[offset++] = len >> 8;
        buf[offset++] = len & 0xFF;
        memcpy(buf + offset, config->username, len);
        offset += len;
    }

    // 密码
    if (config->password[0]) {
        len = strlen(config->password);
        buf[offset++] = len >> 8;
        buf[offset++] = len & 0xFF;
        memcpy(buf + offset, config->password, len);
        offset += len;
    }

    return offset;
}
```

---

## 二、QoS机制

### 2.1 QoS等级

```
QoS 0 - 最多一次(At most once)
    发布者 ──PUBLISH──→ Broker
    无确认，可能丢失

QoS 1 - 至少一次(At least once)
    发布者 ──PUBLISH──→ Broker
    发布者 ←──PUBACK─── Broker
    保证到达，可能重复

QoS 2 - 恰好一次(Exactly once)
    发布者 ──PUBLISH──→ Broker
    发布者 ←──PUBREC──── Broker
    发布者 ──PUBREL───→ Broker
    发布者 ←──PUBCOMP─── Broker
    四次握手，保证不重复
```

### 2.2 QoS实现

```c
// QoS状态机
typedef enum {
    QOS2_IDLE,
    QOS2_PUBLISH_SENT,
    QOS2_PUBREC_RECEIVED,
    QOS2_PUBREL_SENT
} qos2_state_t;

typedef struct {
    uint16_t packet_id;
    qos2_state_t state;
    uint32_t timestamp;
    uint8_t *payload;
    int payload_len;
    int retry_count;
} qos2_transaction_t;

// QoS2发送流程
void qos2_publish(qos2_transaction_t *txn, uint16_t packet_id,
                  uint8_t *data, int len) {
    txn->packet_id = packet_id;
    txn->state = QOS2_PUBLISH_SENT;
    txn->timestamp = get_tick();
    txn->payload = data;
    txn->payload_len = len;
    txn->retry_count = 0;

    // 发送PUBLISH
    mqtt_send_publish(packet_id, data, len, 2);
}

// QoS2接收处理
void qos2_handle_packet(qos2_transaction_t *txn, uint8_t type) {
    switch (txn->state) {
        case QOS2_PUBLISH_SENT:
            if (type == MQTT_PUBREC) {
                txn->state = QOS2_PUBREC_RECEIVED;
                mqtt_send_pubrel(txn->packet_id);
                txn->state = QOS2_PUBREL_SENT;
            }
            break;
        case QOS2_PUBREL_SENT:
            if (type == MQTT_PUBCOMP) {
                txn->state = QOS2_IDLE;
                // 事务完成
            }
            break;
    }
}
```

---

## 三、Topic与通配符

### 3.1 Topic匹配

```c
// Topic通配符规则
// + : 匹配单层
// # : 匹配多层(只能在末尾)
//
// 示例:
// sensor/+/temperature  → sensor/room1/temperature ✓
// sensor/#              → sensor/room1/humidity ✓
// #                     → 任何主题 ✓

bool mqtt_topic_match(const char *topic, const char *filter) {
    while (*topic && *filter) {
        if (*filter == '#') return true;      // 匹配所有剩余层级
        if (*filter == '+') {                 // 跳过当前层
            while (*topic && *topic != '/') topic++;
            filter++;
            continue;
        }
        if (*topic != *filter) return false;
        topic++;
        filter++;
    }
    return (*topic == '\0' && *filter == '\0');
}

// Topic层级解析
typedef struct {
    char levels[8][32];
    int count;
} topic_parts_t;

void mqtt_topic_parse(const char *topic, topic_parts_t *parts) {
    parts->count = 0;
    const char *p = topic;
    int idx = 0;

    while (*p && parts->count < 8) {
        if (*p == '/') {
            parts->levels[parts->count][idx] = '\0';
            parts->count++;
            idx = 0;
        } else {
            if (idx < 31) parts->levels[parts->count][idx++] = *p;
        }
        p++;
    }
    parts->levels[parts->count][idx] = '\0';
    parts->count++;
}
```

---

### 3.2 订阅管理

```c
// 订阅表
typedef struct {
    char topic[128];
    uint8_t qos;
    void (*callback)(const char *topic, const uint8_t *data, int len);
} mqtt_subscription_t;

#define MAX_SUBSCRIPTIONS 32
static mqtt_subscription_t subscriptions[MAX_SUBSCRIPTIONS];
static int sub_count = 0;

int mqtt_subscribe_topic(const char *topic, uint8_t qos,
                         void (*cb)(const char *, const uint8_t *, int)) {
    if (sub_count >= MAX_SUBSCRIPTIONS) return -1;

    strcpy(subscriptions[sub_count].topic, topic);
    subscriptions[sub_count].qos = qos;
    subscriptions[sub_count].callback = cb;
    sub_count++;

    // 发送SUBSCRIBE报文
    uint8_t buf[256];
    int len = build_subscribe(buf, topic, qos);
    tcp_send(buf, len);

    return 0;
}

// 消息分发
void mqtt_dispatch(const char *topic, const uint8_t *data, int len) {
    for (int i = 0; i < sub_count; i++) {
        if (mqtt_topic_match(topic, subscriptions[i].topic)) {
            if (subscriptions[i].callback) {
                subscriptions[i].callback(topic, data, len);
            }
        }
    }
}
```

---

## 四、遗嘱消息与保留消息

### 4.1 遗嘱消息(Will)

```c
// 遗嘱消息配置
void mqtt_set_will(mqtt_connect_config_t *config,
                   const char *topic, const char *message,
                   uint8_t qos, bool retain) {
    strcpy(config->will_topic, topic);
    config->will_message = (uint8_t *)message;
    config->will_message_len = strlen(message);
    config->will_qos = qos;
    config->will_retain = retain;
}

// Broker端遗嘱处理
/*
 * 当Broker检测到客户端异常断开(未发送DISCONNECT):
 * 1. 检查该客户端是否设置了遗嘱
 * 2. 如果有，发布遗嘱消息到遗嘱主题
 * 3. 遗嘱消息遵循其QoS和Retain设置
 */
```

---

### 4.2 保留消息(Retain)

```c
// 保留消息：新订阅者立即收到最后一条保留消息
void mqtt_publish_retained(const char *topic, const uint8_t *data,
                           int len, uint8_t qos) {
    // 设置RETAIN标志
    uint8_t flags = 0x01;  // RETAIN bit
    flags |= (qos & 0x03) << 1;

    mqtt_send_publish_with_flags(topic, data, len, flags);
}

// Broker端保留消息存储
typedef struct {
    char topic[128];
    uint8_t *payload;
    int payload_len;
    uint8_t qos;
} retained_msg_t;

#define MAX_RETAINED 64
static retained_msg_t retained_messages[MAX_RETAINED];

void broker_store_retained(const char *topic, const uint8_t *data,
                           int len, uint8_t qos) {
    // 查找已有保留消息
    for (int i = 0; i < MAX_RETAINED; i++) {
        if (strcmp(retained_messages[i].topic, topic) == 0) {
            if (len == 0) {
                // 空载荷删除保留消息
                memset(&retained_messages[i], 0, sizeof(retained_msg_t));
                return;
            }
            // 更新
            free(retained_messages[i].payload);
            retained_messages[i].payload = malloc(len);
            memcpy(retained_messages[i].payload, data, len);
            retained_messages[i].payload_len = len;
            retained_messages[i].qos = qos;
            return;
        }
    }
    // 新增
    for (int i = 0; i < MAX_RETAINED; i++) {
        if (retained_messages[i].topic[0] == '\0') {
            strcpy(retained_messages[i].topic, topic);
            retained_messages[i].payload = malloc(len);
            memcpy(retained_messages[i].payload, data, len);
            retained_messages[i].payload_len = len;
            retained_messages[i].qos = qos;
            return;
        }
    }
}
```

---

## 五、MQTT 5.0新特性

### 5.1 MQTT 5.0改进

```c
// MQTT 5.0新属性
typedef struct {
    // 属性标识
    uint8_t property_id;
    union {
        uint8_t byte_val;
        uint16_t short_val;
        uint32_t int_val;
        struct { char *data; uint16_t len; } binary;
        struct { char *str; uint16_t len; } string;
    };
} mqtt_property_t;

// 主要新增属性
#define PROP_SESSION_EXPIRY      0x11  // 会话过期时间
#define PROP_RECEIVE_MAXIMUM     0x21  // 接收最大值
#define PROP_MAXIMUM_PACKET_SIZE 0x27  // 最大报文大小
#define PROP_TOPIC_ALIAS_MAX     0x22  // 主题别名最大值
#define PROP_USER_PROPERTY       0x26  // 用户属性(键值对)
#define PROP_CONTENT_TYPE        0x03  // 内容类型
#define PROP_RESPONSE_TOPIC      0x08  // 响应主题
#define PROP_CORRELATION_DATA    0x09  // 关联数据

// 请求-响应模式
void mqtt_request(const char *request_topic, const char *response_topic,
                  const uint8_t *data, int len) {
    // 发布请求，附带响应主题和关联数据
    mqtt_property_t props[] = {
        {.property_id = PROP_RESPONSE_TOPIC,
         .string = {response_topic, strlen(response_topic)}},
        {.property_id = PROP_CORRELATION_DATA,
         .binary = {correlation_id, 16}},
    };

    mqtt_publish_with_properties(request_topic, data, len, props, 2);
}
```

---

## 六、MQTT安全

### 6.1 认证与加密

```c
// TLS配置
typedef struct {
    const char *ca_cert;
    const char *client_cert;
    const char *client_key;
    bool verify_server;
} mqtt_tls_config_t;

// MQTT over TLS
void mqtt_connect_secure(const char *host, int port,
                         mqtt_tls_config_t *tls,
                         mqtt_connect_config_t *config) {
    // 1. TLS握手
    tls_context_t *ctx = tls_init();
    tls_load_ca_cert(ctx, tls->ca_cert);
    tls_load_client_cert(ctx, tls->client_cert, tls->client_key);
    tls_connect(ctx, host, port);

    // 2. MQTT连接(通过TLS通道)
    uint8_t buf[512];
    int len = mqtt_build_connect(buf, config);
    tls_send(ctx, buf, len);

    // 3. 等待CONNACK
    len = tls_recv(ctx, buf, sizeof(buf));
    mqtt_parse_connack(buf, len);
}

// MQTT增强认证(5.0)
void mqtt_enhanced_auth(const char *auth_method,
                        const uint8_t *auth_data, int len) {
    // AUTH报文交换
    mqtt_send_auth(auth_method, auth_data, len);
}
```

---

## 附录：MQTT版本对比

| 特性 | MQTT 3.1.1 | MQTT 5.0 |
|------|-----------|----------|
| QoS | 0/1/2 | 0/1/2 |
| 遗嘱消息 | 支持 | 增强 |
| 保留消息 | 支持 | 支持 |
| 请求-响应 | 不支持 | 支持 |
| 用户属性 | 不支持 | 支持 |
| 会话过期 | 不支持 | 支持 |
| 认证 | 用户名密码 | 增强认证 |
| 主题别名 | 不支持 | 支持 |

---

## 相关链接

- [[物联网协议]] - 物联网协议概览
- [[物联网平台]] - IoT平台接入
- [[TCP-IP协议栈]] - TCP/IP基础
- [[物联网安全]] - TLS与安全
