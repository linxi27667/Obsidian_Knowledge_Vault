# GUI-Guider集成方案

## 2026-04-18 17:15:00

### 背景
续上一轮会话的 GUI Guider 集成工作。上一轮代码已就位但未编译验证。本轮用户提供了 ESP-IDF v5.5.3 环境，要求全盘回退后深度修改，自行编译测试，确保项目能通过编译。

用户核心诉求：在 GUI Guider 的基础上修改成适配智能家居的页面，后续还能导回 GUI Guider 继续编辑。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_prj
- **技术栈**: ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **GUI Guider版本**: 1.10.1-GA（打印机/复印机界面模板）
- **相关分支**: main

### 工作内容

#### 1. 修复 ESP-IDF 环境配置
- 操作: 找到 ESP-IDF 5.5.3 位于 `E:\MCU\esp32\.espressif\v5.5.3\esp-idf`
- 操作: 创建 `idf_build.bat` 批处理脚本配置完整工具链路径
- 状态: ✅ 完成

#### 2. 修复中文自定义字体编译错误
- 操作: 字体文件 `lv_font_chinese_custom_14.c` 和 `16.c` 中 `#include "lvgl/lvgl.h"` 路径找不到
- 操作: 在 CMakeLists.txt 添加 `LV_LVGL_H_INCLUDE_SIMPLE` 编译定义
- 操作: 修正 `lv_font_chinese_custom_16.c` 中符号名从 `lv_font_chinese_custom` 改为 `lv_font_chinese_custom_16`（缺失后缀导致链接失败）
- 状态: ✅ 完成
- 结果: 编译通过，生成 `lvgl_demo_v9.bin` (987KB, 88% 剩余空间)

#### 3. 全盘回退并重新设计集成架构
- 操作: 确定新架构 — `gui/` 目录替代 `ui/`，分为 generated/（可替换）、custom/（可替换）、smart_home/（业务适配层，不受导出影响）
- 状态: ✅ 完成

#### 4. 创建 gui/ 目录结构
- 操作: 创建 `main/gui/generated/`、`main/gui/custom/`、`main/gui/smart_home/`
- 操作: 从 GUI Guider 导出目录复制 generated/ 和 custom/ 代码
- 状态: ✅ 完成

#### 5. 更新 CMakeLists.txt
- 操作: 添加 GUI_GENERATED_SOURCES、GUI_CUSTOM_SOURCES、GUI_ADAPTER_SOURCES
- 操作: 添加对应头文件包含路径
- 状态: ✅ 完成

#### 6. 创建智能家居业务适配层 (gui_adapter.c/h)
- 操作: 编写 GUI Guider 事件 ↔ APP 层函数桥接代码
- 状态: ⏳ 进行中

#### 7. 修改 main.c UI 入口
- 操作: 替换 `UI_Main_Init()` 为 `setup_ui(&guider_ui)`
- 状态: ⏳ 待完成

#### 8. 修改 task_ui.c 适配 GUI Guider 事件循环
- 状态: ⏳ 待完成

#### 9. 编译验证
- 状态: ⏳ 待完成

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/CMakeLists.txt | 修改 | 添加 gui/ 目录源文件，移除 ui/ 目录 |
| main/fonts/lv_font_chinese_custom_16.c | 修改 | 修正符号名 |
| idf_build.bat | 新增 | ESP-IDF 5.5.3 工具链配置 |
| main/gui/ | 新增 | GUI Guider 集成层目录结构 |

### 关键决策
- 采用三层分离架构：generated/（可替换）、custom/（可替换）、smart_home/（不变），确保 GUI Guider 重新导出时不会覆盖业务适配代码
- 保留中文自定义字体文件，通过 `LV_LVGL_H_INCLUDE_SIMPLE` 定义解决 include 路径问题
- 任务 UI 保持 `lv_timer_handler()` 调用（GUI Guider 事件由回调驱动，不需要特殊 UI 循环）

### 遇到的问题
- **问题1**: ESP-IDF 不在系统 PATH 中，Git Bash 下 `idf.py` 找不到
- **根因**: ESP-IDF v5.2.6 和 v5.5.3 路径不同，用户实际使用的是 v5.5.3
- **解决**: 创建自定义 `idf_build.bat` 配置完整工具链

- **问题2**: 中文字体符号 `lv_font_chinese_custom_16` 链接器找不到
- **根因**: lv_font_conv 生成的 16px 字体符号名缺少 `_16` 后缀
- **解决**: 手动修正符号名

### 待办事项
- [x] 修复 ESP-IDF 5.5.3 编译环境
- [x] 修复中文自定义字体编译/链接错误
- [x] 设计集成架构（三层分离）
- [x] 创建 gui/ 目录并复制 GUI Guider 代码
- [x] 更新 CMakeLists.txt
- [ ] 创建智能家居业务适配层 gui_adapter.c/h
- [ ] 修改 main.c UI 入口
- [ ] 修改 task_ui.c 适配 GUI Guider
- [ ] 编译验证
- [ ] 编写 GUI Guider 页面改造指南

### 下次会话须知
> 当前编译已通过（原手写 UI 版本），GUI Guider 代码已复制到 main/gui/ 目录下但尚未集成到 main.c。
> 下一步需要创建 gui_adapter.c/h 并修改 main.c/task_ui.c 完成集成，然后重新编译验证。
> CMakeLists.txt 已更新为 gui/ 目录，但旧 ui/ 目录的引用已移除。
> GUI Guider 的生成代码在 main/gui/generated/，自定义代码在 main/gui/custom/，业务适配层在 main/gui/smart_home/。
