# ESP32 存储与 OTA 升级

> ESP32 片上 Flash、PSRAM、NVS、文件系统以及空中升级（OTA）的完整指南。

---

## 目录

- [[#1. Flash 基础]]
- [[#2. 分区表]]
- [[#3. NVS 非易失性存储]]
- [[#4. 文件系统]]
- [[#5. PSRAM 外部 RAM]]
- [[#6. OTA 基础]]
- [[#7. WiFi OTA]]
- [[#8. OTA 安全]]
- [[#9. 内存管理 API]]

---

## 1. Flash 基础

### 1.1 概述

ESP32 系列芯片外部挂载 SPI NOR Flash，用于存储固件、分区表、NVS 数据、文件系统等内容。Flash 容量从 **512 KB 到 16 MB** 不等，取决于模组型号。

| 模组 | 典型 Flash 大小 |
|------|----------------|
| ESP32-C3-MINI | 4 MB |
| ESP32-WROOM-32 | 4 MB |
| ESP32-WROVER | 4 / 8 / 16 MB |
| ESP32-S3-WROOM | 8 / 16 MB |
| ESP32-P4 | 16 MB |

### 1.2 SPI 模式

Flash 通过 SPI 总线与 CPU 通信，支持以下模式：

- **SPI（Standard SPI）**：单线传输，1-bit，速度较慢，兼容性最好。
- **Dual SPI**：双线传输，2-bit。
- **Quad SPI（QPI）**：四线传输，4-bit，读写带宽大幅提升。
- **Octal SPI（OPI）**：八线传输，8-bit，用于高性能 PSRAM 和 Flash。

ESP32-S3 支持 Quad SPI Flash，ESP32-P4 支持 Octal SPI。

### 1.3 Flash 读写特性

Flash 的基本操作规则：

1. **先擦后写**：Flash 只能将 1 写成 0，不能直接将 0 写成 1。必须先擦除（将整块设为全 1）再写入。
2. **擦除粒度**：最小擦除单位是 **sector（4 KB）**，也有 32 KB 和 64 KB 的 block 擦除。
3. **读取粒度**：任意字节对齐读取。
4. **写入粒度**：最小 4 字节对齐写入（32-bit word）。
5. **擦写寿命**：典型 NOR Flash 为 **10 万次** 擦写循环。

### 1.4 Flash 操作 API

```c
#include "esp_spi_flash.h"
#include "esp_flash.h"

// 读取 Flash 大小
uint32_t flash_size = 0;
esp_flash_get_size(NULL, &flash_size);
ESP_LOGI(TAG, "Flash size: %u bytes", flash_size);

// 直接读取 Flash（地址需要映射到 data bus）
const void *data;
spi_flash_mmap_handle_t handle;
esp_partition_mmap(partition, offset, size,
                   SPI_FLASH_MMAP_DATA, &data, &handle);

// 取消映射
spi_flash_mmap_unmap(handle);
```

### 1.5 XIP 与 mmap

ESP32 支持通过 **mmap** 将 Flash 映射到 CPU 地址空间，实现就地执行（XIP）和直接读取，无需先拷贝到 RAM。

```
Flash 地址空间 -> CPU 虚拟地址空间映射
0x42000000 ~ 0x42FFFFFF  (代码段映射)
0x3F800000 ~ 0x3FBFFFFF  (数据段映射)
```

---

## 2. 分区表

### 2.1 概述

ESP32 使用 **分区表（Partition Table）** 管理 Flash 空间的分配。每个分区有类型、子类型、偏移地址和大小。分区表存储在 Flash 偏移 `0x8000` 处。

### 2.2 CSV 格式

分区表是一个 CSV 文件，每行定义一个分区：

```csv
# Name,   Type, SubType, Offset,  Size,   Flags
nvs,      data, nvs,     0x9000,  0x6000,
phy_init, data, phy,     0xf000,  0x1000,
factory,  app,  factory, 0x10000, 0x140000,
storage,  data, spiffs,  ,        0x100000,
```

字段说明：

| 字段 | 说明 |
|------|------|
| Name | 分区名称，最长 16 字符 |
| Type | `app`（固件）或 `data`（数据） |
| SubType | 子类型，见下表 |
| Offset | 起始地址，留空自动计算 |
| Size | 分区大小，支持 K 和 M 后缀 |
| Flags | `encrypted`（加密）、`readonly`（只读） |

### 2.3 分区类型

#### app 类型

| SubType | 说明 |
|---------|------|
| `factory` | 出厂固件 |
| `ota_0` ~ `ota_15` | OTA 分区，共 16 个槽位 |
| `test` | 测试固件 |

#### data 类型

| SubType | 说明 |
|---------|------|
| `nvs` | NVS 键值对存储 |
| `phy` | PHY 初始化数据 |
| `spiffs` | SPIFFS 文件系统 |
| `littlefs` | LittleFS 文件系统 |
| `fat` | FAT 文件系统 |
| `coredump` | 核心转储 |
| `nvs_keys` | NVS 加密密钥 |

### 2.4 单 APP 布局（无 OTA）

最简单的布局，只有一个 factory 分区：

```csv
# Name,   Type, SubType, Offset,  Size,   Flags
nvs,      data, nvs,     0x9000,  0x6000,
phy_init, data, phy,     0xf000,  0x1000,
factory,  app,  factory, 0x10000, 0x140000,
```

适用场景：不需要 OTA 升级的产品，固件大小约 1.25 MB。

### 2.5 双 OTA 布局

支持 OTA 升级的标准布局，包含两个 OTA 分区：

```csv
# Name,    Type, SubType, Offset,  Size,    Flags
nvs,       data, nvs,     0x9000,  0x4000,
otadata,   data, ota,     0xd000,  0x2000,
phy_init,  data, phy,     0xf000,  0x1000,
ota_0,     app,  ota_0,   0x10000, 0x140000,
ota_1,     app,  ota_1,   0x150000,0x140000,
storage,   data, littlefs,,        0x100000,
```

OTA 分区的切换由 `otadata` 分区管理。写入 ota_0 时 ota_1 空闲，反之亦然。

### 2.6 自定义分区

在 `menuconfig` 中指定自定义分区表：

```
Component config → Partition Table → Custom partition table CSV
```

或者在 `CMakeLists.txt` / `sdkconfig` 中：

```
CONFIG_PARTITION_TABLE_CUSTOM=y
CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"
```

编译时可通过 `gen_esp32part.py` 工具验证：

```bash
python gen_esp32part.py partitions.csv  # 验证并打印布局
```

### 2.7 分区操作 API

```c
#include "esp_partition.h"

// 查找分区
const esp_partition_t *part = esp_partition_find_first(
    ESP_PARTITION_TYPE_DATA,
    ESP_PARTITION_SUBTYPE_DATA_SPIFFS,
    "storage");

// 读取分区
uint8_t buf[256];
esp_partition_read(part, 0, buf, sizeof(buf));

// 写入分区（先擦后写）
esp_partition_erase_range(part, 0, 4096);
esp_partition_write(part, 0, data, data_len);

// 遍历所有分区
esp_partition_iterator_t it = esp_partition_find(
    ESP_PARTITION_TYPE_ANY,
    ESP_PARTITION_SUBTYPE_ANY,
    NULL);
while (it != NULL) {
    const esp_partition_t *p = esp_partition_get(it);
    ESP_LOGI(TAG, "Partition: %s, offset: 0x%x, size: 0x%x",
             p->label, p->address, p->size);
    it = esp_partition_next(it);
}
esp_partition_iterator_release(it);
```

---

## 3. NVS 非易失性存储

### 3.1 概述

NVS（Non-Volatile Storage）是 ESP-IDF 提供的轻量级键值对存储系统，适合存储少量配置数据。数据持久化在 Flash 的 NVS 分区中。

### 3.2 核心概念

- **Namespace**：命名空间，用于逻辑分组，最长 15 字符。
- **Key**：键名，最长 15 字符。
- **Value**：值，支持多种数据类型。

### 3.3 支持的数据类型

| 类型 | C 类型 | NVS 类型枚举 |
|------|--------|-------------|
| 整型 | `int8_t / uint8_t` | `NVS_TYPE_I8 / NVS_TYPE_U8` |
| 整型 | `int16_t / uint16_t` | `NVS_TYPE_I16 / NVS_TYPE_U16` |
| 整型 | `int32_t / uint32_t` | `NVS_TYPE_I32 / NVS_TYPE_U32` |
| 整型 | `int64_t / uint64_t` | `NVS_TYPE_I64 / NVS_TYPE_U64` |
| 字符串 | `char[]` | `NVS_TYPE_STR` |
| 二进制 | `uint8_t[]` | `NVS_TYPE_BLOB` |

### 3.4 NVS 基本操作流程

```
nvs_flash_init() -> nvs_open() -> nvs_set_xxx() -> nvs_commit() -> nvs_close()
                                  nvs_get_xxx()
```

### 3.5 完整 API 示例

```c
#include "nvs_flash.h"
#include "nvs.h"

// 1. 初始化 NVS（通常在 app_main 中调用一次）
esp_err_t ret = nvs_flash_init();
if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
    ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    // NVS 分区损坏或版本不匹配，擦除后重新初始化
    ESP_ERROR_CHECK(nvs_flash_erase());
    ESP_ERROR_CHECK(nvs_flash_init());
}

// 2. 打开命名空间
nvs_handle_t my_handle;
ESP_ERROR_CHECK(nvs_open("config", NVS_READWRITE, &my_handle));

// 3. 写入数据
int32_t baud_rate = 115200;
ESP_ERROR_CHECK(nvs_set_i32(my_handle, "baud_rate", baud_rate));

uint8_t mode = 1;
ESP_ERROR_CHECK(nvs_set_u8(my_handle, "wifi_mode", mode));

const char *ssid = "MyWiFi";
ESP_ERROR_CHECK(nvs_set_str(my_handle, "ssid", ssid));

// 4. 提交（确保写入 Flash）
ESP_ERROR_CHECK(nvs_commit(my_handle));

// 5. 读取数据
int32_t read_baud = 0;
ret = nvs_get_i32(my_handle, "baud_rate", &read_baud);
if (ret == ESP_ERR_NVS_NOT_FOUND) {
    ESP_LOGW(TAG, "baud_rate not found, using default");
    read_baud = 9600;
}

// 读取字符串
char ssid_buf[33];
size_t ssid_len = sizeof(ssid_buf);
ESP_ERROR_CHECK(nvs_get_str(my_handle, "ssid", ssid_buf, &ssid_len));

// 6. 关闭句柄
nvs_close(my_handle);
```

### 3.6 NVS 批量操作与遍历

```c
// 遍历命名空间下所有键
nvs_iterator_t it = NULL;
esp_err_t err = nvs_entry_find("nvs", "config", NVS_TYPE_ANY, &it);
while (err == ESP_OK) {
    nvs_entry_info_t info;
    nvs_entry_info(it, &info);
    ESP_LOGI(TAG, "Key: %s, Type: %d", info.key, info.type);
    err = nvs_entry_next(&it);
}
nvs_release_iterator(it);
```

### 3.7 NVS 加密

NVS 支持基于 Flash 加密的 AES-256 加密，保护敏感数据：

```c
// 在 sdkconfig 中启用
// CONFIG_NVS_ENCRYPTION=y

// 使用 nvs_encr_lib 加密初始化
#include "nvs_flash.h"
#include "esp_encrypted_img.h"

// 初始化加密 NVS
nvs_flash_cfg_t cfg = NVS_FLASH_CONFIG_DEFAULT();
// 加密密钥存储在 nvs_keys 分区
ESP_ERROR_CHECK(nvs_flash_init());
```

加密 NVS 需要配合 **Flash 加密** 功能使用。密钥存储在 `nvs_keys` 分区中。

### 3.8 NVS 分区损坏恢复

```c
// 检测并恢复损坏的 NVS 分区
esp_err_t ret = nvs_flash_init();
if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
    ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_LOGW(TAG, "NVS partition corrupted, erasing...");
    ESP_ERROR_CHECK(nvs_flash_erase());
    ESP_ERROR_CHECK(nvs_flash_init());
}
```

---

## 4. 文件系统

### 4.1 概述

ESP-IDF 支持多种文件系统，用于在 Flash 或 SD 卡上存储文件：

| 文件系统 | 目录支持 | 掉电安全 | 适用场景 |
|---------|---------|---------|---------|
| SPIFFS | 不支持 | 一般 | 简单文件存储 |
| LittleFS | 支持 | 优秀 | 推荐的 Flash 文件系统 |
| FAT | 支持 | 一般 | SD 卡、兼容性 |

### 4.2 SPIFFS

SPIFFS（SPI Flash File System）是 ESP-IDF 最早支持的 Flash 文件系统。

特点：
- **不支持目录**，所有文件在扁平命名空间中。
- 使用 wear leveling 均匀磨损。
- 适合存储少量小文件（Web 页面、配置文件）。

```c
#include "esp_spiffs.h"

// 初始化 SPIFFS
esp_vfs_spiffs_conf_t conf = {
    .base_path = "/spiffs",
    .partition_label = "storage",
    .max_files = 5,
    .format_if_mount_failed = true,
};
ESP_ERROR_CHECK(esp_vfs_spiffs_register(&conf));

// 检查 SPIFFS 信息
size_t total = 0, used = 0;
esp_spiffs_info("storage", &total, &used);
ESP_LOGI(TAG, "SPIFFS: total=%zu, used=%zu", total, used);

// 使用标准文件 API
FILE *f = fopen("/spiffs/hello.txt", "r");
if (f) {
    char buf[64];
    fgets(buf, sizeof(buf), f);
    fclose(f);
}

// 写入文件
f = fopen("/spiffs/data.bin", "wb");
if (f) {
    uint8_t data[] = {0x01, 0x02, 0x03};
    fwrite(data, 1, sizeof(data), f);
    fclose(f);
}

// 卸载
esp_vfs_spiffs_unregister("storage");
```

### 4.3 LittleFS

LittleFS 是推荐的 Flash 文件系统，比 SPIFFS 更可靠。

特点：
- **支持目录**，可以创建子目录组织文件。
- **掉电安全**：写入过程中断电不会丢失已有数据。
- 内置 wear leveling。
- 支持文件元数据。

```c
#include "esp_littlefs.h"

// 初始化 LittleFS
esp_vfs_littlefs_conf_t conf = {
    .base_path = "/littlefs",
    .partition_label = "storage",
    .format_if_mount_failed = true,
    .dont_mount = false,
};
ESP_ERROR_CHECK(esp_vfs_littlefs_register(&conf));

// 创建目录
mkdir("/littlefs/config", 0777);

// 写入文件到子目录
FILE *f = fopen("/littlefs/config/settings.json", "w");
if (f) {
    fprintf(f, "{\"key\": \"value\"}");
    fclose(f);
}

// 列出目录内容
DIR *dir = opendir("/littlefs/config");
struct dirent *entry;
while ((entry = readdir(dir)) != NULL) {
    ESP_LOGI(TAG, "File: %s", entry->d_name);
}
closedir(dir);

// 检查文件系统信息
size_t total = 0, used = 0;
esp_littlefs_info("storage", &total, &used);
ESP_LOGI(TAG, "LittleFS: total=%zu, used=%zu", total, used);
```

### 4.4 SPIFFS vs LittleFS 对比

| 特性 | SPIFFS | LittleFS |
|------|--------|----------|
| 目录结构 | 扁平，无目录 | 支持多级目录 |
| 掉电安全 | 部分支持 | 完全支持 |
| 磨损均衡 | 内置 | 内置 |
| 写入速度 | 较快 | 中等 |
| RAM 占用 | 较少 | 稍多 |
| 推荐程度 | 旧项目兼容 | 新项目首选 |

### 4.5 FAT 文件系统（SD 卡）

FAT 文件系统主要用于 SD 卡存储：

```c
#include "esp_vfs_fat.h"
#include "sdmmc_cmd.h"

// SD 卡挂载配置
sdmmc_host_t host = SDSPI_HOST_DEFAULT();
spi_bus_config_t bus_cfg = {
    .mosi_io_num = GPIO_NUM_23,
    .miso_io_num = GPIO_NUM_19,
    .sclk_io_num = GPIO_NUM_18,
    .quadwp_io_num = -1,
    .quadhd_io_num = -1,
    .max_transfer_sz = 4000,
};
spi_bus_initialize(host.slot, &bus_cfg, SDSPI_DEFAULT_DMA);

esp_vfs_fat_sdmmc_mount_config_t mount_config = {
    .format_if_mount_failed = false,
    .max_files = 5,
    .allocation_unit_size = 16 * 1024,
};

sdmmc_card_t *card;
ESP_ERROR_CHECK(esp_vfs_fat_sdspi_mount("/sdcard", &host,
    &mount_config, &card));

// 使用标准文件 API 读写 SD 卡
FILE *f = fopen("/sdcard/data.csv", "a");
if (f) {
    fprintf(f, "%d,%f,%s\n", 1, 3.14, "hello");
    fclose(f);
}

// 卸载
esp_vfs_fat_sdcard_unmount("/sdcard", card);
spi_bus_free(host.slot);
```

### 4.6 文件系统烧录

在 `CMakeLists.txt` 中添加文件系统镜像生成：

```cmake
# SPIFFS
spiffs_create_partition_image(storage data_folder FLASH_IN_PROJECT)

# LittleFS
littlefs_create_partition_image(storage data_folder FLASH_IN_PROJECT)
```

---

## 5. PSRAM 外部 RAM

### 5.1 概述

部分 ESP32 模组（如 WROVER、S3-WROOM-1）集成了外部 **PSRAM（Pseudo-Static RAM）**，提供 2 MB ~ 8 MB 的额外 RAM。

### 5.2 PSRAM 类型

| 类型 | 数据线 | 速度 | 适用芯片 |
|------|--------|------|---------|
| QPI PSRAM | 4-bit | ~40 MHz | ESP32, ESP32-S2 |
| OPI PSRAM | 8-bit | ~80 MHz | ESP32-S3, ESP32-P4 |

### 5.3 启用 PSRAM

在 `menuconfig` 中启用：

```
Component config → ESP PSRAM → Support for external, SPI-connected RAM
```

或者在 `sdkconfig` 中：

```
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_QUAD=y          # QPI 模式
CONFIG_SPIRAM_SPEED_80M=y          # 频率
CONFIG_SPIRAM_FETCH_INSTRUCTIONS=y # 从 PSRAM 执行代码
CONFIG_SPIRAM_RODATA=y             # 只读数据放入 PSRAM
```

### 5.4 静态分配到 PSRAM

使用 `EXT_RAM_ATTR` 属性将全局变量放入 PSRAM：

```c
#include "esp_attr.h"

// 大数组放入 PSRAM，节省内部 SRAM
EXT_RAM_ATTR uint8_t large_buffer[1024 * 1024];  // 1 MB

// 常量数据放入 PSRAM
EXT_RAM_ATTR const uint8_t lookup_table[65536] = { ... };

// 静态对象
EXT_RAM_ATTR static float fft_buffer[4096];
```

注意：`EXT_RAM_ATTR` 仅适用于全局和静态变量，不能用于栈上局部变量。

### 5.5 动态分配到 PSRAM

使用 `heap_caps_malloc` 系列函数：

```c
#include "esp_heap_caps.h"

// 从 PSRAM 分配内存
void *buf = heap_caps_malloc(1024 * 1024, MALLOC_CAP_SPIRAM);
if (buf == NULL) {
    ESP_LOGE(TAG, "PSRAM allocation failed");
}

// 从 PSRAM 分配并清零
void *buf2 = heap_caps_calloc(256, sizeof(int), MALLOC_CAP_SPIRAM);

// 从 PSRAM 分配并重新调整大小
void *buf3 = heap_caps_realloc(buf, 2048 * 1024, MALLOC_CAP_SPIRAM);

// 释放
heap_caps_free(buf2);

// 优先从 PSRAM 分配，不够再用内部 RAM
void *buf4 = malloc(1024 * 1024);  // 如果启用 CONFIG_SPIRAM_USE_MALLOC
```

### 5.6 DMA 限制

PSRAM 不能直接用于 DMA 传输，原因如下：

1. DMA 控制器只能访问内部 SRAM 和特定外设地址。
2. SPI、I2S、Camera 等外设的 DMA buffer 必须在内部 SRAM 中。

解决方案：

```c
// 分配 DMA 兼容的 buffer
uint8_t *dma_buf = heap_caps_malloc(4096, MALLOC_CAP_DMA);

// 从 PSRAM 拷贝到 DMA buffer
memcpy(dma_buf, psram_data, 4096);

// DMA 传输完成后拷贝回 PSRAM
memcpy(psram_data, dma_buf, 4096);
heap_caps_free(dma_buf);
```

### 5.7 PSRAM 初始化检测

```c
#include "esp_psram.h"

// 检测 PSRAM 是否可用
if (esp_psram_is_initialized()) {
    size_t psram_size = esp_psram_get_size();
    ESP_LOGI(TAG, "PSRAM available: %zu bytes", psram_size);
} else {
    ESP_LOGW(TAG, "PSRAM not available");
}

// 查看 PSRAM 可用内存
size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
size_t largest_block = heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);
ESP_LOGI(TAG, "PSRAM free: %zu, largest block: %zu",
         free_psram, largest_block);
```

---

## 6. OTA 基础

### 6.1 概述

OTA（Over-The-Air）允许通过无线网络远程更新 ESP32 固件，无需物理接触设备。ESP-IDF 提供了完整的 OTA 框架。

### 6.2 双分区原理

OTA 基于 Flash 中的两个 app 分区实现：

```
Flash 布局:
+------------------+
| Partition Table  |  0x8000
+------------------+
| NVS              |  0x9000
+------------------+
| OTA Data         |  0xD000   <- 记录当前活动分区
+------------------+
| ota_0 (app0)     |  0x10000  <- 固件 A
+------------------+
| ota_1 (app1)     |  0x150000 <- 固件 B
+------------------+
```

工作流程：

1. 设备运行 `ota_0` 中的固件。
2. 下载新固件到 `ota_1`。
3. 更新 OTA Data 标记 `ota_1` 为活动分区。
4. 重启后从 `ota_1` 启动新固件。
5. 下次更新时写入 `ota_0`，交替使用。

### 6.3 OTA 分区配置

```csv
# 双 OTA 布局
otadata,  data, ota,     0xd000,   0x2000,
ota_0,    app,  ota_0,   0x10000,  0x140000,
ota_1,    app,  ota_1,   0x150000, 0x140000,
```

### 6.4 OTA 更新 API

```c
#include "esp_ota_ops.h"
#include "esp_http_client.h"

// 获取当前运行的分区
const esp_partition_t *running = esp_ota_get_running_partition();
ESP_LOGI(TAG, "Running partition: %s at 0x%x",
         running->label, running->address);

// 获取下一个可用的 OTA 分区
const esp_partition_t *update = esp_ota_get_next_update_partition(NULL);
ESP_LOGI(TAG, "Update partition: %s at 0x%x",
         update->label, update->address);

// 开始 OTA 更新
esp_ota_handle_t handle;
ESP_ERROR_CHECK(esp_ota_begin(update, OTA_SIZE_UNKNOWN, &handle));

// 写入固件数据（通常在 HTTP 回调中循环调用）
esp_err_t err = esp_ota_write(handle, data, data_len);
if (err != ESP_OK) {
    ESP_LOGE(TAG, "OTA write failed: %s", esp_err_to_name(err));
    esp_ota_abort(handle);
    return;
}

// 结束并验证
ESP_ERROR_CHECK(esp_ota_end(handle));

// 设置启动分区
ESP_ERROR_CHECK(esp_ota_set_boot_partition(update));

// 重启
esp_restart();
```

### 6.5 Rollback 回滚机制

ESP-IDF 支持固件回滚，如果新固件有问题可以回退到上一个版本：

```c
// 在新固件启动后标记为确认
// 如果不确认，下次重启会自动回滚
#include "esp_ota_ops.h"

// 方式 1: 手动确认
esp_ota_mark_app_valid_cancel_rollback();

// 方式 2: 自动回滚配置
// sdkconfig:
// CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y

// 检测是否从 rollback 恢复
esp_ota_img_states_t state;
const esp_partition_t *running = esp_ota_get_running_partition();
if (esp_ota_get_state_partition(running, &state) == ESP_OK) {
    if (state == ESP_OTA_IMG_PENDING_VERIFY) {
        // 新固件待确认
        if (app_is_working_correctly()) {
            esp_ota_mark_app_valid_cancel_rollback();
        } else {
            esp_ota_mark_app_invalid_rollback_and_reboot();
        }
    }
}
```

### 6.6 OTA 标记状态

| 状态 | 说明 |
|------|------|
| `ESP_OTA_IMG_NEW` | 新固件，从未启动 |
| `ESP_OTA_IMG_PENDING_VERIFY` | 已启动，待确认 |
| `ESP_OTA_IMG_VALID` | 已确认，有效固件 |
| `ESP_OTA_IMG_INVALID` | 已标记为无效 |
| `ESP_OTA_IMG_UNDEFINED` | 未定义状态 |

---

## 7. WiFi OTA

### 7.1 概述

WiFi OTA 是最常见的 OTA 方式，通过 HTTPS 从服务器下载新固件。

### 7.2 esp_https_ota API

```c
#include "esp_https_ota.h"
#include "esp_ota_ops.h"

esp_err_t do_firmware_upgrade(const char *url) {
    esp_http_client_config_t config = {
        .url = url,
        .cert_pem = (const char *)server_cert_pem_start,
        .timeout_ms = 5000,
        .keep_alive_enable = true,
    };

    esp_https_ota_config_t ota_config = {
        .http_config = &config,
    };

    esp_https_ota_handle_t ota_handle = NULL;
    esp_err_t err = esp_https_ota_begin(&ota_config, &ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "OTA begin failed: %s", esp_err_to_name(err));
        return err;
    }

    // 获取固件大小
    int image_size = esp_https_ota_get_image_size(ota_handle);
    ESP_LOGI(TAG, "Firmware size: %d bytes", image_size);

    // 循环读取并写入
    while (1) {
        err = esp_https_ota_perform(ota_handle);
        if (err == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            // 数据下载中，继续
            continue;
        }
        if (err == ESP_OK) {
            break;
        }
        ESP_LOGE(TAG, "OTA perform failed: %s", esp_err_to_name(err));
        esp_https_ota_abort(ota_handle);
        return err;
    }

    // 检查固件完整性
    if (!esp_https_ota_is_complete_data_received(ota_handle)) {
        ESP_LOGE(TAG, "Incomplete data received");
        esp_https_ota_abort(ota_handle);
        return ESP_FAIL;
    }

    // 完成 OTA
    err = esp_https_ota_finish(ota_handle);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "OTA successful, restarting...");
        esp_restart();
    }
    return err;
}
```

### 7.3 HTTPS 证书配置

```c
// 内嵌证书（推荐用于生产环境）
extern const uint8_t server_cert_pem_start[] asm("_binary_server_cert_pem_start");
extern const uint8_t server_cert_pem_end[]   asm("_binary_server_cert_pem_end");

esp_http_client_config_t config = {
    .url = "https://ota.example.com/firmware.bin",
    .cert_pem = (const char *)server_cert_pem_start,
};

// 使用 CA 证书包（适合多服务器场景）
// 在 CMakeLists.txt 中:
// target_add_binary_data(${COMPONENT_LIB} "certs/ca_cert.pem" TEXT)
```

### 7.4 进度回调

```c
// 自定义进度回调
static void ota_progress_callback(size_t current, size_t total) {
    int percent = (current * 100) / total;
    ESP_LOGI(TAG, "OTA progress: %d%% (%zu/%zu)", percent, current, total);
}

// 使用 esp_https_ota 时，可以通过事件获取进度
static void ota_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    if (event_base == ESP_HTTPS_OTA_EVENT) {
        switch (event_id) {
            case ESP_HTTPS_OTA_START:
                ESP_LOGI(TAG, "OTA started");
                break;
            case ESP_HTTPS_OTA_CONNECTED:
                ESP_LOGI(TAG, "Connected to server");
                break;
            case ESP_HTTPS_OTA_GET_IMG_DESC:
                ESP_LOGI(TAG, "Reading image descriptor");
                break;
            case ESP_HTTPS_OTA_VERIFY_CHIP_ID:
                ESP_LOGI(TAG, "Verifying chip ID");
                break;
            case ESP_HTTPS_OTA_DECRYPT_CB:
                ESP_LOGI(TAG, "Decrypting firmware");
                break;
            case ESP_HTTPS_OTA_WRITE_FLASH:
                ESP_LOGI(TAG, "Writing to flash");
                break;
            case ESP_HTTPS_OTA_UPDATE_BOOT_PARTITION:
                ESP_LOGI(TAG, "Updating boot partition");
                break;
            case ESP_HTTPS_OTA_FINISH:
                ESP_LOGI(TAG, "OTA finished");
                break;
            case ESP_HTTPS_OTA_ABORT:
                ESP_LOGE(TAG, "OTA aborted");
                break;
        }
    }
}
```

### 7.5 版本检查

```c
// 固件版本信息嵌入
#include "esp_app_desc.h"

// 获取当前固件版本
const esp_app_desc_t *app_desc = esp_app_get_description();
ESP_LOGI(TAG, "Firmware version: %s", app_desc->version);
ESP_LOGI(TAG, "Project name: %s", app_desc->project_name);
ESP_LOGI(TAG, "Compile time: %s %s", app_desc->date, app_desc->time);

// OTA 前版本比较
bool should_upgrade(const char *current_ver, const char *new_ver) {
    int cur_major, cur_minor, cur_patch;
    int new_major, new_minor, new_patch;

    sscanf(current_ver, "%d.%d.%d", &cur_major, &cur_minor, &cur_patch);
    sscanf(new_ver, "%d.%d.%d", &new_major, &new_minor, &new_patch);

    if (new_major > cur_major) return true;
    if (new_major == cur_major && new_minor > cur_minor) return true;
    if (new_major == cur_major && new_minor == cur_minor &&
        new_patch > cur_patch) return true;

    return false;
}
```

### 7.6 自定义 OTA 流程

```c
// 使用 esp_http_client 手动实现 OTA（更灵活）
esp_err_t custom_ota(const char *url) {
    esp_http_client_config_t config = {
        .url = url,
        .cert_pem = (const char *)server_cert_pem_start,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_open(client, 0);

    int content_length = esp_http_client_fetch_headers(client);
    ESP_LOGI(TAG, "Firmware size: %d", content_length);

    const esp_partition_t *update = esp_ota_get_next_update_partition(NULL);
    esp_ota_handle_t handle;
    esp_ota_begin(update, content_length, &handle);

    char buf[1024];
    int total_read = 0;
    while (total_read < content_length) {
        int read = esp_http_client_read(client, buf, sizeof(buf));
        if (read <= 0) break;
        esp_ota_write(handle, buf, read);
        total_read += read;
    }

    esp_ota_end(handle);
    esp_ota_set_boot_partition(update);
    esp_http_client_cleanup(client);
    return ESP_OK;
}
```

---

## 8. OTA 安全

### 8.1 签名验证

固件签名防止恶意固件被安装：

```
# sdkconfig 配置
CONFIG_SECURE_SIGNED_APPS=y
CONFIG_SECURE_BOOT_V2_RSA=y
CONFIG_SECURE_BOOT_RSA_KEY_PATH="secure_boot_signing_key.pem"
```

签名流程：

1. 编译时使用私钥对固件签名。
2. 烧录时将公钥写入 eFuse。
3. Bootloader 启动时验证固件签名。
4. 签名验证失败则拒绝启动。

```bash
# 生成签名密钥
espsecure.py generate_signing_key secure_boot_signing_key.pem

# 签名固件
espsecure.py sign_data --keyfile secure_boot_signing_key.pem firmware.bin
```

### 8.2 降级保护

防止固件回退到有漏洞的旧版本：

```c
// 在固件中记录最低可接受版本
#define MIN_ALLOWED_VERSION "1.2.0"

bool check_version_allowed(const char *version) {
    // 简单版本比较
    if (should_upgrade(MIN_ALLOWED_VERSION, version)) {
        // version 大于等于最低版本
        return true;
    }
    // 也可以在 eFuse 中烧录 anti-rollback 版本号
    return false;
}

// eFuse 防回滚（硬件级别）
// 烧录最低版本到 eFuse，Bootloader 拒绝低于此版本的固件
// 配置:
// CONFIG_SECURE_BOOT_ENABLE_ANTI_ROLLBACK=y
// CONFIG_SECURE_BOOT_ANTIREPLAY_VERSION=2
```

### 8.3 Flash 加密

保护固件不被读取和逆向：

```
# sdkconfig
CONFIG_FLASH_ENCRYPTION_ENABLED=y
CONFIG_FLASH_ENCRYPTION_AES_XTS_128=y
```

Flash 加密特性：
- 加密后 Flash 内容无法直接读取。
- 首次烧录时加密，后续更新自动加密。
- 需要配合 secure boot 使用效果最佳。

### 8.4 安全 OTA 完整流程

```
1. 服务器生成带签名的固件
2. 设备通过 HTTPS 下载固件
3. 验证固件签名
4. 验证版本号（防降级）
5. 写入 OTA 分区
6. 设置启动分区
7. 重启 -> Bootloader 验证签名
8. 启动新固件
9. 固件自行确认（防回滚）
```

---

## 9. 内存管理 API

### 9.1 内存区域

ESP32 有多个内存区域：

| 区域 | 大小 | 说明 |
|------|------|------|
| 内部 SRAM | 320~520 KB | 高速，DMA 兼容 |
| PSRAM | 2~8 MB | 外部，较慢 |
| Flash | 1~16 MB | 只读映射 |

### 9.2 内存查询 API

```c
#include "esp_heap_caps.h"

// 查询总空闲内存
size_t free_heap = esp_get_free_heap_size();
ESP_LOGI(TAG, "Free heap: %zu bytes", free_heap);

// 查询内部 SRAM 空闲
size_t free_internal = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
ESP_LOGI(TAG, "Free internal SRAM: %zu bytes", free_internal);

// 查询 PSRAM 空闲
size_t free_psram = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
ESP_LOGI(TAG, "Free PSRAM: %zu bytes", free_psram);

// 查询 DMA 可用内存
size_t free_dma = heap_caps_get_free_size(MALLOC_CAP_DMA);
ESP_LOGI(TAG, "Free DMA memory: %zu bytes", free_dma);

// 查询最大连续空闲块
size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_DEFAULT);
ESP_LOGI(TAG, "Largest free block: %zu bytes", largest);

// 查询最小历史空闲值（用于检测是否接近 OOM）
size_t min_free = heap_caps_get_minimum_free_size(MALLOC_CAP_DEFAULT);
ESP_LOGI(TAG, "Minimum free heap ever: %zu bytes", min_free);
```

### 9.3 内存泄漏检测

ESP-IDF 提供了多种内存调试工具：

```c
// 1. 启用 heap tracing（menuconfig）
// CONFIG_HEAP_TRACING_STANDALONE=y
// CONFIG_HEAP_TRACING_DST_CRDIR=/tmp

// 2. 手动检查内存泄漏
void check_memory_leak(void) {
    static size_t last_free = 0;
    size_t current_free = esp_get_free_heap_size();

    if (last_free > 0) {
        int diff = last_free - current_free;
        if (diff > 100) {
            ESP_LOGW(TAG, "Possible memory leak: %d bytes lost", diff);
        }
    }
    last_free = current_free;
}

// 3. 使用 heap_caps_print_heap_info 打印详细信息
heap_caps_print_heap_info(MALLOC_CAP_DEFAULT);
heap_caps_print_heap_info(MALLOC_CAP_SPIRAM);
```

### 9.4 多堆内存分配

```c
// 按能力分配内存
void *ptr;

// 任意位置分配
ptr = malloc(1024);

// 仅从内部 SRAM 分配（DMA 需要）
ptr = heap_caps_malloc(1024, MALLOC_CAP_DMA);

// 仅从 PSRAM 分配（大缓冲区）
ptr = heap_caps_malloc(1024 * 1024, MALLOC_CAP_SPIRAM);

// 从 32-bit 对齐的内存分配
ptr = heap_caps_malloc(1024, MALLOC_CAP_32BIT);

// 从可以执行代码的内存分配
ptr = heap_caps_malloc(1024, MALLOC_CAP_EXEC);

// 组合能力
ptr = heap_caps_malloc(1024, MALLOC_CAP_DMA | MALLOC_CAP_8BIT);
```

### 9.5 内存调试配置

```
# menuconfig 中的调试选项

CONFIG_HEAP_POISONING_LIGHT=y    # 轻量级堆毒化（检测溢出）
CONFIG_HEAP_POISONING_COMPREHENSIVE=y  # 全面堆毒化（更精确但更慢）
CONFIG_HEAP_ABORT_WHEN_ALLOCATION_FAILS=y  # 分配失败时 abort
CONFIG_HEAP_TASK_TRACKING=y      # 跟踪每个任务的内存使用
CONFIG_HEAP_USE_HOOKS=y          # 使用 hook 函数监控分配
```

### 9.6 内存使用最佳实践

1. **大对象放 PSRAM**：图片缓冲区、音频数据、大型数据结构使用 `MALLOC_CAP_SPIRAM`。
2. **DMA buffer 放内部 RAM**：外设 DMA buffer 必须使用 `MALLOC_CAP_DMA`。
3. **避免碎片化**：尽量在初始化时分配大块内存，运行中复用。
4. **定期检查**：使用 `heap_caps_get_minimum_free_size()` 确保不会 OOM。
5. **栈大小优化**：使用 `uxTaskGetStackHighWaterMark()` 检查任务栈使用情况。

```c
// 检查任务栈使用
void check_task_stack(void) {
    UBaseType_t high_water = uxTaskGetStackHighWaterMark(NULL);
    ESP_LOGI(TAG, "Stack high water mark: %u bytes", high_water * sizeof(StackType_t));
    // 如果值很小（< 256），考虑增大栈大小
}
```

---

## 附录：常用头文件速查

| 功能 | 头文件 |
|------|--------|
| Flash 操作 | `esp_flash.h`, `spi_flash_mmap.h` |
| 分区表 | `esp_partition.h` |
| NVS | `nvs_flash.h`, `nvs.h` |
| SPIFFS | `esp_spiffs.h` |
| LittleFS | `esp_littlefs.h` |
| FAT | `esp_vfs_fat.h`, `sdmmc_cmd.h` |
| PSRAM | `esp_psram.h`, `esp_heap_caps.h` |
| OTA | `esp_ota_ops.h`, `esp_https_ota.h` |
| 内存管理 | `esp_heap_caps.h`, `esp_system.h` |
| VFS | `esp_vfs.h` |
