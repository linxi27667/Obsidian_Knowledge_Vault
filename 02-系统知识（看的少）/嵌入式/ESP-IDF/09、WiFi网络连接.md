# ESP-IDF WiFi网络连接 （无线局域网连接与网络配置）

## 核心概念

- **ESP32内置WiFi** - 支持2.4GHz 802.11 b/g/n协议
- **STA模式** - Station模式，连接路由器/AP
- **AP模式** - Access Point模式，作为热点供其他设备连接
- **STA+AP混合模式** - 同时作为客户端和热点

---

## 一、WiFi初始化

### 1.1 初始化流程

```c
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

static const char *TAG = "WIFI";

void wifi_init(void)
{
    // 1. 初始化NVS（WiFi需要）
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 2. 初始化TCP/IP栈
    ESP_ERROR_CHECK(esp_netif_init());
    
    // 3. 创建默认事件循环
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    // 4. 创建默认网络接口
    esp_netif_t *sta_netif = esp_netif_create_default_wifi_sta();
    assert(sta_netif);
    
    // 5. 初始化WiFi
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    ESP_LOGI(TAG, "WiFi initialized");
}
```

**初始化流程图：**

```
NVS初始化 ──> TCP/IP初始化 ──> 事件循环创建 ──> 网络接口创建 ──> WiFi初始化
    │              │                │                  │              │
    │              │                │                  │              │
    ▼              ▼                ▼                  ▼              ▼
┌─────────┐  ┌──────────┐    ┌──────────┐      ┌──────────┐   ┌──────────┐
│存储WiFi  │  │  网络栈   │    │ 事件分发  │      │ 网络接口  │   │ WiFi驱动 │
│配置数据  │  │         │    │ 系统     │      │ 管理     │   │         │
└─────────┘  └──────────┘    └──────────┘      └──────────┘   └──────────┘
```

---

### 1.2 事件处理注册

```c
// 定义事件处理函数
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
            case WIFI_EVENT_STA_START:
                ESP_LOGI(TAG, "WiFi STA started");
                esp_wifi_connect();
                break;
                
            case WIFI_EVENT_STA_CONNECTED:
                ESP_LOGI(TAG, "WiFi connected");
                break;
                
            case WIFI_EVENT_STA_DISCONNECTED:
                ESP_LOGI(TAG, "WiFi disconnected, retrying...");
                esp_wifi_connect();
                break;
                
            default:
                break;
        }
    } else if (event_base == IP_EVENT) {
        if (event_id == IP_EVENT_STA_GOT_IP) {
            ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
            ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        }
    }
}

// 注册事件处理
ESP_ERROR_CHECK(esp_event_handler_instance_register(
    WIFI_EVENT, 
    ESP_EVENT_ANY_ID,
    &wifi_event_handler,
    NULL,
    NULL));

ESP_ERROR_CHECK(esp_event_handler_instance_register(
    IP_EVENT,
    IP_EVENT_STA_GOT_IP,
    &wifi_event_handler,
    NULL,
    NULL));
```

---

## 二、STA模式

### 2.1 配置连接

```c
void wifi_sta_init(void)
{
    // 配置STA
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "YOUR_SSID",
            .password = "YOUR_PASSWORD",
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,  // 最低安全级别
            .sae_pwe_h2e = WPA3_SAE_PWE_BOTH,
        },
    };
    
    // 设置模式为STA
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    
    // 设置配置
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    
    // 启动WiFi
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi STA mode started, connecting to %s", wifi_config.sta.ssid);
}
```

> ⚠️ **v5.5+ 重要变更**：从v5.5开始，`esp_wifi_set_config()` 在WiFi连接阶段（connecting phase）调用时会返回错误。如果在连接过程中需要修改配置，请先调用 `esp_wifi_disconnect()` 断开连接，或等待 `WIFI_EVENT_STA_BEACON_TIMEOUT` 事件后再修改配置。

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `ssid` | 网络名称 | 你的WiFi名 |
| `password` | 密码 | 你的WiFi密码 |
| `authmode` | 认证模式 | `WIFI_AUTH_WPA2_PSK` |
| `scan_method` | 扫描方式 | `WIFI_ALL_CHANNEL_SCAN` |
| `sort_method` | 排序方式 | `WIFI_CONNECT_AP_BY_SIGNAL` |

---

### 2.2 扫描AP

```c
void wifi_scan(void)
{
    // 配置扫描参数
    wifi_scan_config_t scan_config = {
        .ssid = NULL,           // 扫描所有SSID
        .bssid = NULL,          // 扫描所有BSSID
        .channel = 0,           // 扫描所有信道
        .show_hidden = true,    // 显示隐藏SSID
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,  // 主动扫描
        .scan_time.active.min = 100,
        .scan_time.active.max = 300,
    };
    
    // 启动扫描
    ESP_ERROR_CHECK(esp_wifi_scan_start(&scan_config, true));  // true=阻塞模式
    
    // 获取AP数量
    uint16_t ap_count = 0;
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_num(&ap_count));
    ESP_LOGI(TAG, "Found %d APs", ap_count);
    
    // 获取AP列表
    wifi_ap_record_t *ap_list = (wifi_ap_record_t *)malloc(
        sizeof(wifi_ap_record_t) * ap_count);
    ESP_ERROR_CHECK(esp_wifi_scan_get_ap_records(&ap_count, ap_list));
    
    // 打印AP信息
    for (int i = 0; i < ap_count; i++) {
        ESP_LOGI(TAG, "AP %d: SSID=%s, RSSI=%d, Channel=%d, Auth=%d",
                 i + 1,
                 ap_list[i].ssid,
                 ap_list[i].rssi,
                 ap_list[i].primary,
                 ap_list[i].authmode);
    }
    
    free(ap_list);
}
```

---

### 2.3 连接与断开

```c
// 手动连接
void wifi_connect(void)
{
    ESP_ERROR_CHECK(esp_wifi_connect());
    ESP_LOGI(TAG, "Connecting...");
}

// 断开连接
void wifi_disconnect(void)
{
    ESP_ERROR_CHECK(esp_wifi_disconnect());
    ESP_LOGI(TAG, "Disconnected");
}

// 重新连接
void wifi_reconnect(void)
{
    wifi_disconnect();
    vTaskDelay(pdMS_TO_TICKS(100));
    wifi_connect();
}
```

---

## 三、AP模式

### 3.1 配置AP

```c
void wifi_ap_init(void)
{
    // 配置AP
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "ESP32_AP",
            .ssid_len = strlen("ESP32_AP"),
            .password = "12345678",           // 至少8位
            .max_connection = 4,              // 最大连接数
            .authmode = WIFI_AUTH_WPA2_PSK,   // 认证模式
            .channel = 6,                     // 信道
        },
    };
    
    // 设置模式为AP
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    
    // 设置配置
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    
    // 启动WiFi
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi AP mode started");
    ESP_LOGI(TAG, "SSID: %s", wifi_config.ap.ssid);
    ESP_LOGI(TAG, "Password: %s", wifi_config.ap.password);
}
```

---

### 3.2 获取已连接设备

```c
void wifi_ap_list_stations(void)
{
    wifi_sta_list_t station_list;
    ESP_ERROR_CHECK(esp_wifi_ap_get_sta_list(&station_list));
    
    ESP_LOGI(TAG, "Connected stations: %d", station_list.num);
    
    for (int i = 0; i < station_list.num; i++) {
        ESP_LOGI(TAG, "Station %d: MAC=" MACSTR ", RSSI=%d",
                 i + 1,
                 MAC2STR(station_list.sta[i].mac),
                 station_list.sta[i].rssi);
    }
}
```

---

## 四、STA+AP混合模式

### 4.1 混合模式配置

```c
void wifi_apsta_init(void)
{
    // 配置STA
    wifi_config_t sta_config = {
        .sta = {
            .ssid = "YOUR_HOME_WIFI",
            .password = "YOUR_PASSWORD",
        },
    };
    
    // 配置AP
    wifi_config_t ap_config = {
        .ap = {
            .ssid = "ESP32_Config",
            .password = "12345678",
            .max_connection = 2,
        },
    };
    
    // 设置为APSTA模式
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    
    // 设置STA配置
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta_config));
    
    // 设置AP配置
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    
    // 启动WiFi
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi APSTA mode started");
}
```

**混合模式网络架构：**

```
                    Internet
                       │
                       ▼
                ┌─────────────┐
                │   Router    │ 192.168.1.1
                │  (Internet) │
                └──────┬──────┘
                       │
            ┌──────────┴──────────┐
            │                     │
        STA连接               其他设备
     192.168.1.x            192.168.1.x
            │
            ▼
        ┌─────────┐
        │  ESP32  │
        │  APSTA  │
        │  模式   │
        └────┬────┘
             │
             │ AP热点
             │ 192.168.4.1
             │
      ┌──────┼──────┐
      │      │      │
   手机    平板    电脑
192.168.4.x
```

---

## 五、WiFi事件处理

### 5.1 WiFi事件类型

| 事件 | 说明 | 处理建议 |
|------|------|----------|
| `WIFI_EVENT_STA_START` | STA启动 | 调用`esp_wifi_connect()` |
| `WIFI_EVENT_STA_CONNECTED` | 连接成功 | 等待IP事件 |
| `WIFI_EVENT_STA_DISCONNECTED` | 断开连接 | 重连处理 |
| `WIFI_EVENT_STA_AUTHMODE_CHANGE` | 认证模式改变 | 更新安全配置 |
| `WIFI_EVENT_AP_START` | AP启动 | 开始服务 |
| `WIFI_EVENT_AP_STACONNECTED` | 设备连接 | 记录设备 |
| `WIFI_EVENT_AP_STADISCONNECTED` | 设备断开 | 清理记录 |

---

### 5.2 IP事件类型

| 事件 | 说明 |
|------|------|
| `IP_EVENT_STA_GOT_IP` | STA获取IP |
| `IP_EVENT_STA_LOST_IP` | STA丢失IP |
| `IP_EVENT_AP_STAIPASSIGNED` | AP分配IP给设备 |
| `IP_EVENT_GOT_IP6` | 获取IPv6 |

---

### 5.3 断开原因码

```c
void handle_disconnect_reason(uint8_t reason)
{
    switch (reason) {
        case WIFI_REASON_AUTH_EXPIRE:
            ESP_LOGW(TAG, "Auth expired");
            break;
        case WIFI_REASON_AUTH_FAIL:
            ESP_LOGW(TAG, "Auth failed (wrong password)");
            break;
        case WIFI_REASON_NO_AP_FOUND:
            ESP_LOGW(TAG, "AP not found");
            break;
        case WIFI_REASON_ASSOC_FAIL:
            ESP_LOGW(TAG, "Association failed");
            break;
        case WIFI_REASON_HANDSHAKE_TIMEOUT:
            ESP_LOGW(TAG, "Handshake timeout");
            break;
        default:
            ESP_LOGW(TAG, "Disconnect reason: %d", reason);
            break;
    }
}
```

---

## 六、低功耗模式

### 6.1 Modem-sleep

```c
// Modem-sleep：关闭WiFi射频，保持连接
void wifi_enable_modem_sleep(void)
{
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_MIN_MODEM));
    ESP_LOGI(TAG, "Modem sleep enabled");
}

// 关闭省电模式
void wifi_disable_sleep(void)
{
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
}
```

| 省电模式 | 说明 | 功耗 |
|----------|------|------|
| `WIFI_PS_NONE` | 无省电 | 高 |
| `WIFI_PS_MIN_MODEM` | 最小Modem sleep | 中 |
| `WIFI_PS_MAX_MODEM` | 最大Modem sleep | 低 |

---

### 6.2 深度睡眠与WiFi

```c
// 配置唤醒后自动连接
ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_FLASH));

// 进入深度睡眠前保存WiFi配置
esp_wifi_stop();
esp_wifi_set_ps(WIFI_PS_NONE);

// 配置定时唤醒
esp_sleep_enable_timer_wakeup(10 * 1000 * 1000);  // 10秒

// 进入深度睡眠
esp_deep_sleep_start();

// 唤醒后WiFi自动恢复连接
```

---

## 七、完整示例

### 示例1：智能配网（SmartConfig）

```c
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_smartconfig.h"

static const char *TAG = "SMARTCONFIG";

// 事件组
static EventGroupHandle_t s_wifi_event_group;

// 事件位
#define WIFI_CONNECTED_BIT  BIT0
#define WIFI_FAIL_BIT       BIT1
#define SMARTCONFIG_DONE_BIT BIT2

static void smartconfig_task(void *parm);

static void event_handler(void *arg, esp_event_base_t event_base,
                          int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        xTaskCreate(smartconfig_task, "smartconfig_task", 4096, NULL, 3, NULL);
    } else if (event_base == WIFI_EVENT && 
               event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ESP_LOGI(TAG, "Got IP address");
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == SC_EVENT) {
        if (event_id == SC_EVENT_SCAN_DONE) {
            ESP_LOGI(TAG, "SmartConfig scan done");
        } else if (event_id == SC_EVENT_FOUND_CHANNEL) {
            ESP_LOGI(TAG, "SmartConfig found channel");
        } else if (event_id == SC_EVENT_GOT_SSID_PSWD) {
            ESP_LOGI(TAG, "SmartConfig got SSID and password");
            
            smartconfig_event_got_ssid_pswd_t *evt = 
                (smartconfig_event_got_ssid_pswd_t *)event_data;
            
            wifi_config_t wifi_config;
            uint8_t ssid[33] = {0};
            uint8_t password[65] = {0};
            
            memcpy(ssid, evt->ssid, sizeof(evt->ssid));
            memcpy(password, evt->password, sizeof(evt->password));
            
            ESP_LOGI(TAG, "SSID: %s", ssid);
            ESP_LOGI(TAG, "PASSWORD: %s", password);
            
            // 保存配置并连接
            bzero(&wifi_config, sizeof(wifi_config_t));
            memcpy(wifi_config.sta.ssid, evt->ssid, sizeof(wifi_config.sta.ssid));
            memcpy(wifi_config.sta.password, evt->password, 
                   sizeof(wifi_config.sta.password));
            
            ESP_ERROR_CHECK(esp_wifi_disconnect());
            ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
            ESP_ERROR_CHECK(esp_wifi_connect());
        } else if (event_id == SC_EVENT_SEND_ACK_DONE) {
            ESP_LOGI(TAG, "SmartConfig send ack done");
            xEventGroupSetBits(s_wifi_event_group, SMARTCONFIG_DONE_BIT);
        }
    }
}

static void smartconfig_task(void *parm)
{
    ESP_ERROR_CHECK(esp_smartconfig_set_type(SC_TYPE_ESPTOUCH));
    
    smartconfig_start_config_t cfg = SMARTCONFIG_START_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_smartconfig_start(&cfg));
    
    ESP_LOGI(TAG, "SmartConfig started, use ESP Touch app to configure");
    
    // 等待配网完成
    EventBits_t uxBits = xEventGroupWaitBits(
        s_wifi_event_group,
        WIFI_CONNECTED_BIT | SMARTCONFIG_DONE_BIT,
        true, false, portMAX_DELAY);
    
    if (uxBits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi connected to AP");
    }
    
    esp_smartconfig_stop();
    vTaskDelete(NULL);
}

void app_main(void)
{
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    s_wifi_event_group = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    // 注册事件处理
    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        SC_EVENT, ESP_EVENT_ANY_ID, &event_handler, NULL));
    
    // 启动WiFi
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
}
```

---

### 示例2：WiFi连接状态指示灯

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "driver/gpio.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"

static const char *TAG = "WIFI_LED";

#define LED_GPIO        GPIO_NUM_2

static EventGroupHandle_t wifi_event_group;
#define WIFI_CONNECTED_BIT  BIT0

static void led_task(void *pvParameters)
{
    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);
    
    while (1) {
        EventBits_t bits = xEventGroupGetBits(wifi_event_group);
        
        if (bits & WIFI_CONNECTED_BIT) {
            // 已连接：LED常亮
            gpio_set_level(LED_GPIO, 1);
            vTaskDelay(pdMS_TO_TICKS(1000));
        } else {
            // 未连接：LED闪烁
            gpio_set_level(LED_GPIO, 1);
            vTaskDelay(pdMS_TO_TICKS(100));
            gpio_set_level(LED_GPIO, 0);
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && 
               event_id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
        esp_wifi_connect();
        ESP_LOGI(TAG, "Retry connecting...");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    wifi_event_group = xEventGroupCreate();
    
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "YOUR_SSID",
            .password = "YOUR_PASSWORD",
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    xTaskCreate(led_task, "led_task", 1024, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "WiFi LED indicator started");
}
```

---

### 示例3：自动重连与断线检测

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"

static const char *TAG = "WIFI_RECONNECT";

#define WIFI_CONNECTED_BIT      BIT0
#define WIFI_DISCONNECTED_BIT   BIT1

static EventGroupHandle_t wifi_event_group;
static int s_retry_num = 0;
static const int MAX_RETRY = 5;

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "WiFi started, connecting...");
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && 
               event_id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t *event = 
            (wifi_event_sta_disconnected_t *)event_data;
        
        ESP_LOGW(TAG, "Disconnected, reason: %d", event->reason);
        
        if (s_retry_num < MAX_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "Retry %d/%d", s_retry_num, MAX_RETRY);
        } else {
            ESP_LOGE(TAG, "Max retries reached, giving up");
            xEventGroupSetBits(wifi_event_group, WIFI_DISCONNECTED_BIT);
        }
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Connected! IP: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

bool wifi_wait_connected(uint32_t timeout_ms)
{
    EventBits_t bits = xEventGroupWaitBits(
        wifi_event_group,
        WIFI_CONNECTED_BIT | WIFI_DISCONNECTED_BIT,
        pdFALSE, pdFALSE,
        pdMS_TO_TICKS(timeout_ms));
    
    return (bits & WIFI_CONNECTED_BIT) != 0;
}

void app_main(void)
{
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    wifi_event_group = xEventGroupCreate();
    
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "YOUR_SSID",
            .password = "YOUR_PASSWORD",
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    // 等待连接（30秒超时）
    if (wifi_wait_connected(30000)) {
        ESP_LOGI(TAG, "WiFi connection established");
    } else {
        ESP_LOGE(TAG, "Failed to connect to WiFi");
    }
}
```

---

## 附录：WiFi API速查表

### 初始化与配置

| API | 说明 |
|-----|------|
| `esp_wifi_init()` | 初始化WiFi |
| `esp_wifi_deinit()` | 反初始化WiFi |
| `esp_wifi_set_mode()` | 设置WiFi模式 |
| `esp_wifi_get_mode()` | 获取WiFi模式 |
| `esp_wifi_set_config()` | 设置配置 |
| `esp_wifi_get_config()` | 获取配置 |
| `esp_wifi_start()` | 启动WiFi |
| `esp_wifi_stop()` | 停止WiFi |

### 连接管理

| API | 说明 |
|-----|------|
| `esp_wifi_connect()` | 连接AP |
| `esp_wifi_disconnect()` | 断开连接 |
| `esp_wifi_scan_start()` | 开始扫描 |
| `esp_wifi_scan_get_ap_records()` | 获取扫描结果 |
| `esp_wifi_set_ps()` | 设置省电模式 |

### 信息获取

| API | 说明 |
|-----|------|
| `esp_wifi_sta_get_ap_info()` | 获取已连接AP信息 |
| `esp_wifi_ap_get_sta_list()` | 获取已连接设备列表 |
| `esp_wifi_get_mac()` | 获取MAC地址 |
| `esp_wifi_set_mac()` | 设置MAC地址 |

### SmartConfig

| API | 说明 |
|-----|------|
| `esp_smartconfig_start()` | 开始SmartConfig |
| `esp_smartconfig_stop()` | 停止SmartConfig |
| `esp_smartconfig_set_type()` | 设置配网类型 |

### WiFi模式

| 模式 | 说明 |
|------|------|
| `WIFI_MODE_NULL` | 空模式 |
| `WIFI_MODE_STA` | STA模式 |
| `WIFI_MODE_AP` | AP模式 |
| `WIFI_MODE_APSTA` | AP+STA模式 |
