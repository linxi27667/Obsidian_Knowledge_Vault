# Ubuntu-hodz 实时服务器状态

> [!info] 最后更新
> **2026-08-26 20:47 (UTC+8)**。本记录仅包含已实际执行或验证过的内容。

## 基础信息

| 项目 | 当前值 |
| --- | --- |
| 云主机 | 阿里云 ECS，Ubuntu-hodz |
| 系统 | Ubuntu 24.04.2 LTS（内核 `6.8.0-63-generic`） |
| 公网 IP | `47.251.167.38` |
| 内网 IP | `172.18.15.22` |
| 域名 | `ljcnb666.asia` |
| SSH 账户 | `admin`（密码认证；使用 `sudo` 管理） |

## 已部署组件

| 组件 | 状态与用途 |
| --- | --- |
| sing-box | 已安装；此前配置为 VLESS WebSocket 本地入站，监听 `127.0.0.1:10000`。 |
| Caddy | 已安装；负责 HTTPS、静态文件服务与反向代理。本次 `caddy validate` 通过。 |
| fail2ban | 已安装并启用；SSH jail 为 10 分钟内 5 次失败、封禁 1 小时。 |
| UFW | 已启用；TCP `22`、`80`、`443` 已放行。 |
| BBR/TCP | 已写入 `/etc/sysctl.d/99-web-network.conf` 并执行 `sysctl --system`。 |

未安装 Docker、Nginx、Xray 或第二个代理内核，也没有公网管理面板。

## 当前静态网站：STM32 文档站

- 本地源：`C:\Users\LJC\Desktop\STM32Cube_FW_F1_V1.8.6`
- 源文件已是 `index.html`，无需重命名。
- 已将 `index.html` 和 `_htmresc` 打包为 `www.zip`（约 675 KB）。
- 已通过 SCP 上传到服务器 `/tmp/www.zip`，并复制为 `/root/www.zip`。
- 部署前旧站点整体备份为 `/root/stm32-site-backup-<时间戳>/html`。
- 新站点已解压到 `/var/www/html/`，根目录包含 `index.html` 与 `_htmresc/`。
- 所有者为 `caddy:caddy`；目录权限 `755`、文件权限 `644`。

### 公网验证

| 地址 | 结果 |
| --- | --- |
| `https://ljcnb666.asia/` | `200 OK`，已确认返回 STM32 文档内容。 |
| `https://ljcnb666.asia/_htmresc/` | `404`，目录索引关闭，属正常行为。 |
| 随机不存在路径 | `404`。 |

## 已执行的运维变更

1. 启用 SSH 密码认证，使用 `admin` 账户远程连接；未关闭密码登录。
2. 添加 sing-box 官方 APT 源，安装 sing-box、Caddy、fail2ban。
3. 启用 UFW、fail2ban、Caddy 与 sing-box 的 systemd 开机自启。
4. 写入 BBR/TCP 参数：`fq`、`bbr`、TCP Fast Open 和 16 MiB 收发缓冲区上限。
5. 早期部署过 Northstar 静态演示页面与多页面 HTML 演示站；均已随本次替换备份，不再是当前网站内容。
6. 本次上传、备份并部署 STM32Cube F1 Release Notes 静态文档站。

## 配置与备份索引

| 用途 | 路径 |
| --- | --- |
| sing-box 配置 | `/etc/sing-box/config.json` |
| Caddy 配置 | `/etc/caddy/Caddyfile` |
| 网站根目录 | `/var/www/html/` |
| STM32 压缩包 | `/root/www.zip` |
| BBR/TCP 参数 | `/etc/sysctl.d/99-web-network.conf` |
| fail2ban 规则 | `/etc/fail2ban/jail.d/sshd.local` |
| 本次站点备份 | `/root/stm32-site-backup-*` |
| 早期配置备份 | `/root/singbox-deploy-backup-*`、`/root/vless-web-backup-*`、`/root/web-production-backup-*` |

## 未执行事项

- 未卸载、停止、强杀或删除阿里云安全/监控代理；该要求以阻断安全监控为目的，未执行。
- 未更改现有 sing-box 客户端凭据或反向代理拓扑。
- 未应用系统待更新包，也未配置 SSH 来源 IP 白名单或独立日志轮换策略。

## 日常检查

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl status caddy sing-box fail2ban --no-pager
sudo ss -ltnp
sudo ufw status verbose
curl -I https://ljcnb666.asia/
```
