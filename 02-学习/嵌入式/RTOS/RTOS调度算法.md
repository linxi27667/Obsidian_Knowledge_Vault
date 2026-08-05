# RTOS调度算法

## 核心概念

- **调度器** - 决定哪个任务运行
- **抢占** - 高优先级打断低优先级
- **时间片** - 同优先级轮转
- **实时性** - 确定性响应

---

## 一、调度算法概述

### 1.1 调度类型

| 类型 | 特点 | 应用 |
|------|------|------|
| 抢占式 | 高优先级立即抢占 | 实时系统 |
| 协作式 | 主动让出CPU | 简单系统 |
| 时间片轮转 | 同优先级分时 | 通用系统 |
| 混合式 | 抢占+时间片 | 多数RTOS |

---

### 1.2 调度策略

```c
// 调度策略比较
/*
 * 1. FIFO(先来先服务):
 *    - 非抢占
 *    - 短任务可能饥饿
 *
 * 2. 优先级调度:
 *    - 可抢占
 *    - 优先级反转问题
 *
 * 3. 最短截止时间优先(EDF):
 *    - 动态优先级
 *    - 理论最优
 *
 * 4. 速率单调(RMS):
 *    - 静态优先级
 *    - 周期越短优先级越高
 */
```

---

## 二、FreeRTOS调度

### 2.1 调度器实现

```c
// FreeRTOS调度器核心
/*
 * 1. 优先级就绪表(pxReadyTasksLists[])
 * 2. 当前任务指针(pxCurrentTCB)
 * 3. 上下文切换(vPortYield)
 */

// 就绪表结构
typedef struct xLIST {
    UBaseType_t uxNumberOfItems;
    ListItem_t *pxIndex;
    ListItem_t xListEnd;
} List_t;

// 每个优先级一个就绪列表
static List_t pxReadyTasksLists[configMAX_PRIORITIES];

// 调度决策
void vTaskSwitchContext(void) {
    // 找到最高优先级的就绪任务
    UBaseType_t uxTopPriority = uxTopReadyPriority;

    while (listLIST_IS_EMPTY(&pxReadyTasksLists[uxTopPriority])) {
        uxTopPriority--;
    }

    // 获取该优先级的下一个任务
    listGET_OWNER_OF_NEXT_ENTRY(pxCurrentTCB, &pxReadyTasksLists[uxTopPriority]);
}
```

---

### 2.2 时间片调度

```c
// 时间片配置
/*
 * configUSE_TIME_SLICING = 1  // 启用时间片
 * configTICK_RATE_HZ = 1000   // 1ms滴答
 *
 * 同优先级任务轮流执行，每个任务运行1个tick
 */

// 时间片中断处理
void xTaskIncrementTick(void) {
    TCB_t *pxTCB = pxCurrentTCB;

    // 检查时间片是否用完
    if (listCURRENT_LIST_LENGTH(&pxReadyTasksLists[pxTCB->uxPriority]) > 1) {
        // 请求上下文切换
        xYieldPending = pdTRUE;
    }
}
```

---

### 2.3 优先级反转

```c
// 优先级反转问题
/*
 * 任务优先级: H > M > L
 *
 * 1. L 获取资源锁
 * 2. H 就绪，抢占 L
 * 3. H 尝试获取锁，阻塞
 * 4. M 就绪，抢占 L
 * 5. M 运行(优先级高于 L)
 * 6. L 无法释放锁 → H 被 M 间接阻塞
 */

// 解决方案1: 优先级继承
void mutex_take_priority_inheritance(mutex_t *m) {
    if (m->holder != NULL && m->holder->priority < current_task->priority) {
        // 提升持有者优先级
        m->holder->priority = current_task->priority;
    }
    // 等待锁
    wait_for_mutex(m);
}

// 解决方案2: 优先级天花板
/*
 * 预设资源的天花板优先级 = 使用该资源的最高任务优先级
 * 任务获取资源时立即提升到天花板优先级
 */
```

---

## 三、调度算法实现

### 3.1 优先级位图

```c
// 位图快速查找最高优先级
static UBaseType_t uxTopReadyPriority = 0;

// 设置优先级位
#define taskRECORD_READY_PRIORITY(uxPriority) \
    uxTopReadyPriority |= (1UL << (uxPriority))

// 清除优先级位
#define taskRESET_READY_PRIORITY(uxPriority) \
    uxTopReadyPriority &= ~(1UL << (uxPriority))

// 获取最高优先级(使用CLZ指令)
#define taskGET_HIGHEST_PRIORITY() \
    (31UL - __builtin_clz(uxTopReadyPriority))

// ARM CLZ实现
static inline uint32_t clz(uint32_t x) {
    uint32_t count;
    __asm__ volatile ("clz %0, %1" : "=r"(count) : "r"(x));
    return count;
}
```

---

### 3.2 EDF调度

```c
// 最短截止时间优先(EDF)
typedef struct {
    uint32_t deadline;
    uint32_t period;
    uint32_t execution_time;
    uint32_t remaining_time;
} edf_task_t;

edf_task_t edf_tasks[MAX_TASKS];
int edf_task_count = 0;

int edf_schedule(void) {
    int earliest = -1;
    uint32_t min_deadline = UINT32_MAX;

    for (int i = 0; i < edf_task_count; i++) {
        if (edf_tasks[i].remaining_time > 0 &&
            edf_tasks[i].deadline < min_deadline) {
            min_deadline = edf_tasks[i].deadline;
            earliest = i;
        }
    }

    return earliest;
}

void edf_tick(void) {
    for (int i = 0; i < edf_task_count; i++) {
        if (edf_tasks[i].remaining_time > 0) {
            edf_tasks[i].remaining_time--;
        }
    }
}
```

---

### 3.3 RMS调度

```c
// 速率单调调度(RMS)
/*
 * 静态优先级: 周期越短，优先级越高
 *
 * 可调度性测试:
 *   Σ(Ci/Ti) ≤ n(2^(1/n) - 1)
 *
 *   Ci: 执行时间
 *   Ti: 周期
 *   n: 任务数
 *
 * n=3时: 可调度界限 ≈ 0.780
 * n→∞时: 可调度界限 → ln(2) ≈ 0.693
 */

typedef struct {
    uint32_t period;
    uint32_t execution_time;
    uint32_t priority;  // 周期越短优先级越高
} rms_task_t;

bool rms_is_schedulable(rms_task_t *tasks, int count) {
    float utilization = 0;
    for (int i = 0; i < count; i++) {
        utilization += (float)tasks[i].execution_time / tasks[i].period;
    }

    float bound = count * (powf(2.0f, 1.0f / count) - 1.0f);
    return utilization <= bound;
}
```

---

## 四、上下文切换

### 4.1 ARM Cortex-M上下文切换

```c
// ARM上下文保存
/*
 * 自动保存(硬件):
 *   R0-R3, R12, LR, PC, xPSR
 *
 * 手动保存(软件):
 *   R4-R11, EXC_RETURN
 */

// PendSV中断(上下文切换)
__attribute__((naked))
void PendSV_Handler(void) {
    __asm__ volatile (
        // 保存上下文
        "mrs r0, psp\n"
        "stmdb r0!, {r4-r11}\n"

        // 保存当前任务SP
        "ldr r1, =pxCurrentTCB\n"
        "ldr r1, [r1]\n"
        "str r0, [r1]\n"

        // 调度下一个任务
        "bl vTaskSwitchContext\n"

        // 加载新任务SP
        "ldr r1, =pxCurrentTCB\n"
        "ldr r1, [r1]\n"
        "ldr r0, [r1]\n"

        // 恢复上下文
        "ldmia r0!, {r4-r11}\n"
        "msr psp, r0\n"

        // 返回
        "bx lr\n"
    );
}
```

---

### 4.2 RISC-V上下文切换

```c
// RISC-V上下文切换
__attribute__((naked))
void context_switch(uint32_t *old_sp, uint32_t *new_sp) {
    __asm__ volatile (
        // 保存旧上下文
        "addi sp, sp, -32\n"
        "sw ra, 0(sp)\n"
        "sw s0, 4(sp)\n"
        "sw s1, 8(sp)\n"
        "sw s2, 12(sp)\n"
        "sw s3, 16(sp)\n"
        "sw s4, 20(sp)\n"
        "sw s5, 24(sp)\n"
        "sw s6, 28(sp)\n"

        // 切换栈指针
        "sw sp, 0(a0)\n"
        "lw sp, 0(a1)\n"

        // 恢复新上下文
        "lw ra, 0(sp)\n"
        "lw s0, 4(sp)\n"
        "lw s1, 8(sp)\n"
        "lw s2, 12(sp)\n"
        "lw s3, 16(sp)\n"
        "lw s4, 20(sp)\n"
        "lw s5, 24(sp)\n"
        "lw s6, 28(sp)\n"
        "addi sp, sp, 32\n"

        "ret\n"
    );
}
```

---

## 五、调度器优化

### 5.1 延迟调度

```c
// 延迟调度(减少上下文切换)
void vTaskDelay(TickType_t xTicksToDelay) {
    // 将任务从就绪表移到延迟表
    vListRemove(&pxCurrentTCB->xStateListItem);

    // 设置唤醒时间
    listSET_LIST_ITEM_VALUE(&pxCurrentTCB->xStateListItem,
                            xTickCount + xTicksToDelay);

    // 插入延迟表(按唤醒时间排序)
    vListInsert(&xDelayedTaskList, &pxCurrentTCB->xStateListItem);

    // 触发调度
    taskYIELD();
}
```

---

### 5.2 空闲任务处理

```c
// 空闲任务钩子
void vApplicationIdleHook(void) {
    // 进入低功耗模式
    __WFI();
}

// 空闲任务(最低优先级)
void vTaskIdle(void *pvParameters) {
    for (;;) {
        // 清理已删除任务的内存
        prvCheckTasksWaitingTermination();

        // 调用空闲钩子
        #if (configUSE_IDLE_HOOK == 1)
        vApplicationIdleHook();
        #endif
    }
}
```

---

## 六、多核调度

### 6.1 对称多处理(SMP)

```c
// SMP调度(ESP32双核)
/*
 * 两个核心共享就绪表
 * 每个核心独立运行任务
 * 需要自旋锁保护共享数据
 */

// 核心亲和性
typedef struct {
    TaskHandle_t task;
    BaseType_t core_id;  // 绑定到特定核心
} task_affinity_t;

void vTaskCoreAffinitySet(TaskHandle_t xTask, BaseType_t xCoreID) {
    // 设置任务可运行的核心掩码
    taskENTER_CRITICAL();
    pxTCB->xCoreID = xCoreID;
    taskEXIT_CRITICAL();
}
```

---

## 附录：调度算法对比

| 算法 | 实时性 | 复杂度 | 公平性 | 应用 |
|------|--------|--------|--------|------|
| 抢占式优先级 | 高 | 低 | 低 | 实时系统 |
| 时间片轮转 | 中 | 低 | 高 | 通用系统 |
| EDF | 最高 | 高 | 中 | 硬实时 |
| RMS | 高 | 中 | 中 | 周期任务 |
| CFS | 中 | 高 | 高 | Linux |

---

## 相关链接

- [[FreeRTOS基础]] - FreeRTOS基础
- [[RT-Thread基础]] - RT-Thread
- [[Zephyr RTOS]] - Zephyr
- [[计算机组成原理]] - CPU架构
