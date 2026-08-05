# GUI-Guider智能家居面板设计

## 2026-04-18 19:00:00

### 背景
用户需要基于小智ESP32项目架构，设计一套GUI-Guider风格的智能家居控制面板UI，1024x600分辨率，思源黑体，适配ESP-IDF 5.5.3 + LVGL v9.4。先要求生成可运行代码，后要求废弃第一版，生成可直接导入GUI-Guider的`.guiguider`项目文件，并提供第二版重构提示词。

### 项目信息
- **项目路径**: `E:\MCU\Gui-Guider\project\smart_home` (v1.0 已废弃，保留参考)
- **v2.0路径**: `E:\MCU\Gui-Guider\project\smart_home2.0` (待按提示词重构)
- **对标项目**: `E:\MCU\esp32\xaiozhi1111111111111111111111111\xiaozhi-esp32-main`
- **技术栈**: GUI-Guider 1.10.1 / LVGL v9 / ESP-IDF 5.5.3 / ESP32-P4
- **屏幕**: 1024x600 MIPI DSI + GT911触摸

### 工作内容

#### 1. 研读GUI-Guider代码架构
- 操作: 深度分析 `test/c_code` 目录，理解`generated/` + `custom/`架构模式
- 状态: ✅ 完成
- 结果: 掌握了`gui_guider.h`(UI结构体)、`setup_scr_*.c`(屏幕构建)、`events_init.c`(事件注册)的模式

#### 2. 研读小智ESP32项目完整架构
- 操作: 全面分析 xiaozhi-esp32-main，包括boards/display/APP/BSP/protocols/mcp_server等
- 状态: ✅ 完成
- 关键发现:
  - **三层楼IoT架构**: 一楼(大厅灯/大门)、二楼(3灯+风扇+晾衣架)、三楼(阳台灯+2天窗+晾衣架)
  - **ESP-NOW协议**: IOT_CMD_DISCOVER/ANNOUNCE_V2/SET_LIGHT/SET_SERVO等12种命令
  - **设备状态**: kDeviceStateIdle/Connecting/Listening/Speaking
  - **MCP工具**: set_brightness(0-100), set_volume(0-100), set_theme(light/dark)
  - **WiFi配网**: HotSpot AP + BluFi + 声学配网
  - **存储**: NVS持久化
  - **1024x600板**: esp-p4-function-ev-board (MIPI DSI)

#### 3. 研读GUI-Guider .guiguider JSON格式
- 操作: 逆向工程 `test/test.guiguider` (84000行JSON)
- 状态: ✅ 完成
- 结果: 完全理解`FrontJson`屏幕定义、widget属性、style数组、event动作链的JSON结构

#### 4. 生成v1.0智能家居项目 (smart_home/)
- 操作: 创建完整的GUI-Guider架构C代码 + .guiguider项目文件
- 状态: ✅ 完成
- 内容:
  - 5个Tab: 首页/设备/场景/WiFi/设置
  - `generated/`: gui_guider.h + 6个setup文件 + events_init.c/h
  - `custom/`: custom.c/h + lv_conf_ext.h
  - `smart_home.guiguider`: 311KB，可直接GUI-Guider打开
  - import/font/: 已复制Montserrat和思源宋体

#### 5. 提供v2.0重构提示词 (smart_home2.0/)
- 操作: 基于小智架构约束，编写完整的v2.0重构提示词
- 状态: ✅ 完成 (等待用户执行)
- v2.0核心变更:
  - 首页增加设备状态指示器 + ESP-NOW从机在线列表
  - 设备页按楼层分组(一楼/二楼/三楼)，对接真实IoT API
  - 场景页映射 `App_IOT_Scenario_XXX()`
  - 网络页增加ESP-NOW设备管理区
  - 设置页对接MCP Tool (亮度/音量/主题)
  - 颜色方案改为深色状态栏(#1A1A2E)

### 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `smart_home/smart_home.guiguider` | 新增 | GUI-Guider项目文件 311KB |
| `smart_home/generated/gui_guider.h` | 新增 | UI结构体+颜色常量 |
| `smart_home/generated/gui_guider.c` | 新增 | TabView构建入口 |
| `smart_home/generated/widgets_init.h` | 新增 | 函数声明 |
| `smart_home/generated/setup_scr_statusbar.c` | 新增 | 状态栏初始化 |
| `smart_home/generated/setup_scr_home.c` | 新增 | 首页控件 |
| `smart_home/generated/setup_scr_devices.c` | 新增 | 设备页控件 |
| `smart_home/generated/setup_scr_scenes.c` | 新增 | 场景页控件(2x2网格) |
| `smart_home/generated/setup_scr_wifi.c` | 新增 | WiFi页+密码对话框 |
| `smart_home/generated/setup_scr_settings.c` | 新增 | 设置页控件 |
| `smart_home/generated/events_init.c` | 新增 | 全部事件回调 |
| `smart_home/generated/events_init.h` | 新增 | 事件声明 |
| `smart_home/custom/custom.c` | 新增 | 定时器+事件注册 |
| `smart_home/custom/custom.h` | 新增 | 自定义接口 |
| `smart_home/custom/lv_conf_ext.h` | 新增 | LVGL扩展配置 |
| `smart_home/fonts/font_shsans.h` | 新增 | 字体占位声明 |
| `smart_home/CMakeLists.txt` | 新增 | ESP-IDF组件注册 |
| `smart_home/README.md` | 新增 | 完整文档 |
| `smart_home/import/font/montserratMedium.ttf` | 复制 | 字体资源 |
| `smart_home/import/font/SourceHanSerifSC-Regular.otf` | 复制 | 字体资源(占位) |
| `generate_guiguider.py` | 新增 | Python生成脚本 (933行) |

### 关键决策
- **一键导入优先**: 用户不需要在GUI-Guider中手动重建，直接生成`.guiguider`文件
- **v1.0用LV Symbol**: 图标用LV_SYMBOL而非图片，减少资源依赖
- **场景页改为2x2网格**: 比原始列表设计更有视觉层次
- **v2.0完全重构**: 废弃v1.0的通用设计，改为与小智项目深度契合的专用面板

### 遇到的问题
- **问题1**: `make_cont()`缺少`shadow_color`参数导致Python脚本报错
- **解决**: 补充函数签名和default_style透传
- **问题2**: Windows Python 输出GBK编码错误
- **解决**: 避免在Python print中使用Unicode特殊字符
- **注意**: `smart_home/`中已有C源码和`.guiguider`两种产出，后续以`.guiguider`为主

### 待办事项
- [ ] 用户清理 smart_home2.0/ 目录
- [ ] 用户执行v2.0重构提示词，生成完整v2.0项目
- [ ] v2.0需在GUI-Guider中打开验证UI布局
- [ ] v2.0需替换思源宋体为思源黑体
- [ ] 后续将v2.0 C代码移植到 xiaozhi-esp32-main 的 display 层

### 下次会话须知
> 1. `smart_home/` 是v1.0通用设计，已废弃但保留C代码参考
> 2. `smart_home2.0/` 是v2.0工作目录，需要用户先清理后按提示词重新生成
> 3. `generate_guiguider.py` 是核心生成脚本，可直接复用/修改
> 4. v2.0必须与小智项目深度对接：三层楼IoT设备、ESP-NOW、MCP Tool、NVS存储
> 5. 小智项目的IoT API在 `main/APP/Src/iot_controller.c` 中定义
> 6. ESP-NOW命令结构体: `iot_command_packet_t {command, device_id, gpio_index, value, reserved[4]}`
> 7. 目标硬件是 ESP32-P4 Function EV Board (1024x600 MIPI DSI + GT911)
> 8. 字体必须用思源黑体 SourceHanSansSC-Regular.ttf，当前用思源宋体占位
