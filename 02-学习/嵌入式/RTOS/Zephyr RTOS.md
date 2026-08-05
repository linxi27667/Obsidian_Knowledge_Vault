# Zephyr RTOS

## 核心概念

- **Zephyr** - Linux基金会支持的开源RTOS
- **West** - Zephyr元工具(构建/烧录/调试)
- **Device Tree** - 硬件描述(借鉴Linux)
- **Kconfig** - 内核配置系统

---

## 一、Zephyr概述

### 1.1 特点

| 特点 | 说明 |
|------|------|
| 多架构支持 | ARM, RISC-V, x86, Xtensa, ARC |
| 丰富组件 | 网络, 文件系统, USB, Bluetooth |
| 安全认证 | PSA, IEC 62443 |
| 模块化 | Kconfig可裁剪 |
| 设备树 | 硬件描述 |
| 构建系统 | CMake + West |

---

### 1.2 vs FreeRTOS

| 特性 | Zephyr | FreeRTOS |
|------|--------|----------|
| 构建系统 | CMake/West | Makefile/CMake |
| 配置 | Kconfig | FreeRTOSConfig.h |
| 设备驱动 | 设备树+驱动框架 | 无标准框架 |
| 网络 | 完整TCP/IP栈 | 需第三方 |
| Bluetooth | 原生支持 | 需第三方 |
| 文件系统 | 多种支持 | 需第三方 |
| 学习曲线 | 陡峭 | 平缓 |
| 资源占用 | 较多 | 较少 |

---

## 二、环境搭建

### 2.1 安装

```bash
# 安装Python
sudo apt install python3-pip python3-venv

# 安装West
pip3 install --user west

# 初始化项目
west init ~/zephyrproject
cd ~/zephyrproject
west update

# 安装依赖
west zephyr-export
pip3 install -r zephyr/scripts/requirements.txt

# 安装Zephyr SDK
wget https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v0.16.5/zephyr-sdk-0.16.5_linux-x86_64.tar.xz
tar xjf zephyr-sdk-0.16.5_linux-x86_64.tar.xz
cd zephyr-sdk-0.16.5
./setup.sh
```

---

### 2.2 项目结构

```
zephyrproject/
├── zephyr/           # Zephyr内核
├── modules/
│   ├── hal/          # 硬件抽象层
│   └── lib/          # 第三方库
└── application/      # 用户应用
    ├── CMakeLists.txt
    ├── prj.conf
    ├── app.overlay
    └── src/
        └── main.c
```

---

## 三、第一个应用

### 3.1 Hello World

```c
// src/main.c
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

int main(void) {
    printk("Hello World! %s\n", CONFIG_BOARD);
    return 0;
}
```

**CMakeLists.txt：**
```cmake
cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(hello_world)
target_sources(app PRIVATE src/main.c)
```

**prj.conf：**
```
# 空配置，使用默认
```

**构建与烧录：**
```bash
# 构建
west build -b esp32c3_devkitm

# 烧录
west flash

# 监控串口
west espressif monitor
```

---

### 3.2 多线程

```c
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

#define STACK_SIZE 1024
#define PRIORITY 5

K_THREAD_STACK_DEFINE(thread1_stack, STACK_SIZE);
K_THREAD_STACK_DEFINE(thread2_stack, STACK_SIZE);

struct k_thread thread1_data, thread2_data;

void thread1_entry(void *p1, void *p2, void *p3) {
    while (1) {
        printk("Thread 1\n");
        k_msleep(1000);
    }
}

void thread2_entry(void *p1, void *p2, void *p3) {
    while (1) {
        printk("Thread 2\n");
        k_msleep(2000);
    }
}

int main(void) {
    k_thread_create(&thread1_data, thread1_stack, STACK_SIZE,
                    thread1_entry, NULL, NULL, NULL,
                    PRIORITY, 0, K_NO_WAIT);

    k_thread_create(&thread2_data, thread2_stack, STACK_SIZE,
                    thread2_entry, NULL, NULL, NULL,
                    PRIORITY, 0, K_NO_WAIT);

    return 0;
}
```

---

## 四、内核服务

### 4.1 线程管理

```c
#include <zephyr/kernel.h>

// 静态定义线程
K_THREAD_DEFINE(my_tid, 1024, my_thread_entry,
                NULL, NULL, NULL, 5, 0, 0);

// 动态创建
K_THREAD_STACK_DEFINE(my_stack, 1024);
struct k_thread my_thread;

k_tid_t tid = k_thread_create(&my_thread, my_stack, 1024,
                               my_entry, NULL, NULL, NULL,
                               5, 0, K_NO_WAIT);

// 线程优先级
k_thread_priority_set(tid, 3);

// 线程休眠
k_msleep(100);       // 毫秒
k_usleep(1000);      // 微秒
k_sleep(K_MSEC(100)); // 内核超时

// 让出CPU
k_yield();
```

---

### 4.2 信号量

```c
#include <zephyr/kernel.h>

K_SEM_DEFINE(my_sem, 0, 1);  // 初始值0, 最大值1

// 获取信号量
k_sem_take(&my_sem, K_FOREVER);
k_sem_take(&my_sem, K_MSEC(100));  // 超时

// 释放信号量
k_sem_give(&my_sem);
```

---

### 4.3 互斥锁

```c
#include <zephyr/kernel.h>

K_MUTEX_DEFINE(my_mutex);

void protected_function(void) {
    k_mutex_lock(&my_mutex, K_FOREVER);

    // 临界区
    shared_resource++;

    k_mutex_unlock(&my_mutex);
}
```

---

### 4.4 消息队列

```c
#include <zephyr/kernel.h>

#define MSG_SIZE sizeof(struct sensor_data)
#define MSG_NUM 10

K_MSGQ_DEFINE(sensor_msgq, MSG_SIZE, MSG_NUM, 4);

struct sensor_data {
    int temperature;
    int humidity;
};

// 发送
void producer(void) {
    struct sensor_data data = {25, 60};
    k_msgq_put(&sensor_msgq, &data, K_FOREVER);
}

// 接收
void consumer(void) {
    struct sensor_data data;
    k_msgq_get(&sensor_msgq, &data, K_FOREVER);
    printk("Temp: %d, Hum: %d\n", data.temperature, data.humidity);
}
```

---

### 4.5 定时器

```c
#include <zephyr/kernel.h>

K_TIMER_DEFINE(my_timer, timer_handler, NULL);

void timer_handler(struct k_timer *timer) {
    printk("Timer fired!\n");
}

int main(void) {
    // 启动周期性定时器
    k_timer_start(&my_timer, K_MSEC(1000), K_MSEC(500));

    // 一次性定时器
    // k_timer_start(&my_timer, K_MSEC(1000), K_NO_WAIT);

    // 停止定时器
    // k_timer_stop(&my_timer);

    return 0;
}
```

---

### 4.6 工作队列

```c
#include <zephyr/kernel.h>

K_WORK_DEFINE(my_work, work_handler);

void work_handler(struct k_work *work) {
    printk("Work item executed\n");
}

int main(void) {
    // 提交工作
    k_work_submit(&my_work);
    return 0;
}

// 延迟工作
K_WORK_DELAYABLE_DEFINE(my_delayed_work, delayed_handler);

void delayed_handler(struct k_work *work) {
    printk("Delayed work executed\n");
}

// 提交延迟工作
k_work_schedule(&my_delayed_work, K_MSEC(5000));
```

---

### 4.7 事件

```c
#include <zephyr/kernel.h>

K_EVENT_DEFINE(my_event);

#define EVENT_BIT_0 (1 << 0)
#define EVENT_BIT_1 (1 << 1)

// 等待事件
void waiting_thread(void) {
    uint32_t events = k_event_wait(&my_event, EVENT_BIT_0 | EVENT_BIT_1,
                                    true, K_FOREVER);
    if (events & EVENT_BIT_0) {
        printk("Event 0 received\n");
    }
}

// 发送事件
void signaling_thread(void) {
    k_event_post(&my_event, EVENT_BIT_0);
}
```

---

## 五、设备驱动

### 5.1 设备树

**设备树覆盖(app.overlay)：**
```dts
/ {
    aliases {
        my-led = &led0;
    };

    leds {
        compatible = "gpio-leds";
        led0: led_0 {
            gpios = <&gpio0 13 GPIO_ACTIVE_HIGH>;
            label = "Green LED";
        };
    };
};

&i2c0 {
    status = "okay";
    clock-frequency = <I2C_BITRATE_FAST>;

    my_sensor: bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
    };
};
```

---

### 5.2 GPIO驱动

```c
#include <zephyr/drivers/gpio.h>

static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(DT_ALIAS(my_led), gpios);

int main(void) {
    // 配置GPIO
    gpio_pin_configure_dt(&dev, GPIO_OUTPUT_ACTIVE);

    while (1) {
        gpio_pin_toggle_dt(&led);
        k_msleep(500);
    }
    return 0;
}
```

---

### 5.3 I2C驱动

```c
#include <zephyr/drivers/i2c.h>

static const struct i2c_dt_spec dev_i2c = I2C_DT_SPEC_GET(DT_NODELABEL(my_sensor));

int sensor_read(void) {
    uint8_t reg = 0xD0;  // 芯片ID寄存器
    uint8_t id;

    i2c_write_read_dt(&dev_i2c, &reg, 1, &id, 1);
    printk("Sensor ID: 0x%02x\n", id);

    return 0;
}
```

---

### 5.4 SPI驱动

```c
#include <zephyr/drivers/spi.h>

static const struct spi_dt_spec dev_spi = SPI_DT_SPEC_GET(DT_NODELABEL(my_spi_dev),
                                                            SPI_WORD_SET(8), 0);

int spi_transfer(void) {
    uint8_t tx_buf[] = {0x01, 0x02};
    uint8_t rx_buf[2];

    struct spi_buf tx = { .buf = tx_buf, .len = sizeof(tx_buf) };
    struct spi_buf rx = { .buf = rx_buf, .len = sizeof(rx_buf) };

    struct spi_buf_set tx_set = { .buffers = &tx, .count = 1 };
    struct spi_buf_set rx_set = { .buffers = &rx, .count = 1 };

    spi_transceive_dt(&dev_spi, &tx_set, &rx_set);

    return 0;
}
```

---

## 六、网络

### 6.1 Socket API

```c
#include <zephyr/net/socket.h>

void tcp_client(void) {
    int sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(8080),
    };
    inet_pton(AF_INET, "192.168.1.100", &addr.sin_addr);

    connect(sock, (struct sockaddr *)&addr, sizeof(addr));

    send(sock, "Hello", 5, 0);

    char buf[128];
    int len = recv(sock, buf, sizeof(buf), 0);

    close(sock);
}
```

---

### 6.2 MQTT客户端

```c
#include <zephyr/net/mqtt.h>

static struct mqtt_client client;

void mqtt_connect(void) {
    mqtt_client_init(&client);

    client.broker = (struct sockaddr *)&broker_addr;
    client.evt_cb = mqtt_event_handler;
    client.client_id.utf8 = "zephyr_client";
    client.client_id.size = strlen(client.client_id.utf8);

    mqtt_connect(&client);
}

void mqtt_publish(const char *topic, const char *data) {
    struct mqtt_topic pub_topic = {
        .topic.utf8 = topic,
        .topic.size = strlen(topic),
    };

    struct mqtt_publish_param param = {
        .message.topic = pub_topic,
        .message.payload.data = data,
        .message.payload.len = strlen(data),
        .message_id = k_cycle_get_32(),
        .dup_flag = 0,
        .qos = MQTT_QOS_0_AT_MOST_ONCE,
    };

    mqtt_publish(&client, &param);
}
```

---

## 七、Bluetooth

### 7.1 BLE广播

```c
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>

static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR),
    BT_DATA_BYTES(BT_DATA_UUID16_ALL, 0x0d, 0x18),  // Heart Rate
};

int main(void) {
    bt_enable(NULL);
    bt_le_adv_start(BT_LE_ADV_CONN, ad, ARRAY_SIZE(ad), NULL, 0);
    return 0;
}
```

---

### 7.2 GATT服务

```c
static ssize_t read_value(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                          void *buf, uint16_t len, uint16_t offset) {
    uint8_t value = 42;
    return bt_gatt_attr_read(conn, attr, buf, len, offset, &value, sizeof(value));
}

BT_GATT_SERVICE_DEFINE(my_svc,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_DECLARE_16(0x1234)),
    BT_GATT_CHARACTERISTIC(BT_UUID_DECLARE_16(0x5678),
                           BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ,
                           read_value, NULL, NULL),
);
```

---

## 八、电源管理

### 8.1 系统休眠

```c
#include <zephyr/pm/pm.h>
#include <zephyr/pm/policy.h>

// 自动休眠(配置)
// prj.conf:
// CONFIG_PM=y
// CONFIG_PM_DEVICE=y

// 手动休眠
void enter_sleep(void) {
    k_msleep(100);
    // 系统自动进入低功耗
}
```

---

### 8.2 设备电源管理

```c
#include <zephyr/pm/device.h>

// 挂起设备
pm_device_action_run(dev, PM_DEVICE_ACTION_SUSPEND);

// 恢复设备
pm_device_action_run(dev, PM_DEVICE_ACTION_RESUME);
```

---

## 九、构建系统

### 9.1 West命令

| 命令 | 说明 |
|------|------|
| west build | 构建项目 |
| west flash | 烧录固件 |
| west debug | GDB调试 |
| west monitor | 串口监控 |
| west update | 更新模块 |
| west list | 列出模块 |

---

### 9.2 Kconfig配置

**prj.conf：**
```
# 启用GPIO
CONFIG_GPIO=y

# 启用I2C
CONFIG_I2C=y

# 启用网络
CONFIG_NETWORKING=y
CONFIG_NET_IPV4=y
CONFIG_NET_TCP=y

# 启用Bluetooth
CONFIG_BT=y
CONFIG_BT_PERIPHERAL=y

# 内存配置
CONFIG_HEAP_MEM_POOL_SIZE=4096
CONFIG_MAIN_STACK_SIZE=2048
```

---

### 9.3 板级配置

```bash
# 查看支持的板
west boards | grep esp32

# 指定板构建
west build -b esp32c3_devkitm

# 指定配置
west build -b esp32c3_devkitm -- -DCONFIG_DEBUG=y
```

---

## 十、调试

### 10.1 日志

```c
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(my_module, LOG_LEVEL_DBG);

void my_function(void) {
    LOG_INF("Info message");
    LOG_WRN("Warning message");
    LOG_ERR("Error message");
    LOG_DBG("Debug message: %d", 42);
}
```

**prj.conf配置：**
```
CONFIG_LOG=y
CONFIG_LOG_DEFAULT_LEVEL=3
CONFIG_LOG_BACKEND_UART=y
```

---

### 10.2 Shell

```c
#include <zephyr/shell/shell.h>

static int cmd_hello(const struct shell *shell, size_t argc, char **argv) {
    shell_print(shell, "Hello %s!", argv[1]);
    return 0;
}

SHELL_CMD_REGISTER(hello, NULL, "Say hello", cmd_hello);
```

**prj.conf配置：**
```
CONFIG_SHELL=y
CONFIG_SHELL_BACKEND_SERIAL=y
```

---

## 附录：资源

### 官方资源

| 资源 | 链接 |
|------|------|
| 文档 | docs.zephyrproject.org |
| GitHub | github.com/zephyrproject-rtos/zephyr |
| 示例 | zephyr/samples |

### 常用模块

| 模块 | 说明 |
|------|------|
| LittleFS | 文件系统 |
| MQTT | 消息协议 |
| OpenThread | Thread协议 |
| LVGL | 图形库 |

---

## 相关链接

- [[FreeRTOS基础]] - FreeRTOS对比
- [[Linux驱动开发]] - 设备树参考
- [[CMake]] - 构建系统
- [[ESP-IDF开发]] - ESP32开发
