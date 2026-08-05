---
tags:
  - 项目管理
  - GitHub
  - 仓库重构
  - 命名规范
  - AI 辅助开发
  - GcCarLifts
created: 2026-05-15
updated: 2026-05-15
---

# GcCarLifts GitHub 仓库重构方案 & 完整目录详解

> **目标**: 建立清晰、统一、可扩展的仓库管理体系，便于团队协作与 AI 辅助开发。
> **状态**: 📝 规划中（尚未执行，仅展示重构后的预期状态）
> **对应公司**: GC Technology Limited（高昌科技）— gctechnology.com
> **数据来源**: 2026-05-15 直接从 GitHub 克隆的实际仓库内容

---

## 📌 一、命名规范定义（重构标准）

采用 **`类别_业务名称`** 格式（大驼峰 + 下划线），前缀明确标识仓库性质，后缀描述具体业务内容。

| 前缀 | 含义 | 适用内容 | 示例 |
|---|---|---|---|
| `Fw_` | Firmware (固件) | STM32/ESP32/单片机嵌入式代码 | `Fw_LifterController` |
| `Hmi_` | HMI (人机界面) | 显示屏 UI 工程、多语言配置 | `Hmi_Lifter_8.0MC` |
| `Hw_` | Hardware (硬件) | 原理图、PCB、BOM、封装库 | `Hw_CircuitBoards` |
| `Web_` | Website (网站) | 官网前端、后台管理系统 | `Web_OfficialSite` |
| `Cnc_` | CNC (数控) | 机床加工程序、后处理文件 | `Cnc_MachinePrograms` |
| `Doc_` | Documentation (文档) | 标准库、专利、技术手册 | `Doc_EquipmentStandards` |
| `Admin_` | Administration (行政) | 政策申报、财务报表、资质 | `Admin_GreenFactory` |
| `Design_` | Design (设计) | AI/PSD 源文件、3D 模型 | `Design_ProductCatalog` |
| `Tool_` | Tools (工具) | 烧录工具、自动化脚本、测试软件 | `Tool_FlashDownloader` |
| `Demo_` | Demo (演示) | 模板、示例代码 | `Demo_GitHubTemplate` |

---

## 📌 二、仓库重命名与拆分映射表

| 序号 | 现有名称 (Old) | **重构后名称 (New)** | 类别 | 文件数 | 重构动作 |
|---|---|---|---|---|---|
| 1 | `GcMultiLinkLift` | **`Fw_LifterController`** | 固件 | ~22,475 | 重命名 |
| 2 | `lifter_display_promgram` | **`Hmi_Lifter_8.0MC`** + **`Hmi_Lifter_TPFI`** | HMI | ~5,835 | **拆分为 2 个仓库** |
| 3 | `allCircuitBoardData` | **`Hw_CircuitBoards`** | 硬件 | ~585 | 重命名（固件移至 `Fw_`） |
| 4 | `gaochang-web` | **`Web_OfficialSite`** | 网站 | ~359 | 重命名 |
| 5 | `web-gaochang-bak` | **`Web_OfficialSite_Archive`** | 网站 | ~322 | 重命名（建议归档或删除） |
| 6 | `Auto-Equip-Standards` | **`Doc_EquipmentStandards`** | 文档 | 0 (空) | 重命名（需补充内容） |
| 7 | `GcPatents` | **`Doc_Patents`** | 文档 | ~392 | 重命名 |
| 8 | `NC-program` | **`Cnc_MachinePrograms`** | 数控 | ~9,397 | 重命名 |
| 9 | `gaochang-green-factory-gz` | **`Admin_GreenFactory`** | 行政 | ~467 | 重命名 |
| 10 | `Adobe_illustrate_model` | **`Design_ProductCatalog`** | 设计 | 2 | 重命名 |
| 11 | `demo-repository` | **`Demo_GitHubTemplate`** | 演示 | - | 重命名（建议删除） |

---

## 📌 三、针对老板 5 个问题的深度排查与拆分建议

### 1. 电路板的资料全不全？（对应原仓库 7：`allCircuitBoardData`）
*   **现状**: 包含 3 种板型（`01_2n20MrA`、`02_BV`、`03_SV`）。每种包含固件、硬件、生产资料。另有 `09_Doc` 文件夹。
*   **问题**: 
    *   **混杂**: 固件源码（`.gpj`, `.uvproj`）和硬件设计混在一起。
    *   **建议**: **硬件与代码分离**。

### 2. 电路板的程序全不全？（对应原仓库 7 & 1）
*   **现状**: 仓库 7 有旧板型/小板型程序（BV 板有 20+ 个固件版本，SV 板有 10+ 个版本），仓库 1 有主控程序。
*   **建议**: 建立 **`Fw_` (Firmware)** 统一仓库。

### 3. 嵌入式的程序全不全？（对应原仓库 1：`GcMultiLinkLift`）
*   **现状**: 包含 STM32F407 主控（新板/改造版）、ESP32 通信模块、OTA 程序。
*   **核心项目**:
    *   **新板系列 (newBoard)**: 5.5MC, 8.0MC, 8.0MC_ESP32, TPFI
    *   **改造版系列 (reconsitution)**: 5.5MC, 8.0MC, TPFI, clear_w25qxx
    *   **OTA 系列**: newBoard_Boot (Bootloader), 各型号 OTA APP
    *   **ESP32**: ESP32_Proj (ESP-NOW + UART 通信)
*   **代码结构**: 每个 STM32 项目包含 `APP/` (业务逻辑), `BSP/` (板级支持), `Core/` (STM32Cube 生成), `Drivers/` (HAL 库), `MDK-ARM/` (Keil 工程), `Middlewares/` (中间件), `RTT_easylog/` (日志)。

### 4. 嵌入式还有哪些有关的资料？
*   **现有文档**: `LEARNING_PATH_14D.md` (14 天学习路径), `NEWBOARD_OTA_APP_IOT_PLAN.md` (OTA 规划), `README.md`, `APP业务逻辑说明.md` (改造版 8.0MC), `OTA升级安全说明.md`。
*   **建议补充**: 通信协议说明书、引脚定义表、烧录与调试指南。

### 5. 显示屏单独分拆，对吧？（对应原仓库 2：`lifter_display_promgram`）
*   **现状**: 14 个文件夹，按型号和品牌分类。
*   **结论**: **强烈建议拆分！**

---

## 📌 四、详细拆分执行方案

### 1. 🖥️ 显示屏拆分策略 (原 `lifter_display_promgram`)

| 新仓库名 | 包含内容 (原文件夹) | 说明 |
|---|---|---|
| **`Hmi_Lifter_8.0MC`** | `0_8.0MC_屏幕_直接复制重量显示文本版`<br>`1_8.0MC_屏幕_无电池_无logo`<br>`1_8.0MC_屏幕_无重量_无logo`<br>`1_8.0MC_屏幕_无重量_无logo-意大利`<br>`2_8.0MC_屏幕_无电池_高昌`<br>`2_8.0MC_屏幕_无重量_高昌`<br>`3_8.0MC_屏幕_无电池_Duka`<br>`3_8.0MC_屏幕_无重量_Duka`<br>`4_8.0MC_屏幕_无电池_LAUNCH`<br>`4_8.0MC_屏幕_无重量_LAUNCH`<br>`5_8.0MC_屏幕_无重量_无logo-多语言` | 8.0MC 型号全部配置，共 11 个文件夹 |
| **`Hmi_Lifter_TPFI`** | `1_TPFI_屏幕_无重量_无logo`<br>`2_TPFI_屏幕_无重量_高昌`<br>`5_TPFI_屏幕_无重量_无logo-多语言` | TPFI 型号全部配置，共 3 个文件夹 |

### 2. 🔌 固件与硬件分离策略

| 新仓库名 | 来源 | 内容说明 |
|---|---|---|
| **`Fw_LifterController`** | 原 `GcMultiLinkLift` + 仓库 7 中的活跃源码 | 所有嵌入式源码 (STM32, ESP32, 小板 MCU) |
| **`Hw_CircuitBoards`** | 原 `allCircuitBoardData` | 仅保留硬件设计 (原理图, PCB) 和生产资料 (BOM, Gerber) |

---

## 📌 五、重构后仓库完整目录详解

> 以下目录结构基于 **2026-05-15 从 GitHub 实际克隆的内容**，包含所有文件夹和关键文件。

---

### 1. 📦 Fw_LifterController — 举升机主控固件

> **原仓库**: `GcMultiLinkLift`
> **文件数**: ~22,475 个文件
> **描述**: 多立柱液压举升机主控固件，基于 STM32F407 微控制器，实现 RS232 转 WiFi 通信、主从机协同控制、OTA 远程升级。

```text
Fw_LifterController/
│
├── 📄 根目录文件
│   ├── .gitignore
│   ├── GcMultiLinkLift.code-workspace       # VS Code 工作区配置
│   ├── README.md                            # 项目说明文档
│   ├── LEARNING_PATH_14D.md                 # 14 天学习路径（新员工培训）
│   ├── NEWBOARD_OTA_APP_IOT_PLAN.md         # 新版 OTA + IoT 开发计划
│   └── 251220.双胞式举升机控制程序及方案阶段性任务.xlsx  # 任务进度表
│
├── 📡 ESP32_Proj/                           # ESP32 通信模块项目 (ESP-IDF)
│   ├── main/
│   │   ├── CMakeLists.txt                   # ESP-IDF 构建配置
│   │   ├── main.c / main.h                  # ESP32 主程序入口
│   │   ├── espnow_uart_common.c / .h        # ESP-NOW + UART 通用通信模块
│   │   └── 说明.txt
│   └── download_ESP32/                      # ESP32 固件烧录工具包
│       ├── monitor.bat / monitor.ps1        # 烧录监控脚本
│       ├── README.md / 快速开始.txt
│       └── flash_download_tool/             # 乐鑫官方烧录工具 (含 Python 环境)
│           ├── configure/esp32c5/           # ESP32-C5 烧录参数
│           ├── dl_temp/                     # 烧录临时文件
│           ├── tools/python/                # 便携 Python + esptool/espefuse/espsecure
│           └── logs/                        # 烧录日志
│
├── 🔄 newBoard_OTA_APP/                     # 新版主板 OTA 远程升级程序
│   ├── newBoard_Boot/                       # Bootloader (引导程序)
│   │   ├── newBoard_Boot.ioc                # STM32CubeMX 配置
│   │   ├── OTA升级PC端说明.txt
│   │   ├── OTA升级包安全说明.md
│   │   ├── BSP/bsp_w25q128.c/.h             # W25Q128 Flash 驱动
│   │   ├── CRC32/crc32.c/.h                 # CRC32 校验
│   │   ├── Core/Inc+Src/                    # STM32Cube 生成的 HAL 代码
│   │   ├── Drivers/CMSIS + STM32F4xx_HAL_Driver/
│   │   ├── MDK-ARM/newBoard_Boot.uvprojx    # Keil MDK 工程
│   │   └── RTT_easylog/                     # SEGGER RTT 日志 + easylogger
│   │
│   ├── stm407_lifter_newBoard_5.5MC_OTA/    # 5.5MC 新版 OTA APP
│   ├── stm407_lifter_newBoard_8.0MC_OTA/    # 8.0MC 新版 OTA APP
│   └── stm407_lifter_newBoard_8.0MC_ESP32_OTA/  # 8.0MC ESP32 版 OTA APP
│       └── (每个 OTA APP 包含: APP/, BSP/, Core/, Drivers/, MDK-ARM/, Middlewares/, RTT_easylog/)
│           ├── APP/Inc+Src/                 # 应用层业务逻辑
│           ├── BSP/AT24CXX/                 # AT24CXX EEPROM 驱动
│           ├── BSP/W25QXX/                  # W25QXX Flash 驱动
│           ├── Middlewares/CRC16/           # CRC16 校验
│           ├── Middlewares/CRC32/           # CRC32 校验
│           ├── Middlewares/FIFO/            # 环形缓冲区
│           ├── Middlewares/Ymodem/          # Ymodem 文件传输协议
│           └── Middlewares/Third_Party/     # 第三方中间件 (FreeRTOS 等)
│
├── 🆕 新板系列 (stm407_lifter_newBoard_*)   # 新版主板固件 (STM32Cube 生成)
│   ├── stm407_lifter_newBoard_5.5MC/        # 5.5 吨新版
│   ├── stm407_lifter_newBoard_8.0MC/        # 8.0 吨新版
│   ├── stm407_lifter_newBoard_8.0MC_ESP32/  # 8.0 吨 + WiFi (ESP32) 版
│   └── stm407_lifter_newBoard_TPFI/         # TPFI 型号新版
│       ├── .mxproject / .gitignore          # STM32CubeMX 项目标记
│       └── MDK-ARM/
│           ├── startup_stm32f407xx.s        # 启动文件
│           └── stm407_lifter_reconsitution.uvprojx  # Keil 工程
│
├── 🔧 改造版系列 (stm407_lifter_reconsitution_*)  # 旧板改造固件
│   ├── stm407_lifter_reconsitution_5.5MC/   # 5.5 吨改造版
│   ├── stm407_lifter_reconsitution_8.0MC/   # 8.0 吨改造版
│   │   ├── stm407_lifter_reconsitution.ioc  # STM32CubeMX 配置
│   │   ├── APP业务逻辑说明.md               # ⭐ 重要文档：业务逻辑说明
│   │   ├── 举升机控制程序映射.txt            # 程序映射表
│   │   └── MDK-ARM/                         # Keil 工程
│   ├── stm407_lifter_reconsitution_TPFI/    # TPFI 改造版
│   └── stm407_lifter_reconsitution_clear_w25qxx/  # 清除 Flash 专用固件
│       └── (每个项目包含: .ioc, MDK-ARM/, Core/, Drivers/ 等)
│
└── 📋 每个 STM32 项目的标准目录结构
    ├── APP/Inc+Src/                         # 应用层 (14 个任务模块)
    │   ├── adc_task.c/.h                    # ADC 采样任务
    │   ├── battery_task.c/.h                # 电池管理任务
    │   ├── change_wifi_task.c/.h            # WiFi 切换任务
    │   ├── disk_task.c/.h                   # U 盘/SD 卡任务
    │   ├── encoder_task.c/.h                # 编码器任务
    │   ├── log_task.c/.h                    # 日志记录任务
    │   ├── move_lift_task.c/.h              # 举升机运动控制任务
    │   ├── onlineCheck_task.c/.h            # 在线检测任务
    │   ├── screen_task.c/.h                 # 屏幕显示任务
    │   ├── set_pwm_task.c/.h                # PWM 设置任务
    │   ├── user_key_task.c/.h               # 用户按键任务
    │   └── wifi_handle_task.c/.h            # WiFi 数据处理任务
    ├── BSP/                                 # 板级支持包
    │   ├── AT24CXX/                         # EEPROM 驱动
    │   ├── W25QXX/                          # Flash 驱动
    │   └── Inc/                             # BSP 头文件
    ├── Core/Inc+Src/                        # STM32CubeMX 自动生成的代码
    ├── Drivers/
    │   ├── CMSIS/                           # ARM CMSIS 库
    │   └── STM32F4xx_HAL_Driver/            # ST HAL 驱动库
    ├── MDK-ARM/                             # Keil MDK 工程目录
    │   ├── startup_stm32f407xx.s            # 启动汇编
    │   ├── stm407_lifter_reconsitution.uvprojx  # Keil 工程文件
    │   └── RTE/                             # Keil RTE 组件
    └── Middlewares/                         # 中间件
        ├── CRC16/ / CRC32/ / FIFO/ / Ymodem/
        └── Third_Party/                     # FreeRTOS 等第三方库
```

---

### 2. 📦 Hmi_Lifter_8.0MC — 8.0MC 型号 HMI 显示屏程序

> **原仓库**: `lifter_display_promgram` (拆分后)
> **文件数**: ~4,200 个文件 (估算)
> **描述**: 8.0MC 型号举升机 HMI 人机界面程序，涵盖高昌/Duka/LAUNCH/意大利版/多语言版等多品牌定制配置。

```text
Hmi_Lifter_8.0MC/
│
├── 0_8.0MC_屏幕_直接复制重量显示文本版/     # 基础版（直接复制重量显示文本）
│   ├── 8.0MC20251108.bak / .dpj / .pkgx    # HMI 工程文件（备份/项目/包）
│   ├── EVWindows.dat~ / frw0.frp            # 窗口配置
│   ├── PLCGEDefaultProperties.xml           # PLCG 默认属性
│   ├── HMI0/                                # 界面窗口文件 (.whe)
│   │   ├── 0_Frame0.whe / 0_首页.whe        # 首页框架
│   │   ├── 10_参数设置.whe / 11_用户管理.whe
│   │   ├── 12_添加用户.whe / 13_删除用户.whe
│   │   ├── 14_修改用户.whe / 15_删除用户.whe
│   │   ├── 16_修改密码.whe / 17_语言选择.whe
│   │   ├── 18_设备权限设置.whe / 18_添加设备.whe
│   │   ├── 19_设备状态.whe / 20_操作说明.whe
│   │   ├── 21_系统设置.whe / 22_操作说明(中文).whe
│   │   ├── 23_操作说明(英文).whe
│   │   ├── 2_Fast Selection.whe             # 快速选择
│   │   ├── 3_NUM Keyboard.whe               # 数字键盘
│   │   ├── 4_ASCII Keyboard.whe             # ASCII 键盘
│   │   ├── 5_File List Window.whe           # 文件列表窗口
│   │   ├── 6_Password Window.whe            # 密码窗口
│   │   ├── 7_Confirm Action Window.whe      # 确认操作窗口
│   │   ├── 8_HEX Keyboard.whe               # 十六进制键盘
│   │   ├── 9_Login Window.whe / 9_登录界面.whe
│   │   ├── 1_Common Window.whe              # 公共窗口
│   │   ├── 32766_Pass Through.whe           # 透传窗口
│   │   ├── 32767_External Device Download.whe
│   │   └── HMI0.lg / HMI0.whe               # HMI 主文件
│   ├── image/                               # 界面图片资源
│   │   ├── GC-8.0MC blue picture.jpg        # 高昌 8.0MC 蓝色背景图
│   │   ├── button-*.png / *.bmp             # 按钮图片
│   │   ├── k.button*.png / k.lamp*.png      # 控件图片
│   │   ├── WIFI信号*.png                    # WiFi 信号图标
│   │   ├── 运行状态*.png / 暂停*.png         # 状态图标
│   │   ├── 中国.jpg / 美国.jpg / 德国.jpg    # 国旗图片
│   │   └── ... (约 60+ 张图片)
│   ├── tar/                                 # 打包文件
│   └── temp/hmi0 + temp/image/              # 临时文件
│
├── 1_8.0MC_屏幕_无电池_无logo/              # 无电池、无 logo 版本
├── 1_8.0MC_屏幕_无重量_无logo/              # 无重量显示、无 logo 版本
├── 1_8.0MC_屏幕_无重量_无logo-意大利/        # 意大利版（无重量、无 logo）
├── 2_8.0MC_屏幕_无电池_高昌/                # 高昌品牌（无电池）
├── 2_8.0MC_屏幕_无重量_高昌/                # 高昌品牌（无重量）
├── 3_8.0MC_屏幕_无电池_Duka/                # Duka 品牌（无电池）
├── 3_8.0MC_屏幕_无重量_Duka/                # Duka 品牌（无重量）
├── 4_8.0MC_屏幕_无电池_LAUNCH/              # LAUNCH 品牌（无电池）
├── 4_8.0MC_屏幕_无重量_LAUNCH/              # LAUNCH 品牌（无重量）
└── 5_8.0MC_屏幕_无重量_无logo-多语言/        # 多语言版（含 11 种语言翻译表）
    └── (每个文件夹结构相同: HMI0/, image/, tar/, temp/)
```

---

### 3. 📦 Hmi_Lifter_TPFI — TPFI 型号 HMI 显示屏程序

> **原仓库**: `lifter_display_promgram` (拆分后)
> **文件数**: ~1,200 个文件 (估算)
> **描述**: TPFI 型号举升机 HMI 人机界面程序，含高昌/多语言版本。

```text
Hmi_Lifter_TPFI/
│
├── 1_TPFI_屏幕_无重量_无logo/               # 无重量显示、无 logo 版本
├── 2_TPFI_屏幕_无重量_高昌/                 # 高昌品牌（无重量）
└── 5_TPFI_屏幕_无重量_无logo-多语言/         # 多语言版
    └── (每个文件夹结构: HMI0/, image/, tar/, temp/)
```

---

### 4. 📦 Hw_CircuitBoards — 电路板硬件资料

> **原仓库**: `allCircuitBoardData`
> **文件数**: ~585 个文件
> **描述**: 举升机控制电路板完整技术资料库，按板型分类。包含 3 种板型的固件、硬件设计、生产资料。

```text
Hw_CircuitBoards/
│
├── 01_2n20MrA/                              # 2n20MrA 型号电路板
│   └── 01_Firmware/
│       ├── 6.0丝杠4圈(自适应)(响应)(模式)(延时)(式)--4-6T通用20231021/
│       │   ├── 1继电器定义和端口定义.doc      # 端口定义文档
│       │   ├── Gppw.gpj / .gps               # GP 软件工程文件
│       │   ├── Project.inf / ProjectDB.mdb    # 项目数据库
│       │   ├── 工程名.dp2                     # 工程配置文件
│       │   └── Resource/
│       │       ├── param.wpa                  # 参数文件
│       │       ├── Others/COMMENT.wcd         # 注释文件
│       │       └── POU/Body/MAIN.wpg          # 主程序
│       └── 丝杠4圈(自适应)(新程序)/
│           └── (同上结构)
│
├── 02_BV/                                   # BV 型号电路板
│   ├── 01_Firmware/                         # 固件源码 (Keil C51 / 汇编)
│   │   ├── 5.0FS/                           # 5.0FS 版本
│   │   │   ├── 5.0FS.c / STARTUP.A51        # C 源码 + 启动汇编
│   │   │   ├── 5.0FS.uvproj / .uvopt        # Keil 工程
│   │   │   ├── Listings/                    # 编译列表文件 (.lst, .m51)
│   │   │   └── Objects/50FS.hex             # 编译输出 (.hex)
│   │   ├── 5.0MB/                           # 5.0MB 版本
│   │   ├── 5.5M-D/                          # 5.5M-D 版本
│   │   ├── 5.5MM4/                          # 5.5MM4 版本
│   │   ├── M418(带过温保护)CE/               # M418 CE 认证版
│   │   ├── M418(带过温保护)(CE)(暂停用)/     # M418 CE 暂停版
│   │   ├── M4(单电机)(大台)(电动小车)/        # M4 单电机版
│   │   ├── MS1(自适应)(举升机)(举升延时)-(下降延时)-(一键下降)230426/
│   │   ├── MS1(自适应)(举升机)(举升延时)-(下降延时)200515/
│   │   ├── MS3(自适应)CE-(延时)0.25秒230720/
│   │   ├── MS3(自适应)CE-(延时)0.6秒230223/
│   │   ├── MS3(自适应)CE(延时)0.8秒230223/
│   │   ├── MS3(自适应)CE(举升延时)-(下降延时)-(延时)1.5秒230202/
│   │   ├── MS3(自适应)CE(举升延时)-(下降延时)-(无过温开启)200515/
│   │   ├── MS3(自适应)CE(举升延时)-(下降延时)200515/
│   │   ├── MS3(自适应)CE(举升延时)-(下降延时)5.5吨(双电机)230406/
│   │   ├── MSL0.25S(举升机)/                # MSL 0.25 秒版
│   │   ├── MSL(举升机)(新程序)/
│   │   ├── MSL(举升机)(新程序)(延时)1S(延时)0.25秒(带过温保护)/
│   │   ├── MSL(举升机)(新程序)(延时)0.5秒(带过温保护)/
│   │   ├── MSL(延时)0.5s/
│   │   ├── MSL(延时)0.65s/
│   │   ├── MSL(带过温保护)CE/
│   │   ├── MSL(带过温保护)CE-(暂停使用)/
│   │   └── MSL(带过温保护)CE(延时)1s(延时)0.25s/
│   │       └── (每个版本包含: .c, .uvproj, .uvopt, Listings/, Objects/)
│   ├── 02_Hardware/                         # 硬件设计文件
│   └── 03_Production/                       # 生产资料
│       └── BV02.Gerber_20190806.2PCS/       # Gerber 生产文件
│
├── 03_SV/                                   # SV 型号电路板
│   ├── 01_Firmware/
│   │   ├── HPD20250402(新程序)/             # HPD 2025-04-02 新版
│   │   ├── S-M4(自适应)CE-(举升延时)-(下降延时)-(无过温开启)20200515/
│   │   ├── S-M4(自适应)CE(举升延时)-(下降延时)200515/
│   │   ├── S-M4(自适应)(举升延时)-(下降延时)200515/
│   │   ├── SLE(自适应)CE-(举升延时)-(下降延时)-(无过温)-(延时)2S-(延时后)(延时关闭)20230406/
│   │   ├── SLE(自适应)CE-(举升延时)-(下降延时)-(无过温)-(延时)3S-(延时后)(延时关闭)20230406/
│   │   ├── SLE(自适应)(举升延时)-(下降延时)200603/
│   │   ├── SL(举升机)(延时)/
│   │   ├── S(举升机)(新程序)/
│   │   ├── 举升机(新程序)/
│   │   ├── 举升机(延时)4s/
│   │   └── 小车(举升机)(延时)/
│   │       └── (每个版本包含: .c, .uvproj, .uvopt, Listings/, Objects/)
│   ├── 02_Hardware/                         # 硬件设计文件
│   └── 03_Production/                       # 生产资料
│       └── SV05_20201026X5PCS/              # Gerber 生产文件
│
└── 09_Doc/                                  # 文档资料
    └── (单片机手册等技术文档)
```

---

### 5. 📦 Web_OfficialSite — 高昌科技官网

> **原仓库**: `gaochang-web`
> **文件数**: ~359 个文件
> **描述**: 高昌科技官方网站，基于 Astro + AstroWind 模板，支持中英文双语，部署于 Cloudflare Pages。

```text
Web_OfficialSite/
│
├── 📄 根目录配置文件
│   ├── astro.config.ts                      # Astro 构建配置
│   ├── tailwind.config.js                   # Tailwind CSS 配置
│   ├── tsconfig.json                        # TypeScript 配置
│   ├── eslint.config.js                     # ESLint 配置
│   ├── .prettierrc.cjs / .prettierignore    # Prettier 格式化
│   ├── package.json / package-lock.json     # NPM 依赖
│   ├── Dockerfile / docker-compose.yml      # Docker 部署配置
│   ├── vercel.json / netlify.toml           # Vercel/Netlify 部署
│   ├── wrangler.json                        # Cloudflare Workers 配置
│   ├── .npmrc / .dockerignore / .editorconfig
│   ├── AGENTS.md / CLAUDE.md                # AI 助手配置
│   ├── README.md / PROJECT_MANUAL.md        # 项目文档
│   ├── AstroWind学习路径.md                 # AstroWind 学习指南
│   ├── Astro框架对比分析.md                 # 框架选型分析
│   ├── 迁移项目到新仓库并替换bun为npm_c826bd35.plan.md
│   ├── 首页数据动态加载.md                   # 动态数据加载方案
│   └── 公司数据动态加载方案.md               # 公司数据方案
│
├── .github/workflows/
│   └── actions.yaml                         # GitHub CI/CD 工作流
│
├── .vscode/
│   ├── extensions.json / launch.json / settings.json
│   └── astrowind/config-schema.json         # AstroWind 配置 Schema
│
├── public/
│   ├── manifest.json / robots.txt / service-worker.js / _headers
│   ├── decapcms/config.yml / index.html     # Decap CMS 内容管理
│   └── images/
│       ├── gc-logo.webp / homePage1.webp
│       ├── about/                           # 关于我们图片
│       │   ├── 2003-guangzhou-hq.webp
│       │   ├── 2008-wuhu-GC-factory.webp
│       │   ├── 2014-wuhu-GS-factory.webp
│       │   └── gaochang-factory-front-door.webp
│       └── honors/                          # 荣誉资质图片
│           ├── en/                          # 英文版证书
│           │   ├── ISO9001 认证证书(英文).png
│           │   ├── EAC 认证证书.png
│           │   └── GC-5.5MSI CE.png
│           └── zh/                          # 中文版证书
│               ├── 高新技术企业证书.png
│               ├── 知识产权示范企业.png
│               └── ... (20+ 张证书)
│
├── nginx/nginx.conf                         # Nginx 反向代理配置
│
├── .log/ / .logs/                           # 构建日志
│   └── gaochang-web.production.*.build.log
│
└── src/                                     # (Astro 源代码目录)
    └── (页面组件、布局、样式等)
```

---

### 6. 📦 Web_OfficialSite_Archive — 官网备份（旧版本）

> **原仓库**: `web-gaochang-bak`
> **文件数**: ~322 个文件
> **描述**: 旧版本官网备份，待删除。结构与 `Web_OfficialSite` 类似，基于 Astro + AstroWind。

```text
Web_OfficialSite_Archive/
│
├── .dockerignore / .editorconfig / .gitignore
├── .npmrc / .prettierignore / .prettierrc.cjs
├── .stackblitzrc / sandbox.config.json
├── AGENTS.md
├── astro.config.ts / tailwind.config.js / tsconfig.json
├── eslint.config.js
├── docker-compose.yml / Dockerfile
├── netlify.toml / vercel.json / wrangler.json
├── package.json / package-lock.json
├── LICENSE.md
├── README.md / PROJECT_MANUAL.md
├── gaochang-web.code-workspace
├── .github/workflows/actions.yaml
├── .log/ / .logs/                           # 构建日志
├── .vscode/                                 # VS Code 配置
├── nginx/nginx.conf                         # Nginx 配置
├── public/                                  # 静态资源
│   ├── manifest.json / robots.txt / service-worker.js
│   ├── decapcms/                            # Decap CMS
│   └── images/                              # 图片资源
│       ├── about/                           # 关于图片
│       └── honors/                          # 荣誉证书
│           ├── en/                          # 英文版
│           └── zh/                          # 中文版
└── src/                                     # Astro 源代码
```

---

### 7. 📦 Doc_EquipmentStandards — 举升机设备标准库

> **原仓库**: `Auto-Equip-Standards`
> **文件数**: 0 (空仓库)
> **描述**: 举升机耐磨滑块与丝杆螺母的材料选型、标准获取与采购知识库。
> **⚠️ 状态**: 当前为空，需补充内容。

```text
Doc_EquipmentStandards/
│
└── (空仓库，待补充)
    建议补充内容:
    ├── GB-T 国家标准/                       # 国家标准文档
    ├── ISO 国际标准/                        # ISO 标准文档
    ├── 材料选型指南/                        # 工程塑料/金属选型
    ├── 供应商名录/                          # 合格供应商清单
    └── 测试报告/                            # 材料测试报告
```

---

### 8. 📦 Doc_Patents — 高昌科技专利库

> **原仓库**: `GcPatents`
> **文件数**: ~392 个文件
> **描述**: 系统化归档、分类、检索高昌科技专利资源，包含专利撰写 skill 和大量专利 Markdown 文档。

```text
Doc_Patents/
│
├── pdf_to_markdown.py                       # PDF 转 Markdown 脚本
├── README_pdf_to_markdown.md                # 脚本使用说明
├── requirements.txt                         # Python 依赖
│
├── 专利撰写skill参考资料/                   # 专利撰写 AI 技能
│   ├── requirements.txt
│   ├── resize_patent_figures.py             # 专利图片缩放脚本
│   ├── 专利模板-发明专利.md                 # 发明专利模板
│   ├── 专利撰写与提交-学习并执行指南.md      # 撰写指南
│   ├── .cursor/skills/patent-drafting-reading/
│   │   ├── reference.md                     # 参考资料
│   │   └── SKILL.md                         # Cursor 技能定义
│   ├── out_patent_application/              # 专利输出文件
│   │   ├── 专利申请书-一种具有远程监控预警功能的系统.md
│   │   └── 专利申请书-一种带自动升降功能的装置.md
│   ├── Technical_Disclosure_Document/       # 技术交底书
│   │   ├── doc_to_md.py                     # Word 转 Markdown
│   │   ├── 技术交底书-一种具有远程监控预警功能的系统.docx/.md
│   │   └── 技术交底书-一种带自动升降功能的装置.docx/.md
│   └── 未修改图片/ / 已修改图片/             # 专利附图
│
├── 高昌公司专利markdown/                    # 高昌专利 Markdown 归档
│   ├── 广州广泰(营运)汽车检测设备有限公司/   # 广州广泰专利
│   │   ├── CN112499502A-一种举升机.md
│   │   ├── CN112499502B-一种举升机.md
│   │   ├── CN112499503A-一种机械结构.md
│   │   ├── CN113603005A-多滑块结构.md
│   │   ├── CN113636494A-升降机构.md
│   │   ├── CN113636495A-锁止结构.md
│   │   ├── CN113683013A-同步机构.md
│   │   ├── CN113683014A-一种举升机.md
│   │   ├── CN114199458B-一种轮胎举升机.md
│   │   ├── CN117776023A-一种控制方法.md
│   │   ├── CN117963773A-一种支撑结构.md
│   │   ├── CN118083851A-剪叉式举升机支撑结构.md
│   │   ├── CN118108146A-一种举升机.md
│   │   ├── CN119972667A-同步举升装置.md
│   │   ├── CN206033115U-实用新型.md
│   │   └── ... (40+ 项专利)
│   └── 高昌公司/                            # 高昌公司专利
│       └── ... (更多专利文档)
```

---

### 9. 📦 Cnc_MachinePrograms — 数控机床加工程序

> **原仓库**: `NC-program`
> **文件数**: ~9,397 个文件
> **描述**: 数控加工领域的程序开发与管理，包含大量 GSK (广数) 系统 CNC 加工程序。

```text
Cnc_MachinePrograms/
│
├── 1楼_2号机_(广数系统GSK988TA)(加工中心的坐标)_12刀位/
│   ├── 0602.CNC / 1050.CNC / 10501.CNC
│   ├── 12354.CNC / 1253.CNC / 2.CNC / 3.CNC / 31.CNC
│   ├── 6.0TS.CNC / 60.CNC / 602.CNC / 6023.CNC / 603X.CNC / 6066.CNC
│   ├── 9000.CNC / CJJ.CNC / DJ0.CNC / DJ000.CNC / FG.CNC
│   ├── GC75.662.CNC / GC75.CNC
│   ├── GD100-61-2.CNC / GD100-61-7.CNC / GD100-65-4-B.CNC
│   ├── GD110-61-B.CNC / GD110-65.CNC / GD120-61-7.CNC / GD120-65.CNC
│   ├── GD125-61.CNC
│   ├── GD40-71-3-M20-B.CNC / GD40-71-WK.CNC / GD40-8-B.CNC
│   ├── GD50-35.CNC / GD50-50WK.CNC / GD50-52-A-B.CNC
│   ├── GD50-60-B.CNC / GD50-60-WK.CNC / GD50-64-3-B.CNC / GD50-64-3.CNC
│   ├── GD50-66-3.CNC
│   ├── GD60-48-3-B.CNC / GD60-62-2-B.CNC / GD60-66.CNC
│   ├── GD60-82-B.CNC / GD60-88-3.CNC
│   ├── GD63-62-3-.CNC / GD63-62-3-B.CNC
│   ├── GD70-16-B.CNC / GD70-16.CNC / GD70-64-7.CNC
│   ├── GD75-30-3.CNC / GD75-62-3-B.CNC / GD75-62-3.CNC
│   ├── GD75-62-7-B.CNC / GD75-62-7.CNC / GD75-70-A.CNC / GD75-70-B.CNC
│   ├── GD75-88-7.CNC
│   ├── GD80-61-2.CNC / GD80-65-3-B.CNC / GD80-65-3.CNC
│   ├── GD85-16-B.CNC / GD85-16.CNC / GD85-64-7.CNC
│   ├── GD90-62-3.CNC / GD90-62-7-B.CNC / GD90-62-7.CNC
│   ├── GGA100-73.CNC / GGA120-73.CNC / GGA63-70A.CNC
│   ├── GGAI-70-4.5.CNC / GGAI-80-45.CNC
│   ├── GGAI100-60.CNC / GGAI100-65-B.CNC / GGAI100-65X.CNC
│   ├── GGAI100-70-3.5MS.CNC
│   ├── GGAI110-68-B-3.5MS.CNC / GGAI110-70-3.5MS.CNC / GGAI110-70.CNC
│   ├── GGAI120-65.CNC / GGAI120-70-20.0MMI-B.CNC / GGAI120-70DJ.CNC
│   ├── GGAI125-70-4.5MS.CNC
│   ├── GGAI40-34.CNC / GGAI40-55.CNC / GGAI50-48.CNC / GGAI50-57.CNC
│   ├── GGAI50-62.CNC / GGAI60-28.CNC
│   ├── GGAI60-42-V8.0.CNC / GGAI60-42.CNC / GGAI60-45.CNC / GGAI60-58.CNC
│   ├── GGAI60-66-A.CNC / GGAI60-66-B.CNC
│   ├── GGAI63-70-B.CNC
│   ├── GGAI70-66-4.0SLE3.CNC / GGAI70-66.CNC / GGAI70-70.CNC
│   ├── GGAI75-38.CNC / GGAI75-51.CNC / GGAI75-58.CNC / GGAI75-66.CNC
│   ├── GGAI75-70-B.CNC
│   ├── GGAI80-30-B.CNC / GGAI80-70-X.CNC / GGAI80-70.CNC
│   ├── GGAI85-66.CNC / GGAI90-51.CNC
│   ├── GGAI90-60-8AGV.CNC
│   ├── GHS100-55.CNC / GL.CNC / GL12.0XT-A-11.CNC
│   ├── GLDG-QD.CNC / GLDG12XT.CNC / GZ.CNC
│   ├── HKZZT-2.CNC / HKZZT.CNC / HL000.CNC / HL001.CNC
│   ├── HS100-55-36.CNC / HS100-55-42.CNC / HS100-55-M36-B.CNC
│   ├── HS108-55.CNC / HS110-55-36-4.5MS.CNC
│   └── ... (数百个 .CNC 文件)
│
├── 1楼_3号机_(丝杠)(大端头)(GSK988TA)_12刀位/
├── 1楼_VMC850L加工中心/
├── 3楼_1号机_(广数系统GSK980)_4刀位/
├── 3楼_2号机_(广数系统GSK980)_6刀位/
├── 3楼_3号机_(广数系统)(新系统)980TDC_4刀位/
├── 3楼_4号机_(广数系统)_4刀位/
├── 3楼_5号机_(广数系统)(小系统)_4刀位/
├── 3楼_6号机_(广数系统)_4刀位/
├── 3楼_7号机_(广数系统)_6刀位/
├── 3楼_8号机_(广数系统)_4刀位/
└── MC/                                    # 加工中心通用程序
    └── (各机床对应的 CNC 加工程序)
```

---

### 10. 📦 Admin_GreenFactory — 广州高昌绿色工厂申报

> **原仓库**: `gaochang-green-factory-gz`
> **文件数**: ~467 个文件
> **描述**: 绿色工厂政策申报资料，包含国家级/省级/市级绿色工厂申报指南、参考材料、申报文稿及佐证材料。

```text
Admin_GreenFactory/
│
├── 📄 根目录文件
│   ├── .gitattributes
│   ├── AGENTS.md / CLAUDE.md / README.md
│   ├── gaochang-green-factory-gz.code-workspace
│   ├── 260410-绿色工厂申报要求-一个清单.md     # 申报要求清单
│   ├── extract_pv.py                          # Python 提取脚本
│   └── _patch_docx_renew.py                   # Word 文档补丁脚本
│
├── 01-政策文件和2026年申报指南/               # (空，待补充)
│
├── 02-绿色工厂参考资料/
│   ├── 高昌科技.高昌科技提供参考/
│   │   └── 250815.高昌科技绿色工厂外部参考资料/
│   │       ├── 全国碳市场研究白皮书.pdf
│   │       ├── 1_国家级绿色工厂/
│   │       │   ├── 0_参考资料/
│   │       │   ├── 1_申报通知/
│   │       │   ├── 3_模板/
│   │       │   ├── 4_案例/
│   │       │   ├── 企业案例/
│   │       │   └── 政策法规/
│   │       │       └── 02 双碳政策/
│   │       ├── 1_广东省省级绿色工厂/
│   │       │   ├── 0_参考资料/
│   │       │   │   └── 历史版本/
│   │       │   │       ├── 01-国家级绿色工厂-新版.pptx
│   │       │   │       ├── 02-广东省绿色工厂-旧版.pptx
│   │       │   │       ├── 02-广东省绿色工厂-旧版2025.pptx
│   │       │   │       └── 03-广东省绿色工厂-东莞.pptx
│   │       │   ├── 1_示范案例/
│   │       │   │   └── 东莞市2025年市级绿色工厂示范.wps
│   │       │   ├── 1_申报通知/
│   │       │   └── 1_高昌科技申报通知/
│   │       ├── 1_东莞市市级绿色工厂/
│   │       │   ├── 0_参考资料/
│   │       │   │   └── 01-国家级绿色工厂-新版.pptx
│   │       │   ├── 1_申报指南/
│   │       │   ├── 1_高昌科技申报/
│   │       │   └── 3_模板/
│   │       ├── 2_能源管理体系/
│   │       │   └── 能源管理体系证书/
│   │       ├── 3_环境管理体系/
│   │       ├── 3_职业健康安全管理体系/
│   │       │   └── 证书/
│   │       ├── 3_质量管理体系/
│   │       │   └── 证书/
│   │       ├── DG-东莞-绿色工厂/
│   │       ├── GD-广东-绿色工厂/
│   │       ├── JS-江苏-绿色工厂/
│   │       ├── 前批项目通过企业名单、分数/
│   │       ├── 参考资料/
│   │       │   ├── 1-广东省绿色工厂-新版.pptx
│   │       │   └── 国家级绿色工厂申报指南20240401 V1.0/
│   │       │       ├── 绿色工厂申报书解读《绿色工厂评价通则》（GBT36132-2018）.xmind
│   │       │       ├── 1-国家级绿色工厂申报流程/
│   │       │       ├── 2-绿色工厂评价基础要求及知识产权推荐/
│   │       │       ├── 3-绿色工厂通则解读/
│   │       │       │   ├── 国家级绿色工厂企业基本情况表/
│   │       │       │   └── 维度指标对比表/
│   │       │       ├── 4_高昌科技/
│   │       │       │   ├── 关于广泰-企业创新平台项目-证明材料2024年3月-2024年4月/
│   │       │       │   └── 绿色工厂能源管理体系证明材料/
│   │       │       ├── 5_评价标准/
│   │       │       └── 绿色工厂需要提交的材料（参考用）/
│   │       ├── 分厂分厂案例/
│   │       └── 绿色工厂评价报告/
│   └── 高昌科技.沙利文企业管理咨询有限公司/
│
├── 03-申报文稿+佐证材料-高昌科技/
│   ├── 1-国家级绿色工厂数据登记信息登记表.md
│   ├── 指标1-统计报表B204-1和B205-1/
│   │   ├── 指标1-2佐证-B204-1企业能源购进/
│   │   └── ...
│   └── ... (申报文稿和佐证材料)
│
└── 04-其他/                                   # (其他补充材料)
```

---

### 11. 📦 Design_ProductCatalog — 产品目录 AI 设计源文件

> **原仓库**: `Adobe_illustrate_model`
> **文件数**: 2 个文件
> **描述**: 高昌科技产品目录 Adobe Illustrator 设计源文件。

```text
Design_ProductCatalog/
│
├── GC_Catelog_Model.ai                      # 产品目录 AI 源文件
└── README.md                                # 说明文档
```

---

## 📌 六、AI 辅助开发落地指南

仓库规范化后，AI (如 Cursor, Claude, Copilot) 将发挥巨大作用。以下是具体应用场景：

### 1. 代码解释与生成 (针对 `Fw_LifterController`)
*   **场景**: 新员工看不懂 STM32 的定时器中断逻辑。
*   **操作**: 在 IDE 中选中代码 → 问 AI "解释这段代码的逻辑，并画出流程图"。

### 2. 协议文档生成 (针对 `Fw_` 和 `Hmi_`)
*   **场景**: 需要编写 RS232 通信协议文档。
*   **操作**: 投喂 `Fw_LifterController` 中的串口处理代码 → 让 AI "根据代码提取所有支持的指令，生成 Markdown 格式的通信协议文档"。

### 3. 专利与技术交底书 (针对 `Doc_Patents`)
*   **场景**: 发明了一种新的举升机同步算法。
*   **操作**: 投喂 `Fw_LifterController` 中的同步算法代码 → 让 AI "基于此代码逻辑，撰写一份专利技术交底书"。

### 4. 标准检索 (针对 `Doc_EquipmentStandards`)
*   **场景**: 查询耐磨滑块的摩擦系数标准。
*   **操作**: 在 `Doc_EquipmentStandards` 中搜索 → 让 AI "总结 GB/T XXXX 中关于工程塑料摩擦系数的测试方法和要求"。

---

## 📌 七、执行步骤清单

1.  **本地备份**: Clone 所有仓库到本地备份文件夹。 ✅ (已完成)
2.  **创建新仓库**: 在 GitHub 上按新名称创建空仓库。
3.  **迁移代码**:
    *   **HMI**: 复制对应文件夹内容到新仓库。
    *   **固件**: 合并 STM32 和小板源码到 `Fw_LifterController`。
    *   **硬件**: 清理 `Hw_CircuitBoards`，删除源码，只留设计文件。
4.  **更新 Remote**: 本地 Git 执行 `git remote set-url origin <新 URL>`。
5.  **清理**: 删除 `demo-repository` 和 `web-gaochang-bak`。
6.  **AI 训练**: 将新仓库结构告知 AI 助手，建立索引。
