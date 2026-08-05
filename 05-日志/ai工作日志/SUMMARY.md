# 工作日志汇总索引

## 2026-05-20
- [LVGL智能家居融合 Phase1实施记录](./2026-05-20/LVGL智能家居融合 Phase1实施记录.md) — 将 `lvgl_demo_v9` 智能家居面板融合进 xiaozhi-for-p4 主项目，完成需求分析(READ_DOC.md)、实施计划(PALN.md)、Phase1代码实现与固件烧录(COM28)；修复 WakeNet 启动崩溃(懒加载)、GT911触摸注册、字体过大问题

## 2026-04-19
- [GUI-Guider智能家居仿真器修复-11-48](./2026-04-19/GUI-Guider智能家居仿真器修复/GUI-Guider智能家居仿真器修复-11-48-00.md) — 修复smart_home2.guiguider模板：Application.screen缺少完整widgets定义导致代码生成卡死，从FrontJson派生填充后keys完全匹配
- [GUI-Guider智能家居仿真器修复-14-20](./2026-04-19/GUI-Guider智能家居仿真器修复/GUI-Guider智能家居仿真器修复-14-20-00.md) — 参考test项目架构重生成setup_scr_*.c，所有源文件编译成功，make链接阶段env target在Git Bash下语法冲突
- [GUI-Guider智能家居仿真器修复](./2026-04-19/GUI-Guider智能家居仿真器修复/GUI-Guider智能家居仿真器修复-00-53-07.md) — 白屏未响应排查：TINY_TTF加载大字库致卡死，改为内置Montserrat解决；单页加载正常，5页+事件卡死待排查

## 2026-04-18
- [LVGL中文字体下载](./2026-04-18/LVGL中文字体下载/LVGL中文字体下载-16-49-41.md) — 下载20个思源黑体LVGL预编译.c字体文件(12-38px)、头文件、CMakeLists模板、完整使用教学文档
- [GUI-Guider智能家居面板设计](./2026-04-18/GUI-Guider智能家居面板设计/GUI-Guider智能家居面板设计-19-00-00.md) — 逆向工程.guiguider格式，生成可直接导入GUI-Guider的智能家居项目(v1.0)，提供v2.0重构提示词(深度契合小智IoT架构)
- [GUI-Guider-UI设计清单](./2026-04-18/GUI-Guider-UI设计清单/GUI-Guider-UI设计清单-18-00-00.md) — 完整UI设计规格文档，含5个页面所有控件坐标/尺寸/颜色/字体/事件回调，供GUI Guider图形化创建使用
- [ESP32-P4-LVGL智能家居系统-14-32](./2026-04-18/ESP32-P4-LVGL智能家居系统/ESP32-P4-LVGL智能家居系统-14-32-19.md) — 修复屏幕不亮（移除Task_UI冲突、禁用字体压缩）、Flash烧录修复、恢复业务代码
- [GUI-Guider集成方案-17-15](./2026-04-18/GUI-Guider集成方案/GUI-Guider集成方案-17-15-00.md) — ESP-IDF 5.5.3 环境配置、字体编译修复、GUI Guider 代码集成架构设计、gui/ 目录创建
- [GUI-Guider集成方案](./2026-04-18/GUI-Guider集成方案/GUI-Guider集成方案-17-00-00.md) — 评估GUI Guider 1.10.1与现有LVGL v9.4.0项目集成可行性，制定桥接方案
- [GUI-Guider集成方案-项目交接指南](./2026-04-18/GUI-Guider集成方案/GUI-Guider集成方案-项目交接指南.md) — 完整项目交接文档：架构、替换流程、6大踩坑记录、中文导入指引
- [GUI-Guider集成方案-15-03](./2026-04-18/GUI-Guider集成方案/GUI-Guider集成方案-15-03-13.md) — 废弃运行时字体替换、gui_adapter.c恢复干净、下载中文字体
- [GUI-Guider集成方案-14-36](./2026-04-18/GUI-Guider集成方案/GUI-Guider集成方案-14-36-00.md) — 运行时字体替换方案、copy_gui.bat脚本、编译烧录验证通过
- [ESP32-P4-LVGL智能家居系统-02-30](./2026-04-18/ESP32-P4-LVGL智能家居系统/ESP32-P4-LVGL智能家居系统-02-30-00.md) — 修复LVGL死锁崩溃、全中文UI、CJK字体乱码修复、iOS动画、编译烧录成功
- [ESP32-P4-LVGL智能家居系统-14-35](./2026-04-18/ESP32-P4-LVGL智能家居系统/ESP32-P4-LVGL智能家居系统-14-35-00.md) — lv_font_conv自定义字体修复汉字乱码、清理Guider残留引用、编译成功、README创建

## 2026-04-17
- [ESP32-P4 LVGL Demo 配置烧录](./2026-04-17/ESP32-P4-LVGL-Demo配置烧录-16-30-00.md) — ESP32-P4 v1.3 芯片兼容性修复、LVGL demo 编译烧录成功，屏幕黑屏待排查
