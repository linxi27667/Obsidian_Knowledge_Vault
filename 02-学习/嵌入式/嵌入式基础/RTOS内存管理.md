# RTOS内存管理

## 核心概念

- **堆管理** - 动态内存分配
- **内存池** - 固定大小分配
- **栈管理** - 任务栈
- **内存保护** - MPU/MMU

---

## 一、堆管理策略

### 1.1 FreeRTOS堆实现

```c
// heap_1: 只分配不释放
void *pvPortMalloc(size_t size) {
    void *ptr = NULL;
    if (pucAlignedHeap + size < pucHeapEnd) {
        ptr = pucAlignedHeap;
        pucAlignedHeap += size;
    }
    return ptr;
}

// heap_4: 合并空闲块
typedef struct A_BLOCK_LINK {
    struct A_BLOCK_LINK *pxNextFreeBlock;
    size_t xBlockSize;
} BlockLink_t;

void *pvPortMalloc(size_t xWantedSize) {
    BlockLink_t *pxBlock, *pxPreviousBlock;

    // 对齐
    xWantedSize += heapSTRUCT_SIZE;
    if (xWantedSize & heapBYTE_ALIGNMENT_MASK) {
        xWantedSize += heapBYTE_ALIGNMENT - (xWantedSize & heapBYTE_ALIGNMENT_MASK);
    }

    // 遍历空闲链表
    pxPreviousBlock = &xStart;
    pxBlock = xStart.pxNextFreeBlock;

    while (pxBlock->xBlockSize < xWantedSize && pxBlock->pxNextFreeBlock != NULL) {
        pxPreviousBlock = pxBlock;
        pxBlock = pxBlock->pxNextFreeBlock;
    }

    if (pxBlock->xBlockSize >= xWantedSize) {
        // 分割块
        if (pxBlock->xBlockSize - xWantedSize > heapMINIMUM_BLOCK_SIZE) {
            BlockLink_t *pxNewBlock = (void *)((uint8_t *)pxBlock + xWantedSize);
            pxNewBlock->xBlockSize = pxBlock->xBlockSize - xWantedSize;
            pxBlock->xBlockSize = xWantedSize;
            vInsertBlockIntoFreeList(pxNewBlock);
        }

        pxPreviousBlock->pxNextFreeBlock = pxBlock->pxNextFreeBlock;
        pxBlock->pxNextFreeBlock = NULL;
    }

    return (void *)(((uint8_t *)pxBlock) + heapSTRUCT_SIZE);
}

void vPortFree(void *pv) {
    BlockLink_t *pxBlock = (BlockLink_t *)((uint8_t *)pv - heapSTRUCT_SIZE);
    vInsertBlockIntoFreeList(pxBlock);
}
```

---

### 1.2 内存池

```c
// 固定大小内存池
typedef struct pool_block {
    struct pool_block *next;
} pool_block_t;

typedef struct {
    pool_block_t *free_list;
    uint8_t *memory;
    size_t block_size;
    size_t block_count;
    size_t allocated;
} memory_pool_t;

void pool_init(memory_pool_t *pool, void *mem, size_t block_size, size_t count) {
    pool->memory = (uint8_t *)mem;
    pool->block_size = block_size;
    pool->block_count = count;
    pool->allocated = 0;
    pool->free_list = NULL;

    // 构建空闲链表
    for (size_t i = 0; i < count; i++) {
        pool_block_t *block = (pool_block_t *)(pool->memory + i * block_size);
        block->next = pool->free_list;
        pool->free_list = block;
    }
}

void *pool_alloc(memory_pool_t *pool) {
    if (pool->free_list == NULL) return NULL;

    pool_block_t *block = pool->free_list;
    pool->free_list = block->next;
    pool->allocated++;

    return block;
}

void pool_free(memory_pool_t *pool, void *ptr) {
    pool_block_t *block = (pool_block_t *)ptr;
    block->next = pool->free_list;
    pool->free_list = block;
    pool->allocated--;
}

// 使用示例
#define POOL_BLOCK_SIZE 64
#define POOL_BLOCK_COUNT 32

static uint8_t pool_memory[POOL_BLOCK_SIZE * POOL_BLOCK_COUNT];
static memory_pool_t my_pool;

void example(void) {
    pool_init(&my_pool, pool_memory, POOL_BLOCK_SIZE, POOL_BLOCK_COUNT);

    void *ptr = pool_alloc(&my_pool);
    // 使用内存...
    pool_free(&my_pool, ptr);
}
```

---

## 二、栈管理

### 2.1 任务栈

```c
// 任务栈配置
#define TASK_STACK_SIZE 256  // 字

// 栈溢出检测
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName) {
    // 栈溢出处理
    printf("Stack overflow in task: %s\n", pcTaskName);
    while (1);
}

// 栈使用监控
void monitor_stack_usage(void) {
    TaskHandle_t task = xTaskGetCurrentTaskHandle();
    UBaseType_t high_water = uxTaskGetStackHighWaterMark(task);

    printf("Stack high water mark: %u words\n", high_water);

    if (high_water < 20) {
        printf("WARNING: Stack nearly full!\n");
    }
}
```

---

### 2.2 栈分析

```c
// 栈填充模式
#define STACK_FILL_PATTERN 0xA5A5A5A5

void fill_stack(uint32_t *stack, size_t size) {
    for (size_t i = 0; i < size; i++) {
        stack[i] = STACK_FILL_PATTERN;
    }
}

size_t calc_stack_usage(uint32_t *stack, size_t size) {
    size_t unused = 0;
    for (size_t i = 0; i < size; i++) {
        if (stack[i] == STACK_FILL_PATTERN) {
            unused++;
        } else {
            break;
        }
    }
    return (size - unused) * sizeof(uint32_t);
}
```

---

## 三、内存保护

### 3.1 MPU配置

```c
// MPU区域配置
typedef struct {
    uint32_t base;
    uint32_t size;
    uint32_t attributes;
} mpu_region_t;

void configure_mpu(void) {
    // Region 0: Flash(只读)
    MPU->RNR = 0;
    MPU->RBAR = 0x08000000;
    MPU->RASR = (17 << MPU_RASR_SIZE_Pos) |  // 512KB
                MPU_RASR_ENABLE_Msk |
                (3 << MPU_RASR_AP_Pos);       // 全访问

    // Region 1: RAM(读写)
    MPU->RNR = 1;
    MPU->RBAR = 0x20000000;
    MPU->RASR = (15 << MPU_RASR_SIZE_Pos) |  // 128KB
                MPU_RASR_ENABLE_Msk |
                (3 << MPU_RASR_AP_Pos);

    // Region 2: 外设(读写，无执行)
    MPU->RNR = 2;
    MPU->RBAR = 0x40000000;
    MPU->RASR = (23 << MPU_RASR_SIZE_Pos) |  // 16MB
                MPU_RASR_ENABLE_Msk |
                (3 << MPU_RASR_AP_Pos) |
                MPU_RASR_XN_Msk;              // 禁止执行

    // 使能MPU
    MPU->CTRL = MPU_CTRL_ENABLE_Msk | MPU_CTRL_PRIVDEFENA_Msk;
    __asm__ volatile ("dsb");
    __asm__ volatile ("isb");
}
```

---

## 四、内存调试

### 4.1 内存泄漏检测

```c
// 内存泄漏跟踪
typedef struct {
    void *ptr;
    size_t size;
    const char *file;
    int line;
    uint32_t timestamp;
} alloc_record_t;

#define MAX_RECORDS 100
static alloc_record_t alloc_records[MAX_RECORDS];
static int record_count = 0;

void *tracked_malloc(size_t size, const char *file, int line) {
    void *ptr = pvPortMalloc(size);
    if (ptr && record_count < MAX_RECORDS) {
        alloc_records[record_count].ptr = ptr;
        alloc_records[record_count].size = size;
        alloc_records[record_count].file = file;
        alloc_records[record_count].line = line;
        alloc_records[record_count].timestamp = get_tick();
        record_count++;
    }
    return ptr;
}

void tracked_free(void *ptr, const char *file, int line) {
    for (int i = 0; i < record_count; i++) {
        if (alloc_records[i].ptr == ptr) {
            // 移除记录
            alloc_records[i] = alloc_records[record_count - 1];
            record_count--;
            break;
        }
    }
    vPortFree(ptr);
}

// 检查泄漏
void check_memory_leaks(void) {
    if (record_count > 0) {
        printf("Memory leaks detected:\n");
        for (int i = 0; i < record_count; i++) {
            printf("  %p (%u bytes) at %s:%d\n",
                   alloc_records[i].ptr,
                   alloc_records[i].size,
                   alloc_records[i].file,
                   alloc_records[i].line);
        }
    }
}
```

---

## 附录：堆策略对比

| 策略 | 分配 | 释放 | 碎片 | 复杂度 |
|------|------|------|------|--------|
| heap_1 | O(1) | 不支持 | 无 | 低 |
| heap_2 | O(n) | O(1) | 有 | 中 |
| heap_4 | O(n) | O(n) | 合并 | 中 |
| heap_5 | O(n) | O(n) | 合并 | 高 |
| 内存池 | O(1) | O(1) | 无 | 低 |

---

## 相关链接

- [[FreeRTOS基础]] - FreeRTOS基础
- [[FreeRTOS进阶]] - FreeRTOS进阶
- [[可靠性工程]] - 内存保护
