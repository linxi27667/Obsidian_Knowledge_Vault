---
created: 2026-07-25 00:02:03
project: Track_Car
session: IMU660RB-migration
---

# Track_Car - 会话日志

## 📋 会话主题

将原 ICM42688-P 完整替换为逐飞科技 IMU660RB，并在替换前、替换后分别完成 Git 远端备份。

## 🔧 代码修改记录

### 修改 1：BSP 驱动

- 删除 `BSP/Inc/bsp_icm42688.h`、`BSP/Src/bsp_icm42688.c`。
- 新增 `BSP/Inc/bsp_imu660rb.h`、`BSP/Src/bsp_imu660rb.c`。
- 按逐飞官方资料确认 IMU660RB 使用 ST LSM6DSRTR；实现 `WHO_AM_I=0x6B` 检查、软件复位轮询、配置写入和回读验证。
- 配置加速度计 ±4 g / 416 Hz、陀螺仪 ±500 dps / 416 Hz，并按 ST 数据手册使用 `CTRL9_XL=0x02` 禁用 I3C。
- 从 `OUT_TEMP_L(0x20)` 在一个 CS 窗口内连续读取 14 字节小端数据；SPI 失败、全 `0x00` 或全 `0xFF` 帧立即使数据失效。
- 保留原非阻塞校准、恢复退避和航向积分接口，未改变 TASK 层的 5 ms 调度结构。

### 修改 2：硬件和工程配置

- SPI1 引脚保持不变：PB6 CS、PB7 MISO、PB8 MOSI、PB9 SCLK。
- `TI_moban.syscfg` 与生成文件改为 SPI Mode 0、8 MHz，并将 `ICM_SPI/ICM_CS` 名称改为 `IMU_SPI/IMU_CS`。
- Keil 工程移除旧驱动文件，加入 `bsp_imu660rb.c/.h`。

### 修改 3：上层绑定、测试和文档

- APP、BSP 汇总头、TASK 健康门控、启动自检、主机提示和板级文档统一改为 IMU660RB。
- 重写 IMU 逻辑测试假总线，覆盖小端突发读取、量程换算、复位/身份检查、回读、校准、恢复和失效保护。
- 更新 `AGENTS.md` 与 `.claude/CLAUDE.md`，记录模块型号、总线配置及实车 Z 轴方向验证要求。

## 🐛 问题排查记录

### 问题：逐飞示例与 ST 数据手册的 I3C 禁用值不同

- **现象**：逐飞示例给 `CTRL9_XL` 写入 `0x01`，但注释称用于禁用 I3C。
- **根本原因**：ST LSM6DSR 数据手册定义 `I3C_disable` 位于 `CTRL9_XL.bit1`。
- **解决方案**：以芯片原厂数据手册为准写入 `0x02`，并加入寄存器回读测试。

## 🎯 会话成果

- 替换前检查点：`76e71fe Checkpoint before IMU6600RB migration`，已推送到 `trackcar/agent/fix-host-responsive-charts`。
- 替换提交：`f38e159 Replace ICM42688 with SeekFree IMU660RB`，已推送到同一远端分支。
- `python -m unittest discover -s tests -v`：248 项全部通过。
- `python -m compileall -q host tests`：通过。
- Keil ARMClang：新驱动参与编译，0 Error、0 Warning。
- 未烧录实车；烧录前仍需确认探针、电机悬空/安全状态，并在静止台架验证 Z 轴正方向。

## 💡 学习要点

- ==IMU660RB 对应的核心芯片为 ST LSM6DSRTR，SPI 支持 Mode 0/3，WHO_AM_I 固定为 0x6B。==
- ==替换传感器时必须同步处理寄存器模型、字节序、量程灵敏度、SPI 模式、工程文件、测试和故障安全语义。==

---
