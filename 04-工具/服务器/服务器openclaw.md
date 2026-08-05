# 阿里云服务器 OpenClaw 部署与连接指南

> **服务器公网 IP**: `8.134.167.240`
> **登录用户**: `root`
> **OpenClaw 版本**: `2026.5.5`
> **网关端口**: `18789`
> **访问令牌 (Token)**: `10108888yy`

---

## 1. 服务器环境准备

- **系统**: Ubuntu 24.04 (Noble)
- **Node.js**: v24.15.0 (通过宝塔面板安装)
- **路径**: `/www/server/nodejs/v24.15.0/bin`

### 关键配置修复
由于宝塔环境自定义了 npm 全局路径，导致 `openclaw` 命令无法识别，需将 Node.js bin 目录加入 PATH：
```bash
export PATH="/www/server/nodejs/v24.15.0/bin:$PATH"
echo 'export PATH="/www/server/nodejs/v24.15.0/bin:$PATH"' >> ~/.bashrc
```

---

## 2. OpenClaw 安装与配置

### 安装命令
```bash
# 使用国内镜像加速
npm config set registry https://registry.npmmirror.com
npm install -g openclaw@latest
```

### 配置修复记录
1. **`thinkingFormat` 校验失败**
   - 报错: `Invalid input (allowed: "openai", "openrouter", "deepseek", "zai")`
   - 修复: 将配置文件中所有 `"thinkingFormat": "qwen"` 替换为 `"openai"`。
   ```bash
   sed -i 's/"thinkingFormat": "qwen"/"thinkingFormat": "openai"/g' ~/.openclaw/openclaw.json
   ```

2. **绑定地址设置**
   - 修改为允许局域网/外部访问：
   ```bash
   openclaw config set gateway.bind lan
   openclaw config set gateway.auth.token "10108888yy"
   ```

3. **CORS 跨域允许**
   - 允许公网 IP 访问控制面板：
   ```bash
   openclaw config set gateway.controlUi.allowedOrigins '["http://8.134.167.240:18789"]'
   ```

---

## 3. 服务管理常用命令

```bash
# 启动/停止/重启
openclaw gateway start
openclaw gateway stop
openclaw gateway restart

# 查看状态
openclaw gateway status

# 查看日志
openclaw logs --tail 50
openclaw logs --follow

# 发送测试消息
openclaw agent --message "你好" --agent main
```

---

## 4. 连接地址 (URL)

| 访问方式             | 地址 (URL)                     | 说明                   |
| :--------------- | :--------------------------- | :------------------- |
| **本地访问 (推荐)**    | http://localhost:18789       | 需先运行 SSH 隧道，浏览器兼容性最好 |
| **公网直接访问**       | `http://8.134.167.240:18789` | 需配置安全组放行 18789 端口    |
| **WebSocket 地址** | `ws://localhost:18789`       | 客户端连接网关用的底层地址        |

---

## 5. 本地连接方式 (SSH 隧道)

由于浏览器安全限制，Web 面板必须通过 `localhost` 或 `HTTPS` 访问。推荐使用 SSH 隧道。

### 步骤
1. **双击运行桌面脚本**: `C:\Users\30817\Desktop\连接 OpenClaw.bat`
2. **输入服务器密码** 建立连接。
3. **保持窗口开启**，在浏览器访问：
    **http://localhost:18789**
4. 输入 Token: `10108888yy` 即可连接。

### 手动命令 (备用)
```powershell
ssh -L 18789:127.0.0.1:18789 root@8.134.167.240
```

---

## 6. 常见问题排查

- **`openclaw: command not found`**: 检查 PATH 是否包含 Node.js bin 目录。
- **Gateway 启动失败**: 检查 `openclaw logs`，通常是配置文件格式错误或端口被占用。
- **连接被拒绝**: 检查阿里云安全组是否放行 TCP `18789` 端口。
- **浏览器提示 "origin not allowed"**: 检查 `gateway.controlUi.allowedOrigins` 配置。

---
*最后更新: 2026-05-06*
