# ESP32无线通信详解

> **核心概念**：WiFi STA/AP、SmartConfig、BLE GATT、ESP-NOW、Mesh、MQTT over WiFi
> **芯片支持**：ESP32 / ESP32-S2 / ESP32-S3 / ESP32-C3 / ESP32-C6 / ESP32-H2
> **开发框架**：ESP-IDF v5.x

---

## 1. WiFi基础

ESP32内置WiFi模块，支持802.11 b/g/n协议，工作在2.4GHz频段（ESP32-C6支持5GHz WiFi 6）。WiFi子系统支持Station（STA）、SoftAP和STA+AP共存三种模式。

### 1.1 WiFi STA模式

STA（Station）模式是ESP32最常见的工作方式，作为客户端连接到已有的路由器/AP。

**基本工作流程：**
1. 初始化WiFi子系统（`esp_wifi_init()`）
2. 设置WiFi模式为STA（`esp_wifi_set_mode(WIFI_MODE_STA)`）
3. 配置SSID和密码
4. 启动WiFi（`esp_wifi_start()`）
5. 连接AP（`esp_wifi_connect()`）
6. 等待`WIFI_EVENT_STA_CONNECTED`和`IP_EVENT_STA_GOT_IP`事件

**扫描与连接AP：**

WiFi扫描可以发现周围可用的接入点，获取SSID、RSSI、加密方式等信息。

```c
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "string.h"

static const char *TAG = "wifi_scan";

// 扫描周围WiFi
void wifi_scan(void)
{
    wifi_scan_config_t scan_config = {
        .ssid = NULL,           // 扫描所有SSID
        .bssid = NULL,          // 扫描所有BSSID
        .channel = 0,           // 扫描所有信道
        .show_hidden = true,    // 显示隐藏SSID
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,
        .scan_time.active = {
            .min = 100,
            .max = 300,
        },
    };

    ESP_ERROR_CHECK(esp_wifi_scan_start(&scan_config, true));  // 阻塞扫描

    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);
    ESP_LOGI(TAG, "发现 %d 个AP", ap_count);

    if (ap_count > 0) {
        wifi_ap_record_t *ap_list = malloc(sizeof(wifi_ap_record_t) * ap_count);
        esp_wifi_scan_get_ap_records(&ap_count, ap_list);

        for (int i = 0; i < ap_count; i++) {
            ESP_LOGI(TAG, "SSID: %-32s | RSSI: %d | 信道: %d | 加密: %d",
                     ap_list[i].ssid,
                     ap_list[i].rssi,
                     ap_list[i].primary,
                     ap_list[i].authmode);
        }
        free(ap_list);
    }
}
```

**SSID/密码配置：**

```c
// STA配置结构体
wifi_config_t wifi_sta_config = {
    .sta = {
        .ssid = "MyWiFi",               // 最长32字节
        .password = "mypassword123",     // 最长64字节
        .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        .sae_pwe_h2e = WPA3_SAE_PWE_BOTH,  // WPA3支持
    },
};

// 应用配置
esp_wifi_set_mode(WIFI_MODE_STA);
esp_wifi_set_config(WIFI_IF_STA, &wifi_sta_config);
```

**静态IP/DHCP：**

默认使用DHCP自动获取IP。如需静态IP：

```c
#include "esp_netif.h"

// 关闭DHCP客户端
esp_netif_t *sta_netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
esp_netif_dhcpc_stop(sta_netif);

// 设置静态IP
esp_netif_ip_info_t ip_info = {
    .ip.addr = esp_ip4addr_aton("192.168.1.100"),
    .netmask.addr = esp_ip4addr_aton("255.255.255.0"),
    .gw.addr = esp_ip4addr_aton("192.168.1.1"),
};
esp_netif_set_ip_info(sta_netif, &ip_info);

// 设置DNS服务器
esp_netif_dns_info_t dns_info = {
    .ip.u_addr.ip4.addr = esp_ip4addr_aton("8.8.8.8"),
    .ip.type = ESP_IPADDR_TYPE_V4,
};
esp_netif_set_dns_info(sta_netif, ESP_NETIF_DNS_MAIN, &dns_info);
```

**断线重连机制：**

```c
#include "esp_event.h"

static int s_retry_num = 0;
#define MAXIMUM_RETRY 5

static void event_handler(void *arg, esp_event_base_t event_base,
                          int32_t event_id, void *event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < MAXIMUM_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "第%d次重连...", s_retry_num);
        } else {
            ESP_LOGE(TAG, "超过最大重连次数，停止重连");
            // 可在此触发配网流程或进入低功耗模式
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "获取IP: " IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;  // 重置重连计数
    }
}
```

**信号强度(RSSI)获取：**

```c
wifi_ap_record_t ap_info;
if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK) {
    ESP_LOGI(TAG, "当前AP RSSI: %d dBm", ap_info.rssi);
    // RSSI参考值：
    // -30 dBm  极好（信号满格）
    // -67 dBm  良好（视频通话）
    // -70 dBm  一般（网页浏览）
    // -80 dBm  较差（基本连接）
    // -90 dBm  极差（几乎断开）
}
```

### 1.2 WiFi AP模式

AP（Access Point）模式使ESP32自身成为热点，允许其他设备连接。

**软AP配置：**

```c
#include "esp_wifi.h"
#include "esp_netif.h"

void wifi_ap_init(void)
{
    // 创建默认AP网络接口
    esp_netif_create_default_wifi_ap();

    wifi_config_t wifi_ap_config = {
        .ap = {
            .ssid = "ESP32-AP",             // 热点名称
            .ssid_len = strlen("ESP32-AP"),
            .channel = 1,                    // WiFi信道 1-13
            .password = "12345678",          // 密码（至少8位）
            .max_connection = 4,             // 最大连接数（最多10）
            .authmode = WIFI_AUTH_WPA2_PSK,  // 加密方式
            .pmf_cfg = {
                .required = true,
            },
        },
    };

    // 如果密码长度为0，设为开放网络
    if (strlen("12345678") == 0) {
        wifi_ap_config.ap.authmode = WIFI_AUTH_OPEN;
    }

    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_ap_config);
    esp_wifi_start();

    ESP_LOGI(TAG, "AP模式启动，SSID:%s 信道:%d",
             wifi_ap_config.ap.ssid, wifi_ap_config.ap.channel);
}
```

**AP+STA共存模式：**

ESP32可以同时作为STA和AP使用，适用于网关设备。

```c
void wifi_apsta_init(void)
{
    esp_netif_create_default_wifi_ap();
    esp_netif_create_default_wifi_sta();

    // STA配置 - 连接路由器
    wifi_config_t sta_config = {
        .sta = {
            .ssid = "HomeRouter",
            .password = "router_password",
        },
    };

    // AP配置 - 自建热点
    wifi_config_t ap_config = {
        .ap = {
            .ssid = "ESP32-Gateway",
            .ssid_len = strlen("ESP32-Gateway"),
            .channel = 6,
            .password = "gateway123",
            .max_connection = 4,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    esp_wifi_set_mode(WIFI_MODE_APSTA);
    esp_wifi_set_config(WIFI_IF_STA, &sta_config);
    esp_wifi_set_config(WIFI_IF_AP, &ap_config);
    esp_wifi_start();
}
```

**Web配置页面(Captive Portal)：**

当设备未配置WiFi信息时，启动AP模式并运行一个Web服务器，用户通过浏览器配置WiFi。

```c
#include "esp_http_server.h"

// Captive Portal DNS重定向 - 所有域名指向ESP32
static void start_dns_server(void)
{
    // 简化示例：将所有DNS查询响应为ESP32的AP IP（默认192.168.4.1）
    // 实际应用中需要实现完整的DNS服务器
}

// 配置页面HTML（嵌入到代码中）
static const char config_page_html[] = R"(
<!DOCTYPE html>
<html>
<head><meta charset='UTF-8'><title>WiFi配置</title></head>
<body>
<h2>ESP32 WiFi配置</h2>
<form action='/save' method='POST'>
  SSID: <input type='text' name='ssid'><br><br>
  密码: <input type='password' name='password'><br><br>
  <input type='submit' value='保存并连接'>
</form>
</body>
</html>
)";

// 处理根路径请求 - 返回配置页面
static esp_err_t root_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, config_page_html, HTTPD_RESP_USE_STRLEN);
}

// 处理保存配置请求
static esp_err_t save_handler(httpd_req_t *req)
{
    char buf[256];
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret <= 0) return ESP_FAIL;
    buf[ret] = '\0';

    // 解析表单数据 ssid=xxx&password=xxx
    char ssid[33] = {0};
    char password[65] = {0};
    // 使用httpd_query_key_value解析（需包含esp_http_server.h）
    // 此处为简化示例

    // 保存到NVS
    nvs_handle_t nvs;
    nvs_open("wifi_config", NVS_READWRITE, &nvs);
    nvs_set_str(nvs, "ssid", ssid);
    nvs_set_str(nvs, "password", password);
    nvs_commit(nvs);
    nvs_close(nvs);

    httpd_resp_send(req, "配置已保存，设备将重启...", HTTPD_RESP_USE_STRLEN);

    vTaskDelay(pdMS_TO_TICKS(2000));
    esp_restart();
    return ESP_OK;
}

void start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    httpd_start(&server, &config);

    httpd_uri_t root = {
        .uri = "/", .method = HTTP_GET, .handler = root_handler
    };
    httpd_uri_t save = {
        .uri = "/save", .method = HTTP_POST, .handler = save_handler
    };

    httpd_register_uri_handler(server, &root);
    httpd_register_uri_handler(server, &save);
}
```

### 1.3 WiFi安全

**WPA2/WPA3：**

ESP32支持以下认证模式：
- `WIFI_AUTH_OPEN` — 无加密（不推荐）
- `WIFI_AUTH_WEP` — WEP加密（已淘汰）
- `WIFI_AUTH_WPA_PSK` — WPA-PSK
- `WIFI_AUTH_WPA2_PSK` — WPA2-PSK（最常用）
- `WIFI_AUTH_WPA_WPA2_PSK` — WPA/WPA2混合
- `WIFI_AUTH_WPA3_PSK` — WPA3-PSK（ESP-IDF v5.x支持）
- `WIFI_AUTH_WPA2_WPA3_PSK` — WPA2/WPA3混合

**企业级WPA2(802.1X)：**

连接企业级WiFi需要EAP认证：

```c
#include "esp_eap_client.h"

void wifi_enterprise_init(void)
{
    esp_netif_create_default_wifi_sta();

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "CorpWiFi",
        },
    };

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);

    // 配置EAP参数
    esp_wifi_sta_enterprise_enable();

    // 设置用户名和密码（PEAP/TTLS方式）
    esp_eap_client_set_identity((uint8_t *)"username", strlen("username"));
    esp_eap_client_set_username((uint8_t *)"username", strlen("username"));
    esp_eap_client_set_password((uint8_t *)"password", strlen("password"));

    // 如需CA证书验证
    // esp_eap_client_set_ca_cert(ca_pem_start, ca_pem_size);

    esp_wifi_start();
    esp_wifi_connect();
}
```

### 1.4 代码示例

**完整STA连接WiFi示例：**

```c
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

static const char *TAG = "wifi_sta";
static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data)
{
    static int retry_count = 0;

    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (retry_count < 5) {
            esp_wifi_connect();
            retry_count++;
            ESP_LOGI(TAG, "重连中 (%d/5)...", retry_count);
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "已连接! IP: " IPSTR, IP2STR(&event->ip_info.ip));
        retry_count = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void wifi_init_sta(const char *ssid, const char *password)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    // 注册事件处理
    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "",
            .password = "",
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    strncpy((char *)wifi_config.sta.ssid, ssid, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, password, sizeof(wifi_config.sta.password) - 1);

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    // 等待连接结果
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE, portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi连接成功");
    } else {
        ESP_LOGE(TAG, "WiFi连接失败");
    }
}

void app_main(void)
{
    nvs_flash_init();
    wifi_init_sta("MyWiFi", "mypassword");
}
```

**SmartConfig配网(微信/AirKiss)：**

SmartConfig是一种无需预先知道WiFi信息的配网方式，手机App将WiFi信息编码到WiFi包中，ESP32通过监听空口包获取SSID和密码。

```c
#include "esp_smartconfig.h"
#include "esp_wifi.h"
#include "esp_event.h"

static EventGroupHandle_t s_smartconfig_event_group;
#define SC_DONE_BIT BIT0

static void smartconfig_event_handler(void *arg, esp_event_base_t event_base,
                                      int32_t event_id, void *event_data)
{
    switch (event_id) {
        case SC_EVENT_SCAN_DONE:
            ESP_LOGI(TAG, "SmartConfig扫描完成");
            break;
        case SC_EVENT_FOUND_CHANNEL:
            ESP_LOGI(TAG, "找到目标信道");
            break;
        case SC_EVENT_GOT_SSID_PSWD: {
            ESP_LOGI(TAG, "获取到WiFi信息");
            smartconfig_event_got_ssid_pswd_t *evt =
                (smartconfig_event_got_ssid_pswd_t *)event_data;

            wifi_config_t wifi_config;
            memset(&wifi_config, 0, sizeof(wifi_config_t));
            memcpy(wifi_config.sta.ssid, evt->ssid, sizeof(wifi_config.sta.ssid));
            memcpy(wifi_config.sta.password, evt->password, sizeof(wifi_config.sta.password));

            // 如果使用ESP-Touch v2，需要设置token
            // wifi_config.sta.bssid_set = evt->bssid_set;
            // if (evt->bssid_set) {
            //     memcpy(wifi_config.sta.bssid, evt->bssid, 6);
            // }

            esp_wifi_disconnect();
            esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
            esp_wifi_connect();

            // 保存到NVS以便后续自动连接
            nvs_handle_t nvs;
            nvs_open("wifi_cfg", NVS_READWRITE, &nvs);
            nvs_set_str(nvs, "ssid", (char *)evt->ssid);
            nvs_set_str(nvs, "password", (char *)evt->password);
            nvs_commit(nvs);
            nvs_close(nvs);
            break;
        }
        case SC_EVENT_SEND_ACK_DONE:
            xEventGroupSetBits(s_smartconfig_event_group, SC_DONE_BIT);
            ESP_LOGI(TAG, "SmartConfig配网完成");
            break;
    }
}

void start_smartconfig(void)
{
    s_smartconfig_event_group = xEventGroupCreate();

    esp_event_handler_register(SC_EVENT, ESP_EVENT_ANY_ID,
                               &smartconfig_event_handler, NULL);

    // 选择配网协议类型
    // SC_TYPE_ESPTOUCH       - ESP-Touch (乐鑫自有协议)
    // SC_TYPE_AIRKISS        - 微信AirKiss
    // SC_TYPE_ESPTOUCH_AIRKISS - 同时支持两种
    esp_smartconfig_set_type(SC_TYPE_ESPTOUCH_AIRKISS);

    smartconfig_start_config_t cfg = SMARTCONFIG_START_CONFIG_DEFAULT();
    esp_smartconfig_start(&cfg);

    ESP_LOGI(TAG, "SmartConfig已启动，使用手机App进行配网...");
}
```

**ESP-Touch配网：**

ESP-Touch是乐鑫开发的SmartConfig协议实现，使用ESP-Touch App或微信扫码配网。

```c
// ESP-Touch v2 配网（支持Token认证，更安全）
void start_esptouch_v2(void)
{
    esp_smartconfig_set_type(SC_TYPE_ESPTOUCH_V2);

    smartconfig_start_config_t cfg = {
        .enable_log = true,
        .esp_touch_v2_enable_crypt = true,    // 启用加密
        .esp_touch_v2_key = "1234567890abcdef"  // 16字节密钥
    };
    esp_smartconfig_start(&cfg);
}
```

---

## 2. 蓝牙BLE

ESP32集成双模蓝牙：经典蓝牙(BR/EDR)和低功耗蓝牙(BLE)。BLE专为低功耗、短数据包传输设计，广泛用于物联网设备。

### 2.1 BLE基础概念

**BLE协议栈架构：**

```
+---------------------------+
|       Application         |   <-- 用户代码
+---------------------------+
|        GATT层             |   <-- 属性读写
+---------------------------+
|        ATT层              |   <-- 属性协议
+---------------------------+
|        SMP层              |   <-- 安全管理
+---------------------------+
|        GAP层              |   <-- 设备发现/连接
+---------------------------+
|     Host (L2CAP/HCI)      |   <-- 主机控制接口
+---------------------------+
|      Controller           |   <-- 射频/链路层
+---------------------------+
```

ESP-IDF提供两套BLE协议栈：
- **Bluedroid**：功能全面，占用资源多（默认）
- **NimBLE**：轻量级，资源占用少，推荐新项目使用

**GAP(通用访问配置)：**

GAP定义设备如何被发现和连接：
- **Broadcaster**：只发送广播（如Beacon）
- **Observer**：只扫描，不连接
- **Peripheral**：可被连接的从设备（ESP32最常见角色）
- **Central**：主动连接的主设备（如手机）

**GATT(通用属性配置)：**

GATT定义数据如何在已连接设备间传输：
- **Server**：拥有数据（属性表）的一方
- **Client**：读写Server数据的一方
- 角色独立于GAP角色：一个Peripheral通常是GATT Server

**Service / Characteristic / Descriptor：**

```
GATT Server（ESP32）
├── Service: Heart Rate (UUID: 0x180D)
│   ├── Characteristic: Heart Rate Measurement (UUID: 0x2A37)
│   │   ├── Properties: Notify
│   │   ├── Value: [0x06, 0x40]  (心率值)
│   │   └── Descriptor: CCCD (0x2902)  <-- Client Characteristic Configuration
│   └── Characteristic: Body Sensor Location (UUID: 0x2A38)
│       ├── Properties: Read
│       └── Value: 0x01 (胸部)
└── Service: Battery Service (UUID: 0x180F)
    └── Characteristic: Battery Level (UUID: 0x2A19)
        ├── Properties: Read, Notify
        └── Value: 85 (%)
```

**UUID概念：**

- **16-bit UUID**：蓝牙SIG定义的标准UUID，如 `0x180D`（心率服务）
- **128-bit UUID**：自定义UUID，格式 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- 自定义服务建议使用128-bit UUID避免冲突

```c
// 生成自定义UUID示例
// 服务UUID: 12345678-1234-5678-1234-56789abcdef0
static const uint8_t SERVICE_UUID[16] = {
    0xf0, 0xde, 0xbc, 0x9a, 0x78, 0x56, 0x34, 0x12,
    0x78, 0x56, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12
};
```

### 2.2 BLE Server

**创建GATT Server：**

以下使用NimBLE协议栈（推荐），ESP-IDF v5.x中已内置。

```c
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble_server";

// 自定义服务和特征UUID
// 服务: 12345678-1234-5678-1234-56789abcdef0
// 特征: 12345678-1234-5678-1234-56789abcdef1
static const ble_uuid128_t gatt_svc_uuid =
    BLE_UUID128_INIT(0xf0, 0xde, 0xbc, 0x9a, 0x78, 0x56, 0x34, 0x12,
                     0x78, 0x56, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12);
static const ble_uuid128_t gatt_chr_uuid =
    BLE_UUID128_INIT(0xf1, 0xde, 0xbc, 0x9a, 0x78, 0x56, 0x34, 0x12,
                     0x78, 0x56, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12);

// 读写回调处理
static int chr_access_cb(uint16_t conn_handle, uint16_t attr_handle,
                         struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    switch (ctxt->op) {
        case BLE_GATT_ACCESS_OP_READ_CHR:
            ESP_LOGI(TAG, "读取请求, handle=%d", attr_handle);
            // 填充返回数据
            uint8_t value[] = {0x42, 0x00};
            int rc = os_mbuf_append(ctxt->om, value, sizeof(value));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;

        case BLE_GATT_ACCESS_OP_WRITE_CHR:
            ESP_LOGI(TAG, "写入请求, 长度=%d", ctxt->om->om_len);
            // 处理写入数据
            uint8_t buf[64];
            int len = min(ctxt->om->om_len, sizeof(buf));
            os_mbuf_copydata(ctxt->om, 0, len, buf);
            ESP_LOGI(TAG, "收到数据: %.*s", len, buf);
            return 0;

        default:
            return BLE_ATT_ERR_UNLIKELY;
    }
}

// GATT服务定义
static const struct ble_gatt_svc_def gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &gatt_svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]){
            {
                .uuid = &gatt_chr_uuid.u,
                .access_cb = chr_access_cb,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE |
                         BLE_GATT_CHR_F_NOTIFY,
            },
            { 0 }  // 数组终止符
        },
    },
    { 0 },  // 服务数组终止符
};
```

**Notify/Indicate发送数据：**

Notify和Indicate是Server主动向Client推送数据的方式。区别在于Indicate需要Client确认。

```c
static uint16_t conn_handle_global = BLE_HS_CONN_HANDLE_NONE;
static uint16_t chr_val_handle = 0;

// 通过Notify发送数据给已连接的Client
void send_notify_data(uint8_t *data, uint16_t len)
{
    if (conn_handle_global == BLE_HS_CONN_HANDLE_NONE) {
        ESP_LOGW(TAG, "无设备连接");
        return;
    }

    struct os_mbuf *om = ble_hs_mbuf_from_flat(data, len);
    if (om == NULL) {
        ESP_LOGE(TAG, "分配mbuf失败");
        return;
    }

    // ble_gattc_notify_custom会自动检查CCCD是否已启用Notify
    int rc = ble_gattc_notify_custom(conn_handle_global, chr_val_handle, om);
    if (rc != 0) {
        ESP_LOGE(TAG, "发送Notify失败: %d", rc);
    }
}

// 使用示例：发送传感器数据
void send_sensor_data(float temperature, float humidity)
{
    uint8_t data[8];
    memcpy(data, &temperature, 4);
    memcpy(data + 4, &humidity, 4);
    send_notify_data(data, sizeof(data));
}
```

### 2.3 BLE Client

**扫描BLE设备：**

```c
static void ble_scan_cb(struct ble_gap_disc_desc *disc)
{
    if (disc->event != BLE_GAP_DISC_EVENT) return;

    // 打印设备信息
    char addr_str[18];
    snprintf(addr_str, sizeof(addr_str), "%02x:%02x:%02x:%02x:%02x:%02x",
             disc->addr.val[5], disc->addr.val[4], disc->addr.val[3],
             disc->addr.val[2], disc->addr.val[1], disc->addr.val[0]);

    // 解析广播数据中的设备名称
    struct ble_hs_adv_fields fields;
    ble_hs_adv_parse_fields(&fields, disc->data, disc->length_data);

    char name[32] = {0};
    if (fields.name != NULL) {
        snprintf(name, sizeof(name), "%.*s", fields.name_len, fields.name);
    }

    ESP_LOGI(TAG, "发现设备: %s (%s) RSSI:%d", name, addr_str, disc->rssi);

    // 检查是否为目标设备（通过名称或UUID过滤）
    if (strstr(name, "ESP32-Sensor") != NULL) {
        ble_gap_disc_cancel();  // 停止扫描
        // 发起连接
        struct ble_gap_conn_params conn_params = {
            .scan_itvl = 0x0010,
            .scan_window = 0x0010,
            .itvl_min = 0x0006,
            .itvl_max = 0x0006,
            .latency = 0,
            .supervision_timeout = 0x0100,
            .min_ce_len = 0x0006,
            .max_ce_len = 0x0006,
        };
        ble_gap_connect(&disc->addr, 30000, &conn_params, NULL, NULL);
    }
}

void start_ble_scan(void)
{
    struct ble_gap_disc_params disc_params = {
        .filter_duplicates = 1,
        .passive = 0,
        .itvl = 0x0010,
        .window = 0x0010,
        .filter_policy = 0,
        .limited = 0,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 15000, &disc_params, ble_scan_cb, NULL);
}
```

**发现Service/Characteristic并读写数据：**

```c
static uint16_t conn_handle;
static uint16_t target_chr_val_handle;

// GATT服务发现回调
static int ble_on_disc_svc(uint16_t conn_handle,
                           const struct ble_gatt_error *error,
                           const struct ble_gatt_svc *service, void *arg)
{
    if (error->status != 0) {
        ESP_LOGE(TAG, "服务发现失败: %d", error->status);
        return 0;
    }

    ESP_LOGI(TAG, "发现服务 handle=%d-%d", service->start_handle, service->end_handle);

    // 继续发现该服务下的特征
    ble_gattc_disc_all_chrs(conn_handle, service->start_handle,
                            service->end_handle, ble_on_disc_chr, NULL);
    return 0;
}

// 特征发现回调
static int ble_on_disc_chr(uint16_t conn_handle,
                           const struct ble_gatt_error *error,
                           const struct ble_gatt_chr *chr, void *arg)
{
    if (error->status != 0) return 0;

    // 查找目标特征（通过UUID匹配）
    if (ble_uuid_cmp(&chr->uuid.u, &gatt_chr_uuid.u) == 0) {
        target_chr_val_handle = chr->val_handle;
        ESP_LOGI(TAG, "找到目标特征, handle=%d", target_chr_val_handle);

        // 读取特征值
        ble_gattc_read(conn_handle, target_chr_val_handle, ble_on_read, NULL);
    }
    return 0;
}

// 读取回调
static int ble_on_read(uint16_t conn_handle,
                       const struct ble_gatt_error *error,
                       struct ble_gatt_attr *attr, void *arg)
{
    if (error->status != 0) {
        ESP_LOGE(TAG, "读取失败: %d", error->status);
        return 0;
    }

    uint8_t buf[64];
    int len = os_mbuf_copydata(attr->om, 0, sizeof(buf), buf);
    ESP_LOGI(TAG, "读取到 %d 字节数据", len);
    return 0;
}

// 写入数据
void write_to_server(uint8_t *data, uint16_t len)
{
    struct os_mbuf *om = ble_hs_mbuf_from_flat(data, len);
    ble_gattc_write(conn_handle, target_chr_val_handle, om, NULL, NULL);
}
```

**订阅Notify：**

```c
// Notify接收回调
static int ble_on_notify(uint16_t conn_handle,
                         const struct ble_gatt_error *error,
                         struct ble_gatt_attr *attr, void *arg)
{
    if (error->status == 0 && attr != NULL) {
        uint8_t buf[64];
        int len = os_mbuf_copydata(attr->om, 0, sizeof(buf), buf);
        ESP_LOGI(TAG, "收到Notify数据(%d字节)", len);
        // 处理数据...
    }
    return 0;
}

// 订阅Notify
void subscribe_notify(uint16_t conn_handle, uint16_t chr_val_handle)
{
    uint8_t value[2] = {0x01, 0x00};  // 启用Notify (0x0001)
    struct os_mbuf *om = ble_hs_mbuf_from_flat(value, 2);

    // 写入CCCD（Client Characteristic Configuration Descriptor）
    uint16_t cccd_handle = chr_val_handle + 1;  // CCCD通常紧跟在value handle之后
    ble_gattc_write(conn_handle, cccd_handle, om, NULL, NULL);
}
```

### 2.4 BLE高级

**BLE配对与绑定：**

```c
#include "host/sm/sm.h"

void configure_ble_security(void)
{
    // 设置IO能力
    // BLE_HS_IO_NO_INPUT_OUTPUT - 无输入输出（Just Works）
    // BLE_HS_IO_DISPLAY_ONLY    - 仅显示（Numeric Comparison）
    // BLE_HS_IO_KEYBOARD_ONLY   - 仅键盘（Passkey Entry）
    ble_hs_cfg.io_cap = BLE_HS_IO_NO_INPUT_OUTPUT;

    // 配对参数
    ble_gap_pair_init();

    // 设置安全等级
    // BLE_SM_PAIR_AUTHREQ_BOND   - 绑定（保存密钥）
    // BLE_SM_PAIR_AUTHREQ_MITM   - 防中间人攻击
    // BLE_SM_PAIR_AUTHREQ_SC     - 安全连接（BLE 4.2+）
    ble_hs_cfg.sm_sc = 1;         // 启用安全连接
    ble_hs_cfg.sm_bonding = 1;    // 启用绑定
    ble_hs_cfg.sm_mitm = 1;       // 启用MITM保护
    ble_hs_cfg.sm_our_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;
    ble_hs_cfg.sm_their_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;
}
```

**BLE MTU协商：**

BLE默认MTU为23字节（有效负载20字节），可通过协商增大到512字节。

```c
// Server端设置首选MTU
void ble_set_preferred_mtu(void)
{
    // 设置Server支持的最大MTU
    ble_att_set_preferred_mtu(247);  // 推荐值，平衡性能和可靠性
}

// 连接后MTU会自动协商，也可手动请求
// Client端请求更大MTU：
void request_mtu(uint16_t conn_handle)
{
    ble_gattc_exchange_mtu(conn_handle, NULL, NULL);
}

// 获取协商后的MTU
void check_mtu(uint16_t conn_handle)
{
    uint16_t mtu;
    int rc = ble_att_mtu(conn_handle, &mtu);
    if (rc == 0) {
        ESP_LOGI(TAG, "当前MTU: %d (有效负载: %d)", mtu, mtu - 3);
    }
}
```

**BLE5.0特性（ESP32-C6/S3支持）：**

```c
// 扩展广播（Extended Advertising）- BLE 5.0
// 广播数据最长可达254字节（传统仅31字节）
void setup_extended_advertising(void)
{
    struct ble_gap_ext_adv_params params = {
        .connectable = 1,
        .scannable = 0,
        .high_duty_directed = 0,
        .legacy_pdu = 0,           // 使用扩展PDU
        .anonymous = 0,
        .include_tx_power = 1,
        .scan_req_notif = 0,
        .own_addr_type = BLE_OWN_ADDR_PUBLIC,
        .primary_phy = BLE_HCI_LE_PHY_1M,    // 主广播信道PHY
        .secondary_phy = BLE_HCI_LE_PHY_2M,  // 辅助信道PHY（2Mbps）
        .sid = 0,
    };
    ble_gap_ext_adv_configure(0, &params, NULL, NULL, NULL);
}

// 2Mbps PHY - 更高的数据吞吐量
void set_2mbit_phy(uint16_t conn_handle)
{
    ble_gap_set_prefered_default_le_phy(BLE_HCI_LE_PHY_2M, BLE_HCI_LE_PHY_2M);
}
```

**NimBLE vs Bluedroid协议栈对比：**

| 特性 | NimBLE | Bluedroid |
|------|--------|-----------|
| 内存占用 | ~100KB Flash, ~10KB RAM | ~300KB Flash, ~60KB RAM |
| 功能覆盖 | 仅BLE | BLE + 经典蓝牙 |
| API风格 | 较底层，灵活 | 较高层，易用 |
| 适用场景 | 资源受限、纯BLE | 需要经典蓝牙、功能全面 |
| 配置宏 | CONFIG_BT_NIMBLE_ENABLED | CONFIG_BT_BLUEDROID_ENABLED |
| 推荐程度 | 新项目推荐 | 兼容旧项目 |

### 2.5 代码示例

**BLE Server - 心率传感器：**

```c
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "services/ans/ble_svc_ans.h"
#include "services/bas/ble_svc_bas.h"
#include "services/heart_rate/ble_svc_hrs.h"

static const char *TAG = "ble_hr_server";
static uint16_t conn_handle_hr = BLE_HS_CONN_HANDLE_NONE;

// GAP事件处理
static int gap_event_cb(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            ESP_LOGI(TAG, "连接 %s, handle=%d",
                     event->connect.status == 0 ? "成功" : "失败",
                     event->connect.conn_handle);
            if (event->connect.status == 0) {
                conn_handle_hr = event->connect.conn_handle;
            } else {
                // 连接失败，重新开始广播
                ble_svc_gap_device_start_advertising();
            }
            break;

        case BLE_GAP_EVENT_DISCONNECT:
            ESP_LOGI(TAG, "断开连接, 原因=%d", event->disconnect.reason);
            conn_handle_hr = BLE_HS_CONN_HANDLE_NONE;
            ble_svc_gap_device_start_advertising();
            break;

        case BLE_GAP_EVENT_SUBSCRIBE:
            ESP_LOGI(TAG, "订阅事件: attr_handle=%d, cur_notify=%d",
                     event->subscribe.attr_handle, event->subscribe.cur_notify);
            break;
    }
    return 0;
}

// 启动广播
void ble_hr_advertise(void)
{
    struct ble_gap_adv_params adv_params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,  // 可连接非定向广播
        .disc_mode = BLE_GAP_DISC_MODE_GEN,  // 可发现
        .itvl_min = 0x0020,
        .itvl_max = 0x0040,
        .channel_map = 7,
    };

    // 设置广播数据
    struct ble_hs_adv_fields adv_fields = {0};
    adv_fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    adv_fields.tx_pwr_lvl_is_present = 1;
    adv_fields.tx_pwr_lvl = BLE_HS_ADV_TX_PWR_LVL_AUTO;

    const char *name = ble_svc_gap_device_name();
    adv_fields.name = (uint8_t *)name;
    adv_fields.name_len = strlen(name);
    adv_fields.name_is_complete = 1;

    // 添加心率服务UUID到广播数据
    adv_fields.uuids16 = (ble_uuid16_t[]){
        BLE_UUID16_INIT(BLE_GATT_SVC_UUID_HEART_RATE),
    };
    adv_fields.num_uuids16 = 1;
    adv_fields.uuids16_is_complete = 1;

    ble_gap_adv_set_fields(&adv_fields);

    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                      &adv_params, gap_event_cb, NULL);
}

// 模拟心率数据发送
void heart_rate_task(void *param)
{
    uint8_t heart_rate = 72;
    bool increasing = true;

    while (1) {
        // 模拟心率变化
        if (increasing) {
            heart_rate += 2;
            if (heart_rate >= 100) increasing = false;
        } else {
            heart_rate -= 2;
            if (heart_rate <= 65) increasing = true;
        }

        if (conn_handle_hr != BLE_HS_CONN_HANDLE_NONE) {
            // BLE心率测量格式：Flags(1B) + Heart Rate(1-2B)
            uint8_t hr_data[2] = {0x00, heart_rate};  // 0x00 = 8-bit心率值
            struct os_mbuf *om = ble_hs_mbuf_from_flat(hr_data, sizeof(hr_data));
            ble_gattc_notify_custom(conn_handle_hr,
                                    ble_svc_hrs_handle, om);
            ESP_LOGI(TAG, "发送心率: %d BPM", heart_rate);
        }

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    nvs_flash_init();

    nimble_port_init();
    ble_hs_cfg.reset_cb = NULL;
    ble_hs_cfg.sync_cb = NULL;
    ble_hs_cfg.gatts_register_cb = NULL;

    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_svc_hrs_init();  // 初始化心率服务

    ble_svc_gap_device_name_set("ESP32-HeartRate");
    ble_svc_gap_device_appearance_set(BLE_GAP_APPEARANCE_HEART_RATE_BELT);

    nimble_port_freertos_init(NULL);

    // 启动广播
    ble_hr_advertise();

    // 启动心率数据任务
    xTaskCreate(heart_rate_task, "heart_rate", 4096, NULL, 5, NULL);
}
```

**BLE Client - 读取传感器数据：**

```c
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/ble_gatt.h"

static const char *TAG = "ble_client";
static uint16_t conn_handle_sensor = BLE_HS_CONN_HANDLE_NONE;

// 心率服务UUID和特征UUID
static const ble_uuid16_t hr_svc_uuid = BLE_UUID16_INIT(0x180D);
static const ble_uuid16_t hr_chr_uuid = BLE_UUID16_INIT(0x2A37);

static uint16_t hr_chr_val_handle = 0;

// 服务发现完成回调
static int on_svc_disc(uint16_t conn_handle,
                       const struct ble_gatt_error *error,
                       const struct ble_gatt_svc *service, void *arg)
{
    if (error->status == BLE_HS_EDONE) {
        ESP_LOGI(TAG, "服务发现完成");
    } else if (error->status == 0) {
        ESP_LOGI(TAG, "发现服务: start=%d end=%d",
                 service->start_handle, service->end_handle);

        // 发现该服务下的特征
        ble_gattc_disc_all_chrs(conn_handle, service->start_handle,
                                service->end_handle, on_chr_disc, NULL);
    }
    return 0;
}

// 特征发现回调
static int on_chr_disc(uint16_t conn_handle,
                       const struct ble_gatt_error *error,
                       const struct ble_gatt_chr *chr, void *arg)
{
    if (error->status == BLE_HS_EDONE) {
        ESP_LOGI(TAG, "特征发现完成");
        // 订阅Notify
        if (hr_chr_val_handle != 0) {
            subscribe_notify(conn_handle, hr_chr_val_handle);
        }
    } else if (error->status == 0) {
        if (ble_uuid_cmp(&chr->uuid.u, &hr_chr_uuid.u) == 0) {
            hr_chr_val_handle = chr->val_handle;
            ESP_LOGI(TAG, "发现心率特征, handle=%d, properties=0x%02x",
                     chr->val_handle, chr->properties);
        }
    }
    return 0;
}

// Notify接收回调
static int on_notify(uint16_t conn_handle,
                     const struct ble_gatt_error *error,
                     struct ble_gatt_attr *attr, void *arg)
{
    if (error->status == 0 && attr != NULL) {
        uint8_t buf[16];
        int len = os_mbuf_copydata(attr->om, 0, sizeof(buf), buf);
        if (len >= 2) {
            uint8_t flags = buf[0];
            uint8_t heart_rate;
            if (flags & 0x01) {
                // 16-bit心率值
                heart_rate = buf[1] | (buf[2] << 8);
            } else {
                // 8-bit心率值
                heart_rate = buf[1];
            }
            ESP_LOGI(TAG, "收到心率数据: %d BPM", heart_rate);
        }
    }
    return 0;
}

// 连接事件处理
static int client_gap_event_cb(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            if (event->connect.status == 0) {
                conn_handle_sensor = event->connect.conn_handle;
                ESP_LOGI(TAG, "连接成功，开始服务发现");
                ble_gattc_disc_svc_by_uuid(conn_handle_sensor,
                    &hr_svc_uuid.u, on_svc_disc, NULL);
            } else {
                ESP_LOGE(TAG, "连接失败: %d", event->connect.status);
            }
            break;

        case BLE_GAP_EVENT_DISCONNECT:
            ESP_LOGI(TAG, "断开连接");
            conn_handle_sensor = BLE_HS_CONN_HANDLE_NONE;
            hr_chr_val_handle = 0;
            break;
    }
    return 0;
}

// 扫描并连接目标设备
void client_scan_and_connect(void)
{
    struct ble_gap_disc_params disc_params = {
        .filter_duplicates = 1,
        .passive = 0,
        .itvl = 0x0010,
        .window = 0x0010,
    };
    ble_gap_disc(BLE_OWN_ADDR_PUBLIC, 15000, &disc_params,
                 client_scan_cb, NULL);
}
```

**BLE透传(UART over BLE)：**

UART over BLE（也称NUS - Nordic UART Service）是最常见的BLE透传方案。

```c
// Nordic UART Service UUID
// 服务: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
// TX特征(Notify): 6E400003-...  (Server -> Client)
// RX特征(Write):  6E400002-...  (Client -> Server)

static const ble_uuid128_t nus_svc_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x01, 0x00, 0x40, 0x6e);
static const ble_uuid128_t nus_tx_chr_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x03, 0x00, 0x40, 0x6e);
static const ble_uuid128_t nus_rx_chr_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x02, 0x00, 0x40, 0x6e);

// NUS RX回调 - 收到手机发来的数据
static int nus_rx_cb(uint16_t conn_handle, uint16_t attr_handle,
                     struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    uint8_t buf[244];  // MTU-3
    int len = os_mbuf_copydata(ctxt->om, 0, sizeof(buf), buf);
    ESP_LOGI(TAG, "BLE RX(%d字节): %.*s", len, len, buf);

    // 转发到UART或其他处理
    uart_write_bytes(UART_NUM_0, buf, len);
    return 0;
}

// 发送数据到手机
void ble_uart_send(const uint8_t *data, uint16_t len)
{
    if (conn_handle_global == BLE_HS_CONN_HANDLE_NONE) return;

    // 如果数据超过MTU-3，需要分包发送
    uint16_t mtu = ble_att_mtu(conn_handle_global) - 3;
    uint16_t offset = 0;

    while (offset < len) {
        uint16_t chunk = min(mtu, len - offset);
        struct os_mbuf *om = ble_hs_mbuf_from_flat(data + offset, chunk);
        ble_gattc_notify_custom(conn_handle_global, nus_tx_val_handle, om);
        offset += chunk;
    }
}
```

---

## 3. ESP-NOW

ESP-NOW是乐鑫开发的短距离无线通信协议，基于WiFi物理层，无需建立WiFi连接即可直接通信，具有低延迟、低功耗的特点。

### 3.1 ESP-NOW基础

**ESP-NOW协议特点：**
- 无连接：无需WiFi连接/握手，直接发送
- 低延迟：典型延迟 < 5ms
- 点对点/广播：支持一对一和一对多
- 数据包限制：单包最大250字节
- 基于WiFi：与WiFi共享射频模块，需注意共存
- 加密：支持PMK（主密钥）和LMK（本地密钥）加密

**MAC地址管理：**

ESP-NOW通信基于MAC地址，每个设备有唯一MAC地址。

```c
#include "esp_wifi.h"
#include "esp_mac.h"

// 获取本机MAC地址
void print_mac_address(void)
{
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_STA, mac);
    ESP_LOGI(TAG, "MAC地址: %02x:%02x:%02x:%02x:%02x:%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}
```

**对等设备注册：**

通信前必须将对端MAC地址注册为对等设备（peer）。

```c
#include "esp_now.h"

// 注册对等设备
esp_now_peer_info_t peer_info = {
    .channel = 0,                    // 0 = 使用当前WiFi信道
    .encrypt = false,                // 是否加密
    .ifidx = WIFI_IF_STA,            // 接口
};
memcpy(peer_info.peer_addr, peer_mac, 6);

esp_err_t ret = esp_now_add_peer(&peer_info);
if (ret != ESP_OK) {
    ESP_LOGE(TAG, "添加对等设备失败: %s", esp_err_to_name(ret));
}

// 删除对等设备
esp_now_del_peer(peer_mac);

// 检查是否已注册
bool exists = esp_now_is_peer_exist(peer_mac);
```

**数据加密(PMK/LMK)：**

```c
// 设置PMK（主密钥）- 全局，16字节
uint8_t pmk[16] = "MyPMKKey1234567";  // 16字节
esp_now_set_pmk(pmk);

// 注册对等设备时设置LMK（本地密钥）- 每个对等设备不同
esp_now_peer_info_t peer_info = {
    .peer_addr = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66},
    .lmk = "LocalKey1234567",  // 16字节
    .encrypt = true,            // 必须启用
    .channel = 0,
    .ifidx = WIFI_IF_STA,
};
esp_now_add_peer(&peer_info);
```

### 3.2 ESP-NOW应用

**一对多广播：**

```c
// 使用广播地址 FF:FF:FF:FF:FF:FF 发送给所有已注册的peer
uint8_t broadcast_mac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// 注册广播peer
esp_now_peer_info_t broadcast_peer = {
    .peer_addr = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},
    .channel = 0,
    .encrypt = false,
    .ifidx = WIFI_IF_STA,
};
esp_now_add_peer(&broadcast_peer);

// 发送广播
esp_now_send(broadcast_mac, data, len);
```

**ESP-NOW + WiFi共存：**

ESP-NOW可以和WiFi STA/AP共存，但需要在同一信道上。

```c
void espnow_with_wifi_init(void)
{
    // 1. 先初始化WiFi
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_start();

    // 2. 连接WiFi（确保信道一致）
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "MyRouter",
            .password = "password",
        },
    };
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_connect();

    // 3. 初始化ESP-NOW（使用相同信道）
    esp_now_init();
    esp_now_register_recv_cb(recv_callback);

    // 添加peer时channel设为0表示使用当前WiFi信道
    esp_now_peer_info_t peer = {
        .channel = 0,  // 自动使用WiFi信道
        .encrypt = false,
        .ifidx = WIFI_IF_STA,
    };
    memcpy(peer.peer_addr, target_mac, 6);
    esp_now_add_peer(&peer);
}
```

### 3.3 代码示例

**发送端：**

```c
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freotas/task.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_log.h"
#include "esp_mac.h"

static const char *TAG = "espnow_tx";

// 对端MAC地址（需要替换为实际地址）
static uint8_t peer_mac[6] = {0x24, 0x6F, 0x28, 0xAA, 0xBB, 0xCC};

// 发送回调
static void send_cb(const uint8_t *mac_addr, esp_now_send_status_t status)
{
    if (mac_addr == NULL) return;

    ESP_LOGI(TAG, "发送 %s -> %02x:%02x:%02x:%02x:%02x:%02x",
             status == ESP_NOW_SEND_SUCCESS ? "成功" : "失败",
             mac_addr[0], mac_addr[1], mac_addr[2],
             mac_addr[3], mac_addr[4], mac_addr[5]);
}

// 接收回调
static void recv_cb(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    ESP_LOGI(TAG, "收到来自 %02x:%02x:%02x:%02x:%02x:%02x 的数据(%d字节)",
             info->src_addr[0], info->src_addr[1], info->src_addr[2],
             info->src_addr[3], info->src_addr[4], info->src_addr[5], len);

    ESP_LOGI(TAG, "数据: %.*s", len, data);
}

void espnow_sender_init(void)
{
    // 初始化WiFi（STA模式，不需要连接AP）
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());

    // 初始化ESP-NOW
    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_send_cb(send_cb));
    ESP_ERROR_CHECK(esp_now_register_recv_cb(recv_cb));

    // 注册对等设备
    esp_now_peer_info_t peer_info = {
        .channel = 0,
        .encrypt = false,
        .ifidx = WIFI_IF_STA,
    };
    memcpy(peer_info.peer_addr, peer_mac, 6);
    ESP_ERROR_CHECK(esp_now_add_peer(&peer_info));

    ESP_LOGI(TAG, "ESP-NOW发送端初始化完成");
}

// 发送任务
void espnow_send_task(void *param)
{
    uint8_t data[250];
    int count = 0;

    while (1) {
        int len = snprintf((char *)data, sizeof(data),
                           "Hello ESP-NOW #%d", count++);

        esp_err_t ret = esp_now_send(peer_mac, data, len + 1);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "发送失败: %s", esp_err_to_name(ret));
        }

        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

void app_main(void)
{
    nvs_flash_init();
    espnow_sender_init();
    xTaskCreate(espnow_send_task, "send_task", 4096, NULL, 5, NULL);
}
```

**接收端：**

```c
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_now.h"
#include "esp_log.h"

static const char *TAG = "espnow_rx";

// 接收回调 - 数据到达时自动调用
static void recv_cb(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    // 打印发送方MAC地址
    ESP_LOGI(TAG, "收到来自 %02x:%02x:%02x:%02x:%02x:%02x 的数据",
             info->src_addr[0], info->src_addr[1], info->src_addr[2],
             info->src_addr[3], info->src_addr[4], info->src_addr[5]);

    // RSSI和信道信息
    ESP_LOGI(TAG, "RSSI: %d, 信道: %d", info->rx_ctrl->rssi, info->rx_ctrl->channel);

    // 处理数据
    ESP_LOGI(TAG, "数据内容(%d字节): %.*s", len, len, data);

    // 可选：回发应答
    // esp_now_send(info->src_addr, ack_data, ack_len);
}

// 发送回调
static void send_cb(const uint8_t *mac_addr, esp_now_send_status_t status)
{
    ESP_LOGI(TAG, "发送状态: %s", status == ESP_NOW_SEND_SUCCESS ? "成功" : "失败");
}

void espnow_receiver_init(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_ERROR_CHECK(esp_now_init());
    ESP_ERROR_CHECK(esp_now_register_recv_cb(recv_cb));
    ESP_ERROR_CHECK(esp_now_register_send_cb(send_cb));

    ESP_LOGI(TAG, "ESP-NOW接收端初始化完成，等待数据...");
}

void app_main(void)
{
    nvs_flash_init();
    espnow_receiver_init();

    // 接收端无需额外任务，回调函数会自动处理
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

**应答机制实现：**

ESP-NOW本身不保证送达，需要应用层实现应答机制。

```c
#include "freertos/timers.h"

#define ACK_TIMEOUT_MS 500
#define MAX_RETRY 3

typedef struct {
    uint8_t msg_id;      // 消息ID
    uint8_t type;        // 0=数据, 1=ACK
    uint8_t data[240];   // 数据内容
    uint16_t len;        // 数据长度
} espnow_msg_t;

static uint8_t s_msg_id = 0;
static bool s_ack_received = false;
static TimerHandle_t s_ack_timer;

// ACK超时处理
static void ack_timeout_cb(TimerHandle_t timer)
{
    ESP_LOGW(TAG, "ACK超时，重传...");
    // 重传逻辑
}

// 发送带应答的数据
esp_err_t espnow_send_with_ack(const uint8_t *peer_addr,
                                const uint8_t *data, uint16_t len)
{
    espnow_msg_t msg;
    msg.msg_id = s_msg_id++;
    msg.type = 0;  // 数据类型
    memcpy(msg.data, data, len);
    msg.len = len;

    for (int retry = 0; retry < MAX_RETRY; retry++) {
        s_ack_received = false;

        esp_now_send(peer_addr, (uint8_t *)&msg, len + 4);

        // 启动超时定时器
        xTimerStart(s_ack_timer, portMAX_DELAY);

        // 等待ACK
        int wait_ms = 0;
        while (!s_ack_received && wait_ms < ACK_TIMEOUT_MS) {
            vTaskDelay(pdMS_TO_TICKS(10));
            wait_ms += 10;
        }
        xTimerStop(s_ack_timer, portMAX_DELAY);

        if (s_ack_received) {
            ESP_LOGI(TAG, "收到ACK (msg_id=%d)", msg.msg_id);
            return ESP_OK;
        }
    }

    ESP_LOGE(TAG, "发送失败，已重试%d次", MAX_RETRY);
    return ESP_FAIL;
}
```

---

## 4. ESP-WIFI-MESH

ESP-WIFI-MESH是基于WiFi的mesh网络方案，设备间自动组网，支持多跳路由，适用于大面积覆盖场景。

### 4.1 Mesh网络拓扑

```
         [根节点 - 连接路由器]
           /     |      \
      [中间节点] [中间节点] [中间节点]
       /    \       |        \
   [叶节点] [叶节点] [叶节点] [叶节点]
```

- **根节点(Root)**：连接外部网络（路由器），是mesh网络的网关
- **中间节点(Intermediate)**：既连接父节点又为子节点提供连接
- **叶节点(Leaf)**：只连接父节点，不接受子节点

### 4.2 Mesh网络组建流程

```c
#include "esp_mesh.h"
#include "esp_mesh_internal.h"

static const char *TAG = "mesh";

// Mesh网络配置
static mesh_cfg_t mesh_config = {
    .channel = 0,                    // 自动选择信道
    .mesh_id = {0x77, 0x77, 0x77, 0x77, 0x77, 0x77},  // Mesh网络ID
    .mesh_ap = {
        .ssid = "MESH_AP",
        .password = "mesh1234567",
        .authmode = WIFI_AUTH_WPA2_PSK,
        .max_connection = 6,         // 子节点最大连接数
    },
};

// Mesh路由表（自动维护）
// mesh_route_table_t route_table;

void mesh_event_cb(mesh_event_t event)
{
    switch (event.id) {
        case MESH_EVENT_STARTED:
            ESP_LOGI(TAG, "Mesh网络启动");
            break;

        case MESH_EVENT_STOPPED:
            ESP_LOGI(TAG, "Mesh网络停止");
            break;

        case MESH_EVENT_CHILD_CONNECTED:
            ESP_LOGI(TAG, "子节点连接: " MACSTR, MAC2STR(event.info.child_connected.mac));
            break;

        case MESH_EVENT_CHILD_DISCONNECTED:
            ESP_LOGI(TAG, "子节点断开: " MACSTR, MAC2STR(event.info.child_disconnected.mac));
            break;

        case MESH_EVENT_ROUTING_TABLE_ADD:
            ESP_LOGI(TAG, "路由表更新，新增节点");
            break;

        case MESH_EVENT_ROOT_ADDRESS:
            ESP_LOGI(TAG, "根节点地址: " IPSTR, IP2STR(&event.info.root_address.addr));
            break;

        case MESH_EVENT_TODS_STATE:
            ESP_LOGI(TAG, "到外部网络状态: %s",
                     event.info.toDS_state ? "已连接" : "未连接");
            break;

        default:
            break;
    }
}

void mesh_init(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // 初始化Mesh
    ESP_ERROR_CHECK(esp_mesh_init());
    ESP_ERROR_CHECK(esp_mesh_set_config(&mesh_config));
    ESP_ERROR_CHECK(esp_mesh_set_event_cb(mesh_event_cb));

    // 设置Mesh网络参数
    esp_mesh_set_max_layer(6);           // 最大层数
    esp_mesh_set_vote_percentage(1);     // 根节点投票阈值
    esp_mesh_set_ap_authmode(WIFI_AUTH_WPA2_PSK);

    // 启动Mesh
    ESP_ERROR_CHECK(esp_mesh_start());

    ESP_LOGI(TAG, "Mesh初始化完成，本节点层: %d", esp_mesh_get_layer());
}
```

### 4.3 Mesh数据收发

```c
// Mesh数据包结构
typedef struct {
    uint8_t type;        // 数据类型
    uint8_t src_mac[6];  // 源MAC
    uint8_t dst_mac[6];  // 目的MAC
    uint8_t data[200];   // 数据
    uint16_t len;        // 数据长度
} mesh_data_t;

// 发送到根节点
void send_to_root(const uint8_t *data, uint16_t len)
{
    mesh_data_t mesh_data = {
        .type = MESH_DATA_TODS,  // 发送到外部网络（通过根节点）
    };
    memcpy(mesh_data.data, data, len);
    mesh_data.len = len;

    mesh_addr_t root_addr;
    esp_mesh_get_root_addr(&root_addr);

    esp_err_t err = esp_mesh_send(&root_addr, &mesh_data, len + 8,
                                   MESH_DATA_TODS, NULL, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "发送到根节点失败: %s", esp_err_to_name(err));
    }
}

// Mesh接收任务
void mesh_recv_task(void *param)
{
    mesh_addr_t from;
    mesh_data_t recv_data;
    int flag;

    while (1) {
        int err = esp_mesh_recv(&from, &recv_data, sizeof(recv_data),
                                 portMAX_DELAY, &flag, NULL, 0);
        if (err == ESP_OK) {
            ESP_LOGI(TAG, "收到数据 from " MACSTR ": %.*s",
                     MAC2STR(from.addr), recv_data.len, recv_data.data);
        }
    }
}
```

---

## 5. MQTT over WiFi

MQTT（Message Queuing Telemetry Transport）是物联网中最常用的消息协议，基于发布/订阅模式，轻量高效。

### 5.1 MQTT客户端

**ESP-MQTT组件：**

ESP-IDF内置MQTT客户端库，支持MQTT 3.1.1和MQTT 5.0。

```c
#include "mqtt_client.h"

static esp_mqtt_client_handle_t client = NULL;

// MQTT事件处理
static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;

    switch (event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT已连接");
            // 订阅主题
            esp_mqtt_client_subscribe(client, "device/control", 1);
            esp_mqtt_client_subscribe(client, "device/config", 0);
            break;

        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGW(TAG, "MQTT断开连接");
            // 客户端会自动重连
            break;

        case MQTT_EVENT_SUBSCRIBED:
            ESP_LOGI(TAG, "订阅成功, msg_id=%d", event->msg_id);
            break;

        case MQTT_EVENT_DATA:
            ESP_LOGI(TAG, "收到消息: topic=%.*s, data=%.*s",
                     event->topic_len, event->topic,
                     event->data_len, event->data);
            // 处理收到的消息
            handle_mqtt_message(event->topic, event->topic_len,
                               event->data, event->data_len);
            break;

        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT错误: %d", event->error_handle->error_type);
            break;

        case MQTT_EVENT_PUBLISHED:
            ESP_LOGI(TAG, "消息已发布, msg_id=%d", event->msg_id);
            break;
    }
}
```

**连接Broker：**

```c
void mqtt_init(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://broker.emqx.io:1883",
        // 或者使用结构体配置
        // .broker.address.hostname = "broker.emqx.io",
        // .broker.address.port = 1883,
        // .broker.address.transport = MQTT_TRANSPORT_OVER_TCP,
        .credentials.client_id = "esp32_device_001",
        .credentials.username = "user",
        .credentials.authentication.password = "password",
        .session.keepalive = 60,        // 心跳间隔（秒）
        .session.last_will = {           // 遗嘱消息
            .topic = "device/status",
            .msg = "offline",
            .msg_len = 7,
            .qos = 1,
            .retain = 1,
        },
        .network.reconnect_timeout_ms = 10000,  // 重连间隔
    };

    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID,
                                   mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);
}
```

**QoS等级：**

| QoS | 说明 | 可靠性 | 适用场景 |
|-----|------|--------|----------|
| 0 | 最多一次 | 不保证送达 | 传感器周期数据（允许丢失） |
| 1 | 至少一次 | 保证送达，可能重复 | 控制命令（需确认） |
| 2 | 恰好一次 | 保证不重复 | 计费/关键数据 |

```c
// QoS 0 - 发后即忘
esp_mqtt_client_publish(client, "sensor/temp", "25.5", 0, 0, 0);

// QoS 1 - 确保送达
esp_mqtt_client_publish(client, "device/alarm", "overheat", 0, 1, 0);

// QoS 2 - 恰好一次（开销最大）
esp_mqtt_client_publish(client, "billing/data", "payload", 0, 2, 0);
```

### 5.2 MQTT高级

**TLS/SSL加密连接：**

```c
// PEM格式证书（嵌入到固件中）
extern const uint8_t ca_cert_pem_start[] asm("_binary_ca_cert_pem_start");
extern const uint8_t ca_cert_pem_end[]   asm("_binary_ca_cert_pem_end");

void mqtt_tls_init(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtts://broker.emqx.io:8883",
        .broker.verification.certificate = (const char *)ca_cert_pem_start,
        .broker.verification.certificate_len = ca_cert_pem_end - ca_cert_pem_start,
        // 双向TLS认证（可选）
        // .credentials.authentication.certificate = client_cert_pem,
        // .credentials.authentication.key = client_key_pem,
    };

    client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(client, ESP_EVENT_ANY_ID,
                                   mqtt_event_handler, NULL);
    esp_mqtt_client_start(client);
}
```

**主题通配符：**

```
+  - 匹配单级主题
#  - 匹配多级主题（必须在最后）

示例：
sensor/+/temperature  -> 匹配 sensor/room1/temperature, sensor/room2/temperature
device/#              -> 匹配 device/status, device/control, device/config 等所有子主题
home/+/+/temperature  -> 匹配 home/floor1/room1/temperature
```

### 5.3 代码示例

**发布传感器数据：**

```c
#include "cJSON.h"

void publish_sensor_data(float temperature, float humidity, float pressure)
{
    // 构建JSON数据
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "temperature", temperature);
    cJSON_AddNumberToObject(root, "humidity", humidity);
    cJSON_AddNumberToObject(root, "pressure", pressure);
    cJSON_AddNumberToObject(root, "timestamp", (double)time(NULL));

    char *json_str = cJSON_PrintUnformatted(root);

    // 发布到MQTT（QoS 0，不等待确认）
    esp_mqtt_client_publish(client, "sensor/environment",
                            json_str, 0, 0, 0);

    ESP_LOGI(TAG, "发布传感器数据: %s", json_str);

    // 清理
    cJSON_free(json_str);
    cJSON_Delete(root);
}

// 定时发布任务
void sensor_publish_task(void *param)
{
    while (1) {
        float temp = read_temperature();   // 读取传感器
        float humi = read_humidity();
        float pres = read_pressure();

        publish_sensor_data(temp, humi, pres);

        vTaskDelay(pdMS_TO_TICKS(30000));  // 30秒发布一次
    }
}
```

**订阅控制命令：**

```c
void handle_mqtt_message(const char *topic, int topic_len,
                         const char *data, int data_len)
{
    // 确保字符串以null结尾
    char topic_str[128] = {0};
    char data_str[512] = {0};
    strncpy(topic_str, topic, min(topic_len, sizeof(topic_str) - 1));
    strncpy(data_str, data, min(data_len, sizeof(data_str) - 1));

    if (strcmp(topic_str, "device/control") == 0) {
        // 解析控制命令JSON
        cJSON *root = cJSON_Parse(data_str);
        if (root) {
            const char *cmd = cJSON_GetObjectItem(root, "cmd")->valuestring;

            if (strcmp(cmd, "led_on") == 0) {
                gpio_set_level(LED_GPIO, 1);
                publish_status("led", "on");
            } else if (strcmp(cmd, "led_off") == 0) {
                gpio_set_level(LED_GPIO, 0);
                publish_status("led", "off");
            } else if (strcmp(cmd, "reboot") == 0) {
                publish_status("system", "rebooting");
                vTaskDelay(pdMS_TO_TICKS(1000));
                esp_restart();
            } else if (strcmp(cmd, "set_interval") == 0) {
                int interval = cJSON_GetObjectItem(root, "value")->valueint;
                // 修改传感器上报间隔
                ESP_LOGI(TAG, "设置上报间隔: %d秒", interval);
            }

            cJSON_Delete(root);
        }
    } else if (strcmp(topic_str, "device/config") == 0) {
        // 处理配置更新
        ESP_LOGI(TAG, "收到配置更新: %s", data_str);
    }
}

void publish_status(const char *component, const char *status)
{
    char topic[64];
    snprintf(topic, sizeof(topic), "device/status/%s", component);

    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "status", status);
    cJSON_AddNumberToObject(root, "timestamp", (double)time(NULL));
    char *json = cJSON_PrintUnformatted(root);

    esp_mqtt_client_publish(client, topic, json, 0, 1, 1);  // QoS 1, Retain

    cJSON_free(json);
    cJSON_Delete(root);
}
```

---

## 6. HTTP/HTTPS客户端

ESP-IDF提供HTTP客户端库，支持GET/POST等方法，以及HTTPS加密通信。

### 6.1 GET/POST请求

```c
#include "esp_http_client.h"

// HTTP事件处理（可选，用于处理流式响应）
static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    switch (evt->event_id) {
        case HTTP_EVENT_ON_DATA:
            ESP_LOGI(TAG, "收到数据(%d字节): %.*s",
                     evt->data_len, evt->data_len, (char *)evt->data);
            break;
        case HTTP_EVENT_ERROR:
            ESP_LOGE(TAG, "HTTP错误");
            break;
        default:
            break;
    }
    return ESP_OK;
}

// GET请求
void http_get_request(void)
{
    esp_http_client_config_t config = {
        .url = "http://httpbin.org/get",
        .method = HTTP_METHOD_GET,
        .event_handler = http_event_handler,
        .timeout_ms = 10000,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);

    esp_err_t err = esp_http_client_perform(client);
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        int content_length = esp_http_client_get_content_length(client);
        ESP_LOGI(TAG, "HTTP GET 状态码: %d, 长度: %d", status, content_length);
    } else {
        ESP_LOGE(TAG, "HTTP GET 失败: %s", esp_err_to_name(err));
    }

    esp_http_client_cleanup(client);
}

// POST请求（JSON数据）
void http_post_request(const char *json_data)
{
    esp_http_client_config_t config = {
        .url = "http://httpbin.org/post",
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);

    // 设置请求头
    esp_http_client_set_header(client, "Content-Type", "application/json");

    // 设置POST数据
    esp_http_client_set_post_field(client, json_data, strlen(json_data));

    esp_err_t err = esp_http_client_perform(client);
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "POST状态码: %d", esp_http_client_get_status_code(client));
    }

    esp_http_client_cleanup(client);
}
```

### 6.2 HTTPS证书配置

```c
// CA证书嵌入（在CMakeLists.txt中添加：
// target_add_binary_data(my_app "certs/ca_cert.pem" TEXT)
extern const uint8_t server_cert_pem_start[] asm("_binary_ca_cert_pem_start");
extern const uint8_t server_cert_pem_end[]   asm("_binary_ca_cert_pem_end");

void https_request(void)
{
    esp_http_client_config_t config = {
        .url = "https://api.example.com/data",
        .cert_pem = (const char *)server_cert_pem_start,
        .timeout_ms = 15000,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        ESP_LOGI(TAG, "HTTPS状态码: %d", esp_http_client_get_status_code(client));
    }
    esp_http_client_cleanup(client);
}
```

### 6.3 OTA升级(基于HTTP)

```c
#include "esp_ota_ops.h"
#include "esp_http_client.h"

void ota_upgrade_task(void *param)
{
    esp_http_client_config_t config = {
        .url = "http://server.com/firmware/latest.bin",
        .timeout_ms = 30000,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "HTTP连接失败");
        return;
    }

    int content_length = esp_http_client_fetch_headers(client);
    ESP_LOGI(TAG, "固件大小: %d 字节", content_length);

    esp_ota_handle_t ota_handle;
    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    esp_ota_begin(update_partition, content_length, &ota_handle);

    char buf[1024];
    int total_read = 0;
    while (1) {
        int read = esp_http_client_read(client, buf, sizeof(buf));
        if (read <= 0) break;

        esp_ota_write(ota_handle, buf, read);
        total_read += read;

        // 显示进度
        if (content_length > 0) {
            int progress = (total_read * 100) / content_length;
            ESP_LOGI(TAG, "OTA进度: %d%%", progress);
        }
    }

    esp_ota_end(ota_handle);
    esp_ota_set_boot_partition(update_partition);
    esp_http_client_cleanup(client);

    ESP_LOGI(TAG, "OTA升级完成，重启...");
    esp_restart();
}
```

---

## 7. Socket编程

ESP-IDF基于lwIP协议栈，提供标准BSD Socket API。

### 7.1 TCP Client/Server

**TCP Client：**

```c
#include "lwip/sockets.h"
#include "lwip/netdb.h"

void tcp_client_task(void *param)
{
    struct sockaddr_in dest_addr;
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(8080);
    dest_addr.sin_addr.s_addr = inet_addr("192.168.1.100");

    int sock = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGE(TAG, "创建socket失败: %d", errno);
        return;
    }

    // 设置超时
    struct timeval timeout = { .tv_sec = 10 };
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

    int err = connect(sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    if (err != 0) {
        ESP_LOGE(TAG, "连接失败: %d", errno);
        close(sock);
        return;
    }

    ESP_LOGI(TAG, "TCP连接成功");

    // 发送数据
    const char *payload = "Hello from ESP32";
    send(sock, payload, strlen(payload), 0);

    // 接收响应
    char rx_buf[128];
    int len = recv(sock, rx_buf, sizeof(rx_buf) - 1, 0);
    if (len > 0) {
        rx_buf[len] = '\0';
        ESP_LOGI(TAG, "收到响应: %s", rx_buf);
    }

    close(sock);
    vTaskDelete(NULL);
}
```

**TCP Server：**

```c
void tcp_server_task(void *param)
{
    int listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_IP);

    struct sockaddr_in server_addr = {
        .sin_family = AF_INET,
        .sin_port = htons(8080),
        .sin_addr.s_addr = htonl(INADDR_ANY),
    };

    bind(listen_sock, (struct sockaddr *)&server_addr, sizeof(server_addr));
    listen(listen_sock, 3);  // 最多3个待处理连接

    ESP_LOGI(TAG, "TCP服务器监听端口 8080");

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);
        int client_sock = accept(listen_sock, (struct sockaddr *)&client_addr, &addr_len);

        if (client_sock < 0) {
            ESP_LOGE(TAG, "accept失败");
            continue;
        }

        ESP_LOGI(TAG, "新连接来自: %s:%d",
                 inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

        // 处理连接（实际应用中应为每个连接创建任务）
        char rx_buf[128];
        int len = recv(client_sock, rx_buf, sizeof(rx_buf) - 1, 0);
        if (len > 0) {
            rx_buf[len] = '\0';
            ESP_LOGI(TAG, "收到: %s", rx_buf);
            // 回发响应
            send(client_sock, rx_buf, len, 0);
        }

        close(client_sock);
    }
}
```

### 7.2 UDP通信

```c
void udp_send_receive(void)
{
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    struct sockaddr_in dest_addr = {
        .sin_family = AF_INET,
        .sin_port = htons(12345),
        .sin_addr.s_addr = inet_addr("192.168.1.255"),  // 广播地址
    };

    // 启用广播
    int broadcast = 1;
    setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));

    // 发送广播
    const char *msg = "ESP32 broadcast";
    sendto(sock, msg, strlen(msg), 0,
           (struct sockaddr *)&dest_addr, sizeof(dest_addr));

    // 接收数据
    char rx_buf[128];
    struct sockaddr_in source_addr;
    socklen_t addr_len = sizeof(source_addr);

    int len = recvfrom(sock, rx_buf, sizeof(rx_buf) - 1, 0,
                       (struct sockaddr *)&source_addr, &addr_len);
    if (len > 0) {
        rx_buf[len] = '\0';
        ESP_LOGI(TAG, "收到来自 %s: %s",
                 inet_ntoa(source_addr.sin_addr), rx_buf);
    }

    close(sock);
}
```

### 7.3 WebSocket客户端

```c
#include "esp_websocket_client.h"

static void websocket_event_handler(void *handler_args, esp_event_base_t base,
                                     int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;

    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            ESP_LOGI(TAG, "WebSocket已连接");
            break;

        case WEBSOCKET_EVENT_DATA:
            ESP_LOGI(TAG, "收到数据: %.*s", data->data_len, data->data_ptr);
            break;

        case WEBSOCKET_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "WebSocket断开");
            break;

        case WEBSOCKET_EVENT_ERROR:
            ESP_LOGE(TAG, "WebSocket错误");
            break;
    }
}

void websocket_init(void)
{
    esp_websocket_client_config_t ws_cfg = {
        .uri = "ws://echo.websocket.org",
        // .uri = "wss://echo.websocket.org",  // 加密连接
        // .cert_pem = ca_cert_pem,              // WSS证书
        .ping_interval_sec = 30,
        .task_stack = 4096,
    };

    esp_websocket_client_handle_t client = esp_websocket_client_init(&ws_cfg);
    esp_websocket_register_events(client, WEBSOCKET_EVENT_ANY,
                                  websocket_event_handler, NULL);
    esp_websocket_client_start(client);

    // 发送数据
    esp_websocket_client_send_text(client, "Hello WebSocket", strlen("Hello WebSocket"), 1000);

    // 关闭连接
    // esp_websocket_client_close(client, 1000);
}
```

---

## 8. 网络调试与优化

### 8.1 WiFi信号优化

**天线选择：**

ESP32开发板通常有三种天线配置：
- PCB板载天线：简单，无需外接，但增益低
- IPEX外接天线：通过U.FL/IPEX连接器外接天线，信号更强
- 两者共存：通过射频开关切换

```c
// 设置天线类型（部分模组支持）
// 在menuconfig中配置：
// ESP32_PHY_ANTENNA_SELECT  -> 自动/内置/外接
// ESP32_WIFI_TX_ANTENNA     -> 自动/内置/外接
// ESP32_WIFI_RX_ANTENNA     -> 自动/内置/外接
```

**功率设置：**

```c
// 设置WiFi发射功率（单位：0.25dBm）
// 范围：8(2dBm) 到 78(19.5dBm)，默认为34(8.5dBm)
esp_wifi_set_max_tx_power(78);  // 最大功率 19.5dBm

// 获取当前功率
int8_t power;
esp_wifi_get_max_tx_power(&power);
ESP_LOGI(TAG, "当前发射功率: %.2f dBm", power * 0.25);
```

### 8.2 内存优化

lwIP配置（在menuconfig中）：

```
Component config → lwIP
  ├── TCP_MSS: 1436 (默认) -> 降低可节省内存
  ├── TCP_SND_BUF: 5744 -> 根据需求调整
  ├── TCP_WND: 5744 -> 接收窗口大小
  ├── TCP_MAX_LISTEN_BACKLOG: 5 -> 监听队列深度
  ├── LWIP_NETCONN: 关闭（使用socket API时）
  └── LWIP_SOCKET: 启用
```

```c
// 运行时查看内存状态
ESP_LOGI(TAG, "空闲堆内存: %d 字节", esp_get_free_heap_size());
ESP_LOGI(TAG, "最小空闲堆: %d 字节", esp_get_minimum_free_heap_size());
```

### 8.3 网络超时处理

```c
// Socket超时设置
struct timeval timeout = {
    .tv_sec = 5,
    .tv_usec = 0,
};
setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

// HTTP客户端超时
esp_http_client_config_t config = {
    .timeout_ms = 10000,           // 请求超时
    .connect_timeout_ms = 5000,    // 连接超时
};

// MQTT重连策略
esp_mqtt_client_config_t mqtt_cfg = {
    .network.reconnect_timeout_ms = 10000,
    .session.keepalive = 60,
};
```

### 8.4 常见网络问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| WiFi连接失败 | SSID/密码错误 | 检查配置，使用SmartConfig |
| WiFi信号弱 | 距离远/干扰 | 更换天线，调整功率，换信道 |
| MQTT频繁断连 | 网络不稳定 | 增加keepalive，检查QoS |
| 内存不足 | lwIP缓冲过大 | 减小TCP窗口/MSS |
| DNS解析失败 | DNS服务器不可用 | 手动设置DNS |
| TCP连接超时 | 防火墙/端口未开放 | 检查网络配置 |

---

## 9. 实战应用场景

### 9.1 智能家居设备WiFi接入方案

```
[智能灯/插座] <--WiFi STA--> [家庭路由器] <--Internet--> [云平台/手机App]
     |
     +-- 首次配网：SmartConfig / BLE配网
     +-- 正常工作：WiFi STA + MQTT
     +-- 固件升级：OTA over HTTP
```

**配网+联网完整流程：**

```c
// 1. 检查NVS中是否有已保存的WiFi配置
bool has_saved_wifi(void)
{
    nvs_handle_t nvs;
    char ssid[33] = {0};
    size_t len = sizeof(ssid);

    if (nvs_open("wifi_cfg", NVS_READONLY, &nvs) == ESP_OK) {
        esp_err_t err = nvs_get_str(nvs, "ssid", ssid, &len);
        nvs_close(nvs);
        return (err == ESP_OK && strlen(ssid) > 0);
    }
    return false;
}

// 2. 主流程
void app_main(void)
{
    nvs_flash_init();

    if (has_saved_wifi()) {
        // 有保存的配置，直接连接
        wifi_init_sta_from_nvs();
    } else {
        // 无配置，启动配网
        wifi_init_ap_mode();
        start_webserver();    // Captive Portal
        start_smartconfig();  // 同时启动SmartConfig
    }
}
```

### 9.2 传感器节点MQTT上报

```
[温度/湿度传感器] --> ESP32 --> WiFi STA --> MQTT Broker --> [服务器/仪表盘]
                    |
                    +-- 定时采集（30s）
                    +-- 数据打包（JSON）
                    +-- 异常报警（QoS 1）
                    +-- 省电模式（Light Sleep）
```

```c
// 带省电的传感器上报
void sensor_node_task(void *param)
{
    while (1) {
        // 读取传感器
        sensor_data_t data = read_all_sensors();

        // 构建并发送JSON
        publish_sensor_data(data.temperature, data.humidity, data.battery);

        // 检查是否需要报警
        if (data.temperature > 40.0) {
            publish_alarm("high_temperature", data.temperature);
        }

        // 进入Light Sleep省电
        esp_sleep_enable_timer_wakeup(30 * 1000000);  // 30秒后唤醒
        esp_light_sleep_start();
    }
}
```

### 9.3 BLE配网+WiFi通信混合方案

这是许多智能设备的标准方案：首次配网使用BLE（低功耗、无需WiFi信息），正常工作切换到WiFi+MQTT。

```c
// 阶段1：BLE配网
void phase1_ble_provisioning(void)
{
    // 启动BLE Server，暴露WiFi配置特征
    ble_provisioning_server_init();

    // 等待手机App通过BLE发送WiFi信息
    wifi_config_t wifi_cfg;
    wait_for_ble_wifi_config(&wifi_cfg);  // 阻塞等待

    // 保存配置
    save_wifi_config_to_nvs(&wifi_cfg);

    // 关闭BLE
    ble_server_stop();

    ESP_LOGI(TAG, "BLE配网完成，切换到WiFi模式");
}

// 阶段2：WiFi + MQTT
void phase2_wifi_mqtt(void)
{
    wifi_init_sta(saved_ssid, saved_password);
    mqtt_init();

    while (1) {
        publish_sensor_data();
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}

// 主流程
void app_main(void)
{
    if (!has_saved_wifi()) {
        phase1_ble_provisioning();
    }
    phase2_wifi_mqtt();
}
```

### 9.4 ESP-NOW传感器网络

多个ESP32传感器节点通过ESP-NOW将数据汇聚到一个网关节点，网关再通过WiFi+MQTT上报到云端。

```
[传感器1] --ESP-NOW--> [网关ESP32] --WiFi/MQTT--> [云平台]
[传感器2] --ESP-NOW-->      |
[传感器3] --ESP-NOW-->      |
```

```c
// 传感器节点
void sensor_node_main(void)
{
    espnow_init();
    register_gateway_peer(gateway_mac);

    while (1) {
        sensor_data_t data = read_sensors();
        espnow_send_to_gateway((uint8_t *)&data, sizeof(data));
        vTaskDelay(pdMS_TO_TICKS(60000));  // 1分钟上报一次
    }
}

// 网关节点
void gateway_main(void)
{
    // 初始化ESP-NOW（接收传感器数据）
    espnow_init();
    espnow_register_recv_cb(gateway_recv_cb);

    // 初始化WiFi+MQTT（上报到云端）
    wifi_init_sta("ssid", "password");
    mqtt_init();

    while (1) {
        // 从队列中取出传感器数据并上报
        sensor_report_t report;
        if (xQueueReceive(sensor_queue, &report, pdMS_TO_TICKS(1000))) {
            mqtt_publish_report(&report);
        }
    }
}
```

---

## 10. API速查表

### WiFi API

| 函数 | 说明 |
|------|------|
| `esp_wifi_init()` | 初始化WiFi子系统 |
| `esp_wifi_set_mode()` | 设置WiFi模式（STA/AP/STA+AP） |
| `esp_wifi_set_config()` | 配置STA/AP参数 |
| `esp_wifi_start()` | 启动WiFi |
| `esp_wifi_stop()` | 停止WiFi |
| `esp_wifi_connect()` | STA连接AP |
| `esp_wifi_disconnect()` | STA断开连接 |
| `esp_wifi_scan_start()` | 开始扫描 |
| `esp_wifi_scan_get_ap_records()` | 获取扫描结果 |
| `esp_wifi_scan_get_ap_num()` | 获取扫描到的AP数量 |
| `esp_wifi_set_max_tx_power()` | 设置最大发射功率 |
| `esp_wifi_get_max_tx_power()` | 获取当前发射功率 |
| `esp_wifi_sta_get_ap_info()` | 获取已连接AP信息（含RSSI） |

### BLE API (NimBLE)

| 函数 | 说明 |
|------|------|
| `nimble_port_init()` | 初始化NimBLE |
| `ble_svc_gap_device_name_set()` | 设置设备名称 |
| `ble_gap_adv_start()` | 开始广播 |
| `ble_gap_adv_stop()` | 停止广播 |
| `ble_gap_disc()` | 开始扫描 |
| `ble_gap_disc_cancel()` | 取消扫描 |
| `ble_gap_connect()` | 发起连接 |
| `ble_gap_terminate()` | 断开连接 |
| `ble_gattc_notify_custom()` | 发送Notify |
| `ble_gattc_read()` | 读取特征值 |
| `ble_gattc_write()` | 写入特征值 |
| `ble_gattc_disc_svc_by_uuid()` | 发现服务 |
| `ble_gattc_disc_all_chrs()` | 发现特征 |
| `ble_att_mtu()` | 获取当前MTU |

### ESP-NOW API

| 函数 | 说明 |
|------|------|
| `esp_now_init()` | 初始化ESP-NOW |
| `esp_now_deinit()` | 反初始化 |
| `esp_now_add_peer()` | 添加对等设备 |
| `esp_now_del_peer()` | 删除对等设备 |
| `esp_now_is_peer_exist()` | 检查对等设备是否存在 |
| `esp_now_send()` | 发送数据 |
| `esp_now_register_send_cb()` | 注册发送回调 |
| `esp_now_register_recv_cb()` | 注册接收回调 |
| `esp_now_set_pmk()` | 设置主密钥 |

### MQTT API

| 函数 | 说明 |
|------|------|
| `esp_mqtt_client_init()` | 创建MQTT客户端 |
| `esp_mqtt_client_start()` | 启动客户端 |
| `esp_mqtt_client_stop()` | 停止客户端 |
| `esp_mqtt_client_destroy()` | 销毁客户端 |
| `esp_mqtt_client_publish()` | 发布消息 |
| `esp_mqtt_client_subscribe()` | 订阅主题 |
| `esp_mqtt_client_unsubscribe()` | 取消订阅 |
| `esp_mqtt_client_register_event()` | 注册事件回调 |

### HTTP Client API

| 函数 | 说明 |
|------|------|
| `esp_http_client_init()` | 创建HTTP客户端 |
| `esp_http_client_cleanup()` | 销毁客户端 |
| `esp_http_client_perform()` | 执行请求 |
| `esp_http_client_open()` | 打开连接（流式） |
| `esp_http_client_read()` | 读取响应数据 |
| `esp_http_client_set_header()` | 设置请求头 |
| `esp_http_client_set_post_field()` | 设置POST数据 |
| `esp_http_client_get_status_code()` | 获取状态码 |
| `esp_http_client_get_content_length()` | 获取内容长度 |

### NVS存储API

| 函数 | 说明 |
|------|------|
| `nvs_flash_init()` | 初始化NVS |
| `nvs_open()` | 打开命名空间 |
| `nvs_set_str()` | 写入字符串 |
| `nvs_get_str()` | 读取字符串 |
| `nvs_set_blob()` | 写入二进制 |
| `nvs_get_blob()` | 读取二进制 |
| `nvs_commit()` | 提交更改 |
| `nvs_close()` | 关闭句柄 |

---

## 附录：menuconfig关键配置

```
# WiFi
CONFIG_ESP_WIFI_STATIC_RX_BUFFER_NUM=10
CONFIG_ESP_WIFI_DYNAMIC_RX_BUFFER_NUM=32
CONFIG_ESP_WIFI_DYNAMIC_TX_BUFFER_NUM=32
CONFIG_ESP_WIFI_RX_BA_WIN=6
CONFIG_ESP_WIFI_SOFTAP_SUPPORT=w

# BLE（NimBLE）
CONFIG_BT_NIMBLE_ENABLED=y
CONFIG_BT_NIMBLE_MAX_CONNECTIONS=3
CONFIG_BT_NIMBLE_MAX_BONDS=5
CONFIG_BT_NIMBLE_MEM_ALLOC_MODE_INTERNAL=y

# MQTT
CONFIG_MQTT_PROTOCOL_311=y
CONFIG_MQTT_TRANSPORT_SSL=y

# HTTP
CONFIG_ESP_HTTP_CLIENT_ENABLE_HTTPS=y

# Mesh
CONFIG_ESP_WIFI_MESH_SUPPORT=y
```
