# ESP32 内存管理与分区系统

## 概述
ESP32系列芯片有三种存储介质，各有不同的用途和访问方式。本文档基于xiaozhi-for-p4项目实践整理。

---

## 1. 三种存储介质对比

| 存储类型 | 物理位置 | 速度 | 用途 | 典型大小 |
|---------|---------|------|------|---------|
| **Flash** | 外部SPI芯片 | 慢(需缓存) | 固件代码、常量、文件系统 | 4-16MB |
| **PSRAM** | 外部SPI芯片 | 中(80-200MHz) | 大块数据、模型、堆扩展 | 2-8MB |
| **SRAM** | 芯片内部 | 快(零延迟) | 栈、关键变量、TCM | 320KB-512KB |

---

## 2. 内存地址空间布局

### ESP32-P4 内存映射
```
TCM (紧耦合内存): 0x30100000, 8KB     ← 最快，放关键代码
SRAM Low:         0x4FF00000, ~180KB  ← 主要工作RAM
SRAM High:        0x4FF40000, 384KB   ← 额外RAM

PSRAM 指令区:     0x48000020          ← 代码可从PSRAM执行(XIP)
PSRAM 数据区:     0x48000020          ← 常量数据映射
```

### Flash地址空间图(16MB示例)
```
0x000000 ┌─────────────────┐
         │ bootloader       │  (ESP-IDF内置,不占分区)
0x008000 ├─────────────────┤
         │ 分区表           │  (用户定义的.csv文件)
0x009000 ├─────────────────┤
         │ nvs (16KB)       │  ← WiFi密码、设备配置
0x00D000 ├─────────────────┤
         │ phy_init (4KB)   │  ← 射频校准数据
0x00F000 ├─────────────────┤
         │ (保留)           │
0x020000 ├─────────────────┤
         │                  │
         │ app (12.5MB)     │  ← 固件主体
         │                  │
         │ ├─ .text (代码)  │
         │ ├─ .rodata       │  ← 只读数据(可含AI模型)
         │ ├─ .data          │
         │ └─ .bss           │
0xCA0000 ├─────────────────┤
         │ assets (3MB)     │  ← 字体、主题、唤醒词
0xFA0000 ├─────────────────┤
         │ face_db (256KB)  │  ← 人脸特征数据
0xFE0000 ├─────────────────┤
         │ (未使用)         │
0x1000000 └─────────────────┘  (16MB结束)
```

---

## 3. 分区表详解

### 分区表文件格式
```csv
# Name,   Type, SubType, Offset,  Size,     作用
nvs,      data, nvs,     0x9000,   0x4000,   ← 键值存储
phy_init, data, phy,     0xf000,   0x1000,   ← PHY初始化
app,      app,  factory, 0x20000,  0xC80000, ← 固件
assets,   data, spiffs,  ,         0x300000, ← 资源文件
face_db,  data, spiffs,  ,         0x40000,  ← 人脸数据
```

### 分区类型说明
- **app**: 应用程序固件
- **data**: 数据存储
  - `nvs`: 非易失性存储(键值对)
  - `phy`: PHY初始化数据
  - `spiffs`: SPI Flash文件系统
  - `ota`: OTA升级数据

### 常用分区表配置
| 配置 | 适用场景 | 特点 |
|-----|---------|------|
| single_app | 单固件 | 简单，无OTA |
| two_ota | 双OTA分区 | 支持回滚 |
| custom | 自定义 | 灵活，按需分配 |

---

## 4. ESP-IDF启动流程与分区加载

### 启动时序
```
1. ROM Bootloader
   └─ 从Flash 0x8000读取分区表
   └─ 解析每个分区的offset/size
   └─ 建立分区索引表

2. Second Stage Bootloader
   └─ 加载app分区固件
   └─ 初始化PSRAM(如果配置)
   └─ 将.rodata拷贝到PSRAM(如果配置)
   └─ 建立Flash缓存(MMU)

3. 跳转到app_main()
   └─ 执行用户代码
```

### 关键配置项
```c
// sdkconfig 中的PSRAM配置：
CONFIG_SPIRAM=y                     // 启用PSRAM
CONFIG_SPIRAM_SPEED_200M=y          // 200MHz高速模式
CONFIG_SPIRAM_XIP_FROM_PSRAM=y      // 允许从PSRAM执行代码
CONFIG_SPIRAM_FETCH_INSTRUCTIONS=y  // 指令放PSRAM
CONFIG_SPIRAM_RODATA=y              // 只读数据放PSRAM
```

---

## 5. 内存分配机制

### 自动分配策略
```c
// malloc()决策逻辑：
if (size < 4KB) {
    return 内部SRAM;  // 快，适合小数据
} else {
    return PSRAM;     // 大，适合模型/图像
}
```

### 显式控制方法
```c
#include <esp_heap_caps.h>

// 分配到内部SRAM（音频缓冲、网络包）
void* fast_buf = heap_caps_malloc(4096, MALLOC_CAP_INTERNAL);

// 分配到PSRAM（大模型、图像数据）
void* big_buf = heap_caps_malloc(1024*1024, MALLOC_CAP_SPIRAM);

// 分配可DMA访问的内存（某些外设需要）
void* dma_buf = heap_caps_malloc(4096, MALLOC_CAP_DMA);
```

### 关键配置参数
```c
CONFIG_SPIRAM_MALLOC_ALWAYSINTERNAL=4096    // <4KB走内部SRAM
CONFIG_SPIRAM_MALLOC_RESERVE_INTERNAL=65536 // 保留64KB给关键路径
```

---

## 6. 分区访问API

### 查找分区
```c
#include <esp_partition.h>

const esp_partition_t* partition = esp_partition_find_first(
    ESP_PARTITION_TYPE_DATA,          // 类型
    ESP_PARTITION_SUBTYPE_ANY,        // 子类型
    "assets"                          // 标签名
);
```

### 内存映射访问(零拷贝)
```c
#include <spi_flash_mmap.h>

const void* map_ptr;
spi_flash_mmap_handle_t map_handle;

esp_partition_mmap(
    partition_,                       // 分区对象
    offset,                           // 分区内偏移
    size,                             // 映射大小
    SPI_FLASH_MMAP_DATA,             // 数据访问模式
    &map_ptr,                        // 返回的内存地址
    &map_handle                      // 映射句柄
);

// 直接读取，无需拷贝
const char* data = (const char*)map_ptr;
```

### 分区读写
```c
// 读取分区
esp_partition_read(partition, offset, buffer, size);

// 写入分区(需先擦除)
esp_partition_erase_range(partition, offset, size);
esp_partition_write(partition, offset, buffer, size);
```

---

## 7. 固件大小管理

### 查看固件大小
```bash
# 查看分区表
idf.py partition-table

# 查看固件各段大小
idf.py size-components

# 查看详细内存分布
idf.py size-files
```

### 固件大小与Flash关系
```
固件大小 ≤ app分区大小
         ↓
如果固件 > 分区 → 编译报错
如果固件 < 分区 → 浪费空间(但可接受)
```

### 减小固件体积的方法
1. **优化代码**：移除未使用的函数
2. **压缩资源**：使用SPIFFS/LittleFS存储资源
3. **外部存储**：大模型放SD卡或网络下载
4. **分区调整**：合理分配app和assets比例

---

## 8. AI模型存储策略

### 三种存储方式对比
| 方式 | 优点 | 缺点 | 适用场景 |
|-----|------|------|---------|
| **FLASH_RODATA** | 零拷贝、简单 | 增大固件、占Flash | 小模型(<2MB) |
| **FLASH_PARTITION** | 独立分区、可单独更新 | 需要分区管理 | 中等模型 |
| **SD_CARD** | 不占Flash | 加载慢、需文件系统 | 大模型 |

### 配置示例
```c
// sdkconfig.defaults.esp32p4：
CONFIG_HUMAN_FACE_DETECT_MODEL_IN_FLASH_RODATA=y  // 模型嵌入固件
CONFIG_HUMAN_FACE_FEAT_MODEL_IN_FLASH_RODATA=y    // 特征模型嵌入固件
```

---

## 9. 实践要点

### 关键记忆点
1. **Flash**：存储固件和数据，掉电不丢失
2. **PSRAM**：运行时大内存，掉电丢失
3. **SRAM**：快速内部RAM，掉电丢失
4. **分区表**：Flash的"地址簿"，定义各区域用途
5. **malloc**：自动选择内存区域
6. **mmap**：零拷贝访问Flash数据

### 常见问题
- **固件太大**：检查.rodata是否包含大模型
- **内存不足**：检查malloc是否正确使用PSRAM
- **启动失败**：检查分区表偏移是否正确
- **OTA失败**：检查ota_0/ota_1分区大小

---

## 10. 相关文件索引

### 项目配置文件
- `sdkconfig` - 主配置文件
- `sdkconfig.defaults.esp32p4` - ESP32-P4默认配置
- `partitions/v2/16m.csv` - 分区表定义

### 代码文件
- `main/ota.cc` - OTA升级实现
- `main/assets.cc` - 资源分区访问
- `main/main.cc` - 主程序入口

### 链接脚本
- `build_ninja/esp-idf/esp_system/ld/memory.ld` - 内存布局定义
- `build_ninja/esp-idf/esp_system/ld/sections.ld` - 段定义

---

## 学习日期
2026-06-24

## 项目背景
xiaozhi-for-p4 - ESP32-P4智能家居语音助手
