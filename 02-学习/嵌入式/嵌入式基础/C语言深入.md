# C语言深入

## 核心概念

- **指针** - 存储内存地址的变量
- **内存管理** - 动态分配与释放内存
- **位操作** - 对二进制位进行操作
- **结构体** - 自定义数据类型

---

## 一、指针深入

### 1.1 指针基础

**定义：**
```c
int *p;        // 指向int的指针
char *p;       // 指向char的指针
void *p;       // 通用指针
```

**取地址与解引用：**
```c
int a = 10;
int *p = &a;   // p存储a的地址
int b = *p;    // b = 10，解引用
```

---

### 1.2 指针与数组

**数组名即指针：**
```c
int arr[5] = {1, 2, 3, 4, 5};
int *p = arr;  // p指向arr[0]

// 以下等价：
arr[i]  // 数组下标访问
*(p+i)  // 指针偏移访问
p[i]    // 指针下标访问
```

**指针运算：**
```c
p + 1   // 指向下一个元素
p - 1   // 指向上一个元素
p++     // 指向下一个元素
p--     // 指向上一个元素
p2 - p1 // 两个指针之间的元素个数
```

---

### 1.3 指针与函数

**指针作为参数：**
```c
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

// 调用
swap(&x, &y);
```

**函数返回指针：**
```c
int* create_array(int size) {
    int *arr = (int*)malloc(size * sizeof(int));
    return arr;
}
```

**函数指针：**
```c
int (*func_ptr)(int, int);  // 声明
func_ptr = add;             // 赋值
int result = func_ptr(3, 5); // 调用
```

---

### 1.4 多级指针

```c
int a = 10;
int *p = &a;      // 一级指针
int **pp = &p;    // 二级指针
int ***ppp = &pp; // 三级指针

// 访问：
***ppp = 20;  // a = 20
```

**应用：** 动态二维数组、指针数组

---

### 1.5 指针数组与数组指针

**指针数组：**
```c
int *arr[5];  // 数组，每个元素是指针
```

**数组指针：**
```c
int (*p)[5];  // 指针，指向一个数组
```

**示例：**
```c
int arr[3][4];
int (*p)[4] = arr;  // p指向第一行

// 访问：
p[i][j]    // 等价于 arr[i][j]
*(*(p+i)+j) // 等价于 arr[i][j]
```

---

## 二、内存管理

### 2.1 内存区域

```
┌─────────────────────┐ 高地址
│       栈(Stack)      │ ← 局部变量、函数参数
├─────────────────────┤
│         ↓            │
│                     │
│         ↑            │
├─────────────────────┤
│     堆(Heap)         │ ← 动态分配
├─────────────────────┤
│   全局/静态区         │ ← 全局变量、static
├─────────────────────┤
│   代码区(Text)        │ ← 程序代码
└─────────────────────┘ 低地址
```

---

### 2.2 动态内存分配

**malloc：**
```c
int *p = (int*)malloc(10 * sizeof(int));
if (p == NULL) {
    // 分配失败
}
```

**calloc：**
```c
int *p = (int*)calloc(10, sizeof(int));  // 自动初始化为0
```

**realloc：**
```c
p = (int*)realloc(p, 20 * sizeof(int));  // 调整大小
```

**free：**
```c
free(p);
p = NULL;  // 避免野指针
```

---

### 2.3 内存泄漏

**常见原因：**
1. 分配后未释放
2. 重新分配前未释放旧内存
3. 异常路径未释放
4. 循环中反复分配

**检测工具：**
- Valgrind
- AddressSanitizer
- Visual Leak Detector

---

### 2.4 野指针与悬空指针

**野指针：** 未初始化的指针
```c
int *p;        // 野指针
*p = 10;       // 未定义行为
```

**悬空指针：** 指向已释放内存的指针
```c
int *p = (int*)malloc(sizeof(int));
free(p);
*p = 10;       // 悬空指针，未定义行为
```

**避免方法：**
- 初始化指针为NULL
- 释放后置为NULL
- 使用前检查是否为NULL

---

## 三、位操作

### 3.1 位运算符

| 运算符 | 名称 | 示例 | 说明 |
|--------|------|------|------|
| & | 按位与 | a & b | 都为1才为1 |
| \| | 按位或 | a \| b | 有1就为1 |
| ^ | 按位异或 | a ^ b | 不同为1 |
| ~ | 按位取反 | ~a | 0变1，1变0 |
| << | 左移 | a << n | 左移n位 |
| >> | 右移 | a >> n | 右移n位 |

---

### 3.2 位操作应用

**设置位：**
```c
// 设置第n位为1
flags |= (1 << n);
```

**清除位：**
```c
// 清除第n位为0
flags &= ~(1 << n);
```

**翻转位：**
```c
// 翻转第n位
flags ^= (1 << n);
```

**检查位：**
```c
// 检查第n位是否为1
if (flags & (1 << n)) {
    // 第n位为1
}
```

---

### 3.3 位域

```c
struct flags {
    unsigned int ready : 1;    // 1位
    unsigned int error : 1;    // 1位
    unsigned int mode  : 2;    // 2位
    unsigned int count : 4;    // 4位
};
```

**应用：** 节省内存、硬件寄存器映射

---

### 3.4 嵌入式常用位操作

**寄存器操作：**
```c
// 读寄存器
uint32_t val = REG;

// 写寄存器
REG = val;

// 设置位
REG |= BIT_MASK;

// 清除位
REG &= ~BIT_MASK;

// 读取特定位
uint32_t field = (REG >> SHIFT) & MASK;
```

---

## 四、结构体

### 4.1 结构体定义

```c
struct student {
    char name[20];
    int age;
    float score;
};
```

**初始化：**
```c
struct student s1 = {"Tom", 20, 95.5};
struct student s2 = {.name = "Jerry", .age = 21};
```

---

### 4.2 结构体指针

```c
struct student s = {"Tom", 20, 95.5};
struct student *p = &s;

// 访问方式：
p->age     // 等价于 (*p).age
s.age      // 直接访问
```

---

### 4.3 结构体内存对齐

**对齐规则：**
1. 每个成员按其大小对齐
2. 结构体总大小是最大成员的整数倍
3. 填充(padding)确保对齐

**示例：**
```c
struct example {
    char a;     // 1字节 + 3字节填充
    int b;      // 4字节
    char c;     // 1字节 + 3字节填充
};
// 总大小：12字节（不是6字节）
```

**强制对齐：**
```c
#pragma pack(1)  // 1字节对齐
struct packed {
    char a;
    int b;
    char c;
};
// 总大小：6字节
```

---

### 4.4 结构体与函数

**传递结构体：**
```c
void print_student(struct student s) {
    printf("%s, %d, %.1f\n", s.name, s.age, s.score);
}
```

**传递结构体指针：**
```c
void update_score(struct student *s, float score) {
    s->score = score;
}
```

**返回结构体：**
```c
struct student create_student(char *name, int age) {
    struct student s;
    strcpy(s.name, name);
    s.age = age;
    s.score = 0;
    return s;
}
```

---

## 五、联合体与枚举

### 5.1 联合体(union)

```c
union data {
    int i;
    float f;
    char c;
};
```

**特点：** 所有成员共享同一内存，大小等于最大成员

**应用：**
```c
union {
    uint32_t word;
    struct {
        uint32_t bit0 : 1;
        uint32_t bit1 : 1;
        // ...
    } bits;
} reg;
```

---

### 5.2 枚举(enum)

```c
enum color {
    RED,     // 0
    GREEN,   // 1
    BLUE     // 2
};

enum weekday {
    MON = 1,
    TUE,
    WED,
    THU,
    FRI,
    SAT,
    SUN
};
```

**应用：** 提高代码可读性

---

## 六、预处理器

### 6.1 宏定义

**无参宏：**
```c
#define PI 3.14159
#define MAX_SIZE 100
```

**带参宏：**
```c
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define SQUARE(x) ((x) * (x))
```

**注意事项：**
```c
// 错误：
#define SQUARE(x) x * x
SQUARE(3+1)  // 展开为 3+1*3+1 = 7

// 正确：
#define SQUARE(x) ((x) * (x))
SQUARE(3+1)  // 展开为 ((3+1) * (3+1)) = 16
```

---

### 6.2 条件编译

```c
#ifdef DEBUG
    printf("Debug mode\n");
#endif

#ifndef HEADER_H
#define HEADER_H
    // 头文件内容
#endif

#if defined(WIN32)
    // Windows代码
#elif defined(LINUX)
    // Linux代码
#else
    // 其他平台
#endif
```

---

### 6.3 预定义宏

| 宏 | 说明 |
|----|------|
| `__FILE__` | 当前文件名 |
| `__LINE__` | 当前行号 |
| `__DATE__` | 编译日期 |
| `__TIME__` | 编译时间 |
| `__func__` | 当前函数名 |

**应用：**
```c
#define LOG(fmt, ...) \
    printf("[%s:%d] " fmt, __FILE__, __LINE__, ##__VA_ARGS__)
```

---

## 七、关键字深入

### 7.1 static

**局部变量：** 生命周期延长至程序结束
```c
void counter() {
    static int count = 0;  // 只初始化一次
    count++;
    printf("%d\n", count);
}
```

**全局变量/函数：** 限制作用域为当前文件
```c
static int file_var = 0;        // 仅当前文件可见
static void file_func() {}      // 仅当前文件可见
```

---

### 7.2 const

**常量：**
```c
const int MAX = 100;
MAX = 200;  // 错误
```

**指针与const：**
```c
const int *p;        // 指向常量的指针，*p不可改
int * const p;       // 常量指针，p不可改
const int * const p; // 都不可改
```

---

### 7.3 volatile

**作用：** 告诉编译器不要优化该变量

**应用场景：**
- 中断服务程序中的变量
- 多线程共享变量
- 硬件寄存器

```c
volatile int flag = 0;

// 中断中
void ISR() {
    flag = 1;
}

// 主循环中
while (flag == 0) {
    // 等待中断
}
```

---

### 7.4 typedef

**类型别名：**
```c
typedef unsigned int uint32_t;
typedef struct student Student;
typedef int (*FuncPtr)(int, int);
```

**应用：**
```c
uint32_t value = 100;
Student s = {"Tom", 20};
FuncPtr func = add;
```

---

## 八、链表

### 8.1 单链表

**定义：**
```c
struct node {
    int data;
    struct node *next;
};
```

**创建节点：**
```c
struct node* create_node(int data) {
    struct node *new = (struct node*)malloc(sizeof(struct node));
    new->data = data;
    new->next = NULL;
    return new;
}
```

**插入节点：**
```c
void insert_head(struct node **head, int data) {
    struct node *new = create_node(data);
    new->next = *head;
    *head = new;
}
```

**删除节点：**
```c
void delete_node(struct node **head, int data) {
    struct node *curr = *head;
    struct node *prev = NULL;
    
    while (curr != NULL) {
        if (curr->data == data) {
            if (prev == NULL) {
                *head = curr->next;
            } else {
                prev->next = curr->next;
            }
            free(curr);
            return;
        }
        prev = curr;
        curr = curr->next;
    }
}
```

---

### 8.2 双链表

**定义：**
```c
struct dnode {
    int data;
    struct dnode *prev;
    struct dnode *next;
};
```

---

### 8.3 循环链表

**特点：** 尾节点的next指向头节点

**应用：** 约瑟夫环、任务调度

---

## 九、栈与队列

### 9.1 栈（LIFO）

**实现：**
```c
#define STACK_SIZE 100

struct stack {
    int data[STACK_SIZE];
    int top;
};

void push(struct stack *s, int val) {
    if (s->top < STACK_SIZE - 1) {
        s->data[++s->top] = val;
    }
}

int pop(struct stack *s) {
    if (s->top >= 0) {
        return s->data[s->top--];
    }
    return -1;  // 栈空
}
```

**应用：** 函数调用、表达式求值、括号匹配

---

### 9.2 队列（FIFO）

**实现：**
```c
#define QUEUE_SIZE 100

struct queue {
    int data[QUEUE_SIZE];
    int front;
    int rear;
    int count;
};

void enqueue(struct queue *q, int val) {
    if (q->count < QUEUE_SIZE) {
        q->data[q->rear] = val;
        q->rear = (q->rear + 1) % QUEUE_SIZE;
        q->count++;
    }
}

int dequeue(struct queue *q) {
    if (q->count > 0) {
        int val = q->data[q->front];
        q->front = (q->front + 1) % QUEUE_SIZE;
        q->count--;
        return val;
    }
    return -1;  // 队列空
}
```

**应用：** 任务调度、缓冲区、BFS

---

## 十、文件操作

### 10.1 文件打开与关闭

```c
FILE *fp = fopen("file.txt", "r");
if (fp == NULL) {
    perror("打开文件失败");
    return -1;
}

fclose(fp);
```

**打开模式：**
| 模式 | 说明 |
|------|------|
| r | 只读 |
| w | 只写（清空） |
| a | 追加 |
| r+ | 读写 |
| w+ | 读写（清空） |
| a+ | 读写（追加） |

---

### 10.2 文件读写

**字符读写：**
```c
int ch = fgetc(fp);
fputc('A', fp);
```

**字符串读写：**
```c
char buf[100];
fgets(buf, 100, fp);
fputs("Hello", fp);
```

**格式化读写：**
```c
int age;
fscanf(fp, "%d", &age);
fprintf(fp, "Age: %d", age);
```

**块读写：**
```c
fread(buf, size, count, fp);
fwrite(buf, size, count, fp);
```

---

### 10.3 文件定位

```c
rewind(fp);                    // 回到开头
fseek(fp, 0, SEEK_SET);       // 定位到开头
fseek(fp, 0, SEEK_END);       // 定位到末尾
fseek(fp, 10, SEEK_CUR);      // 当前位置后移10字节
long pos = ftell(fp);          // 获取当前位置
```

---

## 十一、调试技巧

### 11.1 断言

```c
#include <assert.h>

assert(ptr != NULL);  // 条件为假时终止程序
```

---

### 11.2 打印调试

```c
#ifdef DEBUG
#define DBG(fmt, ...) printf("[DBG] " fmt "\n", ##__VA_ARGS__)
#else
#define DBG(fmt, ...)
#endif
```

---

### 11.3 GDB调试

```bash
gcc -g main.c -o main    # 编译时加调试信息
gdb ./main               # 启动GDB
(gdb) break main         # 设置断点
(gdb) run                # 运行
(gdb) print var          # 打印变量
(gdb) next               # 单步执行
(gdb) continue           # 继续运行
```

---

## 十二、嵌入式C编程规范

### 12.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | 小写下划线 | sensor_value |
| 函数 | 小写下划线 | read_sensor() |
| 宏 | 大写下划线 | MAX_BUFFER_SIZE |
| 类型 | 首字母大写 | SensorData |
| 常量 | 大写下划线 | PI_VALUE |

---

### 12.2 代码风格

**缩进：** 使用4个空格或Tab

**大括号：**
```c
if (condition) {
    // 代码
} else {
    // 代码
}
```

**注释：**
```c
// 单行注释

/*
 * 多行注释
 * 用于函数说明
 */
```

---

### 12.3 安全编程

**避免缓冲区溢出：**
```c
// 错误：
char buf[10];
strcpy(buf, "This is a very long string");

// 正确：
char buf[10];
strncpy(buf, "This is a very long string", sizeof(buf)-1);
buf[sizeof(buf)-1] = '\0';
```

**避免整数溢出：**
```c
// 错误：
int a = INT_MAX;
int b = a + 1;  // 溢出

// 正确：
if (a > INT_MAX - 1) {
    // 处理溢出
} else {
    int b = a + 1;
}
```

---

## 附录：关键字速查表

| 关键字 | 说明 |
|--------|------|
| auto | 自动变量（默认） |
| break | 跳出循环 |
| case | switch分支 |
| char | 字符类型 |
| const | 常量 |
| continue | 继续循环 |
| default | 默认分支 |
| do | do-while循环 |
| double | 双精度浮点 |
| else | if分支 |
| enum | 枚举 |
| extern | 外部声明 |
| float | 单精度浮点 |
| for | for循环 |
| goto | 跳转 |
| if | 条件判断 |
| int | 整型 |
| long | 长整型 |
| register | 寄存器变量 |
| return | 返回 |
| short | 短整型 |
| signed | 有符号 |
| sizeof | 大小 |
| static | 静态 |
| struct | 结构体 |
| switch | 多分支 |
| typedef | 类型定义 |
| union | 联合体 |
| unsigned | 无符号 |
| void | 无类型 |
| volatile | 易变 |
| while | while循环 |

---

## 相关链接

- [[数据结构与算法]] - 算法基础
- [[计算机组成原理]] - 体系结构
- [[嵌入式C编程]] - 嵌入式实践
