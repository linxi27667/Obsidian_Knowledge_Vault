# FreeRTOS进阶

## 核心概念

- **内存管理** - 堆策略
- **MPU保护** - 内存保护
- **对称多处理** - 多核调度
- **低功耗** - Tickless模式

---

## 一、内存管理进阶

### 1.1 堆策略选择

```c
// heap_1: 只分配不释放
// heap_2: 允许释放，不合并
// heap_4: 允许释放，合并相邻空闲块
// heap_5: 跨越多个非连续内存区域

// heap_4实现
typedef struct A_BLOCK_LINK {
    struct A_BLOCK_LINK *pxNextFreeBlock;
    size_t xBlockSize;
} BlockLink_t;

static BlockLink_t xStart, xEnd;

void *pvPortMalloc(size_t xWantedSize) {
    BlockLink_t *pxBlock, *pxPreviousBlock, *pxNewBlockLink;

    vTaskSuspendAll();
    {
        // 对齐
        xWantedSize += heapSTRUCT_SIZE;
        xWantedSize &= ~heapBYTE_ALIGNMENT_MASK;

        // 遍历空闲链表
        pxPreviousBlock = &xStart;
        pxBlock = xStart.pxNextFreeBlock;

        while ((pxBlock->xBlockSize < xWantedSize) && (pxBlock->pxNextFreeBlock != NULL)) {
            pxPreviousBlock = pxBlock;
            pxBlock = pxBlock->pxNextFreeBlock;
        }

        if (pxBlock->xBlockSize >= xWantedSize) {
            // 分割块
            if ((pxBlock->xBlockSize - xWantedSize) > heapMINIMUM_BLOCK_SIZE) {
                pxNewBlockLink = (void *)(((uint8_t *)pxBlock) + xWantedSize);
                pxNewBlockLink->xBlockSize = pxBlock->xBlockSize - xWantedSize;
                pxBlock->xBlockSize = xWantedSize;

                // 插入空闲链表
                pxNewBlockLink->pxNextFreeBlock = pxPreviousBlock->pxNextFreeBlock;
                pxPreviousBlock->pxNextFreeBlock = pxNewBlockLink;
            }

            // 从空闲链表移除
            pxPreviousBlock->pxNextFreeBlock = pxBlock->pxNextFreeBlock;

            // 标记为已分配
            pxBlock->pxNextFreeBlock = NULL;
        }
    }
    xTaskResumeAll();

    return (void *)(((uint8_t *)pxBlock) + heapSTRUCT_SIZE);
}

// 合并空闲块
static void prvInsertBlockIntoFreeList(BlockLink_t *pxBlockToInsert) {
    BlockLink_t *pxIterator;

    // 遍历找到合适位置
    for (pxIterator = &xStart; pxIterator->pxNextFreeBlock < pxBlockToInsert;
         pxIterator = pxIterator->pxNextFreeBlock) {
    }

    // 检查是否可以与前一个块合并
    if (((uint8_t *)pxIterator) + pxIterator->xBlockSize == (uint8_t *)pxBlockToInsert) {
        pxIterator->xBlockSize += pxBlockToInsert->xBlockSize;
        pxBlockToInsert = pxIterator;
    }

    // 检查是否可以与后一个块合并
    if (((uint8_t *)pxBlockToInsert) + pxBlockToInsert->xBlockSize ==
        (uint8_t *)pxIterator->pxNextFreeBlock) {
        if (pxIterator->pxNextFreeBlock != xEnd.pxNextFreeBlock) {
            pxBlockToInsert->xBlockSize += pxIterator->pxNextFreeBlock->xBlockSize;
            pxBlockToInsert->pxNextFreeBlock = pxIterator->pxNextFreeBlock->pxNextFreeBlock;
        }
    }

    pxBlockToInsert->pxNextFreeBlock = pxIterator->pxNextFreeBlock;
    pxIterator->pxNextFreeBlock = pxBlockToInsert;
}
```

---

### 1.2 内存池

```c
// 固定大小内存池(零碎片)
typedef struct pool_block {
    struct pool_block *next;
} pool_block_t;

typedef struct {
    pool_block_t *free_list;
    uint8_t *pool;
    size_t block_size;
    size_t block_count;
} memory_pool_t;

void pool_init(memory_pool_t *pool, void *mem, size_t block_size, size_t count) {
    pool->pool = (uint8_t *)mem;
    pool->block_size = block_size;
    pool->block_count = count;
    pool->free_list = NULL;

    // 构建空闲链表
    for (size_t i = 0; i < count; i++) {
        pool_block_t *block = (pool_block_t *)(pool->pool + i * block_size);
        block->next = pool->free_list;
        pool->free_list = block;
    }
}

void *pool_alloc(memory_pool_t *pool) {
    pool_block_t *block = pool->free_list;
    if (block) {
        pool->free_list = block->next;
    }
    return block;
}

void pool_free(memory_pool_t *pool, void *ptr) {
    pool_block_t *block = (pool_block_t *)ptr;
    block->next = pool->free_list;
    pool->free_list = block;
}
```

---

## 二、MPU保护

### 2.1 MPU配置

```c
// Cortex-M MPU区域
typedef struct {
    uint32_t base;
    uint32_t size;
    uint32_t attributes;
    uint32_t number;
} mpu_region_t;

// 配置MPU区域
void mpu_configure_region(mpu_region_t *region) {
    MPU->RNR = region->number;
    MPU->RBAR = region->base & MPU_RBAR_ADDR_Msk;
    MPU->RASR = region->attributes | MPU_RASR_ENABLE_Msk |
                ((31 - __builtin_clz(region->size)) << MPU_RASR_SIZE_Pos);
}

// FreeRTOS MPU任务
void mpu_task_entry(void *param) {
    // 配置任务MPU区域
    mpu_region_t regions[] = {
        {0x08000000, 0x10000, MPU_RASR_AP_RO | MPU_RASR_C_Msk, 0},  // Flash只读
        {0x20000000, 0x8000, MPU_RASR_AP_RW | MPU_RASR_C_Msk, 1},   // RAM读写
        {0x40000000, 0x100000, MPU_RASR_AP_RW | MPU_RASR_XN_Msk, 2}, // 外设
    };

    for (int i = 0; i < 3; i++) {
        mpu_configure_region(&regions[i]);
    }

    // 启用MPU
    MPU->CTRL = MPU_CTRL_ENABLE_Msk | MPU_CTRL_PRIVDEFENA_Msk;
    __asm__ volatile ("dsb");
    __asm__ volatile ("isb");

    // 任务代码
    while (1) {
        // ...
    }
}
```

---

### 2.2 特权级分离

```c
// 特权级和非特权级
/*
 * 特权级(Pileged):
 * - 可以访问所有资源
 * - 可以修改MPU配置
 * - 内核代码运行在此级别
 *
 * 非特权级(Unprivileged):
 * - 受MPU限制
 * - 不能修改MPU配置
 * - 用户代码运行在此级别
 */

// 创建MPU保护任务
void create_mpu_task(void) {
    // 任务参数
    TaskParameters_t params = {
        .pvTaskCode = mpu_task_entry,
        .pcName = "MPU Task",
        .usStackDepth = 256,
        .pvParameters = NULL,
        .uxPriority = 2,
        .puxStackBuffer = stack_buffer,
        .xRegions = {
            {0x08000000, 0x10000, portMPU_REGION_READ_ONLY},
            {0x20000000, 0x8000, portMPU_REGION_READ_WRITE},
            {0, 0, 0},
        }
    };

    xTaskCreateRestricted(&params, &task_handle);
}
```

---

## 三、Tickless低功耗

### 3.1 Tickless实现

```c
// Tickless模式: 空闲时停止tick中断
/*
 * 原理:
 * 1. 空闲任务运行时，计算下次唤醒时间
 * 2. 配置定时器到下次唤醒时间
 * 3. 进入低功耗模式
 * 4. 唤醒后补偿丢失的tick
 */

void vPortSuppressTicksAndSleep(TickType_t xExpectedIdleTime) {
    // 确保不会太短
    if (xExpectedIdleTime < configEXPECTED_IDLE_TIME_BEFORE_SLEEP) {
        return;
    }

    // 停止tick定时器
    portNVIC_SYSTICK_CTRL_REG &= ~portNVIC_SYSTICK_ENABLE_BIT;

    // 配置唤醒定时器
    uint32_t reload = xExpectedIdleTime * portNVIC_SYSTICK_LOAD;
    wakeup_timer_set(reload);

    // 进入睡眠
    __asm__ volatile ("wfi");

    // 唤醒后
    TickType_t elapsed = wakeup_timer_get_elapsed();
    vTaskStepTick(elapsed);

    // 重启tick定时器
    portNVIC_SYSTICK_CTRL_REG |= portNVIC_SYSTICK_ENABLE_BIT;
}

// 配置
#define configUSE_TICKLESS_IDLE 1
#define configEXPECTED_IDLE_TIME_BEFORE_SLEEP 5
```

---

### 3.2 动态时钟

```c
// 动态频率调节
void vApplicationIdleHook(void) {
    // 空闲时降低频率
    if (xTaskGetTickCount() - last_activity > IDLE_THRESHOLD) {
        set_cpu_frequency(LOW_FREQ);
    }
}

// 活动检测
void activity_detected(void) {
    last_activity = xTaskGetTickCount();
    set_cpu_frequency(HIGH_FREQ);
}
```

---

## 四、多核FreeRTOS

### 4.1 SMP调度

```c
// SMP配置
#define configNUMBER_OF_CORES 2
#define configUSE_CORE_AFFINITY 1

// 核心亲和性
#define tskCORE_0 (1 << 0)
#define tskCORE_1 (1 << 1)
#define tskCORE_ALL (tskCORE_0 | tskCORE_1)

void create_smp_task(void) {
    TaskHandle_t task;

    // 创建任务
    xTaskCreate(task_entry, "Task", 256, NULL, 2, &task);

    // 设置核心亲和性
    vTaskCoreAffinitySet(task, tskCORE_0);  // 绑定到核心0
}

// 任务迁移
void migrate_task(TaskHandle_t task, BaseType_t core) {
    vTaskCoreAffinitySet(task, (1 << core));
}
```

---

### 4.2 自旋锁

```c
// FreeRTOS自旋锁(SMP)
typedef struct {
    volatile uint32_t lock;
} spinlock_t;

#define SPIN_LOCK_INITIALIZER {0}

void spin_lock(spinlock_t *lock) {
    while (__sync_lock_test_and_set(&lock->lock, 1)) {
        // 自旋等待
        __asm__ volatile ("wfe");  // 等待事件
    }
    __asm__ volatile ("dmb");  // 内存屏障
}

void spin_unlock(spinlock_t *lock) {
    __asm__ volatile ("dmb");
    __sync_lock_release(&lock->lock);
    __asm__ volatile ("sev");  // 发送事件
}

// FreeRTOS API
void critical_section_example(void) {
    // 任务级临界区
    taskENTER_CRITICAL();
    // ... 共享资源访问
    taskEXIT_CRITICAL();

    // ISR级临界区
    UBaseType_t saved = taskENTER_CRITICAL_FROM_ISR();
    // ... 共享资源访问
    taskEXIT_CRITICAL_FROM_ISR(saved);
}
```

---

## 五、任务通知进阶

### 5.1 通知作为轻量级IPC

```c
// 任务通知代替信号量
void producer_task(void *param) {
    while (1) {
        // 处理数据
        process_data();

        // 通知消费者(代替信号量)
        xTaskNotifyGive(consumer_task_handle);

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void consumer_task(void *param) {
    while (1) {
        // 等待通知(代替xSemaphoreTake)
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        // 处理数据
        consume_data();
    }
}

// 任务通知传递值
void send_value(TaskHandle_t target, uint32_t value) {
    xTaskNotify(target, value, eSetValueWithOverwrite);
}

uint32_t receive_value(void) {
    uint32_t value;
    xTaskNotifyWait(0, 0xFFFFFFFF, &value, portMAX_DELAY);
    return value;
}
```

---

## 附录：FreeRTOS配置

```c
// FreeRTOSConfig.h关键配置
#define configUSE_PREEMPTION 1           // 抢占式调度
#define configUSE_IDLE_HOOK 1            // 空闲钩子
#define configUSE_TICK_HOOK 0            // Tick钩子
#define configCPU_CLOCK_HZ 168000000     // CPU频率
#define configTICK_RATE_HZ 1000          // Tick频率
#define configMAX_PRIORITIES 16          // 最大优先级
#define configMINIMAL_STACK_SIZE 128     // 最小栈大小
#define configTOTAL_HEAP_SIZE (64*1024)  // 堆大小
#define configMAX_TASK_NAME_LEN 16       // 任务名长度
#define configUSE_TRACE_FACILITY 1       // 跟踪功能
#define configUSE_MUTEXES 1              // 互斥量
#define configQUEUE_REGISTRY_SIZE 8      // 队列注册表
#define configUSE_RECURSIVE_MUTEXES 1    // 递归互斥量
#define configUSE_COUNTING_SEMAPHORES 1  // 计数信号量
#define configUSE_TASK_NOTIFICATIONS 1   // 任务通知
```

---

## 相关链接

- [[FreeRTOS基础]] - FreeRTOS基础
- [[RTOS调度算法]] - 调度算法
- [[功耗优化进阶]] - 低功耗设计
- [[STM32进阶]] - STM32高级特性
