# FreeRTOS 深入与实战

> **定位**：FreeRTOS 内核原理、API 深入分析与工程实战笔记。
> **适用版本**：FreeRTOS V10.x / V11.x，ESP-IDF 集成版本。
> **前置知识**：C 语言、基本操作系统概念、嵌入式开发基础。

---

## 一、FreeRTOS 内核架构

### 1.1 整体架构概览

FreeRTOS 是一个**可裁剪、可抢占、基于优先级**的实时操作系统内核。核心组件包括：

| 组件 | 职责 |
|------|------|
| 任务调度器 (Scheduler) | 决定哪个任务获得 CPU 使用权 |
| 时间管理 (Tick) | 系统时基，驱动延时与时间片轮转 |
| 任务管理 (Task) | 任务创建、删除、挂起、恢复 |
| 队列 (Queue) | 任务间通信的核心机制 |
| 信号量/互斥量 | 同步与互斥 |
| 软件定时器 | 基于 Tick 的软件定时 |
| 内存管理 | 堆内存分配策略 |
| 事件标志组 | 多条件同步 |

### 1.2 调度器类型

FreeRTOS 支持三种调度策略：

```c
/* 在 FreeRTOSConfig.h 中配置 */

/* 1. 抢占式调度（默认，推荐）*/
#define configUSE_PREEMPTION    1

/* 2. 时间片轮转（同优先级任务轮转）*/
#define configUSE_TIME_SLICING  1

/* 3. 协作式调度（只有主动让出才切换）*/
#define configUSE_PREEMPTION    0
```

**抢占式调度**：高优先级任务就绪时立即抢占低优先级任务，实时性最好。
**时间片轮转**：同优先级任务按 Tick 为单位轮流执行，每个任务运行一个 Tick。
**协作式调度**：任务必须显式调用 `taskYIELD()` 或阻塞才会切换，实时性最差。

### 1.3 Tick 中断原理

Tick 中断是 FreeRTOS 的"心跳"，由硬件定时器周期性触发。

```
时间轴：
|--Tick--|--Tick--|--Tick--|--Tick--|--Tick--|
    |        |        |        |
    v        v        v        v
  TickISR  TickISR  TickISR  TickISR
```

**Tick 中断处理流程**：

1. 保存当前任务上下文（硬件自动压栈部分寄存器）
2. 调用 `xTaskIncrementTick()`
   - 递增 Tick 计数器 `xTickCount`
   - 检查延时列表，唤醒到期任务
   - 检查时间片是否用完，触发上下文切换
3. 若需切换，调用 `vTaskSwitchContext()` 选择最高优先级就绪任务
4. 恢复目标任务上下文（硬件自动出栈）

**关键配置**：

```c
/* Tick 频率，通常 100~1000 Hz */
#define configTICK_RATE_HZ          1000

/* 最低中断优先级（STM32 通常为 15）*/
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY         15

/* 可调用 FreeRTOS API 的最高中断优先级 */
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY    5

/* 实际写入寄存器的值（左移 4 位）*/
#define configKERNEL_INTERRUPT_PRIORITY     ( configLIBRARY_LOWEST_INTERRUPT_PRIORITY << 4 )
#define configMAX_SYSCALL_INTERRUPT_PRIORITY ( configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << 4 )
```

### 1.4 上下文切换原理

上下文切换是调度器的核心操作，分为**主动切换**和**被动切换**：

**主动切换**（任务调用 `taskYIELD()` 或阻塞 API）：
```
PendSV 异常触发 → PendSV_Handler → vPortPendSVHandler
  1. 关中断
  2. 保存 R4-R11 到当前任务栈
  3. 更新当前任务 TCB 的 pxTopOfStack
  4. 调用 vTaskSwitchContext() 选择新任务
  5. 从新任务 TCB 的 pxTopOfStack 恢复 R4-R11
  6. 开中断，返回
```

**被动切换**（Tick 中断中发现更高优先级任务就绪）：
```
Tick ISR → SysTick_Handler → xPortSysTickHandler
  → xTaskIncrementTick() → vTaskSwitchContext()
  → 触发 PendSV（延迟切换，不在 ISR 内直接切换）
```

> **关键设计**：PendSV 的中断优先级被设置为最低（0xFF），确保它在所有 ISR 执行完毕后才触发，避免在中断内做复杂的上下文切换。

**ARM Cortex-M 上下文切换的关键寄存器**：

| 寄存器 | 说明 |
|--------|------|
| PSP | 进程栈指针，每个任务独立栈 |
| MSP | 主栈指针，ISR 使用 |
| LR | 链接寄存器，保存返回地址 |
| xPSR | 状态寄存器 |
| R4-R11 | 软件保存的通用寄存器 |
| R0-R3, R12, LR, PC, xPSR | 硬件自动压栈 |

---

## 二、任务管理深入

### 2.1 任务状态机

FreeRTOS 任务有四种基本状态：

```
                    ┌──────────────────────────────────┐
                    │                                  │
                    v                                  │
    ┌──────────┐  创建   ┌──────────┐  运行完成/删除  ┌──────────┐
    │          │ ------→ │  Ready   │ ←──────┐       │  Running │
    │ 不存在   │         │ (就绪态) │        │       │ (运行态) │
    │          │ ←────── │          │ ───────┘       └────┬─────┘
    └──────────┘  删除   └────┬─────┘  同优先级时间片用完 │
                    │         │                           │
                    │    等待事件 │  事件到达/超时        │ 等待事件
                    │         │                           │
                    │         v                           v
                    │   ┌───────────────────────────────────┐
                    │   │         Blocked (阻塞态)          │
                    └───│  等待队列/信号量/延时/事件        │
                        └───────────────────────────────────┘
                                        │
                                   suspend│
                                        v
                               ┌──────────────┐
                               │ Suspended    │
                               │ (挂起态)     │
                               └──────────────┘
```

**状态转换触发条件**：

| 转换 | 触发 API |
|------|----------|
| 不存在 → 就绪 | `xTaskCreate()` / `xTaskCreateStatic()` |
| 就绪 → 运行 | 调度器选择该任务 |
| 运行 → 就绪 | 时间片用完 / 更高优先级任务就绪 |
| 运行 → 阻塞 | `vTaskDelay()` / `xQueueReceive()` / `xSemaphoreTake()` 等带超时的 API |
| 阻塞 → 就绪 | 等待的事件到达 / 超时到期 |
| 任意 → 挂起 | `vTaskSuspend()` |
| 挂起 → 就绪 | `vTaskResume()` / `xTaskResumeFromISR()` |
| 任意 → 不存在 | `vTaskDelete()` |

### 2.2 优先级继承

当高优先级任务等待低优先级任务持有的资源时，会出现**优先级反转**问题。优先级继承是 FreeRTOS 互斥量的解决方案。

**经典优先级反转场景**：

```
任务优先级：H(高) > M(中) > L(低)

时间线：
L 获取 Mutex → M 就绪并抢占 L → H 就绪但 Mutex 被 L 持有
→ H 阻塞等待 Mutex → M 持续运行 → H 被 M 间接阻塞！

结果：H 的实际执行延迟取决于 M 的执行时间，这是不可接受的。
```

**优先级继承解决方案**：

```
L 获取 Mutex → H 就绪但 Mutex 被 L 持有
→ L 的优先级临时提升到 H 的级别 → L 继续运行
→ L 释放 Mutex → L 恢复原优先级 → H 获取 Mutex 并运行

结果：H 只被 L 的临界区阻塞，不受 M 影响。
```

> **注意**：优先级继承只用在 `xSemaphoreCreateMutex()` 创建的互斥量上。二值信号量不支持优先级继承。

### 2.3 任务通知替代信号量

FreeRTOS V10.0+ 引入任务通知（Task Notifications），可替代部分信号量和事件标志的用法，且速度更快、内存更省。

**任务通知 vs 队列/信号量对比**：

| 特性 | 队列/信号量 | 任务通知 |
|------|------------|---------|
| 速度 | 较慢（需操作队列结构） | 快 2-3 倍（直接操作 TCB） |
| 内存 | 需要额外分配 | 无需额外内存（用 TCB 内部字段） |
| 多对一 | 支持多个发送者 | 仅支持一个接收者 |
| 带数据 | 队列可以带数据 | 可以携带 32 位值 |
| 累加 | 计数信号量可累加 | 通知值可累加 |

**任务通知 API**：

```c
/* 发送通知（替代二值信号量）*/
BaseType_t xTaskNotifyGive(TaskHandle_t xTaskToNotify);

/* 接收通知（阻塞等待）*/
uint32_t ulTaskNotifyTake(BaseType_t xClearCountOnExit,
                          TickType_t xTicksToWait);
/*
 * xClearCountOnExit = pdTRUE  → 模拟二值信号量（取后清零）
 * xClearCountOnExit = pdFALSE → 模拟计数信号量（取后减1）
 */

/* 更通用的通知 API */
BaseType_t xTaskNotify(TaskHandle_t xTaskToNotify,
                       uint32_t ulValue,
                       eNotifyAction eAction);
BaseType_t xTaskNotifyWait(uint32_t ulBitsToClearOnEntry,
                           uint32_t ulBitsToClearOnExit,
                           uint32_t *pulNotificationValue,
                           TickType_t xTicksToWait);
```

**eNotifyAction 枚举值**：

| 值 | 行为 |
|----|------|
| `eNoAction` | 仅更新通知状态，不改值 |
| `eSetBits` | 按位或（类似事件标志组） |
| `eIncrement` | 通知值加 1（类似计数信号量） |
| `eSetValueWithOverwrite` | 覆盖写入值 |
| `eSetValueWithoutOverwrite` | 不覆盖，若已有未处理通知则失败 |

**使用示例 —— ISR 通知任务**：

```c
/* 任务侧 */
void vSensorTask(void *pvParameters)
{
    uint32_t ulNotificationValue;
    for (;;)
    {
        /* 等待 ISR 发送的通知 */
        xTaskNotifyWait(0x00, 0xFFFFFFFF, &ulNotificationValue, portMAX_DELAY);
        /* 处理传感器数据 */
        process_sensor_data(ulNotificationValue);
    }
}

/* ISR 侧 */
void ADC_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    uint32_t adc_value = ADC->DR;

    xTaskNotifyFromISR(xSensorTaskHandle, adc_value,
                       eSetValueWithOverwrite, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

### 2.4 协程 (Co-routines)

> **注意**：协程已在 FreeRTOS V10.4.1+ 中被标记为 deprecated，不建议在新项目中使用。此处仅作知识了解。

协程是 FreeRTOS 早期提供的轻量级并发机制，所有协程共享同一个栈。

```c
/* 协程函数原型 */
static void vCoRoutineFunction(CoRoutineHandle_t xHandle, UBaseType_t uxIndex);

/* 创建协程 */
xCoRoutineCreate(vCoRoutineFunction, priority, index);

/* 协程内部使用 crDELAY 代替 vTaskDelay */
crDELAY(xHandle, ticks);
```

**协程的局限**：
- 所有协程共享栈，无法使用局部变量（需用 static）
- 不支持优先级继承
- 与任务混合使用时需注意调度顺序
- 已被任务通知等新特性取代

---

## 三、队列深入

### 3.1 队列创建与操作

队列是 FreeRTOS 任务间通信的**核心机制**，信号量和互斥量内部都基于队列实现。

**创建队列**：

```c
/* 动态创建 */
QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength, UBaseType_t uxItemSize);

/* 静态创建 */
QueueHandle_t xQueueCreateStatic(UBaseType_t uxQueueLength,
                                  UBaseType_t uxItemSize,
                                  uint8_t *pucQueueStorageBuffer,
                                  StaticQueue_t *pxQueueBuffer);

/* 示例：创建一个可容纳 10 个 int 的队列 */
QueueHandle_t xDataQueue = xQueueCreate(10, sizeof(int));
```

**队列内部结构**：

```c
/* 简化版队列结构 */
typedef struct QueueDefinition {
    int8_t *pcHead;            /* 队列存储区头指针 */
    int8_t *pcTail;            /* 队列存储区尾指针 */
    int8_t *pcWriteTo;         /* 下一个写入位置 */
    int8_t *pcReadFrom;        /* 下一个读取位置 */
    List_t xTasksWaitingToSend;    /* 发送等待列表 */
    List_t xTasksWaitingToReceive; /* 接收等待列表 */
    volatile UBaseType_t uxMessagesWaiting; /* 当前消息数 */
    UBaseType_t uxLength;      /* 队列长度 */
    UBaseType_t uxItemSize;    /* 单个元素大小 */
    /* ... */
} xQUEUE;
```

**发送操作**：

```c
/* 任务中发送（阻塞） */
BaseType_t xQueueSend(QueueHandle_t xQueue,
                      const void *pvItemToQueue,
                      TickType_t xTicksToWait);

/* 等同于 xQueueSend */
BaseType_t xQueueSendToBack(QueueHandle_t xQueue,
                             const void *pvItemToQueue,
                             TickType_t xTicksToWait);

/* 发送到队首（LIFO） */
BaseType_t xQueueSendToFront(QueueHandle_t xQueue,
                              const void *pvItemToQueue,
                              TickType_t xTicksToWait);

/* ISR 中发送 */
BaseType_t xQueueSendFromISR(QueueHandle_t xQueue,
                              const void *pvItemToQueue,
                              BaseType_t *pxHigherPriorityTaskWoken);
```

**接收操作**：

```c
/* 任务中接收（阻塞） */
BaseType_t xQueueReceive(QueueHandle_t xQueue,
                         void *pvBuffer,
                         TickType_t xTicksToWait);

/* 窥视（不移除） */
BaseType_t xQueuePeek(QueueHandle_t xQueue,
                      void *pvBuffer,
                      TickType_t xTicksToWait);

/* ISR 中接收 */
BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue,
                                 void *pvBuffer,
                                 BaseType_t *pxHigherPriorityTaskWoken);
```

**队列操作的内部流程（发送为例）**：

```
xQueueSend( queue, data, timeout )
    │
    ├─ 队列未满？
    │   ├─ YES → 拷贝数据到队列 → 有任务在等待接收？
    │   │         ├─ YES → 唤醒等待中优先级最高的任务
    │   │         └─ NO  → 返回 pdPASS
    │   └─ NO  → 超时 == 0？
    │             ├─ YES → 返回 errQUEUE_FULL
    │             └─ NO  → 将当前任务挂入 xTasksWaitingToSend
    │                       → 触发上下文切换 → 超时后返回 errQUEUE_FULL
```

### 3.2 队列集 (Queue Sets)

队列集允许任务同时等待多个队列/信号量，任意一个有数据就唤醒。

```c
/* 创建队列集（能容纳 5 个队列/信号量的事件）*/
QueueSetHandle_t xQueueCreateSet(UBaseType_t uxEventQueueLength);

/* 将队列加入集合 */
xQueueAddToSet(xQueue, xQueueSet);
xQueueAddToSet(xSemaphore, xQueueSet);

/* 等待集合中任意成员有事件 */
QueueSetMemberHandle_t xQueueSelectFromSet(QueueSetHandle_t xQueueSet,
                                            TickType_t xTicksToWait);

/* 示例 */
void vProcessTask(void *pvParameters)
{
    QueueSetMemberHandle_t xActivatedMember;
    for (;;)
    {
        xActivatedMember = xQueueSelectFromSet(xMyQueueSet, portMAX_DELAY);
        if (xActivatedMember == xUartQueue)
        {
            /* UART 数据到达 */
        }
        else if (xActivatedMember == xTimerSemaphore)
        {
            /* 定时器信号量 */
        }
    }
}
```

### 3.3 互斥量的队列实现原理

互斥量在 FreeRTOS 内部就是一个特殊的队列，长度为 1，不存储实际数据，只利用队列的"满/空"状态来表示"锁定/未锁定"。

```
互斥量内部基于 Queue 实现：
┌─────────────────────────────┐
│ uxMessagesWaiting: 0 或 1   │  ← 0: 已锁定, 1: 未锁定
│ xMutexHolder: 任务句柄      │  ← 记录持有者（用于优先级继承）
│ uxQueueType: queueQUEUE_IS_MUTEX │
│ xTasksWaitingToSend         │  ← 等待获取的任务列表
└─────────────────────────────┘

获取互斥量 ≈ xQueueReceive（取走一个元素 → 0 → 锁定）
释放互斥量 ≈ xQueueSend（放回一个元素 → 1 → 解锁）
```

### 3.4 递归互斥量

递归互斥量允许同一个任务多次获取同一个互斥量而不会死锁。

```c
/* 创建递归互斥量 */
SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(void);

/* 获取（可重入） */
BaseType_t xSemaphoreTakeRecursive(SemaphoreHandle_t xMutex,
                                    TickType_t xTicksToWait);
/* 每次 Take 会使内部计数器 +1 */

/* 释放 */
BaseType_t xSemaphoreGiveRecursive(SemaphoreHandle_t xMutex);
/* 每次 Give 使计数器 -1，计数器归零时真正释放 */

/* 正确用法 */
void vTaskFunction(void *pvParameters)
{
    xSemaphoreTakeRecursive(xRecursiveMutex, portMAX_DELAY);
    {
        /* 临界区 1 */
        xSemaphoreTakeRecursive(xRecursiveMutex, portMAX_DELAY);
        {
            /* 临界区 2 —— 可以重入 */
        }
        xSemaphoreGiveRecursive(xRecursiveMutex);
    }
    xSemaphoreGiveRecursive(xRecursiveMutex);  /* 真正释放 */
}
```

---

## 四、信号量与互斥量

### 4.1 三种信号量/互斥量对比

| 特性 | 二值信号量 | 计数信号量 | 互斥量 |
|------|-----------|-----------|--------|
| 计数范围 | 0 或 1 | 0 ~ N | 0 或 1 |
| 用途 | 同步（通知） | 资源计数 | 互斥（保护共享资源） |
| 优先级继承 | 不支持 | 不支持 | **支持** |
| 递归获取 | 不支持 | 不支持 | 递归互斥量支持 |
| ISR 中获取 | 不建议 | 不建议 | **禁止** |
| ISR 中释放 | 支持 (FromISR) | 支持 (FromISR) | 不建议 |

**创建 API**：

```c
/* 二值信号量 */
SemaphoreHandle_t xSemaphoreCreateBinary(void);
/* 初始状态：空（需要先 Give 才能 Take）*/

SemaphoreHandle_t xSemaphoreCreateBinaryStatic(StaticSemaphore_t *pxSemaphoreBuffer);

/* 计数信号量 */
SemaphoreHandle_t xSemaphoreCreateCounting(UBaseType_t uxMaxCount,
                                            UBaseType_t uxInitialCount);

/* 互斥量 */
SemaphoreHandle_t xSemaphoreCreateMutex(void);
SemaphoreHandle_t xSemaphoreCreateMutexStatic(StaticSemaphore_t *pxMutexBuffer);

/* 递归互斥量 */
SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(void);
```

### 4.2 优先级反转问题详解

**Mars Pathfinder 案例**（1997年火星探路者号）：

```
任务优先级：气象数据(高) > 通信(中) > 总线管理(低)

执行过程：
1. 总线管理获取互斥量，访问共享总线
2. 气象数据就绪，抢占总线管理
3. 气象数据需要访问总线，但互斥量被总线管理持有
4. 气象数据阻塞等待
5. 通信任务就绪，抢占总线管理（因为通信优先级高于总线管理的原始优先级）
6. 气象数据被通信任务间接阻塞 → 看门狗超时 → 系统复位

解决方案：优先级继承
```

### 4.3 优先级继承协议

FreeRTOS 的优先级继承实现细节：

```c
/* 互斥量内部结构（包含持有者信息）*/
typedef struct QueueDefinition {
    /* ... */
    TaskHandle_t xMutexHolder;      /* 持有互斥量的任务 */
    UBaseType_t uxQueueType;        /* 标识为互斥量 */
} xQUEUE;

/* xSemaphoreTake 内部逻辑（互斥量版本）*/
if (互斥量已被持有)
{
    if (当前任务优先级 > 持有者优先级)
    {
        /* 优先级继承：临时提升持有者优先级 */
        vTaskPrioritySet(xMutexHolder, 当前任务优先级);
    }
    /* 将当前任务挂入等待列表 */
}
```

### 4.4 信号量使用最佳实践

```c
/* 二值信号量：ISR → 任务同步 */
SemaphoreHandle_t xAdcReadySemaphore;

void vInit(void)
{
    xAdcReadySemaphore = xSemaphoreCreateBinary();
}

void vAdcTask(void *pvParameters)
{
    for (;;)
    {
        xSemaphoreTake(xAdcReadySemaphore, portMAX_DELAY);
        /* ADC 转换完成，处理数据 */
        uint16_t value = ADC1->DR;
    }
}

void ADC1_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(xAdcReadySemaphore, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

/* 计数信号量：生产者-消费者模型 */
SemaphoreHandle_t xItemAvailable;

void vInit(void)
{
    /* 最多缓存 10 个，初始 0 个 */
    xItemAvailable = xSemaphoreCreateCounting(10, 0);
}

void vProducer(void *pvParameters)
{
    for (;;)
    {
        produce_item();
        xSemaphoreGive(xItemAvailable);  /* 计数 +1 */
    }
}

void vConsumer(void *pvParameters)
{
    for (;;)
    {
        xSemaphoreTake(xItemAvailable, portMAX_DELAY); /* 计数 -1 */
        consume_item();
    }
}
```

---

## 五、内存管理

### 5.1 五种堆内存方案对比

FreeRTOS 提供 5 种 heap 方案，位于 `portable/MemMang/` 目录。

| 方案 | 文件 | 特点 | 适用场景 |
|------|------|------|---------|
| heap_1 | heap_1.c | 只分配不释放，最简单 | 不会删除任务的系统 |
| heap_2 | heap_2.c | 支持释放，但不合并相邻空闲块 | 不会产生碎片的场景 |
| heap_3 | heap_3.c | 包装标准 malloc/free | 不受 FreeRTOS 管理的堆 |
| heap_4 | heap_4.c | 支持释放，合并相邻空闲块 | **最常用**，通用场景 |
| heap_5 | heap_5.c | 同 heap_4，但支持多段不连续内存 | 内存映射复杂的 MCU |

**heap_1 详解**：

```c
/* heap_1：最简单的分配方案
 * - 只分配，不释放
 * - 没有碎片问题
 * - 分配速度极快（移动指针即可）
 * - 适用于创建后永不删除的系统
 */
void *pvPortMalloc(size_t xWantedSize)
{
    static uint8_t *pucAlignedHeap = NULL;
    void *pvReturn = NULL;

    /* 对齐到 portBYTE_ALIGNMENT */
    xWantedSize = (xWantedSize + (portBYTE_ALIGNMENT - 1)) &
                  ~((size_t)portBYTE_ALIGNMENT - 1);

    if ((pucHeap + xNextFreeByte + xWantedSize) <= pucHeapEnd)
    {
        pvReturn = pucHeap + xNextFreeByte;
        xNextFreeByte += xWantedSize;
    }
    return pvReturn;
}
```

**heap_4 详解**（最常用）：

```c
/* heap_4：带合并的分配方案
 * - 使用 first-fit 算法
 * - 释放时合并相邻空闲块
 * - 可能仍有碎片，但比 heap_2 好得多
 */

/* 内部使用 BlockLink_t 链表管理空闲块 */
typedef struct A_BLOCK_LINK {
    struct A_BLOCK_LINK *pxNextFreeBlock; /* 下一个空闲块 */
    size_t xBlockSize;                    /* 当前块大小（含头部）*/
} BlockLink_t;

/* 空闲块链表：
 * ┌──────────┐    ┌──────────┐    ┌──────────┐
 * │ Block 1  │ → │ Block 2  │ → │ Block 3  │ → NULL
 * │ size: 64 │    │ size: 128│    │ size: 256│
 * └──────────┘    └──────────┘    └──────────┘
 */

/* 释放时合并示例：
 * 释放 Block 2，发现 Block 1 和 Block 3 也空闲
 * ┌──────────┐    ┌──────────┐    ┌──────────┐
 * │ Block 1  │ → │ Block 2  │ → │ Block 3  │
 * │ Free     │    │ Free     │    │ Free     │
 * └──────────┘    └──────────┘    └──────────┘
 *         ↓ 合并为一个大块 ↓
 * ┌──────────────────────────────────────────────┐
 * │         Block 1 (size: 64+128+256)           │
 * │                  Free                        │
 * └──────────────────────────────────────────────┘
 */
```

### 5.2 内存碎片

**碎片类型**：

```
外部碎片（External Fragmentation）：
分配前：[====空闲 4KB====]
分配后：[A=1KB][空闲][B=1KB][空闲 2KB]
释放 A、B 后：[空闲 1KB][空闲][空闲 1KB][空闲 2KB]
→ 有 4KB 空闲，但无法分配 3KB 的连续块！

内部碎片（Internal Fragmentation）：
请求 33 字节，分配 40 字节（对齐到 8 字节）
→ 7 字节被浪费
```

**减少碎片的策略**：

```c
/* 1. 优先使用静态内存分配 */
StaticTask_t xTaskBuffer;
StackType_t xStack[TASK_STACK_SIZE];
xTaskCreateStatic(vTaskFunc, "Task", TASK_STACK_SIZE, NULL,
                  tskIDLE_PRIORITY, xStack, &xTaskBuffer);

/* 2. 避免频繁创建/删除任务 */
/* 好的做法：创建后长期运行，用挂起/恢复代替删除/重建 */

/* 3. 使用固定大小内存池（自定义）*/
/* 4. 定期监控 heap 使用情况 */
size_t xFreeHeapSize = xPortGetFreeHeapSize();
size_t xMinEverFreeHeapSize = xPortGetMinimumEverFreeHeapSize();
```

### 5.3 自定义内存管理

可以通过覆盖 `pvPortMalloc` 和 `vPortFree` 实现自定义内存管理：

```c
/* 方案 1：使用 configAPPLICATION_ALLOCATED_HEAP */
#define configTOTAL_HEAP_SIZE        ((size_t)(32 * 1024))
#define configAPPLICATION_ALLOCATED_HEAP  1

/* 在某个 .c 文件中 */
uint8_t ucHeap[configTOTAL_HEAP_SIZE];

/* 方案 2：使用 malloc/free 包装（heap_3 方案）*/
/* 直接在 FreeRTOSConfig.h 中选择 heap_3 即可 */

/* 方案 3：完全自定义 */
void *pvPortMalloc(size_t xWantedSize)
{
    /* 自定义分配逻辑 */
    void *pvReturn = my_custom_alloc(xWantedSize);
    configASSERT(pvReturn != NULL);
    return pvReturn;
}

void vPortFree(void *pv)
{
    my_custom_free(pv);
}
```

**监控堆使用**：

```c
/* 获取当前空闲堆大小 */
size_t xPortGetFreeHeapSize(void);

/* 获取历史最小空闲堆大小（水位线）*/
size_t xPortGetMinimumEverFreeHeapSize(void);

/* 示例：检测内存泄漏 */
void vCheckHeapLeak(void)
{
    static size_t xPrevFreeHeap = 0;
    size_t xCurrentFreeHeap = xPortGetFreeHeapSize();

    if (xPrevFreeHeap != 0 && xCurrentFreeHeap < xPrevFreeHeap)
    {
        printf("Warning: heap decreased by %d bytes\n",
               xPrevFreeHeap - xCurrentFreeHeap);
    }
    xPrevFreeHeap = xCurrentFreeHeap;
}
```

---

## 六、软件定时器

### 6.1 定时器基础

软件定时器由 FreeRTOS 的定时器守护任务（Timer Service Task）管理，不依赖硬件定时器。

**配置**：

```c
/* FreeRTOSConfig.h */
#define configUSE_TIMERS                1
#define configTIMER_TASK_PRIORITY       (configMAX_PRIORITIES - 1)
#define configTIMER_QUEUE_LENGTH        10
#define configTIMER_TASK_STACK_DEPTH    (configMINIMAL_STACK_SIZE * 2)
```

**创建与操作**：

```c
/* 创建定时器 */
TimerHandle_t xTimerCreate(const char *pcTimerName,
                           const TickType_t xTimerPeriodInTicks,
                           UBaseType_t uxAutoReload,
                           void *pvTimerID,
                           TimerCallbackFunction_t pxCallbackFunction);

/* 参数说明：
 * pcTimerName        - 定时器名称（调试用）
 * xTimerPeriodInTicks - 定时周期（Tick 数）
 * uxAutoReload       - pdTRUE: 自动重载（周期定时器）
 *                      pdFALSE: 单次定时器
 * pvTimerID          - 定时器 ID（可在回调中区分多个定时器）
 * pxCallbackFunction - 超时回调函数
 */

/* 启动定时器 */
BaseType_t xTimerStart(TimerHandle_t xTimer, TickType_t xTicksToWait);
BaseType_t xTimerStartFromISR(TimerHandle_t xTimer,
                               BaseType_t *pxHigherPriorityTaskWoken);

/* 停止定时器 */
BaseType_t xTimerStop(TimerHandle_t xTimer, TickType_t xTicksToWait);

/* 重置定时器 */
BaseType_t xTimerReset(TimerHandle_t xTimer, TickType_t xTicksToWait);

/* 更改周期 */
BaseType_t xTimerChangePeriod(TimerHandle_t xTimer,
                               TickType_t xNewPeriod,
                               TickType_t xTicksToWait);

/* 获取定时器 ID */
void *pvTimerGetTimerID(TimerHandle_t xTimer);
```

### 6.2 定时器守护任务

软件定时器的执行原理：

```
应用代码                    守护任务                    Tick 中断
    |                          |                          |
 xTimerStart()                |                          |
    │                         |                          |
    ├── 命令入队 ──→ 定时器命令队列                       |
    │                    取出命令                         |
    │                    启动定时器                        |
    │                    设置到期时间 ──────────────────→ |
    │                         |              Tick 递增    |
    │                         |              到期!       |
    │                         | ←── 通知守护任务 ──────── |
    │                    执行回调函数                     |
    │                    (如果 autoReload → 重新设置)    |
```

### 6.3 回调函数注意事项

```c
/* 定时器回调函数原型 */
void vTimerCallback(TimerHandle_t xTimer);

/* 重要规则：
 * 1. 回调函数必须快速返回，不能阻塞！
 * 2. 回调函数运行在守护任务的上下文中
 * 3. 回调函数中不能调用会导致阻塞的 API
 */

/* 错误示例 */
void vBadCallback(TimerHandle_t xTimer)
{
    /* 不要在回调中做这些！*/
    vTaskDelay(100);                    /* 阻塞！*/
    xSemaphoreTake(xMutex, portMAX_DELAY); /* 可能阻塞！*/
    xQueueSend(xQueue, &data, portMAX_DELAY); /* 可能阻塞！*/
}

/* 正确示例 */
void vGoodCallback(TimerHandle_t xTimer)
{
    /* 快速操作：设置标志、发送非阻塞队列 */
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    /* 使用带 0 超时的 API，确保不阻塞 */
    xQueueSendFromISR(xQueue, &data, &xHigherPriorityTaskWoken);

    /* 或者只设置一个标志 */
    xEventGroupSetBitsFromISR(xEventGroup, BIT_0, &xHigherPriorityTaskWoken);
}
```

### 6.4 软件定时器 vs 硬件定时器

| 特性 | 软件定时器 | 硬件定时器 |
|------|-----------|-----------|
| 精度 | 受 Tick 频率限制 | 硬件级精度 |
| 最小周期 | 通常 1ms (1kHz Tick) | 可达 ns 级 |
| 回调上下文 | 守护任务（可调用 FreeRTOS API） | ISR（受限 API） |
| 数量 | 无限制（受内存限制） | 受硬件定时器数量限制 |
| 阻塞 | 回调中不能阻塞 | ISR 中不能阻塞 |
| 适用场景 | 非精确计时、周期性任务 | 精确计时、PWM、输入捕获 |

---

## 七、事件标志组

### 7.1 事件标志组基础

事件标志组允许任务等待**多个事件的组合**（与/或逻辑）。

```c
/* 创建事件组 */
EventGroupHandle_t xEventGroupCreate(void);
EventGroupHandle_t xEventGroupCreateStatic(StaticEventGroup_t *pxEventGroupBuffer);

/* 设置事件标志 */
EventBits_t xEventGroupSetBits(EventGroupHandle_t xEventGroup,
                                const EventBits_t uxBitsToSet);

/* ISR 中设置 */
BaseType_t xEventGroupSetBitsFromISR(EventGroupHandle_t xEventGroup,
                                      const EventBits_t uxBitsToSet,
                                      BaseType_t *pxHigherPriorityTaskWoken);

/* 清除事件标志 */
EventBits_t xEventGroupClearBits(EventGroupHandle_t xEventGroup,
                                  const EventBits_t uxBitsToClear);
```

### 7.2 xEventGroupWaitBits 详解

```c
EventBits_t xEventGroupWaitBits(EventGroupHandle_t xEventGroup,
                                 const EventBits_t uxBitsToWaitFor,
                                 const BaseType_t xClearOnExit,
                                 const BaseType_t xWaitForAllBits,
                                 TickType_t xTicksToWait);

/* 参数说明：
 * uxBitsToWaitFor - 要等待的位（可按位或组合）
 * xClearOnExit    - pdTRUE: 满足条件后自动清除这些位
 *                   pdFALSE: 不清除
 * xWaitForAllBits - pdTRUE: 等待所有指定位都置位（AND）
 *                   pdFALSE: 等待任意一位置位（OR）
 * xTicksToWait    - 超时时间
 */

/* 返回值：返回满足条件时的事件标志状态 */
```

**使用示例**：

```c
/* 定义事件位 */
#define BIT_SENSOR_READY    (1 << 0)
#define BIT_KEY_PRESSED     (1 << 1)
#define BIT_NETWORK_OK      (1 << 2)
#define BIT_ALL_READY       (BIT_SENSOR_READY | BIT_KEY_PRESSED | BIT_NETWORK_OK)

EventGroupHandle_t xSystemEvents;

void vInitTask(void *pvParameters)
{
    xSystemEvents = xEventGroupCreate();

    /* 等待所有子系统就绪 */
    EventBits_t uxBits = xEventGroupWaitBits(
        xSystemEvents,
        BIT_ALL_READY,
        pdTRUE,         /* 满足后清除 */
        pdTRUE,         /* 等待全部（AND）*/
        pdMS_TO_TICKS(5000)
    );

    if ((uxBits & BIT_ALL_READY) == BIT_ALL_READY)
    {
        printf("All subsystems ready\n");
    }
    else
    {
        printf("Timeout! uxBits = 0x%02X\n", uxBits);
    }
}

/* 传感器任务 */
void vSensorTask(void *pvParameters)
{
    /* 初始化传感器 */
    sensor_init();
    xEventGroupSetBits(xSystemEvents, BIT_SENSOR_READY);
    /* ... */
}

/* 按键任务 */
void vKeyTask(void *pvParameters)
{
    /* 等待按键 */
    wait_for_key_press();
    xEventGroupSetBits(xSystemEvents, BIT_KEY_PRESSED);
    /* ... */
}

/* 网络任务 */
void vNetworkTask(void *pvParameters)
{
    /* 等待网络连接 */
    while (!network_connected())
    {
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    xEventGroupSetBits(xSystemEvents, BIT_NETWORK_OK);
    /* ... */
}
```

### 7.3 事件标志组的限制

- 事件标志组最多 **24 个有效位**（在 32 位系统中，高 8 位被 FreeRTOS 内部使用）
- 设置和清除不是原子的多步操作，但 xEventGroupWaitBits 是原子检查
- 事件标志组不会"累加"，多次设置同一位等于设置一次
- ISR 中设置标志可能触发守护任务，延迟一个 Tick 才生效

---

## 八、中断管理

### 8.1 中断安全 API（FromISR 后缀）

FreeRTOS 要求在中断服务程序（ISR）中使用专门的 API，这些 API 带有 `FromISR` 后缀。

**为什么需要 FromISR API**：

```
普通 API 的问题：
- 可能触发上下文切换（ISR 中不能直接切换）
- 可能导致阻塞（ISR 中不能阻塞）
- 可能访问非 ISR 安全的数据结构

FromISR API 的特点：
- 不会阻塞
- 通过 pxHigherPriorityTaskWoken 参数通知是否需要切换
- 由调用者在 ISR 返回前调用 portYIELD_FROM_ISR()
```

**常用 FromISR API 对照表**：

| 普通 API | FromISR API |
|----------|-------------|
| `xQueueSend()` | `xQueueSendFromISR()` |
| `xQueueReceive()` | `xQueueReceiveFromISR()` |
| `xSemaphoreGive()` | `xSemaphoreGiveFromISR()` |
| `xSemaphoreTake()` | **不提供**（ISR 中不能获取信号量）|
| `vTaskDelay()` | **不提供**（ISR 中不能延时）|
| `xTaskNotifyGive()` | `vTaskNotifyGiveFromISR()` |
| `xTaskNotify()` | `xTaskNotifyFromISR()` |
| `xEventGroupSetBits()` | `xEventGroupSetBitsFromISR()` |
| `vTaskResume()` | `xTaskResumeFromISR()` |
| `xTimerStart()` | `xTimerStartFromISR()` |

**标准 ISR 模板**：

```c
void EXTI0_IRQHandler(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    /* 1. 清除中断标志 */
    EXTI->PR = EXTI_PR_PR0;

    /* 2. 处理硬件（读取数据等）*/
    uint32_t data = read_sensor_data();

    /* 3. 使用 FromISR API 通知任务 */
    xQueueSendFromISR(xDataQueue, &data, &xHigherPriorityTaskWoken);

    /* 4. 如果有更高优先级任务被唤醒，请求上下文切换 */
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}
```

### 8.2 中断优先级与 FreeRTOS 的关系

**Cortex-M 中断优先级模型**：

```
优先级数值（越小越优先）：
  0 ─── 最高优先级
  1
  ...
  configMAX_SYSCALL_INTERRUPT_PRIORITY ─── FreeRTOS API 边界
  ...
  configLIBRARY_LOWEST_INTERRUPT_PRIORITY ─── 最低优先级（通常 15）

规则：
- 优先级 >= configMAX_SYSCALL_INTERRUPT_PRIORITY 的中断
  → 不能调用任何 FreeRTOS API
  → 不会被 FreeRTOS 屏蔽（永远可以打断其他代码）

- 优先级 < configMAX_SYSCALL_INTERRUPT_PRIORITY 的中断
  → 可以调用 FromISR API
  → 在临界区中会被 FreeRTOS 屏蔽
```

**配置示例（STM32，4 位优先级）**：

```c
/* FreeRTOSConfig.h */
#define configPRIO_BITS                  4  /* STM32 使用 4 位优先级 */

/* 最低中断优先级 */
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY         15

/* 可调用 FreeRTOS API 的最高中断优先级 */
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY    5

/* 实际写入 NVIC 的值（左移 4 位）*/
#define configKERNEL_INTERRUPT_PRIORITY          (15 << 4)
#define configMAX_SYSCALL_INTERRUPT_PRIORITY     (5 << 4)

/* 优先级层次：
 * 0-4  → 高优先级中断，不受 FreeRTOS 管理，不能调用 API
 * 5-15 → 可调用 FreeRTOS FromISR API
 *      → 其中 15 被 PendSV 和 SysTick 使用
 */
```

### 8.3 临界区与中断屏蔽

```c
/* 任务级临界区（屏蔽可管理的中断）*/
taskENTER_CRITICAL();
/* ... 临界区代码 ... */
taskEXIT_CRITICAL();

/* ISR 级临界区 */
UBaseType_t uxSavedInterruptStatus;
uxSavedInterruptStatus = taskENTER_CRITICAL_FROM_ISR();
/* ... 临界区代码 ... */
taskEXIT_CRITICAL_FROM_ISR(uxSavedInterruptStatus);

/* 仅屏蔽调度器（不关中断）*/
vTaskSuspendAll();
/* ... 不会触发上下文切换，但中断仍可触发 ... */
xTaskResumeAll();

/* 无条件屏蔽所有中断（慎用）*/
portDISABLE_INTERRUPTS();
portENABLE_INTERRUPTS();
```

---

## 九、双核调度（ESP32）

### 9.1 ESP32 双核架构

ESP32 拥有两个 Xtensa LX6 核心：

```
┌─────────────────────────────────────────┐
│                ESP32 SoC                │
│  ┌───────────────┐  ┌───────────────┐  │
│  │   Core 0      │  │   Core 1      │  │
│  │ (Protocol CPU)│  │ (Application) │  │
│  │               │  │               │  │
│  │  独立 FreeRTOS │  │  独立 FreeRTOS │  │
│  │  有自己的      │  │  有自己的      │  │
│  │  就绪列表     │  │  就绪列表     │  │
│  └───────┬───────┘  └───────┬───────┘  │
│          │                  │           │
│          └──── 共享内存 ────┘           │
│          └──── 互斥量/信号量 ────┘       │
└─────────────────────────────────────────┘

ESP-IDF 的 FreeRTOS 是 SMP（对称多处理）变体：
- 两个核心运行同一个 FreeRTOS 内核
- 共享任务就绪列表
- 调度器在两个核心上协调运行
```

### 9.2 核心亲和性与 xTaskCreatePinnedToCore

```c
/* 创建任务并绑定到特定核心 */
TaskHandle_t xTaskCreatePinnedToCore(
    TaskFunction_t pvTaskCode,
    const char * const pcName,
    const uint32_t usStackDepth,
    void * const pvParameters,
    UBaseType_t uxPriority,
    TaskHandle_t * const pxCreatedTask,
    const BaseType_t xCoreID  /* 0 或 1，或 tskNO_AFFINITY */
);

/* 示例：将 LVGL 任务固定到 Core 1 */
xTaskCreatePinnedToCore(
    vLvglTask,
    "LVGL",
    4096,
    NULL,
    5,
    NULL,
    1  /* 固定到 Core 1 */
);

/* tskNO_AFFINITY 表示任务可以在任意核心上运行 */
xTaskCreatePinnedToCore(
    vGeneralTask,
    "General",
    2048,
    NULL,
    3,
    NULL,
    tskNO_AFFINITY
);
```

### 9.3 双核调度策略

```c
/* ESP-IDF FreeRTOS 调度策略：
 *
 * 1. 固定亲和性任务 → 只在指定核心上调度
 * 2. 无亲和性任务 → 在两个核心间平衡分配
 * 3. 高优先级任务可以抢占任意核心上的低优先级任务
 *
 * 选择核心的顺序：
 * 1. 首先尝试当前核心（如果在当前核心调用创建）
 * 2. 然后尝试另一个核心
 * 3. 基于任务数量的负载均衡
 */

/* 运行时更改亲和性 */
BaseType_t xTaskCreateAffinitySet(
    TaskHandle_t xTask,
    BaseType_t xCoreID
);
```

### 9.4 双核系统中的同步

```c
/* 多核环境下的互斥量使用更加重要 */
SemaphoreHandle_t xI2CMutex;

void vInit(void)
{
    xI2CMutex = xSemaphoreCreateMutex();
}

/* Core 0 的任务 */
void vTaskOnCore0(void *pvParameters)
{
    xSemaphoreTake(xI2CMutex, portMAX_DELAY);
    i2c_read_sensor();  /* 访问共享 I2C 总线 */
    xSemaphoreGive(xI2CMutex);
}

/* Core 1 的任务 */
void vTaskOnCore1(void *pvParameters)
{
    xSemaphoreTake(xI2CMutex, portMAX_DELAY);
    i2c_write_display();  /* 同一条 I2C 总线 */
    xSemaphoreGive(xI2CMutex);
}

/* 注意：双核环境下 spinlock 更有效
 * ESP-IDF 提供了 portENTER_CRITICAL() 的多核安全版本
 */
```

### 9.5 双核系统的最佳实践

```
Core 0 (Protocol CPU):
  - WiFi/BLE 协议栈任务（由 ESP-IDF 自动创建）
  - 避免在 Core 0 上运行耗时的用户任务
  - WiFi/BLE 需要 Core 0 有足够 CPU 时间

Core 1 (Application CPU):
  - 用户应用任务（推荐）
  - LVGL 显示任务
  - 传感器采集任务
  - 计算密集型任务

一般建议：
  - 用户任务固定到 Core 1（xCoreID = 1）
  - 需要低延迟的任务使用高优先级
  - 避免两个核心同时访问同一外设（除非有互斥保护）
```

---

## 十、性能优化

### 10.1 栈使用分析

```c
/* 获取任务栈历史最小剩余值（高水位线）*/
UBaseType_t uxTaskGetStackHighWaterMark(TaskHandle_t xTask);

/* 高水位线含义：
 * 返回值 = 栈历史上剩余的最小字数（word）
 * 值越小 → 栈越危险
 * 值为 0 → 栈已经溢出（或非常接近溢出）
 *
 * 经验值：高水位线应 > 总栈大小的 20%
 * 如果高水位线 < 10%，应增大栈
 * 如果高水位线 > 50%，可考虑减小栈以节省内存
 */

/* 示例：打印所有任务的栈使用情况 */
void vPrintTaskStackUsage(void)
{
    TaskStatus_t *pxTaskStatusArray;
    volatile UBaseType_t uxArraySize, x;

    uxArraySize = uxTaskGetNumberOfTasks();
    pxTaskStatusArray = pvPortMalloc(uxArraySize * sizeof(TaskStatus_t));

    if (pxTaskStatusArray != NULL)
    {
        uxArraySize = uxTaskGetSystemState(pxTaskStatusArray, uxArraySize, NULL);

        printf("Task Name\tPriority\tStack High Water Mark\n");
        printf("---------\t--------\t---------------------\n");

        for (x = 0; x < uxArraySize; x++)
        {
            printf("%-16s\t%lu\t\t%lu\n",
                   pxTaskStatusArray[x].pcTaskName,
                   pxTaskStatusArray[x].uxCurrentPriority,
                   pxTaskStatusArray[x].usStackHighWaterMark);
        }

        vPortFree(pxTaskStatusArray);
    }
}
```

### 10.2 任务堆栈大小确定

**方法 1：静态分析**

```c
/* 分析任务函数的局部变量、函数调用深度 */
void vMyTask(void *pvParameters)
{
    /* 局部变量占栈空间 */
    uint8_t buffer[256];       /* 256 字节 */
    int32_t values[64];        /* 256 字节 */
    /* 函数调用链的返回地址、保存的寄存器等 */

    /* 栈大小估算：
     * 局部变量 + 函数调用深度 * 每层开销 + 中断嵌套开销 + 安全余量(20-30%)
     */
}
```

**方法 2：运行时测量**

```c
/* 1. 先用较大的栈启动任务 */
#define INITIAL_STACK_SIZE  4096

void vMyTask(void *pvParameters)
{
    /* 执行各种典型操作 */
    for (;;)
    {
        do_typical_work();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* 2. 使用 uxTaskGetStackHighWaterMark 测量 */
void vMeasureStack(void)
{
    UBaseType_t uxHighWaterMark = uxTaskGetStackHighWaterMark(NULL);
    printf("High water mark: %lu words (%lu bytes)\n",
           uxHighWaterMark, uxHighWaterMark * sizeof(StackType_t));
    /* 如果返回 200（words），实际使用 = 4096 - 200*4 = 3296 字节 */
    /* 推荐栈大小 = 3296 * 1.25 ≈ 4120 → 取整 4096 或 4608 */
}
```

**方法 3：使用 configCHECK_FOR_STACK_OVERFLOW**

```c
/* FreeRTOSConfig.h */
#define configCHECK_FOR_STACK_OVERFLOW  2

/* 实现钩子函数 */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    /* 栈溢出！记录错误信息 */
    printf("Stack overflow in task: %s\n", pcTaskName);
    /* 进入死循环或重启 */
    for (;;);
}

/* 模式 1：检查栈最后 20 字节是否被覆盖（快速但不一定准确）*/
/* 模式 2：用已知模式填充整个栈空间，检查是否被覆盖（更准确但慢）*/
```

### 10.3 运行时统计

```c
/* FreeRTOSConfig.h */
#define configGENERATE_RUN_TIME_STATS       1
#define configUSE_TRACE_FACILITY            1
#define configUSE_STATS_FORMATTING_FUNCTIONS 1

/* 需要提供一个高精度计时器（至少比 Tick 快 10 倍）*/
/* 方法 1：使用硬件定时器 */
extern volatile uint32_t ulRunTimeCounter;
void vConfigureTimerForRunTimeStats(void);

/* 接口函数 */
#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS()  vConfigureTimerForRunTimeStats()
#define portGET_RUN_TIME_COUNTER_VALUE()           ulRunTimeCounter

/* 定时器实现示例（使用 TIM2）*/
void vConfigureTimerForRunTimeStats(void)
{
    /* TIM2 配置为自由运行，100kHz 时钟 */
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    TIM2->PSC = (SystemCoreClock / 2 / 100000) - 1;  /* 100kHz */
    TIM2->ARR = 0xFFFFFFFF;
    TIM2->CR1 |= TIM_CR1_CEN;
}

volatile uint32_t ulRunTimeCounter = 0;
/* 在 TIM2 中断中递增 ulRunTimeCounter，或者直接读 TIM2->CNT */

/* 方法 2：直接读取 DWT 周期计数器（Cortex-M3/M4/M7）*/
#define portCONFIGURE_TIMER_FOR_RUN_TIME_STATS() \
    { CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk; \
      DWT->CYCCNT = 0; DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk; }
#define portGET_RUN_TIME_COUNTER_VALUE()  (DWT->CYCCNT)
```

**获取运行时统计信息**：

```c
/* 方法 1：直接打印统计表 */
char *pcStatsBuffer = pvPortMalloc(1024);
vTaskList(pcStatsBuffer);
printf("Task            State  Prio  Stack  Num\n");
printf("%s\n", pcStatsBuffer);
/*
 * 输出示例：
 * Task            State  Prio  Stack  Num
 * LVGL            R      5     200    3
 * Sensor          B      4     150    1
 * IDLE            R      0     100    0
 * Tmr Svc         B      6     152    5
 *
 * State: R=Running, B=Blocked, S=Suspended, D=Deleted
 */

/* 方法 2：获取每个任务的 CPU 时间百分比 */
char *pcRunTimeStats = pvPortMalloc(512);
vTaskGetRunTimeStats(pcRunTimeStats);
printf("Task            Abs Time      %% Time\n");
printf("%s\n", pcRunTimeStats);
/*
 * 输出示例：
 * Task            Abs Time      % Time
 * LVGL            1234567       45
 * Sensor          234567        8
 * IDLE            1234567       47
 */
```

### 10.4 Trace 工具

```c
/* FreeRTOS 内置 trace 钩子 */
#define traceTASK_CREATE(pxNewTCB)
#define traceTASK_DELETE(pxTaskToDelete)
#define traceTASK_SWITCHED_IN()
#define traceTASK_SWITCHED_OUT()
#define traceQUEUE_SEND(xQueue)
#define traceQUEUE_RECEIVE(xQueue)

/* 使用 Percepio FreeRTOS+Trace：
 * 1. 集成 Recorder 库
 * 2. 配置 trace hooks
 * 3. 运行系统
 * 4. 导出 trace 数据
 * 5. 使用 Tracealyzer 工具分析
 */

/* 使用 SystemView（Segger）：
 * 1. 集成 SEGGER_SYSVIEW 库
 * 2. 配置 FreeRTOS patch
 * 3. 通过 J-Link 实时传输数据
 * 4. 使用 SystemView 查看时间线
 */

/* 简单的自定义 trace（开关上下文记录）*/
typedef struct {
    uint32_t timestamp;
    const char *taskName;
    uint32_t event;  /* 0=switched in, 1=switched out */
} TraceEvent_t;

#define TRACE_BUFFER_SIZE 1024
TraceEvent_t xTraceBuffer[TRACE_BUFFER_SIZE];
volatile uint32_t uxTraceIndex = 0;

#define traceTASK_SWITCHED_IN() \
    { xTraceBuffer[uxTraceIndex].timestamp = portGET_RUN_TIME_COUNTER_VALUE(); \
      xTraceBuffer[uxTraceIndex].taskName = pxCurrentTCB->pcTaskName; \
      xTraceBuffer[uxTraceIndex].event = 0; \
      uxTraceIndex = (uxTraceIndex + 1) % TRACE_BUFFER_SIZE; }
```

---

## 十一、常见问题与解决方案

### 11.1 栈溢出

**症状**：
- HardFault 异常
- 数据莫名被破坏
- 程序跑飞到奇怪的地址
- `configCHECK_FOR_STACK_OVERFLOW` 钩子触发

**诊断方法**：

```c
/* 1. 启用栈溢出检测 */
#define configCHECK_FOR_STACK_OVERFLOW  2

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    printf("OVERFLOW: %s\n", pcTaskName);
    /* 可以在这里设置断点 */
    __asm("bkpt 0");
}

/* 2. 使用 MPU 进行硬件栈保护（如果 MCU 支持）*/
/* FreeRTOS 可配置 MPU 保护每个任务的栈区域 */

/* 3. 在调试器中手动检查栈指针 */
/* 打印 pxCurrentTCB->pxTopOfStack 和栈底部地址 */
```

**解决方案**：

```c
/* 1. 增大栈大小 */
xTaskCreate(vTask, "Task", 2048, NULL, pri, NULL);  /* 2048 words = 8KB */

/* 2. 减少栈上分配的大数组 */
/* 错误 */
void vBad(void *pv)
{
    uint8_t bigBuffer[1024];  /* 占用 1KB 栈空间！*/
    /* ... */
}

/* 正确 */
static uint8_t bigBuffer[1024];  /* 用 static 移到 .bss 段 */
/* 或者动态分配 */
uint8_t *bigBuffer = pvPortMalloc(1024);

/* 3. 减少函数调用深度，避免深层递归 */

/* 4. 将大的局部变量声明为 static 或动态分配 */
```

### 11.2 优先级反转

**诊断方法**：

```c
/* 使用 trace 工具观察任务切换时间线
 * 如果高优先级任务长时间不运行，而低优先级任务在运行
 * → 可能是优先级反转
 */

/* 1. 检查是否使用了互斥量（而非信号量）保护共享资源 */
SemaphoreHandle_t xMutex = xSemaphoreCreateMutex();  /* 正确 */

/* 2. 确保互斥量的获取和释放配对 */
void vTaskFunc(void *pvParameters)
{
    xSemaphoreTake(xMutex, portMAX_DELAY);
    /* ... */
    xSemaphoreGive(xMutex);  /* 确保释放！*/
}

/* 3. 如果确实存在优先级反转，使用互斥量的优先级继承功能 */
/* FreeRTOS 的互斥量默认支持优先级继承 */
```

### 11.3 死锁

**经典死锁场景**：

```c
/* 任务 A */
xSemaphoreTake(xMutex1, portMAX_DELAY);  /* 获取 Mutex1 */
xSemaphoreTake(xMutex2, portMAX_DELAY);  /* 等待 Mutex2 → 死锁！*/

/* 任务 B */
xSemaphoreTake(xMutex2, portMAX_DELAY);  /* 获取 Mutex2 */
xSemaphoreTake(xMutex1, portMAX_DELAY);  /* 等待 Mutex1 → 死锁！*/
```

**解决方案**：

```c
/* 方法 1：统一获取顺序 */
/* 任务 A 和 B 都先获取 Mutex1，再获取 Mutex2 */
xSemaphoreTake(xMutex1, portMAX_DELAY);
xSemaphoreTake(xMutex2, portMAX_DELAY);
/* ... */
xSemaphoreGive(xMutex2);
xSemaphoreGive(xMutex1);

/* 方法 2：使用超时 */
if (xSemaphoreTake(xMutex1, pdMS_TO_TICKS(100)) == pdTRUE)
{
    if (xSemaphoreTake(xMutex2, pdMS_TO_TICKS(100)) == pdTRUE)
    {
        /* 成功获取两个锁 */
        xSemaphoreGive(xMutex2);
    }
    xSemaphoreGive(xMutex1);
}
/* 超时后可以重试或执行备选方案 */

/* 方法 3：使用递归互斥量（当同一任务需要重入时）*/
SemaphoreHandle_t xRecursiveMutex = xSemaphoreCreateRecursiveMutex();
xSemaphoreTakeRecursive(xRecursiveMutex, portMAX_DELAY);
xSemaphoreTakeRecursive(xRecursiveMutex, portMAX_DELAY); /* 不会死锁 */
xSemaphoreGiveRecursive(xRecursiveMutex);
xSemaphoreGiveRecursive(xRecursiveMutex);

/* 方法 4：尽量减少使用多个互斥量
 * 考虑是否真的需要两个互斥量
 * 或者将临界区合并为一个更大的临界区
 */
```

### 11.4 内存泄漏检测

**预防措施**：

```c
/* 1. 使用静态分配（完全避免动态内存问题）*/
StaticTask_t xTaskBuffer;
StackType_t xStack[STACK_SIZE];
TaskHandle_t xTask = xTaskCreateStatic(vTaskFunc, "Task", STACK_SIZE,
                                        NULL, 1, xStack, &xTaskBuffer);

/* 2. 定期检查堆水位线 */
void vMemoryMonitorTask(void *pvParameters)
{
    for (;;)
    {
        size_t freeHeap = xPortGetFreeHeapSize();
        size_t minEverFreeHeap = xPortGetMinimumEverFreeHeapSize();

        printf("Free heap: %u, Min ever: %u\n", freeHeap, minEverFreeHeap);

        if (minEverFreeHeap < MIN_SAFE_HEAP_THRESHOLD)
        {
            printf("WARNING: heap usage is dangerously high!\n");
        }

        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}

/* 3. 使用 vPortFree 后将指针置 NULL */
void vSafeFree(void **ppvPtr)
{
    if (*ppvPtr != NULL)
    {
        vPortFree(*ppvPtr);
        *ppvPtr = NULL;
    }
}

/* 4. 封装 malloc/free 进行跟踪 */
typedef struct {
    void *ptr;
    size_t size;
    const char *file;
    int line;
} AllocRecord_t;

#define TRACKED_MALLOC(size) \
    tracked_malloc(size, __FILE__, __LINE__)

#define TRACKED_FREE(ptr) \
    tracked_free(ptr, __FILE__, __LINE__)
```

### 11.5 HardFault 调试

```c
/* Cortex-M HardFault 处理 */
void HardFault_Handler(void)
{
    /* 方法 1：使用 SCB 寄存器获取故障信息 */
    volatile uint32_t cfsr = SCB->CFSR;   /* 可配置故障状态寄存器 */
    volatile uint32_t hfsr = SCB->HFSR;   /* 硬故障状态寄存器 */
    volatile uint32_t mmfar = SCB->MMFAR; /* 内存管理故障地址 */
    volatile uint32_t bfar = SCB->BFAR;   /* 总线故障地址 */

    printf("HardFault! CFSR=0x%08lX HFSR=0x%08lX\n", cfsr, hfsr);

    if (cfsr & (1 << 7))  /* MMARVALID */
        printf("MMFAR=0x%08lX\n", mmfar);
    if (cfsr & (1 << 15)) /* BFARVALID */
        printf("BFAR=0x%08lX\n", bfar);

    /* 方法 2：分析栈帧（在调试器中）*/
    /* 栈帧布局（入栈顺序）：
     * R0, R1, R2, R3, R12, LR, PC, xPSR
     * PC → 故障发生时的指令地址
     * LR → 返回地址
     */

    /* 进入死循环，方便调试器连接 */
    for (;;);
}

/* 从 HardFault 中恢复栈指针（调试用）*/
void prvGetRegistersFromStack(uint32_t *pulFaultStackAddress)
{
    volatile uint32_t r0 = pulFaultStackAddress[0];
    volatile uint32_t r1 = pulFaultStackAddress[1];
    volatile uint32_t r2 = pulFaultStackAddress[2];
    volatile uint32_t r3 = pulFaultStackAddress[3];
    volatile uint32_t r12 = pulFaultStackAddress[4];
    volatile uint32_t lr = pulFaultStackAddress[5];
    volatile uint32_t pc = pulFaultStackAddress[6];
    volatile uint32_t psr = pulFaultStackAddress[7];

    printf("R0=0x%08lX R1=0x%08lX R2=0x%08lX R3=0x%08lX\n", r0, r1, r2, r3);
    printf("R12=0x%08lX LR=0x%08lX PC=0x%08lX PSR=0x%08lX\n", r12, lr, pc, psr);

    (void)r0; (void)r1; (void)r2; (void)r3;
    (void)r12; (void)lr; (void)pc; (void)psr;
    for (;;);
}

/* 在启动文件中修改 HardFault_Handler 为汇编钩子：
 * HardFault_Handler:
 *     TST LR, #4
 *     ITE EQ
 *     MRSEQ R0, MSP
 *     MRSNE R0, PSP
 *     B prvGetRegistersFromStack
 */
```

### 11.6 任务调度异常

```c
/* 常见问题：任务创建后不运行 */

/* 原因 1：调度器未启动 */
vTaskStartScheduler();  /* 必须调用！*/

/* 原因 2：任务优先级为 0（idle 优先级）*/
/* idle 任务也是优先级 0，可能互相竞争 */
xTaskCreate(vTask, "Task", STACK_SIZE, NULL, 1, NULL);  /* 优先级至少为 1 */

/* 原因 3：栈空间不足导致栈溢出 → 见 11.1 */

/* 原因 4：任务函数中立即阻塞 */
void vBadTask(void *pvParameters)
{
    xSemaphoreTake(xSemaphore, portMAX_DELAY);  /* 永久阻塞，信号量未被 Give */
}

/* 原因 5：中断优先级配置错误 */
/* 确保 configMAX_SYSCALL_INTERRUPT_PRIORITY 正确设置 */
```

---

## 附录：FreeRTOSConfig.h 关键配置速查

```c
/* ======== 核心配置 ======== */
#define configUSE_PREEMPTION                    1   /* 抢占式调度 */
#define configUSE_PORT_OPTIMISED_TASK_SELECTION 1   /* 硬件加速任务选择 */
#define configUSE_TICKLESS_IDLE                 0   /* 低功耗 Tickless 模式 */
#define configCPU_CLOCK_HZ                      240000000  /* CPU 频率 */
#define configTICK_RATE_HZ                      1000       /* Tick 频率 */
#define configMAX_PRIORITIES                    25  /* 最大优先级数 */
#define configMINIMAL_STACK_SIZE                128 /* 最小栈大小(word) */
#define configMAX_TASK_NAME_LEN                 16  /* 任务名最大长度 */
#define configUSE_16_BIT_TICKS                  0   /* 使用 32 位 Tick */
#define configIDLE_SHOULD_YIELD                 1   /* idle 任务让出 CPU */
#define configUSE_TASK_NOTIFICATIONS            1   /* 任务通知 */
#define configTASK_NOTIFICATION_ARRAY_ENTRIES   1   /* 通知数组大小 */
#define configUSE_MUTEXES                       1   /* 互斥量 */
#define configUSE_RECURSIVE_MUTEXES             1   /* 递归互斥量 */
#define configUSE_COUNTING_SEMAPHORES           1   /* 计数信号量 */
#define configQUEUE_REGISTRY_SIZE               8   /* 队列注册表大小 */
#define configUSE_QUEUE_SETS                    0   /* 队列集 */
#define configUSE_TIME_SLICING                  1   /* 时间片轮转 */
#define configUSE_NEWLIB_REENTRANT              0   /* Newlib 可重入 */
#define configENABLE_BACKWARD_COMPATIBILITY     0   /* 向后兼容 */
#define configNUM_THREAD_LOCAL_STORAGE_POINTERS 5   /* TLS 指针数量 */

/* ======== 内存管理 ======== */
#define configSUPPORT_STATIC_ALLOCATION         1   /* 支持静态分配 */
#define configSUPPORT_DYNAMIC_ALLOCATION        1   /* 支持动态分配 */
#define configTOTAL_HEAP_SIZE                   (32*1024) /* 堆大小 */
#define configAPPLICATION_ALLOCATED_HEAP        0   /* 应用分配堆 */

/* ======== 钩子函数 ======== */
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0
#define configCHECK_FOR_STACK_OVERFLOW          2   /* 栈溢出检测 */
#define configUSE_MALLOC_FAILED_HOOK            1   /* malloc 失败钩子 */
#define configUSE_DAEMON_TASK_STARTUP_HOOK      0

/* ======== 运行时统计 ======== */
#define configGENERATE_RUN_TIME_STATS           0
#define configUSE_TRACE_FACILITY                1
#define configUSE_STATS_FORMATTING_FUNCTIONS    0

/* ======== 协程（已弃用）======== */
#define configUSE_CO_ROUTINES                   0
#define configMAX_CO_ROUTINE_PRIORITIES         2

/* ======== 软件定时器 ======== */
#define configUSE_TIMERS                        1
#define configTIMER_TASK_PRIORITY               5
#define configTIMER_QUEUE_LENGTH                10
#define configTIMER_TASK_STACK_DEPTH            256

/* ======== 中断优先级 ======== */
#define configPRIO_BITS                         4
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY         15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY    5
#define configKERNEL_INTERRUPT_PRIORITY          (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY     (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* ======== 断言 ======== */
#define configASSERT(x) if (!(x)) { taskDISABLE_INTERRUPTS(); for(;;); }

/* ======== API 包含 ======== */
#define INCLUDE_vTaskPrioritySet                1
#define INCLUDE_uxTaskPriorityGet               1
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskSuspend                    1
#define INCLUDE_xResumeFromISR                  1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelay                      1
#define INCLUDE_xTaskGetSchedulerState          1
#define INCLUDE_xTaskGetCurrentTaskHandle       1
#define INCLUDE_uxTaskGetStackHighWaterMark     1
#define INCLUDE_eTaskGetState                   1
#define INCLUDE_xTimerPendFunctionCall          1
#define INCLUDE_xTaskAbortDelay                 1
#define INCLUDE_xTaskGetHandle                  1
```

---

## 附录：常用 API 速查表

### 任务管理

| API | 功能 |
|-----|------|
| `xTaskCreate()` | 动态创建任务 |
| `xTaskCreateStatic()` | 静态创建任务 |
| `xTaskCreatePinnedToCore()` | 创建任务并绑定核心（ESP32）|
| `vTaskDelete()` | 删除任务 |
| `vTaskSuspend()` | 挂起任务 |
| `vTaskResume()` | 恢复任务 |
| `xTaskResumeFromISR()` | ISR 中恢复任务 |
| `vTaskDelay()` | 相对延时 |
| `vTaskDelayUntil()` | 绝对延时（精确周期）|
| `vTaskPrioritySet()` | 设置任务优先级 |
| `uxTaskPriorityGet()` | 获取任务优先级 |
| `vTaskList()` | 打印任务列表 |

### 队列

| API | 功能 |
|-----|------|
| `xQueueCreate()` | 创建队列 |
| `xQueueSend()` / `xQueueSendToBack()` | 发送到队尾 |
| `xQueueSendToFront()` | 发送到队首 |
| `xQueueSendFromISR()` | ISR 中发送 |
| `xQueueReceive()` | 接收 |
| `xQueueReceiveFromISR()` | ISR 中接收 |
| `xQueuePeek()` | 窥视（不移除）|
| `uxQueueMessagesWaiting()` | 获取消息数量 |

### 信号量/互斥量

| API | 功能 |
|-----|------|
| `xSemaphoreCreateBinary()` | 创建二值信号量 |
| `xSemaphoreCreateCounting()` | 创建计数信号量 |
| `xSemaphoreCreateMutex()` | 创建互斥量 |
| `xSemaphoreCreateRecursiveMutex()` | 创建递归互斥量 |
| `xSemaphoreTake()` | 获取信号量/互斥量 |
| `xSemaphoreGive()` | 释放信号量/互斥量 |
| `xSemaphoreTakeRecursive()` | 递归获取 |
| `xSemaphoreGiveRecursive()` | 递归释放 |

### 事件标志组

| API | 功能 |
|-----|------|
| `xEventGroupCreate()` | 创建事件组 |
| `xEventGroupSetBits()` | 设置事件位 |
| `xEventGroupClearBits()` | 清除事件位 |
| `xEventGroupWaitBits()` | 等待事件位 |
| `xEventGroupGetBits()` | 获取当前事件位 |

### 软件定时器

| API | 功能 |
|-----|------|
| `xTimerCreate()` | 创建定时器 |
| `xTimerStart()` | 启动 |
| `xTimerStop()` | 停止 |
| `xTimerReset()` | 重置 |
| `xTimerChangePeriod()` | 更改周期 |
| `pvTimerGetTimerID()` | 获取定时器 ID |

### 内存管理

| API | 功能 |
|-----|------|
| `pvPortMalloc()` | 分配内存 |
| `vPortFree()` | 释放内存 |
| `xPortGetFreeHeapSize()` | 获取空闲堆大小 |
| `xPortGetMinimumEverFreeHeapSize()` | 获取历史最小空闲堆 |

---

> **参考资源**：
> - [FreeRTOS 官方文档](https://www.freertos.org/Documentation/RTOS_book.html)
> - [FreeRTOS API 参考](https://www.freertos.org/a00106.html)
> - [ESP-IDF FreeRTOS 文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/freertos.html)
> - 《Mastering the FreeRTOS Real Time Kernel》 - Richard Barry
