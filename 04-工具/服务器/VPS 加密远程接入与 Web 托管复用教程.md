# VPS 加密远程接入与 Web 托管复用教程

> [!important] 架构定位与安全规范
> 本教程基于 **Caddy 2 + sing-box (VLESS-gRPC) + UFW + Fail2ban + Linux BBR** 组合，实现 **443 端口多路复用（正常 Web 服务 / 云盘 / 静态文档站与加密代理流量共存）**。
> 所有明文凭据、UUID、私钥均使用占位符表示，切勿在公网 Git 仓库或明文笔记中暴露敏感信息。

---

## 1. 核心架构与流量流向图

```text
                                 公网客户端 (Browser / sing-box / v2rayN)
                                                 │
                                                 │ HTTPS / TLS 1.3 / HTTP/3 (Port 443)
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │          Caddy L7 反向代理引擎        │
                             │  - ACME 自动申请/续期 TLS 证书 (ECC)   │
                             │  - 开启 HTTP/3 (QUIC) & BBR 网络加速  │
                             │  - 安全响应头 (HSTS / 隐藏 Server 头) │
                             └──────┬─────────────────────────┬──────┘
                                    │                         │
                  gRPC 协议 + 专属 ServiceName 流量          普通 Web 流量 / 伪装站点访问
                                    │                         │
                                    ▼ (h2c 明文 HTTP/2)       ▼
                      ┌───────────────────────────┐   ┌───────────────────────────┐
                      │    sing-box 核心服务      │   │  真实业务 / 伪装站点服务  │
                      │  - 仅监听 127.0.0.1:10000 │   │  1. STM32 / Vue 静态文档  │
                      │  - VLESS 无握手特征       │   │  2. Cloudreve/Alist 私有云│
                      │  - 纯直连 Direct 出站     │   │  3. 404 自定义错误页面   │
                      └─────────────┬─────────────┘   └───────────────────────────┘
                                    │
                                    ▼
                                目标互联网
```

### 核心安全与防探测设计：
1. **端口不直连**：`sing-box` 仅监听 `127.0.0.1:10000` 回环地址，公网防火墙仅放行 `80`、`443` 与 `22`，从根本上防止针对代理端口的端口扫描与主动探测。
2. **主动探测回落与真实服务**：任何非授权请求、普通浏览器访问、主动探测工具直接返回真实的业务站点（文档库、云盘或个人主页），行为与真实网站完全无异。
3. **消除 TLS 握手特征**：由 Caddy（标准 Go Web 服务器）统一完成 TLS 握手，具有全球标准且合法的 TLS 指纹与有效 CA 证书。

---

## 2. 深度对比：为什么选择 gRPC 优于 WebSocket？

在基于 TLS/Web 容器的反代架构中，传输层主要有 **WebSocket (WS)** 与 **gRPC** 两种选择，它们的差异如下：

| 对比维度 | WebSocket (WS) | gRPC (HTTP/2 Multiplexing) | 为什么 gRPC 更好？ |
| :--- | :--- | :--- | :--- |
| **底层协议基础** | HTTP/1.1 Upgrade 协议升级机制 | 原生基于 **HTTP/2** 传输（二进制分帧） | gRPC 与现代微服务 API 流量完全一致，不可区分 |
| **连接复用能力 (Multiplexing)** | **弱**。通常每个 TCP/WS 连接传输单一会话，并发高时频繁建立连接。 | **强**。单条 TCP 连接上通过 HTTP/2 Streams **多路复用**成百上千个并发请求。 | 显著降低并发访问时的 TLS 握手开销与握手往返延迟 (RTT) |
| **头部开销与压缩** | **无头部压缩**。每个数据帧均有独立头部，开销大。 | **HPACK 头部压缩算法**。大幅压缩传输上下文。 | 降低传输数据包体积，减少网络带宽消耗 |
| **DPI 流量行为特征** | 长时间维持单条 HTTP Upgrade 状态的长连接，连接特征明显。 | 行为表现为常规的 RPC 数据调用，与微服务、遥测上报流量无异。 | 极大地降低被机器学习或启发式流控识别为代理的概率 |
| **CDN / 反向代理支持** | 部分 CDN/反代节点需额外调优 timeout 与 upgrade 头部。 | 现代反代（Caddy、Nginx 1.13.10+、Traefik）原生支持 `grpc_pass` / `protocol grpc`。 | 反代开销更小，转发延迟更低 |

---

## 3. 网站与云盘伪装方案详解

为了使 VPS 表现为一个合法的 Web 服务器，推荐以下两种伪装方案：

### 方案 A：技术文档站 / 博客站点伪装（推荐，轻量稳定）
- **适用场景**：个人开发者、技术人员。
- **内容示例**：STM32Cube 固件库参考文档、Doxygen 生成的 C++ API 手册、VitePress / Docusaurus 静态文档。
- **优点**：纯静态 HTML/JS/CSS，极低 CPU/内存占用（< 10MB），无需数据库，抗并发压力极高，且内容真实专业。

### 方案 B：私有云盘 / 文件分享站伪装（Cloudreve / Alist）
- **适用场景**：平时兼顾个人网盘、文件传输、团队知识库需求。
- **部署方式**：
  - 本地运行 Cloudreve 或 Alist（例如监听 `127.0.0.1:5212`）。
  - Caddy 将根路径 `/` 反向代理至本地云盘：
    ```caddy
    example.com {
        # gRPC 代理流量分流
        @authorized_grpc {
            protocol grpc
            path /com.custom.telemetry.v1/*
        }
        reverse_proxy @authorized_grpc h2c://127.0.0.1:10000

        # 其他所有流量转发到私有云盘
        reverse_proxy 127.0.0.1:5212
    }
    ```
- **伪装效果**：探测器和浏览器访问直接展示合法的个人网盘登录页或公共分享目录，完全契合 HTTPS 站点的正常使用逻辑。

---

## 4. 服务端完整配置流程

### 4.1 系统初始化与安全加固

```bash
# 1. 更新系统软件包
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl ca-certificates ufw fail2ban unzip jq

# 2. 开启 BBR 拥塞控制与高并发调优
cat << 'EOF' | sudo tee /etc/sysctl.d/99-custom-network.conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
EOF
sudo sysctl --system

# 3. 配置防火墙与防爆破
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp    # 开启 HTTP/3 QUIC 支持
sudo ufw enable

cat << 'EOF' | sudo tee /etc/fail2ban/jail.local
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
backend = systemd
EOF
sudo systemctl enable --now fail2ban
```

---

### 4.2 安装并配置 sing-box

```bash
# 安装 sing-box 官方源（或通过官方 releases 下载）
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://sing-box.app/gpg.key -o /etc/apt/keyrings/sagernet.asc
echo "deb [signed-by=/etc/apt/keyrings/sagernet.asc] https://deb.sagernet.org/ * *" | sudo tee /etc/apt/sources.list.d/sagernet.list
sudo apt update && sudo apt install -y sing-box
```

编写 `/etc/sing-box/config.json`：
> [!tip] 
> 生成随机 UUID 命令：`cat /proc/sys/kernel/random/uuid`

```json
{
  "log": {
    "level": "warn",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-grpc-in",
      "listen": "127.0.0.1",
      "listen_port": 10000,
      "users": [
        {
          "uuid": "REPLACE_WITH_YOUR_UUID",
          "flow": ""
        }
      ],
      "transport": {
        "type": "grpc",
        "service_name": "com.custom.telemetry.v1"
      }
    }
  ],
  "outbounds": [
    {
      "type": "direct",
      "tag": "direct-out"
    },
    {
      "type": "block",
      "tag": "block-out"
    }
  ]
}
```

启动与校验：
```bash
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl enable --now sing-box
```

---

### 4.3 安装并配置 Caddy 2

```bash
# 安装 Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

部署伪装静态站并配置 `/etc/caddy/Caddyfile`：

```bash
# 准备静态站目录
sudo mkdir -p /var/www/html
# 将你的静态网页放入 /var/www/html (例如 index.html, 404.html)
sudo chown -R caddy:caddy /var/www/html
sudo chmod -R 755 /var/www/html
```

编写 `/etc/caddy/Caddyfile`：

```caddy
yourdomain.com {
    tls {
        protocols tls1.2 tls1.3
    }

    # 安全响应头与指纹抹除
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        -Server
    }

    # 1. 静态伪装站点
    root * /var/www/html
    file_server

    # 2. gRPC 精准匹配分流 (h2c 转发至本地 sing-box)
    @grpc_traffic {
        protocol grpc
        path /com.custom.telemetry.v1/*
    }
    reverse_proxy @grpc_traffic h2c://127.0.0.1:10000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
    }

    # 3. 自定义 404 响应
    handle_errors {
        @404 {
            expression {http.error.status_code} == 404
        }
        rewrite @404 /404.html
        file_server
    }
}
```

校验并重载 Caddy：
```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

---

## 5. 客户端连接配置与一键导入

### 5.1 节点配置参数表

| 配置字段 | 推荐设定值 | 说明 |
| :--- | :--- | :--- |
| **服务器地址 (Address)** | `yourdomain.com` | 你的解析域名（或 CDN 优选 IP） |
| **端口 (Port)** | `443` | 标准 HTTPS 端口 |
| **用户 ID (UUID)** | `<与服务端配置保持一致>` | 唯一身份验证凭据 |
| **传输协议 (Transport)** | `gRPC` | 选用 gRPC 多路复用传输 |
| **服务名称 (ServiceName)** | `com.custom.telemetry.v1` | 需与 Caddy / sing-box 完全一致 |
| **传输模式 (gRPC Mode)** | `gun` | 标准单连接多流模式 |
| **传输安全 (TLS)** | `TLS` | 必须开启 |
| **SNI / ServerName** | `yourdomain.com` | 与域名一致 |
| **ALPN** | `h2` | 协商 HTTP/2 协议 |

### 5.2 通用 VLESS 一键导入链接模板

```text
vless://<YOUR_UUID>@yourdomain.com:443?encryption=none&security=tls&sni=yourdomain.com&alpn=h2&type=grpc&serviceName=com.custom.telemetry.v1&mode=gun#My-Node
```

---

## 6. 排错指南与维护命令

| 故障现象 | 排查方向 | 处理方法 |
| :--- | :--- | :--- |
| **客户端报错 `EOF` 或 `connection refused`** | 1. Caddy 未正常运行<br>2. sing-box 回环端口未监听 | `sudo systemctl status caddy`<br>`sudo ss -tlnp \| grep 10000` |
| **客户端报错 `bad status 404/400`** | ServiceName 或 Caddy Path 匹配不一致 | 检查 Caddyfile 中 `path /<service_name>/*` 与客户端配置是否精确匹配 |
| **浏览器访问显示证书不安全** | ACME 域名验证失败（DNS 未生效或 80 端口被封） | 检查 `dig +short yourdomain.com` 及云安全组 80/443 是否放行 |
| **日常状态一键体检** | 服务健康度检查 | `sudo systemctl status sing-box caddy fail2ban` |

