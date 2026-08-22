# C 语言高级编程详解

> **适用场景**：嵌入式系统开发、操作系统内核、高性能计算、系统级编程
> **前置知识**：C 语言基础语法、基本数据类型、函数、数组
> **最后更新**：2026-06-21

---

## 目录

- [[#一、指针深入]]
- [[#二、内存管理]]
- [[#三、结构体与联合体]]
- [[#四、预处理器]]
- [[#五、位运算]]
- [[#六、函数设计]]
- [[#七、数据结构实现]]
- [[#八、编译过程]]
- [[#九、调试技巧]]
- [[#十、嵌入式 C 特殊技巧]]

---

## 一、指针深入

### 1.1 指针的本质

指针是一个变量，其值为另一个变量的内存地址。在 32 位系统中指针占 4 字节，64 位系统中占 8 字节。

```c
int a = 42;
int *p = &a;    // p 存储 a 的地址
printf("%d\n", *p);  // 解引用，输出 42
```

### 1.2 多级指针

多级指针是指向指针的指针，常用于动态二维数组和函数参数传递。

```c
int a = 10;
int *p = &a;
int **pp = &p;   // 二级指针，指向指针 p

printf("%d\n", **pp);  // 输出 10

// 三级指针（实际项目中较少使用）
int ***ppp = &pp;
printf("%d\n", ***ppp);  // 输出 10
```

**动态二维数组示例**：

```c
int **create_2d_array(int rows, int cols) {
    int **arr = (int **)malloc(rows * sizeof(int *));
    if (!arr) return NULL;

    for (int i = 0; i < rows; i++) {
        arr[i] = (int *)malloc(cols * sizeof(int));
        if (!arr[i]) {
            // 回滚已分配的内存
            for (int j = 0; j < i; j++) free(arr[j]);
            free(arr);
            return NULL;
        }
    }
    return arr;
}

void free_2d_array(int **arr, int rows) {
    for (int i = 0; i < rows; i++) {
        free(arr[i]);
    }
    free(arr);
}
```

### 1.3 函数指针

函数指针存储函数的入口地址，是回调机制的基础。

```c
// 基本语法：返回类型 (*指针名)(参数列表)
int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }

int main() {
    int (*op)(int, int);  // 声明函数指针

    op = add;
    printf("%d\n", op(3, 5));  // 输出 8

    op = sub;
    printf("%d\n", op(3, 5));  // 输出 -2

    return 0;
}
```

**函数指针数组**（常用于状态机、命令分发）：

```c
typedef int (*operation_t)(int, int);

operation_t ops[] = { add, sub, mul, div_op };

// 通过索引调用
int result = ops[op_code](a, b);
```

**qsort 中的函数指针应用**：

```c
int compare_int(const void *a, const void *b) {
    return (*(int *)a - *(int *)b);
}

int arr[] = {5, 2, 8, 1, 9};
qsort(arr, 5, sizeof(int), compare_int);
```

### 1.4 指针数组 vs 数组指针

这是 C 语言中最容易混淆的概念之一。

```c
// 指针数组：数组的每个元素都是指针
int *ptr_arr[5];     // 5 个 int* 指针组成的数组

// 数组指针：指向一个数组的指针
int (*arr_ptr)[5];   // 指向含 5 个 int 的数组的指针
```

**区分技巧**：看 `*` 和 `[]` 的优先级。`[]` 优先级高于 `*`，所以：
- `int *p[5]` 中 `p` 先与 `[5]` 结合，是数组，每个元素是 `int*`
- `int (*p)[5]` 中 `p` 先与 `*` 结合，是指针，指向 `int[5]`

**实际应用**：

```c
// 指针数组：管理多个字符串
const char *names[] = {
    "Alice", "Bob", "Charlie", "David"
};
printf("%s\n", names[2]);  // "Charlie"

// 数组指针：遍历二维数组的一行
int matrix[3][4] = {{1,2,3,4}, {5,6,7,8}, {9,10,11,12}};
int (*row)[4] = matrix;    // row 指向第一行
printf("%d\n", row[1][2]); // 7（第二行第三列）
```

### 1.5 void 指针

`void *` 是通用指针，可以指向任何类型的数据，但不能直接解引用。

```c
void *vp;
int a = 10;
vp = &a;           // 合法，void* 可以接收任意类型指针
// printf("%d", *vp);  // 错误！void* 不能直接解引用
printf("%d", *(int *)vp);  // 正确，需要先强制类型转换

// 典型应用：通用内存操作
void *memcpy(void *dest, const void *src, size_t n);
void *malloc(size_t size);
```

### 1.6 const 指针

`const` 与指针的组合有三种形式，含义各不相同。

```c
int a = 10, b = 20;

// 1. 指向常量的指针：不能通过指针修改所指内容
const int *p1 = &a;
*p1 = 30;    // 错误！不能修改指向的值
p1 = &b;     // 合法，可以改变指向

// 2. 常量指针：指针本身不能被重新赋值
int *const p2 = &a;
*p2 = 30;    // 合法，可以修改指向的值
p2 = &b;     // 错误！不能改变指向

// 3. 指向常量的常量指针：都不能改
const int *const p3 = &a;
*p3 = 30;    // 错误
p3 = &b;     // 错误
```

**记忆口诀**：`const` 在 `*` 左边，修饰指向的内容；`const` 在 `*` 右边，修饰指针本身。

---

## 二、内存管理

### 2.1 C 程序内存布局

一个 C 程序在内存中分为以下区域（从低地址到高地址）：

| 区域 | 存储内容 | 生命周期 | 特点 |
|------|----------|----------|------|
| **代码区（.text）** | 编译后的机器指令 | 程序运行期间 | 只读，可共享 |
| **只读数据区（.rodata）** | const 常量、字符串字面量 | 程序运行期间 | 只读 |
| **已初始化数据区（.data）** | 已初始化的全局/静态变量 | 程序运行期间 | 可读写 |
| **未初始化数据区（.bss）** | 未初始化的全局/静态变量 | 程序运行期间 | 启动时清零 |
| **堆区（heap）** | 动态分配的内存 | 手动管理 | 向高地址增长 |
| **栈区（stack）** | 局部变量、函数参数、返回地址 | 函数调用期间 | 向低地址增长 |

```c
#include <stdio.h>

int global_init = 100;       // .data 区
int global_uninit;           // .bss 区
const int CONST_VAL = 42;    // .rodata 区
static int static_var = 10;  // .data 区

int main() {
    int local_var = 5;           // 栈区
    int *heap_var = malloc(100); // 堆区
    const char *str = "hello";   // .rodata 区

    printf("代码区:   %p\n", (void *)main);
    printf("只读数据: %p\n", (void *)str);
    printf("全局变量: %p\n", (void *)&global_init);
    printf("堆区:     %p\n", (void *)heap_var);
    printf("栈区:     %p\n", (void *)&local_var);

    free(heap_var);
    return 0;
}
```

### 2.2 动态内存分配函数

#### malloc

分配指定字节数的内存，不初始化。

```c
int *arr = (int *)malloc(n * sizeof(int));
if (arr == NULL) {
    // 分配失败处理
    perror("malloc failed");
    return -1;
}
```

#### calloc

分配内存并初始化为零。参数为元素个数和每个元素的大小。

```c
// 分配 n 个 int，全部初始化为 0
int *arr = (int *)calloc(n, sizeof(int));
```

#### realloc

调整已分配内存的大小。可能移动内存块到新位置。

```c
int *tmp = (int *)realloc(arr, new_size * sizeof(int));
if (tmp == NULL) {
    // realloc 失败，原内存 arr 仍然有效
    perror("realloc failed");
    // 不要 free(arr)，因为还需要用
} else {
    arr = tmp;  // 成功，更新指针
}
```

**realloc 注意事项**：
- 若新大小小于原大小，多余部分被截断
- 若新大小大于原大小，扩展的部分未初始化
- 若原位置空间不足，会分配新内存并拷贝旧数据，然后释放旧内存
- 若返回 NULL，原内存块不会被释放

#### free

释放动态分配的内存。

```c
free(arr);
arr = NULL;  // 好习惯：释放后置空，避免悬空指针
```

### 2.3 常见内存错误

| 错误类型 | 描述 | 后果 |
|----------|------|------|
| 内存泄漏 | malloc 后忘记 free | 程序内存持续增长 |
| 悬空指针 | free 后继续使用指针 | 未定义行为 |
| 双重释放 | 对同一块内存 free 两次 | 程序崩溃 |
| 越界访问 | 访问数组/缓冲区之外的内存 | 数据损坏、崩溃 |
| 使用未初始化指针 | 声明指针后直接使用 | 未定义行为 |

**经典内存泄漏示例**：

```c
void leaky_function() {
    int *p = (int *)malloc(100 * sizeof(int));
    if (some_error_condition) {
        return;  // 错误！直接返回导致内存泄漏
    }
    // ... 使用 p ...
    free(p);
}

// 修复版本
void fixed_function() {
    int *p = (int *)malloc(100 * sizeof(int));
    int ret = 0;

    if (some_error_condition) {
        ret = -1;
        goto cleanup;
    }
    // ... 使用 p ...

cleanup:
    free(p);
    return ret;
}
```

### 2.4 内存泄漏检测工具

```bash
# Valgrind（Linux）
valgrind --leak-check=full --show-leak-kinds=all ./program

# AddressSanitizer（GCC/Clang）
gcc -fsanitize=address -g program.c -o program
./program

# Visual Leak Detector（Windows Visual Studio）
# 在项目属性中启用
```

### 2.5 内存对齐

CPU 访问内存时按字长（4 或 8 字节）对齐访问效率最高。

```c
// 自然对齐规则
struct Example {
    char a;     // 1 字节，偏移 0
    // 3 字节填充
    int b;      // 4 字节，偏移 4
    char c;     // 1 字节，偏移 8
    // 7 字节填充（结构体总大小需是最大成员的整数倍）
};  // 总大小：16 字节（而非 6 字节）

// 调整顺序减少填充
struct Optimized {
    int b;      // 4 字节，偏移 0
    char a;     // 1 字节，偏移 4
    char c;     // 1 字节，偏移 5
    // 2 字节填充
};  // 总大小：8 字节
```

**查看对齐方式**：

```c
printf("size = %zu\n", sizeof(struct Example));     // 16
printf("offset a = %zu\n", offsetof(struct Example, a));  // 0
printf("offset b = %zu\n", offsetof(struct Example, b));  // 4
printf("offset c = %zu\n", offsetof(struct Example, c));  // 8
```

---

## 三、结构体与联合体

### 3.1 结构体基础与高级用法

```c
// 基本结构体
struct Point {
    double x;
    double y;
};

// 使用 typedef 简化
typedef struct {
    char name[32];
    int age;
    float score;
} Student;

// 结构体初始化
Student s1 = {"Alice", 20, 95.5};
Student s2 = {.name = "Bob", .age = 22};  // C99 指定初始化
```

### 3.2 位域（Bit Field）

位域允许按位分配结构体成员，常用于嵌入式寄存器映射和协议解析。

```c
// 嵌入式寄存器定义示例
typedef struct {
    uint8_t enable    : 1;  // 第 0 位
    uint8_t mode      : 2;  // 第 1-2 位
    uint8_t priority  : 3;  // 第 3-5 位
    uint8_t reserved  : 2;  // 第 6-7 位
} ControlReg;

ControlReg ctrl;
ctrl.enable = 1;
ctrl.mode = 2;
ctrl.priority = 5;

// 网络协议头解析
typedef struct {
    uint32_t version   : 4;
    uint32_t ihl       : 4;
    uint32_t tos       : 8;
    uint32_t total_len : 16;
} IPv4Header;
```

**位域注意事项**：
- 位域不能跨存储单元边界
- 位域成员类型必须是 `int`、`unsigned int`、`signed int`（C99 允许 `_Bool`）
- 位域的排列顺序依赖编译器（大端/小端）
- 不能对位域成员取地址

### 3.3 结构体对齐与填充

```c
// 使用 pragma 控制对齐
#pragma pack(push, 1)  // 设置 1 字节对齐
struct Packed {
    char a;
    int b;
    char c;
};  // 大小：6 字节（无填充）
#pragma pack(pop)      // 恢复默认对齐

// 使用 __attribute__ 控制对齐（GCC）
struct Aligned {
    char a;
    int b;
} __attribute__((aligned(8)));  // 强制 8 字节对齐
```

### 3.4 结构体 vs 联合体

```c
// 结构体：成员各自占用独立空间
struct StructExample {
    int a;      // 4 字节
    char b;     // 1 字节
    double c;   // 8 字节
};  // 总大小 ≥ 13 字节（含填充）

// 联合体：所有成员共享同一块内存
union UnionExample {
    int a;      // 4 字节
    char b;     // 1 字节
    double c;   // 8 字节
};  // 总大小 = 8 字节（最大成员的大小）
```

**联合体的经典应用 -- 类型双关（Type Punning）**：

```c
// 检测系统字节序
union EndianTest {
    uint32_t value;
    uint8_t bytes[4];
};

union EndianTest test = {.value = 0x01020304};
if (test.bytes[0] == 0x01) {
    printf("大端序\n");
} else {
    printf("小端序\n");
}

// 浮点数位级操作
union FloatBits {
    float f;
    uint32_t bits;
};

union FloatBits fb = {.f = 3.14f};
printf("符号位: %u\n", (fb.bits >> 31) & 1);
printf("指数:   %u\n", (fb.bits >> 23) & 0xFF);
printf("尾数:   0x%06X\n", fb.bits & 0x7FFFFF);
```

### 3.5 柔性数组（Flexible Array Member）

C99 引入，结构体最后一个成员可以是不指定大小的数组。

```c
typedef struct {
    int length;
    int capacity;
    int data[];     // 柔性数组成员，必须是最后一个成员
} IntVector;

IntVector *vector_create(int capacity) {
    IntVector *v = (IntVector *)malloc(
        sizeof(IntVector) + capacity * sizeof(int)
    );
    if (v) {
        v->length = 0;
        v->capacity = capacity;
    }
    return v;
}

void vector_push(IntVector *v, int value) {
    if (v->length < v->capacity) {
        v->data[v->length++] = value;
    }
}

void vector_destroy(IntVector *v) {
    free(v);  // 只需一次 free
}
```

**柔性数组 vs 指针成员**：

| 特性 | 柔性数组 `int data[]` | 指针成员 `int *data` |
|------|----------------------|---------------------|
| 内存分配次数 | 1 次 | 2 次（结构体 + 数组） |
| 缓存友好性 | 好（连续内存） | 差（两次跳转） |
| free 次数 | 1 次 | 2 次 |
| 结构体大小 | 不含柔性数组部分 | 包含指针大小 |

---

## 四、预处理器

### 4.1 宏定义技巧

```c
// 基本宏定义
#define PI 3.14159265358979
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))

// 带副作用的宏参数陷阱
#define MAX_BAD(a, b) ((a) > (b) ? (a) : (b))
int x = 5, y = 10;
int z = MAX_BAD(x++, y++);  // x 被自增了两次！

// 安全版本（使用 GCC 语句表达式）
#define MAX_SAFE(a, b) ({      \
    typeof(a) _a = (a);        \
    typeof(b) _b = (b);        \
    _a > _b ? _a : _b;        \
})

// do-while(0) 技巧：让宏可以像函数一样使用分号
#define LOG(msg) do {           \
    printf("[LOG] %s\n", msg);  \
} while (0)

if (condition)
    LOG("yes");    // 正确，不会出问题
else
    LOG("no");
```

### 4.2 字符串化与连接符

```c
// # 字符串化：将宏参数转为字符串
#define STRINGIFY(x) #x
printf("%s\n", STRINGIFY(hello world));  // "hello world"

// ## 连接符：将两个标记连接为一个
#define CONCAT(a, b) a##b
int var1 = 10;
printf("%d\n", CONCAT(var, 1));  // 输出 10

// 实际应用：自动生成变量名
#define REG(name) reg_##name
uint32_t REG(cr1);   // 等价于 uint32_t reg_cr1;
uint32_t REG(cr2);   // 等价于 uint32_t reg_cr2;
```

### 4.3 可变参数宏（__VA_ARGS__）

```c
// 基本用法
#define DEBUG(fmt, ...) \
    printf("[DEBUG %s:%d] " fmt "\n", __FILE__, __LINE__, ##__VA_ARGS__)

DEBUG("value = %d", 42);
// 输出: [DEBUG main.c:10] value = 42

// ##__VA_ARGS__ 中的 ## 作用：当可变参数为空时，去掉前面的逗号
#define LOG_INFO(fmt, ...) printf("[INFO] " fmt "\n", ##__VA_ARGS__)
LOG_INFO("system ready");  // 没有多余的逗号

// 多级日志宏
#define LOG(level, fmt, ...) \
    fprintf(stderr, "[%s] %s:%d: " fmt "\n", \
            level, __FILE__, __LINE__, ##__VA_ARGS__)

#define LOGE(fmt, ...) LOG("ERROR", fmt, ##__VA_ARGS__)
#define LOGW(fmt, ...) LOG("WARN",  fmt, ##__VA_ARGS__)
#define LOGI(fmt, ...) LOG("INFO",  fmt, ##__VA_ARGS__)
```

### 4.4 条件编译

```c
// 头文件保护
#ifndef MY_HEADER_H
#define MY_HEADER_H
// ... 头文件内容 ...
#endif

// 或使用 #pragma once（非标准但广泛支持）
#pragma once

// 平台检测
#if defined(_WIN32) || defined(_WIN64)
    #define PLATFORM_WINDOWS
#elif defined(__linux__)
    #define PLATFORM_LINUX
#elif defined(__APPLE__)
    #define PLATFORM_MACOS
#endif

// 调试/发布模式切换
#ifdef DEBUG
    #define ASSERT(cond) do { \
        if (!(cond)) { \
            fprintf(stderr, "ASSERT failed: %s at %s:%d\n", \
                    #cond, __FILE__, __LINE__); \
            abort(); \
        } \
    } while (0)
#else
    #define ASSERT(cond) ((void)0)
#endif

// 特性开关
#define FEATURE_USB  1
#define FEATURE_ETH  0
#define FEATURE_WIFI 1

#if FEATURE_USB
    void usb_init(void);
#endif
```

### 4.5 预定义宏

```c
printf("文件名: %s\n", __FILE__);
printf("行号:   %d\n", __LINE__);
printf("函数名: %s\n", __func__);      // C99
printf("日期:   %s\n", __DATE__);
printf("时间:   %s\n", __TIME__);
printf("编译器: %d\n", __STDC__);       // 1 表示符合标准
printf("C标准:  %ld\n", __STDC_VERSION__); // 201112L = C11
```

---

## 五、位运算

### 5.1 基本位运算操作符

| 操作符 | 名称 | 示例 | 结果 |
|--------|------|------|------|
| `&` | 按位与 | `0b1100 & 0b1010` | `0b1000` |
| `\|` | 按位或 | `0b1100 \| 0b1010` | `0b1110` |
| `^` | 按位异或 | `0b1100 ^ 0b1010` | `0b0110` |
| `~` | 按位取反 | `~0b1100` | `...11110011` |
| `<<` | 左移 | `0b0001 << 3` | `0b1000` |
| `>>` | 右移 | `0b1000 >> 2` | `0b0010` |

### 5.2 位操作常用技巧

```c
// 1. 判断奇偶
if (n & 1) { /* 奇数 */ }

// 2. 乘除 2 的幂
int doubled = n << 1;    // n * 2
int halved  = n >> 1;    // n / 2

// 3. 不用临时变量交换两数
a ^= b;
b ^= a;
a ^= b;

// 4. 检查第 n 位是否为 1
bool is_set = (value >> n) & 1;

// 5. 设置第 n 位为 1
value |= (1U << n);

// 6. 清除第 n 位（设为 0）
value &= ~(1U << n);

// 7. 翻转第 n 位
value ^= (1U << n);

// 8. 获取最低位的 1
int lowest = value & (-value);

// 9. 清除最低位的 1
value &= (value - 1);

// 10. 统计二进制中 1 的个数（Brian Kernighan 算法）
int count = 0;
while (n) {
    n &= (n - 1);
    count++;
}

// 11. 判断是否是 2 的幂
bool is_power_of_2 = (n > 0) && ((n & (n - 1)) == 0);

// 12. 对齐到 2 的幂的倍数
#define ALIGN_UP(x, align) (((x) + (align) - 1) & ~((align) - 1))
// align 必须是 2 的幂
```

### 5.3 掩码应用

```c
// 提取特定位段
#define EXTRACT(val, pos, width) \
    (((val) >> (pos)) & ((1U << (width)) - 1))

// 设置特定位段
#define SET_FIELD(val, pos, width, field) \
    ((val) = ((val) & ~(((1U << (width)) - 1) << (pos))) | \
             ((field) << (pos)))

// 示例：RGB565 颜色解析
uint16_t color = 0xF800;  // 红色
uint8_t r = EXTRACT(color, 11, 5);  // 高 5 位
uint8_t g = EXTRACT(color, 5, 6);   // 中 6 位
uint8_t b = EXTRACT(color, 0, 5);   // 低 5 位

// 寄存器操作
#define REG_CR   (*(volatile uint32_t *)0x40021000)

// 设置特定位
REG_CR |= (1 << 3);

// 清除特定位
REG_CR &= ~(1 << 5);

// 修改多位字段
REG_CR = (REG_CR & ~(0x7 << 8)) | (new_value << 8);
```

### 5.4 位域操作与寄存器映射

```c
// 方式一：使用位域
typedef struct {
    volatile uint32_t PE    : 1;  // 第 0 位
    volatile uint32_t MEM   : 1;  // 第 1 位
    volatile uint32_t BUS   : 1;  // 第 2 位
    volatile uint32_t USAGE : 1;  // 第 3 位
    volatile uint32_t       : 3;  // 保留
    volatile uint32_t NOC   : 1;  // 第 7 位
    volatile uint32_t       : 24; // 保留
} SHCSR_TypeDef;

// 方式二：使用掩码宏（更可移植）
#define SHCSR_PE_MASK     (1U << 0)
#define SHCSR_MEM_MASK    (1U << 1)
#define SHCSR_BUS_MASK    (1U << 2)
#define SHCSR_USAGE_MASK  (1U << 3)

#define SHCSR_SET(reg, mask)   ((reg) |= (mask))
#define SHCSR_CLR(reg, mask)   ((reg) &= ~(mask))
#define SHCSR_READ(reg, mask)  ((reg) & (mask))
```

---

## 六、函数设计

### 6.1 递归

递归函数直接或间接调用自身。必须有终止条件（base case）。

```c
// 阶乘
unsigned long long factorial(int n) {
    if (n <= 1) return 1;  // 终止条件
    return n * factorial(n - 1);
}

// 斐波那契（带记忆化优化）
#define MAX_N 100
static long long memo[MAX_N];

long long fibonacci(int n) {
    if (n <= 1) return n;
    if (memo[n] != 0) return memo[n];
    memo[n] = fibonacci(n - 1) + fibonacci(n - 2);
    return memo[n];
}

// 递归转迭代（避免栈溢出）
unsigned long long factorial_iter(int n) {
    unsigned long long result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

// 汉诺塔
void hanoi(int n, char from, char to, char aux) {
    if (n == 1) {
        printf("移动盘 %d: %c -> %c\n", n, from, to);
        return;
    }
    hanoi(n - 1, from, aux, to);
    printf("移动盘 %d: %c -> %c\n", n, from, to);
    hanoi(n - 1, aux, to, from);
}
```

### 6.2 回调函数

回调函数通过函数指针实现，是事件驱动和模块解耦的核心手段。

```c
// 事件回调示例
typedef void (*event_handler_t)(int event_type, void *data);

typedef struct {
    event_handler_t handler;
    void *user_data;
} EventListener;

void register_listener(EventListener *listener,
                       event_handler_t handler,
                       void *user_data) {
    listener->handler = handler;
    listener->user_data = user_data;
}

void dispatch_event(EventListener *listener, int event_type, void *data) {
    if (listener && listener->handler) {
        listener->handler(event_type, data);
    }
}

// 排序回调
typedef int (*compare_func_t)(const void *, const void *);

void bubble_sort(void *base, size_t count, size_t size,
                 compare_func_t cmp) {
    char *ptr = (char *)base;
    for (size_t i = 0; i < count - 1; i++) {
        for (size_t j = 0; j < count - 1 - i; j++) {
            if (cmp(ptr + j * size, ptr + (j + 1) * size) > 0) {
                // 交换
                for (size_t k = 0; k < size; k++) {
                    char tmp = ptr[j * size + k];
                    ptr[j * size + k] = ptr[(j + 1) * size + k];
                    ptr[(j + 1) * size + k] = tmp;
                }
            }
        }
    }
}
```

### 6.3 可变参数函数（va_list）

```c
#include <stdarg.h>

// 求平均值
double average(int count, ...) {
    va_list args;
    va_start(args, count);  // 初始化，count 是最后一个固定参数

    double sum = 0;
    for (int i = 0; i < count; i++) {
        sum += va_arg(args, double);  // 逐个获取参数
    }

    va_end(args);  // 清理
    return sum / count;
}

printf("avg = %.2f\n", average(3, 1.0, 2.0, 3.0));  // 2.00

// 自定义 printf 封装
void my_printf(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);

    char buffer[1024];
    vsnprintf(buffer, sizeof(buffer), fmt, args);
    printf("[LOG] %s", buffer);

    va_end(args);
}
```

### 6.4 内联函数（inline）

```c
// inline 建议编译器将函数调用替换为函数体，减少调用开销
static inline int square(int x) {
    return x * x;
}

// static inline 在头文件中定义可以避免多重定义错误
// 适用于短小且频繁调用的函数

// 对比宏和内联函数
#define SQUARE_MACRO(x) ((x) * (x))     // 无类型检查，可能有副作用
static inline int square_inline(int x) { // 有类型检查，安全
    return x * x;
}

// 内联函数注意事项
// 1. inline 只是建议，编译器可能忽略
// 2. 递归函数通常不会被内联
// 3. 函数体过大会导致代码膨胀
// 4. 配合 -O2 优化级别效果最好
```

---

## 七、数据结构实现

### 7.1 单链表

```c
#include <stdio.h>
#include <stdlib.h>

typedef struct Node {
    int data;
    struct Node *next;
} Node;

// 创建节点
Node *node_create(int data) {
    Node *node = (Node *)malloc(sizeof(Node));
    if (node) {
        node->data = data;
        node->next = NULL;
    }
    return node;
}

// 头插法
void list_push_front(Node **head, int data) {
    Node *node = node_create(data);
    if (node) {
        node->next = *head;
        *head = node;
    }
}

// 尾插法
void list_push_back(Node **head, int data) {
    Node *node = node_create(data);
    if (!node) return;

    if (*head == NULL) {
        *head = node;
        return;
    }
    Node *curr = *head;
    while (curr->next) {
        curr = curr->next;
    }
    curr->next = node;
}

// 删除指定值的节点
void list_remove(Node **head, int data) {
    Node *curr = *head;
    Node *prev = NULL;

    while (curr) {
        if (curr->data == data) {
            if (prev) {
                prev->next = curr->next;
            } else {
                *head = curr->next;
            }
            free(curr);
            return;
        }
        prev = curr;
        curr = curr->next;
    }
}

// 反转链表
Node *list_reverse(Node *head) {
    Node *prev = NULL;
    Node *curr = head;
    while (curr) {
        Node *next = curr->next;
        curr->next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}

// 释放链表
void list_destroy(Node *head) {
    while (head) {
        Node *next = head->next;
        free(head);
        head = next;
    }
}

// 打印链表
void list_print(Node *head) {
    while (head) {
        printf("%d -> ", head->data);
        head = head->next;
    }
    printf("NULL\n");
}
```

### 7.2 栈（基于数组）

```c
#define STACK_MAX_SIZE 100

typedef struct {
    int data[STACK_MAX_SIZE];
    int top;  // 栈顶索引，-1 表示空栈
} Stack;

void stack_init(Stack *s) {
    s->top = -1;
}

bool stack_is_empty(Stack *s) {
    return s->top == -1;
}

bool stack_is_full(Stack *s) {
    return s->top == STACK_MAX_SIZE - 1;
}

bool stack_push(Stack *s, int value) {
    if (stack_is_full(s)) return false;
    s->data[++s->top] = value;
    return true;
}

bool stack_pop(Stack *s, int *value) {
    if (stack_is_empty(s)) return false;
    *value = s->data[s->top--];
    return true;
}

bool stack_peek(Stack *s, int *value) {
    if (stack_is_empty(s)) return false;
    *value = s->data[s->top];
    return true;
}
```

### 7.3 队列（基于数组的循环队列）

```c
#define QUEUE_MAX_SIZE 100

typedef struct {
    int data[QUEUE_MAX_SIZE];
    int front;  // 队头索引
    int rear;   // 队尾索引
    int count;  // 当前元素个数
} Queue;

void queue_init(Queue *q) {
    q->front = 0;
    q->rear = -1;
    q->count = 0;
}

bool queue_is_empty(Queue *q) {
    return q->count == 0;
}

bool queue_is_full(Queue *q) {
    return q->count == QUEUE_MAX_SIZE;
}

bool queue_enqueue(Queue *q, int value) {
    if (queue_is_full(q)) return false;
    q->rear = (q->rear + 1) % QUEUE_MAX_SIZE;
    q->data[q->rear] = value;
    q->count++;
    return true;
}

bool queue_dequeue(Queue *q, int *value) {
    if (queue_is_empty(q)) return false;
    *value = q->data[q->front];
    q->front = (q->front + 1) % QUEUE_MAX_SIZE;
    q->count--;
    return true;
}
```

### 7.4 哈希表

```c
#define HASH_TABLE_SIZE 128

typedef struct HashNode {
    char *key;
    int value;
    struct HashNode *next;  // 链地址法处理冲突
} HashNode;

typedef struct {
    HashNode *buckets[HASH_TABLE_SIZE];
} HashTable;

// 简单的 DJB2 哈希函数
unsigned long hash_function(const char *key) {
    unsigned long hash = 5381;
    int c;
    while ((c = *key++)) {
        hash = ((hash << 5) + hash) + c;  // hash * 33 + c
    }
    return hash % HASH_TABLE_SIZE;
}

HashTable *ht_create(void) {
    HashTable *ht = (HashTable *)calloc(1, sizeof(HashTable));
    return ht;
}

void ht_insert(HashTable *ht, const char *key, int value) {
    unsigned long idx = hash_function(key);

    // 检查键是否已存在
    HashNode *curr = ht->buckets[idx];
    while (curr) {
        if (strcmp(curr->key, key) == 0) {
            curr->value = value;  // 更新
            return;
        }
        curr = curr->next;
    }

    // 插入新节点（头插法）
    HashNode *node = (HashNode *)malloc(sizeof(HashNode));
    node->key = strdup(key);
    node->value = value;
    node->next = ht->buckets[idx];
    ht->buckets[idx] = node;
}

bool ht_get(HashTable *ht, const char *key, int *value) {
    unsigned long idx = hash_function(key);
    HashNode *curr = ht->buckets[idx];

    while (curr) {
        if (strcmp(curr->key, key) == 0) {
            *value = curr->value;
            return true;
        }
        curr = curr->next;
    }
    return false;
}

void ht_destroy(HashTable *ht) {
    for (int i = 0; i < HASH_TABLE_SIZE; i++) {
        HashNode *curr = ht->buckets[i];
        while (curr) {
            HashNode *next = curr->next;
            free(curr->key);
            free(curr);
            curr = next;
        }
    }
    free(ht);
}
```

### 7.5 二叉树

```c
typedef struct TreeNode {
    int data;
    struct TreeNode *left;
    struct TreeNode *right;
} TreeNode;

TreeNode *tree_create_node(int data) {
    TreeNode *node = (TreeNode *)malloc(sizeof(TreeNode));
    if (node) {
        node->data = data;
        node->left = NULL;
        node->right = NULL;
    }
    return node;
}

// BST 插入
TreeNode *bst_insert(TreeNode *root, int data) {
    if (root == NULL) return tree_create_node(data);

    if (data < root->data) {
        root->left = bst_insert(root->left, data);
    } else if (data > root->data) {
        root->right = bst_insert(root->right, data);
    }
    return root;
}

// BST 查找
TreeNode *bst_search(TreeNode *root, int data) {
    if (root == NULL || root->data == data) return root;
    if (data < root->data)
        return bst_search(root->left, data);
    return bst_search(root->right, data);
}

// 前序遍历（根-左-右）
void preorder(TreeNode *root) {
    if (root == NULL) return;
    printf("%d ", root->data);
    preorder(root->left);
    preorder(root->right);
}

// 中序遍历（左-根-右），对 BST 会输出有序序列
void inorder(TreeNode *root) {
    if (root == NULL) return;
    inorder(root->left);
    printf("%d ", root->data);
    inorder(root->right);
}

// 后序遍历（左-右-根）
void postorder(TreeNode *root) {
    if (root == NULL) return;
    postorder(root->left);
    postorder(root->right);
    printf("%d ", root->data);
}

// 释放树（后序方式释放）
void tree_destroy(TreeNode *root) {
    if (root == NULL) return;
    tree_destroy(root->left);
    tree_destroy(root->right);
    free(root);
}

// 计算树的高度
int tree_height(TreeNode *root) {
    if (root == NULL) return 0;
    int left_h = tree_height(root->left);
    int right_h = tree_height(root->right);
    return 1 + (left_h > right_h ? left_h : right_h);
}

// BST 删除
TreeNode *bst_delete(TreeNode *root, int data) {
    if (root == NULL) return NULL;

    if (data < root->data) {
        root->left = bst_delete(root->left, data);
    } else if (data > root->data) {
        root->right = bst_delete(root->right, data);
    } else {
        // 找到要删除的节点
        if (root->left == NULL) {
            TreeNode *temp = root->right;
            free(root);
            return temp;
        } else if (root->right == NULL) {
            TreeNode *temp = root->left;
            free(root);
            return temp;
        }
        // 有两个子节点：用中序后继替换
        TreeNode *successor = root->right;
        while (successor->left) {
            successor = successor->left;
        }
        root->data = successor->data;
        root->right = bst_delete(root->right, successor->data);
    }
    return root;
}
```

---

## 八、编译过程

### 8.1 编译四阶段

```
源文件(.c) --> [预处理] --> 预处理后的文件(.i)
    --> [编译] --> 汇编文件(.s)
    --> [汇编] --> 目标文件(.o)
    --> [链接] --> 可执行文件
```

```bash
# 1. 预处理：展开宏、处理 #include、条件编译
gcc -E main.c -o main.i

# 2. 编译：将 C 代码转换为汇编代码
gcc -S main.i -o main.s

# 3. 汇编：将汇编代码转换为机器码（目标文件）
gcc -c main.s -o main.o

# 4. 链接：将多个目标文件和库合并为可执行文件
gcc main.o utils.o -o program

# 一步到位
gcc -Wall -Wextra -O2 main.c utils.c -o program
```

### 8.2 静态库 vs 动态库

| 特性 | 静态库（.a / .lib） | 动态库（.so / .dll） |
|------|---------------------|---------------------|
| 链接时机 | 编译时 | 运行时 |
| 文件大小 | 较大（包含库代码副本） | 较小 |
| 运行速度 | 略快（无需加载） | 略慢（需动态加载） |
| 更新方式 | 需重新编译 | 替换 .so 文件即可 |
| 内存占用 | 每个程序独立副本 | 多进程可共享 |

**创建和使用静态库**：

```bash
# 编译为目标文件
gcc -c math_utils.c -o math_utils.o
gcc -c string_utils.c -o string_utils.o

# 打包为静态库
ar rcs libmyutils.a math_utils.o string_utils.o

# 使用静态库
gcc main.c -L. -lmyutils -o program
```

**创建和使用动态库**：

```bash
# 编译为位置无关的目标文件
gcc -fPIC -c math_utils.c -o math_utils.o

# 创建动态库
gcc -shared math_utils.o -o libmyutils.so

# 使用动态库
gcc main.c -L. -lmyutils -o program

# 运行时需要设置库路径
export LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH
./program
```

### 8.3 Makefile 编写

```makefile
# 基本变量定义
CC = gcc
CFLAGS = -Wall -Wextra -O2 -g
LDFLAGS =
TARGET = myprogram

# 源文件和目标文件
SRCS = main.c utils.c parser.c
OBJS = $(SRCS:.c=.o)

# 默认目标
all: $(TARGET)

# 链接
$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

# 编译规则：.c -> .o
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 自动依赖生成
-include $(OBJS:.o=.d)

%.o: %.c
	$(CC) $(CFLAGS) -MMD -c $< -o $@

# 清理
clean:
	rm -f $(OBJS) $(OBJS:.o=.d) $(TARGET)

# 伪目标
.PHONY: all clean

# 调试版本
debug: CFLAGS += -DDEBUG -O0
debug: $(TARGET)

# 安装
PREFIX ?= /usr/local
install: $(TARGET)
	install -d $(DESTDIR)$(PREFIX)/bin
	install -m 755 $(TARGET) $(DESTDIR)$(PREFIX)/bin/
```

**多目录 Makefile 示例**：

```makefile
CC = gcc
CFLAGS = -Wall -Wextra -O2 -I./include

SRCS = $(wildcard src/*.c)
OBJS = $(SRCS:.c=.o)
TARGET = build/app

all: $(TARGET)

$(TARGET): $(OBJS)
	@mkdir -p build
	$(CC) $^ -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJS) build/

.PHONY: all clean
```

---

## 九、调试技巧

### 9.1 GDB 常用命令

```bash
# 编译时加 -g 选项保留调试信息
gcc -g -O0 program.c -o program

# 启动 GDB
gdb ./program

# === 基本操作 ===
run                    # 运行程序
run arg1 arg2          # 带参数运行
quit                   # 退出

# === 断点 ===
break main             # 在 main 函数设置断点
break main.c:42        # 在文件第 42 行设断点
break func if x > 10   # 条件断点
info breakpoints       # 查看所有断点
delete 2               # 删除 2 号断点
disable 1              # 禁用 1 号断点
enable 1               # 启用 1 号断点

# === 执行控制 ===
next (n)               # 单步（不进入函数）
step (s)               # 单步（进入函数）
continue (c)           # 继续执行
finish                 # 执行到当前函数返回

# === 查看变量 ===
print variable          # 打印变量值
print *pointer          # 打印指针指向的值
print array[0]@10       # 打印数组前 10 个元素
print/x variable        # 十六进制输出
display variable        # 每次停止时自动显示
watch variable          # 变量值改变时暂停

# === 查看信息 ===
backtrace (bt)          # 查看调用栈
frame 2                 # 切换到第 2 帧
info locals             # 查看当前帧的局部变量
info args               # 查看函数参数
list                    # 显示源代码

# === 内存检查 ===
x/10xw 0x7fff1234      # 查看 10 个 4 字节的十六进制值
x/s pointer             # 查看字符串
x/i $pc                 # 查看当前指令
```

### 9.2 Valgrind 内存检测

```bash
# 内存泄漏检测
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --verbose \
         ./program

# 输出解读
# "definitely lost"  — 确定的内存泄漏
# "indirectly lost"  — 间接泄漏（如链表节点泄漏）
# "possibly lost"    — 可能的泄漏
# "still reachable"  — 程序结束时仍可访问（通常不是问题）

# 缓存使用分析
valgrind --tool=cachegrind ./program

# 线程错误检测
valgrind --tool=helgrind ./program
```

### 9.3 AddressSanitizer

AddressSanitizer（ASan）是 GCC/Clang 内置的内存错误检测工具，比 Valgrind 快很多。

```bash
# 编译时启用
gcc -fsanitize=address -fno-omit-frame-pointer -g program.c -o program

# 运行（自动报告错误）
./program

# 检测的错误类型：
# - 堆缓冲区溢出/下溢
# - 栈缓冲区溢出
# - 全局缓冲区溢出
# - 使用已释放的内存（use-after-free）
# - 内存泄漏（需要额外选项）

# 泄漏检测器
ASAN_OPTIONS=detect_leaks=1 ./program

# 其他 sanitizer
gcc -fsanitize=undefined program.c -o program  # 未定义行为
gcc -fsanitize=thread program.c -o program     # 数据竞争
gcc -fsanitize=memory program.c -o program     # 未初始化内存读取（Clang）
```

### 9.4 实用调试宏

```c
// 调试打印宏
#ifdef DEBUG
    #define DBG(fmt, ...) \
        fprintf(stderr, "[DBG %s:%d %s] " fmt "\n", \
                __FILE__, __LINE__, __func__, ##__VA_ARGS__)
#else
    #define DBG(fmt, ...) ((void)0)
#endif

// 断言增强版
#define ASSERT_MSG(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "ASSERT FAILED: %s\n  at %s:%d in %s()\n  %s\n", \
                #cond, __FILE__, __LINE__, __func__, msg); \
        abort(); \
    } \
} while (0)

// 打印变量的值和类型（GCC typeof）
#define PRINT_VAR(x) \
    _Generic((x), \
        int:     printf(#x " = %d\n", x), \
        float:   printf(#x " = %f\n", x), \
        double:  printf(#x " = %lf\n", x), \
        char *:  printf(#x " = %s\n", x), \
        default: printf(#x " = ?\n"))

// 内存转储
void hex_dump(const void *data, size_t size) {
    const uint8_t *p = (const uint8_t *)data;
    for (size_t i = 0; i < size; i++) {
        if (i % 16 == 0) printf("%04zx: ", i);
        printf("%02x ", p[i]);
        if (i % 16 == 15) printf("\n");
    }
    if (size % 16 != 0) printf("\n");
}
```

---

## 十、嵌入式 C 特殊技巧

### 10.1 volatile 关键字

`volatile` 告诉编译器：该变量可能在程序之外被修改，禁止对其进行优化。

```c
// 适用场景：
// 1. 中断服务程序中修改的变量
volatile int flag = 0;

void ISR_Handler(void) {
    flag = 1;  // 中断中设置标志
}

int main(void) {
    while (flag == 0) {
        // 等待中断
        // 如果没有 volatile，编译器可能将 flag 缓存到寄存器
        // 导致死循环
    }
    // 处理中断事件
}

// 2. 硬件寄存器
#define GPIO_PORT_A  (*(volatile uint32_t *)0x40020000)
#define GPIO_PORT_B  (*(volatile uint32_t *)0x40020400)

// 3. 多线程共享变量
volatile int shared_counter = 0;
```

**volatile 常见错误**：

```c
// 错误：volatile 指针 vs 指向 volatile 的指针
volatile int *p1;       // p1 指向 volatile int，指针本身不是 volatile
int *volatile p2;       // p2 是 volatile 指针，指向普通 int
volatile int *volatile p3;  // 两者都是 volatile

// 错误：自增操作不是原子的
volatile int counter = 0;
counter++;  // 不是原子操作！在多线程环境中不安全
// 正确做法：使用原子操作或关中断保护
```

### 10.2 register 关键字

```c
// 建议编译器将变量存储在寄存器中（现代编译器通常忽略）
register int i;
for (i = 0; i < 100; i++) {
    // 高频使用的循环变量
}

// 注意：不能对 register 变量取地址
// register int x = 10;
// int *p = &x;  // 错误！
```

### 10.3 __attribute__ 扩展（GCC）

```c
// 1. packed：取消结构体填充
struct __attribute__((packed)) ModbusFrame {
    uint8_t  slave_addr;
    uint8_t  func_code;
    uint16_t start_addr;
    uint16_t reg_count;
    uint16_t crc;
};  // 总大小恰好 8 字节，无填充

// 2. aligned：指定对齐方式
struct __attribute__((aligned(32))) CacheLine {
    int data[8];
};  // 32 字节对齐，适合缓存行

// 3. section：将变量放入指定段
__attribute__((section(".noinit")))
uint32_t reset_reason;  // 放入 .noinit 段（不清零）

// 4. weak：弱符号，可被同名强符号覆盖
__attribute__((weak))
void system_hook(void) {
    // 默认空实现，用户可以覆盖
}

// 5. unused：抑制未使用警告
void debug_func(__attribute__((unused)) int param) {
    // param 可能只在 DEBUG 模式下使用
}

// 6. constructor/destructor：自动初始化/清理
__attribute__((constructor))
void early_init(void) {
    // 在 main() 之前自动调用
}

__attribute__((destructor))
void cleanup(void) {
    // 在 main() 之后自动调用
}

// 7. format：检查 printf 风格参数
__attribute__((format(printf, 1, 2)))
void my_log(const char *fmt, ...) {
    // 编译器会检查格式字符串与参数是否匹配
}

// 8. noreturn：标记不返回的函数
__attribute__((noreturn))
void fatal_error(const char *msg) {
    fprintf(stderr, "FATAL: %s\n", msg);
    exit(1);
}

// 9. 位域的字节序控制
typedef struct {
    uint32_t field1 : 8;
    uint32_t field2 : 8;
} __attribute__((packed)) BitField_t;
```

### 10.4 中断安全函数

```c
// 中断服务程序（ISR）注意事项：
// 1. 不能使用阻塞操作（printf、malloc、sleep）
// 2. 不能使用非重入函数
// 3. 执行时间应尽可能短
// 4. 使用 volatile 修饰共享变量

// 通过标志位实现中断与主循环的通信
volatile uint8_t uart_rx_flag = 0;
volatile uint8_t uart_rx_data = 0;

void USART1_IRQHandler(void) {
    if (USART1->SR & USART_SR_RXNE) {
        uart_rx_data = USART1->DR;
        uart_rx_flag = 1;
    }
}

int main(void) {
    while (1) {
        if (uart_rx_flag) {
            uart_rx_flag = 0;
            process_data(uart_rx_data);  // 在主循环中处理
        }
        // 其他任务
    }
}

// 环形缓冲区：中断安全的数据传递
#define RING_BUF_SIZE 256

typedef struct {
    volatile uint8_t buffer[RING_BUF_SIZE];
    volatile uint16_t head;
    volatile uint16_t tail;
} RingBuffer;

void ring_init(RingBuffer *rb) {
    rb->head = 0;
    rb->tail = 0;
}

bool ring_put(RingBuffer *rb, uint8_t data) {
    uint16_t next = (rb->head + 1) % RING_BUF_SIZE;
    if (next == rb->tail) return false;  // 满
    rb->buffer[rb->head] = data;
    rb->head = next;
    return true;
}

bool ring_get(RingBuffer *rb, uint8_t *data) {
    if (rb->head == rb->tail) return false;  // 空
    *data = rb->buffer[rb->tail];
    rb->tail = (rb->tail + 1) % RING_BUF_SIZE;
    return true;
}
```

### 10.5 嵌入式编程模式

```c
// 1. 寄存器映射模式
typedef struct {
    volatile uint32_t CR;
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t RESERVED;
} USART_TypeDef;

#define USART1 ((USART_TypeDef *)0x40011000)
#define USART2 ((USART_TypeDef *)0x40004400)

// 使用
USART1->CR |= (1 << 13);  // 使能 USART1
while (!(USART1->SR & (1 << 6)));  // 等待发送完成
USART1->DR = 'A';

// 2. 位带操作（Cortex-M 特有）
#define BITBAND(addr, bit) \
    (((uint32_t)(addr) & 0xF0000000) + 0x02000000 + \
     (((uint32_t)(addr) & 0x000FFFFF) << 5) + ((bit) << 2))

#define GPIOA_ODR_BIT(n)  (*(volatile uint32_t *)BITBAND(&GPIOA->ODR, n))

GPIOA_ODR_BIT(5) = 1;  // 原子操作设置 PA5
GPIOA_ODR_BIT(5) = 0;  // 原子操作清除 PA5

// 3. 回调注册模式（驱动框架）
typedef struct {
    void (*init)(void);
    void (*start)(void);
    void (*stop)(void);
    void (*irq_handler)(void);
    void *priv_data;
} DriverOps;

// 4. 状态机模式
typedef enum {
    STATE_IDLE,
    STATE_RECEIVING,
    STATE_PROCESSING,
    STATE_SENDING,
    STATE_ERROR
} State_t;

typedef enum {
    EVENT_DATA_READY,
    EVENT_TIMEOUT,
    EVENT_ERROR,
    EVENT_DONE
} Event_t;

State_t state_machine(State_t state, Event_t event) {
    switch (state) {
        case STATE_IDLE:
            if (event == EVENT_DATA_READY) return STATE_RECEIVING;
            break;
        case STATE_RECEIVING:
            if (event == EVENT_DONE) return STATE_PROCESSING;
            if (event == EVENT_TIMEOUT) return STATE_IDLE;
            if (event == EVENT_ERROR) return STATE_ERROR;
            break;
        case STATE_PROCESSING:
            if (event == EVENT_DONE) return STATE_SENDING;
            break;
        case STATE_SENDING:
            if (event == EVENT_DONE) return STATE_IDLE;
            break;
        case STATE_ERROR:
            return STATE_IDLE;  // 错误恢复
    }
    return state;
}
```

### 10.6 MISRA-C 常用规范速查

嵌入式开发中广泛遵循 MISRA-C 编码规范，以下为常见要点：

```c
// 1. 不使用递归（Rule 17.2）
// 改用迭代实现

// 2. 每条语句只做一件事（Rule 15.4）
// 禁止：if (a && b) 和 for 循环中有多条语句

// 3. 不使用动态内存分配（Rule 21.3）
// 禁止：malloc, calloc, realloc, free
// 使用静态分配或内存池

// 4. 显式类型转换（Rule 10.x）
uint16_t a = 100;
uint8_t b = (uint8_t)a;  // 显式截断

// 5. 复合赋值需用大括号
if (a == b) {       // 需要大括号，即使只有一行
    do_something();
}

// 6. 不使用位域（部分规范）
// 用掩码宏替代

// 7. 变量声明后必须初始化
int32_t value = 0;
```

---

## 附录：速查表

### A. 指针声明读法

从变量名开始，由内向外读：

```
int *p;          // p 是指向 int 的指针
int **p;         // p 是指向 int 指针的指针
int *p[10];      // p 是数组，元素是 int 指针
int (*p)[10];    // p 是指针，指向 int[10] 数组
int (*p)(int);   // p 是指针，指向参数为 int、返回 int 的函数
int *p(int);     // p 是函数，参数为 int，返回 int*
```

### B. 格式化字符串

| 格式符 | 类型 | 示例 |
|--------|------|------|
| `%d` | int | `printf("%d", 42)` |
| `%u` | unsigned int | `printf("%u", 42U)` |
| `%ld` | long | `printf("%ld", 42L)` |
| `%f` | float/double | `printf("%f", 3.14)` |
| `%e` | 科学计数法 | `printf("%e", 3.14)` |
| `%x` | 十六进制 | `printf("%x", 255)` → `ff` |
| `%o` | 八进制 | `printf("%o", 8)` → `10` |
| `%s` | 字符串 | `printf("%s", "hello")` |
| `%p` | 指针 | `printf("%p", (void *)ptr)` |
| `%zu` | size_t | `printf("%zu", sizeof(int))` |
| `%%` | 百分号 | `printf("100%%")` → `100%` |

### C. 常用位运算公式

| 操作 | 表达式 | 说明 |
|------|--------|------|
| 设置第 n 位 | `x \|= (1U << n)` | 置 1 |
| 清除第 n 位 | `x &= ~(1U << n)` | 置 0 |
| 翻转第 n 位 | `x ^= (1U << n)` | 取反 |
| 检查第 n 位 | `(x >> n) & 1` | 读取 |
| 最低 1 位 | `x & (-x)` | 提取 |
| 清除最低 1 | `x & (x - 1)` | 去除 |
| 对齐到 2^n | `(x + n - 1) & ~(n - 1)` | 向上对齐 |
| 判断 2 的幂 | `x > 0 && (x & (x-1)) == 0` | 检查 |

### D. sizeof 常见值（64 位系统）

| 类型 | 大小（字节） |
|------|-------------|
| `char` | 1 |
| `short` | 2 |
| `int` | 4 |
| `long` | 8（Linux）/ 4（Windows） |
| `long long` | 8 |
| `float` | 4 |
| `double` | 8 |
| `void *` | 8 |
| `size_t` | 8 |

---

> **参考资源**：
> - 《C 程序设计语言》(K&R) -- C 语言圣经
> - 《C 和指针》-- 深入理解指针
> - 《C 专家编程》-- 高级技巧和陷阱
> - 《C 缺陷与陷阱》-- 避坑指南
> - MISRA-C:2012 -- 嵌入式 C 编码规范
