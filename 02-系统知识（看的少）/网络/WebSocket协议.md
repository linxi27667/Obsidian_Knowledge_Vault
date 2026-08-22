---
title: WebSocket 协议
tags: [网络, WebSocket, 实时通信]
created: 2026-05-04
---

# WebSocket 协议

## 一、WebSocket 是什么

```
端口: 80 (ws://) 或 443 (wss://)
特点: 全双工、持久连接、单向帧传输
```

### 1.1 与 HTTP 对比

**HTTP 请求/响应模式**：
```
客户端                    服务器
  │── GET /api/status ──→│
  │←── 200 OK + JSON ───│
  │（连接关闭）            │
```
- 每次请求建立新连接（HTTP/1.1）
- 服务器不能主动推送数据
- 适合：获取状态、发送命令

**WebSocket 全双工模式**：
```
客户端                    服务器
  │── HTTP 升级请求 ────→│
  │←── 101 Switching ───│
  │←═════════════════════║ 双向数据传输
  │  ←─ 服务器推送 ──────║
  │──→ 客户端发送 ───────║
  │←═════════════════════║
```
- 一次握手，持久连接
- 双向实时通信
- 适合：AI 对话、实时数据流

---

## 二、握手过程

```
客户端                     服务器
  │                              │
  │── HTTP 升级请求 ───────────→│
  │  GET /ws HTTP/1.1            │
  │  Upgrade: websocket          │
  │  Connection: Upgrade         │
  │  Sec-WebSocket-Key: xxxxx    │
  │                              │
  │←── 101 Switching Protocols ─│
  │  Upgrade: websocket          │
  │  Connection: Upgrade         │
  │  Sec-WebSocket-Accept: yyyyy │
  │                              │
  │←══════════════════════════════║ 双向通信
  │  ←─ Frame: "Hello" ─────────║
  │──→ Frame: "Hi back" ────────║
  │←══════════════════════════════║
```

---

## 三、WebSocket 帧格式（简化）

```
┌──────┬──────┬──────────────┐
│ FIN  │ opcode│ Payload Len  │
├──────┴──────┴──────────────┤
│   Mask Key (4字节, 客户端)  │
├────────────────────────────┤
│       Payload Data          │
└────────────────────────────┘

opcode: 0x1=文本 0x2=二进制 0x8=关闭 0x9=Ping 0xA=Pong
```

---

## 四、适用场景

- AI 对话（小智项目用 WebSocket 连接大模型）
- 浏览器实时数据推送
- 在线游戏
- 实时协作编辑

---

## 五、WebSocket vs MQTT

| | WebSocket | MQTT |
|--|-----------|------|
| 模型 | 点对点 | 发布/订阅 |
| 消息路由 | 无主题概念 | 主题系统+通配符 |
| QoS | 无 | 3 级 (0/1/2) |
| 离线消息 | ❌ | ✅（持久会话+遗嘱） |
| 适用 | 浏览器实时通信 | IoT 设备间通信 |

---

## 六、MQTT over WebSocket

MQTT 可以通过 WebSocket 传输（端口 9001），适用于：
- 浏览器中直接使用 MQTT（Web MQTT 客户端）
- 穿越严格防火墙（只允许 80/443 端口）
- 小智项目中的 WebSocket 协议就用于 AI 对话
