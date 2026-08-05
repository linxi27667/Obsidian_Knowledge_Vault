# ESP32-P4 LVGL Demo v9 配置与烧录

## 2026-04-17 16:30:00

### 背景
用户使用 ESP32-P4-Function-EV-Board 开发板（芯片 v1.3），需要配置并烧录 LVGL v9.1 demo。官方示例代码无法直接编译烧录。

### 项目信息
- **项目路径**: E:\MCU\esp32\p4\lvgl_demo_v9
- **ESP-IDF版本**: v5.5.3（安装路径 E:\MCU\esp32\.espressif\v5.5.3\esp-idf）
- **LVGL版本**: v9.1.0（E:\MCU\esp32\p4\lvgl__lvgl-v9.1.0）
- **芯片版本**: ESP32-P4 v1.3
- **开发板**: ESP32-P4-Function-EV-Board
- **LCD**: 7英寸 MIPI DSI 电容触摸屏，1024x600，EK79007驱动
- **串口**: COM28

### 工作内容

#### 1. 修复 ESP32-P4 v1.3 芯片版本兼容性
- 操作: 在 sdkconfig.defaults 中添加 CONFIG_ESP32P4_SELECTS_REV_LESS_V3=y
- 状态: ✅ 完成
- 结果: 解决 v1.3 芯片与 IDF 默认 v3.1 最低版本要求的冲突

#### 2. 修复 CMakeLists.txt 路径错误
- 操作: 将 EXTRA_COMPONENT_DIRS 从 ../common_components 改为 ../examples/common_components
- 状态: ✅ 完成
- 结果: 正确指向 bsp_extra 组件

#### 3. 修复触摸初始化导致程序崩溃
- 操作: 修改 lvgl_adapter_init.c，将触摸初始化失败从 fatal (return NULL) 改为 warning (continue without touch)
- 状态: ✅ 完成
- 结果: GT911 触摸 I2C 通信失败不再导致程序崩溃，LVGL 继续运行

#### 4. 添加 EK79007 显示屏 DISPON 命令
- 操作: 在 esp_lcd_ek79007.c 的 panel_ek79007_init 函数中，init 完成后发送 0x29 (DISPON) 命令
- 状态: ✅ 完成
- 结果: DISPON 发送成功 (ret=0)

#### 5. 创建 IDF 构建脚本
- 操作: 创建 build_idf.bat 批处理文件，配置完整的 ESP-IDF v5.5.3 环境变量（工具链、Python venv、MSYSTEM 清理）
- 状态: ✅ 完成

#### 6. 编译、烧录、调试
- 操作: 多次编译烧录，通过串口日志验证
- 状态: ✅ 完成（软件层面）
- 当前串口日志状态：
  - ✅ MIPI DSI PHY 上电成功
  - ✅ EK79007 面板初始化成功 (version: 2.0.2)
  - ✅ DISPON 发送成功 (ret=0)
  - ✅ LVGL 任务启动成功
  - ✅ 背光 100%
  - ❌ GT911 触摸 I2C 失败（已绕过）

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| lvgl_demo_v9/sdkconfig.defaults | 修改 | 添加 ESP32P4_SELECTS_REV_LESS_V3=y |
| lvgl_demo_v9/CMakeLists.txt | 修改 | 修复 EXTRA_COMPONENT_DIRS 路径 |
| lvgl_demo_v9/main/lvgl_adapter_init.c | 修改 | 触摸失败改为警告继续运行 |
| lvgl_demo_v9/managed_components/espressif__esp_lcd_ek79007/esp_lcd_ek79007.c | 修改 | 添加 DISPON (0x29) 命令发送 |
| lvgl_demo_v9/build_idf.bat | 新增 | IDF 构建脚本 |

### 关键决策
- EK79007 驱动的 vendor_specific_init_default 序列只有 0x11 (SLEEPOUT)，缺少 0x29 (DISPON)，需要在 init 后补充
- 触摸 GT911 I2C 失败可能是硬件连接问题（排线/上拉电阻），先绕过以保证显示屏工作

### 遇到的问题
- **问题**: 编译时报 "MSys/Mingw is no longer supported" 错误
- **根因**: Bash shell 环境中 MSYSTEM 环境变量存在，ESP-IDF v5.5.3 不再支持 MSys 环境
- **解决**: 在 build_idf.bat 中设置 MSYSTEM= 清除该变量，并通过 CMD 执行

- **问题**: idf.py 找不到编译器 riscv32-esp-elf-gcc
- **根因**: 环境变量未包含工具链路径
- **解决**: 在 build_idf.bat 中完整设置 PATH

- **问题**: 首次烧录后程序崩溃 (MCAUSE=0x02 非法指令)
- **根因**: GT911 触摸初始化失败，导致 assert(disp != NULL) 触发
- **解决**: 修改 lvgl_adapter_init.c 使触摸失败不阻塞整个初始化流程

### 待办事项
- [x] 修复芯片版本兼容性
- [x] 修复编译路径问题
- [x] 修复触摸崩溃问题
- [x] 添加 DISPON 命令
- [x] 成功编译烧录
- [ ] 解决屏幕黑屏问题（可能硬件连接问题，见下方）
- [ ] 修复 GT911 触摸 I2C 通信

### 下次会话须知
> 软件已烧录成功，串口日志显示所有初始化步骤均成功（DSI PHY、EK79007、DISPON、LVGL任务、背光100%）。
> 但屏幕仍然黑屏，怀疑硬件连接问题：
> 1. FFC排线方向是否正确（金属触点朝向）
> 2. LCD适配板是否有5V供电
> 3. GPIO26(PWM背光)和GPIO27(RST_LCD)杜邦线连接是否正确
> 
> GT911 触摸 I2C 失败（地址 0x5D），需要检查 I2C 上拉电阻和接线。
> 使用 build_idf.bat 脚本进行编译烧录操作。
> 开发板串口: COM28
