---
title: 2026-10-16 USB Type-C接口引脚与USB2.0设备连接
date: 2026-10-16
recorded_at: "2026-10-16T11:29:07+08:00"
timezone: Asia/Shanghai
source_activity_date: 2026-10-16
source_document: "用户提供的 Type-C 参考原理图截图；USB-IF USB Type-C Cable and Connector Specification"
status: "已解释24个触点功能；当前图按USB2.0设备/受电端使用，保护与外壳接地仍需核对"
tags: [日志, 嵌入式, USB, USB-C, Type-C, 原理图]
---

# 2026-10-16 USB Type-C 接口引脚与 USB 2.0 设备连接

## 本次目标与结论

这次根据用户给出的原理图，逐组说明 USB Type-C 插座的 24 个触点为什么这样安排，并核对图中的两个 5.1 kΩ电阻。当前图显示的是只用 USB 2.0 数据、作为 USB-C 受电设备（Sink/UFP）的简单接法：CC1、CC2 各自通过 5.1 kΩ接地；USB 2.0 的 D+/D−触点按方向合并到对应数据网；超高速差分线与 SBU 在当前用途下未接。

Type-C 是连接器和连接管理方式，不代表一定支持 USB 3.x、USB PD 或视频。只做 USB 2.0 时可不使用高速 TX/RX 对和 SBU；若要当电源输出端，或需要 USB PD/Alt Mode，则不能只靠两颗 5.1 kΩ电阻，必须另按角色加入 CC/PD 控制与 VBUS 电源管理。

## 先看原图

下图是用户提供的参考原理图截图。图中 R7、R8 分别把 CC1、CC2 下拉到 GND；VBUS 引脚并接为供电网；多组 GND 并接；D+/D−引脚标注 USB2.0 数据网；SBU 与高速数据引脚作未连接处理；EH 外壳脚连接到图中的 GND 网络。

![用户提供的 USB Type-C 参考原理图：双5.1kΩ Rd、USB2.0数据与外壳脚](<资料/TypeC/USB_TypeC_reference_schematic.png>)

本图适合作为 USB2.0 Sink/UFP 连接参考。VBUS 的保险/过压与反灌保护、ESD 保护器件、外壳与机壳地的连接策略仍要按整机输入电源和接口环境补齐。

## 24 个触点逐组说明

Type-C 插座 A、B 两排共 24 个触点。以下表格按插座触点列出；不同图纸符号的上下/左右绘制方向可能不同，应以引脚号为准。

| 触点 | 信号 | 为什么这样设计 | 当前 USB2.0 设备接法 |
|---|---|---|---|
| A1、B1、A12、B12 | GND | 多个地触点给电源和信号提供回流，也分布在插头两侧配合翻转插入 | 全部接地，靠近连接器做好回流与保护 |
| A4、A9、B4、B9 | VBUS | 多个触点并联供电，使插头翻转后两面都能取得 VBUS，并分担电流 | 全部并到 VBUS；作为受电端输入时接输入保护/电源路径 |
| A5 | CC1 | Configuration Channel，用于检测连接、方向、角色与默认电流能力；PD 通信也走活动 CC | 作为 Sink 时通过一个独立 Rd 接地，典型 5.1 kΩ |
| B5 | CC2 | 与 CC1 配合覆盖插头翻转的另一方向；活动方向的 CC 负责连接管理 | 另用一个独立 Rd 接地，典型 5.1 kΩ；不要把 CC1/CC2 短接 |
| A6、B6 | D+ | 两个物理位置对应翻转方向；USB2.0 数据对不依赖高速通道切换 | USB2.0 receptacle 的 A6 与 B6 汇到同一 D+ 网，并满足 USB 走线规则 |
| A7、B7 | D− | 与 D+ 成差分数据对，并覆盖两种插头方向 | A7 与 B7 汇到同一 D−网；不能与 D+ 互换 |
| A2 | SSTX1+ | USB 3.x SuperSpeed 第 1 组发送差分对正端 | 仅 USB2.0 时不接 |
| A3 | SSTX1− | USB 3.x SuperSpeed 第 1 组发送差分对负端 | 仅 USB2.0 时不接 |
| B2 | SSTX2+ | USB 3.x SuperSpeed 第 2 组发送差分对正端，支持翻转方向 | 仅 USB2.0 时不接 |
| B3 | SSTX2− | USB 3.x SuperSpeed 第 2 组发送差分对负端，支持翻转方向 | 仅 USB2.0 时不接 |
| A10 | SSRX2− | USB 3.x SuperSpeed 接收差分对负端 | 仅 USB2.0 时不接 |
| A11 | SSRX2+ | USB 3.x SuperSpeed 接收差分对正端 | 仅 USB2.0 时不接 |
| B10 | SSRX1− | USB 3.x SuperSpeed 接收差分对负端，支持翻转方向 | 仅 USB2.0 时不接 |
| B11 | SSRX1+ | USB 3.x SuperSpeed 接收差分对正端，支持翻转方向 | 仅 USB2.0 时不接 |
| A8 | SBU1 | Sideband Use，供部分 Alternate Mode 使用的侧带信号 | 当前不使用 Alt Mode 时不接 |
| B8 | SBU2 | 与 SBU1 分别对应不同插入方向 | 当前不使用 Alt Mode 时不接 |
| 金属外壳 / Shield | 屏蔽 | 降低外界干扰，并把插拔放电引向合适的泄放路径 | 本图 EH 脚接 GND；最终是否直连系统地、机壳地或经 RC/电容处理需结合 EMC/ESD 策略确认 |

USB2.0 数据触点在 Type-C 插座上重复，是为可翻转插入服务；超高速差分对则需要在主机端通过方向识别和高速通道切换选择正确通道。VBUS 与 GND 的多触点用于并联供电/回流，不应把不同信号脚误当成重复电源脚。

## R7、R8 的 5.1 kΩ为什么接地

当前设备是受电端，因此 CC1、CC2 各自放一个 Rd 下拉。对端电源端在 CC 上看到 Rd 后，识别到设备已经连接，并根据 Rp/Rd 状态决定默认电流能力与 VBUS 供电状态；插头翻转会让其中一个 CC 成为有效通信通道。

- R7、R8 均为 5.1 kΩ（USB-IF 规范典型 ±20%），分别从 CC1、CC2 接到 GND；两条 CC 网络必须分开。
- 这两个电阻表示 Sink/UFP 角色，不是 USB 数据线上拉，也不是把 VBUS 接到 5.1 kΩ。
- 5.1 kΩ并不等同于申请任意大电流，也不完成 USB PD 电压协商。USB PD 需要 CC 控制器和相应的电源开关/保护方案。
- 如果产品需要从 Type-C 向外供 5 V，应设计成 Source/DFP，按规范使用 Rp/控制器并控制 VBUS；不能照抄当前两个下拉电阻。

## 当前图纸仍需补查的项目

- [ ] 确认产品只需要 USB2.0，还是还要 USB3.x、Alt Mode 或 USB PD；据此决定 SBU、超高速差分线和 CC 控制器。
- [ ] 按受电端实际电源路径核对 VBUS 输入保护、限流、过压与防反灌，并确认 Type-C 端电容和上电时序。
- [ ] 在连接器附近选择适合 USB2.0 的低电容 ESD 保护器件，并保持差分线短、连续、阻抗受控。
- [ ] 核对 USB2.0 D+：A6/B6、D−：A7/B7 的连接，并与 USB-UART 芯片（若使用）及主控接口关系一致。
- [ ] 评估 EH 屏蔽脚接系统 GND、机壳或耦合网络的 EMC/ESD 方案；不能仅凭原理图符号决定最终铜箔连接。
- [ ] 检查 R7/R8 作为 Sink 的 5.1 kΩ Rd 是否分别接 CC1/CC2 到 GND，且没有接到 VBUS。

## 来源与关联记录

- [USB-IF USB Type-C Cable and Connector Specification](https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf)：Type-C 插座触点分配、CC/Rd 与电缆连接规范。
- [TI USB Type-C CC 控制器选择指南](https://www.ti.com/lit/an/sdaa284/sdaa284.pdf)：用于理解 Type-C 可翻转插入、CC 和插座引脚组的关系。
- 用户提供的 [[资料/TypeC/USB_TypeC_reference_schematic.png|参考原理图截图]]。
- [[02-嵌入式日志/2026-10-16/2026-10-16 EG800AK串口双NPN电平转换电路与仿真|同日 EG800AK 双 NPN UART 转换电路]]：此 Type-C 连接器也出现在用户提供的 4G 板原理图第 3 页。
- [[02-嵌入式日志/2026-10-16/2026-10-16 EG800AK的MIC29302WU VBAT供电外围电路|同日 MIC29302WU VBAT 供电设计]]。
