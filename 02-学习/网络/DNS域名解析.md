---
title: DNS 域名解析
tags: [网络, DNS, 域名解析, mDNS]
created: 2026-05-04
---

# DNS 域名解析

## 一、DNS 是什么

```
端口: 53 (TCP/UDP)
功能: 域名 → IP 地址映射
```

**类比**：
```
你记得朋友的名字叫"张三"（域名 broker.emqx.io），
但打电话需要知道他的电话号码（IP 13.212.94.125）。

DNS 就像手机通讯录：你输入"张三"，它自动查找对应的电话号码。

为什么不用 IP 直接访问？因为人记不住 13.212.94.125 这种数字，
但很容易记住 broker.emqx.io 这样的名字。
```

---

## 二、DNS 解析流程

```
用户输入: broker.emqx.io

1. 浏览器缓存 → 查到直接返回
2. OS 缓存 → 查到返回（Windows: ipconfig /flushdns 可清除）
3. hosts 文件 (C:\Windows\System32\drivers\etc\hosts)
4. DNS 服务器（递归查询）:
   本地 DNS → 根服务器(.) → .com → emqx.io → 返回 13.212.94.125
```

**完整查询链**：
```
ESP32 代码: mqtt://broker.emqx.io

1. 查本地 DNS 缓存 → 没有
2. 发给路由器配置的 DNS 服务器（UDP 53）
3. DNS 服务器递归查询:
   本地 DNS → 根服务器(.) → com 服务器 → emqx.io 服务器
4. 拿到结果: broker.emqx.io → 13.212.94.125
5. 返回给 ESP32
6. ESP32 用这个 IP 建立 TCP 连接

查询链：
  ESP32 ─→ 路由器(192.168.1.1)
              ─→ ISP DNS (223.5.5.5)
                   ─→ 根服务器 (.)
                        ─→ .com 服务器
                             ─→ emqx.io 权威服务器
                                  ← 返回 13.212.94.125
```

---

## 三、DNS 记录类型

| 类型 | 用途 | 示例 |
|------|------|------|
| A | 域名 → IPv4 | `broker.emqx.io → 13.212.94.125` |
| AAAA | 域名 → IPv6 | `example.com → 2001:db8::1` |
| CNAME | 别名 | `www.baidu.com → www.a.shifen.com` |
| MX | 邮件服务器 | `gmail.com → alt1.gmail-smtp-in.l.google.com` |
| TXT | 文本记录 | SPF、DKIM 验证 |
| NS | 权威 DNS 服务器 | 管理该域名的 DNS 服务器 |
| PTR | 反向解析 | IP → 域名 |

---

## 四、DNS 报文结构

```
┌────────────────────────────────┐
│          Transaction ID        │  ← 查询标识
├────────────────────────────────┤
│ QR│ Opcode │ Flags │ 响应码     │  ← QR: 0=查询 1=响应
├────────────────────────────────┤
│   问题数  │ 回答数 │ 授权数 │ 附加数 │
├────────────────────────────────┤
│     Questions（查询内容）        │
├────────────────────────────────┤
│     Answers（回答记录）          │
├────────────────────────────────┤
│     Authority（权威服务器）      │
├────────────────────────────────┤
│     Additional（附加信息）       │
└────────────────────────────────┘
```

---

## 五、mDNS（多播 DNS）

**类比**：
```
在一个小办公室里，你想找"小张"（某个设备）。
你不需要查公司通讯录（DNS 服务器），直接喊一声"小张在吗？"
小张回应"我在这！"

这就是 mDNS —— 局域网内的"喊话"，不需要 DNS 服务器。
```

```c
// ESP32 可以注册 mDNS 名称
mdns_hostname_set("xiaozhi-master");
// 局域网内其他设备可以通过 xiaozhi-master.local 访问
// 不依赖 DNS 服务器，基于 UDP 5353 组播
```

**特点**：
- 使用 `.local` 域名
- 不依赖 DNS 服务器
- 基于 UDP 5353 组播
- 仅在局域网内有效

---

## 六、常用 DNS 命令

```bash
# Windows
nslookup broker.emqx.io

# 输出：
# 服务器:  router
# Address:  192.168.1.1
#
# 非权威应答:
# 名称:    broker.emqx.io
# Address:  13.212.94.125

# Linux (更强大)
dig broker.emqx.io +short     # 简洁输出
dig broker.emqx.io ANY        # 查询所有记录
```
