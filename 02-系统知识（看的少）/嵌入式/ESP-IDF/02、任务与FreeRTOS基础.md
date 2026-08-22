# ESP-IDF 任务与FreeRTOS基础 （多任务编程与任务间通信）

## 核心概念

- **ESP32双核架构** - Pro CPU（协议核心）和 App CPU（应用核心），可独立运行任务
- **FreeRTOS内核** - 实时操作系统，负责任务调度和资源管理
- **任务(Task)** - 执行的最小单位，每个任务有自己的栈空间和执行上下文
- **任务优先级** - 0（最低）到 24（最高），数值越大优先级越高

---

## 一、任务基础

### 1.1 创建任务

```c
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

BaseType_t xTaskCreate(
    TaskFunction_t pvTaskCode,      // 任务函数
    const char * const pcName,      // 任务名称（调试用）
    const uint32_t usStackDepth,    // 栈大小（单位：字，4字节）
    void * const pvParameters,      // 传递给任务的参数
    UBaseType_t uxPriority,         // 优先级（0-24）
    TaskHandle_t * const pxCreatedTask  // 任务句柄（可选）
);
```

| 参数 | 说明 | 常用值 |
|------|------|--------|
| `pvTaskCode` | 任务入口函数 | 函数指针 |
| `pcName` | 任务名称 | 调试显示用 |
| `usStackDepth` | 栈大小（字） | 2048-8192 |
| `pvParameters` | 任务参数 | NULL或结构体指针 |
| `uxPriority` | 优先级 | 1-10（建议范围） |
| `pxCreatedTask` | 任务句柄 | NULL或&handle |

---

### 1.2 任务函数原型

```c
void vTaskFunction(void *pvParameters)
{
    // 任务初始化代码
    
    while (1) {
        // 任务主体代码
        
        // 必须让出CPU，否则 starving 其他任务
        vTaskDelay(pdMS_TO_TICKS(100));  // 延时100ms
    }
    
    // 如果任务要结束，必须删除自己
    vTaskDelete(NULL);
}
```

---

### 1.3 删除任务

```c
// 删除自己
vTaskDelete(NULL);

// 删除指定任务
vTaskDelete(xTaskHandle);
```

**任务状态转换图：**

```
                    ┌──────────────┐
                    │    就绪态     │
                    │   (Ready)    │
                    └──────┬───────┘
                           │ 调度器选择
                           ▼
    ┌──────────┐    ┌──────────────┐    ┌──────────┐
    │  阻塞态   │<---│    运行态     │--->│  挂起态   │
    │(Blocked) │    │  (Running)   │    │(Suspended)│
    └────┬─────┘    └──────────────┘    └──────────┘
         │ 事件/延时        │
         │                 │ 调用vTaskSuspend()
         └─────────────────┘
                           vTaskResume()
```

| 状态 | 说明 |
|------|------|
| **就绪态** | 等待CPU执行 |
| **运行态** | 正在执行 |
| **阻塞态** | 等待事件或延时 |
| **挂起态** | 被显式挂起，不参与调度 |

---

## 二、任务参数详解

### 2.1 栈大小配置

```c
// 创建任务时配置栈大小（单位：字 = 4字节）
xTaskCreate(task_func, "Task", 2048, NULL, 5, NULL);  // 8KB栈

// ESP-IDF推荐栈大小
#define STACK_SIZE_SMALL   2048   // 8KB - 简单任务
#define STACK_SIZE_MEDIUM  4096   // 16KB - 一般任务
#define STACK_SIZE_LARGE   8192   // 32KB - 复杂任务
```

**栈溢出检测：**

```c
// 启用栈溢出检测（menuconfig）
// CONFIG_FREERTOS_CHECK_STACKOVERFLOW_CANARY=y

// 监控任务栈使用情况
UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL);
ESP_LOGI(TAG, "Stack remaining: %d words", uxHighWaterMark);
```

---

### 2.2 优先级配置

```c
// 优先级范围：0（最低）到 configMAX_PRIORITIES-1（最高，默认24）

#define PRIORITY_LOW       1   // 后台任务
#define PRIORITY_NORMAL    5   // 普通任务
#define PRIORITY_HIGH      10  // 重要任务
#define PRIORITY_CRITICAL  20  // 关键任务（慎用）

// 创建不同优先级的任务
xTaskCreate(task_background, "BG", 2048, NULL, PRIORITY_LOW, NULL);
xTaskCreate(task_normal, "Normal", 4096, NULL, PRIORITY_NORMAL, NULL);
xTaskCreate(task_urgent, "Urgent", 4096, NULL, PRIORITY_HIGH, NULL);
```

**优先级调度规则：**

```
调度器行为：
┌────────────────────────────────────────────────┐
│  1. 总是选择就绪态中优先级最高的任务执行         │
│  2. 同优先级任务使用时间片轮转（默认100Hz）      │
│  3. 高优先级任务就绪时立即抢占低优先级任务       │
└────────────────────────────────────────────────┘
```

---

### 2.3 核心绑定（双核专用）

```c
#include "freertos/task.h"
#include "esp_freertos_hooks.h"

// 创建绑定到特定核心的任务
xTaskCreatePinnedToCore(
    task_func,           // 任务函数
    "TaskName",          // 名称
    4096,                // 栈大小
    NULL,                // 参数
    5,                   // 优先级
    &xHandle,            // 句柄
    tskNO_AFFINITY       // 核心ID: 0=Pro, 1=App, tskNO_AFFINITY=任意
);

// 核心分配建议
#define CORE_PRO  0   // 协议核心（WiFi/BT）
#define CORE_APP  1   // 应用核心（用户任务）
```

**双核任务分配：**

```
ESP32双核任务分布：
┌─────────────────────────────────────────────────┐
│                  Core 0 (Pro CPU)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  WiFi任务   │  │   BT任务    │  │ 系统任务 │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│  建议：TCP/IP、BLE、系统协议栈相关任务           │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│                  Core 1 (App CPU)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ 传感器读取  │  │  数据处理   │  │ 用户界面 │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│  建议：应用逻辑、传感器、控制算法               │
└─────────────────────────────────────────────────┘
```

---

## 三、任务调度机制

### 3.1 抢占式调度

```c
// 示例：高优先级任务抢占
void high_priority_task(void *pvParameters)
{
    while (1) {
        ESP_LOGI(TAG, "High priority task running");
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void low_priority_task(void *pvParameters)
{
    while (1) {
        ESP_LOGI(TAG, "Low priority task running");
        // 没有延时，会一直占用CPU
        // 高优先级就绪时会立即抢占
    }
}
```

---

### 3.2 时间片轮转

```c
// 同优先级任务按时间片轮转（默认10ms）
void task_a(void *pvParameters)
{
    while (1) {
        ESP_LOGI(TAG, "Task A");
        // 会执行约10ms然后切换到Task B
    }
}

void task_b(void *pvParameters)
{
    while (1) {
        ESP_LOGI(TAG, "Task B");
        // 会执行约10ms然后切换到Task A
    }
}

// 创建同优先级任务
xTaskCreate(task_a, "TaskA", 2048, NULL, 5, NULL);
xTaskCreate(task_b, "TaskB", 2048, NULL, 5, NULL);
```

---

## 四、任务间通信 - 队列(Queue)

### 4.1 创建队列

```c
#include "freertos/queue.h"

// 创建队列
QueueHandle_t xQueueCreate(
    UBaseType_t uxQueueLength,    // 队列长度（元素个数）
    UBaseType_t uxItemSize        // 每个元素大小（字节）
);

// 示例：创建可容纳10个int的队列
QueueHandle_t xQueue = xQueueCreate(10, sizeof(int));

if (xQueue == NULL) {
    ESP_LOGE(TAG, "Queue creation failed");
}
```

---

### 4.2 发送数据到队列

```c
// 发送到队列尾部（阻塞直到成功）
BaseType_t xQueueSend(
    QueueHandle_t xQueue,      // 队列句柄
    const void *pvItemToQueue, // 要发送的数据指针
    TickType_t xTicksToWait    // 等待时间（0=不等待，portMAX_DELAY=无限）
);

// 发送到队列头部（高优先级）
BaseType_t xQueueSendToFront(
    QueueHandle_t xQueue,
    const void *pvItemToQueue,
    TickType_t xTicksToWait
);

// 从中断服务程序发送
BaseType_t xQueueSendFromISR(
    QueueHandle_t xQueue,
    const void *pvItemToQueue,
    BaseType_t *pxHigherPriorityTaskWoken
);
```

---

### 4.3 从队列接收数据

```c
// 从队列接收（阻塞直到有数据）
BaseType_t xQueueReceive(
    QueueHandle_t xQueue,   // 队列句柄
    void *pvBuffer,         // 接收缓冲区
    TickType_t xTicksToWait // 等待时间
);

// 查看队列前端数据（不移除）
BaseType_t xQueuePeek(
    QueueHandle_t xQueue,
    void *pvBuffer,
    TickType_t xTicksToWait
);

// 获取队列中消息数量
UBaseType_t uxQueueMessagesWaiting(QueueHandle_t xQueue);
```

---

## 五、任务同步 - 信号量与互斥锁

### 5.1 二值信号量

```c
#include "freertos/semphr.h"

// 创建二值信号量
SemaphoreHandle_t xSemaphoreCreateBinary(void);

// 释放信号量（发送信号）
BaseType_t xSemaphoreGive(SemaphoreHandle_t xSemaphore);
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t xSemaphore, 
                                  BaseType_t *pxHigherPriorityTaskWoken);

// 获取信号量（等待信号）
BaseType_t xSemaphoreTake(SemaphoreHandle_t xSemaphore, 
                          TickType_t xTicksToWait);
```

**使用场景：任务通知**

```c
SemaphoreHandle_t xBinarySemaphore = NULL;

// ISR中发送信号
void IRAM_ATTR gpio_isr_handler(void *arg)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(xBinarySemaphore, &xHigherPriorityTaskWoken);
    if (xHigherPriorityTaskWoken) {
        portYIELD_FROM_ISR();
    }
}

// 任务中等待信号
void task_wait_for_isr(void *pvParameters)
{
    xBinarySemaphore = xSemaphoreCreateBinary();
    
    while (1) {
        if (xSemaphoreTake(xBinarySemaphore, portMAX_DELAY) == pdTRUE) {
            ESP_LOGI(TAG, "ISR triggered!");
            // 处理中断事件
        }
    }
}
```

---

### 5.2 计数信号量

```c
// 创建计数信号量
SemaphoreHandle_t xSemaphoreCreateCounting(
    UBaseType_t uxMaxCount,     // 最大计数值
    UBaseType_t uxInitialCount  // 初始计数值
);

// 示例：资源池管理（最多5个资源）
SemaphoreHandle_t xResourceSemaphore = xSemaphoreCreateCounting(5, 5);

// 获取资源
void use_resource(void)
{
    if (xSemaphoreTake(xResourceSemaphore, pdMS_TO_TICKS(100)) == pdTRUE) {
        // 使用资源
        // ...
        // 释放资源
        xSemaphoreGive(xResourceSemaphore);
    } else {
        ESP_LOGW(TAG, "No resource available");
    }
}
```

---

### 5.3 互斥锁(Mutex)

```c
// 创建互斥锁
SemaphoreHandle_t xSemaphoreCreateMutex(void);

// 递归互斥锁（允许同任务多次获取）
SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(void);
```

**保护共享资源：**

```c
SemaphoreHandle_t xMutex = NULL;
int shared_counter = 0;

void init_mutex(void)
{
    xMutex = xSemaphoreCreateMutex();
}

void increment_counter(void)
{
    // 获取互斥锁
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
        // 临界区开始
        shared_counter++;
        // 临界区结束
        xSemaphoreGive(xMutex);
    }
}
```

---

## 六、双核任务分配

### 6.1 核心亲和性设置

```c
// 获取当前任务运行的核心ID
BaseType_t xPortGetCoreID(void);

// 获取任务信息
eTaskState eTaskGetState(TaskHandle_t xTask);
UBaseType_t uxTaskPriorityGet(TaskHandle_t xTask);
```

---

### 6.2 核心间通信

```c
// 核心0任务
void core0_task(void *pvParameters)
{
    while (1) {
        // 处理网络数据
        process_network_data();
        
        // 通知核心1
        xQueueSend(xCoreQueue, &data, portMAX_DELAY);
    }
}

// 核心1任务
void core1_task(void *pvParameters)
{
    while (1) {
        Data_t data;
        if (xQueueReceive(xCoreQueue, &data, portMAX_DELAY)) {
            // 处理数据
            process_sensor_data(&data);
        }
    }
}

void app_main(void)
{
    xCoreQueue = xQueueCreate(10, sizeof(Data_t));
    
    // 核心0运行网络任务
    xTaskCreatePinnedToCore(core0_task, "Core0", 4096, NULL, 5, NULL, 0);
    
    // 核心1运行应用任务
    xTaskCreatePinnedToCore(core1_task, "Core1", 4096, NULL, 5, NULL, 1);
}
```

---

## 七、完整示例

### 示例1：生产者-消费者队列模型

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"

static const char *TAG = "PROD_CONS";

// 数据类型
typedef struct {
    int sensor_id;
    float value;
    uint32_t timestamp;
} SensorData_t;

// 队列句柄
static QueueHandle_t xDataQueue = NULL;

// 生产者任务
void vProducerTask(void *pvParameters)
{
    SensorData_t data;
    int counter = 0;
    
    while (1) {
        // 模拟传感器读取
        data.sensor_id = 1;
        data.value = 25.0f + (counter % 10);
        data.timestamp = xTaskGetTickCount();
        
        // 发送到队列（等待100ms）
        if (xQueueSend(xDataQueue, &data, pdMS_TO_TICKS(100)) == pdPASS) {
            ESP_LOGI(TAG, "Produced: sensor=%d, value=%.1f", 
                     data.sensor_id, data.value);
        } else {
            ESP_LOGW(TAG, "Queue full, data dropped");
        }
        
        counter++;
        vTaskDelay(pdMS_TO_TICKS(500));  // 每500ms生产一次
    }
}

// 消费者任务
void vConsumerTask(void *pvParameters)
{
    SensorData_t data;
    
    while (1) {
        // 从队列接收（无限等待）
        if (xQueueReceive(xDataQueue, &data, portMAX_DELAY) == pdPASS) {
            ESP_LOGI(TAG, "Consumed: sensor=%d, value=%.1f, time=%lu", 
                     data.sensor_id, data.value, data.timestamp);
            
            // 模拟数据处理耗时
            vTaskDelay(pdMS_TO_TICKS(200));
        }
    }
}

void app_main(void)
{
    // 创建队列（容量5个元素）
    xDataQueue = xQueueCreate(5, sizeof(SensorData_t));
    
    if (xDataQueue == NULL) {
        ESP_LOGE(TAG, "Failed to create queue");
        return;
    }
    
    // 创建生产者和消费者任务
    xTaskCreate(vProducerTask, "Producer", 2048, NULL, 5, NULL);
    xTaskCreate(vConsumerTask, "Consumer", 2048, NULL, 5, NULL);
}
```

---

### 示例2：使用互斥锁保护共享资源

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"

static const char *TAG = "MUTEX";

// 共享资源
static int shared_counter = 0;
static SemaphoreHandle_t xMutex = NULL;

// 任务1：增加计数器
void vTaskIncrement(void *pvParameters)
{
    const char *taskName = (const char *)pvParameters;
    
    while (1) {
        // 获取互斥锁
        if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
            // 读取-修改-写入
            int temp = shared_counter;
            vTaskDelay(pdMS_TO_TICKS(10));  // 模拟处理时间
            shared_counter = temp + 1;
            
            ESP_LOGI(TAG, "%s: counter = %d", taskName, shared_counter);
            
            // 释放互斥锁
            xSemaphoreGive(xMutex);
        }
        
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

// 任务2：减少计数器
void vTaskDecrement(void *pvParameters)
{
    const char *taskName = (const char *)pvParameters;
    
    while (1) {
        if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
            int temp = shared_counter;
            vTaskDelay(pdMS_TO_TICKS(10));
            shared_counter = temp - 1;
            
            ESP_LOGI(TAG, "%s: counter = %d", taskName, shared_counter);
            
            xSemaphoreGive(xMutex);
        }
        
        vTaskDelay(pdMS_TO_TICKS(150));
    }
}

void app_main(void)
{
    // 创建互斥锁
    xMutex = xSemaphoreCreateMutex();
    
    if (xMutex == NULL) {
        ESP_LOGE(TAG, "Failed to create mutex");
        return;
    }
    
    // 创建两个任务同时访问共享资源
    xTaskCreate(vTaskIncrement, "TaskInc", 2048, "Increment", 5, NULL);
    xTaskCreate(vTaskDecrement, "TaskDec", 2048, "Decrement", 5, NULL);
}
```

---

### 示例3：双核任务分配策略

```c
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_wifi.h"

static const char *TAG = "DUAL_CORE";

#define CORE_PRO  0   // 协议核心
#define CORE_APP  1   // 应用核心

// 队列用于核心间通信
QueueHandle_t xCommandQueue = NULL;
QueueHandle_t xResultQueue = NULL;

// 命令类型
typedef enum {
    CMD_READ_SENSOR,
    CMD_PROCESS_DATA,
    CMD_SEND_NETWORK
} CommandType_t;

typedef struct {
    CommandType_t cmd;
    int data;
} Command_t;

typedef struct {
    int result;
    uint32_t processing_time;
} Result_t;

// 核心0任务：网络通信
void vNetworkTask(void *pvParameters)
{
    ESP_LOGI(TAG, "Network task running on Core %d", xPortGetCoreID());
    
    Command_t cmd;
    Result_t result;
    
    while (1) {
        // 模拟接收网络命令
        cmd.cmd = CMD_READ_SENSOR;
        cmd.data = rand() % 100;
        
        // 发送到应用核心处理
        xQueueSend(xCommandQueue, &cmd, portMAX_DELAY);
        
        // 等待处理结果
        if (xQueueReceive(xResultQueue, &result, pdMS_TO_TICKS(1000))) {
            ESP_LOGI(TAG, "Received result: %d (time: %lu ms)", 
                     result.result, result.processing_time);
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

// 核心1任务：传感器处理
void vProcessingTask(void *pvParameters)
{
    ESP_LOGI(TAG, "Processing task running on Core %d", xPortGetCoreID());
    
    Command_t cmd;
    Result_t result;
    
    while (1) {
        if (xQueueReceive(xCommandQueue, &cmd, portMAX_DELAY)) {
            uint32_t startTime = xTaskGetTickCount();
            
            switch (cmd.cmd) {
                case CMD_READ_SENSOR:
                    // 模拟传感器读取和处理
                    vTaskDelay(pdMS_TO_TICKS(50));
                    result.result = cmd.data * 2;
                    break;
                    
                case CMD_PROCESS_DATA:
                    // 复杂数据处理
                    vTaskDelay(pdMS_TO_TICKS(100));
                    result.result = cmd.data + 100;
                    break;
                    
                default:
                    result.result = -1;
                    break;
            }
            
            result.processing_time = (xTaskGetTickCount() - startTime) * portTICK_PERIOD_MS;
            
            // 返回结果
            xQueueSend(xResultQueue, &result, portMAX_DELAY);
        }
    }
}

void app_main(void)
{
    // 创建队列
    xCommandQueue = xQueueCreate(10, sizeof(Command_t));
    xResultQueue = xQueueCreate(10, sizeof(Result_t));
    
    // 核心0运行网络任务
    xTaskCreatePinnedToCore(vNetworkTask, "Network", 4096, NULL, 5, NULL, CORE_PRO);
    
    // 核心1运行处理任务
    xTaskCreatePinnedToCore(vProcessingTask, "Processing", 4096, NULL, 5, NULL, CORE_APP);
    
    // 主任务可以删除或执行其他工作
    vTaskDelete(NULL);
}
```

---

## 注意事项与最佳实践

### 任务栈大小设置

| 注意点 | 说明 | 建议 |
|--------|------|------|
| **栈溢出** | 栈太小会导致HardFault | 从2048字开始，根据实际调整 |
| **栈浪费** | 栈太大浪费内存 | 使用`uxTaskGetStackHighWaterMark()`监控实际使用 |
| **中断栈** | 中断使用单独栈 | 确保`CONFIG_ESP_MAIN_TASK_STACK_SIZE`足够 |

```c
// 监控任务栈使用情况
void task_monitor(void *pvParameter) {
    while(1) {
        UBaseType_t high_water = uxTaskGetStackHighWaterMark(NULL);
        ESP_LOGI(TAG, "Stack remaining: %d words (%d bytes)", 
                 high_water, high_water * 4);
        vTaskDelay(pdMS_TO_TICKS(5000));  // 每5秒检查一次
    }
}
```

### 常见任务错误

```c
// ❌ 错误：任务函数返回（必须无限循环或自我删除）
void wrong_task(void *pv) {
    do_something();  // 执行一次就返回，导致崩溃！
}

// ✅ 正确：无限循环或自我删除
void correct_task(void *pv) {
    while(1) {
        do_something();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    // 或：vTaskDelete(NULL);  // 自我删除
}

// ❌ 错误：在中断中使用普通延时
void IRAM_ATTR isr_handler(void *arg) {
    vTaskDelay(100);  // 崩溃！中断中不能阻塞
}

// ✅ 正确：使用FreeRTOS中断安全函数
void IRAM_ATTR isr_handler(void *arg) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xQueueSendFromISR(queue, &data, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

### 任务优先级管理

| 优先级 | 用途 | 注意 |
|--------|------|------|
| 24 | 最高，系统保留 | 避免使用，留给系统中断任务 |
| 20-23 | 关键实时任务 | 慎用，可能饿死低优先级任务 |
| 10-19 | 高优先级任务 | 网络、协议栈 |
| 5-9 | 普通任务 | 业务逻辑、数据处理 |
| 1-4 | 低优先级任务 | 日志、监控 |
| 0 | 空闲任务 | 系统最低，用于看门狗喂狗 |

**优先级反转问题**：高优先级任务等待低优先级任务持有的资源时，中间优先级任务可能饿死高优先级任务。使用互斥量的优先级继承机制缓解。

### 双核编程注意事项

```c
// ❌ 错误：在核心0上执行浮点运算（Pro CPU无浮点加速）
void task_on_core0(void *pv) {
    float result = 3.14159 * 2.0;  // 慢！
}

// ✅ 正确：浮点运算绑定到核心1（App CPU有浮点加速）
xTaskCreatePinnedToCore(fp_task, "fp_task", 2048, NULL, 5, NULL, 1);
```

| 核心 | 特点 | 建议用途 |
|------|------|----------|
| **核心0 (Pro)** | 处理WiFi/BT协议栈 | 协议相关任务 |
| **核心1 (App)** | 浮点加速，用户应用 | 业务逻辑、浮点计算 |

### 内存管理

```c
// ❌ 错误：在中断中使用malloc
void IRAM_ATTR isr(void *arg) {
    char *buf = malloc(100);  // 可能导致死锁！
}

// ✅ 正确：使用静态内存或预先分配
static char isr_buf[100];  // 静态分配
void IRAM_ATTR isr(void *arg) {
    // 使用isr_buf
}
```

### 调试技巧

```c
// 获取任务状态
void print_task_info(void) {
    char pcWriteBuffer[512];
    vTaskList(pcWriteBuffer);
    ESP_LOGI(TAG, "\n%s", pcWriteBuffer);
}

// 获取运行时统计
void print_runtime_stats(void) {
    char pcWriteBuffer[512];
    vTaskGetRunTimeStats(pcWriteBuffer);
    ESP_LOGI(TAG, "\n%s", pcWriteBuffer);
}
```

需要在`menuconfig`中启用：`Component config → FreeRTOS → Enable FreeRTOS stats formatting functions`

---

## 附录：任务管理API速查表

### 任务创建与删除

| API | 说明 |
|-----|------|
| `xTaskCreate()` | 创建任务（分配到任意核心） |
| `xTaskCreatePinnedToCore()` | 创建任务并绑定到指定核心 |
| `vTaskDelete()` | 删除任务 |
| `vTaskDelay()` | 任务延时（相对时间） |
| `vTaskDelayUntil()` | 任务延时（绝对时间，周期任务） |

### 任务状态与控制

| API | 说明 |
|-----|------|
| `vTaskSuspend()` | 挂起任务 |
| `vTaskResume()` | 恢复任务 |
| `vTaskPrioritySet()` | 设置任务优先级 |
| `uxTaskPriorityGet()` | 获取任务优先级 |
| `eTaskGetState()` | 获取任务状态 |
| `uxTaskGetStackHighWaterMark()` | 获取任务栈剩余空间 |

### 队列操作

| API | 说明 |
|-----|------|
| `xQueueCreate()` | 创建队列 |
| `xQueueSend()` | 发送到队列 |
| `xQueueReceive()` | 从队列接收 |
| `xQueuePeek()` | 查看队列（不移除） |
| `uxQueueMessagesWaiting()` | 获取队列消息数 |
| `vQueueDelete()` | 删除队列 |

### 信号量操作

| API | 说明 |
|-----|------|
| `xSemaphoreCreateBinary()` | 创建二值信号量 |
| `xSemaphoreCreateCounting()` | 创建计数信号量 |
| `xSemaphoreCreateMutex()` | 创建互斥锁 |
| `xSemaphoreGive()` | 释放信号量 |
| `xSemaphoreTake()` | 获取信号量 |
| `vSemaphoreDelete()` | 删除信号量 |
