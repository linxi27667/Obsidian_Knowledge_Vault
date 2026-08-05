---
created: 2026-07-15 00:00
updated: 2026-07-17 12:30
tags: [FreeRTOS, 任务, 启动]
project_root: E:/MCU/gaochang/Gc_Iot_Lift
---

# FreeRTOS 任务与启动流程（控制任务和通信任务并发协作）

## 核心概念

- ==控制任务必须周期稳定、执行短、不能等待网络==。
- ==DTU 任务允许等待 AT 响应，但不能占用控制任务==。
- 任务栈参数在 Cortex-M4 FreeRTOS 中以 `StackType_t` 个数计，1024 words 通常是 4096 字节。
- ==大剪 1 ms；小剪/超薄/两柱 10 ms==。

## 一、四机型任务实表

### 1.1 大剪 `GC_Big_Scissor/Core/Src/freertos.c`

| 任务 | 创建 | 栈 | 优先级 | 周期 | 入口 |
|---|---|---|---|---|---|
| `defaultTask` | `osThreadNew` | 128×4=512B | Normal | `osDelay(1)` 空转 | CubeMX 占位 |
| `lift` | `Lift_Task_Create` | **1024 words** | `tskIDLE+3` | **1 ms** | `Driver/Src/dri_lift.c` |
| TAS DTU | `TasDtu_Task_Create` | **4096 words** | `tskIDLE+1` | RX 20 ms / error 1 s | `Driver/Src/dri_tas_dtu.c` |

注释未运行：`Debug_Task_Create`、旧 `Control/Safety/Key_Task_Create`。

### 1.2 小剪 `GC_Small_Scissor/Core/Src/freertos.c`

| 任务 | 创建 | 栈 | 优先级 | 周期 | 内容 |
|---|---|---|---|---|---|
| `defaultTask` | `osThreadNew` | **512×4=2048B** | Normal | **10 ms** | 内嵌 `Dri_Lift_Task10ms()` + `LiftIot_Poll()` + LED |
| TAS DTU | `TasDtu_Task_Create` | 4096 words | tskIDLE+1 | 同其他 | 独立任务 |

**无独立 `lift` 任务**；举升逻辑跑在 `defaultTask` 内。

### 1.3 超薄 `GC_Thin_Scissor`

| 任务 | 栈 | 优先级 | 周期 |
|---|---|---|---|
| `defaultTask` | 128×4 | Normal | 空转 |
| `lift` | 1024 words | tskIDLE+3 | **10 ms** |
| TAS DTU | 4096 words | tskIDLE+1 | 同左 |

### 1.4 两柱 `GC-Two_Pillars`

| 任务 | 栈 | 优先级 | 周期 |
|---|---|---|---|
| `defaultTask` | 128×4 | Normal | 空转 |
| **RiseCounter Store** | **384 words** | tskIDLE+1 | 异步落盘 |
| `lift` | 1024 words | tskIDLE+3 | **10 ms** |
| TAS DTU | 4096 words | tskIDLE+1 | 同左 |

两柱独有：`App_RiseCounter_Task_Create` 写 W25Q journal。

## 二、DTU 任务宏

来源：`Driver/Inc/dri_tas_dtu.h`

| 宏 | 值 |
|---|---|
| `TAS_DTU_TASK_STACK_SIZE_WORDS` | 4096 |
| `TAS_DTU_TASK_PRIORITY` | tskIDLE+1 |
| `TAS_DTU_REPORT_PERIOD_MS` | 5000（静止） |
| `TAS_DTU_REPORT_PERIOD_MOTION_MS` | 1000（运动） |
| `TAS_DTU_RX_POLL_PERIOD_MS` | 20 |
| `TAS_DTU_ERROR_RX_POLL_PERIOD_MS` | 1000 |
| `TAS_DTU_RETRY_PERIOD_MS` | 60000 |
| `TAS_DTU_ERROR_RETRY_PERIOD_MS` | 300000 |

## 三、main 初始化顺序

### 3.1 大剪

```text
HAL_Init → SystemClock_Config (HSI→PLL 168MHz)
→ MX_GPIO / DMA / TIM1 / SPI1 / USART3 / USART6
→ RTT + elog
→ App_Product_PrintUID
→ App_BootLedSelfTest          // 大剪独有
→ App_W25Qxx_System_Init       // 同步 g_product_type
→ LiftLock_Init → LiftIot_Init
→ App_IO_Map_Init → LiftCore_Init
→ osKernelInitialize → MX_FREERTOS_Init → osKernelStart
```

### 3.2 小剪

```text
HAL_Init → Clock
→ MX_GPIO / DMA / USART3 / SPI1 / USART6   // 无 TIM1
→ RTT + elog → PrintUID
→ App_IO_Map_Init
→ App_W25Qxx_System_Init
→ LiftIot_Init
→ Dri_Lift_Init → App_LiftCore_Init        // 无 LiftCore_Init
→ osKernel...
```

### 3.3 超薄

```text
HAL_Init → Clock
→ MX_GPIO / DMA / SPI1 / USART3            // 无 TIM1、无 USART6
→ RTT + elog → PrintUID
→ App_W25Qxx_System_Init
→ LiftLock_Init → LiftIot_Init
→ App_IO_Map_Init → LiftCore_Init
→ osKernel...
```

### 3.4 两柱

```text
HAL_Init → Clock
→ MX_GPIO / DMA / TIM1 / SPI1 / USART3 / USART6
→ RTT + elog → PrintUID
→ App_W25Qxx_System_Init
→ LiftLock_Init → LiftIot_Init
→ App_IO_Map_Init → LiftCore_Init
→ App_RiseCounter_Init                     // scheduler 前
→ osKernel...
```

main 中统一注释已移除：`Height_Load / Motor_Init / Safety_Init / Key_Init / Encoder_Init / RS485_Init`。

## 四、Lift_Task 主循环

大剪/超薄/两柱 `dri_lift.c`：

```c
while (1) {
    LiftCore_Poll();
    LiftIot_Poll();
    LiftIot_Snapshot(...);
    App_RiseCounter_Poll(...);   // 大剪/两柱
    // RUN/COM LED
    vTaskDelayUntil(&last_wake_tick, pdMS_TO_TICKS(LIFT_TASK_PERIOD_MS));
}
```

小剪 `defaultTask`：

```c
// 每 10ms
Dri_Lift_Task10ms();  // → App_LiftCore_Task
LiftIot_Poll();
// LED by state
```

为什么使用 `vTaskDelayUntil`：下一次唤醒基于上一次计划时间，偶发超时不会持续漂移。

## 五、TasDtu_Task 主职责

1. 上电等待约 3 s，给 DTU 和蜂窝网络启动时间。
2. `App_TasDtu_Init()` 初始化 USART3、DMA、FIFO。
3. `App_TasDtu_StartMqtt()` 尝试复用已保存配置，失败才重新配置。
4. 循环 `App_TasDtu_ProcessRx()`。
5. 按事件/周期策略上传（静止 5 s，运动 1 s）。
6. 错误状态按 60 s / 300 s 节流重试。

## 六、内存与栈保护

- `configCHECK_FOR_STACK_OVERFLOW = 2`（至少小剪明确配置）
- `vApplicationStackOverflowHook()`：关闭全部输出、打印任务名和堆信息、停机
- `vApplicationMallocFailedHook()`：关闭全部输出、记录剩余堆、停机
- `xPortGetMinimumEverFreeHeapSize()` 观察历史最低余量

来源：`*/Core/Src/freertos.c`、`GC_Small_Scissor/Core/Inc/FreeRTOSConfig.h`

## 七、实时性分析

```text
最坏响应时间 ≈ 输入去抖时间 + 最长控制周期 + 高优先级阻塞/临界区时间
```

普通按键 20 ms 去抖 + 10 ms 控制周期 → 逻辑确认通常 20～30 ms；真实结果必须实测。急停去抖也是 20 ms。

## 八、当前架构值得追问的点

- 大剪 1 ms 是否确有机械/安全需求，CPU 占用是否测量？
- `app_tas_dtu.c` 部分 AT 交互阻塞，是否影响共享 UART 临界区？
- 四工程堆配置不完全一致，是否都验证过 DTU JSON 最坏栈水位？
- CubeMX 默认任务用 CMSIS-RTOS2，业务任务用原生 FreeRTOS API，是混合模式。

## 九、答辩表达

> 我把本地控制和网络通信放在不同任务中。控制任务使用 `vTaskDelayUntil` 保持固定周期，所有动作通过非阻塞状态机推进；DTU 的 AT 配置、接收解析和重连在独立任务中进行。因此网络抖动不会直接阻塞急停与动作状态机。小剪把控制放在 defaultTask 10 ms 循环里，大剪独立 lift 任务 1 ms，两柱额外有异步 RiseStore 任务写 Flash。
