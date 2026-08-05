# GUI-Guider智能家居仿真器修复

## 2026-04-19 00:53:07

### 背景
smart_home2.0 仿真器在 GUI-Guider 中运行后白屏未响应，需要排查并修复。上一次会话中已完成了字体替换、导航栏添加、FontAwesome图标清除等工作，但新编译后出现白屏卡死问题。

### 项目信息
- **项目路径**: E:\MCU\Gui-Guider\project\smart_home2.0
- **技术栈**: GUI-Guider 1.10.1-GA + LVGL v9.3.0 + MinGW/gcc + SDL2
- **目标硬件**: ESP32-P4 + 1024x600 MIPI DSI

### 工作内容

#### 1. 排查白屏未响应根因
- 操作: 先用极简代码（仅创建一个label显示"HELLO WORLD"）测试LVGL渲染是否正常
- 状态: ✅ 完成
- 结果: LVGL渲染正常，深蓝色背景+白色文字正常显示，白屏问题不在底层

#### 2. 逐步恢复UI代码定位问题
- 操作: 只加载setup_scr_home一个页面，不加导航栏、不加事件
- 状态: ✅ 完成
- 结果: 首页UI正常显示！布局、颜色、按钮都正确。中文显示为方块（缺少CJK字体）

#### 3. 测试5个页面+事件+定时器
- 操作: 恢复setup_scr_home/devices/scenes/network/settings + events_init + custom_timer_init
- 状态: ⏳ 待验证
- 结果: 编译通过但运行白屏未响应，问题在5页面加载或事件绑定环节

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| lvgl-simulator/lv_conf.h | 修改 | 恢复DIRECT渲染模式，关闭TINY_TTF |
| lvgl-simulator/Makefile | 修改 | -O3→-O0 -g0→-g（降优化+开调试） |
| lvgl-simulator/main.c | 修改 | 移除SDL_PumpEvents，简化main入口 |
| generated/gui_guider.c | 修改 | 移除sim_fonts_init()调用 |
| custom/sim_fonts.c | 修改 | 移除TTF加载，直接返回Montserrat |
| custom/sim_fonts.h | 修改 | 移除TTF相关声明 |

### 关键决策
- **渲染模式**: 改回 `LV_DISPLAY_RENDER_MODE_DIRECT` + `BUF_COUNT 1`（之前能正常显示的模式）
- **字体策略**: 放弃运行时加载TTF（太慢导致卡死），改用内置Montserrat字体（中文会显示方块）
- **编译优化**: Makefile从 `-O3 -g0` 改为 `-O0 -g`（降低优化便于调试）

### 遇到的问题
- **问题**: 启用TINY_TTF加载simhei.ttf（9.3MB）后白屏未响应
- **根因**: 运行时加载8个字号的超大中文字库耗时极长，看起来像卡死
- **解决**: 关闭TINY_TTF，使用内置Montserrat字体，UI响应正常

### 待办事项
- [ ] 确认5页面+事件绑定时是否卡死（下一步测试）
- [ ] 添加底部Tab栏导航（Home/Devices/Scenes/Network/Settings）
- [ ] 添加非首页的返回按钮
- [ ] 解决中文显示方块问题（需要更高效的字体方案）

### 下次会话须知
> **重要发现**: 单页加载正常 → 5页加载+事件绑定后白屏卡死。需要在main.c中分步恢复代码定位是哪个函数导致的。
> **下一步**: 先把5个setup函数都加上测试，如果卡了再逐个排除。如果不卡就加events_init，再逐个排查。
> **导航栏代码**: custom/nav_bar.c 和 custom/nav_bar.h 已就绪，待主流程稳定后接入。
