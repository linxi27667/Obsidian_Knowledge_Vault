# RT-Thread详解

## 核心概念

- **线程** - 最小调度单位
- **设备框架** - 统一设备驱动模型
- **组件** - 可插拔软件模块
- **RT-Thread** - 国产开源RTOS

---

## 一、RT-Thread架构

### 1.1 系统架构

```
┌─────────────────────────────────────────┐
│           应用层                         │
│    用户应用、组件、包                     │
├─────────────────────────────────────────┤
│           组件层                         │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│  │FinSH │ │文件  │ │网络  │ │GUI   │      │
│  │Shell │ │系统  │ │协议栈│ │(LVGL)│      │
│  └─────┘ └─────┘ └─────┘ └─────┘      │
├─────────────────────────────────────────┤
│           内核层                         │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│  │线程  │ │定时器│ │IPC  │ │内存  │      │
│  │调度器│ │管理  │ │机制  │ │管理  │      │
│  └─────┘ └─────┘ └─────┘ └─────┘      │
├─────────────────────────────────────────┤
│           设备框架                       │
│  ┌─────┐ ┌─────┐ ┌─────┐               │
│  │字符  │ │块设备│ │网络  │               │
│  │设备  │ │     │ │设备  │               │
│  └─────┘ └─────┘ └─────┘               │
├─────────────────────────────────────────┤
│           HAL层                          │
│  ┌─────┐ ┌─────┐ ┌─────┐               │
│  │BSP  │ │驱动  │ │外设  │               │
│  └─────┘ └─────┘ └─────┘               │
├─────────────────────────────────────────┤
│           硬件                           │
└─────────────────────────────────────────┘
```

### 1.2 内核配置

```c
// rtconfig.h - 内核配置
// 线程配置
#define RT_THREAD_PRIORITY_MAX  32
#define RT_TICK_PER_SECOND      1000
#define RT_ALIGN_SIZE           4
#define RT_NAME_MAX             8

// 内存配置
#define RT_USING_HEAP
#define RT_USING_MEMHEAP
#define RT_USING_MEMPOOL

// IPC配置
#define RT_USING_SEMAPHORE
#define RT_USING_MUTEX
#define RT_USING_EVENT
#define RT_USING_MAILBOX
#define RT_USING_MESSAGEQUEUE

// 设备框架
#define RT_USING_DEVICE
#define RT_USING_UART
#define RT_USING_SPI
#define RT_USING_I2C
#define RT_USING_GPIO

// Shell
#define RT_USING_FINSH
#define FINSH_THREAD_NAME       "tshell"
#define FINSH_THREAD_PRIORITY   20
#define FINSH_THREAD_STACK_SIZE 4096
#define FINSH_USING_HISTORY
#define FINSH_HISTORY_LINES     5
```

---

## 二、线程管理

### 2.1 线程创建

```c
#include <rtthread.h>

// 线程栈定义
static struct rt_thread my_thread;
static rt_uint8_t my_stack[1024];

// 线程入口函数
void my_thread_entry(void *param) {
    rt_uint32_t count = 0;

    while (1) {
        rt_kprintf("Thread running: %d\n", count++);
        rt_thread_mdelay(1000);
    }
}

// 创建线程
int create_thread(void) {
    rt_err_t result;

    result = rt_thread_init(&my_thread,
                           "my_task",
                           my_thread_entry,
                           RT_NULL,
                           &my_stack[0],
                           sizeof(my_stack),
                           10,    // 优先级(数值越小优先级越高)
                           20);   // 时间片
    if (result == RT_EOK) {
        rt_thread_startup(&my_thread);
    }

    return result;
}

// 动态创建线程
rt_thread_t create_dynamic_thread(void) {
    rt_thread_t tid;

    tid = rt_thread_create("dyn_task",
                          my_thread_entry,
                          RT_NULL,
                          2048,   // 栈大小
                          10,     // 优先级
                          20);    // 时间片
    if (tid != RT_NULL) {
        rt_thread_startup(tid);
    }

    return tid;
}

// 静态线程宏
static struct rt_thread init_thread;
static rt_uint8_t init_stack[2048];

int rt_application_init(void) {
    rt_thread_init(&init_thread, "init", init_entry, RT_NULL,
                   &init_stack[0], sizeof(init_stack), 0, 10);
    rt_thread_startup(&init_thread);
    return 0;
}
INIT_APP_EXPORT(rt_application_init);  // 自动初始化
```

### 2.2 线程控制

```c
#include <rtthread.h>

// 线程休眠
void sleep_example(void) {
    rt_thread_mdelay(100);     // 毫秒延时
    rt_thread_delay(RT_TICK_PER_SECOND);  // tick延时
    rt_thread_sleep(50);       // tick延时
}

// 线程让出CPU
void yield_example(void) {
    rt_thread_yield();
}

// 线程挂起/恢复
void suspend_resume(void) {
    rt_thread_t tid = rt_thread_find("my_task");

    rt_thread_suspend(tid);
    // ... 其他操作
    rt_thread_resume(tid);
}

// 线程删除
void delete_thread(void) {
    rt_thread_t tid = rt_thread_find("my_task");
    rt_thread_delete(tid);
}

// 线程状态
void check_thread_state(void) {
    rt_thread_t tid = rt_thread_self();

    if (tid->stat == RT_THREAD_READY) {
        rt_kprintf("Thread is ready\n");
    } else if (tid->stat == RT_THREAD_SUSPEND) {
        rt_kprintf("Thread is suspended\n");
    } else if (tid->stat == RT_THREAD_RUNNING) {
        rt_kprintf("Thread is running\n");
    }
}

// 线程优先级设置
void set_priority(rt_thread_t tid, rt_uint8_t prio) {
    rt_thread_control(tid, RT_THREAD_CTRL_CHANGE_PRIORITY, &prio);
}

// 线程CPU亲和性(多核)
void set_cpu_affinity(rt_thread_t tid, rt_uint32_t cpu) {
    rt_thread_control(tid, RT_THREAD_CTRL_BIND_CPU, &cpu);
}

// 线程信息查询
void thread_info(void) {
    rt_thread_t tid = rt_thread_self();
    rt_kprintf("Name: %s\n", tid->name);
    rt_kprintf("Priority: %d\n", tid->current_priority);
    rt_kprintf("Stack: %d/%d\n", tid->stack_size - tid->remaining_stack, tid->stack_size);
}
```

---

## 三、IPC机制

### 3.1 信号量

```c
#include <rtthread.h>

// 静态信号量
static struct rt_semaphore sem;

// 创建信号量
int sem_init(void) {
    return rt_sem_init(&sem, "my_sem", 0, RT_IPC_FLAG_FIFO);
}

// 动态创建信号量
rt_sem_t create_sem(void) {
    return rt_sem_create("my_sem", 0, RT_IPC_FLAG_FIFO);
}

// 等待信号量
void wait_sem(void) {
    rt_err_t result;

    result = rt_sem_take(&sem, RT_WAITING_FOREVER);  // 永久等待
    if (result == RT_EOK) {
        rt_kprintf("Got semaphore\n");
    }

    result = rt_sem_take(&sem, rt_tick_from_millisecond(100));  // 超时
    if (result == -RT_ETIMEOUT) {
        rt_kprintf("Timeout\n");
    }

    result = rt_sem_trytake(&sem);  // 非阻塞
    if (result == -RT_EEMPTY) {
        rt_kprintf("Semaphore not available\n");
    }
}

// 释放信号量
void release_sem(void) {
    rt_sem_release(&sem);
}

// 二进制信号量
void binary_sem_example(void) {
    rt_sem_t bin_sem = rt_sem_create("bin_sem", 0, RT_IPC_FLAG_FIFO);

    // 任务A: 等待事件
    rt_sem_take(bin_sem, RT_WAITING_FOREVER);

    // 任务B: 释放事件
    rt_sem_release(bin_sem);
}

// 计数信号量
void counting_sem_example(void) {
    rt_sem_t cnt_sem = rt_sem_create("cnt_sem", 5, RT_IPC_FLAG_FIFO);

    // 生产者
    rt_sem_release(cnt_sem);

    // 消费者
    rt_sem_take(cnt_sem, RT_WAITING_FOREVER);
}
```

### 3.2 互斥锁

```c
#include <rtthread.h>

// 静态互斥锁
static struct rt_mutex mutex;

// 创建互斥锁
int mutex_init(void) {
    return rt_mutex_init(&mutex, "my_mutex", RT_IPC_FLAG_PRIO);
}

// 动态创建
rt_mutex_t create_mutex(void) {
    return rt_mutex_create("my_mutex", RT_IPC_FLAG_PRIO);
}

// 使用互斥锁
void protected_function(void) {
    rt_mutex_take(&mutex, RT_WAITING_FOREVER);

    // 临界区
    shared_data++;

    rt_mutex_release(&mutex);
}

// 优先级继承
void priority_inheritance_example(void) {
    // 低优先级任务持有mutex
    rt_mutex_take(&mutex, RT_WAITING_FOREVER);

    // 高优先级任务等待mutex
    // 低优先级任务会被提升到高优先级

    rt_mutex_release(&mutex);
}

// 递归锁
void recursive_lock_example(void) {
    rt_mutex_take(&mutex, RT_WAITING_FOREVER);
    // 第一次加锁

    rt_mutex_take(&mutex, RT_WAITING_FOREVER);
    // 第二次加锁(同一任务可以递归加锁)

    rt_mutex_release(&mutex);
    rt_mutex_release(&mutex);
}
```

### 3.3 事件

```c
#include <rtthread.h>

// 事件标志
#define EVENT_FLAG_1    (1 << 0)
#define EVENT_FLAG_2    (1 << 1)
#define EVENT_FLAG_3    (1 << 2)

static struct rt_event event;

// 创建事件
int event_init(void) {
    return rt_event_init(&event, "my_event", RT_IPC_FLAG_FIFO);
}

// 发送事件
void send_event(void) {
    rt_event_send(&event, EVENT_FLAG_1);
    rt_event_send(&event, EVENT_FLAG_1 | EVENT_FLAG_2);
}

// 接收事件
void wait_event(void) {
    rt_uint32_t recved;

    // 等待任意事件
    rt_event_recv(&event, EVENT_FLAG_1 | EVENT_FLAG_2,
                  RT_EVENT_FLAG_OR, RT_WAITING_FOREVER, &recved);

    // 等待所有事件
    rt_event_recv(&event, EVENT_FLAG_1 | EVENT_FLAG_2,
                  RT_EVENT_FLAG_AND, RT_WAITING_FOREVER, &recved);

    // 清除事件
    rt_event_recv(&event, EVENT_FLAG_1 | EVENT_FLAG_2,
                  RT_EVENT_FLAG_AND | RT_EVENT_FLAG_CLEAR,
                  RT_WAITING_FOREVER, &recved);
}

// 状态机示例
#define STATE_INIT      (1 << 0)
#define STATE_RUNNING   (1 << 1)
#define STATE_ERROR     (1 << 2)
#define STATE_STOP      (1 << 3)

void state_machine(void) {
    rt_uint32_t state;

    while (1) {
        rt_event_recv(&event, 0xFFFFFFFF,
                      RT_EVENT_FLAG_OR, RT_WAITING_FOREVER, &state);

        if (state & STATE_INIT) {
            initialize_system();
        }
        if (state & STATE_RUNNING) {
            run_system();
        }
        if (state & STATE_ERROR) {
            handle_error();
        }
        if (state & STATE_STOP) {
            stop_system();
            break;
        }
    }
}
```

### 3.4 消息队列

```c
#include <rtthread.h>

// 消息队列
static struct rt_messagequeue mq;
static char mq_pool[1024];

// 创建消息队列
int mq_init(void) {
    return rt_mq_init(&mq, "my_mq", &mq_pool[0], 64, sizeof(mq_pool), RT_IPC_FLAG_FIFO);
}

// 发送消息
void send_message(void) {
    char msg[64];
    snprintf(msg, sizeof(msg), "Hello %d", count++);
    rt_mq_send(&mq, msg, strlen(msg) + 1);
}

// 接收消息
void receive_message(void) {
    char buf[64];
    rt_err_t result;

    result = rt_mq_recv(&mq, buf, sizeof(buf), RT_WAITING_FOREVER);
    if (result == RT_EOK) {
        rt_kprintf("Received: %s\n", buf);
    }
}

// 紧急消息(插入队首)
void send_urgent(void) {
    char msg[] = "URGENT";
    rt_mq_urgent(&mq, msg);
}

// 消息队列状态
void mq_status(void) {
    rt_kprintf("Entry count: %d\n", mq.entry);
    rt_kprintf("In waiting: %d\n", mq.suspend_thread_count);
}
```

### 3.5 邮箱

```c
#include <rtthread.h>

// 邮箱
static struct rt_mailbox mb;
static rt_uint32_t mb_pool[16];

// 创建邮箱
int mb_init(void) {
    return rt_mb_init(&mb, "my_mb", &mb_pool[0],
                      sizeof(mb_pool) / sizeof(rt_uint32_t), RT_IPC_FLAG_FIFO);
}

// 发送邮件
void send_mail(void) {
    rt_uint32_t data = 0x12345678;
    rt_mb_send(&mb, data);

    // 带超时发送
    rt_mb_send_wait(&mb, data, rt_tick_from_millisecond(100));
}

// 接收邮件
void receive_mail(void) {
    rt_uint32_t value;
    rt_err_t result;

    result = rt_mb_recv(&mb, &value, RT_WAITING_FOREVER);
    if (result == RT_EOK) {
        rt_kprintf("Received: 0x%08X\n", value);
    }
}

// 邮箱用于命令传递
typedef struct {
    rt_uint32_t cmd;
    rt_uint32_t param;
} cmd_msg_t;

void send_command(rt_uint32_t cmd, rt_uint32_t param) {
    cmd_msg_t msg = {cmd, param};
    rt_mb_send(&mb, (rt_uint32_t)&msg);
}
```

---

## 四、定时器

### 4.1 软件定时器

```c
#include <rtthread.h>

// 静态定时器
static struct rt_timer timer;

// 定时器回调
void timeout(void *param) {
    rt_kprintf("Timer expired\n");
}

// 创建定时器
int timer_init(void) {
    rt_timer_init(&timer, "my_timer", timeout, RT_NULL,
                  rt_tick_from_millisecond(1000),
                  RT_TIMER_FLAG_PERIODIC);
    return RT_EOK;
}

// 启动/停止定时器
void timer_control(void) {
    rt_timer_start(&timer);
    // ...
    rt_timer_stop(&timer);
}

// 动态创建定时器
rt_timer_t create_timer(void) {
    return rt_timer_create("my_timer", timeout, RT_NULL,
                          rt_tick_from_millisecond(500),
                          RT_TIMER_FLAG_PERIODIC);
}

// 单次定时器
void one_shot_timer(void) {
    rt_timer_t t = rt_timer_create("one_shot", timeout, RT_NULL,
                                   rt_tick_from_millisecond(100),
                                   RT_TIMER_FLAG_ONE_SHOT);
    rt_timer_start(t);
}

// 定时器标志
// RT_TIMER_FLAG_ONE_SHOT    - 单次
// RT_TIMER_FLAG_PERIODIC    - 周期
// RT_TIMER_FLAG_SOFT_TIMER  - 软件定时器(在timer线程执行)
// RT_TIMER_FLAG_HARD_TIMER  - 硬件定时器(在中断执行)

// 定时器控制
void timer_operations(void) {
    // 修改定时周期
    rt_tick_t new_tick = rt_tick_from_millisecond(2000);
    rt_timer_control(&timer, RT_TIMER_CTRL_SET_TIME, &new_tick);

    // 重启定时器
    rt_timer_control(&timer, RT_TIMER_CTRL_SET_ONESHOT, RT_NULL);
    rt_timer_start(&timer);
}
```

---

## 五、内存管理

### 5.1 动态内存

```c
#include <rtthread.h>

// 动态内存分配
void dynamic_memory(void) {
    // 分配
    void *ptr = rt_malloc(1024);
    if (ptr == RT_NULL) {
        rt_kprintf("Memory allocation failed\n");
        return;
    }

    // 使用
    rt_memset(ptr, 0, 1024);

    // 重新分配
    ptr = rt_realloc(ptr, 2048);

    // 释放
    rt_free(ptr);

    // 分配并清零
    void *ptr2 = rt_calloc(10, 100);

    // 内存信息
    rt_uint32_t total, used, max_used;
    rt_memory_info(&total, &used, &max_used);
    rt_kprintf("Total: %d, Used: %d, Max: %d\n", total, used, max_used);
}

// 内存池
static struct rt_mempool mp;
static rt_uint8_t mp_pool[10 * 128];

int mp_init(void) {
    return rt_mp_init(&mp, "my_mp", &mp_pool[0],
                      sizeof(mp_pool), 128);
}

// 从内存池分配
void *pool_alloc(void) {
    return rt_mp_alloc(&mp, RT_WAITING_FOREVER);
}

// 释放到内存池
void pool_free(void *ptr) {
    rt_mp_free(ptr);
}

// 堆内存统计
void heap_info(void) {
    rt_uint32_t total, used, max;
    rt_memory_info(&total, &used, &max);
    rt_kprintf("Heap: total=%d, used=%d, max=%d\n", total, used, max);
}
```

---

## 六、设备框架

### 6.1 设备注册

```c
#include <rtdevice.h>

// 设备操作接口
static struct rt_device my_dev;

static rt_err_t my_dev_init(rt_device_t dev) {
    // 硬件初始化
    return RT_EOK;
}

static rt_err_t my_dev_open(rt_device_t dev, rt_uint16_t oflag) {
    return RT_EOK;
}

static rt_err_t my_dev_close(rt_device_t dev) {
    return RT_EOK;
}

static rt_size_t my_dev_read(rt_device_t dev, rt_off_t pos, void *buffer, rt_size_t size) {
    // 读取数据
    return size;
}

static rt_size_t my_dev_write(rt_device_t dev, rt_off_t pos, const void *buffer, rt_size_t size) {
    // 写入数据
    return size;
}

static rt_err_t my_dev_control(rt_device_t dev, int cmd, void *args) {
    switch (cmd) {
        case 0x01:
            // 自定义命令
            break;
    }
    return RT_EOK;
}

// 注册设备
int my_device_register(void) {
    my_dev.type = RT_Device_Class_Char;
    my_dev.init = my_dev_init;
    my_dev.open = my_dev_open;
    my_dev.close = my_dev_close;
    my_dev.read = my_dev_read;
    my_dev.write = my_dev_write;
    my_dev.control = my_dev_control;

    return rt_device_register(&my_dev, "my_dev", RT_DEVICE_FLAG_RDWR);
}

// 使用设备
void use_device(void) {
    rt_device_t dev = rt_device_find("my_dev");
    if (dev == RT_NULL) {
        rt_kprintf("Device not found\n");
        return;
    }

    rt_device_open(dev, RT_DEVICE_OFLAG_RDWR);

    char buf[] = "Hello";
    rt_device_write(dev, 0, buf, sizeof(buf));

    char rx[64];
    rt_device_read(dev, 0, rx, sizeof(rx));

    rt_device_control(dev, 0x01, RT_NULL);

    rt_device_close(dev);
}
```

### 6.2 GPIO设备

```c
#include <rtdevice.h>
#include <drv_gpio.h>

// GPIO引脚定义
#define LED_PIN    GET_PIN(A, 5)   // PA5
#define BTN_PIN    GET_PIN(C, 13)  // PC13

// GPIO输出
void gpio_output_example(void) {
    rt_pin_mode(LED_PIN, PIN_MODE_OUTPUT);
    rt_pin_write(LED_PIN, PIN_HIGH);
    rt_thread_mdelay(500);
    rt_pin_write(LED_PIN, PIN_LOW);
}

// GPIO输入
void gpio_input_example(void) {
    rt_pin_mode(BTN_PIN, PIN_MODE_INPUT_PULLUP);

    if (rt_pin_read(BTN_PIN) == PIN_LOW) {
        rt_kprintf("Button pressed\n");
    }
}

// GPIO中断
void btn_isr(void *args) {
    rt_kprintf("Button interrupt\n");
}

void gpio_interrupt_example(void) {
    rt_pin_mode(BTN_PIN, PIN_MODE_INPUT_PULLUP);
    rt_pin_attach_irq(BTN_PIN, PIN_IRQ_MODE_FALLING, btn_isr, RT_NULL);
    rt_pin_irq_enable(BTN_PIN, PIN_IRQ_ENABLE);
}

// PWM输出
void pwm_example(void) {
    rt_device_t pwm = rt_device_find("pwm1");
    rt_device_open(pwm, RT_DEVICE_OFLAG_WRONLY);

    struct rt_pwm_configuration cfg = {
        .channel = 1,
        .period = 1000000,    // 1MHz = 1us
        .pulse = 500000,      // 50%占空比
    };

    rt_device_control(pwm, PWM_CMD_SET, &cfg);
}
```

### 6.3 UART设备

```c
#include <rtdevice.h>

// UART配置
static rt_device_t uart_dev;

int uart_init(void) {
    uart_dev = rt_device_find("uart2");
    if (uart_dev == RT_NULL) {
        return -RT_ERROR;
    }

    // 配置串口参数
    struct serial_configure cfg = BAUDRATE_115200 | DATA_BITS_8 | STOP_BITS_1 | PARITY_NONE;
    rt_device_control(uart_dev, RT_DEVICE_CTRL_CONFIG, &cfg);

    // 打开设备
    rt_device_open(uart_dev, RT_DEVICE_FLAG_INT_RX);

    // 设置接收回调
    rt_device_set_rx_indicate(uart_dev, uart_rx_ind);

    return RT_EOK;
}

// 接收回调
static rt_err_t uart_rx_ind(rt_device_t dev, rt_size_t size) {
    // 唤醒接收线程
    rt_sem_release(&rx_sem);
    return RT_EOK;
}

// 发送数据
void uart_send(const void *data, rt_size_t len) {
    rt_device_write(uart_dev, 0, data, len);
}

// 接收数据(中断模式)
static struct rt_semaphore rx_sem;
static rt_uint8_t rx_buffer[256];
static rt_size_t rx_index = 0;

void uart_rx_thread(void *param) {
    rt_sem_init(&rx_sem, "rx_sem", 0, RT_IPC_FLAG_FIFO);

    while (1) {
        rt_sem_take(&rx_sem, RT_WAITING_FOREVER);

        rt_size_t len;
        while ((len = rt_device_read(uart_dev, -1, rx_buffer + rx_index,
                                      sizeof(rx_buffer) - rx_index)) > 0) {
            rx_index += len;
        }

        // 处理接收到的数据
        process_uart_data(rx_buffer, rx_index);
        rx_index = 0;
    }
}

// DMA接收
void uart_dma_init(void) {
    rt_device_control(uart_dev, RT_DEVICE_CTRL_CONFIG, &dma_cfg);
    rt_device_open(uart_dev, RT_DEVICE_FLAG_DMA_RX);
}
```

### 6.4 I2C设备

```c
#include <rtdevice.h>

// I2C设备
static struct rt_i2c_bus_device *i2c_bus;

int i2c_init(void) {
    i2c_bus = (struct rt_i2c_bus_device *)rt_device_find("i2c1");
    if (i2c_bus == RT_NULL) {
        return -RT_ERROR;
    }
    return RT_EOK;
}

// I2C读写
rt_size_t i2c_read(rt_uint8_t addr, rt_uint8_t reg, rt_uint8_t *buf, rt_size_t len) {
    struct rt_i2c_msg msgs[2];

    msgs[0].addr = addr;
    msgs[0].flags = RT_I2C_WR;
    msgs[0].buf = &reg;
    msgs[0].len = 1;

    msgs[1].addr = addr;
    msgs[1].flags = RT_I2C_RD;
    msgs[1].buf = buf;
    msgs[1].len = len;

    return rt_i2c_transfer(i2c_bus, msgs, 2);
}

rt_size_t i2c_write(rt_uint8_t addr, rt_uint8_t reg, rt_uint8_t *buf, rt_size_t len) {
    struct rt_i2c_msg msgs[1];
    rt_uint8_t *data = rt_malloc(len + 1);

    data[0] = reg;
    rt_memcpy(data + 1, buf, len);

    msgs[0].addr = addr;
    msgs[0].flags = RT_I2C_WR;
    msgs[0].buf = data;
    msgs[0].len = len + 1;

    rt_size_t ret = rt_i2c_transfer(i2c_bus, msgs, 1);
    rt_free(data);
    return ret;
}

// I2C扫描
void i2c_scan(void) {
    for (rt_uint8_t addr = 0x08; addr < 0x78; addr++) {
        struct rt_i2c_msg msg;
        msg.addr = addr;
        msg.flags = RT_I2C_RD;
        msg.buf = RT_NULL;
        msg.len = 0;

        if (rt_i2c_transfer(i2c_bus, &msg, 1) == 1) {
            rt_kprintf("Found device at 0x%02X\n", addr);
        }
    }
}
```

---

## 七、FinSH Shell

### 7.1 Shell命令

```c
#include <finsh.h>

// 导出函数到Shell
void hello(void) {
    rt_kprintf("Hello RT-Thread!\n");
}
MSH_CMD_EXPORT(hello, say hello);

// 带参数的命令
int cmd_set(int argc, char **argv) {
    if (argc < 3) {
        rt_kprintf("Usage: set <key> <value>\n");
        return -1;
    }

    rt_kprintf("Setting %s = %s\n", argv[1], argv[2]);
    return 0;
}
MSH_CMD_EXPORT(cmd_set, set parameter);

// FinSH函数(不带参数)
void list_threads(void) {
    rt_thread_t tid;
    rt_kprintf("Thread List:\n");
    // 遍历线程链表
    for (tid = (rt_thread_t)rt_object_find("my_task", RT_Object_Class_Thread);
         tid != RT_NULL;
         tid = (rt_thread_t)rt_list_entry(tid->list.next, struct rt_object, list)) {
        rt_kprintf("  %s: priority=%d, stack=%d\n",
                   tid->name, tid->current_priority, tid->stack_size);
    }
}
FINSH_FUNCTION_EXPORT(list_threads, list all threads);

// 系统命令
// list_thread  - 列出线程
// list_sem     - 列出信号量
// list_mutex   - 列出互斥锁
// list_event   - 列出事件
// list_mq      - 列出消息队列
// list_mb      - 列出邮箱
// list_timer   - 列出定时器
// list_device  - 列出设备
// version      - 版本信息
// free         - 内存信息
```

---

## 八、组件系统

### 8.1 自动初始化

```c
#include <rtthread.h>

// 组件初始化级别
// INIT_BOARD_EXPORT     - 板级初始化(最先)
// INIT_PREV_EXPORT      - 前期初始化
// INIT_DEVICE_EXPORT    - 设备初始化
// INIT_COMPONENT_EXPORT - 组件初始化
// INIT_ENV_EXPORT       - 环境初始化
// INIT_APP_EXPORT       - 应用初始化(最后)

// 板级初始化
int board_init(void) {
    // 系统时钟、GPIO等初始化
    return 0;
}
INIT_BOARD_EXPORT(board_init);

// 设备初始化
int sensor_init(void) {
    // 注册传感器设备
    return 0;
}
INIT_DEVICE_EXPORT(sensor_init);

// 应用初始化
int app_init(void) {
    // 创建应用线程
    return 0;
}
INIT_APP_EXPORT(app_init);
```

### 8.2 软件包管理

```c
// Env工具管理软件包
// 1. 在packages目录下选择软件包
// 2. pkgs --update  更新软件包
// 3. scons  重新编译

// 常用软件包
// - cJSON: JSON解析
// - EasyFlash: Flash存储
// - FreeModbus: Modbus协议
// - LittlevGL2RTT: LVGL移植
// - RT-Thread-Nano: Nano版本

// 使用cJSON
#include <cJSON.h>

void json_example(void) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "name", "RT-Thread");
    cJSON_AddNumberToObject(root, "version", 5.0);

    char *json = cJSON_Print(root);
    rt_kprintf("%s\n", json);

    cJSON_free(json);
    cJSON_Delete(root);
}
```

---

## 九、网络编程

### 9.1 Socket接口

```c
#include <sys/socket.h>
#include <netdb.h>

// TCP客户端
int tcp_client(void) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(8080);
    server.sin_addr.s_addr = inet_addr("192.168.1.100");

    connect(sock, (struct sockaddr *)&server, sizeof(server));

    char buf[] = "Hello";
    send(sock, buf, sizeof(buf), 0);

    char recv_buf[128];
    int len = recv(sock, recv_buf, sizeof(recv_buf), 0);
    rt_kprintf("Received: %.*s\n", len, recv_buf);

    closesocket(sock);
    return 0;
}

// TCP服务器
void tcp_server(void) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in server;
    server.sin_family = AF_INET;
    server.sin_port = htons(8080);
    server.sin_addr.s_addr = INADDR_ANY;

    bind(sock, (struct sockaddr *)&server, sizeof(server));
    listen(sock, 5);

    while (1) {
        struct sockaddr_in client;
        socklen_t len = sizeof(client);
        int client_sock = accept(sock, (struct sockaddr *)&client, &len);

        char buf[128];
        int recv_len = recv(client_sock, buf, sizeof(buf), 0);
        send(client_sock, buf, recv_len, 0);

        closesocket(client_sock);
    }
}

// UDP
void udp_example(void) {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(1234);
    addr.sin_addr.s_addr = INADDR_ANY;

    bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    char buf[128];
    struct sockaddr_in from;
    socklen_t fromlen = sizeof(from);
    recvfrom(sock, buf, sizeof(buf), 0, (struct sockaddr *)&from, &fromlen);
}
```

---

## 附录：RT-Thread版本对比

| 版本 | 特点 | 适用场景 |
|------|------|----------|
| 标准版 | 完整内核+组件 | 复杂应用 |
| Nano版 | 极简内核(3KB) | 资源受限 |
| Smart版 | Linux兼容 | MPU平台 |

---

## 相关链接

- [[RT-Thread基础]] - RT-Thread基础
- [[FreeRTOS基础]] - FreeRTOS
- [[Zephyr RTOS]] - Zephyr
- [[嵌入式系统基础]] - 嵌入式系统
