# ESP-IDF OTA空中升级 （固件远程更新与版本管理）

## 核心概念

- **OTA** - Over-The-Air，通过网络更新设备固件
- **双分区方案** - OTA_0和OTA_1两个应用分区，支持固件回滚
- **OTA数据分区** - 存储OTA状态和启动配置
- **安全启动** - 固件签名验证，防止非法固件运行

---

## 一、OTA工作原理

### 1.1 OTA分区布局

```
Flash布局（支持OTA）：

0x000000 ┌─────────────────────┐
         │     Bootloader      │  32KB
0x008000 ├─────────────────────┤
         │   Partition Table   │  4KB
0x009000 ├─────────────────────┤
         │        NVS          │  24KB
0x00F000 ├─────────────────────┤
         │      OTA Data       │  8KB (OTA状态)
0x010000 ├─────────────────────┤
         │                     │
         │   factory app       │  1MB (出厂固件)
         │                     │
0x110000 ├─────────────────────┤
         │                     │
         │   OTA_0 (app0)      │  1MB (OTA分区0)
         │                     │
0x210000 ├─────────────────────┤
         │                     │
         │   OTA_1 (app1)      │  1MB (OTA分区1)
         │                     │
0x310000 ├─────────────────────┤
         │      Storage        │  (可选存储)
0x400000 └─────────────────────┘

启动流程：
1. Bootloader读取OTA Data分区
2. 确定启动哪个OTA分区（OTA_0或OTA_1）
3. 验证固件有效性
4. 跳转到应用分区执行
```

---

### 1.2 固件切换原理

```
OTA更新流程：

当前运行: OTA_0                    新固件写入: OTA_1
┌──────────┐                       ┌──────────┐
│  旧固件   │ ←──────────────────  │  新固件   │
│  v1.0    │    下载并写入         │  v1.1    │
│  RUNNING │                       │  READY   │
└──────────┘                       └──────────┘
       │                                  │
       │    重启后                         │
       ▼                                  ▼
┌──────────┐                       ┌──────────┐
│  旧固件   │                       │  新固件   │
│  v1.0    │                       │  v1.1    │
│  STANDBY │ ←──────────────────  │  RUNNING │
└──────────┘                       └──────────┘

回滚机制：
如果新固件异常，下次启动自动回滚到旧版本
```

---

## 二、OTA配置

### 2.1 分区表配置

```csv
# partitions.csv - 支持OTA的分区表
# Name,   Type, SubType, Offset,  Size,     Flags
nvs,      data, nvs,     0x9000,  0x6000,
otadata,  data, ota,     0xf000,  0x2000,
app0,     app,  ota_0,   0x10000, 0x1F0000,  # OTA分区0
app1,     app,  ota_1,   0x200000,0x1F0000,  # OTA分区1
spiffs,   data, spiffs,  0x3F0000,0x10000,
```

---

### 2.2 使能OTA组件

```bash
# menuconfig配置
idf.py menuconfig

# 路径：
# Component config -> OTA -> [ ] OTA 

# 或者修改 sdkconfig.defaults:
CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y
CONFIG_PARTITION_TABLE_TWO_OTA=y
CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y
```

---

## 三、HTTP OTA实现

### 3.1 基本OTA流程

```c
#include "esp_ota_ops.h"
#include "esp_http_client.h"
#include "esp_log.h"

static const char *TAG = "OTA";

#define OTA_URL "http://192.168.1.100:8080/firmware.bin"

void ota_update_task(void *pvParameter)
{
    esp_err_t ret;
    
    ESP_LOGI(TAG, "Starting OTA update...");
    
    // 1. 配置HTTP客户端
    esp_http_client_config_t config = {
        .url = OTA_URL,
        .timeout_ms = 10000,
        .keep_alive_enable = true,
    };
    
    // 2. 执行OTA
    ret = esp_https_ota(&config);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "OTA successful, restarting...");
        esp_restart();
    } else {
        ESP_LOGE(TAG, "OTA failed: %s", esp_err_to_name(ret));
    }
    
    vTaskDelete(NULL);
}
```

---

### 3.2 带进度显示的OTA

```c
#include "esp_ota_ops.h"
#include "esp_http_client.h"
#include "esp_log.h"

static const char *TAG = "OTA_ADVANCED";

// OTA进度回调
void ota_progress_callback(esp_https_ota_handle_t handle)
{
    static int last_percentage = -1;
    int image_size = esp_https_ota_get_image_size(handle);
    int image_read = esp_https_ota_get_image_len_read(handle);
    
    if (image_size > 0) {
        int percentage = (image_read * 100) / image_size;
        if (percentage != last_percentage) {
            ESP_LOGI(TAG, "OTA Progress: %d%% (%d/%d bytes)", 
                     percentage, image_read, image_size);
            last_percentage = percentage;
        }
    }
}

void advanced_ota_task(void *pvParameter)
{
    esp_err_t ret;
    
    ESP_LOGI(TAG, "Starting Advanced OTA...");
    
    esp_http_client_config_t config = {
        .url = OTA_URL,
        .timeout_ms = 10000,
        .keep_alive_enable = true,
    };
    
    esp_https_ota_config_t ota_config = {
        .http_config = &config,
    };
    
    esp_https_ota_handle_t https_ota_handle = NULL;
    
    // 开始OTA
    ret = esp_https_ota_begin(&ota_config, &https_ota_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA begin failed: %s", esp_err_to_name(ret));
        goto ota_end;
    }
    
    // 循环读取和写入
    while (1) {
        ret = esp_https_ota_perform(https_ota_handle);
        if (ret != ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            break;
        }
        
        // 显示进度
        ota_progress_callback(https_ota_handle);
        
        // 可以在这里添加看门狗喂狗
        // esp_task_wdt_reset();
    }
    
    // 检查完成状态
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA perform failed: %s", esp_err_to_name(ret));
        goto ota_end;
    }
    
    // 完成OTA
    ret = esp_https_ota_finish(https_ota_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA finish failed: %s", esp_err_to_name(ret));
        goto ota_end;
    }
    
    ESP_LOGI(TAG, "OTA successful!");
    ESP_LOGI(TAG, "Prepare to restart system!");
    
    // 重启前延时，确保日志输出
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    
ota_end:
    if (https_ota_handle != NULL) {
        esp_https_ota_abort(https_ota_handle);
    }
    vTaskDelete(NULL);
}
```

---

## 四、OTA升级流程

### 4.1 标准OTA流程

```c
// 完整的OTA流程函数
esp_err_t do_ta_update(const char *url)
{
    ESP_LOGI(TAG, "Starting OTA from: %s", url);
    
    // 1. 获取当前分区信息
    const esp_partition_t *running = esp_ota_get_running_partition();
    ESP_LOGI(TAG, "Running partition: %s", running->label);
    
    // 2. 获取更新分区
    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    ESP_LOGI(TAG, "Writing to partition: %s (type: 0x%x, subtype: 0x%x, offset: 0x%x)",
             update_partition->label, 
             update_partition->type, 
             update_partition->subtype,
             update_partition->address);
    
    // 3. 开始OTA
    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = 10000,
    };
    
    esp_err_t ret = esp_https_ota(&config);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "OTA completed successfully");
        
        // 4. 验证新固件
        if (esp_ota_check_chunk_hash() == ESP_OK) {
            ESP_LOGI(TAG, "Firmware hash verified");
        }
        
        return ESP_OK;
    } else {
        ESP_LOGE(TAG, "OTA failed: %s", esp_err_to_name(ret));
        return ret;
    }
}
```

---

### 4.2 手动OTA流程

```c
// 手动控制OTA的每个步骤
esp_err_t manual_ota_update(const char *url)
{
    esp_err_t ret;
    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = 10000,
    };
    
    // 1. 开始OTA会话
    esp_https_ota_handle_t ota_handle = NULL;
    ret = esp_https_ota_begin(&config, &ota_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA begin failed");
        return ret;
    }
    
    // 2. 执行OTA（循环读取）
    while (1) {
        ret = esp_https_ota_perform(ota_handle);
        
        if (ret == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
            // 继续下载
            ESP_LOGI(TAG, "Downloaded: %d bytes", 
                     esp_https_ota_get_image_len_read(ota_handle));
        } else {
            // 完成或出错
            break;
        }
    }
    
    // 3. 检查是否成功
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA perform failed");
        esp_https_ota_abort(ota_handle);
        return ret;
    }
    
    // 4. 完成OTA
    ret = esp_https_ota_finish(ota_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "OTA finish failed");
        return ret;
    }
    
    ESP_LOGI(TAG, "OTA successful!");
    return ESP_OK;
}
```

---

## 五、OTA回滚机制

### 5.1 启用回滚

```c
// menuconfig中启用:
// CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y

// 代码中使用:
#include "esp_ota_ops.h"

// 标记当前固件有效
void mark_app_valid(void)
{
    esp_err_t ret = esp_ota_mark_app_valid_cancel_rollback();
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "App marked as valid");
    } else {
        ESP_LOGE(TAG, "Failed to mark app valid: %s", esp_err_to_name(ret));
    }
}
```

---

### 5.2 回滚状态检查

```c
void check_rollback_status(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;
    
    if (esp_ota_get_state_partition(running, &ota_state) == ESP_OK) {
        switch (ota_state) {
            case ESP_OTA_IMG_PENDING_VERIFY:
                ESP_LOGI(TAG, "Running firmware is pending verification");
                // 需要验证后调用 esp_ota_mark_app_valid_cancel_rollback()
                break;
                
            case ESP_OTA_IMG_VALID:
                ESP_LOGI(TAG, "Running firmware is valid");
                break;
                
            case ESP_OTA_IMG_INVALID:
                ESP_LOGW(TAG, "Running firmware is marked invalid");
                break;
                
            case ESP_OTA_IMG_ABORTED:
                ESP_LOGW(TAG, "Running firmware was aborted");
                break;
                
            case ESP_OTA_IMG_NEW:
                ESP_LOGI(TAG, "Running firmware is new");
                break;
                
            default:
                ESP_LOGW(TAG, "Unknown OTA state");
                break;
        }
    }
}
```

---

### 5.3 自动回滚验证

```c
void app_main(void)
{
    // 初始化
    // ...
    
    // 检查OTA状态
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;
    
    if (esp_ota_get_state_partition(running, &ota_state) == ESP_OK) {
        if (ota_state == ESP_OTA_IMG_PENDING_VERIFY) {
            ESP_LOGI(TAG, "First boot after OTA, running diagnostics...");
            
            // 运行自检
            bool diagnostics_ok = run_diagnostics();
            
            if (diagnostics_ok) {
                ESP_LOGI(TAG, "Diagnostics passed, confirming OTA");
                esp_ota_mark_app_valid_cancel_rollback();
            } else {
                ESP_LOGE(TAG, "Diagnostics failed, rolling back");
                esp_ota_mark_app_invalid_rollback_and_reboot();
            }
        }
    }
    
    // 继续正常运行
    // ...
}

bool run_diagnostics(void)
{
    // 检查关键功能
    // - WiFi连接
    // - 传感器读取
    // - 网络通信
    // ...
    
    return true;  // 或 false
}
```

---

## 六、OTA安全

### 6.1 HTTPS OTA

```c
// 使用HTTPS进行安全OTA
esp_http_client_config_t config = {
    .url = "https://example.com/firmware.bin",
    .timeout_ms = 10000,
    
    // 证书配置（推荐）
    .cert_pem = server_cert_pem_start,  // 服务器证书
    
    // 或禁用证书验证（不推荐用于生产）
    // .skip_cert_common_name_check = true,
};

esp_err_t ret = esp_https_ota(&config);
```

---

### 6.2 固件签名验证

```c
// 启用安全启动和签名验证（menuconfig）
// Security features -> Enable signature verification

// 代码中检查签名
#include "esp_secure_boot.h"

void verify_firmware_signature(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    
    esp_err_t ret = esp_secure_boot_verify_signature(running->address, 
                                                      running->size);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Firmware signature verified");
    } else {
        ESP_LOGE(TAG, "Firmware signature verification failed!");
    }
}
```

---

## 七、完整示例

### 示例1：HTTP OTA升级实现

```c
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "nvs_flash.h"

static const char *TAG = "OTA_EXAMPLE";

#define OTA_URL "http://192.168.1.100:8080/firmware.bin"

static EventGroupHandle_t ota_event_group;
#define OTA_START_BIT       BIT0
#define OTA_SUCCESS_BIT     BIT1
#define OTA_FAIL_BIT        BIT2

static void ota_task(void *pvParameter)
{
    ESP_LOGI(TAG, "Starting OTA task");
    
    // 等待OTA启动信号
    EventBits_t bits = xEventGroupWaitBits(
        ota_event_group,
        OTA_START_BIT,
        pdTRUE, pdFALSE, portMAX_DELAY);
    
    if (!(bits & OTA_START_BIT)) {
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(TAG, "Beginning OTA download from %s", OTA_URL);
    
    esp_http_client_config_t config = {
        .url = OTA_URL,
        .timeout_ms = 10000,
        .keep_alive_enable = true,
    };
    
    esp_err_t ret = esp_https_ota(&config);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "OTA successful!");
        xEventGroupSetBits(ota_event_group, OTA_SUCCESS_BIT);
        
        // 延时确保日志输出
        vTaskDelay(pdMS_TO_TICKS(1000));
        esp_restart();
    } else {
        ESP_LOGE(TAG, "OTA failed: %s", esp_err_to_name(ret));
        xEventGroupSetBits(ota_event_group, OTA_FAIL_BIT);
    }
    
    vTaskDelete(NULL);
}

void start_ota(void)
{
    xEventGroupSetBits(ota_event_group, OTA_START_BIT);
}

void check_firmware_version(void)
{
    const esp_partition_t *running = esp_ota_get_running_partition();
    esp_app_desc_t running_app_info;
    
    if (esp_ota_get_partition_description(running, &running_app_info) == ESP_OK) {
        ESP_LOGI(TAG, "Running firmware version: %s", running_app_info.version);
        ESP_LOGI(TAG, "Project name: %s", running_app_info.project_name);
        ESP_LOGI(TAG, "Compile time: %s %s", running_app_info.date, running_app_info.time);
    }
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
    
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    // 创建事件组
    ota_event_group = xEventGroupCreate();
    
    // 检查当前固件信息
    check_firmware_version();
    
    // 检查回滚状态
    check_rollback_status();
    
    // 创建OTA任务
    xTaskCreate(&ota_task, "ota_task", 8192, NULL, 5, NULL);
    
    // 模拟触发OTA（实际应用中可以由命令、HTTP请求等触发）
    vTaskDelay(pdMS_TO_TICKS(5000));
    ESP_LOGI(TAG, "Triggering OTA...");
    start_ota();
    
    // 等待OTA结果
    bits = xEventGroupWaitBits(
        ota_event_group,
        OTA_SUCCESS_BIT | OTA_FAIL_BIT,
        pdTRUE, pdFALSE, pdMS_TO_TICKS(120000));
    
    if (bits & OTA_SUCCESS_BIT) {
        ESP_LOGI(TAG, "OTA will restart system");
    } else if (bits & OTA_FAIL_BIT) {
        ESP_LOGE(TAG, "OTA failed");
    } else {
        ESP_LOGW(TAG, "OTA timeout");
    }
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

### 示例2：带版本检查的OTA

```c
#include <string.h>
#include <stdlib.h>
#include "cJSON.h"
#include "esp_log.h"
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "esp_ota_ops.h"

static const char *TAG = "OTA_VERSION";

#define VERSION_URL "http://192.168.1.100:8080/version.json"
#define FIRMWARE_URL "http://192.168.1.100:8080/firmware.bin"

// 当前固件版本
#define CURRENT_VERSION "1.0.0"

typedef struct {
    char version[16];
    char url[128];
    char changelog[256];
} firmware_info_t;

esp_err_t fetch_version_info(firmware_info_t *info)
{
    char response_buffer[512] = {0};
    
    esp_http_client_config_t config = {
        .url = VERSION_URL,
        .timeout_ms = 5000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_http_client_set_method(client, HTTP_METHOD_GET);
    
    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open HTTP connection");
        esp_http_client_cleanup(client);
        return err;
    }
    
    int content_length = esp_http_client_fetch_headers(client);
    if (content_length > 0 && content_length < sizeof(response_buffer)) {
        int read_len = esp_http_client_read(client, response_buffer, content_length);
        response_buffer[read_len] = '\0';
    }
    
    esp_http_client_close(client);
    esp_http_client_cleanup(client);
    
    // 解析JSON
    cJSON *root = cJSON_Parse(response_buffer);
    if (root == NULL) {
        ESP_LOGE(TAG, "Failed to parse JSON");
        return ESP_FAIL;
    }
    
    cJSON *version = cJSON_GetObjectItem(root, "version");
    cJSON *url = cJSON_GetObjectItem(root, "url");
    cJSON *changelog = cJSON_GetObjectItem(root, "changelog");
    
    if (version && url) {
        strncpy(info->version, version->valuestring, sizeof(info->version));
        strncpy(info->url, url->valuestring, sizeof(info->url));
        if (changelog) {
            strncpy(info->changelog, changelog->valuestring, sizeof(info->changelog));
        }
    }
    
    cJSON_Delete(root);
    return ESP_OK;
}

bool version_compare(const char *current, const char *new)
{
    // 简单版本比较 (1.0.0 vs 1.1.0)
    int cur[3], neu[3];
    sscanf(current, "%d.%d.%d", &cur[0], &cur[1], &cur[2]);
    sscanf(new, "%d.%d.%d", &neu[0], &neu[1], &neu[2]);
    
    for (int i = 0; i < 3; i++) {
        if (neu[i] > cur[i]) return true;
        if (neu[i] < cur[i]) return false;
    }
    return false;  // 版本相同
}

void ota_with_version_check(void)
{
    firmware_info_t info = {0};
    
    ESP_LOGI(TAG, "Checking for updates...");
    ESP_LOGI(TAG, "Current version: %s", CURRENT_VERSION);
    
    if (fetch_version_info(&info) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to fetch version info");
        return;
    }
    
    ESP_LOGI(TAG, "Available version: %s", info.version);
    ESP_LOGI(TAG, "Changelog: %s", info.changelog);
    
    if (version_compare(CURRENT_VERSION, info.version)) {
        ESP_LOGI(TAG, "New version available, starting OTA...");
        
        esp_http_client_config_t config = {
            .url = info.url,
            .timeout_ms = 10000,
        };
        
        esp_err_t ret = esp_https_ota(&config);
        if (ret == ESP_OK) {
            ESP_LOGI(TAG, "OTA successful, restarting...");
            esp_restart();
        } else {
            ESP_LOGE(TAG, "OTA failed: %s", esp_err_to_name(ret));
        }
    } else {
        ESP_LOGI(TAG, "Already running latest version");
    }
}
```

---

## 附录：OTA API速查表

### OTA操作

| API | 说明 |
|-----|------|
| `esp_https_ota()` | 简化OTA接口 |
| `esp_https_ota_begin()` | 开始OTA |
| `esp_https_ota_perform()` | 执行OTA |
| `esp_https_ota_finish()` | 完成OTA |
| `esp_https_ota_abort()` | 中止OTA |
| `esp_https_ota_get_image_len_read()` | 获取已下载大小 |
| `esp_https_ota_get_image_size()` | 获取固件总大小 |

### 分区操作

| API | 说明 |
|-----|------|
| `esp_ota_get_running_partition()` | 获取当前运行分区 |
| `esp_ota_get_next_update_partition()` | 获取下一个更新分区 |
| `esp_ota_set_boot_partition()` | 设置启动分区 |
| `esp_ota_get_boot_partition()` | 获取启动分区 |
| `esp_ota_erase_last_boot_app_partition()` | 擦除上次启动分区 |

### 回滚操作

| API | 说明 |
|-----|------|
| `esp_ota_mark_app_valid_cancel_rollback()` | 标记有效，取消回滚 |
| `esp_ota_mark_app_invalid_rollback_and_reboot()` | 标记无效，回滚重启 |
| `esp_ota_get_state_partition()` | 获取分区OTA状态 |

### 信息获取

| API | 说明 |
|-----|------|
| `esp_ota_get_partition_description()` | 获取分区描述 |
| `esp_ota_check_chunk_hash()` | 校验固件哈希 |
| `esp_ota_write()` | 写入OTA数据 |
| `esp_ota_end()` | 结束OTA写入 |

### OTA状态

| 状态 | 说明 |
|------|------|
| `ESP_OTA_IMG_NEW` | 新固件 |
| `ESP_OTA_IMG_PENDING_VERIFY` | 等待验证 |
| `ESP_OTA_IMG_VALID` | 已验证有效 |
| `ESP_OTA_IMG_INVALID` | 无效 |
| `ESP_OTA_IMG_ABORTED` | 已中止 |
| `ESP_OTA_IMG_UNDEFINED` | 未定义 |
