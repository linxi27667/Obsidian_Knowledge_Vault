---
created: 2026-07-15 00:00
updated: 2026-07-17 13:00
tags: [Web, Node.js, Express, SQLite, 面试]
project_root: E:/MCU/gaochang/Gc_Iot_Lift/Gaochang_Iot_Web
---

# Web 管理平台概览（知道用了什么、解决什么、怎样连到设备）

## 核心概念

- ==Web 端是管理与数据平台，不参与毫秒级安全闭环==。
- 面试重点是技术选型、数据流、权限和命令确认，不需要逐行背前端代码。

## 一、技术栈

| 技术 | 作用 |
|---|---|
| Node.js | 后端运行时 |
| Express | REST API 和静态页面服务 |
| mqtt.js | MQTT Broker 连接、订阅和发布 |
| better-sqlite3 | 本地关系型数据存储 |
| ws | WebSocket 实时消息推送 |
| JWT | 无状态身份认证 |
| bcryptjs | 密码哈希 |
| uuid / dotenv / cors | 工具库 |
| 原生 HTML/CSS/JS | 管理界面 |
| Chart.js | 运行与统计图表 |

来源：`Gaochang_Iot_Web/package.json`

## 二、入口和模块

| 文件 | 职责 |
|---|---|
| `server.js` | Express、路由、WebSocket、MQTT 启动 |
| `src/mqtt-bridge.js` | MQTT v1/兼容协议、数据入库、命令状态机 |
| `src/database.js` | SQLite 建表、迁移与访问 |
| `src/routes/auth.js` | 登录注册与 JWT |
| `src/routes/devices.js` | 设备台账和状态 |
| `src/routes/commands.js` | 锁机、解锁、查询、清报警、配置等 |
| `src/routes/alarms.js` | 告警记录 |
| `src/routes/maintenance.js` | 保养记录 |
| `src/routes/device_ops.js` | 设备操作日志 |
| `src/routes/binding.js` / `admin.js` | 绑定与管理 |
| `public/` | 浏览器端页面 |

## 三、MQTT 配置

| 项 | 值 |
|---|---|
| 默认 Broker | `mqtt://8.134.167.240:1883` |
| 前缀 | `gaochang/lift` |
| v1 | `gaochang/lift/v1` |
| v1 订阅 | `gaochang/lift/v1/devices/+/up` |
| v1 下行 | `gaochang/lift/v1/devices/{chip_uid}/down` |

兼容旧主题：`gaochang/lift/+/telemetry|status|response|op_log|event`。

v1 type 分流：`telemetry / event / operation_log / command_response / offline_batch`  
未知 UID / product_type 不匹配 → isolate。

## 四、数据流

```text
设备上行 MQTT
→ mqtt-bridge 校验 UID 和消息类型
→ SQLite 更新设备/告警/日志/保养/命令状态
→ WebSocket 推送浏览器

浏览器 REST 请求
→ JWT 和角色权限校验
→ 创建 command_queue 记录与 msg_id
→ MQTT 发布下行
→ 等待 command_response
→ 更新命令终态和设备状态
```

## 五、命令路由

| HTTP | cmd |
|---|---|
| POST `/lock/:id` | lock |
| POST `/unlock/:id` | unlock |
| POST `/query/:id` | get_status |
| POST `/maintenance_done/:id` | maintenance_done |
| POST `/reset_usage/:id` | reset_usage（admin） |
| POST `/lock-all` `/unlock-all` | 批量 |
| POST `/buzzer_on\|off/:id` | buzzer_* |
| POST `/clear_alarm/:id` | clear_alarm |
| POST `/fault_clear/:id` | fault_clear（admin） |
| POST `/set_config\|get_config/:id` | 配置 |
| GET `/status/:msgId` | 查队列 |

超时 15s，最多 2 次尝试；**仅 command_response 成功后改 locked 状态**。

## 六、命令状态机

```text
pending → sent → succeeded / rejected / timeout / failed
```

平台不会在“发布成功”时立即假设设备已经锁定。msg_id 去重：5 分钟窗口、最多 1000 条。

## 七、核心表

```text
users, devices, device_status, unbound_device_status,
alarms, maintenance_records, operation_logs, device_operation_logs,
command_queue, device_registry, binding_logs, product_configs,
device_bindings, binding_requests
```

## 八、安全与权限

- JWT 验证登录身份
- bcrypt 保存密码哈希
- WebSocket 连接同样检查账号和凭据
- 命令路由按用户角色鉴权
- 设备 UID 必须在台账中登记
- 前端传来的 `account` 不能替代后端认证身份

## 九、面试回答模板

### 30 秒版本

> 平台端使用 Node.js 和 Express 提供 REST API，mqtt.js 连接 Broker，better-sqlite3 保存设备、告警、保养和命令记录，WebSocket 向浏览器实时推送，JWT 和 bcrypt 负责认证。平台通过 UID 隔离的 MQTT 主题下发命令，并等待设备 `command_response` 后才确认执行成功。

### 为什么选 SQLite

> 当前部署规模偏单机和私有化，SQLite 部署简单。若设备规模或并发提升，可迁移到 PostgreSQL/MySQL，并保留现有业务模型。

### Web 是否控制安全

> Web 只做远程管理与审计，真正的急停、限位和输出关闭都由 STM32 本地执行。

## 十、只需要阅读的文件

- [x] `package.json`
- [x] `server.js`
- [x] `src/mqtt-bridge.js` 连接、v1 收包和 `publishV1Down`
- [x] `src/routes/commands.js` 锁机接口
- [x] `src/database.js` 核心表结构
