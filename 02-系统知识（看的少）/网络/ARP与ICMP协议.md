---
title: ARP 与 ICMP 协议
tags: [网络, ARP, ICMP, ping, traceroute]
created: 2026-05-04
---

# ARP 与 ICMP 协议

## 一、ARP（地址解析协议）

### 1.1 ARP 是什么

```
功能: IP 地址 → MAC 地址映射
范围: 仅在局域网内有效
```

**类比**：
```
公司里你要给同事送文件，你知道他工号是 200（IP 地址），
但你需要知道他的工位在哪里（MAC 地址）才能亲自送过去。

ARP 就是你站在办公室大喊："工号 200 在哪？"
只有工号 200 的人会回应："我在 A 栋 3 楼 5 号工位！"
你记住了，下次直接送过去，不用再问。
```

**技术解释**：
网络层用 IP 地址寻址，但实际数据帧在物理层传输需要 MAC 地址。
ARP 解决的问题："192.168.1.200 的 MAC 地址是什么？"

### 1.2 ARP 工作流程

```
设备 A (192.168.1.100) 想发给 设备 B (192.168.1.200)

1. A 查自己的 ARP 缓存表 → 没有 B 的记录
2. A 广播 ARP 请求（发给局域网内所有设备）:
   "谁的 IP 是 192.168.1.200？请告诉 192.168.1.100"

   ┌───────┐    ARP Request (广播 FF:FF:FF:FF:FF:FF)    ┌───────┐
   │ 设备A │ ──────────────────────────────────────→  │ 设备B │
   │100    │                                         │200    │
   └───────┘                                         └───────┘
        ← ← ← ← ← ←  局域网内所有设备都收到  → → → → → →

3. 只有 B 回应（单播）:
   "我是 192.168.1.200，我的 MAC 是 AA:BB:CC:DD:EE:FF"

4. A 将 B 的 IP→MAC 映射存入 ARP 缓存（有效期通常几分钟）
5. A 用 B 的 MAC 地址封装以太网帧，发送数据
```

### 1.3 查看 ARP 缓存

```bash
# Windows / Linux / macOS 通用
arp -a

# 输出示例:
# Internet Address   Physical Address   Type
#   192.168.1.1      00-11-22-33-44-55  dynamic
#   192.168.1.100    aa-bb-cc-dd-ee-ff  dynamic
```

### 1.4 ESP32 中的 ARP

ESP32 连接 WiFi 后自动处理 ARP，无需手动配置。ESP-IDF 底层 lwIP 协议栈自动响应 ARP 请求。

---

## 二、ICMP 协议（Internet 控制消息协议）

### 2.1 ICMP 是什么

```
协议号: 1 (IP 头部中的 protocol 字段)
特点: 辅助 IP 传递网络状态信息
```

**类比**：
```
IP 数据包像快递包裹，ICMP 像快递系统的"状态通知"：
- "您的包裹已送达" → Echo Reply
- "收件地址不存在" → Destination Unreachable
- "包裹在路上超时了" → Time Exceeded

ICMP 不是用来传数据的，而是用来传"网络状态"的。
```

### 2.2 ping 命令的原理

```
ping 8.8.8.8 的本质：

1. 发送 ICMP Echo Request（回显请求）到 8.8.8.8
2. 对方收到后回复 ICMP Echo Reply（回显响应）
3. 计算往返时间（RTT = Round Trip Time）

数据包格式：
┌──────┬──────┬──────┬─────────────────────────────┐
│ Type │ Code │ 校验和 │         数据载荷              │
├──────┼──────┼──────┼─────────────────────────────┤
│  8   │  0   │ xxxx  │  时间戳 + 序列号 + 填充数据   │  ← Echo Request
│  0   │  0   │ xxxx  │  时间戳 + 序列号 + 填充数据   │  ← Echo Reply
└──────┴──────┴──────┴─────────────────────────────┘
```

**延迟参考**：
- `< 1ms`：局域网（同一 WiFi）
- `1-20ms`：同城服务器
- `20-100ms`：国内跨省
- `100-300ms`：跨国

### 2.3 traceroute / tracert 原理

**类比**：
```
你想知道从你家到某个地方经过了哪些路口。

做法：你每次派一个人出门，但只允许走 N 步。
- 第 1 次：只允许走 1 步 → 到了第 1 个路口就回来，告诉你路口在哪
- 第 2 次：允许走 2 步 → 到了第 2 个路口就回来，告诉你路口在哪
- 第 3 次：允许走 3 步 → 到了第 3 个路口就回来
- ...一直增加到到达目的地

这样你就知道了完整路线。
```

```
利用 IP 包的 TTL（Time To Live）字段：

每经过一个路由器，TTL - 1。TTL = 0 时，路由器丢弃数据包并
发回 ICMP "Time Exceeded" 消息。

tracert 流程：
  发送 TTL=1 的包 → 路由器1 返回 Time Exceeded → 获知路由器1 IP
  发送 TTL=2 的包 → 路由器2 返回 Time Exceeded → 获知路由器2 IP
  发送 TTL=3 的包 → 路由器3 返回 Time Exceeded → 获知路由器3 IP
  ...
  直到到达目标，收到 Echo Reply
```

### 2.4 常见 ICMP 类型

| Type | 名称 | 触发条件 |
|------|------|---------|
| 0 | Echo Reply | ping 响应 |
| 3 | Destination Unreachable | 目标不可达（端口关闭、网络不通） |
| 5 | Redirect | 路由器告诉主机有更优路径 |
| 8 | Echo Request | ping 请求 |
| 11 | Time Exceeded | TTL 耗尽（traceroute 用） |

---

## 三、ping 命令详解

```bash
# Windows
ping 192.168.1.1
ping 8.8.8.8 -t          # 持续 ping（Ctrl+C 停止）

# Linux
ping 192.168.1.1 -c 4    # ping 4 次
ping 192.168.1.1 -i 0.2  # 间隔 0.2 秒

# 输出解读：
# 64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=3.2 ms
#                                          └── RTT 延迟
```
