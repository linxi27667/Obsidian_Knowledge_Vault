# RISC-V架构详解

## 核心概念

- **RISC-V** - 开源指令集架构
- **RV32I** - 基础整数指令集
- **CSR** - 控制状态寄存器
- **特权模式** - Machine/Supervisor/User

---

## 一、RISC-V基础

### 1.1 寄存器

```c
// RISC-V寄存器
/*
 * 32个通用寄存器(x0-x31)
 * x0: 硬连线0
 * x1(ra): 返回地址
 * x2(sp): 栈指针
 * x3(gp): 全局指针
 * x4(tp): 线程指针
 * x5-x7(t0-t2): 临时寄存器
 * x8(s0/fp): 帧指针
 * x9(s1): 保存寄存器
 * x10-x17(a0-a7): 函数参数
 * x18-x27(s2-s11): 保存寄存器
 * x28-x31(t3-t6): 临时寄存器
 */

// CSR寄存器
/*
 * mstatus: 机器状态
 * mtvec: 机器陷阱向量
 * mepc: 机器异常PC
 * mcause: 机器陷阱原因
 * mie: 机器中断使能
 * mip: 机器中断挂起
 */
```

### 1.2 指令格式

```c
// RISC-V指令格式
/*
 * R型: [funct7 | rs2 | rs1 | funct3 | rd | opcode]
 * I型: [imm[11:0] | rs1 | funct3 | rd | opcode]
 * S型: [imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode]
 * B型: [imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode]
 * U型: [imm[31:12] | rd | opcode]
 * J型: [imm[20|10:1|11|19:12] | rd | opcode]
 */

// 常用指令
void riscv_instruction_examples(void) {
    // 算术指令
    __asm__ volatile("add x1, x2, x3");   // x1 = x2 + x3
    __asm__ volatile("sub x1, x2, x3");   // x1 = x2 - x3
    __asm__ volatile("and x1, x2, x3");   // x1 = x2 & x3
    __asm__ volatile("or x1, x2, x3");    // x1 = x2 | x3
    __asm__ volatile("xor x1, x2, x3");   // x1 = x2 ^ x3

    // 立即数指令
    __asm__ volatile("addi x1, x2, 100"); // x1 = x2 + 100
    __asm__ volatile("andi x1, x2, 0xFF");// x1 = x2 & 0xFF

    // 加载/存储
    __asm__ volatile("lw x1, 0(x2)");    // x1 = mem[x2]
    __asm__ volatile("sw x1, 0(x2)");    // mem[x2] = x1

    // 分支
    __asm__ volatile("beq x1, x2, label"); // if(x1==x2) goto label
    __asm__ volatile("bne x1, x2, label"); // if(x1!=x2) goto label
    __asm__ volatile("blt x1, x2, label"); // if(x1<x2) goto label

    // 跳转
    __asm__ volatile("jal ra, func");     // ra=PC+4, goto func
    __asm__ volatile("jalr ra, x1, 0");  // ra=PC+4, goto x1
}
```

---

## 二、特权模式

### 2.1 特权级别

```c
// 特权级别
typedef enum {
    PRV_U = 0,  // 用户模式
    PRV_S = 1,  // 监管模式
    PRV_M = 3,  // 机器模式
} privilege_level_t;

// mstatus寄存器
typedef struct {
    uint32_t mie   : 1;   // 全局中断使能
    uint32_t mpie  : 1;   // 之前的中断使能
    uint32_t mpp   : 2;   // 之前的特权级别
    uint32_t mprv  : 1;   // 修改特权
    uint32_t mxr   : 1;   // 使能读取可执行
    uint32_t tw    : 1;   // 等待中断
    uint32_t tsr   : 1;   // 陷阱SRET
} mstatus_t;

// 陷阱处理
void trap_handler(void) {
    uint32_t mcause;
    __asm__ volatile("csrr %0, mcause" : "=r"(mcause));

    if (mcause & 0x80000000) {
        // 中断
        uint32_t irq = mcause & 0xFF;
        handle_interrupt(irq);
    } else {
        // 异常
        uint32_t exception = mcause & 0xFF;
        handle_exception(exception);
    }
}
```

---

### 2.2 中断控制

```c
// 中断使能
void enable_interrupts(void) {
    __asm__ volatile("csrsi mstatus, 0x8");  // 设置mie位
}

void disable_interrupts(void) {
    __asm__ volatile("csrci mstatus, 0x8");  // 清除mie位
}

// 中断向量设置
void set_mtvec(void (*handler)(void)) {
    __asm__ volatile("csrw mtvec, %0" : : "r"(handler));
}

// 中断使能/禁用
void enable_irq(int irq) {
    uint32_t mie;
    __asm__ volatile("csrr %0, mie" : "=r"(mie));
    mie |= (1 << irq);
    __asm__ volatile("csrw mie, %0" : : "r"(mie));
}

void disable_irq(int irq) {
    uint32_t mie;
    __asm__ volatile("csrr %0, mie" : "=r"(mie));
    mie &= ~(1 << irq);
    __asm__ volatile("csrw mie, %0" : : "r"(mie));
}
```

---

## 三、ESP32-C3(RISC-V)

### 3.1 ESP32-C3特性

```c
// ESP32-C3特性
/*
 * - RISC-V单核，160MHz
 * - 400KB SRAM
 * - 384KB ROM
 * - WiFi + BLE 5.0
 * - 22个GPIO
 * - 2个SPI
 * - 1个I2C
 * - 2个UART
 * - 4个定时器
 * - ADC(2个12位)
 * - 温度传感器
 */

// ESP32-C3中断
void esp32c3_interrupt_init(void) {
    // 配置PLIC(平台级中断控制器)
    // 设置中断优先级
    // 使能中断
}

// ESP32-C3低功耗
void esp32c3_deep_sleep(uint32_t seconds) {
    // 配置唤醒定时器
    esp_sleep_enable_timer_wakeup(seconds * 1000000);

    // 进入深度睡眠
    esp_deep_sleep_start();
}
```

---

## 四、RISC-V汇编

### 4.1 汇编示例

```assembly
# RISC-V汇编示例
.section .text
.globl _start

_start:
    # 初始化栈指针
    la sp, _stack_top

    # 调用main函数
    call main

    # 无限循环
1:  j 1b

# 函数示例: 加法
add_func:
    add a0, a0, a1    # a0 = a0 + a1
    ret               # 返回

# 中断处理
trap_handler:
    # 保存上下文
    addi sp, sp, -128
    sw ra, 0(sp)
    sw t0, 4(sp)
    sw t1, 8(sp)
    # ... 保存其他寄存器

    # 读取mcause
    csrr t0, mcause
    csrr t1, mepc

    # 处理中断/异常
    call handle_trap

    # 恢复上下文
    lw ra, 0(sp)
    lw t0, 4(sp)
    lw t1, 8(sp)
    # ... 恢复其他寄存器
    addi sp, sp, 128

    # 返回
    mret
```

---

### 4.2 内联汇编

```c
// RISC-V内联汇编
// 读取CSR
uint32_t read_csr(uint32_t csr) {
    uint32_t value;
    __asm__ volatile("csrr %0, %1" : "=r"(value) : "i"(csr));
    return value;
}

// 写入CSR
void write_csr(uint32_t csr, uint32_t value) {
    __asm__ volatile("csrw %0, %1" : : "i"(csr), "r"(value));
}

// 原子操作
uint32_t atomic_add(volatile uint32_t *addr, uint32_t value) {
    uint32_t result;
    __asm__ volatile(
        "amoadd.w %0, %2, %1"
        : "=r"(result), "+A"(*addr)
        : "r"(value)
    );
    return result;
}

// 内存屏障
void memory_barrier(void) {
    __asm__ volatile("fence" ::: "memory");
}

// 等待中断
void wfi(void) {
    __asm__ volatile("wfi");
}
```

---

## 五、RISC-V开发环境

### 5.1 工具链

```bash
# RISC-V GNU工具链
# 编译
riscv32-unknown-elf-gcc -march=rv32imc -mabi=ilp32 -o firmware.elf main.c

# 反汇编
riscv32-unknown-elf-objdump -d firmware.elf

# 调试
riscv32-unknown-elf-gdb firmware.elf

# OpenOCD
openocd -f interface/ftdi/esp32_devkitj_v1.cfg -f target/esp32c3.cfg
```

### 5.2 SDK配置

```cmake
# CMakeLists.txt for RISC-V
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv32)

set(CMAKE_C_COMPILER riscv32-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER riscv32-unknown-elf-g++)

set(CMAKE_C_FLAGS "-march=rv32imc -mabi=ilp32")
set(CMAKE_CXX_FLAGS "-march=rv32imc -mabi=ilp32")

# 链接脚本
set(CMAKE_EXE_LINKER_FLAGS "-T ${CMAKE_SOURCE_DIR}/linker.ld")
```

---

## 附录：RISC-V扩展

| 扩展 | 功能 | 说明 |
|------|------|------|
| M | 乘除法 | 硬件乘除 |
| A | 原子操作 | 多核同步 |
| F | 单精度浮点 | 浮点运算 |
| D | 双精度浮点 | 高精度浮点 |
| C | 压缩指令 | 16位指令 |
| B | 位操作 | 位操作扩展 |

---

## 相关链接

- [[RISC-V开发详解]] - RISC-V基础
- [[ESP-IDF开发详解]] - ESP32开发
- [[计算机组成原理]] - CPU架构
- [[嵌入式系统基础]] - 嵌入式基础
