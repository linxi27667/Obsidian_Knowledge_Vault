# ESP-IDF NVS非易失性存储 （键值对存储与数据持久化）

## 核心概念

- **NVS** - Non-Volatile Storage，Flash上的键值对存储
- **命名空间** - 键值对的分组机制，防止键名冲突
- **磨损均衡** - NVS自动处理Flash擦写均衡，延长寿命
- **支持数据类型** - 整型、字符串、二进制数据

---

## 一、NVS基础

### 1.1 NVS架构

```
NVS存储结构：

Flash分区 (nvs分区)
├─────────────────────────────────────────────────────────┐
│                      页面(Page) 1                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ 命名空间A   │  │ 命名空间B   │  │  命名空间C      │ │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────────┐ │ │
│  │ │key1:int │ │  │ │key1:str│ │  │ │key1:blob    │ │ │
│  │ │key2:str │ │  │ │key2:int│ │  │ │key2:int     │ │ │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────────┘ │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                      页面(Page) 2                        │
│              (当页面1满时，数据迁移到页面2)                │
└─────────────────────────────────────────────────────────┘
```

---

### 1.2 NVS分区配置

```
# partitions.csv 中的NVS分区
# Name,   Type, SubType, Offset,  Size,    Flags
nvs,      data, nvs,     0x9000,  0x6000,
```

| 参数 | 说明 | 典型值 |
|------|------|--------|
| `Size` | 分区大小 | 0x6000 (24KB) |
| `Type` | 类型 | `data` |
| `SubType` | 子类型 | `nvs` |

---

## 二、NVS初始化

### 2.1 初始化NVS

```c
#include "nvs_flash.h"
#include "esp_log.h"

static const char *TAG = "NVS";

void nvs_init(void)
{
    esp_err_t ret = nvs_flash_init();
    
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || 
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        // NVS分区需要擦除
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    
    ESP_ERROR_CHECK(ret);
    ESP_LOGI(TAG, "NVS initialized successfully");
}
```

---

### 2.2 指定分区初始化

```c
// 使用自定义分区
esp_err_t nvs_flash_init_partition(const char *partition_name);

// 示例
ESP_ERROR_CHECK(nvs_flash_init_partition("nvs"));

// 擦除指定分区
esp_err_t nvs_flash_erase_partition(const char *part_name);
```

---

## 三、数据写入

### 3.1 打开NVS句柄

```c
#include "nvs.h"

nvs_handle_t nvs_handle;

// 以读写模式打开命名空间
esp_err_t err = nvs_open("storage", NVS_READWRITE, &nvs_handle);

if (err != ESP_OK) {
    ESP_LOGE(TAG, "Error opening NVS: %s", esp_err_to_name(err));
} else {
    ESP_LOGI(TAG, "NVS namespace opened");
}

// 使用完毕后关闭
nvs_close(nvs_handle);
```

| 模式 | 说明 |
|------|------|
| `NVS_READONLY` | 只读模式 |
| `NVS_READWRITE` | 读写模式 |

---

### 3.2 写入整型数据

```c
// 写入int8_t
int8_t val_i8 = -100;
nvs_set_i8(nvs_handle, "key_i8", val_i8);

// 写入uint8_t
uint8_t val_u8 = 200;
nvs_set_u8(nvs_handle, "key_u8", val_u8);

// 写入int16_t
int16_t val_i16 = -1000;
nvs_set_i16(nvs_handle, "key_i16", val_i16);

// 写入uint16_t
uint16_t val_u16 = 50000;
nvs_set_u16(nvs_handle, "key_u16", val_u16);

// 写入int32_t
int32_t val_i32 = -100000;
nvs_set_i32(nvs_handle, "key_i32", val_i32);

// 写入uint32_t
uint32_t val_u32 = 100000;
nvs_set_u32(nvs_handle, "key_u32", val_u32);

// 写入int64_t
int64_t val_i64 = -10000000000LL;
nvs_set_i64(nvs_handle, "key_i64", val_i64);

// 写入uint64_t
uint64_t val_u64 = 10000000000ULL;
nvs_set_u64(nvs_handle, "key_u64", val_u64);

// 提交写入（重要！）
nvs_commit(nvs_handle);
```

---

### 3.3 写入字符串

```c
// 方式1：直接写入字符串
const char *ssid = "MyHomeWiFi";
nvs_set_str(nvs_handle, "wifi_ssid", ssid);

// 方式2：动态字符串
char password[64] = "my_password_123";
nvs_set_str(nvs_handle, "wifi_pass", password);

// 提交
nvs_commit(nvs_handle);
```

---

### 3.4 写入二进制数据(Blob)

```c
// 定义结构体
typedef struct {
    float calibration_value;
    uint16_t threshold;
    uint8_t enabled;
} device_config_t;

device_config_t config = {
    .calibration_value = 1.25f,
    .threshold = 1000,
    .enabled = 1
};

// 写入blob
nvs_set_blob(nvs_handle, "device_config", &config, sizeof(config));

// 提交
nvs_commit(nvs_handle);
```

---

## 四、数据读取

### 4.1 读取整型数据

```c
int32_t val_i32 = 0;
esp_err_t err = nvs_get_i32(nvs_handle, "key_i32", &val_i32);

if (err == ESP_OK) {
    ESP_LOGI(TAG, "Read int32: %ld", val_i32);
} else if (err == ESP_ERR_NVS_NOT_FOUND) {
    ESP_LOGW(TAG, "Key not found, using default");
    val_i32 = 0;  // 默认值
}

// 其他类型类似...
uint64_t val_u64 = 0;
nvs_get_u64(nvs_handle, "key_u64", &val_u64);
```

---

### 4.2 读取字符串

```c
// 获取字符串长度
size_t length = 0;
nvs_get_str(nvs_handle, "wifi_ssid", NULL, &length);

if (length > 0) {
    // 分配缓冲区
    char *ssid = malloc(length);
    
    // 读取字符串
    nvs_get_str(nvs_handle, "wifi_ssid", ssid, &length);
    
    ESP_LOGI(TAG, "WiFi SSID: %s", ssid);
    
    free(ssid);
}
```

---

### 4.3 读取二进制数据

```c
device_config_t config;
size_t config_size = sizeof(config);

esp_err_t err = nvs_get_blob(nvs_handle, "device_config", &config, &config_size);

if (err == ESP_OK) {
    ESP_LOGI(TAG, "Config: calib=%.2f, threshold=%u, enabled=%u",
             config.calibration_value,
             config.threshold,
             config.enabled);
}
```

---

## 五、数据管理

### 5.1 删除键值对

```c
// 删除单个键
nvs_erase_key(nvs_handle, "key_i32");
nvs_commit(nvs_handle);

// 删除整个命名空间的所有键
nvs_erase_all(nvs_handle);
nvs_commit(nvs_handle);
```

---

### 5.2 遍历命名空间 (v5.0+ API)

```c
// v5.0+ 新的迭代器API：函数返回esp_err_t，通过参数传出迭代器
nvs_iterator_t it = NULL;  // 必须初始化为NULL
esp_err_t res = nvs_entry_find("nvs", "storage", NVS_TYPE_ANY, &it);

while (res == ESP_OK) {
    nvs_entry_info_t info;
    nvs_entry_info(it, &info);  // 获取条目信息

    ESP_LOGI(TAG, "Key: %s, Type: %d", info.key, info.type);

    res = nvs_entry_next(&it);  // 注意：传入&it
}

// 释放迭代器
nvs_release_iterator(it);
```

> ⚠️ **v5.0 API变更说明**：
> - `nvs_entry_find()` 现在返回 `esp_err_t`，通过第4个参数传出迭代器
> - `nvs_entry_next()` 现在返回 `esp_err_t`，通过参数修改迭代器
> - 迭代器必须在使用前初始化为 `NULL`
> - 旧代码中 `it = nvs_entry_find(...)` 和 `it = nvs_entry_next(it)` 的用法已过时

---

### 5.3 获取信息

```c
// 获取已使用的条目数
nvs_stats_t nvs_stats;
nvs_get_stats(NULL, &nvs_stats);

ESP_LOGI(TAG, "NVS Stats:");
ESP_LOGI(TAG, "  Used entries: %d", nvs_stats.used_entries);
ESP_LOGI(TAG, "  Free entries: %d", nvs_stats.free_entries);
ESP_LOGI(TAG, "  Total entries: %d", nvs_stats.total_entries);
ESP_LOGI(TAG, "  Namespace count: %d", nvs_stats.namespace_count);
```

---

## 六、NVS与配置系统

### 6.1 封装NVS操作

```c
// nvs_config.h
#ifndef NVS_CONFIG_H
#define NVS_CONFIG_H

#include <stdint.h>
#include <stdbool.h>
#include <string.h>

// WiFi配置
typedef struct {
    char ssid[32];
    char password[64];
    bool configured;
} wifi_config_nvs_t;

// 设备配置
typedef struct {
    uint32_t device_id;
    float calibration;
    uint16_t sample_interval_ms;
    bool auto_connect;
} device_settings_t;

// API声明
esp_err_t nvs_config_init(void);
esp_err_t nvs_save_wifi_config(const wifi_config_nvs_t *config);
esp_err_t nvs_load_wifi_config(wifi_config_nvs_t *config);
esp_err_t nvs_save_device_settings(const device_settings_t *settings);
esp_err_t nvs_load_device_settings(device_settings_t *settings);

#endif
```

```c
// nvs_config.c
#include "nvs_config.h"
#include "nvs.h"
#include "esp_log.h"

static const char *TAG = "NVS_CONFIG";
static const char *NVS_NAMESPACE = "app_config";

esp_err_t nvs_config_init(void)
{
    return nvs_flash_init();
}

esp_err_t nvs_save_wifi_config(const wifi_config_nvs_t *config)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    
    nvs_set_str(handle, "wifi_ssid", config->ssid);
    nvs_set_str(handle, "wifi_pass", config->password);
    nvs_set_u8(handle, "wifi_cfgd", config->configured ? 1 : 0);
    
    err = nvs_commit(handle);
    nvs_close(handle);
    
    return err;
}

esp_err_t nvs_load_wifi_config(wifi_config_nvs_t *config)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) return err;
    
    size_t len = sizeof(config->ssid);
    nvs_get_str(handle, "wifi_ssid", config->ssid, &len);
    
    len = sizeof(config->password);
    nvs_get_str(handle, "wifi_pass", config->password, &len);
    
    uint8_t configured = 0;
    nvs_get_u8(handle, "wifi_cfgd", &configured);
    config->configured = (configured != 0);
    
    nvs_close(handle);
    
    return ESP_OK;
}

esp_err_t nvs_save_device_settings(const device_settings_t *settings)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    
    nvs_set_u32(handle, "dev_id", settings->device_id);
    nvs_set_blob(handle, "dev_calib", &settings->calibration, sizeof(float));
    nvs_set_u16(handle, "dev_interval", settings->sample_interval_ms);
    nvs_set_u8(handle, "dev_autocon", settings->auto_connect ? 1 : 0);
    
    err = nvs_commit(handle);
    nvs_close(handle);
    
    return err;
}

esp_err_t nvs_load_device_settings(device_settings_t *settings)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) return err;
    
    nvs_get_u32(handle, "dev_id", &settings->device_id);
    
    size_t len = sizeof(float);
    nvs_get_blob(handle, "dev_calib", &settings->calibration, &len);
    
    nvs_get_u16(handle, "dev_interval", &settings->sample_interval_ms);
    
    uint8_t autocon = 0;
    nvs_get_u8(handle, "dev_autocon", &autocon);
    settings->auto_connect = (autocon != 0);
    
    nvs_close(handle);
    
    return ESP_OK;
}
```

---

## 七、完整示例

### 示例1：WiFi凭证保存与读取

```c
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"

static const char *TAG = "NVS_WIFI";

typedef struct {
    char ssid[33];
    char password[65];
    bool configured;
} wifi_creds_t;

esp_err_t save_wifi_credentials(const char *ssid, const char *password)
{
    nvs_handle_t handle;
    esp_err_t err;
    
    err = nvs_open("wifi_storage", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS: %s", esp_err_to_name(err));
        return err;
    }
    
    err = nvs_set_str(handle, "ssid", ssid);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error saving SSID: %s", esp_err_to_name(err));
        nvs_close(handle);
        return err;
    }
    
    err = nvs_set_str(handle, "password", password);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error saving password: %s", esp_err_to_name(err));
        nvs_close(handle);
        return err;
    }
    
    err = nvs_set_u8(handle, "configured", 1);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error saving configured flag: %s", esp_err_to_name(err));
        nvs_close(handle);
        return err;
    }
    
    err = nvs_commit(handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error committing: %s", esp_err_to_name(err));
    } else {
        ESP_LOGI(TAG, "WiFi credentials saved successfully");
    }
    
    nvs_close(handle);
    return err;
}

esp_err_t load_wifi_credentials(wifi_creds_t *creds)
{
    nvs_handle_t handle;
    esp_err_t err;
    
    err = nvs_open("wifi_storage", NVS_READONLY, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "No WiFi credentials found");
        creds->configured = false;
        return err;
    }
    
    size_t len = sizeof(creds->ssid);
    err = nvs_get_str(handle, "ssid", creds->ssid, &len);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "SSID not found");
        nvs_close(handle);
        return err;
    }
    
    len = sizeof(creds->password);
    err = nvs_get_str(handle, "password", creds->password, &len);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Password not found");
        nvs_close(handle);
        return err;
    }
    
    uint8_t configured = 0;
    nvs_get_u8(handle, "configured", &configured);
    creds->configured = (configured == 1);
    
    nvs_close(handle);
    
    ESP_LOGI(TAG, "WiFi credentials loaded:");
    ESP_LOGI(TAG, "  SSID: %s", creds->ssid);
    ESP_LOGI(TAG, "  Configured: %s", creds->configured ? "Yes" : "No");
    
    return ESP_OK;
}

void app_main(void)
{
    // 初始化NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 尝试加载WiFi凭证
    wifi_creds_t creds;
    ret = load_wifi_credentials(&creds);
    
    if (ret != ESP_OK || !creds.configured) {
        ESP_LOGI(TAG, "No WiFi credentials, saving defaults...");
        save_wifi_credentials("MyHomeWiFi", "password123");
        
        // 重新加载
        load_wifi_credentials(&creds);
    }
    
    ESP_LOGI(TAG, "Ready to connect to: %s", creds.ssid);
}
```

---

### 示例2：设备配置参数管理

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_log.h"

static const char *TAG = "NVS_DEVICE";

typedef struct {
    uint32_t device_id;
    float calibration_factor;
    uint16_t sample_interval_ms;
    uint8_t debug_mode;
    char device_name[32];
} device_config_t;

// 默认配置
static const device_config_t default_config = {
    .device_id = 0x12345678,
    .calibration_factor = 1.0f,
    .sample_interval_ms = 1000,
    .debug_mode = 0,
    .device_name = "ESP32_Device"
};

static device_config_t current_config;

esp_err_t device_config_load(void)
{
    nvs_handle_t handle;
    esp_err_t err;
    
    err = nvs_open("device_cfg", NVS_READONLY, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "No saved config, using defaults");
        current_config = default_config;
        return err;
    }
    
    // 读取各项配置
    err = nvs_get_u32(handle, "device_id", &current_config.device_id);
    if (err != ESP_OK) current_config.device_id = default_config.device_id;
    
    size_t len = sizeof(float);
    err = nvs_get_blob(handle, "cal_factor", &current_config.calibration_factor, &len);
    if (err != ESP_OK) current_config.calibration_factor = default_config.calibration_factor;
    
    err = nvs_get_u16(handle, "interval", &current_config.sample_interval_ms);
    if (err != ESP_OK) current_config.sample_interval_ms = default_config.sample_interval_ms;
    
    err = nvs_get_u8(handle, "debug", &current_config.debug_mode);
    if (err != ESP_OK) current_config.debug_mode = default_config.debug_mode;
    
    len = sizeof(current_config.device_name);
    err = nvs_get_str(handle, "name", current_config.device_name, &len);
    if (err != ESP_OK) strcpy(current_config.device_name, default_config.device_name);
    
    nvs_close(handle);
    
    ESP_LOGI(TAG, "Config loaded:");
    ESP_LOGI(TAG, "  Device ID: 0x%08X", current_config.device_id);
    ESP_LOGI(TAG, "  Calibration: %.4f", current_config.calibration_factor);
    ESP_LOGI(TAG, "  Interval: %d ms", current_config.sample_interval_ms);
    ESP_LOGI(TAG, "  Debug: %s", current_config.debug_mode ? "ON" : "OFF");
    ESP_LOGI(TAG, "  Name: %s", current_config.device_name);
    
    return ESP_OK;
}

esp_err_t device_config_save(void)
{
    nvs_handle_t handle;
    esp_err_t err;
    
    err = nvs_open("device_cfg", NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Error opening NVS: %s", esp_err_to_name(err));
        return err;
    }
    
    nvs_set_u32(handle, "device_id", current_config.device_id);
    nvs_set_blob(handle, "cal_factor", &current_config.calibration_factor, sizeof(float));
    nvs_set_u16(handle, "interval", current_config.sample_interval_ms);
    nvs_set_u8(handle, "debug", current_config.debug_mode);
    nvs_set_str(handle, "name", current_config.device_name);
    
    err = nvs_commit(handle);
    nvs_close(handle);
    
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Config saved successfully");
    } else {
        ESP_LOGE(TAG, "Error saving config: %s", esp_err_to_name(err));
    }
    
    return err;
}

void device_config_print(void)
{
    ESP_LOGI(TAG, "Current Configuration:");
    ESP_LOGI(TAG, "======================");
    ESP_LOGI(TAG, "Device ID:     0x%08X", current_config.device_id);
    ESP_LOGI(TAG, "Calibration:   %.4f", current_config.calibration_factor);
    ESP_LOGI(TAG, "Interval:      %d ms", current_config.sample_interval_ms);
    ESP_LOGI(TAG, "Debug Mode:    %s", current_config.debug_mode ? "ON" : "OFF");
    ESP_LOGI(TAG, "Device Name:   %s", current_config.device_name);
    ESP_LOGI(TAG, "======================");
}

void app_main(void)
{
    // 初始化NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 加载配置
    device_config_load();
    device_config_print();
    
    // 修改配置
    current_config.calibration_factor = 1.025f;
    current_config.sample_interval_ms = 500;
    strcpy(current_config.device_name, "My_ESP32_Sensor");
    
    // 保存配置
    device_config_save();
    
    // 重新加载验证
    device_config_load();
    device_config_print();
}
```

---

## 附录：NVS API速查表

### 初始化

| API | 说明 |
|-----|------|
| `nvs_flash_init()` | 初始化NVS |
| `nvs_flash_init_partition()` | 初始化指定分区 |
| `nvs_flash_erase()` | 擦除默认分区 |
| `nvs_flash_erase_partition()` | 擦除指定分区 |

### 句柄管理

| API | 说明 |
|-----|------|
| `nvs_open()` | 打开命名空间 |
| `nvs_close()` | 关闭句柄 |

### 写入操作

| API | 说明 |
|-----|------|
| `nvs_set_i8/i16/i32/i64()` | 写入有符号整数 |
| `nvs_set_u8/u16/u32/u64()` | 写入无符号整数 |
| `nvs_set_str()` | 写入字符串 |
| `nvs_set_blob()` | 写入二进制数据 |
| `nvs_commit()` | 提交更改 |

### 读取操作

| API | 说明 |
|-----|------|
| `nvs_get_i8/i16/i32/i64()` | 读取有符号整数 |
| `nvs_get_u8/u16/u32/u64()` | 读取无符号整数 |
| `nvs_get_str()` | 读取字符串 |
| `nvs_get_blob()` | 读取二进制数据 |

### 管理操作

| API | 说明 |
|-----|------|
| `nvs_erase_key()` | 删除键 |
| `nvs_erase_all()` | 删除所有键 |
| `nvs_entry_find(partition, namespace, type, &it)` | 查找条目（v5.0+：返回esp_err_t） |
| `nvs_entry_next(&it)` | 下一个条目（v5.0+：返回esp_err_t） |
| `nvs_release_iterator(it)` | 释放迭代器 |
| `nvs_get_stats()` | 获取统计信息 |

### 错误码

| 错误码 | 说明 |
|--------|------|
| `ESP_OK` | 成功 |
| `ESP_ERR_NVS_NOT_FOUND` | 键不存在 |
| `ESP_ERR_NVS_NO_FREE_PAGES` | 无空闲页面 |
| `ESP_ERR_NVS_INVALID_NAME` | 无效命名空间 |
| `ESP_ERR_NVS_INVALID_LENGTH` | 长度无效 |
| `ESP_ERR_NVS_READ_ONLY` | 只读模式 |
