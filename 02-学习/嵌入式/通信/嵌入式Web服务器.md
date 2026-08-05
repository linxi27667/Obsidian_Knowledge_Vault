# 嵌入式Web服务器

## 核心概念

- **HTTP** - 超文本传输协议
- **WebSocket** - 全双工通信
- **REST API** - 资源导向接口
- **CGI** - 通用网关接口

---

## 一、轻量级HTTP服务器

### 1.1 HTTP请求解析

```c
// HTTP请求解析
typedef struct {
    char method[8];      // GET, POST, PUT, DELETE
    char path[128];      // URI路径
    char version[16];    // HTTP/1.1
    char host[64];
    char content_type[64];
    int content_length;
    char *body;
    int body_len;

    // 查询参数
    struct {
        char key[32];
        char value[64];
    } query_params[8];
    int param_count;

    // 头部
    struct {
        char name[32];
        char value[128];
    } headers[16];
    int header_count;
} http_request_t;

int http_parse_request(const char *data, int len, http_request_t *req) {
    const char *p = data;
    const char *end = data + len;

    // 解析请求行: METHOD PATH VERSION
    int i = 0;
    while (p < end && *p != ' ' && i < 7) req->method[i++] = *p++;
    req->method[i] = '\0';
    p++;  // 跳过空格

    i = 0;
    while (p < end && *p != ' ' && *p != '?' && i < 127) req->path[i++] = *p++;
    req->path[i] = '\0';

    // 解析查询参数
    if (*p == '?') {
        p++;
        req->param_count = 0;
        while (p < end && *p != ' ' && req->param_count < 8) {
            i = 0;
            while (p < end && *p != '=' && *p != '&' && *p != ' ' && i < 31)
                req->query_params[req->param_count].key[i++] = *p++;
            req->query_params[req->param_count].key[i] = '\0';
            if (*p == '=') {
                p++;
                i = 0;
                while (p < end && *p != '&' && *p != ' ' && i < 63)
                    req->query_params[req->param_count].value[i++] = *p++;
                req->query_params[req->param_count].value[i] = '\0';
            }
            if (*p == '&') p++;
            req->param_count++;
        }
    }

    p++;  // 跳过空格
    i = 0;
    while (p < end && *p != '\r' && i < 15) req->version[i++] = *p++;
    req->version[i] = '\0';
    p += 2;  // 跳过\r\n

    // 解析头部
    req->header_count = 0;
    while (p < end && *p != '\r' && req->header_count < 16) {
        i = 0;
        while (p < end && *p != ':' && i < 31)
            req->headers[req->header_count].name[i++] = *p++;
        req->headers[req->header_count].name[i] = '\0';
        p += 2;  // 跳过": "
        i = 0;
        while (p < end && *p != '\r' && i < 127)
            req->headers[req->header_count].value[i++] = *p++;
        req->headers[req->header_count].value[i] = '\0';
        p += 2;  // 跳过\r\n
        req->header_count++;
    }
    p += 2;  // 跳过空行

    // 提取Content-Length
    req->content_length = 0;
    for (i = 0; i < req->header_count; i++) {
        if (strcasecmp(req->headers[i].name, "Content-Length") == 0) {
            req->content_length = atoi(req->headers[i].value);
        }
    }

    // 载荷
    req->body = (char *)p;
    req->body_len = end - p;

    return 0;
}
```

---

### 1.2 HTTP响应构建

```c
// HTTP响应
typedef struct {
    int status_code;
    char status_text[32];
    char content_type[64];
    char *body;
    int body_len;
    bool keep_alive;
} http_response_t;

int http_build_response(uint8_t *buf, int max_len, http_response_t *resp) {
    int offset = 0;

    // 状态行
    offset += snprintf((char *)buf + offset, max_len - offset,
                       "HTTP/1.1 %d %s\r\n",
                       resp->status_code, resp->status_text);

    // 头部
    offset += snprintf((char *)buf + offset, max_len - offset,
                       "Content-Type: %s\r\n"
                       "Content-Length: %d\r\n"
                       "Connection: %s\r\n",
                       resp->content_type,
                       resp->body_len,
                       resp->keep_alive ? "keep-alive" : "close");

    // CORS头(可选)
    offset += snprintf((char *)buf + offset, max_len - offset,
                       "Access-Control-Allow-Origin: *\r\n");

    // 空行
    buf[offset++] = '\r';
    buf[offset++] = '\n';

    // 载荷
    if (resp->body_len > 0) {
        memcpy(buf + offset, resp->body, resp->body_len);
        offset += resp->body_len;
    }

    return offset;
}

// 常用响应
void http_send_ok(int client, const char *body) {
    http_response_t resp = {
        .status_code = 200,
        .content_type = "application/json",
        .body = (char *)body,
        .body_len = strlen(body),
    };
    strcpy(resp.status_text, "OK");

    uint8_t buf[1024];
    int len = http_build_response(buf, sizeof(buf), &resp);
    lwip_send(client, buf, len, 0);
}

void http_send_not_found(int client) {
    const char *body = "{\"error\":\"Not Found\"}";
    http_response_t resp = {
        .status_code = 404,
        .content_type = "application/json",
        .body = (char *)body,
        .body_len = strlen(body),
    };
    strcpy(resp.status_text, "Not Found");

    uint8_t buf[512];
    int len = http_build_response(buf, sizeof(buf), &resp);
    lwip_send(client, buf, len, 0);
}
```

---

## 二、REST API框架

### 2.1 路由注册

```c
// 路由处理器
typedef void (*http_handler_t)(int client, http_request_t *req);

typedef struct {
    char method[8];
    char path[64];
    http_handler_t handler;
} http_route_t;

#define MAX_ROUTES 32
static http_route_t routes[MAX_ROUTES];
static int route_count = 0;

void http_register_route(const char *method, const char *path,
                         http_handler_t handler) {
    if (route_count >= MAX_ROUTES) return;
    strcpy(routes[route_count].method, method);
    strcpy(routes[route_count].path, path);
    routes[route_count].handler = handler;
    route_count++;
}

// 路由匹配
http_handler_t http_find_route(const char *method, const char *path) {
    for (int i = 0; i < route_count; i++) {
        if (strcmp(routes[i].method, method) == 0 &&
            strcmp(routes[i].path, path) == 0) {
            return routes[i].handler;
        }
    }
    return NULL;
}

// 路径参数提取
bool http_extract_param(const char *path, const char *pattern,
                        const char *param_name, char *value, int max_len) {
    // /api/sensors/{id} → /api/sensors/123 → id=123
    const char *p = path;
    const char *t = pattern;

    while (*p && *t) {
        if (*t == '{') {
            const char *end = strchr(t, '}');
            if (!end) return false;

            // 匹配参数名
            if (strncmp(t + 1, param_name, end - t - 1) == 0) {
                int i = 0;
                while (*p && *p != '/' && i < max_len - 1) {
                    value[i++] = *p++;
                }
                value[i] = '\0';
                return true;
            }
            t = end + 1;
        } else {
            if (*p != *t) return false;
            p++;
            t++;
        }
    }
    return false;
}
```

---

### 2.2 JSON处理

```c
// 简单JSON构建器
typedef struct {
    char *buf;
    int offset;
    int max_len;
    bool first;
} json_builder_t;

void json_init(json_builder_t *jb, char *buf, int max_len) {
    jb->buf = buf;
    jb->offset = 0;
    jb->max_len = max_len;
    jb->first = true;
    jb->buf[jb->offset++] = '{';
}

void json_add_string(json_builder_t *jb, const char *key, const char *value) {
    if (!jb->first) jb->buf[jb->offset++] = ',';
    jb->offset += snprintf(jb->buf + jb->offset, jb->max_len - jb->offset,
                           "\"%s\":\"%s\"", key, value);
    jb->first = false;
}

void json_add_int(json_builder_t *jb, const char *key, int value) {
    if (!jb->first) jb->buf[jb->offset++] = ',';
    jb->offset += snprintf(jb->buf + jb->offset, jb->max_len - jb->offset,
                           "\"%s\":%d", key, value);
    jb->first = false;
}

void json_add_float(json_builder_t *jb, const char *key, float value, int precision) {
    if (!jb->first) jb->buf[jb->offset++] = ',';
    jb->offset += snprintf(jb->buf + jb->offset, jb->max_len - jb->offset,
                           "\"%s\":%.*f", key, precision, value);
    jb->first = false;
}

void json_end(json_builder_t *jb) {
    jb->buf[jb->offset++] = '}';
    jb->buf[jb->offset] = '\0';
}

// 传感器API示例
void handle_get_temperature(int client, http_request_t *req) {
    float temp = sensor_read_temperature();
    float humidity = sensor_read_humidity();

    char buf[128];
    json_builder_t jb;
    json_init(&jb, buf, sizeof(buf));
    json_add_float(&jb, "temperature", temp, 1);
    json_add_float(&jb, "humidity", humidity, 1);
    json_end(&jb);

    http_send_ok(client, buf);
}
```

---

## 三、WebSocket

### 3.1 WebSocket握手

```c
// WebSocket握手
int websocket_handshake(int client, http_request_t *req) {
    // 获取Sec-WebSocket-Key
    char ws_key[128] = {0};
    for (int i = 0; i < req->header_count; i++) {
        if (strcasecmp(req->headers[i].name, "Sec-WebSocket-Key") == 0) {
            strcpy(ws_key, req->headers[i].value);
            break;
        }
    }

    // 计算Accept Key: SHA1(Key + GUID) → Base64
    const char *ws_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    char accept_input[256];
    snprintf(accept_input, sizeof(accept_input), "%s%s", ws_key, ws_guid);

    uint8_t sha1[20];
    sha1_calc((uint8_t *)accept_input, strlen(accept_input), sha1);

    char accept_key[64];
    base64_encode(sha1, 20, accept_key);

    // 发送响应
    char response[256];
    int len = snprintf(response, sizeof(response),
                       "HTTP/1.1 101 Switching Protocols\r\n"
                       "Upgrade: websocket\r\n"
                       "Connection: Upgrade\r\n"
                       "Sec-WebSocket-Accept: %s\r\n"
                       "\r\n", accept_key);

    lwip_send(client, response, len, 0);
    return 0;
}
```

---

### 3.2 WebSocket帧

```c
// WebSocket帧格式
typedef struct {
    uint8_t  fin : 1;
    uint8_t  rsv : 3;
    uint8_t  opcode : 4;
    uint8_t  mask : 1;
    uint8_t  payload_len;
    uint32_t masking_key;
    uint8_t *payload;
    int payload_length;
} ws_frame_t;

// WebSocket操作码
#define WS_CONTINUATION  0x0
#define WS_TEXT          0x1
#define WS_BINARY        0x2
#define WS_CLOSE         0x8
#define WS_PING          0x9
#define WS_PONG          0xA

int ws_build_frame(uint8_t *buf, uint8_t opcode, const uint8_t *data, int len) {
    int offset = 0;

    buf[offset++] = 0x80 | opcode;  // FIN + opcode

    if (len < 126) {
        buf[offset++] = len;
    } else if (len < 65536) {
        buf[offset++] = 126;
        buf[offset++] = len >> 8;
        buf[offset++] = len & 0xFF;
    } else {
        buf[offset++] = 127;
        // 64位长度(嵌入式通常不需要)
    }

    memcpy(buf + offset, data, len);
    offset += len;

    return offset;
}

// WebSocket消息处理
void ws_handle_message(int client, uint8_t *data, int len) {
    ws_frame_t frame;
    frame.opcode = data[0] & 0x0F;
    frame.mask = (data[1] >> 7) & 1;

    int offset = 2;
    uint64_t payload_len = data[1] & 0x7F;

    if (payload_len == 126) {
        payload_len = (data[2] << 8) | data[3];
        offset += 2;
    } else if (payload_len == 127) {
        // 64位长度
        offset += 8;
    }

    if (frame.mask) {
        memcpy(&frame.masking_key, data + offset, 4);
        offset += 4;
    }

    frame.payload = data + offset;
    frame.payload_length = payload_len;

    // 解码载荷
    if (frame.mask) {
        for (int i = 0; i < frame.payload_length; i++) {
            frame.payload[i] ^= ((uint8_t *)&frame.masking_key)[i % 4];
        }
    }

    switch (frame.opcode) {
        case WS_TEXT:
        case WS_BINARY:
            // 处理消息
            ws_process_data(client, frame.payload, frame.payload_length);
            break;
        case WS_PING: {
            // 回复PONG
            uint8_t pong[128];
            int pong_len = ws_build_frame(pong, WS_PONG,
                                          frame.payload, frame.payload_length);
            lwip_send(client, pong, pong_len, 0);
            break;
        }
        case WS_CLOSE:
            lwip_close(client);
            break;
    }
}
```

---

## 四、SSE(Server-Sent Events)

### 4.1 SSE推送

```c
// SSE响应头
void sse_start(int client) {
    const char *headers =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/event-stream\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: keep-alive\r\n"
        "\r\n";
    lwip_send(client, headers, strlen(headers), 0);
}

// SSE事件发送
void sse_send_event(int client, const char *event, const char *data) {
    char buf[256];
    int len;

    if (event) {
        len = snprintf(buf, sizeof(buf), "event: %s\ndata: %s\n\n", event, data);
    } else {
        len = snprintf(buf, sizeof(buf), "data: %s\n\n", data);
    }

    lwip_send(client, buf, len, 0);
}

// 实时传感器数据推送
void sse_sensor_stream(int client) {
    sse_start(client);

    while (1) {
        float temp = sensor_read_temperature();
        char data[64];
        snprintf(data, sizeof(data), "{\"temperature\":%.1f}", temp);
        sse_send_event(client, "sensor", data);

        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## 五、静态文件服务

### 5.1 内嵌文件系统

```c
// 内嵌文件资源
typedef struct {
    const char *path;
    const char *content_type;
    const uint8_t *data;
    int data_len;
} embedded_file_t;

// 内嵌HTML/CSS/JS
static const char index_html[] =
    "<!DOCTYPE html>"
    "<html><head><title>ESP32</title></head>"
    "<body><h1>Embedded Web Server</h1>"
    "<div id=\"data\"></div>"
    "<script>"
    "var ws = new WebSocket('ws://' + location.host + '/ws');"
    "ws.onmessage = function(e) {"
    "  document.getElementById('data').innerText = e.data;"
    "};"
    "</script></body></html>";

static const embedded_file_t files[] = {
    {"/", "text/html", (uint8_t *)index_html, sizeof(index_html) - 1},
};

void handle_static_file(int client, const char *path) {
    for (int i = 0; i < sizeof(files)/sizeof(files[0]); i++) {
        if (strcmp(files[i].path, path) == 0) {
            http_response_t resp = {
                .status_code = 200,
                .body = (char *)files[i].data,
                .body_len = files[i].data_len,
            };
            strcpy(resp.status_text, "OK");
            strcpy(resp.content_type, files[i].content_type);

            uint8_t buf[4096];
            int len = http_build_response(buf, sizeof(buf), &resp);
            lwip_send(client, buf, len, 0);
            return;
        }
    }
    http_send_not_found(client);
}
```

---

## 附录：嵌入式Web框架对比

| 框架 | 平台 | 特点 |
|------|------|------|
| lwIP httpd | 通用 | 轻量级，CGI/SSI |
| Mongoose | 通用 | 功能丰富 |
| ESP-IDF httpd | ESP32 | 集成度高 |
| CivetWeb | 通用 | C实现 |

---

## 相关链接

- [[TCP-IP协议栈]] - 网络基础
- [[物联网平台]] - 云平台接入
- [[LVGL]] - GUI与Web结合
- [[物联网安全]] - HTTPS安全
