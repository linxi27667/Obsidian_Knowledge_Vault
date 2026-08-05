---
created: 2026-07-25 17:12:37
project: writer_robot
session: network-disconnect-continuation
---

# writer_robot - 断网连续执行

## 会话主题

将断网语义改为“通信只下达命令，已经被 MSPM0 接受的当前 G-code 行必须继续完成”。

## 代码修改记录

### MSPM0 `TASK/writer_cloud.c`

- 重连只重建 ESP-01S/MQTT 传输状态，不再因断网调用急停、清作业或设置
  `needs_rehome`。
- 保留当前 G-code 的完成结果、STOP ACK 和回零完成状态，在线后再发布。
- 显式 STOP、限位保护、运动错误和本地急停保持原有安全行为。

### Web `backend/app/mqtt/scheduler.py`

- `availability online:false` 仅标记设备离线，保留活跃 runtime、回零和 STOP 状态。
- 设备离线时停止 ACK 超时、重发和回零完成超时的计时；重连后继续原 payload。

### 协议与验收

- 新增 decision：`docs/decisions/20260725-network-disconnect-continuation.md`。
- 更新 V1 协议、验收项、MSPM0 约束和项目背景，明确单行缓存边界。
- 增加服务器回归：活跃行离线后不取消、不重试；重连后同 seq 重发且 completed ACK
  只推进一次。

## 验证结果

- Web 后端：`27 passed`。
- MSPM0 协议：`PASS: 88 protocol checks`。
- MSPM0 Keil Rebuild：`0 Error(s), 0 Warning(s)`；`Code=54900 RO=9912 RW=132 ZI=32220`。
- 小智主机测试：11 项通过。
- 小智 ESP-IDF 构建通过；应用分区剩余 36%。
- 前端 Vitest 和生产构建通过。
- Docker 健康检查：`{"ok":true,"mqtt_connected":true,"fonts":5}`。

## 真机状态

- 小智和 MSPM0 尚未烧录本轮产物：当前没有 ESP32-S3 下载串口，只有 J-Link CDC
  `COM40`；不能猜测历史/蓝牙串口。
- 小智本地 MQTT 配置文件不存在，不能把占位 broker 地址烧入后宣称能连真实服务。
- MSPM0 实际写字仍需先确认无笔/抬笔、急停可用、机构清空和真实调试器身份。

## 经验

- 当前协议只缓存一条活跃 G-code，因此“当前已下达行不停”可实现；“整页剩余未下达行
  离线持续完成”需要完整作业缓存和新的内存/断电恢复设计，不能混为一谈。
