# GCC与链接脚本

## 核心概念

- **GCC** - GNU编译器集合
- **链接脚本** - 控制内存布局
- **启动文件** - 初始化硬件和C环境
- **优化选项** - 代码优化级别

---

## 一、GCC编译流程

### 1.1 编译阶段

```
源文件 → 预处理 → 编译 → 汇编 → 链接 → 可执行文件
.c       .i       .s      .o      .elf
```

| 阶段 | 工具 | 命令 |
|------|------|------|
| 预处理 | cpp | gcc -E |
| 编译 | cc1 | gcc -S |
| 汇编 | as | gcc -c |
| 链接 | ld | gcc |

---

### 1.2 交叉编译

```bash
# ARM交叉编译
arm-none-eabi-gcc -o output.elf main.c

# RISC-V交叉编译
riscv32-unknown-elf-gcc -o output.elf main.c

# ESP32 (Xtensa)
xtensa-esp32-elf-gcc -o output.elf main.c
```

---

## 二、GCC选项

### 2.1 编译选项

| 选项 | 说明 |
|------|------|
| -c | 只编译不链接 |
| -o | 输出文件名 |
| -I | 头文件路径 |
| -D | 定义宏 |
| -Wall | 开启所有警告 |
| -Werror | 警告当错误 |
| -g | 生成调试信息 |
| -O0/-O1/-O2/-O3 | 优化级别 |
| -Os | 优化大小 |
| -ffunction-sections | 每个函数一个段 |
| -fdata-sections | 每个数据一个段 |
| -std=c11 | C语言标准 |
| -mcpu | 目标CPU |
| -mthumb | Thumb指令集 |
| -mfloat-abi | 浮点ABI |

---

### 2.2 优化级别

| 级别 | 说明 | 适用 |
|------|------|------|
| -O0 | 无优化 | 调试 |
| -O1 | 基本优化 | 开发 |
| -O2 | 更多优化 | 发布 |
| -O3 | 最大优化 | 性能关键 |
| -Os | 大小优化 | 嵌入式 |
| -Og | 调试优化 | 调试+优化 |

---

### 2.3 链接选项

| 选项 | 说明 |
|------|------|
| -l | 链接库 |
| -L | 库搜索路径 |
| -T | 链接脚本 |
| -nostdlib | 不链接标准库 |
| -nostartfiles | 不链接启动文件 |
| -Wl,--gc-sections | 删除未使用段 |
| -Wl,-Map | 生成map文件 |
| -specs=nano.specs | 使用newlib-nano |
| -specs=nosys.specs | 无系统调用 |

---

## 三、链接脚本

### 3.1 基本语法

```ld
/* 链接脚本示例 */
ENTRY(Reset_Handler)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
    RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS
{
    .text :
    {
        . = ALIGN(4);
        *(.vectors)        /* 中断向量表 */
        *(.text)           /* 代码 */
        *(.text*)
        . = ALIGN(4);
        _etext = .;
    } >FLASH

    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } >FLASH

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } >RAM AT> FLASH

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } >RAM

    _sidata = LOADADDR(.data);
}
```

---

### 3.2 内存定义

```ld
MEMORY
{
    /* 名称(属性) : 起始地址, 长度 */
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
    RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 128K
    CCM (rwx)   : ORIGIN = 0x10000000, LENGTH = 64K
    DTCM (rwx)  : ORIGIN = 0x20000000, LENGTH = 128K
    ITCM (rwx)  : ORIGIN = 0x00000000, LENGTH = 64K
}
```

**属性说明：**
| 属性 | 说明 |
|------|------|
| r | 可读 |
| w | 可写 |
| x | 可执行 |
| a | 可分配 |

---

### 3.3 段定义

```ld
SECTIONS
{
    /* 向量表 */
    .vectors :
    {
        . = ALIGN(4);
        KEEP(*(.vectors))
        . = ALIGN(4);
    } >FLASH

    /* 代码 */
    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.glue_7)         /* ARM/Thumb胶合代码 */
        *(.glue_7t)
        . = ALIGN(4);
        _etext = .;
    } >FLASH

    /* 只读数据 */
    .rodata :
    {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } >FLASH

    /* 初始化数据(存储在Flash, 运行在RAM) */
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } >RAM AT> FLASH

    /* 零初始化数据 */
    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } >RAM

    /* 堆栈 */
    .stack (NOLOAD) :
    {
        . = ALIGN(8);
        . += 0x2000;  /* 8KB栈 */
        _estack = .;
    } >RAM

    /* 计算data段的加载地址 */
    _sidata = LOADADDR(.data);
}
```

---

### 3.4 特殊符号

```ld
/* 提供给C代码使用的符号 */
_estack = ORIGIN(RAM) + LENGTH(RAM);  /* 栈顶 */
_sidata = LOADADDR(.data);            /* data初始值地址 */
_sdata = .;                           /* data段起始 */
_edata = .;                           /* data段结束 */
_sbss = .;                            /* bss段起始 */
_ebss = .;                            /* bss段结束 */
_heap_start = .;                      /* 堆起始 */
_heap_end = _estack - 0x2000;         /* 堆结束(留8KB栈) */
```

---

## 四、启动文件

### 4.1 ARM启动文件

```c
/* startup_stm32f4xx.c */
#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata, _sdata, _edata;
extern uint32_t _sbss, _ebss;

void Reset_Handler(void);
void Default_Handler(void);

/* 中断向量表 */
__attribute__((section(".vectors")))
const uint32_t vectors[] = {
    (uint32_t)&_estack,         // 初始栈指针
    (uint32_t)Reset_Handler,    // 复位处理
    (uint32_t)NMI_Handler,      // NMI
    (uint32_t)HardFault_Handler, // HardFault
    // ... 其他中断
};

void Reset_Handler(void) {
    // 复制data段
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }

    // 清零bss段
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }

    // 调用main
    main();

    // 不应该到这里
    while (1);
}

void Default_Handler(void) {
    while (1);
}

/* 弱符号定义 */
__attribute__((weak)) void NMI_Handler(void) { Default_Handler(); }
__attribute__((weak)) void HardFault_Handler(void) { Default_Handler(); }
// ... 其他中断处理
```

---

### 4.2 RISC-V启动文件

```c
/* startup_riscv.c */
#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata, _sdata, _edata;
extern uint32_t _sbss, _ebss;

__attribute__((naked, section(".vectors")))
void _start(void) {
    __asm__ volatile (
        "la sp, _estack\n"      // 设置栈指针
        "la t0, _sdata\n"       // 目标地址
        "la t1, _edata\n"       // 结束地址
        "la t2, _sidata\n"      // 源地址
        "1:\n"
        "bgeu t0, t1, 2f\n"
        "lw t3, 0(t2)\n"
        "sw t3, 0(t0)\n"
        "addi t0, t0, 4\n"
        "addi t2, t2, 4\n"
        "j 1b\n"
        "2:\n"
        "la t0, _sbss\n"        // bss起始
        "la t1, _ebss\n"        // bss结束
        "3:\n"
        "bgeu t0, t1, 4f\n"
        "sw zero, 0(t0)\n"
        "addi t0, t0, 4\n"
        "j 3b\n"
        "4:\n"
        "call main\n"           // 调用main
        "5:\n"
        "j 5b\n"                // 无限循环
    );
}
```

---

## 五、启动代码详解

### 5.1 data段初始化

```
Flash (ROM):
┌──────────┐
│ _sidata   │ ← data段初始值
│ .data内容 │
└──────────┘
          ↓ 复制
RAM:
┌──────────┐
│ _sdata    │ ← data段运行地址
│ .data内容 │
│ _edata    │
└──────────┘
```

**C代码中的对应：**
```c
// 全局初始化变量 -> .data段
int global_var = 42;

// 全局未初始化变量 -> .bss段
int global_zero;

// 常量 -> .rodata段
const int constant = 100;
```

---

### 5.2 bss段清零

```c
// 清零bss段
extern uint32_t _sbss, _ebss;

void clear_bss(void) {
    uint32_t *dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }
}
```

---

## 六、GCC内置函数

### 6.1 内存操作

```c
// 内存屏障
__asm volatile("dsb" ::: "memory");  // ARM
__asm volatile("fence" ::: "memory"); // RISC-V

// 编译器屏障
__asm volatile("" ::: "memory");

// 内建函数
__builtin_return_address(0);  // 返回地址
__builtin_frame_address(0);   // 帧地址
__builtin_clz(x);             // 前导零计数
__builtin_ctz(x);             // 尾随零计数
__builtin_popcount(x);        // 置位计数
__builtin_bswap32(x);         // 字节序交换
```

---

### 6.2 属性

```c
// 函数属性
__attribute__((noreturn))     // 函数不返回
__attribute__((naked))        // 无函数序言/结尾
__attribute__((weak))         // 弱符号
__attribute__((section(".my_section")))  // 指定段
__attribute__((aligned(4)))   // 对齐
__attribute__((packed))       // 紧凑结构
__attribute__((unused))       // 可能未使用
__attribute__((used))         // 强制保留

// 变量属性
__attribute__((section(".my_data"))) int my_var;
__attribute__((aligned(16))) int aligned_var;
```

---

## 七、优化技巧

### 7.1 减小代码大小

```bash
# 编译选项
-Os                          # 大小优化
-ffunction-sections          # 每个函数一个段
-fdata-sections              # 每个数据一个段
-Wl,--gc-sections            # 删除未使用段
-Wl,--relax                  # 长跳转优化为短跳转
-flto                        # 链接时优化
-specs=nano.specs            # 使用小库
```

---

### 7.2 提高性能

```bash
# 编译选项
-O2                          # 性能优化
-mcpu=cortex-m4              # 指定CPU
-mthumb                      # Thumb指令集
-mfloat-abi=hard             # 硬件浮点
-mfpu=fpv4-sp-d16            # FPU类型
-ffast-math                  # 快速数学
-funroll-loops               # 循环展开
```

---

### 7.3 查看生成代码

```bash
# 生成汇编
arm-none-eabi-gcc -S main.c

# 反汇编
arm-none-eabi-objdump -d firmware.elf

# 查看段大小
arm-none-eabi-size firmware.elf

# 查看符号表
arm-none-eabi-nm firmware.elf

# 查看map文件
arm-none-eabi-gcc -Wl,-Map=output.map ...
```

---

## 八、Makefile示例

### 8.1 嵌入式Makefile

```makefile
# 工具链
PREFIX = arm-none-eabi-
CC = $(PREFIX)gcc
AS = $(PREFIX)gcc -x assembler-with-cpp
LD = $(PREFIX)gcc
OBJCOPY = $(PREFIX)objcopy
SIZE = $(PREFIX)size

# 目标
TARGET = firmware

# 源文件
C_SOURCES = src/main.c src/utils.c
ASM_SOURCES = startup_stm32f4xx.s

# 包含路径
C_INCLUDES = -Iinclude -ICMSIS/Include

# 编译选项
CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
CFLAGS += -Os -Wall -fdata-sections -ffunction-sections
CFLAGS += $(C_INCLUDES)
CFLAGS += -DSTM32F407xx

# 链接选项
LDSCRIPT = STM32F407VGTx_FLASH.ld
LDFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
LDFLAGS += -T$(LDSCRIPT) -Wl,-Map=$(TARGET).map,--gc-sections
LDFLAGS += -specs=nano.specs -specs=nosys.specs

# 对象文件
OBJECTS = $(C_SOURCES:.c=.o) $(ASM_SOURCES:.s=.o)

# 默认目标
all: $(TARGET).elf $(TARGET).hex $(TARGET).bin size

# 链接
$(TARGET).elf: $(OBJECTS)
	$(LD) $(OBJECTS) $(LDFLAGS) -o $@

# 编译C
%.o: %.c
	$(CC) -c $(CFLAGS) $< -o $@

# 编译汇编
%.o: %.s
	$(AS) -c $(CFLAGS) $< -o $@

# 生成hex
%.hex: %.elf
	$(OBJCOPY) -O ihex $< $@

# 生成bin
%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

# 显示大小
size: $(TARGET).elf
	$(SIZE) $<

# 清理
clean:
	rm -f $(OBJECTS) $(TARGET).elf $(TARGET).hex $(TARGET).bin $(TARGET).map

.PHONY: all clean size
```

---

## 附录：段类型

| 段 | 内容 | 位置 |
|----|------|------|
| .text | 代码 | Flash |
| .rodata | 只读数据 | Flash |
| .data | 初始化数据 | Flash→RAM |
| .bss | 零初始化数据 | RAM |
| .heap | 动态分配 | RAM |
| .stack | 栈 | RAM |

---

## 相关链接

- [[Makefile与CMake]] - 构建系统
- [[STM32基础]] - STM32开发
- [[调试技术详解]] - 调试方法
