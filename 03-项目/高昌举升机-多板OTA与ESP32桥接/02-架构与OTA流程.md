---
created: 2026-07-17 14:00
updated: 2026-07-17 14:00
tags: [OTA, Bootloader, 架构, ESP32]
project_root: E:/MCU/gaochang/GcMultiLinkLift
---

# 架构与 OTA 流程

## 一、业务固件能力（主控共性）

从 README 归纳，主控侧持续覆盖：

- 举升动作 / 比例阀 PWM  
- 编码器、高度、电池采集  
- 屏幕、按键、蜂鸣器  
- 多设备通信与在线状态  
- 参数存储、外部 Flash  
- WiFi/无线处理、OTA 接收  

任务级文件名线索：`move_lift_task.c`、`user_key_task.c`、`ota_task.c`、`disk_task.c` 等。

## 二、为什么有多套工程目录

工业现场常见：**板卡改版、阀组流量差异、是否带 ESP32、是否启用 OTA** 导致多固件并存。

| 目录关键词 | 含义 |
|---|---|
| reconsitution | 重构阶段 |
| newBoard | 新硬件 |
| 5.5MC / 8.0MC | 不同机械/控制配置版本 |
| TPFI | 特殊方案分支 |
| clear_w25qxx | Flash 清理工具型 |
| ESP32 | 带无线桥 |
| OTA | 可升级 APP 或 Boot |

简历表述：

> 维护多板卡/多配置固件矩阵，通过目录与任务模块化隔离差异，降低改一版坏一版的风险。

## 三、OTA 两段式（核心）

### 3.1 APP 阶段（收包）

```text
通信收到固件流
→ 写外部 Flash 分区
→ 校验长度/CRC（或签名）
→ 写“待升级”标志与元数据
→ 有序重启
```

### 3.2 Boot 阶段（刷写）

```text
上电进入 Bootloader
→ 读标志：无升级则直接跳 APP
→ 有升级：校验包 → 擦写内部 Flash
→ 成功：清标志跳 APP
→ 失败：保留旧 APP / 回滚策略
```

### 3.3 安全关注点（答辩用）

| 点 | 为什么重要 |
|---|---|
| 校验失败不刷 | 防变砖 |
| 双区/旧镜像回滚 | 升级中掉电 |
| 标志原子性 | 半写标志导致循环重启 |
| 加密（ota_aes，若启用） | 防篡改包 |
| 升级时禁运动输出 | 安全 |

## 四、ESP32 桥接支线

`ESP32_Proj` / `*_ESP32` 工程：

- 角色：Wi-Fi 联网、透传或协议转换、配合 OTA 传包  
- **不**承担举升安全互锁  
- 与 `Gc_Iot_Lift` 的 TAS 4G DTU 路线不同：MultiLink 更偏局域网/Wi-Fi 桥演进  

对比一句话：

> IoT_Lift 用蜂窝 DTU 做远程管理；MultiLink 部分版本用 ESP32 做现场无线与升级通道。

## 五、建议精读顺序

1. 任选一个 `newBoard` 主工程：`main` → 任务创建 → move/key  
2. `newBoard_Boot`：`boot_ota.c` 状态  
3. OTA APP：`ota_task.c` 收包状态  
4. ESP32 工程：与 STM32 的 UART/SPI 接口文档或代码  
