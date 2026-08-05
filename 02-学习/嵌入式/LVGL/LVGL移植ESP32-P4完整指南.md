---
tags: [embedded, lvgl, esp32-p4, porting, gui, chinese-font]
created: 2026-05-11
updated: 2026-05-11
---

# LVGL v9 移植 ESP32-P4 完整指南

## 副标题：从PC模拟器到MIPI DSI真机 — 含中文完整适配

---

## 1. 核心概念

### 1.1 LVGL 移植的三个关键接口

```
┌──────────────────────────────────────────────┐
│              LVGL 核心 (纯C, 平台无关)        │
├──────────────────────────────────────────────┤
│  接口1: Display Driver (lv_display_t)        │
│         └── flush_cb → 将像素发给你的屏幕    │
│  接口2: Input Device (lv_indev_t)            │
│         └── read_cb → 从你的输入设备读数据   │
│  接口3: Tick (lv_tick_inc)                   │
│         └── 周期性调用, 告诉LVGL时间流逝     │
├──────────────────────────────────────────────┤
│         你的平台代码 (需实现)                  │
└──────────────────────────────────────────────┘
```

### 1.2 移植的本质

LVGL移植 = 实现3个接口 + 配置lv_conf.h

```
PC模拟器 (SDL2):                    ESP32-P4:
lv_sdl_window_create()  → 窗口      lv_display_create() + flush_cb → MIPI DSI
lv_sdl_mouse_create()   → 鼠标      lv_indev_create() + read_cb    → GT911 I2C
lv_tick_inc(5) 循环     → tick      FreeRTOS task → lv_tick_inc(1)
```

### 1.3 本项目的移植策略

使用 **esp_lv_adapter** 中间件（Espressif官方），而非手写裸接口：

```
手写裸接口:                   使用esp_lv_adapter:
需要理解LVGL内部细节          只需配置结构体
代码量 ~200行                 代码量 ~30行
容易出错（线程安全等）        已验证的生产级代码
适合学习原理                  适合工程开发
本项目使用 ✓
```

---

## 2. 章节详解：移植步骤

### 2.1 步骤1：环境准备

```
ESP-IDF v5.3+ 已安装
工具链: riscv32-esp-elf (ESP-IDF自带)
CMake 3.16+
```

**关键组件** (managed_components/):

| 组件 | 作用 |
|------|------|
| `lvgl__lvgl` | LVGL v9 核心库 |
| `espressif__esp_lvgl_adapter` | LVGL适配中间件 |
| `espressif__esp_lcd_ek79007` | EK79007 驱动IC |
| `espressif__esp_lcd_touch_gt911` | GT911 触摸IC |
| `espressif__esp32_p4_function_ev_board_noglib` | 开发板BSP |

### 2.2 步骤2：配置 sdkconfig (LVGL相关)

```
# menuconfig 关键设置

Component config → LVGL configuration:
  [*] LVGL library version 9
  Color depth → 16 (RGB565)
  Memory size (bytes) → (65536)
  Default font → Montserrat 14
  [*] Enable Montserrat 12
  [*] Enable Montserrat 14
  [*] Enable Montserrat 16
  [*] Enable Montserrat 20
  [*] Enable Montserrat 24
  [*] Enable Montserrat 26
  [*] Enable Tiny TTF font engine   ← 中文支持关键!
```

### 2.3 步骤3：编写 lvgl_adapter_init.c

```c
// lvgl_adapter_init.c (精简版核心逻辑)

lv_display_t *lvgl_adapter_init(const bsp_display_cfg_t *cfg)
{
    // === 第1步: 初始化显示硬件 (BSP层) ===
    bsp_lcd_handles_t handles = { 0 };
    bsp_display_new_with_handles(&cfg->hw_cfg, &handles);
    // 内部: DSI PHY → DSI Bus → Panel IO → Panel Device

    // === 第2步: 初始化 LVGL 核心 + 创建 LVGL Task ===
    esp_lv_adapter_init(&ESP_LV_ADAPTER_DEFAULT_CONFIG());
    // 内部: lv_init() + 创建 FreeRTOS task 运行 lv_timer_handler()

    // === 第3步: 注册显示设备 ===
    esp_lv_adapter_display_config_t disp_cfg =
        ESP_LV_ADAPTER_DISPLAY_MIPI_DEFAULT_CONFIG(
            handles.panel, handles.io,
            BSP_LCD_H_RES, BSP_LCD_V_RES,
            ESP_LV_ADAPTER_ROTATE_0);
    disp_cfg.profile.buffer_height = 20;
    lv_display_t *disp = esp_lv_adapter_register_display(&disp_cfg);

    // === 第4步: 注册触摸输入 ===
    esp_lcd_touch_handle_t touch = NULL;
    bsp_touch_new(NULL, &touch);
    esp_lv_adapter_register_touch(
        &ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(disp, touch));

    // === 第5步: 启动 LVGL ===
    esp_lv_adapter_start();
    return disp;
}
```

### 2.4 步骤4：编写 main.c (含 SPIFFS 挂载)

```c
#include "esp_spiffs.h"

static void mount_spiffs(void)
{
    esp_vfs_spiffs_conf_t conf = {
        .base_path = "/spiffs",
        .partition_label = "storage",
        .max_files = 5,
        .format_if_mount_failed = true,
    };
    esp_err_t err = esp_vfs_spiffs_register(&conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "SPIFFS mount failed: %d", err);
        return;
    }
}

void app_main(void)
{
    mount_spiffs();  // ← 字体加载前必须挂载

    lv_display_t *disp = lvgl_adapter_init(&cfg);
    bsp_display_backlight_on();

    esp_lv_adapter_lock(-1);
    ui_app_init();    // ← 内部调用 ui_font_init() 加载中文字体
    lv_timer_create(ui_poll_cb, 5, NULL);
    esp_lv_adapter_unlock();
}
```

### 2.5 步骤5：移植 UI 代码

**UI代码的移植性**：

| 代码类型 | PC → ESP32 | 需要改动 |
|----------|:---:|------|
| lv_obj_create / lv_btn_create | 100%兼容 | 无 |
| lv_obj_set_style_* | 100%兼容 | 无 |
| lv_label_set_text (UTF-8中文) | 100%兼容 | 需中文字体 |
| lv_chart_create / lv_timer_create | 100%兼容 | 无 |
| 文件操作 (fopen/fread) | 需SPIFFS | 改路径为 `/spiffs/` |
| time() / localtime() | 兼容 | ESP32支持time.h |

**PORTING CHECKLIST**：

```c
// 1. include路径: "lvgl/lvgl.h" → "lvgl.h"
//    (ESP-IDF组件系统直接使用顶层include)

// 2. 颜色格式: RGB888 → RGB565 (lv_color_hex()自动处理)

// 3. 字体可用性: 检查sdkconfig启用了哪些Montserrat字号
//    不可用字号需映射到已启用的最大字号(26)
```

### 2.6 步骤6：CMakeLists.txt 集成

**顶层 CMakeLists.txt**:

```cmake
project(lvgl_demo_v9)
spiffs_create_partition_image(storage spiffs_data FLASH_IN_PROJECT)
```

**main/CMakeLists.txt**:

```cmake
file(GLOB_RECURSE UI_SOURCES
    "ui/core/*.c" "ui/pages/*.c" "ui/widgets/*.c"
    "ui/fonts/*.c" "ui/model/*.c" "ui/services/*.c"
)

idf_component_register(
    SRCS main.c lvgl_adapter_init.c ${UI_SOURCES}
    INCLUDE_DIRS . ui ui/core ui/pages ui/widgets
                  ui/fonts ui/model ui/services
)
```

---

## 3. 中文字体完整适配 (重点)

### 3.1 为什么 Montserrat 不能显示中文

```
LVGL渲染文字的流程:
lv_label_set_text(label, "温度")  
    │
    ▼ 遍历每个UTF-8字符
查找 '温' 的 glyph → 在 Montserrat 字体中查找
    │
    ▼ 未找到!
显示 □ (方块/tofu)
```

**根本原因**: Montserrat 是西文字体，只包含拉丁字符的 glyph (字形)。
中文字符有数万个，不可能全部打包进 Bitmap 字体。

### 3.2 方案选型

| 方案 | 原理 | 内存 | 性能 | 灵活度 |
|------|------|:---:|:---:|:---:|
| **Tiny TTF + SPIFFS** ✅ | TTF存flash，运行时渲染 | 10MB PSRAM | 中 | 任意中文 |
| binfont 预渲染 | 选中文字→C数组，编译进固件 | ~200KB | 高 | 固定字符集 |
| freetype | 完整FreeType引擎 | 大 | 低 | 任意中文 |

**选择 Tiny TTF 的理由**:
- ESP32-P4 有 16MB PSRAM，10MB 不是问题
- 支持任意中文字符，不需要预选
- LVGL 内置，无需额外组件
- FontAwesome 图标字体同理

### 3.3 Flash 分区规划

```
ESP32-P4 16MB Flash 布局:
┌──────────────────────────────────────────────────┐
│ Offset    │ Size   │ Name      │ 用途             │
├───────────┼────────┼───────────┼──────────────────┤
│ 0x8000    │        │ 分区表    │ partition table  │
│ 0x9000    │ 24KB   │ nvs       │ 系统配置          │
│ 0xF000    │ 4KB    │ phy_init  │ PHY初始化数据     │
│ 0x10000   │ 3MB    │ factory   │ 固件 (~836KB)    │
│ 0x310000  │ 12MB   │ storage   │ SPIFFS (字体)    │
└───────────┴────────┴───────────┴──────────────────┘
```

**计算关键点**:
- `factory` 分区从 `0x10000` (64KB对齐) 开始，3MB 足够
- `storage` 分区从 `0x310000` (=49×64KB, 对齐) 开始
- SPIFFS 分区大小必须是 **64KB (块大小) 的整数倍**: `12M = 12×1024×1024 = 192×64KB` ✓
- 总使用: 3MB + 12MB + ~100KB ≈ 15.1MB < 16MB ✓

### 3.4 SPIFFS 文件系统配置

**分区表** (`partitions.csv`):
```csv
# Name,   Type, SubType, Offset,  Size
nvs,      data, nvs,     0x9000,  0x6000,
phy_init, data, phy,     0xf000,  0x1000,
factory,  app,  factory, 0x10000, 3M,
storage,  data, spiffs,  ,        12M,
```

**sdkconfig 关键配置**:
```ini
CONFIG_LV_USE_TINY_TTF=y     # 启用Tiny TTF渲染引擎
CONFIG_SPIFFS_PAGE_SIZE=256  # SPIFFS页大小
CONFIG_SPIFFS_OBJ_NAME_LEN=32
CONFIG_SPIFFS_USE_MAGIC=y    # 魔数校验
CONFIG_SPIFFS_USE_MAGIC_LENGTH=y
CONFIG_SPIFFS_META_LENGTH=4
```

### 3.5 字体文件部署

```
项目根目录/
├── spiffs_data/              ← CMake 自动打包为 SPIFFS 镜像
│   ├── NotoSansSC.ttf        ← 思源黑体 (10MB, 完整CJK)
│   └── fa-solid-900.ttf      ← FontAwesome 图标 (420KB)
├── partitions.csv
└── CMakeLists.txt            ← spiffs_create_partition_image(...)
```

**编译时**:
```
spiffsgen.py 0xc00000 spiffs_data/ storage.bin
    │              │            │
    │              │            └── 输出: SPIFFS 镜像
    │              └── 输入: 字体文件目录
    └── 分区大小: 12MB
```

**烧录时**: `storage.bin` 随固件一起写入 flash 的 `storage` 分区。

### 3.6 ui_font.c 双路径实现

```c
// 核心设计: #if LV_USE_TINY_TTF 双路径编译
//   启用Tiny TTF → 从SPIFFS加载TTF渲染中文
//   未启用      → 回退到内置Montserrat (中文显示方块)

#if LV_USE_TINY_TTF

/* TTF数据必须常驻内存 — lv_tiny_ttf_create_data 持有数据指针 */
static void *s_cn_ttf_data = NULL;  // 10MB in PSRAM
static void *s_fa_ttf_data = NULL;  // 420KB in PSRAM

static void *load_ttf_file(const char *path, size_t *out_size)
{
    // 使用标准 fopen 从 SPIFFS(VFS) 读取
    FILE *f = fopen(path, "rb");      // "/spiffs/NotoSansSC.ttf"
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    void *data = lv_malloc(len);      // ← PSRAM 分配 (lv_malloc→系统malloc)
    fread(data, 1, len, f);
    fclose(f);
    *out_size = len;
    return data;
}

void ui_font_init(void)
{
    // 1. 加载中文字体 → 生成5个字号
    s_cn_ttf_data = load_ttf_file("/spiffs/NotoSansSC.ttf", &s_cn_ttf_size);
    if (s_cn_ttf_data) {
        s_cn_12 = lv_tiny_ttf_create_data(s_cn_ttf_data, s_cn_ttf_size, 12);
        s_cn_14 = lv_tiny_ttf_create_data(s_cn_ttf_data, s_cn_ttf_size, 14);
        s_cn_16 = lv_tiny_ttf_create_data(s_cn_ttf_data, s_cn_ttf_size, 16);
        s_cn_20 = lv_tiny_ttf_create_data(s_cn_ttf_data, s_cn_ttf_size, 20);
        s_cn_24 = lv_tiny_ttf_create_data(s_cn_ttf_data, s_cn_ttf_size, 24);
    }

    // 2. 加载FontAwesome图标字体
    s_fa_ttf_data = load_ttf_file("/spiffs/fa-solid-900.ttf", &fa_size);
    if (s_fa_ttf_data) {
        s_fa_icon = lv_tiny_ttf_create_data(s_fa_ttf_data, fa_size, 20);
    }
}

const lv_font_t *ui_font_cn(uint8_t size)
{
    // 优先返回TTF渲染字体，失败时回退到Montserrat
    if (s_cn_14) {  // 如果中文TTF加载成功
        switch (nearest_cn_size(size)) {
            case 12: return s_cn_12;
            case 14: return s_cn_14;
            case 20: return s_cn_20;
            case 24: return s_cn_24;
            default: return s_cn_24;
        }
    }
    // 回退到内置字体（中文会显示方块，但至少不崩溃）
    return UI_FONT_24;
}

#else
// 未启用Tiny TTF时，ui_font_cn 返回内置 Montserrat
const lv_font_t *ui_font_cn(uint8_t size) { return UI_FONT_24; }
#endif
```

### 3.7 中文显示的完整数据流

```
┌─────────────────────────────────────────────────────────────┐
│  编译时                                                      │
│  ┌─────────────┐    spiffsgen.py     ┌──────────────┐       │
│  │ spiffs_data/ │ ──────────────────→ │ storage.bin  │       │
│  │ *.ttf        │   打包为SPIFFS镜像   │ (12MB)       │       │
│  └─────────────┘                      └──────┬───────┘       │
│                                              │ flash写入      │
├──────────────────────────────────────────────┼───────────────┤
│  运行时                                      ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               ESP32-P4 Flash (16MB)                  │    │
│  │  ┌──────────┐  ┌──────────────────────────────────┐ │    │
│  │  │ factory  │  │          storage (SPIFFS)         │ │    │
│  │  │ (固件)   │  │  NotoSansSC.ttf │ fa-solid.ttf   │ │    │
│  │  └──────────┘  └────────┬─────────────────────────┘ │    │
│  └──────────────────────────┼───────────────────────────┘    │
│                             │                                │
│                  esp_vfs_spiffs_register("/spiffs")          │
│                             │                                │
│                    ┌────────▼────────┐                       │
│                    │   VFS 层        │                       │
│                    │ /spiffs/*.ttf   │                       │
│                    └────────┬────────┘                       │
│                             │                                │
│                      fopen("/spiffs/NotoSansSC.ttf")         │
│                             │                                │
│                    ┌────────▼────────┐                       │
│                    │  PSRAM (16MB)   │                       │
│                    │  TTF数据 ~10MB  │ ← lv_malloc 分配      │
│                    └────────┬────────┘                       │
│                             │                                │
│              lv_tiny_ttf_create_data(data, size, 12)         │
│              lv_tiny_ttf_create_data(data, size, 14)         │
│              ... (同一份数据生成5个字号)                      │
│                             │                                │
│                    ┌────────▼────────┐                       │
│                    │  渲染流程        │                       │
│                    │  lv_label ("温度")                      │
│                    │    → ui_i18n_font()                     │
│                    │      → ui_font_cn(14)                   │
│                    │        → s_cn_14 (lv_font_t*)           │
│                    │          → lv_tiny_ttf 渲染 温/度 字形   │
│                    │            → flush_cb → MIPI DSI → LCD  │
│                    └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.8 编译过程中踩过的坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `lv_font_montserrat_36' undeclared` | sdkconfig只启用了Montserrat 12-26，36未启用 | 将UI_FONT_36/48映射到26 |
| `control reaches end of non-void function` | 编译器无法分析 switch 覆盖所有路径 | 确保 switch 有 default 分支 |
| `image size should be a multiple of block size` | SPIFFS分区大小(12000000)不是64KB的倍数 | 改用 `12M` (12×1024×1024) |
| `#error "Invalid drive letter"` | `LV_USE_FS_STDIO=y` 需要配置驱动字母 | 关闭 FS_STDIO，直接用 fopen+VFS |
| SPIFFS 分区溢出 | 13M > flash剩余空间 | 改为12M (3M factory + 12M storage = 15M) |
| `lv_malloc(10MB)` 失败 | LVGL内存池默认只有64KB | `CONFIG_LV_USE_CLIB_MALLOC=y` 使LVGL使用系统malloc(含PSRAM) |

### 3.9 lv_tiny_ttf_create_data 的内存语义

```
lv_tiny_ttf_create_data(void *data, size_t data_size, lv_coord_t font_size)

关键约束:
1. data 指针指向的 TTF 二进制数据必须常驻内存
2. 多个字号可以共享同一份 TTF 数据
3. data 不能释放! 渲染时仍需读取
4. 用 static 变量持有数据指针

错误示范:
  void *ttf = lv_malloc(10MB);
  lv_font_t *f = lv_tiny_ttf_create_data(ttf, size, 12);
  lv_free(ttf);  // ← 错误! f 渲染时会访问已释放内存

正确示范:
  static void *ttf = lv_malloc(10MB);  // static 常驻
  lv_font_t *f12 = lv_tiny_ttf_create_data(ttf, size, 12);
  lv_font_t *f14 = lv_tiny_ttf_create_data(ttf, size, 14);
  // ttf 不释放，随程序生命周期存在
```

---

## 4. PC模拟器 vs ESP32真机 架构对比

### 4.1 对比表

```
┌──────────────────────┬─────────────────────┬──────────────────────┐
│       层次           │   PC 模拟器 (SDL2)   │   ESP32-P4 真机      │
├──────────────────────┼─────────────────────┼──────────────────────┤
│  UI 应用层           │ ui_app.c (相同代码)  │ ui_app.c (相同代码)  │
│  LVGL 核心           │ lvgl v9              │ lvgl v9              │
│  显示驱动             │ lv_sdl_window 创建   │ esp_lv_adapter +    │
│                      │ SDL2 渲染窗口        │ MIPI DSI flush_cb   │
│  输入驱动             │ SDL Mouse/键盘       │ GT911 I2C 触摸      │
│  中文字体             │ TTF fopen 本地文件   │ TTF fopen SPIFFS    │
│  颜色                 │ RGB888 (32-bit)      │ RGB565 (16-bit)     │
│  内存                 │ 系统堆 (GB级)        │ PSRAM 16MB          │
│  构建系统             │ CMake + MinGW        │ ESP-IDF + CMake     │
│  tick                 │ usleep(5000) 循环    │ FreeRTOS task       │
└──────────────────────┴─────────────────────┴──────────────────────┘
```

### 4.2 数据流对比

```
PC SDL2:
lv_timer_handler() → flush_cb → SDL_RenderCopy → GPU → 显示器
       ↑                        (SDL 纹理)
    usleep(5ms)

ESP32-P4:
lv_timer_handler() → flush_cb → esp_lcd_panel_draw_bitmap() → MIPI DSI → EK79007 → LCD
       ↑                              (DMA传输)
    vTaskDelay(1ms)
```

---

## 5. 常见问题与解决

### 5.1 屏幕不显示

```
排查清单:
[ ] DSI PHY 初始化成功? (检查 bsp_display_new 返回值)
[ ] 背光开启? (bsp_display_backlight_on)
[ ] flush_cb 被调用? (加 ESP_LOGI 日志)
[ ] DSI Lane速率正确? (1000 Mbps for EK79007)
```

### 5.2 触摸不响应

```
排查清单:
[ ] I2C 总线正常? (GPIO8/9)
[ ] GT911 地址正确? (0x5D 或 0xBA)
[ ] 触摸中断引脚? (GPIO20)
[ ] lv_indev 创建成功?
```

### 5.3 中文显示方块

```
排查顺序:
[ ] SPIFFS 挂载成功? 看串口日志 "SPIFFS mounted: xxx KB"
[ ] LV_USE_TINY_TTF=y 在 sdkconfig 中?
[ ] TTF 文件存在? 检查 spiffs_data/ 目录
[ ] ui_font_init 日志 "Chinese TTF loaded OK"?
[ ] lv_malloc 成功? PSRAM 可用?
[ ] ui_i18n_font() 返回的是 TTF 字体还是 Montserrat 回退?
```

### 5.4 画面撕裂/闪烁

```
解决方案:
1. 增大 buffer_height (20 → 40 → 全屏)
2. 使用双缓冲
3. 与 TE 信号同步
```

---

## 6. 完整示例：Smart Garden UI移植

### 6.1 移植后ESP32项目完整结构

```
lvgl_esp_p4/
├── CMakeLists.txt               ← 顶层: SPIFFS镜像创建
├── partitions.csv                ← 分区表: 3M app + 12M SPIFFS
├── sdkconfig                     ← LVGL + Tiny TTF + SPIFFS
├── sdkconfig.defaults            ← 可复现的默认配置
├── spiffs_data/                  ← SPIFFS 源文件目录
│   ├── NotoSansSC.ttf            ← 思源黑体 (10MB)
│   └── fa-solid-900.ttf          ← FontAwesome (420KB)
├── main/
│   ├── main.c                    ← SPIFFS挂载 + UI初始化
│   ├── lvgl_adapter_init.c       ← MIPI DSI + 触摸适配
│   ├── CMakeLists.txt            ← 组件注册
│   └── ui/                       ← 移植的Smart Garden UI
│       ├── ui.h                  ← 总入口头文件
│       ├── core/
│       │   ├── ui_app.c/h        ← 应用主控 (页面切换)
│       │   ├── ui_events.c/h     ← 事件发布/订阅
│       │   └── ui_styles.c/h     ← 颜色/样式/组件工厂
│       ├── pages/
│       │   ├── ui_page_data.c/h  ← 传感器数据页
│       │   ├── ui_page_ctrl.c/h  ← 设备控制页
│       │   └── ui_page_set.c/h   ← 设置页
│       ├── widgets/
│       │   ├── ui_header.c/h     ← 顶部状态栏
│       │   └── ui_tabbar.c/h     ← 底部导航栏
│       ├── fonts/
│       │   ├── ui_font.c/h       ← 字体管理 (TTF/回退)
│       ├── model/
│       │   └── garden_model.c/h  ← 花园数据模型
│       └── services/
│           ├── ui_i18n.c/h       ← 中英文国际化
│           └── ui_icons.h        ← FontAwesome 图标定义
└── managed_components/           ← ESP-IDF组件
```

### 6.2 移植修改清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| SDL_main.c → main.c | **重写** | 移除SDL，加入SPIFFS挂载+lvgl_adapter_init |
| ui_app.h | **路径修改** | `"lvgl/lvgl.h"` → `"lvgl.h"` |
| ui_app.c | **路径修改** | 同上 |
| ui_styles.h | **路径修改** | 同上 |
| ui_font.h | **路径+宏修改** | 36/48映射到26 (可用字号) |
| ui_font.c | **重写** | 双路径: TTF加载 + Montserrat回退 |
| ui_i18n.c | **字号修正** | montserrat_36 → montserrat_26 |
| ui_header.c/tabbar.c/pages | **路径修改** | 仅include路径 |
| CMakeLists.txt (root) | **新增** | spiffs_create_partition_image |
| CMakeLists.txt (main) | **重写** | ESP-IDF组件格式 |
| partitions.csv | **重写** | 调整为3M+12M布局 |
| sdkconfig | **新增项** | LV_USE_TINY_TTF=y |

### 6.3 未修改的文件 (纯LVGL API, 100%跨平台)

```
ui/core/ui_events.c     ← 事件系统
ui/core/ui_styles.c     ← 样式工厂函数
ui/pages/ui_page_data.c ← 数据页 (图表+传感器卡片)
ui/pages/ui_page_ctrl.c ← 控制页 (场景+开关)
ui/pages/ui_page_set.c  ← 设置页 (iOS风格列表)
ui/widgets/ui_header.c  ← 顶部栏
ui/widgets/ui_tabbar.c  ← 底部导航
ui/model/garden_model.c ← 花园数据模拟
ui/services/ui_i18n.c   ← 中英文国际化
```

---

## 7. 附录：速查表

### 7.1 LVGL v9 关键 API

```c
// 显示
lv_display_t *disp = lv_display_create(1024, 600);
lv_display_set_flush_cb(disp, my_flush_cb);
lv_display_set_buffers(disp, buf1, buf2, size, LV_DISPLAY_RENDER_MODE_PARTIAL);

// 输入
lv_indev_t *indev = lv_indev_create();
lv_indev_set_type(indev, LV_INDEV_TYPE_POINTER);

// 字体 (Tiny TTF)
lv_font_t *f = lv_tiny_ttf_create_data(ttf_data, data_size, font_size);

// 线程安全
esp_lv_adapter_lock(-1);
// ... LVGL操作 ...
esp_lv_adapter_unlock();
```

### 7.2 内存估算 (1024×600, RGB565, 含中文)

| 项目 | 大小 | 说明 |
|------|------|------|
| 单缓冲 (20行) | ~40KB | 1024×20×2 |
| LVGL内存池 | ~64KB | lv_conf配置 |
| Montserrat 字体 (6个) | ~300KB | built-in bitmap |
| **NotoSansSC TTF数据** | **~10MB** | **PSRAM** |
| FontAwesome TTF数据 | ~420KB | PSRAM |
| UI对象开销 | ~50KB | 取决于复杂度 |
| FreeRTOS + IDF | ~1MB | 系统开销 |
| **总计** | **~12MB** | 16MB PSRAM 足够 |

### 7.3 调试命令

```bash
# 编译
idf.py build

# 烧录 (包含SPIFFS)
idf.py -p COM3 flash

# 查看串口日志 (验证字体加载)
idf.py -p COM3 monitor

# 一键
idf.py -p COM3 build flash monitor
```

### 7.4 关键配置速查

```ini
# sdkconfig.defaults 新增项
CONFIG_LV_USE_TINY_TTF=y         # Tiny TTF 引擎
CONFIG_LV_USE_CLIB_MALLOC=y      # lv_malloc → 系统malloc (含PSRAM)
CONFIG_SPIRAM=y                  # 启用PSRAM
CONFIG_SPIRAM_SPEED_250M=y       # PSRAM 250MHz
```

---

*创建时间: 2026-05-11*
*更新时间: 2026-05-11*
*移植来源: lvgl_sim (PC SDL2) → lvgl_esp_p4 (ESP32-P4 MIPI DSI)*
