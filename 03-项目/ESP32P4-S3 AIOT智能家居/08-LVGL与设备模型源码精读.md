---
created: 2026-07-15 17:45
updated: 2026-07-17 12:00
tags: [LVGL, UI, 设备模型, 事件驱动]
project_root: E:/MCU/esp32/p4/xiaozhi-for-p4
---

# LVGL 与设备模型源码精读（界面不是数据源）

## 核心概念

- ==设备模型保存真实状态，页面只是模型的视图==。
- ==MQTT 回调不直接操作 LVGL==。
- ==UI 事件先入队，再由 50 ms LVGL timer 派发==。
- 模型在 **PSRAM**（`EXT_RAM_BSS_ATTR`），写路径有 mutex。

## 一、UI 目录

```text
main/smart_home/ui/
├─ ui_manager.c / ui_manager.h
├─ ui_theme.c / ui_anim.c
├─ core/       ui_events、主题、样式
├─ model/      mqtt_device_model.c/.h
├─ pages/      data/ctrl/light/scene/env/net/set
├─ services/   资源、欢迎弹窗等
├─ widgets/
└─ fonts/
```

## 二、UI Manager

`UI_Manager_Init(parent)` 创建侧栏、内容区、事件订阅和 50 ms timer。

| ID | 宏 | 页面 |
|---:|---|---|
| 0 | `UI_PAGE_DATA` | 总览 |
| 1 | `UI_PAGE_CTRL` | 控制 |
| 2 | `UI_PAGE_LIGHT` | 灯光 |
| 3 | `UI_PAGE_SCENE` | 场景 |
| 4 | `UI_PAGE_ENV` | 环境 |
| 5 | `UI_PAGE_NET` | 网络 |
| 6 | `UI_PAGE_SET` | 设置 |

API：

| API | 作用 |
|---|---|
| `UI_Manager_Init()` | 初始化 |
| `UI_Manager_Switch_Page()` | 清理内容区并 `page_*_create()` |
| `UI_Manager_Rebuild_Current()` | 重建当前页 |
| `UI_Manager_Poll()` | 派发待处理事件 |
| `UI_Manager_Get_Current_Page()` | 当前页 ID |
| `UI_Manager_Force_Layout()` | 强制布局 |

## 三、事件派发

来源：`ui_events.h` / `ui_manager.c`

```c
static void poll_timer_cb(lv_timer_t *timer) {
    UI_Manager_Poll();   // → ui_events_dispatch_pending()
}
```

### UI 事件类型

| 事件 | 含义 |
|---|---|
| `UI_EVENT_MODEL_UPDATED` | 设备模型变化 |
| `UI_EVENT_MQTT_CONNECTED` / `DISCONNECTED` | MQTT 状态 |
| `UI_EVENT_WIFI_CHANGED` | Wi-Fi 变化 |
| `UI_EVENT_LANG_CHANGED` | 语言 |
| `UI_EVENT_PAGE_SWITCHED` | 切页 |
| `UI_EVENT_FIRE_ALARM` | 火警 |
| `UI_EVENT_SCENE_CHANGED` | 场景变化 |
| `UI_EVENT_LOGIN_REQUIRED` / `SUCCESS` / `FAILED` | 登录 |
| `UI_EVENT_FACE_DETECTED` / `RECOGNIZED` / `NOT_RECOGNIZED` | 人脸 |
| `UI_EVENT_FACE_PREVIEW_FRAME` | 预览帧 |

机制：网络侧 `ui_event_publish` 入队 → LVGL 上下文 `dispatch_pending`。

## 四、设备模型字段

来源：`mqtt_device_model.h`

```text
mqtt_device_model_t:
  devices[RC_DEVICE_MAX=32], device_count
  gateway_connected, refresh_seq, mqtt_state
  wifi_state / wifi_ssid / wifi_aps[16]
  temperature/humidity/pm25/rain/flame/smoke + valid 标志
  rain/smoke/flame_floor_value[3]
  fire/rain/help_floor_status[3] + valid
  weather_* （默认广州 23.1291, 113.2644）
  mqtt_broker, mqtt_rx_count, mqtt_last_seen_sec
  controller_online[3]
  current_scene, scene_seq, scene_name

rc_device_t:
  id, floor, type, name
  connected, controllable, power_on, value, value_text
  floor_id, cmd_type, gpio_index
  red/green/blue/brightness/effect
  servo_open_angle / servo_close_angle
```

### 模型更新来源

| 来源 | 函数/路径 |
|---|---|
| announce | 注册楼层 + MAC |
| heartbeat V2 | `device_model_apply_heartbeat()` |
| heartbeat V3 | `device_model_apply_heartbeat_v3()` |
| response | 命令确认刷新 |
| sensor | 传感器事件 |
| 网络事件 | online/offline |
| 场景 | `device_model_set_scene` |

## 五、设备清单（模型中的逻辑设备）

| device_id | 楼层 | 类型 | cmd | gpio_index | 开/关角 |
|---|---|---|---|---|---|
| floor1_gate | 1 | DOOR | SERVO | 6 | 180/0 |
| floor1_hall_light | 1 | LIGHT | LIGHT | 0 | — |
| floor1_main_power | 1 | MAIN_POWER | MAIN_POWER | 0 | — |
| floor2_master_light | 2 | RGB | RGB | 0 | — |
| floor2_living_light | 2 | LIGHT | LIGHT | 1 | — |
| floor2_toilet_light | 2 | LIGHT | LIGHT | 2 | — |
| floor2_fan | 2 | FAN | RELAY | 0 | — |
| floor2_hanger | 2 | WINDOW | SERVO | 8 | 180/0 |
| floor2_main_power | 2 | MAIN_POWER | MAIN_POWER | 0 | — |
| floor3_balcony_light | 3 | LIGHT | LIGHT | 0 | — |
| floor3_right_skylight | 3 | WINDOW | SERVO | 6 | 90/180 |
| floor3_left_skylight | 3 | WINDOW | SERVO | 7 | 90/0 |
| floor3_hanger | 3 | WINDOW | SERVO | 8 | 180/0 |
| floor3_main_power | 3 | MAIN_POWER | MAIN_POWER | 0 | — |
| floor_all_main_power | ALL | MAIN_POWER | — | — | 派生 |

## 六、页面到命令

```text
LV_EVENT_CLICKED
→ page_* 事件回调
→ mqtt_send_command / scene / rgb
→ UI 可显示“等待确认”
→ response / heartbeat 更新模型
→ UI_EVENT_MODEL_UPDATED
→ 当前页面刷新最终状态
```

不应仅凭点击立即认定硬件已经成功执行。

## 七、智能家居事件中心

来源：`smart_home_event_center.h`

| 事件 | 含义 |
|---|---|
| `SH_EVENT_DEVICE_ONLINE` / `OFFLINE` | 楼层上下线 |
| `SH_EVENT_COMMAND_ACK` / `TIMEOUT` | 命令确认 |
| `SH_EVENT_SENSOR_WARNING` | 传感器警告 |
| `SH_EVENT_FIRE_ALARM` / `RAIN_ALARM` / `HELP_ALARM` | 安全报警 |
| `SH_EVENT_RULE_TRIGGERED` | 规则触发 |
| `SH_EVENT_NETWORK_RECOVERED` | 网络恢复 |

报警 UI：`smart_home_alarm_bridge.cc` 实现 weak 符号 `smart_home_alarm_on_fire/rain/help`。

## 八、小智 UI 与智能家居 UI 融合

`main/display/lcd_display.cc`（约 1750 行）保留小智原有状态、聊天、表情、通知等接口，同时承载智能家居容器。上层 Application 不需要知道当前显示哪个页面。

登录 UI 覆盖在 Locked 状态；登录成功后进入 Idle 并触发 HOME 场景。

## 九、页面生命周期与性能

切页会清理并重建当前内容区。

分析卡顿时检查：

- 是否整页重建过多
- 图片是否来自 PSRAM / TF / Assets
- 是否在 LVGL 回调做网络或推理
- 人脸任务是否抢占 CPU
- 是否持有 DisplayLock 太久
- `main_tasks_` 是否积压

## 十、人脸与 UI 联动

```text
face_recog task (core1, 12KB, prio4)
→ DetectAndRecognize (ESP-DL)
→ Schedule → UI_EVENT_FACE_RECOGNIZED
→ LOGIN_SUCCESS → Idle + HOME 场景
```

预览：420×315 RGB565；帧间隔 400ms；检测 900ms；识别 450ms。

## 十一、阅读清单

- [x] `ui_manager.c` — L3
- [x] `core/ui_events.*` — L3
- [x] `model/mqtt_device_model.*` — L4
- [x] 七个 `pages/page_*.c` — L2（结构已知）
- [ ] `services/ui_asset_service.*` — L2
- [ ] `main/display/lcd_display.cc` — L2（大文件接口级）

## 附录：关键 API

| API | 作用 |
|---|---|
| `UI_Manager_Init()` | 初始化智能家居 UI |
| `UI_Manager_Switch_Page()` | 切页 |
| `UI_Manager_Poll()` | 派发事件 |
| `ui_event_publish()` | 发布 UI 事件 |
| `device_model_apply_heartbeat()` | 写入 V2 快照 |
| `device_model_apply_heartbeat_v3()` | 写入 V3 快照 |
