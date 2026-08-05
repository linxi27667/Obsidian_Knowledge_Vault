---
tags:
  - 项目管理
  - GitHub
  - 技术资料
  - GcCarLifts
created: 2026-05-15
updated: 2026-05-15
---

# GcCarLifts GitHub 组织 — 仓库目录详解

> **组织地址**: https://github.com/GcCarLifts
> **组织类型**: Organization（组织）
> **创建时间**: 2025-10-09
> **仓库总数**: 11 个（全部为私有仓库）
> **对应公司**: GC Technology Limited（高昌科技）— gctechnology.com

---

## 总览：11 个仓库分类

| 类别         | 仓库数 | 仓库名                                                |
| ---------- | --- | -------------------------------------------------- |
| 🔧 嵌入式固件   | 2   | GcMultiLinkLift、lifter_display_promgram            |
| 🌐 Web/软件  | 3   | gaochang-web、web-gaochang-bak、demo-repository      |
| 📚 技术文档/标准 | 3   | Auto-Equip-Standards、GcPatents、allCircuitBoardData |
| 🏭 工程/制造   | 1   | NC-program                                         |
| 📋 行政/政策   | 1   | gaochang-green-factory-gz                          |
| 🎨 设计资源    | 1   | Adobe_illustrate_model                             |

---

## 📦 仓库 1：GcMultiLinkLift — 多立柱液压举升机控制固件

**仓库描述**: 多立柱液压举升机主控固件，支持 STM32F4 系列微控制器，实现 RS232 转 WiFi 通信、主从机协同控制、OTA 远程升级等功能。适用于 5.5 吨、8.0 吨及 TPFI 系列多柱举升机。

**技术栈**: C/C++、STM32 HAL 库、ESP32、Keil MDK-ARM
**最近更新**: 2026-04-01

### 目录结构

```
GcMultiLinkLift/
├── ESP32_Proj/                          # ESP32 通信模块项目
│   └── download_ESP32/                  # ESP32 固件烧录工具配置
│       ├── flash_download_tool/         # 乐鑫官方烧录工具
│       │   ├── configure/esp32c5/       # ESP32-C5 烧录参数配置
│       │   │   ├── security.conf        #   安全启动配置
│       │   │   ├── spi_download.conf    #   SPI 下载配置
│       │   │   └── utility.conf         #   工具通用配置
│       │   ├── dl_temp/                 # 烧录临时文件目录
│       │   ├── tools/python/            # 便携版 Python + esptool 工具链
│       │   └── logs/                    # 烧录操作日志
│       ├── monitor.bat                  # 烧录状态监控脚本（批处理）
│       └── monitor.ps1                  # 烧录状态监控脚本（PowerShell）
│
├── newBoard_OTA_APP/                    # 新版主板 OTA 远程升级应用程序
│
├── stm407_lifter_newBoard_5.5MC/        # STM32F407 新版主板 5.5吨多柱举升机固件
├── stm407_lifter_newBoard_8.0MC/        # STM32F407 新版主板 8.0吨多柱举升机固件
├── stm407_lifter_newBoard_8.0MC_ESP32/  # STM32F407 新版主板 8.0吨 + ESP32 WiFi通信版
├── stm407_lifter_newBoard_TPFI/         # STM32F407 新版主板 TPFI型号固件
│
├── stm407_lifter_reconsitution_5.5MC/   # STM32F407 改造版主板 5.5吨固件
├── stm407_lifter_reconsitution_8.0MC/   # STM32F407 改造版主板 8.0吨固件
├── stm407_lifter_reconsitution_TPFI/    # STM32F407 改造版主板 TPFI型号固件
├── stm407_lifter_reconsitution_clear_w25qxx/  # STM32F407 清除 W25QXX Flash 存储专用固件
│
├── 251220.胞胎式举升机控制程序及方案阶段性任务.xlsx  # 阶段性开发任务追踪表
├── GcMultiLinkLift.code-workspace       # VS Code 工作区配置文件
├── LEARNING_PATH_14D.md                 # 14天固件开发学习路径文档
├── NEWBOARD_OTA_APP_IOT_PLAN.md         # 新版主板 OTA + 物联网功能规划文档
└── README.md                            # 项目说明文档
```

> **每个固件子目录内部结构**（Keil MDK-ARM 标准工程）:
> - `Core/` — 启动文件、系统时钟配置
> - `Drivers/` — STM32 HAL 标准外设库、CMSIS 核心文件
> - `Inc/` — 用户头文件
> - `Src/` — 用户源文件
> - `MDK-ARM/` — Keil 工程文件（.uvprojx）

---

## 📦 仓库 2：lifter_display_promgram — 举升机显示屏程序

**仓库描述**: 举升机 HMI（人机界面）显示屏控制程序，支持多种屏幕型号（8.0MC、TPFI）及多品牌定制（高昌、Duka、LAUNCH、意大利版等），包含无电池版、无重量显示版、多语言版等多种配置。

**技术栈**: HMI 显示屏工程（DPJ/PKGX 格式）
**最近更新**: 2026-03-30

### 目录结构

按 **屏幕型号 + 品牌/语言** 分为 14 个配置文件夹：

| 文件夹名 | 说明 |
|---|---|
| `0_8.0MC_屏幕_直接复制重量显示文本即可` | 8.0MC 屏幕 — 直接复制重量显示文本版本 |
| `1_8.0MC_屏幕_无电池 - 无logo` | 8.0MC 无电池供电版，无品牌标识 |
| `1_8.0MC_屏幕_无重量 - 无logo` | 8.0MC 无重量显示功能版，无品牌标识 |
| `1_8.0MC_屏幕_无重量 - 无logo-意大利` | 意大利市场定制版，无重量显示、无品牌标识 |
| `1_TPFI_屏幕_无重量 - 无logo` | TPFI 型号，无重量显示、无品牌标识 |
| `2_8.0MC_屏幕_无电池 - 高昌` | 8.0MC 无电池版，高昌品牌标识 |
| `2_8.0MC_屏幕_无重量 - 高昌` | 8.0MC 无重量版，高昌品牌标识 |
| `2_TPFI_屏幕_无重量 - 高昌` | TPFI 型号，高昌品牌标识 |
| `3_8.0MC_屏幕_无电池 - Duka` | Duka 品牌定制版（无电池） |
| `3_8.0MC_屏幕_无重量 - Duka` | Duka 品牌定制版（无重量） |
| `4_8.0MC_屏幕_无电池 - LAUNCH` | LAUNCH 品牌定制版（无电池） |
| `4_8.0MC_屏幕_无重量 - LAUNCH` | LAUNCH 品牌定制版（无重量） |
| `5_8.0MC_屏幕_无重量 - 无logo - 多语言` | 多语言通用版（支持 11 种语言） |
| `5_TPFI_屏幕_无重量 - 无logo - 多语言` | TPFI 多语言通用版 |

### 每个配置文件夹内的文件结构

```
{型号}_屏幕_{配置}/
├── HMI0/                    # HMI 人机界面工程主目录
├── image/                   # 屏幕显示图片素材
├── tar/                     # 归档/模板文件
├── temp/                    # 临时文件
├── vg/                      # 矢量图形资源
├── *.dpj                    # 显示屏工程文件
├── *.pkgx                   # 显示屏打包发布文件
├── *.bak                    # 工程备份文件
├── frw0.frp                 # 界面框架配置文件
├── PLCGEDefaultProperties.xml  # PLC 通信默认属性配置
└── EVWindows.dat~           # 窗口布局配置数据
```

> **特殊文件**: `5_8.0MC` 和 `5_TPFI` 多语言版本额外包含 `11_languages_20260119.xls`（11 种语言翻译对照表）

---

## 📦 仓库 3：gaochang-web — 高昌官网（主版本）

**仓库描述**: 高昌公司官方网站前端项目，基于 Astro 静态站点框架构建，支持多语言内容管理、响应式布局，部署于 Vercel/Netlify/Cloudflare 多平台。

**技术栈**: TypeScript、Astro、Tailwind CSS、Decap CMS
**部署平台**: Vercel / Netlify / Cloudflare Workers / Docker
**最近更新**: 2026-03-22

### 目录结构

```
gaochang-web/
├── src/                     # Astro 框架源代码（页面、组件、布局）
├── public/                  # 静态资源目录
│   ├── _headers             # HTTP 响应头配置
│   ├── images/              # 网站图片资源
│   │   ├── about/           # 公司介绍图片
│   │   │   ├── 2003-guangzhou-hq.webp        # 2003 广州总部大楼
│   │   │   ├── 2008-wuhu-GC-factory.webp     # 2008 芜湖高昌工厂
│   │   │   ├── 2014-wuhu-GS-factory.webp     # 2014 芜湖 GS 工厂
│   │   │   └── gaochang-factory-front-door.webp  # 高昌工厂正门
│   │   ├── gc-logo.webp     # 高昌品牌 Logo
│   │   ├── homePage1.webp   # 首页横幅图片
│   │   ├── honors/          # 资质荣誉图片
│   │   │   ├── zh/          # 中文版资质证书（20+ 张）
│   │   │   │   ├── ISO9001 质量管理体系认证证书
│   │   │   │   ├── 船级社交通产品认证证书
│   │   │   │   ├── EAC 认证证书
│   │   │   │   ├── CE 认证证书
│   │   │   │   ├── 科技创新小巨人企业证书
│   │   │   │   ├── 知识产权示范企业牌匾
│   │   │   │   └── ...（共 20+ 张证书）
│   │   │   └── en/          # 英文版资质证书
│   │   └── logo/
│   │       └── logo.svg     # Logo 矢量源文件
│   └── decapcms/            # Decap CMS 内容管理系统
│       ├── config.yml       # CMS 配置文件
│       └── index.html       # CMS 管理入口页面
│
├── docs/                    # 项目开发文档
│   ├── AstroWind学习路径.md
│   ├── Astro主题对比分析.md
│   ├── 内容调用链分析.md
│   ├── 首页内容调用链分析.md
│   └── plans/               # 开发计划文档
│       ├── 2026-03-18-multi-site-astro-design.md
│       └── 2026-03-18-multi-site-astro-implementation.md
│
├── scripts/                 # 构建/部署辅助脚本
├── vendor/                  # 第三方依赖库
├── nginx/
│   └── nginx.conf           # Nginx 反向代理配置
│
├── .github/workflows/
│   └── actions.yaml         # GitHub Actions 持续集成/持续部署配置
├── .logs/                   # 构建日志（5 次生产环境构建记录）
├── .vscode/                 # VS Code 编辑器配置
│   ├── astrowind/
│   │   └── config-schema.json  # AstroWind 主题配置 Schema
│   ├── extensions.json      # 推荐插件列表
│   ├── launch.json          # 调试配置
│   └── settings.json        # 工作区设置
│
├── Dockerfile               # Docker 容器镜像构建文件
├── docker-compose.yml       # Docker Compose 编排配置
├── astro.config.ts          # Astro 框架主配置
├── tailwind.config.js       # Tailwind CSS 样式配置
├── tsconfig.json            # TypeScript 编译配置
├── package.json             # Node.js 项目依赖
├── package-lock.json        # 依赖锁定文件
├── eslint.config.js         # ESLint 代码规范配置
├── .prettierrc.cjs          # Prettier 代码格式化配置
├── vercel.json              # Vercel 平台部署配置
├── netlify.toml             # Netlify 平台部署配置
├── wrangler.json            # Cloudflare Workers 部署配置
├── AGENTS.md                # AI 开发助手配置说明
├── PROJECT_MANUAL.md        # 项目开发手册
└── README.md                # 项目说明文档
```

---

## 📦 仓库 4：web-gaochang-bak — 高昌官网（旧版备份）

**仓库描述**: 高昌官网旧版本备份，结构与主版本（gaochang-web）基本一致，待确认无保留价值后删除。

**最近更新**: 2026-02-13

> ⚠️ **与主版本差异**:
> - `AstroWind学习路径.md`、`Astro主题对比分析.md` 位于根目录（主版本在 `docs/` 下）
> - 额外包含 `temp_4.0tpfi_performance.md`（4.0TPFI 性能测试临时记录）
> - 额外包含 `迁移项目到新仓库并替换bun为npm_c826bd35.plan.md`（项目迁移计划）
> - 额外包含 `.log/` 目录（构建日志）

---

## 📦 仓库 5：GcPatents — 专利资源归档

**仓库描述**: 高昌集团专利资源管理系统，按公司分类归档专利文档（PDF/Markdown），提供专利撰写工作流、技术交底书模板、PDF 转 Markdown 自动化工具，支持专利附图批量处理。

**技术栈**: Python（PDF 处理脚本）、Markdown
**最近更新**: 2026-03-10

### 目录结构

```
GcPatents/
├── 专利撰写skill及流程/              # 专利编写标准化工作流
│   ├── .cursor/                      # Cursor 编辑器项目配置
│   ├── Technical_Disclosure_Document/  # 技术交底书标准模板
│   ├── out_patent_application/       # 最终输出的专利申请文件
│   ├── 已修改图片/                   # 已处理完成的专利附图
│   ├── 待修改图片/                   # 待处理的原始专利附图
│   ├── requirements.txt              # Python 依赖包列表
│   ├── resize_patent_figures.py      # 专利附图尺寸调整脚本
│   ├── 专利申请-还需完成事项.md       # 专利申请待办事项清单
│   └── 专利编写与提交学习与执行流程.md # 专利编写全流程操作指南
│
├── 各公司专利PDF/                    # 按公司分类的专利 PDF 原件
│   ├── 中意泰达(营口)汽车保修设备有限公司/
│   ├── 苏州艾沃意特汽车设备有限公司/
│   ├── 赛埃孚汽车保修设备(太仓)有限公司/
│   └── 路特利举升机（海门）有限公司/
│
├── 各公司专利markdown/               # 专利 Markdown 格式版本（便于检索）
│   ├── 中意泰达(营口)汽车保修设备有限公司/
│   ├── 苏州艾沃意特汽车设备有限公司/
│   ├── 赛埃孚汽车保修设备(太仓)有限公司/
│   └── 路特利举升机（海门）有限公司/
│
├── 已编写的专利/                     # 已完成撰写并提交的专利
│   └── 260227专利申请_一种举升机远程监控与故障报警系统/
│       ├── 专利技术交底书.md              # 技术交底书（Markdown）
│       ├── 专利申请.高昌发明.一种举升机远程监控与故障报警系统_260302.doc  # Word 申请文件
│       ├── 专利申请_一种举升机远程监控与故障报警系统.md  # 专利申请正文
│       ├── 举升机监控与报警流程图.drawio    # 系统流程图源文件（Draw.io）
│       └── 举升机监控与报警流程图_*.jpg     # 系统流程图图片（4 张）
│
├── pdf_to_markdown.py                # PDF 专利文档转 Markdown 自动化脚本
├── README_pdf_to_markdown.md         # PDF 转换工具使用说明
└── requirements.txt                  # Python 依赖包列表
```

---

## 📦 仓库 6：Auto-Equip-Standards — 举升机材料选型与标准知识库

**仓库描述**: 举升机核心零部件（耐磨滑块、丝杆螺母等）材料选型参考资料库，汇集 ISO 国际标准、中国国家标准（GB）、机械行业标准（JB）及企业内部标准，配套采购技术规格书、供应商清单、标准获取自动化工具。

**技术栈**: Markdown、Python、Playwright（浏览器自动化）
**最近更新**: 2026-04-28

### 目录结构

```
Auto-Equip-Standards/
├── 标准库Standards/                  # 技术标准资料库
│   ├── ISO/                         # ISO 国际标准文档
│   ├── 国家标准/                     # 中国国家标准（GB）文档
│   ├── 行业标准/                     # 机械行业标准（JB）文档
│   ├── 企业标准/                     # 高昌企业内部标准
│   └── 待确认/                       # 待核实确认的标准文档
│
├── 采购文件/                         # 采购技术文档
│   ├── 01_滑块采购技术规格书.md       # 耐磨滑块采购技术规格要求
│   ├── 02_丝杆螺母采购技术规格书.md   # 丝杆螺母采购技术规格要求
│   ├── 03_供应商联系清单.md          # 合格供应商联系方式汇总
│   ├── 04_采购订单技术条款模板.md     # 采购合同标准技术条款模板
│   ├── 05_采购任务单_高昌六_陈林.md   # 具体采购任务执行单
│   ├── 06_国家标准获取指南.md        # 国家标准查询与下载操作指南
│   ├── 07_技术部近期工作安排.md       # 技术部门工作计划
│   ├── 08_企业微信消息版本.md        # 企业微信通知模板
│   ├── 09_企知道抓取方法论.md        # 企知道平台标准信息抓取方法
│   ├── 10_国标验证结果汇总表.md       # 国家标准验证结果汇总
│   ├── 11_企知道平台标准信息汇总.md   # 企知道平台标准信息整理
│   ├── 12_标准下载任务成果汇总.md     # 标准下载任务完成报告
│   └── 16_AI控制浏览器完全指令.md    # AI 自动化浏览器操作完整指令集
│
├── tools/                            # 辅助工具脚本
├── 260207.G.工程塑料在举升机的应用方案.md  # 工程塑料在举升机应用的技术方案
├── GkNote_AutoEquipStandards.md      # 知识库学习笔记
├── CLAUDE.md                         # AI 助手项目配置
├── Start-ChromeDebug.ps1             # Chrome 浏览器调试模式启动脚本
├── basedpyright-langserver.cmd       # Python 语言服务器启动脚本
├── GcAutoEquipStandard.code-workspace  # VS Code 工作区配置
├── package.json                      # Node.js 项目依赖（含 Playwright）
├── package-lock.json                 # 依赖锁定文件
├── node_modules/                     # ⚠️ Node.js 依赖包（不应提交至 Git）
├── .sisyphus/                        # Sisyphus 自动化工作记录
├── .opencode/                        # OpenCode MCP 服务配置
├── .gitattributes                    # Git 属性配置
├── .gitignore                        # Git 忽略规则
├── README.md                         # 项目说明文档
└── MERGED_FROM_GcAutoEquipStandard_files.txt  # 文件合并记录
```

---

## 📦 仓库 7：allCircuitBoardData — 所有电路板资料

**仓库描述**: 高昌举升机控制电路板完整技术资料库，按板型分类（2n20MrA、BV、SV），包含固件源码、硬件设计文件（原理图/PCB）、生产资料（BOM/装配图）及单片机数据手册。

**最近更新**: 2026-01-28

### 目录结构

```
allCircuitBoardData/
├── 01_2n20MrA/                      # 2n20MrA 型号电路板
│   └── 01_Firmware/                 # 固件源码
│       └── 6.0丝杠4圈（单感应柱改诊断模式改延时方式）-4-6T通用20231021/
│           ├── Gppw.gpj             # Gppw 工程配置文件
│           ├── Gppw.gps             # Gppw 源代码文件
│           ├── Project.inf          # 项目配置信息
│           ├── ProjectDB.mdb        # 项目数据库文件
│           ├── 1继电器举升机端口定义.doc  # 继电器端口定义文档
│           └── Resource/            # 工程资源文件
│
├── 02_BV/                           # BV 型号电路板
│   ├── 01_Firmware/                 # 固件源码
│   │   └── SLE(自动补油)CE版/       # 自动补油功能 CE 认证版固件
│   │       ├── 123.hex              # 编译输出文件（Intel HEX 格式）
│   │       ├── 123.OBJ              # 目标文件
│   │       ├── 123.LST              # 列表文件（含地址映射）
│   │       ├── 123.M51              # 内存映射文件
│   │       ├── 123.uvproj           # Keil 工程文件
│   │       └── 123.uvgui.dell       # Keil 界面配置文件
│   ├── 02_Hardware/                 # 硬件设计文件（原理图、PCB 布局）
│   └── 03_Production/               # 生产资料（BOM 清单、装配图）
│
├── 03_SV/                           # SV 型号电路板
│   ├── 01_Firmware/                 # 固件源码（结构同 BV）
│   │   └── SLE(自动补油)CE版/       # 自动补油 CE 认证版
│   ├── 02_Hardware/                 # 硬件设计文件
│   └── 03_Production/               # 生产资料
│
└── 09_Doc/                          # 技术文档
    ├── STC1110xx系列单片机器件手册.pdf  # STC 单片机数据手册
    └── 电路板文件生产可行性分析.md      # 电路板生产可行性评估报告
```

---

## 📦 仓库 8：NC-program — 数控加工程序

**仓库描述**: 高昌工厂数控机床加工程序库，按机床位置和数控系统分类管理，涵盖广州数控（GSK980/GSK988TA）、华中数控（HNC-21TD）、VMC850L 加工中心等设备，包含 500+ 个 CNC 程序文件及车床后处理配置文件。

**最近更新**: 2026-01-20

### 目录结构

```
NC-program/
├── 1楼_2号机床_广州数控GSK988TA（加工中心并排）_12工位/
│   └── *.CNC                        # 100+ 个 CNC 加工程序
│                                      # （0602.CNC、1050.CNC、GC75.CNC、GD 系列等）
│
├── 1楼_3号机床_油缸线带动力头GSK988TA_12工位/
│   └── *.CNC                        # 油缸生产线 CNC 程序（带动力头）
│
├── 1楼_VMC850L加工中心/
│   └── *.CNC                        # VMC850L 立式加工中心程序
│
├── 3楼_1号机床_广州数控GSK980_4工位/
│   └── *.CNC                        # GSK980 系统 4 工位车床程序
│
├── 3楼_2号机床_广州数控GSK980_6工位/
│   └── *.CNC                        # GSK980 系统 6 工位车床程序
│
├── 3楼_3号机床_广州数控新机型980TDC_4工位/
│   └── *.CNC                        # GSK980TDC 新机型程序
│
├── 3楼_4号机床_华中数控_4工位/
│   └── HNC-21TD/PROG/               # 华中数控系统程序目录
│
├── 3楼_5号机床_广州数控小机床_4工位/
│   └── *.CNC                        # 小型 GSK 机床程序
│
├── 3楼_6号机床_华中数控_4工位/
│   └── *.CNC                        # 华中数控系统程序
│
├── 3楼_7号机床_华中数控_6工位/
│   └── *.CNC                        # 华中数控 6 工位程序
│
├── 3楼_8号机床_华中数控_4工位/
│   └── HNC-21TD/PROG/               # 华中数控系统，OCD 系列 200+ 个程序
│                                      # （OCD5022、OCD5436、OCD60、OCD70 等）
│
├── MC/                              # 加工零件程序库（按零件名称分类）
│   ├── 45+86/
│   ├── 上支点焊接套D44 D25/
│   ├── D25 97 上车板滚轮轴/
│   ├── D12-540 下支座焊接套（有孔）D50/
│   ├── 28.5 内连杆油缸支承加强套D30/
│   ├── D48 30 子机下支座焊接轴 D40-77/
│   ├── 子机内连杆焊件D36 D25 D28/
│   └── 活塞90 D89-60/
│
└── 车床后处理循环指令（广数华中发那科等）.pst  # 车床后处理配置文件
                                                 # 支持广州数控/华中数控/发那科系统
```

---

## 📦 仓库 9：gaochang-green-factory-gz — 广州高昌绿色工厂

**仓库描述**: 高昌绿色工厂申报资料库，包含国家/省/市三级绿色工厂政策法规、申报指南、第三方服务机构报价、申报材料（按指标分类）、能碳管理平台数据等，用于 2026 年度绿色制造名单申报。

**最近更新**: 2026-05-06

### 目录结构

```
gaochang-green-factory-gz/
├── 01-政策资料和2026年申报指南/       # 政策法规与申报指南
│   ├── GB-T-2589-2020_综合能耗计算通则(OCR).pdf
│   ├── GB-T-36132-2018_绿色工厂评价通则(OCR).pdf
│   ├── GB-T-36132-2025_绿色工厂评价通则(OCR).pdf
│   ├── JB-T-14407-2023_机械行业绿色工厂评价导则(OCR).pdf
│   ├── 广州市工信局2026年度绿色制造名单推荐通知.pdf
│   ├── 穗发改规字〔2025〕3号_新能源与节能环保措施.pdf
│   ├── 附件1：广州市绿色工厂梯度培育信息登记表.docx
│   ├── 附件2：绿色制造名单培育对象汇总表.docx
│   ├── 附件3：专项资金管理系统操作流程.docx
│   ├── 附件4：2026年绿色制造推荐和自评价.docx
│   └── 附件5：绿色工厂成熟度评价方法说明.docx
│
├── 02-服务机构报价/                  # 第三方服务机构资料
│   ├── 三方机构.新玑科技提供资料/
│   │   └── 250815.新玑科技存有外部参考资料/
│   │       ├── 1国家级绿色工厂/       # 国家级绿色工厂申报资料
│   │       │   ├── 0常用资料/
│   │       │   ├── 1政策申报材料/
│   │       │   ├── 3牌匾/
│   │       │   ├── 4报告/
│   │       │   ├── 企业绿码/
│   │       │   └── 合作案例/（含双碳报告附件）
│   │       ├── 1广东省级绿色工厂/     # 广东省级绿色工厂申报资料
│   │       │   ├── 0常用资料/（含历史资料）
│   │       │   ├── 1公示名单/
│   │       │   ├── 1政策申报通知/
│   │       │   └── 1补贴政策及申领通知/
│   │       ├── 1深圳市级绿色工厂/     # 深圳市级绿色工厂申报资料
│   │       ├── 2能源管理体系/         # 能源管理体系认证
│   │       ├── 3环境管理体系/
│   │       ├── 3职业健康管理体系/     # 职业健康安全认证
│   │       ├── 3质量管理体系/         # 质量管理体系认证
│   │       ├── DG-东莞-绿色工厂/
│   │       ├── GD-惠州-绿色工厂/
│   │       ├── JS-宁波-绿色工厂/
│   │       ├── 前期项目分析、评分、报价/
│   │       ├── 参考资料/
│   │       ├── 现场审厂案例/
│   │       └── 第三方评价报告/
│   └── 三方机构.沙玛企业管理咨询有限公司/
│
├── 03-申报文稿+佐证材料-按类型/       # 按评价指标分类的申报材料
│   ├── 门槛-01-四体系证书及内审管评/
│   ├── 门槛-02-绿色制造规划与组织架构/
│   ├── 门槛-03-清洁生产与环评排污许可/
│   ├── 指标1-统计报表B204-1与B205-1/
│   ├── 指标2-温室气体排放核算报告/
│   ├── 指标3-可再生能源利用率/
│   ├── 指标4-能碳管理系统/
│   ├── 指标5-原材料节约应用/
│   ├── 指标6-取水用水与重复利用/
│   ├── 指标7-工业用水重复利用率/
│   ├── 指标8-一般工业固废与危废转移/
│   ├── 指标9-工艺设备先进性/
│   ├── 指标10-绿色低碳改造项目/
│   ├── 指标11-废水废气监测报告/
│   ├── 指标12-绿色设计/
│   ├── 指标13-产品碳足迹/
│   └── 指标15-土地证与建筑面积/
│
├── 04-绿色发展管理平台/              # 绿色发展管理平台数据
│   └── 指标计算过程表/
│
├── unpacked_docx/                    # 解包的 Word 文档临时目录
├── extract_pv.py                     # 数据提取 Python 脚本
├── _patch_docx_renewable.py          # Word 文档批量处理脚本
├── 260410-任务指派与评分要点-一行清单.md  # 任务分配与评分要点清单
├── AGENTS.md                         # AI 开发助手配置
├── CLAUDE.md                         # AI 助手项目配置
├── README.md                         # 项目说明文档
└── gaochang-green-factory-gz.code-workspace  # VS Code 工作区配置
```

---

## 📦 仓库 10：Adobe_illustrate_model — Adobe Illustrator 模型

**仓库描述**: 高昌产品目录 Illustrator 设计源文件，用于产品宣传册、展会物料等平面设计。

**最近更新**: 2026-02-08

```
Adobe_illustrate_model/
├── GC_Catelog_Model.ai              # 高昌产品目录 Illustrator 设计源文件
└── README.md                        # 项目说明文档
```

---

## 📦 仓库 11：demo-repository — 演示仓库

**仓库描述**: GitHub 官方演示模板仓库，包含基础 HTML 页面示例及 GitHub Actions 工作流配置示例。

**最近更新**: 2025-10-09

```
demo-repository/
├── .github/workflows/
│   ├── auto-assign.yml              # 自动分配 Issue/PR 工作流
│   └── proof-html.yml               # HTML 代码校验工作流
├── index.html                       # 示例 HTML 页面
├── package.json                     # Node.js 项目配置
└── README.md                        # 项目说明文档
```

---

## 📊 整理建议

### ✅ 建议保留在 GitHub（代码/技术文档类，8 个仓库）

| 仓库 | 理由 |
|---|---|
| **GcMultiLinkLift** | 嵌入式固件代码，需要版本管理和团队协作开发 |
| **lifter_display_promgram** | HMI 显示屏程序，按型号/品牌分类管理 |
| **gaochang-web** | 官网项目，含 CI/CD 自动化部署流程 |
| **Auto-Equip-Standards** | 技术标准库，Markdown 格式适合 Git 版本管理 |
| **GcPatents** | 专利文档管理，含 Python 自动化处理脚本 |
| **allCircuitBoardData** | 电路板固件源码 + 硬件设计文件 |
| **NC-program** | 数控加工程序，需要版本追踪和历史记录 |
| **Adobe_illustrate_model** | 可保留，但 .ai 文件 Git 管理意义不大 |

### ⚠️ 建议处理

| 仓库 | 建议 | 理由 |
|---|---|---|
| **web-gaochang-bak** | 🗑️ 删除 | 已标注"旧版本，备份待删除" |
| **demo-repository** | 🗑️ 删除 | GitHub 官方演示模板，无实际业务价值 |
| **Auto-Equip-Standards/node_modules/** | 📝 加入 .gitignore | Node.js 依赖包不应提交至 Git |

### 📁 建议迁移到 O 盘（行政/文档类）

| 仓库 | 理由 |
|---|---|
| **gaochang-green-factory-gz** | 全部为 PDF/Word 政策文件和政府申报表格，非代码类资料 |

---

## 🔗 快速访问链接

| 仓库 | 链接 |
|---|---|
| GcMultiLinkLift | https://github.com/GcCarLifts/GcMultiLinkLift |
| lifter_display_promgram | https://github.com/GcCarLifts/lifter_display_promgram |
| gaochang-web | https://github.com/GcCarLifts/gaochang-web |
| web-gaochang-bak | https://github.com/GcCarLifts/web-gaochang-bak |
| GcPatents | https://github.com/GcCarLifts/GcPatents |
| Auto-Equip-Standards | https://github.com/GcCarLifts/Auto-Equip-Standards |
| allCircuitBoardData | https://github.com/GcCarLifts/allCircuitBoardData |
| NC-program | https://github.com/GcCarLifts/NC-program |
| gaochang-green-factory-gz | https://github.com/GcCarLifts/gaochang-green-factory-gz |
| Adobe_illustrate_model | https://github.com/GcCarLifts/Adobe_illustrate_model |
| demo-repository | https://github.com/GcCarLifts/demo-repository |
