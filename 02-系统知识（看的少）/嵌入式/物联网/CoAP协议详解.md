# CoAP协议详解

## 核心概念

- **CoAP** - 受限应用协议(Constrained Application Protocol)
- **RESTful** - 资源导向架构
- **DTLS** - 数据报传输层安全
- **观察(Observe)** - 资源变更通知

---

## 一、协议基础

### 1.1 CoAP报文格式

```c
// CoAP报文头(4字节)
typedef struct {
    uint8_t  ver_t_tkl;      // 版本(2) + 类型(2) + Token长度(4)
    uint8_t  code;           // 方法/响应码
    uint16_t message_id;     // 消息ID
} coap_header_t;

// CoAP版本
#define COAP_VERSION 1

// 消息类型
#define COAP_CON  0  // 确认(需要ACK)
#define COAP_NON  1  // 非确认
#define COAP_ACK  2  // 确认
#define COAP_RST  3  // 重置

// 方法码
#define COAP_EMPTY    0x00
#define COAP_GET      0x01
#define COAP_POST     0x02
#define COAP_PUT      0x03
#define COAP_DELETE   0x04

// 响应码 (class.detail)
#define COAP_CREATED           0x41  // 2.01
#define COAP_DELETED           0x42  // 2.02
#define COAP_VALID             0x43  // 2.03
#define COAP_CHANGED           0x44  // 2.04
#define COAP_CONTENT           0x45  // 2.05
#define COAP_BAD_REQUEST       0x80  // 4.00
#define COAP_UNAUTHORIZED      0x81  // 4.01
#define COAP_NOT_FOUND         0x84  // 4.04
#define COAP_METHOD_NOT_ALLOW  0x85  // 4.05
#define COAP_INTERNAL_ERROR    0xA0  // 5.00

// CoAP选项号
#define COAP_OPT_IF_MATCH      1
#define COAP_OPT_URI_HOST      3
#define COAP_OPT_ETAG          4
#define COAP_OPT_IF_NONE_MATCH 5
#define COAP_OPT_URI_PORT      7
#define COAP_OPT_LOCATION_PATH 8
#define COAP_OPT_URI_PATH      11
#define COAP_OPT_CONTENT_FMT  12
#define COAP_OPT_MAX_AGE       14
#define COAP_OPT_URI_QUERY     15
#define COAP_OPT_ACCEPT        17
#define COAP_OPT_LOCATION_QUERY 20
#define COAP_OPT_BLOCK2        23
#define COAP_OPT_BLOCK1        27
#define COAP_OPT_SIZE2         28
#define COAP_OPT_PROXY_URI    35
#define COAP_OPT_PROXY_SCHEME  39
#define COAP_OPT_SIZE1         60

// 内容格式
#define COAP_FMT_TEXT_PLAIN    0
#define COAP_FMT_APP_LINK      40
#define COAP_FMT_APP_XML       41
#define COAP_FMT_APP_OCTET     42
#define COAP_FMT_APP_JSON      50
#define COAP_FMT_APP_CBOR      60
```

---

### 1.2 CoAP报文构建

```c
// CoAP消息构建
typedef struct {
    coap_header_t header;
    uint8_t token[8];
    int token_len;

    // 选项
    struct {
        uint16_t number;
        uint8_t *value;
        int value_len;
    } options[16];
    int option_count;

    // 载荷
    uint8_t *payload;
    int payload_len;
} coap_message_t;

int coap_build_message(uint8_t *buf, coap_message_t *msg) {
    int offset = 0;

    // 头部
    buf[offset++] = (COAP_VERSION << 6) |
                    ((msg->header.ver_t_tkl & 0x30) >> 2) |
                    (msg->token_len & 0x0F);
    buf[offset++] = msg->header.code;
    buf[offset++] = msg->header.message_id >> 8;
    buf[offset++] = msg->header.message_id & 0xFF;

    // Token
    if (msg->token_len > 0) {
        memcpy(buf + offset, msg->token, msg->token_len);
        offset += msg->token_len;
    }

    // 选项(按编号排序，使用增量编码)
    uint16_t prev_number = 0;
    for (int i = 0; i < msg->option_count; i++) {
        uint16_t delta = msg->options[i].number - prev_number;
        int len = msg->options[i].value_len;

        // 编码选项头
        if (delta < 13 && len < 13) {
            buf[offset++] = (delta << 4) | len;
        } else if (delta < 269 && len < 13) {
            buf[offset++] = (13 << 4) | len;
            buf[offset++] = delta - 13;
        } else {
            buf[offset++] = (14 << 4) | len;
            buf[offset++] = (delta - 269) >> 8;
            buf[offset++] = (delta - 269) & 0xFF;
        }

        // 选项值
        if (len > 0) {
            memcpy(buf + offset, msg->options[i].value, len);
            offset += len;
        }

        prev_number = msg->options[i].number;
    }

    // 载荷标记
    if (msg->payload_len > 0) {
        buf[offset++] = 0xFF;  // 载荷标记
        memcpy(buf + offset, msg->payload, msg->payload_len);
        offset += msg->payload_len;
    }

    return offset;
}
```

---

## 二、CoAP传输

### 2.1 可靠传输(CON)

```c
// CON消息传输(指数退避)
typedef struct {
    uint16_t message_id;
    coap_message_t *msg;
    uint32_t timeout_ms;
    int retransmit_count;
    uint32_t last_send;
    bool ack_received;
} coap_pending_t;

#define COAP_ACK_TIMEOUT_MS    2000
#define COAP_ACK_RANDOM_FACTOR 1.5
#define COAP_MAX_RETRANSMIT    4

void coap_send_con(coap_pending_t *pending, coap_message_t *msg) {
    pending->message_id = msg->header.message_id;
    pending->msg = msg;
    pending->timeout_ms = COAP_ACK_TIMEOUT_MS;
    pending->retransmit_count = 0;
    pending->last_send = get_tick();
    pending->ack_received = false;

    coap_udp_send(msg);
}

bool coap_retransmit_check(coap_pending_t *pending) {
    if (pending->ack_received) return true;

    uint32_t elapsed = get_tick() - pending->last_send;
    if (elapsed >= pending->timeout_ms) {
        if (pending->retransmit_count >= COAP_MAX_RETRANSMIT) {
            return false;  // 超时，放弃
        }

        // 重传
        coap_udp_send(pending->msg);
        pending->retransmit_count++;
        pending->timeout_ms *= 2;  // 指数退避
        pending->last_send = get_tick();
    }
    return true;
}
```

---

### 2.2 分块传输(Block)

```c
// Block选项
typedef struct {
    uint32_t num;    // 块编号
    uint8_t  m;      // 更多块标志
    uint16_t szx;    // 块大小(2^(szx+4))
} coap_block_t;

// 解析Block选项
coap_block_t coap_parse_block(uint32_t value) {
    coap_block_t block;
    block.num = value >> 4;
    block.m = (value >> 3) & 1;
    block.szx = value & 0x07;
    return block;
}

// 块大小
uint16_t coap_block_size(coap_block_t *block) {
    return 1 << (block->szx + 4);  // 16-1024字节
}

// 大数据分块发送
int coap_send_blockwise(const char *uri_path, uint8_t *data, int total_len) {
    uint16_t block_size = 256;  // szx=4
    int num_blocks = (total_len + block_size - 1) / block_size;

    for (int i = 0; i < num_blocks; i++) {
        int offset = i * block_size;
        int len = (total_len - offset > block_size) ? block_size : (total_len - offset);

        coap_message_t msg;
        msg.header.code = (i == 0) ? COAP_POST : COAP_PUT;

        // Block1选项
        uint32_t block_val = (i << 4) | ((i < num_blocks - 1) ? 0x08 : 0) | 4;
        coap_add_option(&msg, COAP_OPT_BLOCK1, (uint8_t *)&block_val, 1);

        msg.payload = data + offset;
        msg.payload_len = len;

        coap_send_con_and_wait(&msg);
    }
    return 0;
}
```

---

## 三、资源发现

### 3.1 CoRE Link Format

```c
// 资源注册
typedef struct {
    char path[64];
    char rt[32];        // 资源类型
    char if_desc[32];   // 接口描述
    uint8_t ct;         // 内容格式
    bool observable;
} coap_resource_t;

// 资源表
coap_resource_t resources[] = {
    {"/sensors/temperature", "temperature", "sensor", COAP_FMT_APP_JSON, true},
    {"/sensors/humidity",    "humidity",    "sensor", COAP_FMT_APP_JSON, true},
    {"/actuators/led",       "led",         "actuator", COAP_FMT_TEXT_PLAIN, false},
};

// .well-known/core 响应
int coap_build_link_format(uint8_t *buf, int max_len) {
    int offset = 0;
    for (int i = 0; i < sizeof(resources)/sizeof(resources[0]); i++) {
        int n = snprintf((char *)buf + offset, max_len - offset,
                         "</%s>;rt=\"%s\";if=\"%s\";ct=%d%s%s",
                         resources[i].path,
                         resources[i].rt,
                         resources[i].if_desc,
                         resources[i].ct,
                         resources[i].observable ? ";obs" : "",
                         (i < sizeof(resources)/sizeof(resources[0]) - 1) ? "," : "");
        offset += n;
    }
    return offset;
}
```

---

## 四、观察(Observe)

### 4.1 观察模式

```c
// 观察注册
typedef struct {
    char path[64];
    uint16_t token;
    uint32_t last_notify_tick;
    uint32_t max_age;
    uint8_t last_data[256];
    int last_data_len;
    uint32_t last_version;
} coap_observer_t;

// 客户端订阅观察
void coap_observe(const char *uri_path) {
    coap_message_t msg;
    msg.header.code = COAP_GET;

    // Observe选项(值=0注册)
    uint8_t observe = 0;
    coap_add_option(&msg, COAP_OPT_URI_PATH, (uint8_t *)uri_path, strlen(uri_path));
    coap_add_option(&msg, 1, &observe, 1);  // Observe = 0

    coap_send_con_and_wait(&msg);
}

// 服务器端通知
void coap_notify_observers(const char *path, uint8_t *data, int len) {
    for (int i = 0; i < observer_count; i++) {
        if (strcmp(observers[i].path, path) == 0) {
            coap_message_t notify;
            notify.header.code = COAP_CONTENT;
            notify.header.message_id = next_message_id++;
            notify.payload = data;
            notify.payload_len = len;

            // Observe序列号(用于排序)
            uint32_t seq = htonl(observers[i].last_version++);
            coap_add_option(&notify, 1, (uint8_t *)&seq, 3);

            // Max-Age
            uint32_t max_age = observers[i].max_age;
            coap_add_option(&notify, COAP_OPT_MAX_AGE, (uint8_t *)&max_age, 1);

            coap_send_non(&notify);  // NON通知
        }
    }
}
```

---

## 五、DTLS安全

### 5.1 CoAP over DTLS

```c
// DTLS-secured CoAP
typedef struct {
    const char *psk_identity;
    const uint8_t *psk_key;
    int psk_key_len;
} coap_dtls_config_t;

// PSK模式DTLS连接
void coap_dtls_connect(const char *host, int port, coap_dtls_config_t *config) {
    // DTLS握手
    dtls_context_t *dtls = dtls_new_context();
    dtls_set_psk(dtls, config->psk_identity,
                 config->psk_key, config->psk_key_len);
    dtls_connect(dtls, host, port);

    // 通过DTLS发送CoAP
    coap_message_t msg;
    msg.header.code = COAP_GET;
    // ...

    uint8_t buf[512];
    int len = coap_build_message(buf, &msg);
    dtls_send(dtls, buf, len);
}
```

---

## 六、CoAP vs MQTT

| 特性 | CoAP | MQTT |
|------|------|------|
| 传输层 | UDP | TCP |
| 模型 | 请求-响应 | 发布-订阅 |
| 通信模式 | 1:1 | 1:N, N:N |
| 资源消耗 | 更低 | 低 |
| 可靠性 | CON/ACK | QoS 0/1/2 |
| 发现 | Link Format | 无标准 |
| 适用场景 | 传感器/执行器 | 消息推送 |

---

## 附录：常用端口

| 端口 | 协议 | 说明 |
|------|------|------|
| 5683 | CoAP | 非加密 |
| 5684 | CoAPs | DTLS加密 |

---

## 相关链接

- [[物联网协议]] - 物联网协议概览
- [[MQTT协议详解]] - MQTT详解
- [[TCP-IP协议栈]] - 网络基础
- [[物联网安全]] - DTLS安全

---

## 相关笔记

- [[09、WiFi网络连接]] — WiFi 驱动
- [[../通信/MQTT协议详解]] — MQTT 协议
- [[../ESP32/ESP32系列芯片对比]] — 芯片选型
- [[../嵌入式应用/智能家居物联网系统]] — 智能家居实战
- [[../嵌入式基础/00-嵌入式学习路线图]] — 学习路线总览
