# FreeRTOS 概述 （实时操作系统内核，提供任务调度、通信同步、内存管理等功能）

> 创建时间: 2026-05-06
> 来源: https://www.freertos.org/Documentation/00-Overview

## 核心概念

### FreeRTOS 是什么
- ==FreeRTOS是一个开源的实时操作系统内核== - 专为嵌入式设备设计，体积小、功耗低、可移植性强
- ==支持抢占式、协作式和时间片轮转调度== - 可根据应用场景选择合适的调度策略
- ==完全可移植== - 支持超过30种微控制器架构（ARM Cortex-M, RISC-V, Xtensa, MIPS等）

### 关键特性
- ==抢占式多任务调度== - 高优先级任务可以抢占低优先级任务
- ==任务间通信机制== - 队列、信号量、互斥量、事件组、任务通知
- ==软件定时器== - 提供一次性和周期性定时器功能
- ==内存管理== - 提供多种堆管理方案（heap_1 ~ heap_5）
- ==低功耗支持== - Tickless idle mode，适合电池供电设备
- ==可配置性== - 通过FreeRTOSConfig.h裁剪功能和资源占用

### 架构特点
- ==内核小巧== - 典型ROM占用约9KB，RAM占用极小
- ==模块化设计== - 可选择性编译所需功能模块
- ==中断管理== - 提供中断安全API和延迟中断处理机制
- ==无特权模式支持== - 可选MPU保护，增强系统安全性

---

## 调度器

### 调度方式
FreeRTOS支持三种调度策略：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| 抢占式调度 | 高优先级任务就绪时立即抢占CPU | 实时性要求高的场景 |
| 协作式调度 | 任务主动让出CPU后才切换 | 简单应用，功耗敏感 |
| 时间片轮转 | 同优先级任务轮流执行固定时间片 | 同优先级多任务公平执行 |

### 调度器生命周期

```c
// 1. 创建任务
xTaskCreate(prvTaskCode, "TaskName", STACK_SIZE, NULL, PRIORITY, NULL);

// 2. 启动调度器
vTaskStartScheduler();

// 3. 调度器运行中 - 任务按优先级调度
// 4. 可选：停止调度器（极少使用）
vTaskEndScheduler();
```

### 时间片机制
- ==配置宏==: `configUSE_TIME_SLICING` (默认启用)
- 同优先级任务在tick中断时切换
- 可通过 `portTICK_PERIOD_MS` 获取tick周期

---

## 任务管理

### 任务状态机

每个任务在其生命周期内处于以下状态之一：

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| Running | 正在CPU上执行 | 被调度器选中 |
| Ready | 准备运行，等待CPU | 高优先级任务占用CPU |
| Blocked | 等待事件/超时 | 等待队列、延迟、等待信号量 |
| Suspended | 暂停执行 | 调用 `vTaskSuspend()` |

### 任务创建与管理

```c
BaseType_t xTaskCreate(
    TaskFunction_t pvTaskCode,
    const char * const pcName,
    configSTACK_DEPTH_TYPE usStackDepth,
    void * const pvParameters,
    UBaseType_t uxPriority,
    TaskHandle_t * const pxCreatedTask
);
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `pvTaskCode` | `TaskFunction_t` | 任务函数指针 |
| `pcName` | `const char *` | 任务名称（调试用，最多`configMAX_TASK_NAME_LEN`字符） |
| `usStackDepth` | `configSTACK_DEPTH_TYPE` | 栈深度（单位：字/word，非字节） |
| `pvParameters` | `void *` | 传递给任务的参数指针 |
| `uxPriority` | `UBaseType_t` | 任务优先级（0 ~ `configMAX_PRIORITIES`-1） |
| `pxCreatedTask` | `TaskHandle_t *` | 输出参数，返回任务句柄（可设为NULL） |

**返回值**: `BaseType_t` — `pdPASS`表示创建成功，`errCOULD_NOT_ALLOCATE_REQUIRED_MEMORY`表示内存不足

**注意事项**:
- 优先级数值越大，优先级越高
- 空闲任务（Idle task）优先级最低（0）
- 栈深度需根据任务实际使用量确定，可通过 `uxTaskGetStackHighWaterMark()` 检查

### 任务相关API

| 函数 | 说明 |
|------|------|
| `xTaskCreate()` | 创建任务 |
| `vTaskDelete()` | 删除任务 |
| `vTaskDelay()` | 任务延时（相对时间） |
| `vTaskDelayUntil()` | 任务延时到绝对时间点 |
| `vTaskSuspend()` | 挂起任务 |
| `vTaskResume()` | 恢复任务 |
| `vTaskPrioritySet()` | 设置任务优先级 |
| `eTaskGetState()` | 获取任务状态 |

---

## 临界区与锁

### 临界区保护

```c
// 方法1：任务级临界区
taskENTER_CRITICAL();
    // 临界区代码（不能调用可能阻塞的API）
taskEXIT_CRITICAL();

// 方法2：任务级临界区（可嵌套）
taskENTER_CRITICAL_FROM_ISR();
    // 临界区代码
taskEXIT_CRITICAL_FROM_ISR();
```

### 调度器锁

```c
vTaskSuspendAll();      // 挂起调度器（不禁止中断）
    // 可调用不阻塞的API
xTaskResumeAll();       // 恢复调度器
```

### 区别

| 方法 | 中断 | 调度 | 适用场景 |
|------|------|------|----------|
| `taskENTER_CRITICAL` | 禁止中断 | 禁止切换 | 极短临界区 |
| `vTaskSuspendAll` | 不禁止 | 禁止切换 | 较长临界区 |

---

## 内存管理

### 堆管理方案

FreeRTOS提供5种堆管理策略：

| 方案 | 分配 | 释放 | 特点 | 适用场景 |
|------|------|------|------|----------|
| heap_1 | pvPortMalloc | 不可释放 | 最简单，无碎片 | 运行期不删除对象 |
| heap_2 | pvPortMalloc | vPortFree | 最佳适配，有碎片 | 分配大小差异大 |
| heap_3 | malloc | free | 封装标准库，线程安全 | 已有成熟堆管理 |
| heap_4 | pvPortMalloc | vPortFree | 首次适配+合并，减少碎片 | 通用场景 |
| heap_5 | pvPortMalloc | vPortFree | 支持多内存区域 | 复杂内存布局 |

### 内存申请

```c
// 动态创建任务（使用堆内存）
xTaskCreate(...);  // 内部调用pvPortMalloc分配TCB和栈

// 手动内存分配
void *pvBuffer = pvPortMalloc(1024);
if (pvBuffer != NULL) {
    // 使用缓冲区
    vPortFree(pvBuffer);
}
```

---

## 钩子函数

### 支持的钩子

| 钩子函数 | 调用时机 | 配置宏 |
|----------|----------|--------|
| `vApplicationIdleHook()` | 空闲任务每次执行 | `configUSE_IDLE_HOOK` |
| `vApplicationTickHook()` | 每次tick中断 | `configUSE_TICK_HOOK` |
| `vApplicationMallocFailedHook()` | 内存分配失败 | `configUSE_MALLOC_FAILED_HOOK` |
| `vApplicationDaemonTaskStartupHook()` | RTOS守护任务启动 | `configUSE_DAEMON_TASK_STARTUP_HOOK` |
| `vApplicationStackOverflowHook()` | 栈溢出检测触发 | `configCHECK_FOR_STACK_OVERFLOW` |

### 示例

```c
void vApplicationIdleHook(void)
{
    // 进入低功耗模式
    __WFI();  // Wait For Interrupt
}
```

---

## 附录：FreeRTOS API 速查表

### 任务管理
| 函数 | 说明 |
|------|------|
| `xTaskCreate()` | 创建任务 |
| `vTaskDelete()` | 删除任务 |
| `vTaskDelay()` | 相对延时 |
| `vTaskDelayUntil()` | 绝对延时 |
| `vTaskSuspend()` | 挂起任务 |
| `vTaskResume()` | 恢复任务 |

### 调度器控制
| 函数 | 说明 |
|------|------|
| `vTaskStartScheduler()` | 启动调度器 |
| `vTaskEndScheduler()` | 停止调度器 |
| `vTaskSuspendAll()` | 挂起调度器 |
| `xTaskResumeAll()` | 恢复调度器 |
| `taskENTER_CRITICAL()` | 进入临界区 |
| `taskEXIT_CRITICAL()` | 退出临界区 |

### 内存管理
| 函数 | 说明 |
|------|------|
| `pvPortMalloc()` | 分配内存 |
| `vPortFree()` | 释放内存 |
| `xPortGetFreeHeapSize()` | 获取剩余堆大小 |
| `xPortGetMinimumEverFreeHeapSize()` | 获取历史最小剩余堆 |

### 时间
| 函数 | 说明 |
|------|------|
| `xTaskGetTickCount()` | 获取tick计数 |
| `xTaskGetTickCountFromISR()` | 中断中获取tick计数 |

---

## 相关笔记

- [[二、队列]] — 任务间通信
- [[三、信号量与互斥量]] — 同步机制
- [[四、事件组与任务通知]] — 轻量级同步
- [[五、软件定时器]] — 定时任务
- [[六、中断管理与低功耗]] — 中断与省电
- [[RTOS通信原语详解]] — 通信机制深入
- [[RTOS调度算法]] — 调度策略
- [[02、任务与FreeRTOS基础]] — ESP-IDF 中的 FreeRTOS 实战
- [[08、事件]] — LVGL 事件系统（依赖 RTOS 任务）
- [[../嵌入式基础/00-嵌入式学习路线图]] — 学习路线总览
