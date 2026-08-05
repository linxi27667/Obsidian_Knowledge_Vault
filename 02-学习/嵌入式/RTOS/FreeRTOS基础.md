# FreeRTOS基础

## 核心概念

- **FreeRTOS** - 市场占有率最高的嵌入式RTOS
- **任务(Task)** - 独立的执行单元
- **调度器(Scheduler)** - 决定哪个任务运行
- **队列(Queue)** - 任务间通信

---

## 一、FreeRTOS概述

### 1.1 特点

| 特点 | 说明 |
|------|------|
| 占用小 | 最小6-10KB ROM |
| 实时性 | 可配置调度策略 |
| 可移植 | 支持40+处理器架构 |
| 开源 | MIT许可 |
| 生态 | 丰富组件 |

---

### 1.2 vs RT-Thread

| 特性 | FreeRTOS | RT-Thread |
|------|----------|-----------|
| 内核 | 极简 | 丰富 |
| 组件 | 需第三方 | 内置 |
| 设备框架 | 无 | 完整 |
| Shell | 无 | FinSH |
| 包管理 | 无 | Env |
| 适用 | 简单应用 | 复杂应用 |

---

## 二、任务管理

### 2.1 创建任务

```c
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

void task1(void *arg) {
    while (1) {
        printf("Task 1\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void task2(void *arg) {
    while (1) {
        printf("Task 2\n");
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

void app_main(void) {
    xTaskCreate(task1, "task1", 2048, NULL, 5, NULL);
    xTaskCreate(task2, "task2", 2048, NULL, 5, NULL);
}
```

---

### 2.2 任务参数

```c
xTaskCreate(
    task_func,      // 任务函数
    "task_name",    // 任务名称
    stack_size,     // 栈大小(字节)
    &param,         // 参数
    priority,       // 优先级
    &handle         // 任务句柄
);
```

---

### 2.3 任务状态

```
┌─────┐   创建    ┌──────┐   就绪   ┌──────┐
│ 创建 │ ──────→ │ 就绪  │ ←─────→ │ 运行  │
└─────┘         └──────┘         └──────┘
                    ↑                  │
                    │                  ↓
                ┌──────┐         ┌──────┐
                │ 阻塞  │ ←─────→ │ 挂起  │
                └──────┘         └──────┘
```

---

### 2.4 任务控制

```c
// 删除任务
vTaskDelete(handle);
vTaskDelete(NULL);  // 删除自己

// 挂起任务
vTaskSuspend(handle);
vTaskSuspendAll();  // 挂起所有

// 恢复任务
vTaskResume(handle);
xTaskResumeAll();  // 恢复所有

// 设置优先级
vTaskPrioritySet(handle, new_priority);

// 获取优先级
UBaseType_t prio = uxTaskPriorityGet(handle);

// 延时
vTaskDelay(pdMS_TO_TICKS(100));           // 相对延时
vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(100));  // 绝对延时

// 获取任务信息
TaskStatus_t task_status;
vTaskGetInfo(handle, &task_status, pdTRUE, eInvalid);
```

---

## 三、队列

### 3.1 创建与使用

```c
QueueHandle_t queue;

void producer(void *arg) {
    int data = 0;
    while (1) {
        data++;
        xQueueSend(queue, &data, portMAX_DELAY);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void consumer(void *arg) {
    int data;
    while (1) {
        if (xQueueReceive(queue, &data, portMAX_DELAY)) {
            printf("Received: %d\n", data);
        }
    }
}

void app_main(void) {
    queue = xQueueCreate(10, sizeof(int));
    xTaskCreate(producer, "producer", 2048, NULL, 5, NULL);
    xTaskCreate(consumer, "consumer", 2048, NULL, 5, NULL);
}
```

---

### 3.2 队列操作

```c
// 创建队列
QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength, UBaseType_t uxItemSize);

// 发送
BaseType_t xQueueSend(QueueHandle_t xQueue, const void *pvItemToQueue, TickType_t xTicksToWait);
BaseType_t xQueueSendToBack(QueueHandle_t xQueue, const void *pvItemToQueue, TickType_t xTicksToWait);
BaseType_t xQueueSendToFront(QueueHandle_t xQueue, const void *pvItemToQueue, TickType_t xTicksToWait);
BaseType_t xQueueSendFromISR(QueueHandle_t xQueue, const void *pvItemToQueue, BaseType_t *pxHigherPriorityTaskWoken);

// 接收
BaseType_t xQueueReceive(QueueHandle_t xQueue, void *pvBuffer, TickType_t xTicksToWait);
BaseType_t xQueuePeek(QueueHandle_t xQueue, void *pvBuffer, TickType_t xTicksToWait);

// 查询
UBaseType_t uxQueueMessagesWaiting(QueueHandle_t xQueue);
UBaseType_t uxQueueSpacesAvailable(QueueHandle_t xQueue);
```

---

## 四、信号量

### 4.1 二值信号量

```c
SemaphoreHandle_t sem;

void task_wait(void *arg) {
    while (1) {
        if (xSemaphoreTake(sem, portMAX_DELAY)) {
            printf("Got semaphore\n");
        }
    }
}

void task_give(void *arg) {
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(2000));
        xSemaphoreGive(sem);
    }
}

void app_main(void) {
    sem = xSemaphoreCreateBinary();
    xTaskCreate(task_wait, "wait", 2048, NULL, 5, NULL);
    xTaskCreate(task_give, "give", 2048, NULL, 5, NULL);
}
```

---

### 4.2 计数信号量

```c
// 创建: 最大值10, 初始值0
SemaphoreHandle_t sem = xSemaphoreCreateCounting(10, 0);

// 释放(增加)
xSemaphoreGive(sem);

// 获取(减少)
xSemaphoreTake(sem, portMAX_DELAY);
```

---

### 4.3 互斥锁

```c
SemaphoreHandle_t mutex;

void task1(void *arg) {
    while (1) {
        xSemaphoreTake(mutex, portMAX_DELAY);
        // 临界区
        printf("Task 1 in critical section\n");
        vTaskDelay(pdMS_TO_TICKS(1000));
        xSemaphoreGive(mutex);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void) {
    mutex = xSemaphoreCreateMutex();
    xTaskCreate(task1, "task1", 2048, NULL, 5, NULL);
    xTaskCreate(task2, "task2", 2048, NULL, 5, NULL);
}
```

---

### 4.4 递归互斥锁

```c
SemaphoreHandle_t recursive_mutex;

void recursive_function(int depth) {
    xSemaphoreTakeRecursive(recursive_mutex, portMAX_DELAY);

    if (depth > 0) {
        recursive_function(depth - 1);
    }

    xSemaphoreGiveRecursive(recursive_mutex);
}

void app_main(void) {
    recursive_mutex = xSemaphoreCreateRecursiveMutex();
}
```

---

## 五、事件组

### 5.1 事件操作

```c
EventGroupHandle_t event_group;

#define EVENT_BIT_0 (1 << 0)
#define EVENT_BIT_1 (1 << 1)
#define EVENT_BIT_2 (1 << 2)

void task_wait(void *arg) {
    while (1) {
        // 等待任意事件
        EventBits_t bits = xEventGroupWaitBits(
            event_group,
            EVENT_BIT_0 | EVENT_BIT_1,
            pdTRUE,          // 清除
            pdFALSE,         // 任意位
            portMAX_DELAY
        );

        if (bits & EVENT_BIT_0) printf("Event 0\n");
        if (bits & EVENT_BIT_1) printf("Event 1\n");
    }
}

void task_set(void *arg) {
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        xEventGroupSetBits(event_group, EVENT_BIT_0);
    }
}

void app_main(void) {
    event_group = xEventGroupCreate();
    xTaskCreate(task_wait, "wait", 2048, NULL, 5, NULL);
    xTaskCreate(task_set, "set", 2048, NULL, 5, NULL);
}
```

---

### 5.2 同步

```c
// 多任务同步
#define ALL_SYNC_BITS (EVENT_BIT_0 | EVENT_BIT_1 | EVENT_BIT_2)

void sync_task(void *arg) {
    int task_id = (int)arg;

    // 做准备工作
    vTaskDelay(pdMS_TO_TICKS(task_id * 100));

    // 设置同步位
    xEventGroupSync(event_group,
                    (1 << task_id),     // 设置的位
                    ALL_SYNC_BITS,      // 等待所有位
                    portMAX_DELAY);

    // 所有任务都到达这里后才继续
    printf("Task %d synced\n", task_id);
}
```

---

## 六、软件定时器

### 6.1 定时器操作

```c
TimerHandle_t timer;

void timer_callback(TimerHandle_t xTimer) {
    printf("Timer fired\n");
}

void app_main(void) {
    // 创建定时器
    timer = xTimerCreate(
        "my_timer",
        pdMS_TO_TICKS(1000),  // 周期
        pdTRUE,               // 自动重载
        NULL,
        timer_callback
    );

    // 启动定时器
    xTimerStart(timer, 0);

    // 停止定时器
    // xTimerStop(timer, 0);

    // 改变周期
    // xTimerChangePeriod(timer, pdMS_TO_TICKS(2000), 0);

    // 重置定时器
    // xTimerReset(timer, 0);
}
```

---

## 七、任务通知

### 7.1 代替信号量

```c
void task_wait(void *arg) {
    while (1) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        printf("Notified\n");
    }
}

void task_notify(void *arg) {
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        xTaskNotifyGive(task_handle);
    }
}
```

---

### 7.2 传递数值

```c
void task_wait(void *arg) {
    uint32_t value;
    while (1) {
        if (xTaskNotifyWait(0, ULONG_MAX, &value, portMAX_DELAY)) {
            printf("Value: %lu\n", value);
        }
    }
}

void task_notify(void *arg) {
    uint32_t count = 0;
    while (1) {
        count++;
        xTaskNotify(task_handle, count, eSetValueWithOverwrite);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## 八、内存管理

### 8.1 堆策略

| 方案 | 特点 |
|------|------|
| heap_1 | 只分配不释放 |
| heap_2 | 允许释放,不合并 |
| heap_4 | 合并空闲块 |
| heap_5 | 跨区域管理 |

```c
// 配置 heap_4
#define configTOTAL_HEAP_SIZE  (32 * 1024)

// 动态分配
void *pvPortMalloc(size_t xSize);
void vPortFree(void *pv);
size_t xPortGetFreeHeapSize(void);
size_t xPortGetMinimumEverFreeHeapSize(void);
```

---

## 九、中断管理

### 9.1 ISR与任务通信

```c
QueueHandle_t isr_queue;

void IRAM_ATTR gpio_isr_handler(void *arg) {
    int data = 1;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    xQueueSendFromISR(isr_queue, &data, &xHigherPriorityTaskWoken);

    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

void processing_task(void *arg) {
    int data;
    while (1) {
        if (xQueueReceive(isr_queue, &data, portMAX_DELAY)) {
            printf("ISR data: %d\n", data);
        }
    }
}
```

---

## 十、配置

### 10.1 FreeRTOSConfig.h

```c
// 调度器
#define configUSE_PREEMPTION            1
#define configUSE_TIME_SLICING          1
#define configTICK_RATE_HZ             1000

// 内存
#define configTOTAL_HEAP_SIZE          (32 * 1024)
#define configMINIMAL_STACK_SIZE       (128)

// 任务
#define configMAX_PRIORITIES           5
#define configUSE_MUTEXES              1
#define configUSE_COUNTING_SEMAPHORES  1
#define configUSE_RECURSIVE_MUTEXES    1
#define configUSE_TASK_NOTIFICATIONS   1

// 定时器
#define configUSE_TIMERS               1
#define configTIMER_TASK_PRIORITY      5
#define configTIMER_QUEUE_LENGTH       10
#define configTIMER_TASK_STACK_DEPTH   2048

// 统计
#define configGENERATE_RUN_TIME_STATS  1
#define configUSE_TRACE_FACILITY       1
```

---

## 附录：API速查表

### 任务

| API | 说明 |
|-----|------|
| xTaskCreate | 创建任务 |
| vTaskDelete | 删除任务 |
| vTaskDelay | 延时 |
| vTaskSuspend | 挂起 |
| vTaskResume | 恢复 |

### 队列

| API | 说明 |
|-----|------|
| xQueueCreate | 创建队列 |
| xQueueSend | 发送 |
| xQueueReceive | 接收 |
| xQueuePeek | 查看 |

### 信号量

| API | 说明 |
|-----|------|
| xSemaphoreCreateBinary | 二值信号量 |
| xSemaphoreCreateMutex | 互斥锁 |
| xSemaphoreTake | 获取 |
| xSemaphoreGive | 释放 |

---

## 相关链接

- [[RT-Thread基础]] - RT-Thread对比
- [[STM32基础]] - STM32 + FreeRTOS
- [[ESP-IDF开发]] - ESP32 + FreeRTOS
