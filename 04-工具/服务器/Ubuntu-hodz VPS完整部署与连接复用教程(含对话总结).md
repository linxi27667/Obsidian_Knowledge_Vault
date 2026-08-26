# Ubuntu-hodz VPS 零信任部署与连接完整教程 (对话总结合并版)

> [!important] 架构定位与安全规范
> 本教程完整汇总并无删减地合并了「Ubuntu-hodz 服务器连接教程」、「Ubuntu-hodz 零信任加密通信部署记录」、「VPS 加密远程接入与 Web 托管复用教程」以及原始 **Gemini 对话 (AuHpDqpehrw2)** 中的全部细节和部署流程。
>
> 核心基于 **Caddy 2 + sing-box (VLESS-gRPC) + UFW + Fail2ban + Linux BBR** 黄金组合，实现 **443 端口多路复用（正常 Web 服务 / 云盘 / 静态文档站与加密代理流量共存）**。
> 所有明文凭据、UUID、私钥均使用占位符或已脱敏，切勿在公网 Git 仓库或明文笔记中暴露敏感信息。

---

## 1. 概览、核心架构与流量流向

### 1.1 总体架构图

```text
                                 公网客户端 (Browser / sing-box / v2rayN)
                                                 │
                                                 │ HTTPS / TLS 1.3 / HTTP/3 (Port 443)
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │          Caddy L7 反向代理引擎        │
                             │  - 自动申请/续期 ACME TLS 证书 (ECC)   │
                             │  - 开启 HTTP/3 (QUIC) & BBR 网络加速  │
                             │  - 安全响应头 (HSTS / 隐藏 Server 头) │
                             │  - gRPC ServiceName 精确分流          │
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

### 1.2 组件职责与安全防探测设计

- **sing-box**：仅提供已授权用户的加密远程接入。**端口不直连**，仅监听 `127.0.0.1:10000` 回环地址，外部无法直连，从根本上防止针对代理端口的端口扫描与主动探测。
- **Caddy**：自动申请/续期 ACME 证书，统一完成 TLS 握手，提供全球标准且合法的 TLS 指纹与有效 CA 证书以消除握手特征。它托管正常网站，并把约定的应用流量精确转发到回环端口。任何非授权请求、普通浏览器访问、主动探测工具直接返回真实的业务站点，行为与真实网站完全无异。
- **UFW**：默认拒绝入站，仅放行 SSH (22)、HTTP (80)、HTTPS (443 tcp/udp)。
- **Fail2ban**：限制 SSH 暴力破解尝试。
- **BBR**：TCP 拥塞控制优化，提升弱网环境吞吐。

### 1.3 深度对比：为什么选择 gRPC 优于 WebSocket？

在基于 TLS/Web 容器的反代架构中，传输层主要有 **WebSocket (WS)** 与 **gRPC** 两种选择，它们的差异如下（基于 Gemini 对话补充）：

| 对比维度 | WebSocket (WS) | gRPC (HTTP/2 Multiplexing) | 为什么 gRPC 更好？ |
| :--- | :--- | :--- | :--- |
| **底层协议基础** | HTTP/1.1 Upgrade 协议升级机制 | 原生基于 **HTTP/2** 传输（二进制分帧） | gRPC 与现代微服务 API 流量完全一致，不可区分 |
| **连接复用能力 (Multiplexing)** | **弱**。通常每个 TCP/WS 连接传输单一会话，并发高时频繁建立连接。 | **强**。单条 TCP 连接上通过 HTTP/2 Streams **多路复用**成百上千个并发请求。 | 显著降低并发访问时的 TLS 握手开销与握手往返延迟 (RTT) |
| **头部开销与压缩** | **无头部压缩**。每个数据帧均有独立头部，开销大。 | **HPACK 头部压缩算法**。大幅压缩传输上下文。 | 降低传输数据包体积，减少网络带宽消耗 |
| **DPI 流量行为特征** | 长时间维持单条 HTTP Upgrade 状态的长连接，连接特征明显。 | 行为表现为常规的 RPC 数据调用，与微服务、遥测上报流量无异。 | 极大地降低被机器学习或启发式流控识别为代理的概率 |
| **CDN / 反向代理支持** | 部分 CDN/反代节点需额外调优 timeout 与 upgrade 头部。 | 现代反代（Caddy、Nginx 1.13.10+、Traefik）原生支持 `grpc_pass` / `protocol grpc`。 | 反代开销更小，转发延迟更低 |

---

## 2. 服务器基础信息与初始连接指南

### 2.1 服务器信息

| 项目 | 内容 |
| --- | --- |
| 云厂商 | 阿里云 ECS |
| 实例名称 | `Ubuntu-hodz` |
| 系统 | Ubuntu 24.04.2 LTS |
| 公网 IP | `47.251.167.38` |
| 内网 IP | `172.18.15.22` |
| 域名 | `ljcnb666.asia` |
| SSH 端口 | `22` |
| 初始登录账户 | `admin` |
| 初始登录密码 | `<已脱敏，请通过密码管理器保管或使用 SSH 密钥认证>` |

> [!tip] 安全提示
> 已移除明文密码。建议全面使用 SSH 密钥登录，并关闭密码认证。

### 2.2 从 Windows 终端连接

打开 PowerShell 或 Windows Terminal，运行：

```powershell
ssh admin@47.251.167.38
```

首次连接时若出现主机指纹确认提示，输入 `yes` 并按 Enter。随后输入登录密码。终端中输入密码时不会显示任何字符，这是正常现象。
成功后会看到类似以下提示符：`admin@iZrj9j64kkjbjfdoodvcvmZ:~$`

### 2.3 用 VS Code Remote SSH 连接

1. 在 VS Code 安装 **Remote - SSH** 扩展。
2. 按 `Ctrl + Shift + P`，选择 **Remote-SSH: Connect to Host...**。
3. 选择 **Add New SSH Host...**，填写：`ssh admin@47.251.167.38`
4. 选择 SSH 配置文件后，再次运行 **Remote-SSH: Connect to Host...**，选择刚添加的主机并输入密码。

也可以直接在 `%USERPROFILE%\.ssh\config` 添加：

```sshconfig
Host ubuntu-hodz
    HostName 47.251.167.38
    User admin
    Port 22
```

之后使用：`ssh ubuntu-hodz` 连接。

### 2.4 常用初始系统操作

```bash
uptime             # 查看系统状态
df -h              # 查看磁盘空间
free -h            # 查看内存
sudo apt update    # 更新软件索引
exit               # 退出服务器
```

---

## 3. 阶段一：内核网络栈与高并发调优

### 3.1 TCP BBR 拥塞控制 + 内核参数优化

**操作**：创建 `/etc/sysctl.d/99-custom-network.conf`，写入以下内核参数并通过 `sysctl --system` 生效。

```ini
# 启用 BBR 拥塞控制（Google 出品，提升弱网吞吐）
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# TCP Fast Open（客户端+服务端双向，减少握手延迟）
net.ipv4.tcp_fastopen = 3

# 提高连接队列上限（应对高并发 SYN）
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192

# TIME_WAIT 优化（加速端口回收）
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# 增大 TCP 缓冲区（16MB，提升大带宽吞吐）
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
```

**验证结果**：
```bash
sudo sysctl --system
sysctl net.ipv4.tcp_congestion_control  # 应输出 bbr
lsmod | grep tcp_bbr                    # 确认模块已加载
```

### 3.2 系统文件句柄限制解除

**操作 1**：在 `/etc/security/limits.conf` 追加：
```text
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
```

**操作 2**：创建 `/etc/systemd/system.conf.d/limits.conf`：
```ini
[Manager]
DefaultLimitNOFILE=65535
```

**操作 3**：执行 `systemctl daemon-reexec` 使 systemd 层级生效。

---

## 4. 阶段二：服务器安全基线加固与防护

### 4.1 更新系统软件包及创建用户（可选）

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y curl ca-certificates ufw fail2ban unzip jq

# (可选) 创建日常管理用户
# sudo adduser ops
# sudo usermod -aG sudo ops
```

### 4.2 SSH 密钥认证强制执行（关闭密码登录）

**操作 1 — 服务器端生成 ED25519 密钥对**：
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "admin@ubuntu-hodz"
# 将公钥写入 authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

**操作 2 — 修改 `/etc/ssh/sshd_config`**：
建议先备份：`sudo cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d-%H%M%S)`

```text
PasswordAuthentication no     ← 禁止密码登录
PermitEmptyPasswords no       ← 禁止空密码
PubkeyAuthentication yes      ← 启用密钥认证
PermitRootLogin no            ← 禁止 root 直接登录
```
*(同时扫描并修补 `/etc/ssh/sshd_config.d/` 下所有 cloud-init 覆盖文件)*

**操作 3 — 重启 SSH 服务**：
```bash
sudo sshd -t
sudo systemctl restart ssh
```

**操作 4 — 本地 Windows 端配置**：
将服务器私钥安全保存至本地（如 `C:\Users\LJC\.ssh\ubuntu_hodz_server_ed25519`），更新本地 `config`：
```sshconfig
Host ubuntu-hodz-admin
    HostName 47.251.167.38
    User admin
    Port 22
    IdentityFile ~/.ssh/ubuntu_hodz_server_ed25519
    IdentitiesOnly yes
```
> [!warning] 密码登录已永久关闭
> 从此刻起，只能通过密钥登录。若本地私钥文件丢失，将只能通过云厂商控制台的 VNC 救援通道重置。

### 4.3 UFW 防火墙

**操作**：重置并重新配置 UFW 规则。

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH 远程管理
sudo ufw allow 80/tcp     # HTTP (→ HTTPS 301)
sudo ufw allow 443/tcp    # HTTPS / HTTP/2
sudo ufw allow 443/udp    # QUIC / HTTP/3
sudo ufw enable
sudo ufw status verbose
```

### 4.4 Fail2ban 防暴力破解

**操作**：安装 fail2ban 并创建 `/etc/fail2ban/jail.local`：

```ini
[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 5          # 5 次失败后封禁
bantime  = 3600       # 封禁 1 小时
findtime = 600        # 10 分钟窗口期
backend  = systemd
```

**验证**：
```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

---

## 5. 阶段三：网站与云盘伪装方案详解 (Gemini 对话精要)

为了使 VPS 表现为一个合法的 Web 服务器，推荐以下两种伪装方案：

### 方案 A：技术文档站 / 博客站点伪装（推荐，轻量稳定，当前部署选择）
- **适用场景**：个人开发者、技术人员。
- **内容示例**：STM32Cube 固件库参考文档、Doxygen 生成的 C++ API 手册、VitePress / Docusaurus 静态文档。
- **部署方式**：将网页放入 `/var/www/html`（如 `index.html` 和 `404.html`）。
- **优点**：纯静态 HTML/JS/CSS，极低 CPU/内存占用（< 10MB），抗并发压力极高，且内容真实专业，不暴露代理用途。

### 方案 B：私有云盘 / 文件分享站伪装（Cloudreve / Alist）
- **适用场景**：平时兼顾个人网盘、文件传输、团队知识库需求。
- **部署方式**：本地运行 Cloudreve 或 Alist（监听 `127.0.0.1:5212`），Caddy 将其余流量 `reverse_proxy 127.0.0.1:5212`。
- **伪装效果**：探测器和浏览器访问直接展示合法的个人网盘登录页或公共分享目录，完全契合 HTTPS 站点的逻辑。

---

## 6. 阶段四：核心组件安装与配置 (sing-box + Caddy)

### 6.1 安装并配置 sing-box VLESS + gRPC 多路复用

优先使用 sing-box 官方软件源，不使用来历不明的一键脚本。

```bash
# 安装
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://sing-box.app/gpg.key -o /etc/apt/keyrings/sagernet.asc
echo "deb [signed-by=/etc/apt/keyrings/sagernet.asc] https://deb.sagernet.org/ * *" | sudo tee /etc/apt/sources.list.d/sagernet.list
sudo apt update && sudo apt install -y sing-box
```

编写 `/etc/sing-box/config.json`（UUID 用本机 `cat /proc/sys/kernel/random/uuid` 随机生成并安全保存）：

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
        "service_name": "com.asia.telemetry.sync.v3"
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

**关键设计**：
- 绑定 `127.0.0.1:10000` 避免代理核心暴露公网。
- 日志级别 `warn` 保护隐私不记录访问目标。
- gRPC 服务名 `com.asia.telemetry.sync.v3` 伪装为遥测数据同步服务，DPI 特征低（不应视为绝对规避机制，需配合正常流量）。

启动校验：
```bash
sudo install -o root -g sing-box -m 640 /etc/sing-box/config.json /etc/sing-box/config.json
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl enable --now sing-box
```

### 6.2 安装并配置 Caddy L7 反向代理 + HTTP/3

```bash
# 安装
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# 准备静态站目录
sudo mkdir -p /var/www/html
sudo chown -R caddy:caddy /var/www/html
sudo find /var/www/html -type d -exec chmod 755 {} +
sudo find /var/www/html -type f -exec chmod 644 {} +
```

重写 `/etc/caddy/Caddyfile`：

```caddy
ljcnb666.asia {
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
    encode gzip zstd
    file_server

    # 2. gRPC 精准匹配分流 (h2c 明文 HTTP/2 转发至本地 sing-box)
    @grpc_telemetry {
        protocol grpc
        path /com.asia.telemetry.sync.v3/*
    }
    reverse_proxy @grpc_telemetry h2c://127.0.0.1:10000 {
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

校验并重载：
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
```

---

## 7. 最终验证、客户端配置与交付

### 7.1 服务状态汇总与验收清单

```bash
systemctl is-active sing-box caddy fail2ban
ss -lntup | grep -E ':(22|80|443|10000)\b'
sudo ufw status numbered
curl -I https://ljcnb666.asia/
```

**期望结果**：`10000` 端口只出现在 `127.0.0.1`；公网只暴露计划内 22, 80, 443 端口；网站返回 200 OK 预期状态码；证书有效。

### 7.2 节点连接参数表

| 参数 | 值 | 说明 |
|------|------|------|
| **地址 (SNI / Host)** | `ljcnb666.asia` | 你的解析域名（或 CDN 优选 IP） |
| **端口** | `443` | 标准 HTTPS 端口 |
| **UUID** | `<服务端凭据>` | 唯一身份验证凭据 |
| **协议** | VLESS | 无握手特征 |
| **加密** | none | TLS 层已加密 |
| **传输** | gRPC | 多路复用传输 |
| **ServiceName** | `com.asia.telemetry.sync.v3` | 需与 Caddy/sing-box 完全一致 |
| **gRPC Mode** | gun | 标准单连接多流模式 |
| **TLS** | ✅ 开启 | 必须校验证书 |
| **ALPN** | h2 | 协商 HTTP/2 协议 |

### 7.3 通用 VLESS 一键导入链接模板

仅在本地生成，并通过密码管理器或加密渠道传递：

```text
vless://<YOUR_UUID>@ljcnb666.asia:443?encryption=none&security=tls&sni=ljcnb666.asia&alpn=h2&type=grpc&serviceName=com.asia.telemetry.sync.v3&mode=gun#Ubuntu-hodz-Node
```

### 7.4 排错指南

| 故障现象 | 排查方向 | 处理方法 |
| :--- | :--- | :--- |
| **客户端报错 `EOF` 或 `connection refused`** | 1. Caddy 未正常运行<br>2. sing-box 回环端口未监听 | `sudo systemctl status caddy`<br>`sudo ss -tlnp \| grep 10000` |
| **客户端报错 `bad status 404/400`** | ServiceName 或 Caddy Path 匹配不一致 | 检查 Caddyfile 中 `path /<service_name>/*` 与客户端配置是否精确匹配 |
| **浏览器访问显示证书不安全** | ACME 域名验证失败（DNS 未生效或 80 端口被封） | 检查 `dig +short ljcnb666.asia` 及云安全组 80/443 是否放行 |

---

## 8. 备份、回滚与日常维护规范

### 8.1 运维规范
- 每次改动 `/etc/sing-box/config.json`、`/etc/caddy/Caddyfile` 前务必创建时间戳备份（`cp -a config config.bak.$(date +%Y%m%d)`）。
- 永远先执行 `sing-box check` / `caddy validate`，通过后再 `reload/restart`。
- 定期查看日志：`sudo journalctl -u sing-box -u caddy -f --no-pager`。
- 及时更新系统与组件；轮换泄露过的 SSH 密钥、密码和节点凭据。

### 8.2 SSH 私钥与凭据管理
> [!tip] 安全规范
> 部署产生的私钥与敏感密码已脱敏。请妥善保存在本地安全路径（如 `C:\Users\LJC\.ssh\` 或 Bitwarden 密码管理器中），切勿提交至公网 Git 仓库。

### 8.3 服务器端变更索引清单
| 文件路径 | 状态 | 用途 |
|----------|------|------|
| `/etc/sysctl.d/99-custom-network.conf` | 新建 | BBR + 高并发内核参数 |
| `/etc/security/limits.conf` | 追加 | nofile 65535 句柄限制 |
| `/etc/ssh/sshd_config` | 修改 | 禁用密码登录，启用密钥认证 |
| `/home/admin/.ssh/authorized_keys` | 修改 | 存储本地公钥 |
| `/etc/sing-box/config.json` | 重写 | VLESS + gRPC 配置 |
| `/etc/caddy/Caddyfile` | 重写 | TLS + 反代 + 伪装路由 |
| `/var/www/html/` | 新建 | 存放 `index.html` 及 `404.html` |
| `/etc/fail2ban/jail.local` | 新建 | SSH 防暴力破解规则 |
| `/etc/ufw/` | 修改 | 防火墙端口放行规则 |

---

> **结语**：本全案汇总证明了 “Caddy + sing-box + UFW + Fail2ban + BBR” 是极具工程可行性的黄金组合。回环绑定、配置备份、语法校验、最小端口暴露、证书自动续期和端到端验收则是保证服务稳定与隐蔽的核心最佳实践。
