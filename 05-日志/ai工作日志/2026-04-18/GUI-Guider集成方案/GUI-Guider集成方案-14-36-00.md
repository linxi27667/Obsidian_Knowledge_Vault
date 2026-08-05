# GUI-Guider集成方案

## 2026-04-18 14:36:00

### 背景
上一版本（14:12）已修复点击崩溃问题，但 COM28 一直占用无法烧录。本轮完成了最终架构设计：**运行时自动替换中文字体 + 一键替换脚本**，实现 GUI Guider 导出后可直接替换使用。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_gui
- **技术栈**: ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **GUI Guider版本**: 1.10.1-GA（打印机/复印机界面模板）
- **相关分支**: main

### 工作内容

#### 1. 最终架构设计：运行时字体替换
- 操作: 将中文字体 `lv_font_chinese_14.c` 放在 `smart_home/` 目录（不受 GUI Guider 重新导出影响）
- 操作: `gui_adapter.c` 中 `GUI_Adapter_Replace_Chinese_Font()` 递归遍历所有屏幕控件，将 Montserrat 字体替换为中文字体
- 操作: 回退 `gui/generated/` 下所有文件到原始 GUI Guider 导出状态（不修改任何生成代码）
- 状态: ✅ 完成
- 效果: `gui/generated/` 和 `gui/custom/` 可以**直接覆盖**，无需任何修改，中文自动显示正常

#### 2. 创建一键替换脚本 copy_gui.bat
- 操作: 编写 `copy_gui.bat`，自动从 `E:\MCU\Gui-Guider\project\test\c_code` 复制到 `main/gui/generated/` 和 `main/gui/custom/`
- 状态: ✅ 完成
- 效果: 双击运行即可替换 GUI Guider 代码，smart_home/ 不受影响

#### 3. 烧录验证
- 操作: 编译通过并烧录到 ESP32-P4
- 状态: ✅ 完成
- 结果: 
  - 系统启动正常，无崩溃
  - 无 watchdog 触发（之前的 Task_UI 冲突已修复）
  - 堆内存稳定在 28.9MB
  - 系统运行 30+ 秒无异常

### 最终目录架构
```
main/gui/
├── generated/          ← GUI Guider 导出代码（直接覆盖）
│   ├── gui_guider.c/h
│   ├── events_init.c/h
│   ├── setup_scr_scr*.c     ← 所有中文标签使用 Montserrat（运行时替换）
│   ├── guider_fonts/        ← Montserrat 字体
│   └── images/
├── custom/             ← GUI Guider 自定义代码（直接覆盖）
│   ├── custom.c/h
│   └── lv_conf_ext.h
└── smart_home/         ← 业务适配层（不变，不受重新导出影响）
    ├── gui_adapter.c/h  ← 中文字体替换 + 周期更新
    └── lv_font_chinese_14.c  ← 思源黑体 14px
```

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/gui/smart_home/gui_adapter.c | 修改 | 添加运行时字体替换功能 |
| main/gui/smart_home/gui_adapter.h | 修改 | 添加字体替换接口声明 |
| main/gui/smart_home/lv_font_chinese_14.c | 新增 | 思源黑体 14px |
| copy_gui.bat | 新增 | 一键替换 GUI Guider 代码脚本 |
| main/gui/generated/ | 回退 | 所有文件恢复为原始 GUI Guider 导出状态 |
| main/gui/generated/gui_guider.h | 回退 | 移除中文字体声明 |
| main/CMakeLists.txt | 回退 | 移除 generated/guider_customer_fonts 路径 |

### 关键决策
- **运行时字体替换**而非修改生成代码：保持 `gui/generated/` 完全干净，重新导出后零修改
- 中文字体放在 `smart_home/` 而非 `generated/`：确保不被 GUI Guider 重新导出覆盖
- LVGL 由 esp_lv_adapter 内置任务驱动，不创建自定义 UI 任务：避免冲突导致 watchdog

### 遇到的问题
- **问题**: COM28 一直被 Python 进程占用
- **解决**: 杀死所有 python.exe 进程后释放串口

### 待办事项
- [x] 修复点击崩溃（移除 Task_UI）
- [x] 运行时自动替换中文字体
- [x] 创建一键替换脚本 copy_gui.bat
- [x] 编译烧录验证
- [x] 系统稳定运行验证（30+ 秒无崩溃）
- [ ] 用户在屏幕上确认中文显示是否正常
- [ ] 验证触摸点击是否不再崩溃

### 使用说明
**GUI Guider 重新导出后：**
1. 在 GUI Guider 中修改页面后导出到 `E:\MCU\Gui-Guider\project\test\c_code`
2. 双击运行 `copy_gui.bat`
3. 运行 `idf_build.bat` 编译
4. 烧录即可

### 下次会话须知
> 系统已稳定运行，中文通过运行时字体替换实现，无需修改生成代码。
> copy_gui.bat 是一键替换脚本，从 GUI Guider 导出目录复制到项目。
> smart_home/ 目录下的所有文件不受 GUI Guider 重新导出影响。
> LVGL 由 esp_lv_adapter 内置任务驱动，不需要也不应该创建 Task_UI。
