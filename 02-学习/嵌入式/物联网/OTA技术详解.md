# OTA技术详解

## 核心概念

- **OTA** - Over-The-Air 空中固件升级
- **A/B分区** - 双分区无缝切换
- **差分升级** - 增量更新减少传输量
- **回滚保护** - 版本回退安全机制

---

## 一、OTA架构

### 1.1 整体流程

```
┌─────────────────────────────────────────────────────┐
│                    OTA服务器                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ 固件存储  │  │ 版本管理  │  │ 设备分组管理  │       │
│  └──────────┘  └──────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │ 通知升级 │ ← MQTT/HTTP
    └────┬────┘
         ↓
┌─────────────────────────────────────────────────────┐
│                    设备端                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ 下载固件  │  │ 校验签名  │  │ 写入OTA分区   │       │
│  └──────────┘  └──────────┘  └──────────────┘       │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐       │
│  │ 设置启动  │  │ 重启切换  │  │ 确认升级完成   │       │
│  │ 分区标志  │  │          │  │              │       │
│  └──────────┘  └──────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────┘
```

---

### 1.2 分区方案

```c
// Flash分区表
typedef struct {
    const char *label;
    uint32_t offset;
    uint32_t size;
    uint32_t flags;
} partition_t;

// A/B双分区方案
partition_t partitions[] = {
    {"bootloader",  0x1000,    0x7000,   0},
    {"partition",   0x8000,    0xC00,    0},
    {"ota_0",       0x10000,   0x140000, 0},  // 1.25MB
    {"ota_1",       0x150000,  0x140000, 0},  // 1.25MB
    {"ota_data",    0x290000,  0x2000,   0},  // OTA状态
    {"storage",     0x292000,  0x16E000, 0},  // 数据存储
};

// OTA状态
typedef struct {
    uint32_t ota_state;      // 当前状态
    uint32_t ota_seq;        // 当前固件序号
    uint32_t new_seq;        // 新固件序号
    uint32_t boot_count;     // 启动计数
    uint32_t max_boot_count; // 最大启动次数(确认窗口)
    uint8_t  sha256[32];     // 固件哈希
} ota_state_t;

#define OTA_STATE_IDLE      0
#define OTA_STATE_PENDING   1   // 等待确认
#define OTA_STATE_CONFIRMED 2   // 已确认
#define OTA_STATE_ROLLED    3   // 已回滚
```

---

## 二、OTA下载

### 2.1 HTTP下载

```c
// HTTP OTA下载
typedef struct {
    uint32_t total_size;
    uint32_t downloaded;
    uint8_t sha256[32];
    uint32_t crc;
} ota_download_t;

int ota_http_download(const char *url, ota_download_t *ota) {
    // 1. 获取固件大小
    http_header_t headers[] = {
        {"Range", "bytes=0-"},
    };
    http_response_t *resp = http_head(url, headers, 1);
    ota->total_size = resp->content_length;
    ota->downloaded = 0;

    // 2. 分块下载
    sha256_context_t sha;
    sha256_init(&sha);
    ota->crc = 0xFFFFFFFF;

    while (ota->downloaded < ota->total_size) {
        char range[64];
        uint32_t end = ota->downloaded + OTA_CHUNK_SIZE - 1;
        if (end >= ota->total_size) end = ota->total_size - 1;
        snprintf(range, sizeof(range), "bytes=%u-%u", ota->downloaded, end);

        http_header_t chunk_headers[] = {
            {"Range", range},
        };
        resp = http_get(url, chunk_headers, 1);

        // 写入OTA分区
        uint32_t write_addr = OTA_0_OFFSET + ota->downloaded;
        flash_write(write_addr, resp->body, resp->body_len);

        // 更新校验
        sha256_update(&sha, resp->body, resp->body_len);
        ota->crc = crc32_update(ota->crc, resp->body, resp->body_len);
        ota->downloaded += resp->body_len;

        // 进度回调
        int progress = (ota->downloaded * 100) / ota->total_size;
        ota_progress_callback(progress);
    }

    sha256_final(&sha, ota->sha256);
    ota->crc ^= 0xFFFFFFFF;

    return 0;
}
```

---

### 2.2 MQTT通知触发

```c
// MQTT OTA升级流程
void mqtt_ota_handler(const char *topic, const uint8_t *data, int len) {
    // 解析OTA通知
    json_t *json = json_parse((char *)data);

    const char *version = json_get_string(json, "version");
    const char *url = json_get_string(json, "url");
    const char *hash = json_get_string(json, "sha256");
    uint32_t size = json_get_int(json, "size");

    // 检查版本
    if (compare_versions(version, get_current_version()) <= 0) {
        printf("Already up to date\n");
        return;
    }

    // 开始下载
    ota_download_t ota;
    ota_http_download(url, &ota);

    // 校验
    uint8_t expected_hash[32];
    hex_to_bytes(hash, expected_hash, 32);
    if (memcmp(ota.sha256, expected_hash, 32) != 0) {
        printf("Hash mismatch!\n");
        return;
    }

    // 设置启动分区
    esp_ota_set_boot_partition(esp_ota_get_next_update_partition(NULL));

    // 发送升级进度
    char progress[128];
    snprintf(progress, sizeof(progress),
             "{\"status\":\"downloading\",\"progress\":100}");
    mqtt_publish("device/ota/progress", progress);

    // 重启
    esp_restart();
}
```

---

## 三、差分升级

### 3.1 差分算法

```c
// 差分升级(bdiff/bspatch简化版)
typedef struct {
    uint8_t type;      // COPY或INSERT
    uint32_t offset;   // COPY源偏移
    uint32_t length;   // 数据长度
    uint8_t *data;     // INSERT数据
} diff_control_t;

// 应用差分包
int apply_diff(const uint8_t *old_fw, uint32_t old_size,
               const uint8_t *diff, uint32_t diff_size,
               uint8_t *new_fw, uint32_t *new_size) {
    const uint8_t *p = diff;
    const uint8_t *end = diff + diff_size;
    uint32_t out_offset = 0;

    while (p < end) {
        uint8_t type = *p++;
        uint32_t length = (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3];
        p += 4;

        if (type == 0) {
            // COPY: 从旧固件复制
            uint32_t offset = (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3];
            p += 4;
            memcpy(new_fw + out_offset, old_fw + offset, length);
            out_offset += length;
        } else if (type == 1) {
            // INSERT: 插入新数据
            memcpy(new_fw + out_offset, p, length);
            p += length;
            out_offset += length;
        }
    }

    *new_size = out_offset;
    return 0;
}

// 差分包大小对比
/*
 * 完整固件: 1.25MB
 * 差分包:   50-200KB (通常为原大小的5-15%)
 * 节省带宽: 80-95%
 */
```

---

## 四、安全机制

### 4.1 签名验证

```c
// RSA签名验证
bool ota_verify_signature(const uint8_t *firmware, uint32_t size,
                          const uint8_t *signature) {
    // 计算固件哈希
    uint8_t hash[32];
    sha256(firmware, size, hash);

    // RSA公钥验证
    rsa_public_key_t pub_key = {
        .n = ota_public_key_n,     // 公钥模数
        .e = 65537,                // 公钥指数
    };

    // PKCS#1 v1.5 签名验证
    uint8_t decrypted[256];
    rsa_verify(&pub_key, signature, decrypted);

    // 检查填充和哈希
    if (decrypted[0] != 0x00 || decrypted[1] != 0x01) return false;

    int padding_end = 2;
    while (decrypted[padding_end] == 0xFF) padding_end++;
    if (decrypted[padding_end] != 0x00) return false;

    // 提取并比较哈希
    uint8_t *sig_hash = decrypted + padding_end + 1;
    return (memcmp(sig_hash, hash, 32) == 0);
}
```

---

### 4.2 版本回滚保护

```c
// 回滚保护状态机
typedef enum {
    ROLLBACK_IDLE,
    ROLLBACK_UPGRADED,
    ROLLBACK_CONFIRMED,
    ROLLBACK_ROLLED_BACK
} rollback_state_t;

// 升级后启动
void ota_boot_check(void) {
    ota_state_t state;
    read_ota_state(&state);

    if (state.ota_state == OTA_STATE_PENDING) {
        state.boot_count++;
        write_ota_state(&state);

        if (state.boot_count >= state.max_boot_count) {
            // 启动次数达标，确认升级
            state.ota_state = OTA_STATE_CONFIRMED;
            write_ota_state(&state);
            printf("OTA upgrade confirmed\n");
        }
    }
}

// 回滚触发
void ota_rollback(void) {
    ota_state_t state;
    read_ota_state(&state);

    // 切换到上一个分区
    const esp_partition_t *prev = get_previous_partition();
    esp_ota_set_boot_partition(prev);

    state.ota_state = OTA_STATE_ROLLED;
    write_ota_state(&state);

    printf("Rolling back to previous firmware\n");
    esp_restart();
}
```

---

## 五、断点续传

### 5.1 下载进度保存

```c
// 断点续传
typedef struct {
    char url[256];
    uint32_t total_size;
    uint32_t downloaded;
    uint8_t sha256_partial[32];  // 已下载部分的哈希
    uint32_t crc_partial;
} ota_resume_info_t;

// 保存下载进度
void ota_save_progress(ota_resume_info_t *info) {
    kv_set("ota_resume", info, sizeof(ota_resume_info_t));
}

// 恢复下载
int ota_resume_download(ota_resume_info_t *info) {
    ota_download_t ota;
    ota.total_size = info->total_size;
    ota.downloaded = info->downloaded;
    memcpy(ota.sha256, info->sha256_partial, 32);
    ota.crc = info->crc_partial;

    // 从断点继续
    char range[64];
    snprintf(range, sizeof(range), "bytes=%u-", info->downloaded);

    http_header_t headers[] = {{"Range", range}};
    http_response_t *resp = http_get(info->url, headers, 1);

    // 继续下载...
    sha256_context_t sha;
    sha256_init(&sha);
    sha256_update(&sha, info->sha256_partial, 32);  // 继续哈希

    while (ota.downloaded < ota.total_size) {
        // 下载逻辑...
    }

    return 0;
}
```

---

## 六、OTA服务器接口

### 6.1 设备端API

```c
// OTA客户端
typedef struct {
    char device_id[32];
    char current_version[16];
    char hw_version[16];
} ota_client_info_t;

// 检查更新
int ota_check_update(ota_client_info_t *info) {
    char url[256];
    snprintf(url, sizeof(url),
             "https://ota.example.com/api/check?"
             "device=%s&fw=%s&hw=%s",
             info->device_id,
             info->current_version,
             info->hw_version);

    http_response_t *resp = http_get(url, NULL, 0);
    json_t *json = json_parse(resp->body);

    if (json_get_bool(json, "has_update")) {
        const char *new_ver = json_get_string(json, "version");
        const char *dl_url = json_get_string(json, "url");
        uint32_t size = json_get_int(json, "size");

        printf("Update available: %s → %s\n", info->current_version, new_ver);
        return ota_start_download(dl_url, size);
    }

    return 0;  // 已是最新
}
```

---

## 附录：OTA框架对比

| 框架 | 平台 | 特点 |
|------|------|------|
| ESP-IDF OTA | ESP32 | 原生支持 |
| Mender | Linux | 开源 |
| AWS IoT OTA | AWS | 云集成 |
| Azure IoT Hub | Azure | 企业级 |

---

## 相关链接

- [[ESP-IDF开发详解]] - ESP32 OTA
- [[物联网安全]] - 签名验证
- [[物联网平台]] - 平台OTA
- [[嵌入式文件系统]] - 存储基础
