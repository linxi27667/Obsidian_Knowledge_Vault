# Zephyr RTOS详解

## 核心概念

- **设备树** - 硬件描述语言
- **Kconfig** - 内核配置系统
- **工作队列** - 延迟执行机制
- **Zephyr** - Linux基金会支持的RTOS

---

## 一、Zephyr架构

### 1.1 分层架构

```
┌─────────────────────────────────────┐
│           应用层(Application)        │
├─────────────────────────────────────┤
│           中间件(Middleware)          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │TCP/IP│ │BLE  │ │USB  │ │文件  │  │
│  └─────┘ └─────┘ └─────┘ └─────┘  │
├─────────────────────────────────────┤
│           内核(Kernel)               │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │调度器│ │内存  │ │IPC  │ │设备  │  │
│  └─────┘ └─────┘ └─────┘ └─────┘  │
├─────────────────────────────────────┤
│           HAL(硬件抽象)              │
│  ┌─────┐ ┌─────┐ ┌─────┐           │
│  │MCU  │ │外设  │ │驱动  │           │
│  └─────┘ └─────┘ └─────┘           │
├─────────────────────────────────────┤
│           硬件(Hardware)             │
└─────────────────────────────────────┘
```

### 1.2 内核配置

```c
// prj.conf - 项目配置文件
// CONFIG_HEAP_MEM_POOL_SIZE=4096
// CONFIG_MAIN_STACK_SIZE=2048
// CONFIG_NUM_PREEMPT_PRIORITIES=32
// CONFIG_SYSTEM_WORKQUEUE_STACK_SIZE=2048

// Kconfig语法
// config MY_FEATURE
//     bool "Enable my feature"
//     default y
//     depends on SENSOR
//     help
//       Enable custom feature.

// 使用配置项
// #ifdef CONFIG_MY_FEATURE
//     my_feature_init();
// #endif
```

---

## 二、设备树

### 2.1 设备树语法

```dts
// 设备树源文件(.dts)
// 根节点
/ {
    chosen {
        zephyr,sram = &sram0;
        zephyr,console = &uart0;
    };

    aliases {
        led0 = &green_led;
        sw0 = &button0;
    };
};

// 覆盖板级配置(.overlay)
// / {
//     chosen {
//         zephyr,console = &uart1;
//     };
// };

// GPIO LED定义
/ {
    leds {
        compatible = "gpio-leds";
        green_led: led_0 {
            gpios = <&gpio0 13 GPIO_ACTIVE_HIGH>;
            label = "Green LED";
        };
    };

    buttons {
        compatible = "gpio-keys";
        button0: button_0 {
            gpios = <&gpio0 11 (GPIO_PULL_UP | GPIO_ACTIVE_LOW)>;
            label = "Push button";
        };
    };
};

// I2C设备
&i2c0 {
    status = "okay";
    clock-frequency = <I2C_BITRATE_FAST>;

    bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
        label = "BME280";
    };
};

// SPI设备
&spi0 {
    status = "okay";
    cs-gpios = <&gpio0 4 GPIO_ACTIVE_LOW>;

    display@0 {
        compatible = "ilitek,ili9341";
        reg = <0>;
        spi-max-frequency = <10000000>;
        reset-gpios = <&gpio0 5 GPIO_ACTIVE_LOW>;
        dc-gpios = <&gpio0 6 GPIO_ACTIVE_HIGH>;
    };
};
```

### 2.2 设备树API

```c
#include <zephyr/device.h>
#include <zephyr/devicetree.h>

// 获取设备节点
#define LED0_NODE DT_ALIAS(led0)
#define BME280_NODE DT_NODELABEL(bme280)

// 设备树属性访问
static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED0_NODE, gpios);

// 设备树编译时检查
BUILD_ASSERT(DT_NODE_HAS_STATUS(LED0_NODE, okay), "LED0 not available");

// 设备运行时获取
const struct device *dev = DEVICE_DT_GET(BME280_NODE);
if (!device_is_ready(dev)) {
    printk("Device not ready\n");
    return;
}

// 设备树数组
#define BUTTONS_NODE DT_PATH(buttons)
#define BUTTON_FOREACH_CHILD(node) DT_FOREACH_CHILD(BUTTONS_NODE, node)

// GPIO配置示例
int configure_leds(void) {
    if (!gpio_is_ready_dt(&led)) {
        return -ENODEV;
    }

    int ret = gpio_pin_configure_dt(&led, GPIO_OUTPUT_ACTIVE);
    if (ret < 0) {
        return ret;
    }

    return 0;
}
```

---

## 三、线程与调度

### 3.1 线程管理

```c
#include <zephyr/kernel.h>

// 线程栈定义
K_THREAD_STACK_DEFINE(my_stack, 1024);
static struct k_thread my_thread_data;

// 线程入口函数
void my_thread(void *p1, void *p2, void *p3) {
    int id = (int)(intptr_t)p1;

    while (1) {
        printk("Thread %d running\n", id);
        k_msleep(1000);
    }
}

// 创建线程
k_tid_t tid = k_thread_create(
    &my_thread_data,       // 线程数据
    my_stack,              // 栈空间
    K_THREAD_STACK_SIZEOF(my_stack),  // 栈大小
    my_thread,             // 入口函数
    (void *)1, NULL, NULL, // 参数
    5,                     // 优先级(数值越小优先级越高)
    0,                     // 选项
    K_NO_WAIT              // 启动延迟
);

// 静态定义线程
K_THREAD_DEFINE(
    worker_tid,            // 线程ID
    1024,                  // 栈大小
    my_thread,             // 入口函数
    (void *)2, NULL, NULL, // 参数
    5,                     // 优先级
    0,                     // 选项
    -1                     // 自动启动(-1表示自动)
);

// 线程优先级
#define PRIORITY_HIGH    0
#define PRIORITY_NORMAL  10
#define PRIORITY_LOW     20
#define PRIORITY_IDLE    30

// 协作式线程(不可抢占)
K_THREAD_DEFINE(coop_thread, 512, coop_func, NULL, NULL, NULL,
                K_PRIO_COOP(1), 0, K_NO_WAIT);

// 用户态线程
K_THREAD_DEFINE(user_thread, 1024, user_func, NULL, NULL, NULL,
                5, K_USER, K_NO_WAIT);
```

### 3.2 调度策略

```c
#include <zephyr/kernel.h>

// 时间片配置
// CONFIG_TIMESLICE_SIZE=10  // 时间片10ms

// 设置时间片
k_sched_time_slice_set(10, 0);  // 10ms时间片, CPU 0

// 锁定调度器(禁止抢占)
k_sched_lock();
// 临界区代码
k_sched_unlock();

// 优先级提升
k_thread_priority_set(tid, new_priority);

// 线程休眠
k_msleep(100);         // 相对延时
k_usleep(1000);        // 微秒延时
k_busy_wait(100);      // 忙等待(微秒)

// 放弃CPU
k_yield();

// 线程挂起/恢复
k_thread_suspend(tid);
k_thread_resume(tid);

// 线程终止
k_thread_abort(tid);

// CPU绑定
k_thread_cpu_pin(tid, 1);  // 绑定到CPU 1

// 线程状态检查
uint32_t state = k_thread_state_str(tid, buf, sizeof(buf));
```

---

## 四、IPC机制

### 4.1 信号量

```c
#include <zephyr/kernel.h>

// 定义信号量
K_SEM_DEFINE(my_sem, 0, 1);  // 初始值0, 最大值1

// 二进制信号量
K_SEM_DEFINE(bin_sem, 0, 1);

// 计数信号量
K_SEM_DEFINE(cnt_sem, 0, 10);

// 等待信号量
k_sem_take(&my_sem, K_FOREVER);    // 永久等待
k_sem_take(&my_sem, K_MSEC(100));  // 超时100ms
k_sem_take(&my_sem, K_NO_WAIT);    // 不等待

// 释放信号量
k_sem_give(&my_sem);

// 信号量值
int count = k_sem_count_get(&my_sem);

// 生产者-消费者模式
void producer(void) {
    while (1) {
        produce_data();
        k_sem_give(&cnt_sem);
        k_msleep(100);
    }
}

void consumer(void) {
    while (1) {
        k_sem_take(&cnt_sem, K_FOREVER);
        consume_data();
    }
}
```

### 4.2 消息队列

```c
#include <zephyr/kernel.h>

// 消息结构
typedef struct {
    uint32_t type;
    uint32_t data;
} msg_t;

// 定义消息队列
K_MSGQ_DEFINE(my_msgq, sizeof(msg_t), 10, 4);

// 发送消息
msg_t msg = { .type = 1, .data = 100 };
int ret = k_msgq_put(&my_msgq, &msg, K_FOREVER);
if (ret != 0) {
    printk("Queue full\n");
}

// 非阻塞发送
ret = k_msgq_put(&my_msgq, &msg, K_NO_WAIT);

// 接收消息
msg_t rx_msg;
ret = k_msgq_get(&my_msgq, &rx_msg, K_MSEC(100));
if (ret == 0) {
    printk("Received: type=%d, data=%d\n", rx_msg.type, rx_msg.data);
}

// 消息队列状态
uint32_t free = k_msgq_num_free_get(&my_msgq);
uint32_t used = k_msgq_num_used_get(&my_msgq);

// 清空队列
k_msgq_purge(&my_msgq);

// 动态消息队列
struct k_msgq dyn_msgq;
static char __aligned(4) msgq_buffer[10 * sizeof(msg_t)];
k_msgq_init(&dyn_msgq, msgq_buffer, sizeof(msg_t), 10);
```

### 4.3 管道

```c
#include <zephyr/kernel.h>

// 管道定义
K_PIPE_DEFINE(my_pipe, 256, 4);

// 写入管道
uint8_t data[] = "Hello Zephyr";
size_t bytes_written;
k_pipe_put(&my_pipe, data, sizeof(data), &bytes_written, 1, K_FOREVER);

// 读取管道
uint8_t buf[64];
size_t bytes_read;
k_pipe_get(&my_pipe, buf, sizeof(buf), &bytes_read, 1, K_MSEC(100));

// 管道用于流式数据传输
void uart_rx_handler(uint8_t *data, size_t len) {
    size_t written;
    k_pipe_put(&uart_pipe, data, len, &written, 1, K_NO_WAIT);
}

void data_processor(void) {
    uint8_t buf[32];
    size_t read;
    while (1) {
        k_pipe_get(&uart_pipe, buf, sizeof(buf), &read, 1, K_FOREVER);
        process_data(buf, read);
    }
}
```

### 4.4 互斥锁

```c
#include <zephyr/kernel.h>

// 定义互斥锁
K_MUTEX_DEFINE(my_mutex);

// 优先级继承互斥锁
static struct k_mutex pi_mutex;
k_mutex_init(&pi_mutex);

// 使用互斥锁
void protected_function(void) {
    k_mutex_lock(&my_mutex, K_FOREVER);

    // 临界区
    shared_resource++;

    k_mutex_unlock(&my_mutex);
}

// 优先级天花板协议
// 通过Kconfig配置
// CONFIG_PRIORITY_CEILING=5

// 递归锁
void nested_locking(void) {
    k_mutex_lock(&my_mutex, K_FOREVER);
    // 第一次加锁
    k_mutex_lock(&my_mutex, K_FOREVER);
    // 第二次加锁(同一任务可以多次加锁)
    k_mutex_unlock(&my_mutex);
    k_mutex_unlock(&my_mutex);
}
```

---

## 五、定时器与延迟工作

### 5.1 内核定时器

```c
#include <zephyr/kernel.h>

// 定时器定义
static struct k_timer my_timer;

// 定时器回调
void timer_expiry_fn(struct k_timer *timer) {
    printk("Timer expired\n");
}

void timer_stop_fn(struct k_timer *timer) {
    printk("Timer stopped\n");
}

// 初始化定时器
k_timer_init(&my_timer, timer_expiry_fn, timer_stop_fn);

// 启动定时器
k_timer_start(&my_timer, K_MSEC(1000), K_MSEC(500));  // 周期500ms, 首次1000ms

// 停止定时器
k_timer_stop(&my_timer);

// 定时器状态
uint32_t remaining = k_timer_remaining_get(&my_timer);
bool running = k_timer_status_get(&my_timer) > 0;

// 同步等待定时器
k_timer_status_sync(&my_timer);

// 静态定时器
K_TIMER_DEFINE(static_timer, timer_expiry_fn, timer_stop_fn);

// 高精度定时器(HiRes)
// 需要硬件支持
k_timer_start(&my_timer, K_USEC(100), K_USEC(100));
```

### 5.2 工作队列

```c
#include <zephyr/kernel.h>

// 工作项定义
static struct k_work my_work;

// 工作回调
void work_handler(struct k_work *work) {
    printk("Work executed\n");
    // 不能在这里阻塞
}

// 初始化工作项
k_work_init(&my_work, work_handler);

// 提交工作到系统队列
k_work_submit(&my_work);

// 提交到自定义队列
static struct k_work_q my_work_q;
K_THREAD_STACK_DEFINE(my_stack, 2048);

// 创建工作队列
k_work_queue_init(&my_work_q);
k_work_queue_start(&my_work_q, my_stack,
                   K_THREAD_STACK_SIZEOF(my_stack),
                   K_PRIO_PREEMPT(5), NULL);
k_work_queue_name_set(&my_work_q, "my_wq");

// 提交到自定义队列
k_work_submit_to_queue(&my_work_q, &my_work);

// 延迟工作
static struct k_work_delayable my_dwork;
k_work_init_delayable(&my_dwork, work_handler);

// 延迟执行
k_work_schedule(&my_dwork, K_MSEC(500));

// 取消延迟工作
k_work_cancel_delayable(&my_dwork);

// 工作队列状态检查
bool pending = k_work_pending(&my_work);
bool running = k_work_is_pending(&my_work);

// 同步取消
k_work_cancel_sync(&my_work, NULL);
```

---

## 六、设备驱动

### 6.1 GPIO驱动

```c
#include <zephyr/drivers/gpio.h>

// 设备树获取GPIO规格
#define LED_NODE DT_ALIAS(led0)
static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(LED_NODE, gpios);

#define BTN_NODE DT_ALIAS(sw0)
static const struct gpio_dt_spec btn = GPIO_DT_SPEC_GET(BTN_NODE, gpios);

// GPIO配置
int gpio_setup(void) {
    int ret;

    // 检查设备就绪
    if (!gpio_is_ready_dt(&led)) {
        return -ENODEV;
    }

    // 配置输出
    ret = gpio_pin_configure_dt(&led, GPIO_OUTPUT_ACTIVE);
    if (ret < 0) {
        return ret;
    }

    // 配置输入
    ret = gpio_pin_configure_dt(&btn, GPIO_INPUT);
    if (ret < 0) {
        return ret;
    }

    return 0;
}

// GPIO操作
void gpio_toggle(void) {
    gpio_pin_toggle_dt(&led);
}

// GPIO中断
static struct gpio_callback btn_cb;

void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    printk("Button pressed at %" PRIu32 "\n", k_cycle_get_32());
}

int setup_button_interrupt(void) {
    int ret = gpio_pin_interrupt_configure_dt(&btn, GPIO_INT_EDGE_TO_ACTIVE);
    if (ret < 0) {
        return ret;
    }

    gpio_init_callback(&btn_cb, button_pressed, BIT(btn.pin));
    gpio_add_callback(btn.port, &btn_cb);

    return 0;
}

// 多GPIO批量操作
static const struct gpio_dt_spec leds[] = {
    GPIO_DT_SPEC_GET(DT_ALIAS(led0), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led1), gpios),
    GPIO_DT_SPEC_GET(DT_ALIAS(led2), gpios),
};

void configure_all_leds(void) {
    for (int i = 0; i < ARRAY_SIZE(leds); i++) {
        if (gpio_is_ready_dt(&leds[i])) {
            gpio_pin_configure_dt(&leds[i], GPIO_OUTPUT_INACTIVE);
        }
    }
}
```

### 6.2 I2C驱动

```c
#include <zephyr/drivers/i2c>

// I2C设备获取
#define I2C_DEV_NODE DT_NODELABEL(i2c0)
static const struct device *i2c_dev = DEVICE_DT_GET(I2C_DEV_NODE);

// I2C读写
int i2c_read_sensor(uint8_t dev_addr, uint8_t reg, uint8_t *data, size_t len) {
    return i2c_burst_read(i2c_dev, dev_addr, reg, data, len);
}

int i2c_write_sensor(uint8_t dev_addr, uint8_t reg, uint8_t *data, size_t len) {
    return i2c_burst_write(i2c_dev, dev_addr, reg, data, len);
}

// I2C单字节读写
int i2c_read_byte(uint8_t dev_addr, uint8_t reg, uint8_t *val) {
    return i2c_reg_read_byte(i2c_dev, dev_addr, reg, val);
}

int i2c_write_byte(uint8_t dev_addr, uint8_t reg, uint8_t val) {
    return i2c_reg_write_byte(i2c_dev, dev_addr, reg, val);
}

// I2C扫描
void i2c_scan(void) {
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        uint8_t dummy;
        if (i2c_read(i2c_dev, &dummy, 1, addr) == 0) {
            printk("Found device at 0x%02X\n", addr);
        }
    }
}
```

### 6.3 SPI驱动

```c
#include <zephyr/drivers/spi>

// SPI配置
#define SPI_DEV DT_NODELABEL(spi0)
static const struct device *spi_dev = DEVICE_DT_GET(SPI_DEV);

static const struct spi_cs_control spi_cs = {
    .gpio = GPIO_DT_SPEC_GET(DT_NODELABEL(spi0), cs_gpios),
    .delay = 0,
};

static const struct spi_config spi_cfg = {
    .frequency = 10000000,
    .operation = SPI_WORD_SET(8) | SPI_OP_MODE_MASTER | SPI_MODE_CPOL | SPI_MODE_CPHA,
    .slave = 0,
    .cs = spi_cs,
};

// SPI传输
int spi_transfer(uint8_t *tx, uint8_t *rx, size_t len) {
    struct spi_buf tx_buf = { .buf = tx, .len = len };
    struct spi_buf rx_buf = { .buf = rx, .len = len };
    struct spi_buf_set tx_set = { .buffers = &tx_buf, .count = 1 };
    struct spi_buf_set rx_set = { .buffers = &rx_buf, .count = 1 };

    return spi_transceive(spi_dev, &spi_cfg, &tx_set, &rx_set);
}

// SPI只写
int spi_write_data(uint8_t *data, size_t len) {
    struct spi_buf buf = { .buf = data, .len = len };
    struct spi_buf_set set = { .buffers = &buf, .count = 1 };

    return spi_write(spi_dev, &spi_cfg, &set);
}
```

---

## 七、网络协议栈

### 7.1 TCP/IP

```c
#include <zephyr/net/socket.h>
#include <zephyr/net/net_if.h>

// TCP客户端
int tcp_client(const char *host, uint16_t port) {
    int sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock < 0) {
        return -errno;
    }

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(port),
    };
    inet_pton(AF_INET, host, &addr.sin_addr);

    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(sock);
        return -errno;
    }

    // 发送数据
    const char *msg = "Hello Zephyr";
    send(sock, msg, strlen(msg), 0);

    // 接收响应
    char buf[128];
    int len = recv(sock, buf, sizeof(buf) - 1, 0);
    if (len > 0) {
        buf[len] = '\0';
        printk("Received: %s\n", buf);
    }

    close(sock);
    return 0;
}

// TCP服务器
int tcp_server(uint16_t port) {
    int serv_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(port),
        .sin_addr.s_addr = INADDR_ANY,
    };

    bind(serv_sock, (struct sockaddr *)&addr, sizeof(addr));
    listen(serv_sock, 5);

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t len = sizeof(client_addr);
        int client = accept(serv_sock, (struct sockaddr *)&client_addr, &len);

        char buf[128];
        int recv_len = recv(client, buf, sizeof(buf), 0);
        if (recv_len > 0) {
            send(client, buf, recv_len, 0);
        }
        close(client);
    }
}

// UDP
int udp_echo(uint16_t port) {
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(port),
        .sin_addr.s_addr = INADDR_ANY,
    };

    bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    while (1) {
        char buf[128];
        struct sockaddr_in client_addr;
        socklen_t addr_len = sizeof(client_addr);

        int len = recvfrom(sock, buf, sizeof(buf), 0,
                          (struct sockaddr *)&client_addr, &addr_len);
        if (len > 0) {
            sendto(sock, buf, len, 0,
                   (struct sockaddr *)&client_addr, addr_len);
        }
    }
}
```

### 7.2 MQTT客户端

```c
#include <zephyr/net/mqtt.h>

static struct mqtt_client client;
static uint8_t rx_buffer[512];
static uint8_t tx_buffer[512];

// MQTT事件回调
void mqtt_evt_handler(struct mqtt_client *client, const struct mqtt_evt *evt) {
    switch (evt->type) {
        case MQTT_EVT_CONNACK:
            printk("MQTT connected\n");
            break;
        case MQTT_EVT_PUBLISH:
            printk("Received: topic=%.*s, data=%.*s\n",
                   evt->param.publish.message.topic.topic.size,
                   evt->param.publish.message.topic.topic.utf8,
                   evt->param.publish.message.payload.len,
                   evt->param.publish.message.payload.data);
            break;
        case MQTT_EVT_DISCONNECT:
            printk("MQTT disconnected\n");
            break;
    }
}

// MQTT配置
void mqtt_setup(void) {
    client.broker = (struct sockaddr *)broker_addr;
    client.evt_cb = mqtt_evt_handler;
    client.client_id.utf8 = "zephyr_client";
    client.client_id.size = strlen(client.client_id.utf8);
    client.password = NULL;
    client.user_name = NULL;
    client.protocol_version = MQTT_VERSION_3_1_1;
    client.rx_buf = rx_buffer;
    client.rx_buf_size = sizeof(rx_buffer);
    client.tx_buf = tx_buffer;
    client.tx_buf_size = sizeof(tx_buffer);
}

// 连接MQTT
int mqtt_connect(void) {
    return mqtt_connect(&client);
}

// 订阅主题
int mqtt_subscribe_topic(const char *topic) {
    struct mqtt_topic topics[] = {
        { .topic = { .utf8 = topic, .size = strlen(topic) },
          .qos = MQTT_QOS_1_AT_LEAST_ONCE }
    };

    struct mqtt_subscription_list subs = {
        .list = topics,
        .list_count = 1,
        .message_id = 1,
    };

    return mqtt_subscribe(&client, &subs);
}

// 发布消息
int mqtt_publish(const char *topic, const char *data) {
    struct mqtt_publish_param param = {
        .message.topic.qos = MQTT_QOS_1_AT_LEAST_ONCE,
        .message.topic.topic.utf8 = topic,
        .message.topic.topic.size = strlen(topic),
        .message.payload.data = (uint8_t *)data,
        .message.payload.len = strlen(data),
        .message_id = k_cycle_get_32(),
        .dup_flag = 0,
        .retain_flag = 0,
    };

    return mqtt_publish(&client, &param);
}
```

---

## 八、电源管理

### 8.1 低功耗模式

```c
#include <zephyr/pm/pm.h>
#include <zephyr/pm/device.h>
#include <zephyr/pm/policy.h>

// 系统休眠
void enter_sleep(void) {
    // 设置唤醒源
    pm_policy_state_lock_get(PM_STATE_SOFT_OFF, PM_ALL_SUBSTATES);

    // 进入休眠
    pm_state_force(0, &(struct pm_state_info){
        .state = PM_STATE_SOFT_OFF,
        .substate_id = 0,
        .min_residency_us = 1000,
    });
}

// 设备电源管理
static int my_device_pm_action(const struct device *dev, enum pm_device_action action) {
    switch (action) {
        case PM_DEVICE_ACTION_SUSPEND:
            // 保存状态, 关闭外设
            disable_peripheral();
            break;
        case PM_DEVICE_ACTION_RESUME:
            // 恢复状态, 开启外设
            enable_peripheral();
            break;
        default:
            return -ENOTSUP;
    }
    return 0;
}

PM_DEVICE_DEFINE(my_dev, my_device_pm_action);

// 电源管理回调
static void pm_state_entry(enum pm_state state) {
    if (state == PM_STATE_SUSPEND_TO_IDLE) {
        // 关闭不必要外设
        disable_uart();
        disable_leds();
    }
}

static void pm_state_exit(enum pm_state state) {
    if (state == PM_STATE_SUSPEND_TO_IDLE) {
        // 恢复外设
        enable_uart();
        enable_leds();
    }
}

// 电池电量检测
uint32_t read_battery_voltage(void) {
    const struct device *adc_dev = DEVICE_DT_GET(DT_NODELABEL(adc));
    // ADC读取电池电压
    int16_t buf;
    struct adc_sequence seq = {
        .channels = BIT(0),
        .buffer = &buf,
        .buffer_size = sizeof(buf),
        .resolution = 12,
    };
    adc_read(adc_dev, &seq);
    return buf;
}
```

---

## 九、文件系统

### 9.1 LittleFS

```c
#include <zephyr/fs/fs.h>
#include <zephyr/fs/littlefs.h>

// LittleFS挂载
FS_LITTLEFS_DECLARE_DEFAULT_CONFIG(storage);
static struct fs_mount_t lfs_storage_mnt = {
    .type = FS_LITTLEFS,
    .fs_data = &storage,
    .storage_dev = (void *)FIXED_PARTITION_ID(storage_partition),
    .mnt_point = "/lfs",
};

int mount_fs(void) {
    int ret = fs_mount(&lfs_storage_mnt);
    if (ret < 0) {
        printk("Mount failed: %d\n", ret);
        return ret;
    }
    return 0;
}

// 文件读写
int write_file(const char *path, const void *data, size_t len) {
    struct fs_file_t file;
    fs_file_t_init(&file);

    int ret = fs_open(&file, path, FS_O_CREATE | FS_O_WRITE);
    if (ret < 0) {
        return ret;
    }

    ret = fs_write(&file, data, len);
    fs_close(&file);
    return ret;
}

int read_file(const char *path, void *buf, size_t len) {
    struct fs_file_t file;
    fs_file_t_init(&file);

    int ret = fs_open(&file, path, FS_O_READ);
    if (ret < 0) {
        return ret;
    }

    ret = fs_read(&file, buf, len);
    fs_close(&file);
    return ret;
}

// 目录遍历
int list_dir(const char *path) {
    struct fs_dir_t dir;
    fs_dir_t_init(&dir);

    int ret = fs_opendir(&dir, path);
    if (ret < 0) {
        return ret;
    }

    struct fs_dirent entry;
    while (fs_readdir(&dir, &entry) == 0) {
        if (entry.name[0] == '\0') break;
        printk("%s %s (%u bytes)\n",
               entry.type == FS_DIR_ENTRY_DIR ? "DIR" : "FILE",
               entry.name, entry.size);
    }

    fs_closedir(&dir);
    return 0;
}
```

---

## 十、调试与日志

### 10.1 日志系统

```c
#include <zephyr/logging/log.h>

// 注册模块日志
LOG_MODULE_REGISTER(my_module, LOG_LEVEL_DBG);

// 日志输出
void log_examples(void) {
    LOG_INF("Information message");
    LOG_WRN("Warning message");
    LOG_ERR("Error message");
    LOG_DBG("Debug message");

    // 带格式
    LOG_INF("Value: %d, Name: %s", 42, "test");

    // 十六进制dump
    uint8_t data[] = {0x01, 0x02, 0x03, 0x04};
    LOG_HEXDUMP_INF(data, sizeof(data), "Data:");

    // 条件日志
    if (IS_ENABLED(CONFIG_LOG)) {
        LOG_INF("Logging enabled");
    }
}

// 运行时日志控制
void set_log_level(void) {
    // 设置模块日志级别
    log_filter_set(NULL, Z_LOG_DOMAIN_ID, "my_module", LOG_LEVEL_WRN);
}

// 前端日志(减少代码大小)
// LOG_MODULE_DECLARE(my_module, LOG_LEVEL_WRN);
```

### 10.2 Shell命令

```c
#include <zephyr/shell/shell.h>

// 自定义Shell命令
static int cmd_hello(const struct shell *sh, size_t argc, char **argv) {
    shell_print(sh, "Hello from Zephyr!");
    return 0;
}

static int cmd_get_param(const struct shell *sh, size_t argc, char **argv) {
    if (argc < 2) {
        shell_error(sh, "Usage: get_param <name>");
        return -EINVAL;
    }
    shell_print(sh, "Parameter %s = %d", argv[1], get_param(argv[1]));
    return 0;
}

// 子命令
SHELL_SUBCMD_SET_CREATE(sub_cmds,
    SHELL_CMD(hello, NULL, "Say hello", cmd_hello),
    SHELL_CMD(get, NULL, "Get parameter", cmd_get_param),
);

SHELL_CMD_REGISTER(my, &sub_cmds, "My commands", NULL);

// 动态补全
static void param_name_get(const struct shell *sh, size_t argc, char **argv) {
    // 动态补全参数名
    static const char *params[] = {"voltage", "current", "temperature"};
    for (int i = 0; i < ARRAY_SIZE(params); i++) {
        if (strncmp(argv[argc - 1], params[i], strlen(argv[argc - 1])) == 0) {
            shell_print(sh, "%s", params[i]);
        }
    }
}

// Shell线程
static void shell_thread(void) {
    // Shell在独立线程中运行
    // 默认栈大小4096
}
```

---

## 附录：Zephyr与FreeRTOS对比

| 特性 | Zephyr | FreeRTOS |
|------|--------|----------|
| 配置系统 | Kconfig | FreeRTOSConfig.h |
| 设备树 | 支持(DTS) | 不支持 |
| 网络栈 | 内置lwIP+原生 | 需第三方 |
| 蓝牙 | 内置 | 需第三方 |
| 文件系统 | LittleFS/FAT | FatFs |
| 许可证 | Apache 2.0 | MIT |
| 代码风格 | Linux风格 | 独立风格 |
| 构建系统 | CMake | 各种 |
| 包管理 | West | 手动 |
| 学习曲线 | 陡峭 | 平缓 |

---

## 相关链接

- [[Zephyr RTOS]] - Zephyr基础
- [[FreeRTOS基础]] - FreeRTOS
- [[RT-Thread基础]] - RT-Thread
- [[嵌入式系统基础]] - 嵌入式系统
