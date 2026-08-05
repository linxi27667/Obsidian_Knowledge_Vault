# GUI-Guider集成方案

## 2026-04-18 17:00:00

### 背景
用户已用手工代码编写了 ESP32-P4 LVGL 智能家居界面的组件（6个页面），现在想用 NXP GUI Guider 1.10.1-GA 可视化设计 UI，完全替换手写 UI 页面，同时保障现有业务功能不受影响。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_prj
- **技术栈**: ESP-IDF v5.x + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **相关分支**: main
- **LVGL版本**: v9.4.0（与 GUI Guider 1.10.1-GA 兼容）
- **GUI Guider工程**: E:\MCU\Gui-Guider\project\test\c_code
- **参考demo**: E:\MCU\esp32\p4\lvgl_gui

### 工作内容

#### 1. 分析GUI Guider生成代码结构
- 操作: 阅读生成的 c_code 目录所有文件
- 状态: ✅ 完成
- 结果:
  - `generated/gui_guider.c/h` — UI状态机 + 屏幕切换动画
  - `generated/events_init.c/h` — 每个屏幕的事件回调（已绑定到控件）
  - `generated/setup_scr_scrXXX.c` — 9个屏幕的创建函数
  - `generated/widgets_init.c/h` — 键盘/文本框通用回调
  - `generated/guider_fonts/` — Montserrat字体（C数组内嵌，5个尺寸）
  - `generated/images/` — 图片资源（RGB565A8格式，20+张）
  - `custom/custom.c/h` — 用户自定义代码（滑块/加载动画）
  - 生成的屏幕：scrHome、scrCopy、scrCopy2、scrPrintMenu、scrPrintUSB、scrPrintMobile、scrSetup、scrLoader、scrFinished
  - 使用的是 LVGL v9 API（`lv_image_create`、`lv_screen_load` 等）

#### 2. 复制GUI Guider文件到目标项目
- 操作: 将 generated/ 和 custom/ 目录复制到 main/ui/guider_gen/
- 状态: ✅ 完成
- 结果: 48个文件已就位

#### 3. 创建兼容性补丁
- 操作: 创建 guider_compat.h 处理潜在API差异
- 状态: ✅ 完成
- 内容:
  - `LV_USE_GUIDER_SIMULATOR` → 0
  - `LV_USE_FREEMASTER` → 0
  - `LV_USE_ANALOGCLOCK` → 0
  - `lv_indev_get_act` → `lv_indev_active` (v8→v9兼容)
  - `LV_SCALE_NONE` → 256

#### 4. 创建GUI Guider适配器
- 操作: 创建 guider_ui_adapter.c/h
- 状态: ✅ 完成
- 提供: `Guider_UI_Init()` 和 `Guider_UI_Loop()` 接口

#### 5. 修改 main.c 入口
- 操作: 将 `UI_Main_Init()` 替换为 `Guider_UI_Init()`
- 状态: ✅ 完成

#### 6. 修改 task_ui.c 任务
- 操作: 将 `UI_Main_Loop()` 替换为 `Guider_UI_Loop()`
- 状态: ✅ 完成

#### 7. 修改 CMakeLists.txt
- 操作: 添加 GUIDER_SOURCES 和对应 INCLUDE_DIRS
- 状态: ✅ 完成
- 新增源: generated/*.c, guider_fonts/*.c, images/*.c, custom/*.c

#### 8. 清理不需要的代码
- 操作: 删除之前创建的 ui_callback_bridge.c/h（因GUI Guider自带events_init）
- 操作: 回退 app_device_ctrl.h/c 的修改（不改动业务层）
- 状态: ✅ 完成

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/main.c | 修改 | UI入口从UI_Main_Init改为Guider_UI_Init |
| main/CMakeLists.txt | 修改 | 添加GUI Guider源文件和头文件路径 |
| main/Tasks/Src/task_ui.c | 修改 | UI循环从UI_Main_Loop改为Guider_UI_Loop |
| main/ui/Src/guider_ui_adapter.c | 新增 | GUI Guider适配器实现 |
| main/ui/Inc/guider_ui_adapter.h | 新增 | GUI Guider适配器头文件 |
| main/ui/guider_gen/ | 新增 | GUI Guider生成代码完整目录(48文件) |
| main/ui/guider_gen/guider_compat.h | 新增 | LVGL v9兼容性补丁 |
| main/ui/guider_gen/generated/gui_guider.h | 修改 | 添加guider_compat.h引入 |

### 未编译测试原因
- 当前shell环境无法访问ESP-IDF工具链（idf.py不在PATH中）
- 需要用户在ESP-IDF命令行环境中手动执行 `idf.py build` 验证

### 待办事项
- [x] GUI Guider代码复制到项目
- [x] 兼容性补丁创建
- [x] 适配器层创建
- [x] main.c/task_ui.c/CMakeLists.txt修改
- [x] 业务层代码回退（不改动APP/BSP/Tasks层）
- [ ] **用户需要在ESP-IDF环境下编译验证**: `idf.py build`
- [ ] 如编译有错误，根据报错信息修复
- [ ] 后续可在GUI Guider中修改UI后重新导出替换guider_gen目录

### 下次会话须知
> GUI Guider集成代码已就位，但未编译验证。
> 用户需要在ESP-IDF终端中运行 `idf.py build` 检查编译是否通过。
> GUI Guider 生成的代码在 main/ui/guider_gen/ 下。
> 如果GUI Guider重新导出代码，只需替换 guider_gen/generated/ 和 guider_gen/custom/ 下的文件，适配器层和业务层不需要改动。
> 字体问题：生成的代码使用Montserrat字体（不支持中文），中文标签"智能家居控制系统"等会显示为方块，需要在GUI Guider中添加中文字体或后续适配FreeType。
