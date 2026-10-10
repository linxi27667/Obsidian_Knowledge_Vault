---
title: Gc_Iot_Lift 新电脑环境配置提示词
aliases:
  - Gc_Iot_Li 新电脑环境配置提示词
tags:
  - 高昌举升机
  - Gc_Iot_Lift
  - 环境配置
  - 嵌入式
  - STM32
  - FreeRTOS
  - MQTT
created: 2026-10-10
updated: 2026-10-10
project_url: https://github.com/GcCarLifts/Gc_Iot_Li
status: needs-repository-verification
---

# Gc_Iot_Lift 新电脑环境配置提示词

## 使用说明

下面代码块是一条可以直接复制给 Codex、Cursor 或 Antigravity 的完整提示词。它要求代理先核对仓库和源码证据，再安装工具和执行构建，避免因为仓库私有、改名或文档过期而误配环境。

当前已核实的前置情况：

- 用户提供的两个 Codex 对话链接实际是同一个对话 ID，因此目前只能读取到一条深度对话。
- 用户给出的仓库地址 `https://github.com/GcCarLifts/Gc_Iot_Li` 当前访问返回 404；可能是私有仓库、仓库改名、地址拼写错误或当前账号无权访问。
- Obsidian 知识库中的项目资料多处写作 `Gc_Iot_Lift`，本地历史路径为 `E:/MCU/gaochang/Gc_Iot_Lift`，与 `Gc_Iot_Li` 不完全一致。不能未经确认就用其他仓库替代。
- 以下技术信息来自知识库整理，最终以目标仓库中的 README、工程文件、锁定文件和实际脚本为准。

## 可复制的完整提示词

```text
你是一名 Windows 嵌入式与物联网工程环境配置专家。请帮我在一台全新的 Windows 电脑上配置并验证高昌举升机物联网项目的开发环境。

项目候选地址：
https://github.com/GcCarLifts/Gc_Iot_Li

目标：
1. 确认仓库地址、权限和真实项目名称。
2. 将项目放在 E 盘，推荐路径为 E:\MCU\gaochang\<真实仓库名>。
3. 根据源码证据安装必要工具，不安装无关软件，不凭经验臆造版本或构建命令。
4. 完成固件和 Web 管理端的可重复构建验证；未得到明确授权前，不连接或操作真实设备，不烧录固件。
5. 输出一份完整环境报告：工具版本、安装路径、环境变量、源码路径、构建命令、构建结果、阻塞项和下一步建议。

一、先验证仓库身份和访问权限

- 先访问项目地址并执行只读检查，例如 git ls-remote；如果返回 404、权限错误或仓库不存在，立即暂停克隆，明确告诉我需要确认：
  1) GitHub 组织名；
  2) 仓库名；
  3) 当前账号是否有访问私有仓库的权限。
- 不要擅自把 Gc_Iot_Li 替换为 Gc_Iot_Lift、GcMultiLinkLift 或其他相似仓库。
- 私有仓库使用 Git Credential Manager、GitHub CLI 登录或浏览器授权；不要让我把 Personal Access Token、密码、私钥或云平台密钥粘贴到聊天中。
- 只有确认地址和权限后，才执行克隆。若我确认真实名称为 Gc_Iot_Lift，使用我确认过的地址和目录名，并在报告中记录该更正。

二、克隆和源码勘察

- 在 E 盘创建清晰的项目目录，例如 E:\MCU\gaochang\<repo>。
- 克隆后先读取并记录以下文件（存在才读取）：README、AGENTS.md、CONTRIBUTING.md、package.json、package-lock.json、yarn.lock、pnpm-lock.yaml、.env.example、.ioc、.uvprojx、.uvoptx、.code-workspace、CI 工作流和构建脚本。
- 先生成源码地图，不要立刻全量修改文件。识别以下目录及其实际名称：
  - GC_Big_Scissor：大型剪叉；
  - GC_Small_Scissor：小型剪叉；
  - GC_Thin_Scissor：薄型剪叉；
  - GC-Two_Pillars：双柱；
  - Gaochang_Iot_Web：Node.js Web 管理平台。
- 以实际源码为准核对 MCU、编译器、FreeRTOS 版本、外设、串口、DMA、网络协议、构建目标和启动方式。
- 不要把知识库中的推测当成源码事实；每项结论注明来源文件或命令输出。

三、Windows 工具安装原则

根据源码实际需要安装，安装前先检查电脑上是否已有可用版本：

- Git for Windows、PowerShell；
- Keil MDK-ARM 以及项目要求的 ARM Compiler。若存在 .uvprojx 或 Keil 工程，优先按工程配置选择编译器；提示我处理合法许可证，不要绕过授权；
- SEGGER J-Link Software and Documentation Pack，用于 J-Link/SWD/RTT；
- STM32CubeProgrammer：只有项目烧录或调试流程需要时安装；
- STM32CubeMX：只有存在 .ioc 或项目文档要求时安装；
- Node.js LTS：只有存在 Gaochang_Iot_Web 或其他 Node.js 工程时安装；
- Python：只有发现脚本实际依赖时安装，并以 requirements.txt、pyproject.toml 或脚本说明为准；
- 7-Zip 等辅助工具按需安装；
- Cursor、Antigravity 或 VS Code 只作为编辑器，不替代 Keil 的正式构建链。

建议的 E 盘布局（若安装器支持且不破坏系统默认配置）：

- E:\MCU\gaochang\<repo>：项目源码；
- E:\Tools\Keil：Keil 相关工具；
- E:\Tools\JLink：J-Link 工具；
- E:\Tools\STM32Cube：Cube 工具；
- E:\Tools\Node、E:\Tools\Python：仅在确有需要且安装器支持时使用。

不要为了追求统一路径强行修改只支持系统盘的安装器。每次安装后验证命令是否可用，例如：

- git --version
- node --version
- npm --version
- python --version
- armcc --version 或 armclang --version（以实际安装为准）
- JLink.exe / JLinkExe
- STM32_Programmer_CLI

四、固件工程配置

知识库记录的候选技术栈为 STM32F407ZET6、STM32 HAL、FreeRTOS/CMSIS-RTOS2、Keil MDK-ARM、J-Link、SEGGER RTT、EasyLogger、W25Qxx SPI、USART3 DMA/FIFO 和 TAS-LTE-892D_s4 4G DTU；这些内容必须与目标仓库实际源码再次核对。

- 找出每个固件型号对应的 MDK-ARM 工程和 Target。
- 读取工程中的 Device、Include Paths、Preprocessor Definitions、Compiler Version、Linker Scatter File、输出目录和依赖文件。
- 优先使用 Keil 工程自身配置构建，不要随意改工程选项。
- 先选择一个明确的目标做基线构建，再按计划构建其他型号；不要无说明地全量构建。
- 如果缺少器件包、编译器、许可证或库文件，记录确切错误和解决所需的合法安装包，不要下载来路不明的破解包。
- 构建输出、临时文件和本地配置应遵守项目 .gitignore；不要把生成物或本机绝对路径提交到仓库。

五、Web 管理平台配置

如果确认存在 Gaochang_Iot_Web：

- 先读取 package.json 的 scripts、engines 和依赖版本。
- package-lock.json 存在时优先使用 npm ci；不存在时再根据项目说明使用 npm install。
- 先读取 README 和 .env.example，再创建本机 .env；不能猜测环境变量名称或生产配置。
- 不提交 .env、密码、Token、证书、私钥、数据库文件、抓包文件或真实设备数据。
- 按 package.json 中实际存在的 scripts 启动或构建；不要自行发明 npm 命令。
- 只做本机健康检查和非破坏性测试，避免清库、迁移生产数据库或覆盖真实设备数据。

知识库中的候选 Web 技术栈为 Node.js、Express、mqtt.js、better-sqlite3、ws、JWT、bcryptjs 和 Chart.js；仅作为排查线索，必须以 package.json 和源码为准。

六、协议和安全边界

知识库记录的候选协议包括：MQTT、设备 Client ID gc-lift-{chip_uid}、上行主题 gaochang/lift/v1/devices/{chip_uid}/up、下行主题 gaochang/lift/v1/devices/{chip_uid}/down、QoS 1、msg_id 幂等和设备响应；UART 候选速率为 9600，兼容检查值为 115200。所有内容先与源码和配置核对。

- 不要把 MQTT 地址、用户名、密码、Token 或证书写死到源码，也不要在报告中输出秘密。
- 知识库曾记录过 broker 地址 8.134.167.240:1883，但这只是待核验的历史参考，不能直接当作生产配置使用。
- 升降机的急停、限位、光电、远程锁、状态机和最终输出仲裁必须由本地控制逻辑保障；网络断开不能让设备失去本地安全控制。
- 保持 App_IO_All_Off 之类的全关闭安全路径；不要让 MQTT、Web、UART 或日志阻塞控制任务。
- 不要随意改变输入有效电平、消抖时间、任务周期、优先级、看门狗或故障处理逻辑。
- 发现源码中存在长时间阻塞延时、网络等待进入控制环或绕过急停的风险时，先报告，不要未经授权重构。

七、烧录和硬件调试

- 未得到我明确授权前，不执行烧录、擦除、升级 Bootloader、修改 Option Bytes、改变真实设备参数或连接生产 MQTT。
- 如果我授权硬件调试，再核对 STM32F407 芯片、SWD 接线、J-Link 驱动、目标电压、COM 口和设备序列号。
- 使用 J-Link/SWD/SEGGER RTT 时保留原有调试配置；不要覆盖用户已有工程或设备备份。
- 先进行无硬件的编译、静态检查和日志配置验证，再做最小范围硬件冒烟测试。

八、验收标准

完成后必须给出：

1. 仓库 URL、真实名称、访问验证结果和源码路径；
2. 实际安装的工具、版本、安装位置、许可证或权限阻塞项；
3. Git、Keil/ARM Compiler、J-Link、Cube 工具、Node.js/Python 的验证命令和结果；
4. 每个已选择固件目标的构建命令、结果和错误摘要；
5. Web 项目的依赖安装、构建和本机健康检查结果；
6. 哪些步骤未执行，以及未执行原因；
7. 仍需我确认的仓库、账号、硬件、许可证、网络或生产配置问题；
8. 后续最小安全步骤。

九、Git 操作纪律

- 先执行 git status、git branch --show-current、git remote -v，并保护现有用户修改。
- 不执行 git reset --hard、git checkout --、历史重写、强制推送或批量删除，除非我明确授权。
- 需要修改时优先新建分支，并只提交本次任务产生的文件。
- 提交前检查 git diff、git diff --check 和敏感文件；禁止提交 .env、密钥、Token、私钥、数据库、编译输出和设备日志。
- 在我明确同意后才 push；push 前报告将要推送的分支、提交和文件列表。

请按“检查 → 证据记录 → 安装 → 配置 → 构建 → 非破坏性验证 → 汇报”的顺序执行。每完成一个阶段都列出实际命令、结果和阻塞项；遇到仓库地址或权限问题时停止在安全边界内，不要用相似仓库猜测替代。
```

## 相关知识库线索

- [[03-项目/高昌举升机-IOT/01-导读]]
- [[03-项目/高昌举升机-IOT/02-技术栈]]
- [[03-项目/高昌举升机-IOT/04-系统与代码架构]]
- [[03-项目/高昌举升机-IOT/05-核心业务链路]]
- [[03-项目/高昌举升机-IOT/06-FreeRTOS任务与启动流程]]
- [[03-项目/高昌举升机-IOT/09-TAS-DTU、UART与MQTT协议]]
- [[03-项目/高昌举升机-IOT/11-硬件、构建、烧录与调试]]
- [[05-工作/高昌-举升机/GcCarLifts 仓库重构方案与目录设计]]

外部仓库：<https://github.com/GcCarLifts/Gc_Iot_Li>
