# GUI-Guider集成方案

## 2026-04-18 17:30:00

### 背景
续上两轮会话（17:00 代码已就位但未编译，17:15 全盘回退重新设计三层架构），本轮完成了 GUI Guider 集成代码的完整实现。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_gui
- **技术栈**: ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **GUI Guider版本**: 1.10.1-GA（打印机/复印机界面模板）
- **相关分支**: main

### 工作内容

#### 1. 创建 gui/ 三层目录结构并复制代码
- 操作: 创建 `main/gui/generated/`、`main/gui/custom/`、`main/gui/smart_home/`
- 操作: 从 `E:\MCU\Gui-Guider\project\test\c_code` 复制 generated/ 和 custom/ 代码
- 状态: ✅ 完成

#### 2. 创建智能家居业务适配层
- 操作: 编写 `gui_adapter.c/h`
- 操作: `GUI_Adapter_Init()` — 调用 `setup_ui(&guider_ui)` + `custom_init()`
- 操作: `GUI_Adapter_Periodic_Update()` — 更新日期、WiFi图标、墨水进度条
- 操作: `GUI_Adapter_Notify_*()` — 业务层主动通知 UI 的接口
- 状态: ✅ 完成

#### 3. 更新 CMakeLists.txt
- 操作: 添加 GUI_GENERATED_SOURCES、GUI_CUSTOM_SOURCES、GUI_ADAPTER_SOURCES
- 操作: 添加对应头文件包含路径：gui/generated gui/custom gui/smart_home
- 操作: 移除旧 ui/ 目录引用
- 状态: ✅ 完成

#### 4. 修改 main.c UI 入口
- 操作: 替换 `lv_demo_benchmark()` 为 `GUI_Adapter_Init()`
- 操作: 添加 `Sys_Task_Manager_Init()` 和各个 `TaskXXX_Create()` 调用
- 操作: 添加必要头文件：gui_adapter.h, task_wifi.h, task_mqtt.h, task_device.h, task_monitor.h, task_ui.h
- 状态: ✅ 完成

#### 5. 修改 task_ui.c 实现 UI_Main_Loop
- 操作: 实现 `UI_Main_Loop()` — 调用 `lv_timer_handler()`
- 操作: 添加周期性更新（每 200 次循环约 1s 调用 `GUI_Adapter_Periodic_Update()`）
- 状态: ✅ 完成

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/CMakeLists.txt | 修改 | 添加 gui/ 目录源文件，移除 ui/ 目录 |
| main/main.c | 修改 | UI入口从demo改为GUI_Adapter_Init，创建所有任务 |
| main/Tasks/Src/task_ui.c | 修改 | 实现UI_Main_Loop，添加周期更新 |
| main/gui/ | 新增 | GUI Guider 集成层完整目录 |
| main/gui/generated/ | 新增 | GUI Guider 导出代码（约48文件） |
| main/gui/custom/ | 新增 | GUI Guider 自定义代码（3文件） |
| main/gui/smart_home/gui_adapter.c | 新增 | 智能家居业务适配层实现 |
| main/gui/smart_home/gui_adapter.h | 新增 | 智能家居业务适配层头文件 |

### 架构说明
```
main/gui/
├── generated/      ← GUI Guider 导出代码（重新导出时直接替换）
│   ├── gui_guider.c/h      → lv_ui 结构体 + setup_ui()
│   ├── events_init.c/h     → 各屏幕事件回调（已绑定到控件）
│   ├── setup_scr_scr*.c    → 9个屏幕创建函数
│   ├── guider_fonts/       → Montserrat字体
│   └── images/             → 图片资源
├── custom/         ← GUI Guider 自定义代码（重新导出时直接替换）
│   ├── custom.c/h          → slider_adjust_img_cb, loader_anim_cb
│   └── lv_conf_ext.h       → LVGL配置扩展
└── smart_home/     ← 业务适配层（不变，不受重新导出影响）
    ├── gui_adapter.c/h     → GUI ↔ APP层桥接
```

### 关键决策
- 采用三层分离架构：generated/（可替换）、custom/（可替换）、smart_home/（不变）
- 事件回调由 setup_scr_scrXXX() 自动注册，不需要单独调用 events_init_scrXXX()
- `guider_ui` 全局变量定义在 gui_adapter.c 中（generated/ 中只声明 extern）
- UI_Main_Loop 每 5ms 调用 lv_timer_handler()，每 1s 周期性更新 UI 数据
- 墨水进度条暂用设备状态模拟，后续可改为真实传感器数据

### 待编译验证
- ⚠️ 当前 Git Bash 环境无法访问 ESP-IDF v5.5.3 工具链（export.bat 需要 Windows CMD）
- 需要在 Windows CMD 中运行 `E:\MCU\esp32\.espressif\v5.5.3\esp-idf\export.bat` 然后 `idf.py build`
- 或运行项目根目录下的 `idf_build.bat`
- 已做静态 API 兼容性检查：LVGL v9.4.0 所有使用的 API 均存在

### 待办事项
- [x] 创建 gui/ 目录结构
- [x] 复制 GUI Guider generated/custom 代码
- [x] 创建 gui_adapter.c/h
- [x] 更新 CMakeLists.txt
- [x] 修改 main.c
- [x] 修改 task_ui.c
- [ ] **编译验证**: `idf.py build`（需在 ESP-IDF CMD 环境中）
- [ ] 如编译有错误，根据报错信息修复
- [ ] 在 GUI Guider 中将打印机页面改为智能家居页面后重新导出

### 下次会话须知
> GUI Guider 集成代码已完整实现，所有文件已就位。
> 三层架构：gui/generated/（可替换）、gui/custom/（可替换）、gui/smart_home/（不变）。
> GUI Guider 生成的代码在 main/gui/generated/ 下。
> 重新导出时只需替换 generated/ 和 custom/ 下的文件，smart_home/ 不受影响。
> 需要在 ESP-IDF CMD 环境中运行 `idf.py build` 验证编译。
> 当前 GUI Guider 模板是打印机/复印机界面，后续需在 GUI Guider 中重新设计为智能家居页面。
> 字体使用 Montserrat（不支持中文），中文标签需要后续在 GUI Guider 中添加中文字体。
