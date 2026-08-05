# GUI-Guider集成方案

## 2026-04-18 14:12:00

### 背景
续上三轮会话（17:00/17:15/17:30）GUI Guider 代码已编译通过并烧录成功，但用户反馈三个问题：1)点击按键自动复位 2)比例不对 3)中文全是乱码。本轮需要修复这些问题并重新烧录验证。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_gui
- **技术栈**: ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **GUI Guider版本**: 1.10.1-GA（打印机/复印机界面模板）
- **相关分支**: main

### 工作内容

#### 1. 修复点击按键复位崩溃
- 操作: 移除 Task_UI 自定义任务（与 esp_lv_adapter 内置 LVGL 任务冲突导致 watchdog）
- 操作: 移除 TaskUI_Create() 调用
- 操作: 移除 main.c 中的 task_ui.h 引用
- 状态: ✅ 完成
- 根因: esp_lv_adapter 自带 LVGL 任务，我们创建的 Task_UI 在同一 LVGL 上并发操作，导致 lv_inv_area 崩溃
- 解决: 完全移除自定义 UI 任务，LVGL 由 adapter 内置任务驱动

#### 2. 改用 lv_timer 替代 UI_Main_Loop
- 操作: gui_adapter.c 中使用 lv_timer_create() 创建周期性定时器（1s间隔）
- 操作: 移除 task_ui.c 中的 UI_Main_Loop() 和 Task_UI() 实现
- 状态: ✅ 完成

#### 3. 添加中文字体支持
- 操作: 使用 lv_font_conv 从 SourceHanSansSC-Normal.otf 生成 14px 中文字体
- 操作: 字体文件输出到 main/gui/generated/guider_customer_fonts/lv_font_chinese_14.c
- 状态: ✅ 完成
- 说明: 包含 ASCII 0x20-0x7F 范围 + 中文字符"智能家居控制系统年月日测试，。：%（）"
- 待完成: 需要在 gui_guider.h 中添加字体声明，并将各屏幕中文标签的字体改为中文字体

#### 4. 比例问题分析
- 发现: GUI Guider 模板设计分辨率为 480x272，与实际屏幕 ESP32-P4 的 BSP_LCD_H_RES/BSP_LCD_V_RES 一致
- 结论: 比例问题可能是字体缩放或 LVGL adapter 的 display 配置导致，需要烧录后验证

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/main.c | 修改 | 移除 TaskUI_Create()，移除 task_ui.h，GUI_Adapter_Init 在 esp_lv_adapter_lock 内调用 |
| main/gui/smart_home/gui_adapter.c | 修改 | 使用 lv_timer 驱动周期更新，移除 GUI_Adapter_Periodic_Update 直接调用 |
| main/gui/generated/guider_customer_fonts/lv_font_chinese_14.c | 新增 | 思源黑体 14px 中文字体 |

### 关键决策
- LVGL 任务由 esp_lv_adapter 内置驱动，不再创建自定义 UI 任务
- 使用 lv_timer 机制实现周期性 UI 数据更新（日期、WiFi图标等）
- 中文字体使用 lv_font_conv 从 SourceHanSansSC 生成 C 数组格式

### 遇到的问题
- **问题1**: 烧录后点击按键自动复位，watchdog 触发
- **根因**: Task_UI 与 esp_lv_adapter 内置 LVGL 任务冲突，并发操作 lv_inv_area 导致崩溃
- **解决**: 移除 Task_UI，LVGL 由 adapter 统一管理

- **问题2**: 中文标签显示乱码
- **根因**: GUI Guider 使用 Montserrat 字体，不支持中文字符
- **解决**: 生成思源黑体中文字体，待替换到各中文标签

- **问题3**: 串口被占用无法烧录
- **根因**: 之前的 monitor 进程或串口助手占用 COM28
- **解决**: 需要用户关闭占用程序后重新烧录

### 待办事项
- [x] 修复点击崩溃（移除 Task_UI）
- [x] 生成中文字体文件
- [ ] 在 gui_guider.h 中添加中文字体声明
- [ ] 将各屏幕中文标签字体改为中文字体
- [ ] **重新编译烧录验证**（需等 COM28 空闲）
- [ ] 验证比例是否正常
- [ ] 验证中文显示是否正常

### 下次会话须知
> Task_UI 已移除，LVGL 由 esp_lv_adapter 内置任务驱动。
> 中文字体已生成 lv_font_chinese_14.c，但尚未集成到各屏幕的标签中。
> 下次需要：1)在 gui_guider.h 声明字体 2)替换所有中文标签的字体指针 3)重新编译烧录。
> 烧录时需确保 COM28 空闲（无串口助手/monitor占用）。
