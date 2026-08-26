# 零信任加密通信网络部署记录

> [!info] 部署信息
> - **服务器**：Ubuntu-hodz（阿里云 ECS，Ubuntu 24.04.2 LTS）
> - **公网 IP**：`47.251.167.38`
> - **域名**：`ljcnb666.asia`
> - **执行时间**：2026-08-26 20:02 (UTC+8)
> - **部署方式**：本地 Python paramiko SSH → 远程 Bash 脚本自动化执行
> - **核心组件**：sing-box v1.13.19 + Caddy + UFW + Fail2ban

---

## 总体架构

```
客户端 (VLESS gRPC)
    │
    ▼ TLS 1.3 / HTTPS (端口 443)
┌─────────────────────────────┐
│  Caddy (L7 反向代理)         │
│  - 自动 ACME 证书管理        │
│  - HTTP/3 (QUIC) 支持        │
│  - 安全响应头 (HSTS 等)      │
│  - 伪装静态站点兜底           │
│  - gRPC ServiceName 精确分流  │
└──────────┬──────────────────┘
           │ h2c (明文 HTTP/2)
           ▼ 仅回环 127.0.0.1:10000
┌─────────────────────────────┐
│  sing-box (VLESS 入站)       │
│  - gRPC 多路复用传输          │
│  - 直连出站 (DIRECT)         │
└──────────┬──────────────────┘
           │
           ▼
        互联网
```

---

## 阶段一：内核网络栈与高并发调优

### 1.1 TCP BBR 拥塞控制 + 内核参数优化

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
```
net.ipv4.tcp_congestion_control = bbr  ✅
net.core.default_qdisc = fq           ✅
tcp_bbr 内核模块已加载 (20480)          ✅
```

### 1.2 系统文件句柄限制解除

**操作 1**：在 `/etc/security/limits.conf` 追加：
```
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

## 阶段二：服务器安全基线加固

### 2.1 SSH 密钥认证（强制，密码登录已关闭）

**操作 1 — 服务器端生成 ED25519 密钥对**：
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "admin@ubuntu-hodz"
```

- 密钥指纹：`SHA256:78Cfu0Xr2h848e2hdGONVgSwvAG7W2BxqafkNxtPhGs`
- 公钥已写入 `/home/admin/.ssh/authorized_keys`（权限 `600`）
- `.ssh` 目录权限 `700`
- 密钥对也复制到了 `/home/admin/.ssh/` 下，确保 admin 用户可用

**操作 2 — 修改 `/etc/ssh/sshd_config`**：
```
PasswordAuthentication no     ← 禁止密码登录
PermitEmptyPasswords no       ← 禁止空密码
PubkeyAuthentication yes      ← 启用密钥认证
```
同时扫描并修补了 `/etc/ssh/sshd_config.d/` 下所有 cloud-init 覆盖文件。

**操作 3 — 重启 SSH 服务**：`systemctl restart ssh`

**操作 4 — 本地 Windows 端配置**：

将服务器私钥保存至本地：
```
C:\Users\LJC\.ssh\ubuntu_hodz_server_ed25519
```

更新本地 SSH 配置 `C:\Users\LJC\.ssh\config`：
```sshconfig
Host ubuntu-hodz
    HostName 47.251.167.38
    User root
    Port 22
    IdentityFile ~/.ssh/ubuntu_hodz_server_ed25519
    IdentitiesOnly yes

Host ubuntu-hodz-admin
    HostName 47.251.167.38
    User admin
    Port 22
    IdentityFile ~/.ssh/ubuntu_hodz_server_ed25519
    IdentitiesOnly yes
```

**现在的 SSH 登录方式**：
```powershell
ssh ubuntu-hodz-admin     # admin 用户
ssh ubuntu-hodz           # root 用户
```

> [!warning] 密码登录已永久关闭
> 从此刻起，只能通过密钥登录。如果本地私钥文件 `ubuntu_hodz_server_ed25519` 丢失，将无法通过 SSH 登录服务器，只能通过阿里云控制台的 VNC 远程连接重置。

### 2.2 UFW 防火墙

**操作**：重置并重新配置 UFW 规则。

```
默认策略：deny (入站), allow (出站)

放行规则：
┌──────────┬────────┬───────────────────┐
│ 端口     │ 协议   │ 用途              │
├──────────┼────────┼───────────────────┤
│ 22/tcp   │ TCP    │ SSH 远程管理      │
│ 80/tcp   │ TCP    │ HTTP (→ HTTPS 301)│
│ 443/tcp  │ TCP    │ HTTPS / HTTP/2    │
│ 443/udp  │ UDP    │ QUIC / HTTP/3     │
└──────────┴────────┴───────────────────┘
```

### 2.3 Fail2ban 防暴力破解

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

**验证**：fail2ban sshd jail 运行中，当前无封禁 IP。

---

## 阶段三：sing-box VLESS + gRPC 多路复用

### 3.1 为什么从 WebSocket 升级到 gRPC

| 对比项 | WebSocket | gRPC |
|--------|-----------|------|
| 协议基础 | HTTP/1.1 Upgrade | HTTP/2 原生 |
| 多路复用 | ❌ 单连接单流 | ✅ 单连接多流 |
| 头部压缩 | ❌ 无 | ✅ HPACK |
| 连接特征 | 长连接明显 | 与正常 API 流量混合 |
| CDN 兼容 | 一般 | 优秀 |

### 3.2 服务端配置

**操作**：重写 `/etc/sing-box/config.json`：

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
          "uuid": "13faf372-ddad-46f7-b72a-3944bd7963fc",
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
- **绑定 `127.0.0.1:10000`**：仅监听回环接口，外部无法直连，必须经过 Caddy TLS 层
- **日志级别 `warn`**：不记录客户端 IP 和访问目标，保护隐私
- **gRPC 服务名 `com.asia.telemetry.sync.v3`**：伪装为遥测数据同步服务，DPI 特征极低
- **文件权限**：`root:sing-box 640`

**验证**：
```
sing-box check → 配置校验通过 ✅
systemctl restart sing-box → 服务启动成功 ✅
ss -tlnp → 127.0.0.1:10000 监听中 ✅
```

---

## 阶段四：Caddy L7 反向代理 + HTTP/3

### 4.1 Caddyfile 配置

**操作**：重写 `/etc/caddy/Caddyfile`：

```caddy
ljcnb666.asia {
    tls {
        protocols tls1.2 tls1.3
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        -Server
    }

    root * /var/www/html
    file_server

    @grpc_telemetry {
        protocol grpc
        path /com.asia.telemetry.sync.v3/*
    }
    reverse_proxy @grpc_telemetry h2c://127.0.0.1:10000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
    }

    handle_errors {
        @404 {
            expression {http.error.status_code} == 404
        }
        rewrite @404 /404.html
        file_server
    }
}
```

**功能分解**：

| 功能 | 说明 |
|------|------|
| **TLS 自动管理** | Caddy 自动通过 ACME 申请 Let's Encrypt 证书，支持 TLS 1.2 + 1.3 |
| **HTTP/3 (QUIC)** | Caddy 默认开启，监听 443/udp，弱网环境传输更快 |
| **HSTS 头** | 强制浏览器使用 HTTPS，max-age 1 年，含子域和 preload |
| **隐藏 Server 头** | 删除 Caddy 默认的 `Server` 响应头，减少指纹暴露 |
| **伪装站点** | `/var/www/html/index.html` — 简洁的欢迎页，非代理流量看到正常网站 |
| **gRPC 精确路由** | 仅 `protocol grpc` + `path /com.asia.telemetry.sync.v3/*` 的流量才转发到 sing-box |
| **h2c 反代** | 以明文 HTTP/2 转发到本地 sing-box（TLS 在 Caddy 层终止） |
| **自定义 404** | 访问不存在的路径返回美观的 404 页面 |

### 4.2 伪装静态站点

**操作**：创建了两个 HTML 文件：

- `/var/www/html/index.html` — 欢迎页（"Welcome to ljcnb666.asia"）
- `/var/www/html/404.html` — 自定义 404 页面

直接访问 `https://ljcnb666.asia` 会看到正常网站，不会暴露代理用途。

**验证**：
```
caddy validate → 配置校验通过 ✅
systemctl reload caddy → 服务重载成功 ✅
443/tcp 监听中 (Caddy) ✅
443/udp 监听中 (QUIC)  ✅
```

---

## 阶段五：最终验证与交付

### 5.1 服务状态汇总

| 服务 | 版本 | 状态 | 监听 |
|------|------|------|------|
| sing-box | v1.13.19 | 🟢 active | 127.0.0.1:10000 (TCP) |
| Caddy | — | 🟢 active | *:443 (TCP+UDP), *:80 (TCP) |
| Fail2ban | — | 🟢 active | — |
| UFW | — | 🟢 active | 22, 80, 443/tcp, 443/udp |
| TCP BBR | — | 🟢 enabled | — |

### 5.2 节点连接参数

| 参数 | 值 |
|------|------|
| **地址 (SNI / Host)** | `ljcnb666.asia` |
| **端口** | `443` |
| **UUID** | `13faf372-ddad-46f7-b72a-3944bd7963fc` |
| **协议** | VLESS |
| **加密** | none (TLS 层加密) |
| **传输** | gRPC |
| **ServiceName** | `com.asia.telemetry.sync.v3` |
| **gRPC Mode** | gun |
| **TLS** | ✅ 开启 |
| **ALPN** | h2 |

### 5.3 客户端一键导入链接

```
vless://13faf372-ddad-46f7-b72a-3944bd7963fc@ljcnb666.asia:443?encryption=none&security=tls&sni=ljcnb666.asia&alpn=h2&type=grpc&serviceName=com.asia.telemetry.sync.v3&mode=gun#ljcnb666-vless-grpc
```

复制此链接到 v2rayN / v2rayNG / NekoBox / Clash Verge 等客户端，选择「从剪贴板导入」即可使用。

---

## 本地 Windows 端变更清单

本次部署在本地 Windows 上做了以下改动：

| 文件 | 操作 | 说明 |
|------|------|------|
| `C:\Users\LJC\.ssh\config` | 修改 | 添加 ubuntu-hodz / ubuntu-hodz-admin 主机别名，配置密钥路径 |
| `C:\Users\LJC\.ssh\ubuntu_hodz_server_ed25519` | 新建 | 服务器 ED25519 私钥（用于 SSH 登录） |
| `C:\Users\LJC\.ssh\ubuntu_hodz_ed25519` | 新建 | 本地生成的部署用 ED25519 密钥对（备用） |
| `C:\Users\LJC\.ssh\ubuntu_hodz_ed25519.pub` | 新建 | 上述密钥的公钥 |

---

## 服务器端变更文件清单

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `/etc/sysctl.d/99-custom-network.conf` | 新建 | BBR + 高并发内核参数 |
| `/etc/security/limits.conf` | 追加 | nofile 65535 |
| `/etc/systemd/system.conf.d/limits.conf` | 新建 | systemd 文件描述符限制 |
| `/etc/ssh/sshd_config` | 修改 | 禁用密码登录，启用密钥认证 |
| `/home/admin/.ssh/id_ed25519` | 新建 | 服务器 ED25519 私钥 |
| `/home/admin/.ssh/id_ed25519.pub` | 新建 | 服务器 ED25519 公钥 |
| `/home/admin/.ssh/authorized_keys` | 修改 | 添加公钥条目 |
| `/etc/sing-box/config.json` | 重写 | VLESS + gRPC 配置 |
| `/etc/caddy/Caddyfile` | 重写 | TLS + 反代 + 伪装站点 |
| `/var/www/html/index.html` | 新建 | 伪装欢迎页 |
| `/var/www/html/404.html` | 新建 | 自定义 404 页面 |
| `/etc/fail2ban/jail.local` | 新建 | SSH 防暴力破解规则 |
| `/etc/ufw/` | 修改 | 防火墙规则（22, 80, 443/tcp, 443/udp） |

---

## SSH 私钥与凭据管理
 
> [!tip] 安全规范
> 私钥与敏感密码已做脱敏处理，请妥善保存在本地安全路径（如 `C:\Users\LJC\.ssh\` 或 KeePass/1Password/Bitwarden 密码管理器中），切勿提交至公网 Git 仓库。
 
公钥信息：
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICr7KEow5hIHRIEP4Xd98l/gMrSgj47nb4w12o4Ve/P7 admin@ubuntu-hodz
```

---

## 日常运维命令速查

```bash
# SSH 登录
ssh ubuntu-hodz-admin

# 查看 sing-box 状态与日志
sudo systemctl status sing-box
sudo journalctl -u sing-box -f --no-pager

# 查看 Caddy 状态与日志
sudo systemctl status caddy
sudo journalctl -u caddy -f --no-pager

# 修改 sing-box 配置后
sudo nano /etc/sing-box/config.json
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl restart sing-box

# 修改 Caddy 配置后
sudo nano /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy

# 查看防火墙状态
sudo ufw status verbose

# 查看 fail2ban 封禁情况
sudo fail2ban-client status sshd

# 查看端口监听
sudo ss -tlnp
sudo ss -ulnp

# 查看 BBR 状态
sysctl net.ipv4.tcp_congestion_control

# 查看系统资源
htop
df -h
free -h
```
