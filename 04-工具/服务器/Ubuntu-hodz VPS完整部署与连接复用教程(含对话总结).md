# Ubuntu-hodz VPS 零信任部署与连接完整教程 (对话总结合并版)

> [!important] 架构定位与安全规范
> 本教程完整汇总并无删减地合并了「Ubuntu-hodz 服务器连接教程」、「Ubuntu-hodz 零信任加密通信部署记录」、「Ubuntu-hodz 实时服务器状态」以及历次部署调试的全部细节与最新状态。
>
> 核心基于 **Caddy 2 + sing-box (VLESS-WebSocket) + UFW + Fail2ban + Linux BBR** 黄金组合，实现 **443 端口多路复用（正常 Web 伪装站点 / STM32 文档云盘浏览与加密通信流量共存）**。

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
                             │  - 路径精确分流 (/api/v2/stream/sync) │
                             └──────┬─────────────────────────┬──────┘
                                    │                         │
                 WebSocket 升级与指定 Path 流量              普通 Web 流量 / 伪装站点访问
                                    │                         │
                                    ▼ (HTTP/1.1 WS 反代)      ▼
                      ┌───────────────────────────┐   ┌───────────────────────────┐
                      │    sing-box 核心服务      │   │  真实业务 / 伪装云盘服务  │
                      │  - 仅监听 127.0.0.1:10000 │   │  1. STM32 固件库静态文档  │
                      │  - VLESS + WebSocket 传输 │   │  2. file_server 目录浏览  │
                      │  - 纯直连 Direct 出站     │   │  3. 隐藏隐藏文件 (hide .*)│
                      └─────────────┬─────────────┘   └───────────────────────────┘
                                    │
                                    ▼
                                目标互联网
```

### 1.2 组件职责与安全防探测设计

- **sing-box**：仅提供已授权用户的加密通信隧道。**端口不直连**，严格绑定监听 `127.0.0.1:10000` 本地回环地址，外部无法直连，从根本上杜绝主动探测与端口扫描。
- **Caddy**：自动申请与续期 Let's Encrypt 证书，统一完成 TLS 握手，提供合法的 TLS 指纹与有效 CA 证书。它托管伪装站点（STM32 文档与私有云盘文件浏览），并将特定路径的 WebSocket 升级流量反向代理到本地回环端口。
- **UFW**：默认拒绝入站，仅放行 SSH (22)、HTTP (80)、HTTPS (443 tcp/udp)。
- **Fail2ban**：监控 SSH 认证日志，防止暴力破解。
- **BBR**：持久化开启 TCP BBR 拥塞控制与底层内核网络调优，提升弱网环境下的吞吐量与连接稳定性。

---

## 2. 服务器基础信息与连接指南

### 2.1 服务器信息

| 项目 | 内容 |
| --- | --- |
| 云厂商 | 阿里云 ECS |
| 实例名称 | `Ubuntu-hodz` |
| 系统 | Ubuntu 24.04.2 LTS (Kernel 6.8.0) |
| 公网 IP | `47.251.167.38` |
| 内网 IP | `172.18.15.22` |
| 绑定域名 | `ljcnb666.asia` |
| SSH 端口 | `22` |
| 登录账户 | `admin` / `root` |
| 认证方式 | 密码登录与 **ED25519 密钥认证** 双重支持；密码不写入公开文档 |

---

### 2.2 SSH 连接配置与方法

#### 方式一：终端直接连接 (PowerShell / Windows Terminal)
```powershell
ssh admin@47.251.167.38
# 输入服务器密码（不要写入仓库）
```

#### 方式二：使用本地 SSH 别名与密钥 (已配置于本地 `%USERPROFILE%\.ssh\config`)
```sshconfig
Host ubuntu-hodz-admin
    HostName 47.251.167.38
    User admin
    Port 22
    IdentityFile ~/.ssh/ubuntu_hodz_server_ed25519
    IdentitiesOnly yes

Host ubuntu-hodz
    HostName 47.251.167.38
    User root
    Port 22
    IdentityFile ~/.ssh/ubuntu_hodz_server_ed25519
    IdentitiesOnly yes
```
直接运行：
```powershell
ssh ubuntu-hodz-admin
```

---

## 3. 阶段一：内核网络栈与高并发调优

### 3.1 TCP BBR 拥塞控制与参数优化
配置文件路径：`/etc/sysctl.d/99-custom-network.conf`

```ini
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
```
生效并验证：
```bash
sudo sysctl --system
sysctl net.ipv4.tcp_congestion_control  # 输出: bbr
sysctl net.core.default_qdisc           # 输出: fq
lsmod | grep bbr                        # 确认模块加载
```

### 3.2 解除系统文件句柄限制
- `/etc/security/limits.conf`：
  ```text
  * soft nofile 65535
  * hard nofile 65535
  root soft nofile 65535
  root hard nofile 65535
  ```
- `/etc/systemd/system.conf.d/limits.conf`：
  ```ini
  [Manager]
  DefaultLimitNOFILE=65535
  ```
- 执行 `sudo systemctl daemon-reexec` 生效。

---

## 4. 阶段二：服务器安全基线与探针清理

### 4.1 UFW 防火墙设置
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (跳转 HTTPS)
sudo ufw allow 443/tcp    # HTTPS / HTTP/2
sudo ufw allow 443/udp    # QUIC / HTTP/3
sudo ufw enable
```

### 4.2 Fail2ban 防爆破设置 (`/etc/fail2ban/jail.local`)
```ini
[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 5
bantime  = 3600
findtime = 600
backend  = systemd
```

### 4.3 彻底卸载阿里云监控探针 (释放内存并阻断云端内省)
```bash
systemctl stop aegis aliyundun AssistDaemon 2>/dev/null || true
systemctl disable aegis aliyundun AssistDaemon 2>/dev/null || true
/usr/local/aegis/aegis_uninstall/uninstall.sh 2>/dev/null || true
/usr/local/aegis/aegis_quartz/uninstall.sh 2>/dev/null || true
pkill -9 AliYunDun 2>/dev/null || true
pkill -9 AliHids 2>/dev/null || true
rm -rf /usr/local/aegis /usr/local/share/aliyun-assist
```

---

## 5. 阶段三：核心服务配置 (sing-box + Caddy)

### 5.1 sing-box 服务端配置 (`/etc/sing-box/config.json`)
```json
{
  "log": {
    "level": "warn",
    "timestamp": true
  },
  "inbounds": [
    {
      "type": "vless",
      "tag": "vless-ws-in",
      "listen": "127.0.0.1",
      "listen_port": 10000,
      "users": [
        {
          "uuid": "<VLESS_UUID>",
          "flow": ""
        }
      ],
      "transport": {
        "type": "ws",
        "path": "/api/v2/stream/sync"
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

校验并重载：
```bash
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl restart sing-box
```

---

### 5.2 Caddy 伪装与反向代理配置 (`/etc/caddy/Caddyfile`)
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

    # 【WebSocket 流量分流与静态伪装】
    route {
        @ws_path {
            path /api/v2/stream/sync
        }
        reverse_proxy @ws_path 127.0.0.1:10000 {
            header_up Host {host}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
        }

        root * /var/www/html
        file_server browse {
            hide .*
        }
    }
}
```

校验并重载：
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

---

### 5.3 伪装站点内容部署
- `/var/www/html/index.html`：STM32Cube 官方固件库发布说明。
- `/var/www/html/_htmresc/`：文档静态图片、样式资源。
- 目录浏览权限：`chown -R caddy:caddy /var/www/html && chmod 755 /var/www/html`。
- 效果：普通用户或探测扫描直接访问域名呈现真实的嵌入式开发文档站点及云盘文件列表。

---

## 6. 节点连接参数与客户端配置

### 6.1 节点参数对照表

| 参数项 | 配置值 | 说明 |
|---|---|---|
| **协议 (Protocol)** | `VLESS` | 无握手特征轻量协议 |
| **地址 (Address)** | `ljcnb666.asia` | 域名 (或 CDN IP) |
| **端口 (Port)** | `443` | 标准 HTTPS 端口 |
| **用户 ID (UUID)** | `<VLESS_UUID>` | 服务端唯一鉴权 ID，不提交真实值 |
| **加密 (Encryption)** | `none` | 由外层 TLS 保护 |
| **传输协议 (Network)** | `ws` (WebSocket) | 兼容性极高的传输层 |
| **伪装路径 (Path)** | `/api/v2/stream/sync` | 与 Caddyfile 精确匹配 |
| **Host / SNI** | `ljcnb666.asia` | 域名 |
| **底层传输安全 (TLS)** | `tls` | 开启 |
| **ALPN** | `h2,http/1.1` | 自动协商 |

---

### 6.2 客户端一键导入链接 (v2rayN / NekoBox / Clash)

```text
vless://<VLESS_UUID>@ljcnb666.asia:443?encryption=none&security=tls&sni=ljcnb666.asia&type=ws&host=ljcnb666.asia&path=%2Fapi%2Fv2%2Fstream%2Fsync#ljcnb666-vless-ws
```

---

## 7. 日常运维命令速查

```bash
# 1. 查看服务状态
systemctl status sing-box --no-pager
systemctl status caddy --no-pager
systemctl status fail2ban --no-pager

# 2. 修改配置后重载
sudo sing-box check -c /etc/sing-box/config.json && sudo systemctl restart sing-box
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy

# 3. 检查端口与防火墙
sudo ss -tlnp | grep -E '(:10000|:443|:80|:22)'
sudo ufw status verbose

# 4. 查看实时日志
sudo journalctl -u sing-box -f --no-pager
sudo journalctl -u caddy -f --no-pager
```

---

## 8. 2026-08-27 直连节点优化记录与速度对比

> [!note] 当前状态
> 本节是在保留上文原始部署方案的基础上追加的实测记录。旧的 Caddy + sing-box 方案仍保留，可用于回滚；当前推荐优先测试新增的 sing-box 直连 `2053` 节点。

### 8.1 当前双路径架构

```text
旧路径：客户端
  -> Caddy :443 / :8443 (TLS + WebSocket 反向代理)
  -> sing-box 127.0.0.1:10000
  -> direct-out

新路径：客户端
  -> sing-box :2053 (TLS + WebSocket 直连)
  -> direct-out
```

新路径使用的入站标签为 `vless-direct-2053`，配置特点如下：

```json
{
  "type": "vless",
  "tag": "vless-direct-2053",
  "listen": "0.0.0.0",
  "listen_port": 2053,
  "tcp_fast_open": true,
  "tls": {
    "enabled": true,
    "certificate_path": "/etc/sing-box/certs/ljcnb666.asia.crt",
    "key_path": "/etc/sing-box/certs/ljcnb666.asia.key"
  },
  "transport": {
    "type": "ws",
    "path": "/api/v2/stream/sync"
  },
  "multiplex": {
    "enabled": true
  }
}
```

`2053/tcp` 已加入 UFW，Caddy 仍继续监听 `443` 和 `8443`，所以新增直连入站不会覆盖原节点。

### 8.2 当前直连节点参数

```text
地址：ljcnb666.asia
端口：2053
协议：VLESS
传输：WebSocket
TLS：开启
SNI：ljcnb666.asia
Host：ljcnb666.asia
Path：/api/v2/stream/sync
UUID：<VLESS_UUID>
```

v2rayN 一键导入：

```text
vless://<VLESS_UUID>@ljcnb666.asia:2053?encryption=none&security=tls&sni=ljcnb666.asia&type=ws&host=ljcnb666.asia&path=%2Fapi%2Fv2%2Fstream%2Fsync#ljcnb666-direct-2053
```

### 8.3 与 us46 的关键差异

| 项目 | 原 Ubuntu-hodz 方案 | 当前直连方案 | us46 快速方案 |
| --- | --- | --- | --- |
| 公网接入 | Caddy | sing-box | sing-box |
| VLESS TLS 终止 | Caddy | sing-box | sing-box |
| VLESS 监听 | 回环 `127.0.0.1:10000` | 公网 `:2053` | 公网 `:2053` |
| WebSocket 反代 | 有 | 无 | 无 |
| TCP Fast Open | 原文记录有，但入站未显式配置 | 已开启 | 已开启 |
| Multiplex | 无 | 已开启 | 已开启 |
| 网卡队列 | 曾为 `fq_codel` | 已改为 `fq` | `fq` |
| 拥塞控制 | BBR | BBR | BBR |
| 内核 | Ubuntu 默认 6.8 | Ubuntu 默认 6.8 | XanMod 6.16 |

### 8.4 为什么旧方案速度慢

之前的判断主要依据 ping，不足以解释下载速度差异。实际测试得到的证据如下：

| 测试路径 | 结果 |
| --- | ---: |
| 服务器本机直连 CacheFly | 约 `178 MB/s` |
| 电脑直连 ljc `443` 的普通 HTTPS 文件 | 约 `0.28 MB/s` |
| 电脑直连 ljc `8443` 的普通 HTTPS 文件 | 约 `0.59 MB/s` |
| 电脑经 ljc `8443` VLESS/WS | 约 `0.71 MB/s` |
| 电脑经 ljc `2053` 直连 VLESS/WS | 约 `1.07 MB/s` |
| 战网切换到直连 `2053` 后截图实测 | 约 `10.47 MB/s` |

旧方案慢的主要原因是多个因素叠加：

1. `443` 上的客户端 TCP 连接 RTT 约 `176-202 ms`，服务器端能观察到明显重传；服务器 CPU、内存、网卡错误和本机公网出口均正常。
2. 旧路径每条数据连接都要经过 `Caddy TLS -> Caddy WebSocket 反代 -> sing-box`，多了一层 L7 代理和数据转发。
3. `443` 与 `8443` 的同内容 HTTPS 对照已经出现明显差异，说明端口路径或策略也会影响吞吐。
4. `us46` 的公网 IP、运营商回程和跨境线路更好，这是 ping 接近时仍能出现十倍吞吐差距的主要原因之一。
5. XanMod 内核、Fast Open 和 multiplex 可以减少开销，但不能修复跨境链路的丢包，因此它们不是 us46 快的唯一原因。

### 8.5 已执行的优化与验证

- 网卡队列从 `fq_codel` 调整为 `fq`。
- 持久化启用 BBR 和 `net.ipv4.tcp_mtu_probing=1`。
- 保留原 Caddy 伪装站和 `443/8443` 回滚路径。
- 新增 sing-box 直连 TLS VLESS `2053`。
- 新节点已使用本机独立 Xray 端到端验证，配置检查通过，sing-box 与 Caddy 均为 active。

### 8.6 证书与回滚注意事项

直连 `2053` 使用的是从 Caddy ACME 存储复制出的证书：

```text
/etc/sing-box/certs/ljcnb666.asia.crt
/etc/sing-box/certs/ljcnb666.asia.key
```

Caddy 续期后不会自动更新这两份复制文件。证书续期后需要重新复制证书并重启 sing-box，否则直连节点可能因证书过期失效。原 Caddy 节点不受此问题影响。

服务器配置备份：

```text
/etc/sing-box/config.json.before-direct-2053
/etc/caddy/Caddyfile.before-port-test
```

如需回滚直连入站，应先从 `/etc/sing-box/config.json` 删除 `vless-direct-2053`，再执行：

```bash
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl restart sing-box
```

回滚不会删除 Caddy 的 `443/8443` 节点。

---

## 9. 2026-08-27 最终三协议部署与使用建议

> [!important] 当前推荐
> 当前服务器同时运行三种接入方式：`2054/udp` Hysteria2、`2055/tcp` VLESS-Reality、`2053/tcp` VLESS-WebSocket。三者共用同一个 `direct-out` 出站，但传输层不同，互相独立。现有 Caddy `443/8443` 入口继续保留。

### 9.1 三协议最终对照

| 协议与端口 | 传输层 | 受限网络兼容性 | 大文件吞吐 | 推荐场景 |
| --- | --- | --- | --- | --- |
| `Hysteria2 :2054/udp` | QUIC/UDP | 依赖 UDP 是否畅通 | 当前三者最快 | 战网、Steam、视频、大文件 |
| `VLESS-Reality :2055/tcp` | TCP + Reality | TCP 兼容性好 | 中高，受 TCP 丢包影响 | 日常 TCP、网页、办公、备用 |
| `VLESS-WS :2053/tcp` | TCP + WebSocket | 客户端兼容性最好 | 当前最慢 | 老旧客户端或最终保底 |

受控测试中，使用同一台电脑、同一个 CacheFly 10 MB 文件、三条连接顺序测试：

```text
Hysteria2 2054：约 6.19 MB/s
VLESS-Reality 2055：约 2.41 MB/s
VLESS-WS 2053：约 0.89 MB/s
```

战网实际下载截图曾出现约 `14.5 MB/s`（Hysteria2）、`9.8 MB/s`（Reality）和 `0.1 MB/s`（WS）。不同 CDN、连接并发数、时间段和客户端缓存会造成明显波动，不能把单次结果当作永久保证。

### 9.2 Hysteria2 服务端配置

服务端入站标签：`hysteria2-2054`。

```json
{
  "type": "hysteria2",
  "tag": "hysteria2-2054",
  "listen": "0.0.0.0",
  "listen_port": 2054,
  "users": [
    { "password": "<HY2_PASSWORD>" }
  ],
  "tls": {
    "enabled": true,
    "certificate_path": "/etc/sing-box/certs/ljcnb666.asia.crt",
    "key_path": "/etc/sing-box/certs/ljcnb666.asia.key"
  }
}
```

客户端参数：

```text
服务器：ljcnb666.asia
端口：2054/UDP
密码：<HY2_PASSWORD>
TLS SNI：ljcnb666.asia
```

Hysteria2 不是 VLESS，v2rayN 需要使用支持 sing-box/Hysteria2 的核心或客户端。它不是“强行突破带宽”的协议；UDP 被限速、丢包或云厂商限制时，速度可能反而低于 TCP。

### 9.3 VLESS-Reality 服务端配置

服务端入站标签：`vless-reality-2055`。Reality 使用自己的密钥对，不是借用或复制苹果、微软等第三方证书。

```json
{
  "type": "vless",
  "tag": "vless-reality-2055",
  "listen": "0.0.0.0",
  "listen_port": 2055,
  "tcp_fast_open": true,
  "users": [
    { "uuid": "<VLESS_UUID>" }
  ],
  "tls": {
    "enabled": true,
    "server_name": "www.apple.com",
    "reality": {
      "enabled": true,
      "handshake": {
        "server": "www.apple.com",
        "server_port": 443
      },
      "private_key": "<REALITY_PRIVATE_KEY>",
      "short_id": ["<REALITY_SHORT_ID>"]
    }
  }
}
```

客户端必须使用服务端对应的公钥 `publicKey`，并设置 `fingerprint=chrome`、`serverName=www.apple.com`、`shortId` 和 TCP 传输。Reality 可以降低自建证书和 Caddy 反代开销，但不代表绝对不可识别或绝对不会被封锁。

Reality 客户端敏感参数应从管理员的私密备份中填写：

```text
publicKey：<REALITY_PUBLIC_KEY>
shortId：<REALITY_SHORT_ID>
```

生成新的 UUID 和 Reality 密钥对：

```bash
uuidgen
sudo sing-box generate reality-keypair
```

### 9.4 三个节点的使用场景命名

```text
大流量下载｜Hysteria2-2054
日常 TCP 备用｜VLESS-Reality-2055
通用兼容备用｜VLESS-WS-2053
```

建议日常使用顺序：

1. 战网、Steam、代码仓库和大文件：优先 Hysteria2。
2. UDP 被限制、公司或校园网络只允许 TCP：切换 VLESS-Reality。
3. 客户端不支持 Reality 或出现兼容问题：使用 VLESS-WS。

### 9.5 多人共用建议

多人使用时，所有用户仍共享同一台 VPS 的出口带宽、CPU、内存和跨境线路；协议本身不能把总带宽复制成多份。建议每个用户使用独立凭据：

- Hysteria2：为每个人设置独立 password。
- VLESS：为每个人设置独立 UUID。
- 出现异常时只撤销对应用户，不影响其他设备。
- 不要公开发布节点链接、密码、UUID、Reality 私钥或 SSH 密码。

### 9.6 验证、备份与端口检查

```bash
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl restart sing-box
systemctl is-active sing-box caddy
sudo ss -ltnup | grep -E ':(2053|2054|2055|443|8443) '
sudo ufw status verbose
```

当前备份包括：

```text
/etc/sing-box/config.json.before-direct-2053
/etc/sing-box/config.json.before-hy2-reality
/etc/caddy/Caddyfile.before-port-test
```

证书复制到 `/etc/sing-box/certs/` 后，Caddy 自动续期不会自动更新 sing-box 使用的副本。证书续期后应重新复制证书、校验配置并重启 sing-box；否则 `2053` 直连和 `2054` Hysteria2 可能在证书过期后失效。Reality `2055` 不依赖这份证书，但依赖自己的 Reality 私钥和短 ID。

> [!warning] 公开仓库安全
> 本文用于公开同步时不包含 SSH 密码、VLESS UUID、Hysteria2 password、Reality private key 或完整可用链接。真实凭据只应保存在本机密码管理器或服务器受限配置文件中。
