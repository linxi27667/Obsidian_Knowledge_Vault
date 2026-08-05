# RT-Thread基础

## 核心概念

- **RT-Thread** - 国产开源实时操作系统
- **线程** - 任务调度的基本单位
- **IPC** - 进程间通信机制
- **设备框架** - 统一的设备驱动模型

---

## 一、RT-Thread概述

### 1.1 特点

**优势：**
- 国产自主可控
- 组件丰富
- 社区活跃
- 文档完善

**版本：**
| 版本 | 特点 | 应用 |
|------|------|------|
| Nano | 极小内核 | 资源受限设备 |
| Standard | 完整内核 | 通用嵌入式 |
| Smart | 带MMU | 复杂应用 |

---

### 1.2 架构

```
┌─────────────────────────────────────┐
│           应用层                     │
├─────────────────────────────────────┤
│         组件层                       │
│  文件系统 | 网络 | GUI | 设备框架   │
├─────────────────────────────────────┤
│         内核层                       │
│  线程 | 定时器 | IPC | 内存管理     │
├─────────────────────────────────────┤
│         BSP层                        │
│  驱动 | 外设 | 板级支持             │
└─────────────────────────────────────┘
```

---

## 二、内核基础

### 2.1 线程管理

**创建线程：**
```c
#include <rtthread.h>

static struct rt_thread thread1;
static rt_uint8_t thread1_stack[512];

void thread1_entry(void *parameter) {
    while (1) {
        rt_kprintf("Thread1 running\n");
        rt_thread_mdelay(1000);
    }
}

int main(void) {
    rt_thread_init(&thread1,
                   "thread1",
                   thread1_entry,
                   RT_NULL,
                   &thread1_stack[0],
                   sizeof(thread1_stack),
                   10,    // 优先级
                   10);   // 时间片
    
    rt_thread_startup(&thread1);
    
    return 0;
}
```

**动态创建：**
```c
rt_thread_t thread = rt_thread_create("thread1",
                                      thread1_entry,
                                      RT_NULL,
                                      512,
                                      10,
                                      10);
if (thread != RT_NULL) {
    rt_thread_startup(thread);
}
```

---

### 2.2 线程状态

```
        ┌───────────┐
        │   初始态   │
        └─────┬─────┘
              │ rt_thread_startup
              ▼
        ┌───────────┐
        │   就绪态   │◄─────────┐
        └─────┬─────┘          │
              │ 调度            │
              ▼                │
        ┌───────────┐          │
        │   运行态   │──────────┘
        └─────┬─────┘   时间片/让出
              │
              │ 等待资源
              ▼
        ┌───────────┐
        │   挂起态   │
        └───────────┘
```

---

### 2.3 线程优先级

| 优先级 | 说明 |
|--------|------|
| 0 | 最高优先级 |
| ... | ... |
| RT_THREAD_PRIORITY_MAX-1 | 最低优先级 |

**常用优先级：**
```c
#define RT_THREAD_PRIORITY_MAX 32
#define RT_THREAD_PRIORITY_MIN 0
```

---

### 2.4 时间片调度

```c
// 设置时间片
rt_thread_control(thread, RT_THREAD_CTRL_CHANGE_TIME_SLICE, &tick);
```

---

## 三、定时器

### 3.1 软件定时器

```c
static rt_timer_t timer1;

void timer1_timeout(void *parameter) {
    rt_kprintf("Timer1 timeout\n");
}

// 创建定时器
timer1 = rt_timer_create("timer1",
                         timer1_timeout,
                         RT_NULL,
                         10,    // 10个tick
                         RT_TIMER_FLAG_PERIODIC);  // 周期定时器

// 启动定时器
rt_timer_start(timer1);

// 停止定时器
rt_timer_stop(timer1);

// 删除定时器
rt_timer_delete(timer1);
```

**定时器标志：**
| 标志 | 说明 |
|------|------|
| RT_TIMER_FLAG_ONE_SHOT | 单次定时 |
| RT_TIMER_FLAG_PERIODIC | 周期定时 |
| RT_TIMER_FLAG_SOFT_TIMER | 软件定时器 |
| RT_TIMER_FLAG_HARD_TIMER | 硬件定时器 |

---

## 四、IPC通信

### 4.1 信号量

```c
static rt_sem_t sem1;

// 创建信号量
sem1 = rt_sem_create("sem1", 0, RT_IPC_FLAG_FIFO);

// 等待信号量
rt_err_t result = rt_sem_take(sem1, RT_WAITING_FOREVER);
if (result == RT_EOK) {
    // 获取成功
}

// 发送信号量
rt_sem_release(sem1);

// 删除信号量
rt_sem_delete(sem1);
```

---

### 4.2 互斥量

```c
static rt_mutex_t mutex1;

// 创建互斥量
mutex1 = rt_mutex_create("mutex1", RT_IPC_FLAG_FIFO);

// 获取互斥量
rt_mutex_take(mutex1, RT_WAITING_FOREVER);

// 释放互斥量
rt_mutex_release(mutex1);

// 删除互斥量
rt_mutex_delete(mutex1);
```

---

### 4.3 事件

```c
static rt_event_t event1;

// 创建事件
event1 = rt_event_create("event1", 0, RT_IPC_FLAG_FIFO);

// 发送事件
rt_event_send(event1, 0x01);

// 等待事件
rt_uint32_t recved;
rt_err_t result = rt_event_recv(event1, 0x01,
                                RT_EVENT_FLAG_AND | RT_EVENT_FLAG_CLEAR,
                                RT_WAITING_FOREVER,
                                &recved);

// 删除事件
rt_event_delete(event1);
```

---

### 4.4 消息队列

```c
static rt_mq_t mq1;

// 创建消息队列
mq1 = rt_mq_create("mq1", 32, 10, RT_IPC_FLAG_FIFO);

// 发送消息
char msg[] = "Hello";
rt_mq_send(mq1, msg, sizeof(msg));

// 接收消息
char buf[32];
rt_err_t result = rt_mq_recv(mq1, buf, sizeof(buf), RT_WAITING_FOREVER);

// 删除消息队列
rt_mq_delete(mq1);
```

---

### 4.5 邮箱

```c
static rt_mailbox_t mb1;

// 创建邮箱
mb1 = rt_mb_create("mb1", 10, RT_IPC_FLAG_FIFO);

// 发送邮件
rt_mb_send(mb1, 1234);

// 接收邮件
rt_uint32_t value;
rt_err_t result = rt_mb_recv(mb1, &value, RT_WAITING_FOREVER);

// 删除邮箱
rt_mb_delete(mb1);
```

---

## 五、内存管理

### 5.1 内存池

```c
static rt_mp_t mp1;
static rt_uint8_t mp_pool[1024];

// 创建内存池
mp1 = rt_mp_create("mp1", 10, 64);

// 分配内存
void *ptr = rt_mp_alloc(mp1, RT_WAITING_FOREVER);

// 释放内存
rt_mp_free(ptr);

// 删除内存池
rt_mp_delete(mp1);
```

---

### 5.2 堆内存

```c
// 分配内存
void *ptr = rt_malloc(1024);

// 分配并清零
void *ptr = rt_calloc(10, 1024);

// 重新分配
ptr = rt_realloc(ptr, 2048);

// 释放内存
rt_free(ptr);
```

---

## 六、设备框架

### 6.1 设备注册

```c
#include <rtdevice.h>

static rt_device_t my_device;

static rt_err_t my_init(rt_device_t dev) {
    return RT_EOK;
}

static rt_err_t my_open(rt_device_t dev, rt_uint16_t oflag) {
    return RT_EOK;
}

static rt_err_t my_close(rt_device_t dev) {
    return RT_EOK;
}

static rt_size_t my_read(rt_device_t dev, rt_off_t pos, void *buffer, rt_size_t size) {
    return size;
}

static rt_size_t my_write(rt_device_t dev, rt_off_t pos, const void *buffer, rt_size_t size) {
    return size;
}

static rt_err_t my_control(rt_device_t dev, int cmd, void *args) {
    return RT_EOK;
}

// 设备操作方法
static struct rt_device_ops my_ops = {
    .init = my_init,
    .open = my_open,
    .close = my_close,
    .read = my_read,
    .write = my_write,
    .control = my_control,
};

// 注册设备
int my_device_init(void) {
    my_device = rt_device_create(RT_Device_Class_Char, 0);
    my_device->ops = &my_ops;
    rt_device_register(my_device, "mydevice", RT_DEVICE_FLAG_RDWR);
    return 0;
}
INIT_DEVICE_EXPORT(my_device_init);
```

---

### 6.2 设备操作

```c
// 查找设备
rt_device_t dev = rt_device_find("mydevice");

// 打开设备
rt_device_open(dev, RT_DEVICE_OFLAG_RDWR);

// 读取数据
rt_device_read(dev, 0, buffer, size);

// 写入数据
rt_device_write(dev, 0, buffer, size);

// 控制设备
rt_device_control(dev, cmd, args);

// 关闭设备
rt_device_close(dev);
```

---

### 6.3 GPIO设备

```c
#include <drv_gpio.h>

// 配置GPIO
rt_pin_mode(GET_PIN(A, 5), PIN_MODE_OUTPUT);

// 设置GPIO
rt_pin_write(GET_PIN(A, 5), PIN_HIGH);
rt_pin_write(GET_PIN(A, 5), PIN_LOW);

// 读取GPIO
rt_base_t value = rt_pin_read(GET_PIN(A, 0));

// 注册中断
void irq_callback(void *args) {
    rt_kprintf("Interrupt occurred\n");
}
rt_pin_attach_irq(GET_PIN(A, 0), PIN_IRQ_MODE_FALLING, irq_callback, RT_NULL);
rt_pin_irq_enable(GET_PIN(A, 0), PIN_IRQ_ENABLE);
```

---

### 6.4 UART设备

```c
#include <rtdevice.h>

// 查找串口
rt_device_t uart = rt_device_find("uart1");

// 配置串口
struct serial_configure config = RT_SERIAL_CONFIG_DEFAULT;
rt_device_control(uart, RT_DEVICE_CTRL_CONFIG, &config);

// 打开串口
rt_device_open(uart, RT_DEVICE_OFLAG_RDWR | RT_DEVICE_FLAG_INT_RX);

// 发送数据
rt_device_write(uart, 0, "Hello", 5);

// 接收回调
rt_err_t uart_rx_callback(rt_device_t dev, rt_size_t size) {
    char ch;
    rt_device_read(dev, 0, &ch, 1);
    return RT_EOK;
}
rt_device_set_rx_indicate(uart, uart_rx_callback);
```

---

### 6.5 I2C设备

```c
#include <rtdevice.h>

// 查找I2C总线
rt_device_t i2c_bus = rt_device_find("i2c1");

// 打开I2C
rt_device_open(i2c_bus, RT_DEVICE_OFLAG_RDWR);

// 读取数据
struct rt_i2c_msg msg;
msg.addr = 0x68;
msg.flags = RT_I2C_RD;
msg.buf = buffer;
msg.len = 2;
rt_device_control(i2c_bus, RT_I2C_DEV_CTRL_MSG, &msg);
```

---

## 七、FinSH控制台

### 7.1 命令注册

```c
#include <finsh.h>

// 导出函数
void hello(void) {
    rt_kprintf("Hello RT-Thread!\n");
}
MSH_CMD_EXPORT(hello, say hello);

// 带参数函数
int led(int argc, char **argv) {
    if (argc == 2) {
        if (rt_strcmp(argv[1], "on") == 0) {
            rt_pin_write(GET_PIN(A, 5), PIN_HIGH);
        } else if (rt_strcmp(argv[1], "off") == 0) {
            rt_pin_write(GET_PIN(A, 5), PIN_LOW);
        }
    }
    return 0;
}
MSH_CMD_EXPORT(led, led on|off);
```

---

## 八、组件

### 8.1 文件系统

```c
#include <dfs_fs.h>

// 挂载文件系统
dfs_mount("sd0", "/", "elm", 0, 0);

// 文件操作
int fd = open("/file.txt", O_RDONLY);
read(fd, buffer, size);
close(fd);
```

---

### 8.2 网络组件

```c
#include <sys/socket.h>

// 创建socket
int sock = socket(AF_INET, SOCK_STREAM, 0);

// 连接服务器
struct sockaddr_in server;
server.sin_family = AF_INET;
server.sin_port = htons(8080);
inet_pton(AF_INET, "192.168.1.100", &server.sin_addr);
connect(sock, (struct sockaddr*)&server, sizeof(server));

// 发送数据
send(sock, "Hello", 5, 0);

// 接收数据
recv(sock, buffer, sizeof(buffer), 0);
```

---

## 九、构建系统

### 9.1 SCons构建

```python
# SConscript
from building import *

cwd = GetCurrentDir()
src = Glob('*.c')
CPPPATH = [cwd]

group = DefineGroup('mygroup', src, depend = [''], CPPPATH = CPPPATH)

Return('group')
```

**构建命令：**
```bash
scons            # 构建
scons -c         # 清理
scons --menuconfig  # 配置
```

---

### 9.2 Env工具

```bash
# 安装Env
pip install env

# 配置工程
scons --menuconfig

# 更新软件包
pkgs --update

# 构建
scons
```

---

## 十、移植指南

### 10.1 移植步骤

1. 准备BSP模板
2. 实现时钟初始化
3. 实现串口驱动
4. 实现中断控制器
5. 实现定时器驱动
6. 测试基本功能

---

### 10.2 关键文件

| 文件 | 说明 |
|------|------|
| board.c | 板级初始化 |
| board.h | 板级配置 |
| drv_uart.c | 串口驱动 |
| drv_gpio.c | GPIO驱动 |
| startup.S | 启动代码 |

---

## 附录：API速查表

### 线程管理

| API | 说明 |
|-----|------|
| rt_thread_create | 创建线程 |
| rt_thread_delete | 删除线程 |
| rt_thread_startup | 启动线程 |
| rt_thread_delay | 延时 |

### 定时器

| API | 说明 |
|-----|------|
| rt_timer_create | 创建定时器 |
| rt_timer_start | 启动定时器 |
| rt_timer_stop | 停止定时器 |

### IPC

| API | 说明 |
|-----|------|
| rt_sem_create | 创建信号量 |
| rt_mutex_create | 创建互斥量 |
| rt_event_create | 创建事件 |
| rt_mq_create | 创建消息队列 |

### 设备

| API | 说明 |
|-----|------|
| rt_device_find | 查找设备 |
| rt_device_open | 打开设备 |
| rt_device_read | 读取设备 |
| rt_device_write | 写入设备 |

---

## 相关链接

- [[FreeRTOS]] - FreeRTOS对比
- [[嵌入式Linux]] - Linux实践
- [[ESP-IDF]] - ESP32开发
