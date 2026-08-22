---
title: Mosquitto (MQTT Broker)
tags: [MQTT, Mosquitto, Broker, Docker]
created: 2026-05-04
---

# Mosquitto 是什么

## 一、Mosquitto 是什么

**类比**：
```
想象 Mosquitto 是一个"邮局"：

- 你（ESP32 设备）不用知道收件人（其他设备）在哪
- 你只需要把信（消息）交给邮局（Mosquitto）
- 邮局根据信封上的地址（Topic 主题）分拣
- 订阅了某个地址的人会自动收到信

Mosquitto 就是这个"邮局"——MQTT Broker（消息代理服务器）。
它负责接收、存储、转发所有 MQTT 消息。
```

### 核心角色

```
                  ┌──────────────┐
                  │  Mosquitto   │
                  │   Broker     │
                  │  (邮局/中转站) │
                  └──────┬───────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐      ┌───▼────┐     ┌────▼────┐
   │ ESP32   │      │ 手机    │     │ 电脑    │
   │ 主控    │      │ MQTT客户端│    │ MQTT客户端│
   │ 发布消息 │      │ 订阅消息 │     │ 订阅消息 │
   └─────────┘      └────────┘     └────────┘
```

- **Mosquitto = MQTT Broker**：消息中转站
- **客户端 = ESP32/手机/电脑**：发布或订阅消息
- 客户端之间**互不知道对方存在**，完全通过 Mosquitto 解耦

### 特点

| 特点 | 说明 |
|------|------|
| 开源免费 | Eclipse 基金会维护 |
| 轻量 | 内存占用极小，树莓派都能跑 |
| 简单 | 配置容易，上手快 |
| 跨平台 | Windows/Linux/macOS/Docker |
| 适合开发 | IoT 项目最常用的测试用 Broker |

---

## 二、Mosquitto 能做什么

```
1. 接收设备发布的消息 → 转发给所有订阅者
2. 管理设备连接 → 谁在线、谁离线
3. 遗嘱消息 → 设备异常断开时自动通知
4. 保留消息 → 新设备连入时立即知道最新状态
5. 主题过滤 → 只把相关消息发给相关订阅者
```

### Mosquitto vs 其他 Broker

| Broker | 特点 | 适用场景 |
|--------|------|----------|
| **Mosquitto** | 轻量、简单、单节点 | 开发、小规模 IoT 项目 |
| **EMQX** | 高性能、集群、Web 管理界面 | 生产环境、大规模部署 |
| **HiveMQ** | 企业级、插件丰富 | 商业项目 |
| **RabbitMQ (MQTT插件)** | 多协议支持 | 已有 RabbitMQ 基础设施 |

**建议**：学习/开发阶段用 Mosquitto，生产环境升级到 EMQX。

---

## 三、Docker 部署 Mosquitto

### 3.1 快速启动

```bash
# 最简单方式，一行启动（允许匿名访问）
docker run -d --name mosquitto -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

- `-p 1883:1883`：MQTT 主端口
- `-p 9001:9001`：WebSocket 端口（浏览器用）

### 3.2 带配置文件启动（推荐）

```bash
# 创建配置目录
mkdir -p /mosquitto/config /mosquitto/data /mosquitto/log

# 创建 mosquitto.conf 配置文件
```

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

```bash
# 带配置启动
docker run -d --name mosquitto \
  -p 1883:1883 -p 9001:9001 \
  -v /mosquitto/config:/mosquitto/config \
  -v /mosquitto/data:/mosquitto/data \
  -v /mosquitto/log:/mosquitto/log \
  eclipse-mosquitto
```

### 3.3 常用管理命令

```bash
# 停止 / 启动 / 删除
docker stop mosquitto
docker start mosquitto
docker rm mosquitto

# 查看日志
docker logs mosquitto
docker logs -f mosquitto  # 实时跟踪

# 查看容器 IP
docker inspect -f '{{.NetworkSettings.IPAddress}}' mosquitto
```

---

## 四、Mosquitto 命令行工具

### 4.1 订阅消息

```bash
# 订阅某个主题（-v 显示主题名）
mosquitto_sub -h 127.0.0.1 -p 1883 -t "xiaozhi/iot/#" -v

# 订阅所有主题
mosquitto_sub -h 127.0.0.1 -t "#" -v
```

### 4.2 发布消息

```bash
# 发布普通消息
mosquitto_pub -h 127.0.0.1 -p 1883 -t "xiaozhi/iot/cmd/broadcast" -m '{"cmd":0x30}'

# 发布保留消息（-r）
mosquitto_pub -h 127.0.0.1 -t "sensor/temp" -m "25.6" -r

# 指定 QoS（-q）
mosquitto_pub -h 127.0.0.1 -t "cmd/open" -m "1" -q 1

# 带用户名密码
mosquitto_pub -h 127.0.0.1 -u admin -P password -t "topic" -m "data"
```

### 4.3 查看 Broker 状态

```bash
# 查看系统主题（Broker 内置信息）
mosquitto_sub -h 127.0.0.1 -t '$SYS/broker/#' -v
```

常见 `$SYS` 信息：

| 主题 | 含义 |
|------|------|
| `$SYS/broker/clients/connected` | 当前连接客户端数 |
| `$SYS/broker/clients/total` | 历史总连接数 |
| `$SYS/broker/messages/stored` | 存储的消息数 |
| `$SYS/broker/uptime` | Broker 运行时间 |

---

## 五、配置用户名密码认证

```bash
# 1. 创建密码文件
echo "admin:123456" > /mosquitto/config/passwords

# 2. 修改 mosquitto.conf
```

```conf
# 关闭匿名
allow_anonymous false

# 指定密码文件
password_file /mosquitto/config/passwords

# ACL 访问控制
acl_file /mosquitto/config/acl
```

```conf
# acl 文件示例
# 用户可以读自己设备相关的主题
user admin
topic readwrite #

user device1
topic readwrite xiaozhi/iot/cmd/1
topic readwrite xiaozhi/iot/resp/1
```

```bash
# 3. 重启 Mosquitto 生效
docker restart mosquitto
```

---

## 六、Mosquitto 在小智项目中的角色

```
小智项目 MQTT 主题规划：
xiaozhi/iot/
├── cmd/                    ← 命令（主控 → 从设备）
├── resp/                   ← 响应（从设备 → 主控）
├── heartbeat/              ← 心跳
├── announce/               ← 上线通知
└── status/                 ← 状态（遗嘱消息）

Mosquitto 负责：
1. 接收主控发布的命令 → 转发给对应的从设备
2. 接收从设备的响应 → 转发给主控
3. 检测从设备异常断开 → 发布遗嘱消息
4. 新设备连入 → 发送保留消息，让它知道已有设备在线
```

---

## 七、常见问题

### Q: Mosquitto 连接不上怎么办？

```bash
# 1. 检查容器是否在运行
docker ps | grep mosquitto

# 2. 检查端口是否监听
netstat -ano | findstr :1883

# 3. 查看容器日志
docker logs mosquitto

# 4. 测试本地连通性
telnet 127.0.0.1 1883
```

### Q: Mosquitto 能代替 EMQX 用于生产吗？

- **可以**：小规模（几十个设备）、单节点部署
- **不行**：需要高可用、集群、水平扩展的场景
- **建议**：生产环境用 EMQX，开发阶段用 Mosquitto
