# 远程无线RTT调试与嵌入式工具全景

> 创建日期：2026-06-28
> 数据来源：GitHub仓库、SEGGER官网、中文社区(CSDN/知乎/电子发烧友)、国际社区(Reddit/Hackaday/EEVblog)
> 目标：完整的远程无线RTT方案 + 全部嵌入式工具清单

---

# 第一部分：远程无线RTT调试方案（全部）

## 一、现成可用方案（GitHub项目）

### 1.1 ESP系列无线调试探针（最热门）

| 项目 | Stars | 芯片 | 功能 | 链接 |
|------|-------|------|------|------|
| **wireless-esp8266-dap** | 653 | ESP8266/ESP32/C3/S3 | 无线CMSIS-DAP，SWD/JTAG over WiFi，可选40MHz SPI加速 | github.com/windowsair/wireless-esp8266-dap |
| **blackmagic-espidf** | 296 | ESP8266 | Black Magic Probe固件跑在ESP上，WiFi telnet UART + HTTP xterm.js终端 | github.com/walmis/blackmagic-espidf |
| **cmsis_dap_tcp_esp32** | 24 | ESP32 | CMSIS-DAP over TCP/IP，ESP32连WiFi，OpenOCD通过cmsis-dap-tcp后端连接 | github.com/bkuschak/cmsis_dap_tcp_esp32 |
| **ESP32-Debugger** | 23 | ESP32-S3 | DAPLink调试器，有线/无线调试，单/双端无线下载，虚拟串口 | github.com/MGod-monkey/ESP32-Debugger |
| **esp32jtag_firmware** | 9 | ESP32-S3 | 一体化硬件调试工具：JTAG/SWD(BlackMagic+CMSIS-DAP)、16通道逻辑分析仪、FPGA编程器、XVC服务器、信号发生器。WiFi Web UI(HTTPS)、OTA更新、WebSocket UART桥接 | github.com/EZ32Inc/esp32jtag_firmware |
| **CMSIS-DAP-Wireless** | 34 | ESP | 无线CMSIS-DAP实现 | github.com/K-O-Carnivist/CMSIS-DAP-Wireless |
| **wireless-cmsis-dap** | 11 | ESP | 低成本无线ARM仿真器，含硬件设计 | github.com/sxp123/wireless-cmsis-dap |
| **OverWire** | 1 | ESP32 | WiFi刷写/调试STM32，企业级就绪 | github.com/rmingon/OverWire |
| **wifi_debugger** | 4 | ESP32 | WiFi调试器项目 | github.com/crowzK/wifi_debugger |
| **openocd_remote_swd_esp32** | 2 | ESP32 | ESP32实现OpenOCD remote_swd协议（已弃用但架构参考价值高） | github.com/bkuschak/openocd_remote_swd_esp32 |

### 1.2 RTT桥接/代理/转发（网络传输）

| 项目 | Stars | 语言 | 功能 | 链接 |
|------|-------|------|------|------|
| **rtt-bridge** | 3 | Rust | 桌面GUI桥接器，通过DAPLink/CMSIS-DAP读取RTT，支持TCP/UDP转发，CLI模式可用于AI/自动化 | github.com/mimicccccc/rtt-bridge |
| **trace-recorder-rtt-proxy** | 1 | Rust | 通过网络代理调试探针操作和TraceRecorder RTT数据 | github.com/auxoncorp/trace-recorder-rtt-proxy |
| **rtt-proxy** | 0 | TypeScript | RTT代理 | github.com/charlie-niekirk/rtt-proxy |
| **RTT2UART** | 69 | Python | Segger RTT转UART串口，无需J-Link Viewer即可输出RTT | github.com/tianxiaoMCU/RTT2UART |

### 1.3 商业/工业无线调试探针

| 项目 | Stars | 类型 | 功能 | 链接 |
|------|-------|------|------|------|
| **WchLinkW** | 30 | 2.4GHz无线 | WCH RISC-V和ARM SWD/JTAG双调试器，有线/无线 | github.com/WeActStudio/WeActStudio.WchLinkW |
| **ctxLink** | 多仓库 | WiFi(ESP32) | 无线调试探针项目，ESP32 WiFi模块，有3D打印外壳 | github.com/sidprice/ctxLink_cases |
| **J-Link WiFi** | 官方 | WiFi(802.11 b/g/n) | SEGGER官方无线调试探针，1MB/s下载，15MHz接口 | segger.com/products/debug-probes/j-link/models/j-link-wifi/ |

### 1.4 RTT查看器/客户端工具

| 项目 | Stars | 语言 | 支持探针 | 链接 |
|------|-------|------|----------|------|
| **RTTView** | 284 | Python | J-Link + DAPLink | github.com/XIVN1987/RTTView |
| **strtt** | 72 | C | ST-Link | github.com/phryniszak/strtt |
| **segger-rtt-viewer** | 50 | Python | J-Link | github.com/bojanpotocnik/segger-rtt-viewer |
| **rtt_stlink** | 36 | C | ST-Link | github.com/trlsmax/rtt_stlink |
| **pyrtt-viewer** | 27 | Python | nRF J-Link | github.com/thomasstenersen/pyrtt-viewer |
| **RTT-Console** | 20 | Python | J-Link | github.com/dudulung/RTT-Console |
| **RTTView-CMSIS-DAP** | 13 | Python | CMSIS-DAP/DAPLink | github.com/lixuyongmt/RTTView |
| **j-link-rtt-viewer-pyqt** | 4 | Python(PySide6) | J-Link，Fluent风格GUI + MCU内存读写 + 固件烧录 | github.com/MisakaMikoto128/j-link-rtt-viewer-pyqt |
| **jlink-rtt-client** | 1 | Rust | J-Link | github.com/9names/jlink-rtt-client |
| **rtt-console** | 0 | Rust | 双向RTT控制台 | github.com/dimpolo/rtt-console |

### 1.5 AI/MCP集成调试

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **embedded-debugger-mcp** | 115 | MCP服务器，probe-rs调试ARM Cortex-M和RISC-V，支持Claude/Codex | github.com/Adancurusul/embedded-debugger-mcp |
| **Mklink-AI-Probe** | 18 | MKLink硬件探针 + AI代理(Claude/OpenAI)自然语言驱动固件烧录、波形可视化、内存检查、故障诊断 | github.com/su5176/Mklink-AI-Probe |
| **flashprobe-mcp** | 1 | MCP服务器，probe-rs/espflash烧录+RTT监控，支持STM32/nRF/RP2350/ESP | github.com/okhsunrog/flashprobe-mcp |
| **brontes-probe-mcp** | 0 | 嵌入式调试探针MCP服务器：编程、暂停、内存读取、ITM/SWO流式传输(stdio/socket/TCP) | github.com/cms-pm/brontes-probe-mcp |
| **embedded-agent-bridge** | 9 | AI代理桥接嵌入式调试(串口、GDB、OpenOCD) | github.com/shanemmattner/embedded-agent-bridge |

---

## 二、远程RTT调试方案汇总（按实现难度排序）

### 方案A：J-Link Remote Server（零改造，5分钟搞定）

```
[目标MCU] --SWD--> [J-Link] --USB--> [PC-A: JLinkRemoteServer]
                                           │
                                      局域网/VPN/Tailscale
                                           │
                                    [PC-B: Ozone/SystemView/RTT Viewer]
```

- 成本：已有J-Link则免费
- 优点：官方支持，零改造
- 缺点：近端需要一台PC
- 跨网络：用Tailscale/WireGuard VPN

### 方案B：wireless-esp8266-dap（最热门开源方案，⭐653）

```
[目标MCU] --SWD--> [ESP32-S3: wireless-esp8266-dap]
                         │
                    WiFi (CMSIS-DAP over TCP)
                         │
                  [PC: OpenOCD + GDB/SystemView]
```

- 成本：ESP32-S3开发板 ~¥30
- 优点：社区活跃，开箱即用，支持SWD/JTAG
- 缺点：不直接支持RTT查看（需配合OpenOCD）
- 适合：需要无线烧录+调试的场景

### 方案C：blackmagic-espidf（WiFi telnet + Web终端，⭐296）

```
[目标MCU] --SWD--> [ESP8266: blackmagic-espidf]
                         │
                    WiFi (Telnet + HTTP)
                         │
              [PC: telnet连接 / 浏览器xterm.js终端]
```

- 成本：ESP8266开发板 ~¥10
- 优点：自带Web终端，telnet UART输出
- 缺点：ESP8266性能有限
- 适合：最轻量的无线调试方案

### 方案D：rtt-bridge（专用RTT网络转发，⭐3）

```
[目标MCU] --SWD--> [DAPLink/CMSIS-DAP] --USB--> [PC-A: rtt-bridge]
                                                       │
                                                  TCP/UDP转发
                                                       │
                                                [PC-B: RTT终端]
```

- 成本：DAPLink ~¥10-30
- 优点：专门为RTT设计，支持TCP/UDP转发
- 缺点：项目较小，需要近端PC
- 适合：已有DAPLink，需要远程查看RTT

### 方案E：RTT2UART + ESP32 WiFi转发（⭐69）

```
[目标MCU] --SWD--> [J-Link] --USB--> [PC: RTT2UART] --UART--> [ESP32: WiFi TCP Server]
                                                                      │
                                                                 WiFi转发
                                                                      │
                                                              [远端PC/手机: TCP客户端]
```

- 成本：已有J-Link + ESP32 ~¥30
- 优点：RTT2UART成熟，ESP32转发简单
- 缺点：需要近端PC运行RTT2UART
- 适合：不想改目标MCU代码

### 方案F：ESP32-S3一体化调试器（⭐9，功能最强）

```
[目标MCU] --SWD--> [ESP32-S3: esp32jtag_firmware]
                         │
                    WiFi (HTTPS + WebSocket)
                         │
              [浏览器: Web UI 调试终端 + 逻辑分析仪]
```

- 成本：ESP32-S3开发板 ~¥30
- 优点：JTAG/SWD + 16通道逻辑分析仪 + FPGA编程器 + XVC服务器 + 信号发生器，一体化
- 缺点：项目较新，社区较小
- 适合：想要全能工具的开发者

### 方案G：cmsis_dap_tcp_esp32（OpenOCD直连，⭐24）

```
[目标MCU] --SWD--> [ESP32: cmsis_dap_tcp_esp32]
                         │
                    WiFi (CMSIS-DAP TCP)
                         │
                  [PC: OpenOCD (cmsis-dap-tcp后端)]
```

- 成本：ESP32开发板 ~¥20
- 优点：OpenOCD原生支持，无需额外驱动
- 缺点：需要编译OpenOCD（含cmsis-dap-tcp后端）
- 适合：OpenOCD深度用户

### 方案H：J-Link WiFi（官方商业方案）

```
[目标MCU] --SWD--> [J-Link WiFi] --WiFi--> [PC: Ozone/SystemView/RTT Viewer]
```

- 成本：~$500+（约¥3500+）
- 优点：开箱即用，官方支持，1MB/s下载
- 缺点：贵
- 适合：企业/团队，预算充足

### 方案I：WCH-LinkW（国产2.4GHz无线，⭐30）

```
[目标MCU(CH32V/STM32)] --SWD--> [WCH-LinkW] --2.4GHz--> [PC: MounRiver Studio/OpenOCD]
```

- 成本：~¥50-80
- 优点：国产、便宜、2.4GHz无线
- 缺点：主要支持WCH芯片，对其他MCU支持有限
- 适合：WCH RISC-V开发

### 方案J：OpenOCD远程模式 + VPN

```
[目标MCU] --SWD--> [DAPLink/J-Link] --USB--> [远程主机: OpenOCD -s bindto 0.0.0.0]
                                                    │
                                               SSH隧道/VPN/Tailscale
                                                    │
                                             [本地PC: GDB/Ozone]
```

- 成本：已有调试探针 + 远程主机
- 优点：标准OpenOCD方案，支持所有MCU
- 缺点：WiFi延迟影响实时调试体验
- 适合：远程实验室/工厂调试

---

## 三、RTT核心实现（底层库）

| 项目 | Stars | 语言 | 用途 | 链接 |
|------|-------|------|------|------|
| **SEGGERMicro/RTT** | 210 | C | 官方RTT源码 | github.com/SEGGERMicro/RTT |
| **probe-rs/rtt-target** | 196 | Rust | Rust目标侧RTT实现 | github.com/probe-rs/rtt-target |
| **probe-rs/probe-rs-rtt** | 23 | Rust | probe-rs宿主侧RTT库 | github.com/probe-rs/probe-rs-rtt |
| **adfernandes/segger-rtt** | 39 | C | 官方RTT源码干净副本 | github.com/adfernandes/segger-rtt |
| **haydenridd/zig-rtt** | 9 | Zig | Zig语言RTT实现 | github.com/haydenridd/zig-rtt |
| **m-chichikalov/segger** | 6 | Go | TinyGo的RTT+SystemView实现 | github.com/m-chichikalov/segger |
| **SEGGERMicro/SystemView** | 103 | C | SystemView目标侧源码和RTOS补丁 | github.com/SEGGERMicro/SystemView |

---

# 第二部分：嵌入式工具全景（150+项目）

## 四、调试探针与片上调试器

### 4.1 开源调试框架

| 项目 | Stars | 语言 | 功能 | 链接 |
|------|-------|------|------|------|
| **probe-rs** | 2805 | Rust | ARM/RISC-V调试工具集，原生RTT，支持ST-Link/CMSIS-DAP/J-Link | github.com/probe-rs/probe-rs |
| **OpenOCD** | 2237 | C | 片上调试器，ARM/MIPS/RISC-V，GDB服务器 | github.com/openocd-org/openocd |
| **pyOCD** | 1431 | Python | ARM Cortex-M编程/调试Python库 | github.com/pyocd/pyOCD |
| **RISC-V OpenOCD** | 518 | C | RISC-V增强版OpenOCD | github.com/riscv-collab/riscv-openocd |
| **ESP32 OpenOCD** | 453 | C | ESP32 JTAG支持的OpenOCD分支 | github.com/espressif/openocd-esp32 |
| **Black Magic Probe** | 硬件131 | C | 一体化GDB服务器调试探针 | github.com/blackmagic-debug/blackmagic-hardware |
| **Black Magic Probe Book** | 161 | C | BMP完整指南和工具 | github.com/compuphase/Black-Magic-Probe-Book |

### 4.2 CMSIS-DAP固件

| 项目 | Stars | 芯片 | 功能 | 链接 |
|------|-------|------|------|------|
| **DAPLink(官方)** | 2752 | 多种 | ARM官方DAPLink固件，拖拽烧录+虚拟串口+CMSIS-DAP | github.com/ARMmbed/DAPLink |
| **CMSIS-DAP(官方)** | 132 | ARM | ARM官方CMSIS-DAP参考实现 | github.com/ARM-software/CMSIS-DAP |
| **CMSIS-DAP STM32** | 495 | STM32 | STM32移植CMSIS-DAP + CDC串口 | github.com/x893/CMSIS-DAP |
| **CMSIS-DAP SWO BluePill** | 440 | STM32F103 | BluePill上的CMSIS-DAP + SWO | github.com/RadioOperator/STM32F103C8T6_CMSIS-DAP_SWO |
| **DAPLink AT32/CH32** | 347 | AT32F425/CH32V | DAPLink移植到更便宜的MCU | github.com/XIVN1987/DAPLink |
| **free-dap** | 330 | 多种 | 免费开源CMSIS-DAP固件 | github.com/ataradov/free-dap |
| **dap42** | 234 | STM32F042/F103 | CMSIS-DAP固件 | github.com/devanlai/dap42 |
| **CH32V305 DAPLink HS** | 25 | CH32V305 | WCH-LinkE上的USB2.0高速DAPLink | github.com/prosper00/CH32V305-DAPLink-HS |
| **CMSIS-DAP JS** | 132 | TypeScript | 浏览器/Node.js CMSIS-DAP接口 | github.com/ARMmbed/dapjs |

### 4.3 WCH-Link工具链

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **wlink** | 317 | Rust开源WCH-Link命令行工具 | github.com/ch32-rs/wlink |
| **WCH-LinkE** | - | 增强版，支持CH32V/F全系列 | wch.cn |
| **WCH-LinkW** | 30 | 2.4GHz无线版 | github.com/WeActStudio/WeActStudio.WchLinkW |
| **WCH_WebLink** | 15 | ESP32编程CH32V003 | github.com/Subjective-Reality-Labs/WCH_WebLink |

### 4.4 其他调试探针

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Raspberry Pi Debug Probe** | 1185 | RP2040 CMSIS-DAP + UART | github.com/raspberrypi/debugprobe |
| **vllink_lite** | 298 | 低成本CMSIS-DAP V2调试器 | github.com/vllogic/vllink_lite |
| **J-Link OB** | 155 | ARM ICE JTAG SWD J-Link克隆 | github.com/GCY/JLINK-ARM-OB |
| **DirtyJTAG** | 614 | JTAG探针固件 | github.com/dirtyjtag/DirtyJTAG |
| **pico-dirtyJtag** | 455 | Pico上的DirtyJTAG | github.com/phdussud/pico-dirtyJtag |
| **RailLink** | 131 | J-Link v9紧凑隔离版 | github.com/Misaka0x2730/RailLink |
| **Adafruit adalink** | 123 | J-Link Commander + STLink V2的Python封装 | github.com/adafruit/Adafruit_Adalink |
| **XIAO Debug Mate** | 17 | ESP32-S3调试方案，DAPLink+UART+LED矩阵+功耗分析 | github.com/Seeed-Studio/OSHW-XIAO-Debug-Mate |

---

## 五、逻辑分析仪与信号分析

### 5.1 Sigrok生态（开源信号分析）

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **PulseView** | 758 | Sigrok GUI前端，逻辑分析仪+示波器 | github.com/sigrokproject/pulseview |
| **libsigrok** | 427 | Sigrok核心库 | github.com/sigrokproject/libsigrok |
| **libsigrokdecode** | 135 | 协议解码器库 | github.com/sigrokproject/libsigrokdecode |
| **libserialport** | 239 | 跨平台串口库 | github.com/sigrokproject/libserialport |
| **sigrok-cli** | 85 | Sigrok命令行 | github.com/sigrokproject/sigrok-cli |
| **sigrok-pico** | 1053 | 树莓派Pico做逻辑分析仪/示波器 | github.com/pico-coder/sigrok-pico |
| **esp32_sigrok** | 198 | ESP32做SUMP逻辑分析仪 | github.com/Ebiroll/esp32_sigrok |
| **SmuView** | 153 | Sigrok GUI用于电源/电子负载/万用表 | github.com/knarfS/smuview |

### 5.2 其他逻辑分析仪

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **DSLogic** | 国产 | 1GHz采样率，开源软件DSView | dreamsourcelab.com |
| **Saleae Logic** | 行业标杆 | 最好用的软件，协议解码丰富 | saleae.com |
| **RP2040逻辑分析仪** | 95 | Pico逻辑分析仪，CSV导出 | github.com/gamblor21/rp2040-logic-analyzer |
| **Arduino逻辑分析仪** | 127 | Arduino SUMP协议逻辑分析仪 | github.com/pschatzmann/logic-analyzer |
| **Web逻辑分析仪** | 31 | ESP8266/ESP32 Web逻辑分析仪 | github.com/hepter/web-logic-analyzer |
| **SUMP2** | 101 | FPGA开源逻辑分析仪 | github.com/blackmesalabs/sump2 |
| **Bitmagic** | 93 | 开源逻辑分析仪和数据采集 | github.com/esden/bitmagic |
| **OpenLogicBit** | 173 | FPGA逻辑分析仪门阵列 | github.com/ultraembedded/openlogicbit |

---

## 六、协议分析工具

| 项目 | Stars | 协议 | 链接 |
|------|-------|------|------|
| **Wireshark** | 免费 | 网络/串口/蓝牙/USB | wireshark.org |
| **NFC Laboratory** | 546 | NFC信号分析(SDR) | github.com/josevcm/nfc-laboratory |
| **CuiShark** | 258 | 终端协议分析器 | github.com/cuishark/cuishark |
| **Saleae SPI Flash** | 44 | SPI Flash协议分析 | github.com/kasjer/saleae_spiflash |
| **USBCx** | 33 | USB PD协议分析 | github.com/tejv/USBCx |
| **I3C Saleae Analyzer** | 29 | I3C协议分析 | github.com/xyphro/XyphroLabs-I3C-Saleae-Protocol-Analyzer |
| **DRPD** | 21 | USB-PD协议分析(开源，支持EPR) | github.com/T76-org/drpd |
| **LPC Analyzer** | 19 | LPC协议分析(Kingst) | github.com/Ryzee119/LPCAnalyzer |
| **Bus Pirate** | 开源 | SPI/I2C/UART通用分析 | buspirate.com |

---

## 七、Flash编程器与固件烧录

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **esptool** | 6395 | ESP全系列串口烧录工具 | github.com/espressif/esptool |
| **flashrom** | 1141 | 通用Flash ROM编程器 | github.com/flashrom/flashrom |
| **espflash** | 727 | Rust版ESP烧录器 | github.com/esp-rs/espflash |
| **NodeMCU PyFlasher** | 1600 | NodeMCU GUI烧录器 | github.com/marcelstoer/nodemcu-pyflasher |
| **esptool-js** | 508 | 浏览器版ESP烧录器(WebSerial) | github.com/espressif/esptool-js |
| **ESP32-MPY-Jama** | 498 | ESP32 MicroPython UI工具 | github.com/jczic/ESP32-MPY-Jama |
| **CH341A工具** | 213 | CH341A EEPROM/FLASH编程器 | github.com/tomek-o/CH341A-tool |
| **CH341A软件集合** | 531 | CH341A全平台软件 | github.com/YTEC-info/CH341A-Softwares |
| **SPI Flash编程器** | 110 | Arduino SPI Flash编程器 | github.com/nfd/spi-flash-programmer |
| **ufprog** | 113 | 通用Flash编程器 | github.com/hackpascal/ufprog |
| **MCUboot** | 1940 | 32位MCU安全启动 | github.com/mcu-tools/mcuboot |
| **nihao** | 13 | Rust版Flash编程器+片上调试器 | github.com/luojia65/nihao |

---

## 八、嵌入式测试框架

| 项目 | Stars | 语言 | 功能 | 链接 |
|------|-------|------|------|------|
| **Unity** | 5278 | C | 嵌入式C单元测试框架(#1) | github.com/ThrowTheSwitch/Unity |
| **Ceedling** | 823 | Ruby | C项目单元测试+构建系统 | github.com/ThrowTheSwitch/Ceedling |
| **pytest-embedded** | 142 | Python | Espressif官方pytest插件 | github.com/espressif/pytest-embedded |
| **Embedded-Test** | 84 | C | 超简单嵌入式测试框架 | github.com/QuantumLeaps/Embedded-Test |
| **awesome-embedded-testing** | 8 | - | 嵌入式测试工具和资源集合 | github.com/onmcu/awesome-embedded-testing |
| **parrot** | 8 | Python | Robot Framework嵌入式测试自动化 | github.com/zilogic-systems/parrot |
| **EDTT** | 20 | Python | 嵌入式设备测试工具 | github.com/EDTTool/EDTT |

---

## 九、嵌入式日志与追踪

| 项目 | Stars | 语言 | 功能 | 链接 |
|------|-------|------|------|------|
| **defmt** | 1189 | Rust | 延迟格式化日志，RTT传输，RLE压缩 | github.com/knurling-rs/defmt |
| **defmt-serial** | 40 | Rust | defmt通过串口输出 | github.com/gauteh/defmt-serial |
| **defmt-bbq** | 20 | Rust | bbqueue传输defmt | github.com/jamesmunns/defmt-bbq |
| **Microprofile** | 1586 | C | 嵌入式性能分析器 | github.com/jonasmr/microprofile |
| **Logscope** | 29 | TypeScript | VS Code嵌入式日志查看器(Zephyr) | github.com/NovelBits/logscope |
| **embedded-log** | 27 | C | 小巧嵌入式日志库 | github.com/to9/embedded-log |
| **Rustmeter** | 32 | Rust | Perfetto UI嵌入式性能追踪 | github.com/Christopher-06/rustmeter |
| **ptm2human** | 57 | C | ARM PTM/ETM v4 trace解码器 | github.com/hwangcc23/ptm2human |

---

## 十、RTOS与RTOS调试

### 10.1 主流RTOS

| 项目 | Stars | 特色 | 链接 |
|------|-------|------|------|
| **Zephyr** | 15741 | 可扩展、优化、安全，多架构 | github.com/zephyrproject-rtos/zephyr |
| **LVGL** | 23923 | 嵌入式图形库(不是RTOS但常配合) | github.com/lvgl/lvgl |
| **MicroPython** | 21838 | MC上的Python | github.com/micropython/micropython |
| **RT-Thread** | 12069 | 国产IoT RTOS | github.com/RT-Thread/rt-thread |
| **Embassy** | 9464 | Rust异步嵌入式框架 | github.com/embassy-rs/embassy |
| **NuttX** | 3924 | Apache成熟RTOS | github.com/apache/nuttx |
| **ESPHome** | 11311 | ESP32/8266配置化控制 | github.com/esphome/esphome |
| **PlatformIO** | 9316 | 跨平台嵌入式IDE | github.com/platformio/platformio-core |

### 10.2 RTOS可视化/调试

| 工具 | RTOS支持 | 功能 | 价格 |
|------|----------|------|------|
| **SEGGER SystemView V4** | FreeRTOS/embOS/ThreadX/Zephyr/NuttX/uC/OS | 事件时间线、CPU负载、堆监控、DataPlot、多核 | 非商业免费 |
| **Percepio Tracealyzer** | FreeRTOS/Zephyr/ThreadX/PX5/SafeRTOS/VxWorks/Linux | 最强可视化、100+视图、连续流/快照 | 商业付费 |
| **TraceX** | Eclipse ThreadX | ThreadX官方工具 | 免费 |
| **RTOS_trace** | 通用 | RTOS trace库和文档 | github.com/RTEdbg/RTOS_trace |

---

## 十一、嵌入式仿真与模拟

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Renode** | 2603 | 开源嵌入式系统仿真框架，RISC-V/ARM/x86，CI/CD集成 | github.com/renode/renode |
| **Renode Verilator** | 26 | Renode与Verilator集成 | github.com/antmicro/renode-verilator-integration |
| **Renode GitHub Action** | 21 | GitHub Actions运行Renode测试 | github.com/antmicro/renode-test-action |

---

## 十二、静态分析

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Cppcheck** | 6662 | C/C++静态分析 | github.com/cppcheck-opensource/cppcheck |
| **CodeChecker** | 2579 | 分析器工具+缺陷数据库+查看器 | github.com/Ericsson/codechecker |
| **clang-power-tools** | 543 | VS clang-tidy集成 | github.com/Caphyon/clang-power-tools |
| **MISRA C/C++ checker** | 181 | MISRA合规检查 | github.com/rettichschnidi/clang-tidy-misra |
| **naivesystems/analyze** | 201 | 代码安全和合规静态分析 | github.com/naivesystems/analyze |
| **clangd-tidy** | 158 | 更快的clang-tidy替代 | github.com/lljbash/clangd-tidy |
| **cpp-linter-action** | 142 | GitHub Actions C/C++ linting | github.com/cpp-linter/cpp-linter-action |

---

## 十三、文档生成

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Doxygen** | 6511 | 官方文档生成器 | github.com/doxygen/doxygen |
| **doxygen-awesome-css** | 1386 | Doxygen自定义CSS主题 | github.com/jothepro/doxygen-awesome-css |
| **DoxygenToolkit.vim** | 1254 | Vim Doxygen插件 | github.com/Austinnnn123/DoxygenToolkit.vim |
| **Standardese** | 970 | 下一代Doxygen(C++) | github.com/standardese/standardese |
| **Breathe** | 814 | Sphinx/Doxygen桥接 | github.com/breathe-doc/breathe |
| **hdoc** | 339 | 现代C++文档工具 | github.com/hdoc/hdoc |
| **doxdocgen** | 287 | VS Code Doxygen扩展 | github.com/cschlosser/doxdocgen |

---

## 十四、硬件黑客多工具

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **ESP32-Bit-Pirate** | 4095 | ESP32硬件黑客工具，Web CLI，支持所有协议 | github.com/geo-tp/ESP32-Bit-Pirate |
| **HydraFW** | 440 | HydraBus固件，硬件黑客多工具 | github.com/hydrabus/hydrafw |
| **HydraBus** | 342 | HydraBus开源多工具 | github.com/hydrabus/hydrabus |
| **JTAGenum** | 799 | 扫描引脚JTAG功能 | github.com/cyphunk/JTAGenum |
| **JTAGulator** | 791 | 辅助发现片上调试接口 | github.com/grandideastudio/jtagulator |
| **wifi_jtag** | 174 | ESP8266做无线JTAG编程器 | github.com/emard/wifi_jtag |
| **JTAGWhisperer** | 157 | Arduino JTAG线缆替代 | github.com/sowbug/JTAGWhisperer |
| **ch55x_jtag** | 145 | CH55x USB转JTAG桥 | github.com/diodep/ch55x_jtag |
| **CH347** | 213 | CH347 480Mbps USB转JTAG/I2C/SPI/UART | github.com/WCHSoftGroup/ch347 |
| **esp-usb-bridge** | 389 | ESP32-S2/S3 USB转UART/JTAG桥 | github.com/espressif/esp-usb-bridge |
| **jtag2updi** | 373 | Arduino UPDI编程器 | github.com/ElTangas/jtag2updi |
| **jtag-boundary-scanner** | 175 | JTAG边界扫描调试和测试 | github.com/viveris/jtag-boundary-scanner |
| **xvc-pico** | 489 | Pico做Xilinx虚拟线缆 | github.com/kholia/xvc-pico |

---

## 十五、嵌入式基准测试

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **CoreMark** | 1209 | EEMBC行业标准CPU/MCU基准 | github.com/eembc/coremark |

---

## 十六、嵌入式内存分析

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Nesiac** | 32 | 嵌入式内存使用分析器 | github.com/Eekle/Nesiac |
| **BuddyMemoryMallocFree** | 11 | 深度嵌入式内存管理 | github.com/BACnetEd/BuddyMemoryMallocFree |
| **tinyalloc** | 1 | 嵌入式堆分配器 | github.com/brais-sg/tinyalloc |

---

## 十七、嵌入式CI/CD

| 项目 | Stars | 功能 | 链接 |
|------|-------|------|------|
| **Renode GitHub Action** | 21 | GitHub Actions运行Renode仿真测试 | github.com/antmicro/renode-test-action |
| **embedded-ci-docker** | 2 | Docker嵌入式驱动测试 | github.com/Sensirion/embedded-ci-docker |
| **ci-cd-class-1** | 31 | 嵌入式CI/CD教程(STM32CubeIDE+Git+Jenkins) | github.com/g-schro/ci-cd-class-1 |

---

## 十八、Awesome列表与资源

| 项目 | Stars | 内容 | 链接 |
|------|-------|------|------|
| **Awesome-Embedded** | 8775 | 嵌入式编程精选资源 | github.com/nhivp/Awesome-Embedded |
| **Embedded-Engineering-Roadmap** | 12073 | 嵌入式工程师学习路线图 | github.com/m3y54m/Embedded-Engineering-Roadmap |
| **awesome-embedded-rust** | 7948 | 嵌入式Rust精选资源 | github.com/rust-embedded/awesome-embedded-rust |
| **embedded-resources** | 670 | 嵌入式模板、文档、源码 | github.com/embeddedartistry/embedded-resources |

---

# 第三部分：国产/中文社区工具

## 十九、国产调试工具

### 19.1 H7-TOOL（安富莱/Armfly）⭐推荐

- 基于STM32H750，4.3寸触摸屏独立运行
- 功能：串口助手(多路UART) + 内置示波器 + DAPLink调试器(SWD/JTAG) + CAN/CANFD分析 + RS485调试 + GPIO测量控制 + I2C/SPI调试 + 离线编程器 + 频率计/PWM输出
- 开源/半开源设计
- 价格：~500-800元
- 社区：电子发烧友、阿莫论坛活跃

### 19.2 ESP-Prog（乐鑫官方）

- FTDI FT2232HL芯片
- JTAG调试(OpenOCD) + UART串口下载
- 支持ESP32/S2/S3/C3
- 价格：~30-50元

### 19.3 WCH-Link系列

| 型号 | 价格 | 特色 |
|------|------|------|
| WCH-Link | ~15元 | 基础版 |
| WCH-LinkE | ~20元 | 增强版(推荐) |
| WCH-LinkW | ~50-80元 | 2.4GHz无线版 |

---

## 二十、国产串口/调试助手

| 工具 | 特色 | 平台 | 价格 |
|------|------|------|------|
| **Vofa+** | 实时数据可视化(波形)，JustFloat/FireWater/RawData协议，PID调参神器 | Win/Linux/Mac | 免费 |
| **SSCOM** | 经典串口工具，HEX收发，自定义快捷按钮 | Windows | 免费 |
| **XCOM(正点原子)** | 现代界面串口工具 | Windows | 免费 |
| **野火调试助手** | 串口+CAN+网络调试 | Windows | 免费 |
| **MobaXterm** | 终端+SSH+串口一体化 | Windows | 免费/付费 |
| **Luatools(合宙)** | 合宙模块一体化开发调试 | Windows | 免费 |

---

## 二十一、国产IDE与开发平台

| 工具 | 特色 | 价格 |
|------|------|------|
| **RT-Thread Studio** | 一站式开发，图形化配置，包管理，模拟调试(QEMU/DAP) | 免费 |
| **MounRiver Studio** | WCH RISC-V官方IDE | 免费 |
| **VS Code + Cortex-Debug** | OpenOCD/J-Link/pyOCD后端，SVD寄存器查看，RTT终端 | 免费 |
| **PlatformIO** | 跨平台IDE，支持ArduinoOTA WiFi无线烧录 | 免费 |

---

## 二十二、国产逻辑分析仪/测试仪器

| 工具 | 特色 | 价格区间 |
|------|------|----------|
| **DSLogic(梦源)** | 1GHz采样率，开源软件DSView，Sigrok兼容 | ¥200-500 |
| **Kingst LA** | 国产品牌，Sigrok兼容 | ¥100-300 |
| **致远电子LA系列** | 专业级，协议分析能力强 | ¥500+ |
| **逻辑狗LogicDog** | 国产性价比 | ~¥50 |

---

## 二十三、合宙LuatOS生态工具

| 工具 | 功能 |
|------|------|
| **Luatools** | 固件下载、日志打印、单设备烧录 |
| **LuatOS模拟器** | 无硬件本地调试 |
| **LuatIO** | 可视化IO功能配置 |
| **量产烧录工具** | 循环烧录 |
| **Web TCP/UDP/MQTT/FTP/HTTP测试工具** | 网络通信测试 |
| **FOTA** | 远程OTA固件升级 |
| **iRTU** | 免开发IoT透传软件 |
| **Trae AI** | AI开发和技术支持集成 |

---

# 第四部分：工具采购与选型指南

## 二十四、按预算推荐

### 零预算（免费方案）

| 工具 | 用途 |
|------|------|
| probe-rs + DAPLink(自制) | 调试+烧录 |
| SystemView Friendly License | RTOS可视化 |
| Vofa+ | 串口数据可视化 |
| VS Code + Cortex-Debug | IDE |
| PulseView + 自制逻辑分析仪(Pico) | 信号分析 |
| Cppcheck + clang-tidy | 静态分析 |
| Unity + Ceedling | 单元测试 |
| Renode | 仿真测试 |

### 入门预算（~¥200）

| 工具 | 价格 | 用途 |
|------|------|------|
| DAPLink(正点原子/野火) | ¥30-60 | 调试+烧录 |
| ESP32-S3开发板 | ¥30 | 无线RTT桥接 |
| DSLogic基础版 | ¥100-200 | 逻辑分析 |

### 进阶预算（~¥1000）

| 工具 | 价格 | 用途 |
|------|------|------|
| J-Link BASE/EDU | ¥200-600 | 专业调试+RTT |
| H7-TOOL | ¥500-800 | 多功能调试工具 |
| DSLogic Plus | ¥200-500 | 逻辑分析 |

### 专业预算（~¥5000+）

| 工具 | 价格 | 用途 |
|------|------|------|
| J-Link WiFi | ¥3500+ | 无线调试 |
| Saleae Logic 8 | ¥3500 | 专业逻辑分析 |
| Nordic PPK2 | ¥700 | 功耗分析 |
| Percepio Tracealyzer | 商业报价 | 最强RTOS可视化 |

---

*最后更新：2026-06-28*
*数据来源：GitHub 150+仓库、SEGGER官网、中文社区、国际社区*
