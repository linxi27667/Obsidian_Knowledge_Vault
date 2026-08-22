# TCP/IP协议栈

## 核心概念

- **TCP** - 传输控制协议
- **IP** - 网际协议
- **Socket** - 网络编程接口
- **lwIP** - 轻量级IP协议栈

---

## 一、协议栈架构

### 1.1 TCP/IP分层

```
┌─────────────────────────────┐
│        应用层               │
│   HTTP、MQTT、DNS、DHCP    │
├─────────────────────────────┤
│        传输层               │
│   TCP、UDP                  │
├─────────────────────────────┤
│        网络层               │
│   IP、ICMP、ARP            │
├─────────────────────────────┤
│        链路层               │
│   Ethernet、WiFi            │
├─────────────────────────────┤
│        物理层               │
│   网线、无线电              │
└─────────────────────────────┘
```

---

### 1.2 数据封装

```
应用数据
    ↓
┌───────────────────────────┐
│ TCP头(20字节) + 数据      │  段(Segment)
└───────────────────────────┘
    ↓
┌───────────────────────────┐
│ IP头(20字节) + TCP段      │  包(Packet)
└───────────────────────────┘
    ↓
┌───────────────────────────┐
│ 以太网头(14) + IP包 + FCS │  帧(Frame)
└───────────────────────────┘
```

---

## 二、IP协议

### 2.1 IPv4

```c
// IP头结构
typedef struct {
    uint8_t  version_ihl;    // 版本(4位) + 头长度(4位)
    uint8_t  tos;            // 服务类型
    uint16_t total_length;   // 总长度
    uint16_t id;             // 标识
    uint16_t flags_offset;   // 标志(3位) + 偏移(13位)
    uint8_t  ttl;            // 生存时间
    uint8_t  protocol;       // 协议
    uint16_t checksum;       // 校验和
    uint32_t src_addr;       // 源IP
    uint32_t dst_addr;       // 目的IP
} ip_header_t;

// IP地址操作
#define IP_ADDR(a,b,c,d) ((uint32_t)((a)<<24|(b)<<16|(c)<<8|(d)))

uint32_t ip_addr = IP_ADDR(192, 168, 1, 100);

// IP校验和计算
uint16_t ip_checksum(uint16_t *data, int len) {
    uint32_t sum = 0;
    while (len > 1) {
        sum += *data++;
        len -= 2;
    }
    if (len == 1) {
        sum += *(uint8_t *)data;
    }
    while (sum >> 16) {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    return ~sum;
}
```

---

### 2.2 ICMP协议

```c
// ICMP头
typedef struct {
    uint8_t  type;
    uint8_t  code;
    uint16_t checksum;
    uint16_t id;
    uint16_t sequence;
} icmp_header_t;

// Ping实现
void send_ping(uint32_t target_ip) {
    icmp_header_t icmp;
    icmp.type = 8;  // Echo Request
    icmp.code = 0;
    icmp.id = htons(getpid());
    icmp.sequence = htons(seq_num++);
    icmp.checksum = 0;
    icmp.checksum = ip_checksum((uint16_t *)&icmp, sizeof(icmp));

    ip_send(target_ip, IP_PROTO_ICMP, &icmp, sizeof(icmp));
}

// ICMP处理
void handle_icmp(ip_header_t *ip, icmp_header_t *icmp, int len) {
    switch (icmp->type) {
        case 0:  // Echo Reply
            printf("Reply from %s\n", ip_to_str(ip->src_addr));
            break;
        case 8:  // Echo Request
            // 回复
            icmp->type = 0;
            icmp->checksum = 0;
            icmp->checksum = ip_checksum((uint16_t *)icmp, len);
            ip_send(ip->src_addr, IP_PROTO_ICMP, icmp, len);
            break;
    }
}
```

---

## 三、TCP协议

### 3.1 TCP头

```c
// TCP头结构
typedef struct {
    uint16_t src_port;
    uint16_t dst_port;
    uint32_t seq_num;
    uint32_t ack_num;
    uint8_t  data_offset;    // 数据偏移(4位) + 保留(4位)
    uint8_t  flags;
    uint16_t window;
    uint16_t checksum;
    uint16_t urgent_ptr;
} tcp_header_t;

// TCP标志
#define TCP_FIN  0x01
#define TCP_SYN  0x02
#define TCP_RST  0x04
#define TCP_PSH  0x08
#define TCP_ACK  0x10
#define TCP_URG  0x20

// TCP伪头(校验和计算)
typedef struct {
    uint32_t src_addr;
    uint32_t dst_addr;
    uint8_t  zero;
    uint8_t  protocol;
    uint16_t tcp_length;
} tcp_pseudo_header_t;
```

---

### 3.2 TCP状态机

```c
// TCP连接状态
typedef enum {
    TCP_CLOSED,
    TCP_LISTEN,
    TCP_SYN_SENT,
    TCP_SYN_RECEIVED,
    TCP_ESTABLISHED,
    TCP_FIN_WAIT_1,
    TCP_FIN_WAIT_2,
    TCP_CLOSE_WAIT,
    TCP_CLOSING,
    TCP_LAST_ACK,
    TCP_TIME_WAIT
} tcp_state_t;

// TCP连接
typedef struct {
    tcp_state_t state;
    uint32_t local_addr;
    uint16_t local_port;
    uint32_t remote_addr;
    uint16_t remote_port;
    uint32_t seq;
    uint32_t ack;
    uint16_t window;
    uint8_t *recv_buffer;
    int recv_len;
} tcp_conn_t;

// 三次握手
void tcp_connect(tcp_conn_t *conn, uint32_t dst_ip, uint16_t dst_port) {
    conn->remote_addr = dst_ip;
    conn->remote_port = dst_port;
    conn->seq = rand();
    conn->state = TCP_SYN_SENT;

    // 发送SYN
    tcp_send(conn, TCP_SYN, NULL, 0);
}

void handle_syn_ack(tcp_conn_t *conn, tcp_header_t *tcp) {
    if (conn->state == TCP_SYN_SENT) {
        conn->ack = ntohl(tcp->seq_num) + 1;
        conn->state = TCP_ESTABLISHED;

        // 发送ACK
        tcp_send(conn, TCP_ACK, NULL, 0);
    }
}
```

---

### 3.3 TCP数据传输

```c
// TCP发送数据
int tcp_send_data(tcp_conn_t *conn, uint8_t *data, int len) {
    if (conn->state != TCP_ESTABLISHED) return -1;

    tcp_send(conn, TCP_ACK | TCP_PSH, data, len);
    conn->seq += len;

    return len;
}

// TCP接收数据
int tcp_recv_data(tcp_conn_t *conn, uint8_t *buffer, int max_len) {
    if (conn->recv_len == 0) return 0;

    int copy_len = (conn->recv_len < max_len) ? conn->recv_len : max_len;
    memcpy(buffer, conn->recv_buffer, copy_len);
    conn->recv_len -= copy_len;

    return copy_len;
}

// TCP滑动窗口
typedef struct {
    uint32_t base;        // 窗口基址
    uint32_t next_seq;    // 下一个序列号
    uint16_t window_size; // 窗口大小
    uint8_t *buffer;
    int buffer_size;
} tcp_window_t;

bool tcp_window_can_send(tcp_window_t *win) {
    return (win->next_seq - win->base) < win->window_size;
}
```

---

## 四、UDP协议

### 4.1 UDP实现

```c
// UDP头
typedef struct {
    uint16_t src_port;
    uint16_t dst_port;
    uint16_t length;
    uint16_t checksum;
} udp_header_t;

// UDP发送
int udp_send(uint32_t dst_ip, uint16_t dst_port,
             uint16_t src_port, uint8_t *data, int len) {
    udp_header_t udp;
    udp.src_port = htons(src_port);
    udp.dst_port = htons(dst_port);
    udp.length = htons(sizeof(udp_header_t) + len);
    udp.checksum = 0;

    // 构建完整包
    uint8_t packet[sizeof(udp_header_t) + len];
    memcpy(packet, &udp, sizeof(udp_header_t));
    memcpy(packet + sizeof(udp_header_t), data, len);

    return ip_send(dst_ip, IP_PROTO_UDP, packet, sizeof(packet));
}

// UDP接收
void handle_udp(ip_header_t *ip, udp_header_t *udp, int len) {
    uint16_t dst_port = ntohs(udp->dst_port);
    uint8_t *data = (uint8_t *)udp + sizeof(udp_header_t);
    int data_len = ntohs(udp->length) - sizeof(udp_header_t);

    // 分发到应用层
    switch (dst_port) {
        case 53:   handle_dns(data, data_len); break;
        case 67:   handle_dhcp(data, data_len); break;
        case 123:  handle_ntp(data, data_len); break;
        default:   handle_udp_app(dst_port, data, data_len); break;
    }
}
```

---

## 五、Socket编程

### 5.1 BSD Socket API

```c
// Socket创建
int sock = socket(AF_INET, SOCK_STREAM, 0);

// 绑定
struct sockaddr_in addr;
addr.sin_family = AF_INET;
addr.sin_port = htons(8080);
addr.sin_addr.s_addr = INADDR_ANY;
bind(sock, (struct sockaddr *)&addr, sizeof(addr));

// 监听
listen(sock, 5);

// 接受连接
int client = accept(sock, NULL, NULL);

// 发送接收
send(client, data, len, 0);
recv(client, buffer, sizeof(buffer), 0);

// 关闭
close(client);
close(sock);
```

---

### 5.2 lwIP Socket

```c
// lwIP Socket API
#include "lwip/sockets.h"

void tcp_server_task(void *param) {
    int server_sock = lwip_socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(8080);
    addr.sin_addr.s_addr = INADDR_ANY;

    lwip_bind(server_sock, (struct sockaddr *)&addr, sizeof(addr));
    lwip_listen(server_sock, 5);

    while (1) {
        int client = lwip_accept(server_sock, NULL, NULL);
        if (client >= 0) {
            char buffer[128];
            int len = lwip_recv(client, buffer, sizeof(buffer), 0);
            if (len > 0) {
                lwip_send(client, buffer, len, 0);
            }
            lwip_close(client);
        }
    }
}
```

---

## 六、DNS解析

### 6.1 DNS客户端

```c
// DNS查询
typedef struct {
    uint16_t id;
    uint16_t flags;
    uint16_t questions;
    uint16_t answers;
    uint16_t authority;
    uint16_t additional;
} dns_header_t;

uint32_t dns_resolve(const char *hostname) {
    // 构建DNS查询
    uint8_t query[512];
    dns_header_t *dns = (dns_header_t *)query;

    dns->id = htons(rand());
    dns->flags = htons(0x0100);  // 标准查询
    dns->questions = htons(1);

    // 编码域名
    int offset = sizeof(dns_header_t);
    offset += encode_domain(query + offset, hostname);

    // 查询类型和类
    query[offset++] = 0; query[offset++] = 1;  // A记录
    query[offset++] = 0; query[offset++] = 1;  // IN类

    // 发送查询
    udp_send(DNS_SERVER, 53, 12345, query, offset);

    // 等待响应
    uint8_t response[512];
    int len = udp_recv(response, sizeof(response), 5000);

    // 解析响应
    if (len > 0) {
        return parse_dns_response(response, len);
    }

    return 0;
}
```

---

## 附录：常用端口

| 端口 | 协议 | 用途 |
|------|------|------|
| 20/21 | FTP | 文件传输 |
| 22 | SSH | 安全Shell |
| 23 | Telnet | 远程登录 |
| 25 | SMTP | 邮件发送 |
| 53 | DNS | 域名解析 |
| 80 | HTTP | Web服务 |
| 443 | HTTPS | 安全Web |
| 1883 | MQTT | 消息队列 |
| 5683 | CoAP | 受限应用 |

---

## 相关链接

- [[通信协议详解]] - 通信协议
- [[物联网协议]] - 物联网协议
- [[ESP-IDF开发详解]] - ESP网络编程
