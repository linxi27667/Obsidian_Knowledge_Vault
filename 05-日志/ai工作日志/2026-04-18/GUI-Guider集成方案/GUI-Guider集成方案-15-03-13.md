# GUI-Guider集成方案 — 移除运行时字体替换

## 2026-04-18 15:03:13

### 背景
上一版本实现了运行时字体替换（在 `gui_adapter.c` 中递归遍历控件替换 Montserrat 为中文字体），但用户反馈存在字体错位、点击组件闪退等 bug。用户决定废弃该方案，改为在 GUI Guider 图形界面中直接导入中文字体，导出代码即正确。

本轮工作：移除所有运行时字体替换代码，恢复干净的 `gui_adapter.c`，确保点击触摸不闪退。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_gui
- **技术栈**: ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS + ESP32-P4
- **GUI Guider版本**: 1.10.1-GA（打印机/复印机界面模板）
- **相关分支**: main

### 工作内容

#### 1. 移除运行时字体替换代码
- 操作: 从 `gui_adapter.c` 删除 `replace_font_recursive()`、`GUI_Adapter_Replace_Chinese_Font()`、`LV_FONT_DECLARE(lv_font_chinese_14)`
- 操作: 从 `gui_adapter.h` 删除 `GUI_Adapter_Replace_Chinese_Font()` 声明
- 操作: 删除 `main/gui/smart_home/lv_font_chinese_14.c`
- 状态: ✅ 完成
- 效果: `gui_adapter.c` 恢复纯净状态，只做 `setup_ui()` + `custom_init()` + 定时器创建

#### 2. 下载中文字体供用户 GUI Guider 导入
- 操作: 从 GitHub 下载两个免费中文字体到 `fonts/` 目录
- 状态: ✅ 完成
- 结果:
  - `SourceHanSansSC-Normal.otf` (16MB) — Adobe 思源黑体，成功下载
  - `NotoSansSC-Regular.ttf` (2.3MB) — Google Noto Sans SC，成功下载
  - `AlibabaPuHuiTi-3-55-Regular.ttf` — 阿里巴巴普惠体，GitHub 直接下载始终返回 HTML，下载失败

#### 3. 编译验证
- 操作: 尝试通过 Bash 调用 `idf.py build`
- 状态: ⏳ 待用户在 CMD 中执行
- 原因: Git Bash 环境下 IDF Python 虚拟环境路径无法正确激活，需要用户在 Windows CMD/PowerShell 中运行 `idf_build.bat`

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| main/gui/smart_home/gui_adapter.c | 修改 | 移除运行时字体替换全部代码 |
| main/gui/smart_home/gui_adapter.h | 修改 | 移除 GUI_Adapter_Replace_Chinese_Font 声明 |
| main/gui/smart_home/lv_font_chinese_14.c | 删除 | 不再需要的中文字体 C 文件 |

### 关键决策
- **废弃运行时字体替换**：用户确认该方案有字体错位、点击闪退等 bug，不可用
- **新方案**：用户在 GUI Guider 中图形化导入 TTF/OTF 中文字体 → 导出 → 直接用，零 hack

### 待办事项
- [x] 移除运行时字体替换代码
- [x] 下载中文字体到 fonts/ 目录
- [x] gui_adapter.c 恢复干净状态
- [ ] 用户在 GUI Guider 中导入中文字体并重新导出
- [ ] 用户在 CMD 中运行 `idf_build.bat` 编译
- [ ] 烧录验证中文显示和触摸点击

### 下次会话须知
> `gui_adapter.c` 现在是干净版本，只包含 `setup_ui()` + `custom_init()` + 1s 定时器。
> 不再有运行时字体替换。中文显示依赖用户在 GUI Guider 中手动导入中文字体。
> `fonts/` 目录下已有两个可用中文字体：`SourceHanSansSC-Normal.otf` 和 `NotoSansSC-Regular.ttf`。
> `copy_gui.bat` 仍然可用，一键替换 GUI Guider 导出代码。
> `smart_home/` 目录下的文件不受 GUI Guider 重新导出影响。
