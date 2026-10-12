# MQTT 本质是 TCP

## 核心概念

MQTT 就是在 TCP 之上定义了一套**消息格式规则**，不是独立的传输协议。

```
HTTP    = TCP + 网页请求/响应规则
MQTT    = TCP + 发布/订阅消息规则
WebSocket = TCP + 双向通信规则
FTP     = TCP + 文件传输规则
```

## 网络分层

```
┌─────────────────┐
│   MQTT 报文      │  应用层：你关心的"发布到哪个 topic"
├─────────────────┤
│   TCP 头部       │  传输层：保证数据不丢、不乱、不重复
├─────────────────┤
│   IP 头部        │  网络层：找到目标服务器
├─────────────────┤
│   WiFi 帧        │  链路层：无线信号传输
└─────────────────┘
```

MQTT 只规定"CONNECT、PUBLISH、SUBSCRIBE 这些报文长什么样"，数据可靠传输是 TCP 的事。

## esp_mqtt_client_publish 参数

```c
int esp_mqtt_client_publish(
    esp_mqtt_client_handle_t client,  // MQTT 客户端句柄
    const char *topic,                // 主题，如 "home/sensor/temp"
    const char *data,                 // 消息内容（原始字节，不关心格式）
    int len,                          // 长度，传 0 自动 strlen
    int qos,                          // 0=最多一次，1=至少一次，2=恰好一次
    int retain                        // 1=broker 保留消息，0=不保留
);
```

返回值：成功返回消息 ID（>=0），失败返回 -1。

发 JSON 只是把 JSON 字符串当普通 data 传进去，函数本身不解析格式。

## 学习日期

2026-06-24
