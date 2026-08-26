# Ubuntu-hodz 服务器连接教程

## 服务器信息

| 项目 | 内容 |
| --- | --- |
| 云厂商 | 阿里云 ECS |
| 实例名称 | `Ubuntu-hodz` |
| 系统 | Ubuntu 24.04.2 LTS |
| 公网 IP | `47.251.167.38` |
| 内网 IP | `172.18.15.22` |
| SSH 端口 | `22` |
| 登录账户 | `admin` |
| 登录密码 | `<已脱敏，请通过密码管理器保管或使用 SSH 密钥认证>` |

> [!tip] 安全提示
> 已移除明文密码。建议全面使用 SSH 密钥登录，并关闭密码认证。

## 从 Windows 终端连接

打开 PowerShell 或 Windows Terminal，运行：

```powershell
ssh admin@47.251.167.38
```

首次连接时若出现主机指纹确认提示，输入 `yes` 并按 Enter。随后输入登录密码。终端中输入密码时不会显示任何字符，这是正常现象。

成功后会看到类似以下提示符：

```text
admin@iZrj9j64kkjbjfdoodvcvmZ:~$
```

## 用 VS Code Remote SSH 连接

1. 在 VS Code 安装 **Remote - SSH** 扩展。
2. 按 `Ctrl + Shift + P`，选择 **Remote-SSH: Connect to Host...**。
3. 选择 **Add New SSH Host...**，填写：

   ```text
   ssh admin@47.251.167.38
   ```

4. 选择 SSH 配置文件后，再次运行 **Remote-SSH: Connect to Host...**，选择刚添加的主机。
5. 输入密码即可连接。

也可以直接在 `%USERPROFILE%\\.ssh\\config` 添加：

```sshconfig
Host ubuntu-hodz
    HostName 47.251.167.38
    User admin
    Port 22
```

之后使用：

```powershell
ssh ubuntu-hodz
```

## 当前 SSH 设置

服务器已经启用密码登录：

```text
PasswordAuthentication yes
```

配置文件位于：

```text
/etc/ssh/sshd_config
```

修改 SSH 配置后，请先检查配置，再重启服务：

```bash
sudo sshd -t
sudo systemctl restart ssh
sudo systemctl status ssh --no-pager
```

## 常用操作

```bash
# 查看系统状态
uptime

# 查看磁盘空间
df -h

# 更新软件索引
sudo apt update

# 退出服务器
exit
```

## 安全建议

密码登录仅适合临时使用。稳定使用前，建议创建 SSH 密钥、将公钥写入 `~/.ssh/authorized_keys`，确认密钥可以登录后，再关闭密码登录：

```text
PasswordAuthentication no
PermitRootLogin no
```

修改后执行：

```bash
sudo sshd -t
sudo systemctl restart ssh
```
