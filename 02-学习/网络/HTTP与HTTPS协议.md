---
title: HTTP 与 HTTPS 协议
tags: [网络, HTTP, HTTPS, TLS]
created: 2026-05-04
---

# HTTP 与 HTTPS 协议

## 一、HTTP（超文本传输协议）

```
全称: HyperText Transfer Protocol
端口: 80 (TCP)
版本: HTTP/1.0, HTTP/1.1, HTTP/2, HTTP/3
特点: 请求/响应模型、无状态、文本协议
```

### 1.1 请求格式

```
GET /api/status HTTP/1.1\r\n
Host: 192.168.1.100\r\n
Content-Type: application/json\r\n
\r\n

POST /api/led HTTP/1.1\r\n
Host: 192.168.1.100\r\n
Content-Type: application/json\r\n
Content-Length: 25\r\n
\r\n
{"gpio": 5, "level": 1}
```

### 1.2 响应格式

```
HTTP/1.1 200 OK\r\n
Content-Type: application/json\r\n
Content-Length: 16\r\n
\r\n
{"status":"ok"}
```

### 1.3 常见状态码

| 状态码 | 含义 | 场景 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 301 | Moved Permanently | 永久重定向 |
| 304 | Not Modified | 资源未变（使用缓存） |
| 400 | Bad Request | 请求格式错误 |
| 401 | Unauthorized | 需要认证 |
| 403 | Forbidden | 拒绝访问 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 1.4 HTTP 方法

| 方法 | 用途 | 是否安全 | 是否幂等 |
|------|------|---------|---------|
| GET | 获取资源 | ✅ | ✅ |
| POST | 创建/提交资源 | ❌ | ❌ |
| PUT | 更新/替换资源 | ❌ | ✅ |
| DELETE | 删除资源 | ❌ | ✅ |
| PATCH | 部分更新 | ❌ | ❌ |
| HEAD | 只获取头部 | ✅ | ✅ |

### 1.5 ESP32 中的 HTTP 使用

```c
// ESP-IDF HTTP 客户端示例
esp_http_client_config_t config = {
    .url = "http://192.168.1.100/api/status",
    .method = HTTP_METHOD_GET,
};
esp_http_client_handle_t client = esp_http_client_init(&config);
esp_http_client_perform(client);
```

### 1.6 HTTP 版本对比

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|--|----------|--------|--------|
| 传输层 | TCP | TCP | QUIC (UDP) |
| 多路复用 | ❌（队头阻塞） | ✅（流复用） | ✅（无队头阻塞） |
| 头部压缩 | ❌ | ✅ (HPACK) | ✅ (QPACK) |
| 服务器推送 | ❌ | ✅ | 已弃用 |
| ESP32 支持 | ✅ | ❌（太重） | ❌ |

---

## 二、HTTPS（HTTP over TLS）

```
端口: 443 (TCP)
本质: HTTP + TLS 加密层
```

### 2.1 TLS 握手简化流程

```
客户端                        服务器
  │                              │
  │── Client Hello ────────────→│
  │  "我支持 TLS 1.3, 这些是密码套件" │
  │                              │
  │←── Server Hello ────────────│
  │  "用 TLS 1.3, AES-256-GCM"    │
  │  "这是我的证书"                │
  │                              │
  │  验证证书 (链 → CA → 信任)     │
  │  协商共享密钥 (ECDHE)          │
  │                              │
  │═══ 后续所有 HTTP 数据加密传输 ══│
```

### 2.2 ESP32 HTTPS 配置

```c
esp_http_client_config_t config = {
    .url = "https://api.example.com/data",
    .cert_pem = server_cert,  // 服务器证书 PEM 格式
};
```

### 2.3 HTTP/HTTPS 与 MQTT 对比

| | HTTP | MQTT |
|--|------|------|
| 模型 | 请求/响应 | 发布/订阅 |
| 连接 | 短连接（HTTP/1.1） | 长连接 |
| 服务器推送 | ❌ | ✅ |
| 开销 | 大（Headers 多） | 小（最小 2 字节） |
| 适用 | Web API、REST | IoT 设备通信 |
