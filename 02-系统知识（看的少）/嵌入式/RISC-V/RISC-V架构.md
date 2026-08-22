# RISC-V架构

## 核心概念

- **RISC-V** - 开源指令集架构(ISA)
- **模块化** - 基础指令集 + 扩展指令集
- **特权模式** - Machine/Supervisor/User模式
- **向量扩展** - SIMD向量处理能力

---

## 一、RISC-V概述

### 1.1 发展历史

| 年份 | 事件 |
|------|------|
| 2010 | UC Berkeley启动项目 |
| 2014 | 正式发布ISA规范 |
| 2015 | RISC-V基金会成立 |
| 2019 | 华为、阿里等加入 |
| 2022 | 国际标准组织 |

---

### 1.2 RISC-V特点

**优势：**
- 开源免费
- 模块化设计
- 简洁高效
- 易于扩展
- 生态快速发展

**与ARM对比：**
| 特性 | RISC-V | ARM |
|------|--------|-----|
| 授权 | 开源 | 商业授权 |
| 指令集 | 可扩展 | 固定 |
| 生态 | 发展中 | 成熟 |
| 应用 | IoT、AI | 手机、服务器 |

---

### 1.3 RISC-V应用场景

| 场景 | 芯片 | 特点 |
|------|------|------|
| IoT | ESP32-C3/C6 | 低功耗、WiFi |
| AI | 平头哥玄铁 | 高性能 |
| 服务器 | SiFive P670 | 多核 |
| 汽车 | 芯来科技 | 功能安全 |

---

## 二、寄存器

### 2.1 通用寄存器

| 寄存器 | 别名 | 用途 | 调用约定 |
|--------|------|------|----------|
| x0 | zero | 常数0 | - |
| x1 | ra | 返回地址 | 调用者保存 |
| x2 | sp | 栈指针 | 被调用者保存 |
| x3 | gp | 全局指针 | - |
| x4 | tp | 线程指针 | - |
| x5-x7 | t0-t2 | 临时寄存器 | 调用者保存 |
| x8-x9 | s0-s1 | 保存寄存器 | 被调用者保存 |
| x10-x17 | a0-a7 | 函数参数/返回值 | 调用者保存 |
| x18-x27 | s2-s11 | 保存寄存器 | 被调用者保存 |
| x28-x31 | t3-t6 | 临时寄存器 | 调用者保存 |

---

### 2.2 控制状态寄存器(CSR)

| 寄存器 | 地址 | 说明 |
|--------|------|------|
| mstatus | 0x300 | 机器状态 |
| mtvec | 0x305 | 机器陷阱向量 |
| mepc | 0x341 | 机器异常PC |
| mcause | 0x342 | 机器陷阱原因 |
| mie | 0x304 | 机器中断使能 |
| mip | 0x344 | 机器中断挂起 |

---

### 2.3 浮点寄存器

| 寄存器 | 别名 | 用途 |
|--------|------|------|
| f0-f7 | ft0-ft7 | 临时浮点 |
| f8-f9 | fs0-fs1 | 保存浮点 |
| f10-f17 | fa0-fa7 | 浮点参数 |
| f18-f27 | fs2-fs11 | 保存浮点 |
| f28-f31 | ft8-ft11 | 临时浮点 |

---

## 三、指令集

### 3.1 基础指令集(RV32I)

**算术指令：**
```assembly
add x1, x2, x3      # x1 = x2 + x3
sub x1, x2, x3      # x1 = x2 - x3
addi x1, x2, 10     # x1 = x2 + 10
lui x1, 0x12345     # x1 = 0x12345000
auipc x1, 0x12345   # x1 = PC + 0x12345000
```

**逻辑指令：**
```assembly
and x1, x2, x3      # x1 = x2 & x3
or x1, x2, x3       # x1 = x2 | x3
xor x1, x2, x3      # x1 = x2 ^ x3
andi x1, x2, 0xFF   # x1 = x2 & 0xFF
ori x1, x2, 0xFF    # x1 = x2 | 0xFF
```

**移位指令：**
```assembly
sll x1, x2, x3      # x1 = x2 << x3
srl x1, x2, x3      # x1 = x2 >> x3 (逻辑)
sra x1, x2, x3      # x1 = x2 >> x3 (算术)
slli x1, x2, 2      # x1 = x2 << 2
```

**加载/存储指令：**
```assembly
lw x1, 0(x2)        # x1 = *(int32_t*)(x2)
lh x1, 0(x2)        # x1 = *(int16_t*)(x2)
lb x1, 0(x2)        # x1 = *(int8_t*)(x2)
sw x1, 0(x2)        # *(int32_t*)(x2) = x1
sh x1, 0(x2)        # *(int16_t*)(x2) = x1
sb x1, 0(x2)        # *(int8_t*)(x2) = x1
```

**分支指令：**
```assembly
beq x1, x2, label   # if (x1 == x2) goto label
bne x1, x2, label   # if (x1 != x2) goto label
blt x1, x2, label   # if (x1 < x2) goto label
bge x1, x2, label   # if (x1 >= x2) goto label
bltu x1, x2, label  # if ((unsigned)x1 < (unsigned)x2)
bgeu x1, x2, label  # if ((unsigned)x1 >= (unsigned)x2)
```

**跳转指令：**
```assembly
jal x1, label        # x1 = PC+4; goto label
jalr x1, x2, offset # x1 = PC+4; goto x2+offset
```

---

### 3.2 乘除扩展(M)

```assembly
mul x1, x2, x3      # x1 = x2 * x3 (低32位)
mulh x1, x2, x3     # x1 = (x2 * x3) >> 32 (有符号)
mulhu x1, x2, x3    # x1 = (x2 * x3) >> 32 (无符号)
div x1, x2, x3      # x1 = x2 / x3 (有符号)
divu x1, x2, x3     # x1 = x2 / x3 (无符号)
rem x1, x2, x3      # x1 = x2 % x3 (有符号)
remu x1, x2, x3     # x1 = x2 % x3 (无符号)
```

---

### 3.3 原子操作扩展(A)

```assembly
lr.w x1, (x2)       # Load Reserved
sc.w x1, x3, (x2)   # Store Conditional
amoswap.w x1, x2, (x3)  # Atomic Swap
amoadd.w x1, x2, (x3)   # Atomic Add
amoand.w x1, x2, (x3)   # Atomic AND
amoor.w x1, x2, (x3)    # Atomic OR
```

---

### 3.4 浮点扩展(F/D)

```assembly
fadd.s f1, f2, f3    # f1 = f2 + f3 (单精度)
fsub.s f1, f2, f3    # f1 = f2 - f3
fmul.s f1, f2, f3    # f1 = f2 * f3
fdiv.s f1, f2, f3    # f1 = f2 / f3
fsqrt.s f1, f2       # f1 = sqrt(f2)
fmadd.s f1, f2, f3, f4  # f1 = f2*f3 + f4

flw f1, 0(x2)        # 加载单精度浮点
fsw f1, 0(x2)        # 存储单精度浮点

fcvt.w.s x1, f2      # 浮点转整数
fcvt.s.w f1, x2      # 整数转浮点
```

---

### 3.5 向量扩展(V)

```assembly
vsetvli t0, a0, e32, m1  # 设置向量长度
vle32.v v1, (a1)         # 加载向量
vse32.v v1, (a2)         # 存储向量
vadd.vv v1, v2, v3       # 向量加法
vsub.vv v1, v2, v3       # 向量减法
vmul.vv v1, v2, v3       # 向量乘法
vfmul.vv v1, v2, v3      # 浮点向量乘法
```

---

## 四、特权模式

### 4.1 特权级别

| 级别 | 编号 | 说明 | 应用 |
|------|------|------|------|
| Machine | 3 | 最高特权 | Bootloader |
| Supervisor | 1 | 操作系统 | Linux |
| User | 0 | 用户程序 | 应用 |

---

### 4.2 Machine模式

**功能：**
- 内存保护(PMP)
- 中断处理
- 定时器
- 调试支持

**PMP配置：**
```assembly
# 配置PMP区域
li t0, 0x80000000    # 起始地址
csrw pmpaddr0, t0
li t0, 0x0F          # R/W/X权限
csrw pmpcfg0, t0
```

---

### 4.3 Supervisor模式

**功能：**
- 虚拟内存(Sv32/Sv39/Sv48)
- 异常处理
- 中断委托

**页表配置：**
```assembly
# 配置页表
la t0, page_table
srli t0, t0, 12
csrw satp, t0
```

---

## 五、中断与异常

### 5.1 异常类型

| 编号 | 类型 | 说明 |
|------|------|------|
| 0 | 指令地址未对齐 | 取指地址错误 |
| 1 | 指令访问错误 | 取指权限错误 |
| 2 | 非法指令 | 未定义指令 |
| 3 | 断点 | ebreak指令 |
| 4 | 加载地址未对齐 | 读地址错误 |
| 5 | 加载访问错误 | 读权限错误 |
| 6 | 存储地址未对齐 | 写地址错误 |
| 7 | 存储访问错误 | 写权限错误 |
| 8 | 环境调用 | ecall指令 |

---

### 5.2 中断类型

| 编号 | 类型 | 说明 |
|------|------|------|
| 3 | 软件中断 | M模式软件中断 |
| 7 | 定时器中断 | M模式定时器 |
| 11 | 外部中断 | M模式外部中断 |
| 9 | 软件中断 | S模式软件中断 |
| 5 | 定时器中断 | S模式定时器 |
| 1 | 外部中断 | S模式外部中断 |

---

### 5.3 中断处理

```assembly
# 中断向量表
.section .text.mtvec
.align 2
mtvec_handler:
    # 保存上下文
    addi sp, sp, -128
    sw ra, 0(sp)
    sw t0, 4(sp)
    # ... 保存其他寄存器
    
    # 读取中断原因
    csrr t0, mcause
    bltz t0, interrupt_handler
    
exception_handler:
    # 异常处理
    j exit_handler
    
interrupt_handler:
    # 中断处理
    andi t0, t0, 0x3FF
    li t1, 7
    beq t0, t1, timer_handler
    li t1, 11
    beq t0, t1, external_handler
    
timer_handler:
    # 定时器处理
    j exit_handler
    
external_handler:
    # 外部中断处理
    j exit_handler
    
exit_handler:
    # 恢复上下文
    lw ra, 0(sp)
    lw t0, 4(sp)
    # ... 恢复其他寄存器
    addi sp, sp, 128
    mret
```

---

## 六、RISC-V开发

### 6.1 开发工具链

| 工具 | 说明 |
|------|------|
| GCC | GNU编译器 |
| Clang | LLVM编译器 |
| OpenOCD | 调试器 |
| QEMU | 模拟器 |
| FreedomStudio | SiFive IDE |

**安装工具链：**
```bash
# Ubuntu
sudo apt install gcc-riscv64-unknown-elf
sudo apt install gdb-multiarch

# 或下载SiFive工具链
wget https://github.com/sifive/freedom-tools/releases
```

---

### 6.2 编译选项

```bash
# 编译
riscv64-unknown-elf-gcc -march=rv32imac -mabi=ilp32 \
    -nostdlib -nostartfiles \
    -T linker.ld \
    -o output.elf \
    main.c startup.S

# 反汇编
riscv64-unknown-elf-objdump -d output.elf

# 转换为二进制
riscv64-unknown-elf-objcopy -O binary output.elf output.bin
```

---

### 6.3 链接脚本

```ld
/* linker.ld */
MEMORY
{
    FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 1024K
    RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 256K
}

SECTIONS
{
    .text : {
        *(.text.mtvec)      /* 中断向量表 */
        *(.text.startup)    /* 启动代码 */
        *(.text*)           /* 代码 */
    } > FLASH
    
    .rodata : {
        *(.rodata*)
    } > FLASH
    
    .data : {
        *(.data*)
    } > RAM AT > FLASH
    
    .bss : {
        *(.bss*)
    } > RAM
}
```

---

### 6.4 启动代码

```assembly
# startup.S
.section .text.startup
.global _start

_start:
    # 设置栈指针
    la sp, _stack_top
    
    # 清除BSS段
    la t0, _bss_start
    la t1, _bss_end
bss_clear:
    bge t0, t1, bss_done
    sw zero, 0(t0)
    addi t0, t0, 4
    j bss_clear
bss_done:
    
    # 跳转到main
    call main
    
    # 死循环
hang:
    j hang
```

---

## 七、RISC-V与ESP32

### 7.1 ESP32-C3

**特点：**
- RISC-V单核
- 160MHz
- WiFi + BLE 5.0
- 400KB SRAM

**ESP-IDF支持：**
```bash
idf.py set-target esp32c3
idf.py build
```

---

### 7.2 ESP32-C6

**特点：**
- RISC-V单核
- 160MHz
- WiFi 6 + BLE 5.0 + Thread/Zigbee
- 512KB SRAM

**应用：** Matter设备、智能家居

---

## 八、RISC-V生态

### 8.1 芯片厂商

| 厂商 | 芯片 | 特点 |
|------|------|------|
| SiFive | U74, P670 | 高性能核心 |
| 平头哥 | 玄铁910 | AIoT |
| 芯来科技 | N200, N300 | 嵌入式 |
| 兆易创新 | GD32VF103 | MCU |
| 乐鑫 | ESP32-C3/C6 | WiFi/BLE |

---

### 8.2 操作系统支持

| 操作系统 | 说明 |
|----------|------|
| Linux | 完整支持 |
| FreeRTOS | ESP32-C3/C6 |
| RT-Thread | 完整支持 |
| Zephyr | 完整支持 |
| NuttX | 完整支持 |

---

### 8.3 开发板

| 开发板 | 芯片 | 价格 | 特点 |
|--------|------|------|------|
| ESP32-C3-DevKitC | ESP32-C3 | ¥30 | WiFi/BLE |
| ESP32-C6-DevKitC | ESP32-C6 | ¥50 | WiFi6/Thread |
| Sipeed Longan | GD32VF103 | ¥30 | 入门级 |
| SiFive HiFive1 | FE310 | ¥200 | 官方开发板 |

---

## 附录：指令速查表

### RV32I基础指令

| 类型 | 指令 | 说明 |
|------|------|------|
| 算术 | add, sub, addi | 加减 |
| 逻辑 | and, or, xor, andi | 逻辑运算 |
| 移位 | sll, srl, sra, slli | 移位 |
| 加载 | lw, lh, lb | 加载 |
| 存储 | sw, sh, sb | 存储 |
| 分支 | beq, bne, blt, bge | 条件分支 |
| 跳转 | jal, jalr | 无条件跳转 |

### RV32M乘除指令

| 指令 | 说明 |
|------|------|
| mul | 乘法 |
| mulh | 高位乘法 |
| div | 除法 |
| rem | 取余 |

### RV32F浮点指令

| 指令 | 说明 |
|------|------|
| fadd.s | 浮点加法 |
| fsub.s | 浮点减法 |
| fmul.s | 浮点乘法 |
| fdiv.s | 浮点除法 |

---

## 相关链接

- [[计算机组成原理]] - CPU架构基础
- [[ARM体系结构]] - ARM对比
- [[嵌入式Linux]] - Linux on RISC-V
