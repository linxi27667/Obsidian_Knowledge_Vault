---
title: CoAP 协议
tags: [网络, CoAP, IoT, UDP]
created: 2026-05-04
---

# CoAP 协议

## 一、CoAP 是什么

```
全称: Constrained Application Protocol
端口: 5683 (UDP) / 5684 (DTLS)
特点: RESTful 风格、极轻量、运行在 UDP 上
```

**设计目标**：为资源极度受限的设备（如 8 位 MCU、几十 KB RAM）提供类似 HTTP 的协议。

---

## 二、CoAP vs HTTP 映射

| CoAP | HTTP | 说明 |
|------|------|------|
| GET | GET | 获取资源 |
| POST | POST | 创建资源 |
| PUT | PUT | 更新资源 |
| DELETE | DELETE | 删除资源 |

---

## 三、报文格式

```
┌────────────────────────────────┐
│  Ver(2) │ T(2) │ TKL(4)        │  ← 头部
├─────────┼──────┼───────────────┤
│ Code(8) │      Message ID(16)  │
├─────────┴──────┴───────────────┤
│ Token (0-8 字节，可选）          │
├────────────────────────────────┤
│ Options (温度/内容类型等)       │
├────────────────────────────────┤
│ Payload Marker (0xFF)          │
├────────────────────────────────┤
│ Payload Data                   │
└────────────────────────────────┘

最小头部: 4 字节（比 HTTP 小得多）
```

---

## 四、消息类型

| 类型 | 缩写 | 说明 |
|------|------|------|
| Confirmable | CON | 需要确认（类似 TCP） |
| Non-confirmable | NON | 不需要确认（类似 UDP 裸发） |
| Acknowledgement | ACK | 对 CON 的确认 |
| Reset | RST | 拒绝/错误 |

---

## 五、适用场景

- 超低功耗 IoT 传感器（电池供电，MCU 性能极弱）
- 6LoWPAN 网络（IPv6 over 低功耗无线个人区域网）
- ESP32 一般不需要 CoAP，用 MQTT 更合适

---

## 六、CoAP vs MQTT 对比

| | CoAP | MQTT |
|--|------|------|
| 传输层 | UDP | TCP |
| 模型 | 请求/响应 | 发布/订阅 |
| 开销 | 4 字节头部 | 2 字节头部（最小） |
| QoS | 2 级（CON/NON） | 3 级（0/1/2） |
| 适用 | 极低功耗设备 | 通用 IoT 通信 |
