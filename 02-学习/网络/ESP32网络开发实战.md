---
title: ESP32 网络开发实战
tags: [网络, ESP32, ESP-IDF, WiFi, MQTT]
created: 2026-05-04
---

# ESP32 网络开发实战

## 一、ESP32 联网完整流程

**类比**：
```
ESP32 上网就像一个人去公司上班：

1. 起床开机 → 初始化自己
2. 找路去公司 → 连接 WiFi
3. 签到拿工牌 → 获取 IP 地址（DHCP）
4. 查同事电话号码 → DNS 解析
5. 打通电话 → TCP 连接
6. 自我介绍 → MQTT CONNECT
7. 听对方确认 → CONNACK
8. 订阅感兴趣的话题 → SUBSCRIBE
9. 开始工作 → 收发消息 + 心跳
10. 下班/异常 → 断线重连
```

### 完整流程图

```
┌─ ESP32 上电 ─────────────────────────────────────┐
│                                                   │
│  ① WiFi 初始化                                     │
│     esp_wifi_init()                               │
│                                                   │
│  ② 扫描并连接 AP                                   │
│     esp_wifi_connect()                             │
│     ↓                                              │
│     收到 WIFI_EVENT_STA_CONNECTED                   │
│                                                   │
│  ③ DHCP 获取 IP（DORA 四步）                         │
│     ↓                                              │
│     收到 IP_EVENT_STA_GOT_IP                        │
│     IP: 192.168.1.100/24                           │
│     Gateway: 192.168.1.1                           │
│     DNS: 192.168.1.1                               │
│                                                   │
│  ④ DNS 解析 broker.emqx.io                          │
│     getaddrinfo() → 13.212.94.125                  │
│                                                   │
│  ⑤ TCP 三次握手                                     │
│     192.168.1.100:xxxxx ↔ 13.212.94.125:1883       │
│     状态: ESTABLISHED                              │
│                                                   │
│  ⑥ 发送 MQTT CONNECT                                │
│     Client ID: "xiaozhi_master"                     │
│     Keep Alive: 240s                               │
│                                                   │
│  ⑦ 收到 CONNACK (Return Code 0)                     │
│     状态: MQTT_CONNECTED                           │
│                                                   │
│  ⑧ 发送 SUBSCRIBE                                   │
│     Topic: "xiaozhi/iot/cmd/#" QoS: 0              │
│                                                   │
│  ⑨ 收到 SUBACK                                     │
│     订阅成功                                        │
│                                                   │
│  ⑩ 发布上线通知                                     │
│     PUBLISH "xiaozhi/iot/announce"                  │
│     {"device":"xiaozhi_master","online":true}       │
│                                                   │
│  ⑪ 进入事件循环                                     │
│     每 90s 发送 PINGREQ                             │
│     收到 PUBLISH → 处理命令 → 发布 RESP              │
│                                                   │
│  ⑫ 连接断开                                         │
│     TCP 四次挥手 / 异常断开                           │
│     等待 60s → 重新从步骤 ② 开始                      │
└───────────────────────────────────────────────────┘
```

---

## 二、ESP32 WiFi 连接代码模板

```c
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"

static const char *TAG = "wifi";

static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "WiFi 断开，重连...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "获取到 IP: " IPSTR, IP2STR(&event->ip_info.ip));
        // WiFi 连接完成，可以开始 MQTT 连接了
    }
}

void wifi_init_sta(void) {
    esp_wifi_set_mode(WIFI_MODE_STA);
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "YourWiFiSSID",
            .password = "YourPassword",
        },
    };
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
}
```

---

## 三、ESP32 MQTT 客户端

### 3.1 基本配置

```c
#include "mqtt_client.h"

static esp_mqtt_client_handle_t mqtt_client = NULL;

void mqtt_app_start(void) {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://192.168.1.100:1883",
        .credentials.client_id = "xiaozhi_master",
        .session.keepalive = 240,
        .network.disable_auto_reconnect = false,
        .session.reconnect_timeout_ms = 60000,
    };

    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
}
```

### 3.2 事件处理

```c
static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                                int32_t event_id, void *event_data) {
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT 连接成功");
        esp_mqtt_client_subscribe(mqtt_client, "xiaozhi/iot/cmd/#", 0);
        break;

    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT 断开连接");
        break;

    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "收到消息: topic=%.*s, data=%.*s",
                 event->topic_len, event->topic,
                 event->data_len, event->data);
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGD(TAG, "消息发布成功, msg_id=%d", event->msg_id);
        break;

    case MQTT_EVENT_SUBSCRIBED:
        ESP_LOGD(TAG, "订阅成功, msg_id=%d", event->msg_id);
        break;

    default:
        break;
    }
}
```

### 3.3 发布和订阅

```c
// 发布消息（QoS 0）
esp_mqtt_client_publish(mqtt_client,
    "xiaozhi/iot/resp/xiaozhi_master",
    "{\"status\":\"ok\"}", 0, 0, 0);

// 发布消息（QoS 1）
esp_mqtt_client_publish(mqtt_client,
    "xiaozhi/iot/announce/xiaozhi_master",
    "{\"device\":\"xiaozhi_master\",\"online\":true}", 0, 1, 1);

// 订阅主题
esp_mqtt_client_subscribe(mqtt_client, "xiaozhi/iot/cmd/#", 0);

// 取消订阅
esp_mqtt_client_unsubscribe(mqtt_client, "xiaozhi/iot/cmd/#");
```

---

## 四、ESP32 常见问题排查

### 4.1 无法上网

```
排查路径：

① WiFi 连接了吗？
   串口日志找: "got ip" 或 "WIFI_EVENT_STA_CONNECTED"

② 获取到 IP 了吗？
   串口日志找: "ip:192.168.x.x"

③ 能 ping 通网关吗？
   串口 ping 192.168.1.1 → 通 = 局域网正常

④ 能 ping 通外网吗？
   串口 ping 8.8.8.8 → 通 = 路由器 NAT 正常

⑤ DNS 正常吗？
   串口 ping broker.emqx.io → 解析出 IP = DNS 正常

⑥ TCP 能连上吗？
   MQTT 日志找: "TCP connected" → "MQTT connected"
```

### 4.2 网络层到应用层对照

```
OSI 层     排查方法                          常见错误
───────────────────────────────────────────────────────
物理层     WiFi 信号强度、天线连接            RSSI < -80dBm
数据链路层 WiFi 关联状态、ARP 表              AUTH_EXPIRE 认证失败
网络层     ping、路由表、IP 配置              子网掩码错误、网关错误
传输层     netstat 看 TCP 状态               端口不通、防火墙阻拦
应用层     MQTT 日志、DNS 解析结果            CONNECT 报文参数错误
```

### 4.3 ESP32 连接不上 Broker

| 排查步骤 | 命令/操作 |
|----------|----------|
| 1. WiFi 是否连上 | 串口日志看 `got ip` |
| 2. Broker 是否在运行 | `docker ps` |
| 3. 端口是否开放 | `nc -zv 192.168.1.x 1883` |
| 4. 防火墙是否放行 | Windows Defender 防火墙 |
| 5. Broker 日志 | `docker logs mosquitto` |

### 4.4 ESP32 在同一网络但连不上

- 确认 ESP32 和电脑在**同一个子网**（如都在 192.168.1.x）
- ESP32 连接的是电脑所在 WiFi，不是手机热点
- 路由器没有开启 AP 隔离

### 4.5 NTP 时间同步

```c
// ESP-IDF SNTP 配置
#include "esp_sntp.h"

void time_sync_init(void) {
    esp_sntp_config_t config = ESP_SNTP_DEFAULT_CONFIG("pool.ntp.org");
    esp_sntp_init(&config);

    // 等待时间同步完成
    while (esp_sntp_sync_status() != ESP_SNTP_SYNC_STATUS_COMPLETED) {
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}
```

---

## 五、ESP32 端口使用速查

```
ESP32 作为 MQTT 客户端 → 连接到 Broker 的 1883 端口
ESP32 作为 Web Server  → 监听 80 端口
ESP32 作为 OTA 接收端  → 通常 3232 或自定义端口
ESP32 mDNS 响应        → UDP 5353
ESP32 NTP 时间同步     → UDP 123
ESP32 SNTP             → UDP 123（ESP-IDF 内置）
```
