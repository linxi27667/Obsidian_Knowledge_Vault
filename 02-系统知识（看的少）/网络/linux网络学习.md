---
created: 2025-05-17 09:00
updated: 2025-05-17 09:00
tags: [Linux, 网络, 排障, 有线网]
---

# Linux 有线网络无法上网实战排障全总结

> [!NOTE] 适用场景
> 设备环境：Linux 桌面系统，有线网卡 `enp1s0`
> 初始故障：dhclient 卡死、手动配 IP 后无法上网、域名 ping 报 `Name or service not known`

---

## 一、问题根因

**IP 配置正常、物理连接正常，缺失正确网关 + DNS 配置，并非硬件/驱动故障**

---

## 二、必备命令清单

### 1. 网卡状态与信息
```bash
ip addr show enp1s0
/sbin/ip addr show enp1s0        # ip 命令不可用时
sudo ethtool enp1s0              # 查看物理连接状态
```
> [!TIP] 关键判断
> `Link detected: yes` = 网线、网口、交换机物理连接完全正常

### 2. 网卡启用/禁用
```bash
sudo ip link set enp1s0 up       # 启用
sudo ip link set enp1s0 down     # 禁用
```

### 3. 静态 IP 配置
```bash
sudo ip addr add 10.3.36.213/24 dev enp1s0
```

### 4. 网关配置（外网访问核心）
```bash
sudo ip route add default via 10.3.36.254 dev enp1s0  # 添加
sudo ip route del default                               # 删除旧网关
ip route show                                           # 查看当前网关
```

### 5. DNS 配置（域名解析核心）
```bash
echo "nameserver 223.5.5.5" | sudo tee /etc/resolv.conf
echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf
```

### 6. 网络连通性分层测试
```bash
ping 10.3.36.254       # 1. 测试内网（ping网关）
ping 223.5.5.5         # 2. 测试外网（ping公网IP，bypass DNS）
ping baidu.com         # 3. 测试DNS解析（ping域名）
```

---

## 三、排障流程（按顺序执行）

### 第一步：排查物理连接
```bash
sudo ethtool enp1s0
```
确认 `Link detected: yes`，排除网线、网口、交换机硬件故障。

### 第二步：排除 DHCP 失效
`dhclient enp1s0` 卡死 = 当前网络无 DHCP，必须改用**静态 IP**。

### 第三步：配置静态 IP
```bash
sudo ip addr add 10.3.36.213/24 dev enp1s0
```

### 第四步：配置默认网关（最关键）
无网关 = **只能访问内网，无法访问外网**
```bash
sudo ip route add default via 10.3.36.254 dev enp1s0
```

### 第五步：配置 DNS
无 DNS = **无法解析域名，只能访问 IP**
```bash
echo "nameserver 223.5.5.5" | sudo tee /etc/resolv.conf
echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf
```

### 第六步：分层验证
1. `ping 10.3.36.254` 通 → 内网正常
2. `ping 223.5.5.5` 通 → 外网正常
3. `ping baidu.com` 通 → 全部配置生效，可正常上网

---

## 四、高频报错对照表

| 报错内容 | 报错原因 | 解决办法 |
|----------|----------|----------|
| dhclient 命令一直卡死 | 网络无 DHCP 服务 | 改用静态 IP |
| `Error: Address already assigned` | IP 已重复配置 | 无需重复执行，跳过即可 |
| `RTNETLINK answers: File exists` | 网关已重复配置 | 无需重复添加，跳过即可 |
| ping 公网 IP 100% 丢包 | 未配置/配置错误默认网关 | 先删旧网关，再重新配置正确网关 |
| `Name or service not known` | DNS 未配置/解析失败 | 重新配置公共 DNS |
| `ip: command not found` | 终端输入乱码/命令路径异常 | `Ctrl+C` 清空乱码，用 `/sbin/ip` |
| `tee: command not found` 或语法错误 | 命令缺少空格 | 正确格式：`tee -a /etc/resolv.conf`（-a 前后都有空格） |

---

## 五、核心结论

1. 本次故障**和网卡驱动、硬件、系统损坏无关**，纯网络参数配置缺失
2. Linux 有线网能上网的**三大必备条件**：
   - 同网段静态 IP 配置正确
   - 默认网关配置正确（外网出口）
   - DNS 服务器配置正确（域名解析）
3. 排障黄金逻辑：**先查物理连接 → ping 网关（内网）→ ping 公网 IP（外网）→ ping 域名（DNS）**

---

## 六、一键速查命令

```bash
# 1. 查看网卡IP
ip addr show enp1s0

# 2. 配置静态IP
sudo ip addr add 10.3.36.213/24 dev enp1s0

# 3. 配置网关（删旧+加新）
sudo ip route del default && sudo ip route add default via 10.3.36.254 dev enp1s0

# 4. 配置DNS
echo "nameserver 223.5.5.5" | sudo tee /etc/resolv.conf && echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf

# 5. 分层测试
ping 10.3.36.254 && ping 223.5.5.5 && ping baidu.com
```

---

## 相关链接

- 来源：豆包 AI 对话记录，2025-05-17