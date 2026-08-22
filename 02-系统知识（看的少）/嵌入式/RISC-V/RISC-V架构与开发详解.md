---
title: RISC-V架构与开发详解
tags:
  - RISC-V
  - 嵌入式
  - 指令集架构
  - ISA
date: 2026-06-21
---

# RISC-V架构与开发详解

## 目录

- [[#1. RISC-V概述]]
- [[#2. 指令集架构]]
- [[#3. 扩展指令集]]
- [[#4. 特权级]]
- [[#5. 中断与异常]]
- [[#6. 内存管理]]
- [[#7. RISC-V vs ARM对比]]
- [[#8. 常用RISC-V芯片]]
- [[#9. RISC-V开发工具链]]
- [[#10. RISC-V汇编编程]]
- [[#11. 嵌入式RISC-V开发实战]]

---

## 1. RISC-V概述

### 1.1 什么是RISC-V

RISC-V（读作"RISC-Five"）是一个**开源的指令集架构（ISA）**，由加州大学伯克利分校（UC Berkeley）于2010年发起。它是继x86、ARM之后的第三大处理器架构生态，其核心设计理念是：

- **完全开源**：ISA规范免费开放，任何人可以设计、制造、销售RISC-V芯片，无需授权费
- **模块化设计**：基础指令集 + 可选扩展，按需裁剪
- **简洁优雅**：避免历史包袱，指令编码规整
- **广泛适用**：从8位微控制器到高性能服务器均可覆盖

### 1.2 RISC-V的历史

| 时间 | 事件 |
|------|------|
| 2010 | UC Berkeley启动RISC-V项目 |
| 2014 | 发布RISC-V用户级ISA规范v2.0 |
| 2015 | RISC-V基金会成立 |
| 2019 | 基金会总部迁至瑞士（避免地缘政治影响） |
| 2021 | 发布规范v20191213（稳定版） |
| 2023 | Vector扩展v1.0成为标准 |

### 1.3 基础指令集

RISC-V有两个基础整数指令集：

| 指令集 | 字长 | 地址空间 | 寄存器宽度 | 典型用途 |
|--------|------|----------|------------|----------|
| **RV32I** | 32位 | 4GB | 32位 | 嵌入式微控制器 |
| **RV64I** | 64位 | 256TB | 64位 | 应用处理器、服务器 |

此外还有实验性的 **RV128I**（128位），目前尚未广泛使用。

### 1.4 模块化命名约定

RISC-V的完整ISA名称遵循标准命名格式：

```
RV{XLEN}{extensions}
```

示例：
- **RV32IMAC**：32位基础指令集 + 整数乘除(M) + 原子操作(A) + 压缩指令(C)
- **RV64GC**：64位基础指令集 + G(=IMAFD) + C，这是最常见的通用配置
- **RV32IMFC**：32位 + 乘除 + 单精度浮点 + 压缩，常见于嵌入式

### 1.5 为什么选择RISC-V

1. **零授权费**：降低芯片设计成本，尤其利于中小公司和学术研究
2. **自主可控**：不受国外ISA授权限制，适合国产芯片战略
3. **生态快速发展**：Linux主线支持、GCC/LLVM工具链成熟
4. **灵活性**：可通过自定义指令扩展实现领域专用加速
5. **低功耗**：精简指令集天然适合低功耗嵌入式场景

---

## 2. 指令集架构

### 2.1 通用寄存器

RISC-V定义了 **32个通用寄存器**（x0-x31），在RV64下为64位宽，RV32下为32位宽。

| 寄存器 | ABI名称 | 用途 | 调用约定 |
|--------|---------|------|----------|
| x0 | zero | 硬编码为0 | 常量零 |
| x1 | ra | 返回地址 | Caller-saved |
| x2 | sp | 栈指针 | Callee-saved |
| x3 | gp | 全局指针 | - |
| x4 | tp | 线程指针 | - |
| x5-x7 | t0-t2 | 临时寄存器 | Caller-saved |
| x8 | s0/fp | 保存寄存器/帧指针 | Callee-saved |
| x9 | s1 | 保存寄存器 | Callee-saved |
| x10-x11 | a0-a1 | 函数参数/返回值 | Caller-saved |
| x12-x17 | a2-a7 | 函数参数 | Caller-saved |
| x18-x27 | s2-s11 | 保存寄存器 | Callee-saved |
| x28-x31 | t3-t6 | 临时寄存器 | Caller-saved |

关键特点：
- **x0恒为零**：读取始终返回0，写入丢弃。这简化了很多指令设计
- **没有专用的标志寄存器**（对比ARM的CPSR）：比较结果写入通用寄存器
- **没有PC寄存器可直接读取**：通过`auipc`间接获取

### 2.2 指令格式

RISC-V有 **6种基本指令格式**，所有指令均为32位（RV32/RV64）或16位（C扩展）：

#### R型（寄存器-寄存器操作）

```
31      25 24   20 19   15 14  12 11    7 6      0
+---------+-------+-------+------+--------+--------+
| funct7  |  rs2  |  rs1  |funct3|   rd   | opcode |
+---------+-------+-------+------+--------+--------+
  7 bits    5 bits  5 bits  3 bits 5 bits   7 bits
```

用于：`ADD`, `SUB`, `SLL`, `XOR`, `SRL`, `SRA`, `OR`, `AND` 等

#### I型（立即数操作）

```
31              20 19   15 14  12 11    7 6      0
+-----------------+-------+------+--------+--------+
|    imm[11:0]    |  rs1  |funct3|   rd   | opcode |
+-----------------+-------+------+--------+--------+
    12 bits         5 bits  3 bits 5 bits   7 bits
```

用于：`ADDI`, `LW`, `JALR`, `SLTI`, `XORI`, `LH`, `LB` 等

#### S型（存储指令）

```
31      25 24   20 19   15 14  12 11    7 6      0
+---------+-------+-------+------+--------+--------+
|imm[11:5]|  rs2  |  rs1  |funct3|imm[4:0]| opcode |
+---------+-------+-------+------+--------+--------+
  7 bits    5 bits  5 bits  3 bits  5 bits   7 bits
```

用于：`SW`, `SH`, `SB` 等存储指令

#### B型（条件分支）

```
31    30     25 24   20 19   15 14  12 11    8  7   6      0
+------+-------+-------+-------+------+-------+----+--------+
|imm12 |imm[10:5]|  rs2  |  rs1  |funct3|imm[4:1]|imm11| opcode|
+------+-------+-------+-------+------+-------+----+--------+
 1 bit   6 bits  5 bits  5 bits  3 bits  4 bits  1 bit 7 bits
```

用于：`BEQ`, `BNE`, `BLT`, `BGE`, `BLTU`, `BGEU` 等

#### U型（高位立即数）

```
31                              12 11    7 6      0
+----------------------------------+--------+--------+
|          imm[31:12]              |   rd   | opcode |
+----------------------------------+--------+--------+
            20 bits                 5 bits   7 bits
```

用于：`LUI`（加载高位立即数）, `AUIPC`（PC加高位立即数）

#### J型（跳转）

```
31    30        21 20   19          12 11    7 6      0
+------+---------+----+--------------+--------+--------+
|imm20 |imm[10:1]|imm11|  imm[19:12] |   rd   | opcode |
+------+---------+----+--------------+--------+--------+
 1 bit   10 bits  1 bit   8 bits      5 bits   7 bits
```

用于：`JAL`（跳转并链接）

### 2.3 常用指令分类

#### 算术指令

```assembly
ADD  rd, rs1, rs2      # rd = rs1 + rs2
ADDI rd, rs1, imm      # rd = rs1 + imm (12位有符号)
SUB  rd, rs1, rs2      # rd = rs1 - rs2
LUI  rd, imm           # rd = imm << 12（加载20位高位）
AUIPC rd, imm          # rd = PC + (imm << 12)
```

#### 逻辑指令

```assembly
AND  rd, rs1, rs2      # rd = rs1 & rs2
ANDI rd, rs1, imm      # rd = rs1 & imm
OR   rd, rs1, rs2      # rd = rs1 | rs2
ORI  rd, rs1, imm      # rd = rs1 | imm
XOR  rd, rs1, rs2      # rd = rs1 ^ rs2
XORI rd, rs1, imm      # rd = rs1 ^ imm
```

#### 移位指令

```assembly
SLL  rd, rs1, rs2      # rd = rs1 << rs2 (逻辑左移)
SLLI rd, rs1, shamt    # rd = rs1 << shamt
SRL  rd, rs1, rs2      # rd = rs1 >> rs2 (逻辑右移)
SRLI rd, rs1, shamt    # rd = rs1 >> shamt
SRA  rd, rs1, rs2      # rd = rs1 >> rs2 (算术右移)
SRAI rd, rs1, shamt    # rd = rs1 >> shamt
```

#### 比较指令

```assembly
SLT   rd, rs1, rs2     # rd = (rs1 < rs2) ? 1 : 0 (有符号)
SLTU  rd, rs1, rs2     # rd = (rs1 < rs2) ? 1 : 0 (无符号)
SLTI  rd, rs1, imm     # rd = (rs1 < imm) ? 1 : 0 (有符号)
SLTIU rd, rs1, imm     # rd = (rs1 < imm) ? 1 : 0 (无符号)
```

#### 分支指令

```assembly
BEQ  rs1, rs2, offset  # if (rs1 == rs2) PC += offset
BNE  rs1, rs2, offset  # if (rs1 != rs2) PC += offset
BLT  rs1, rs2, offset  # if (rs1 < rs2) PC += offset (有符号)
BGE  rs1, rs2, offset  # if (rs1 >= rs2) PC += offset (有符号)
BLTU rs1, rs2, offset  # if (rs1 < rs2) PC += offset (无符号)
BGEU rs1, rs2, offset  # if (rs1 >= rs2) PC += offset (无符号)
```

#### 跳转指令

```assembly
JAL  rd, offset        # rd = PC+4; PC += offset (跳转并链接)
JALR rd, rs1, offset   # rd = PC+4; PC = (rs1 + offset) & ~1
```

#### 加载/存储指令

```assembly
LB   rd, offset(rs1)   # rd = SignExtend(Mem[rs1+offset][7:0])
LH   rd, offset(rs1)   # rd = SignExtend(Mem[rs1+offset][15:0])
LW   rd, offset(rs1)   # rd = SignExtend(Mem[rs1+offset][31:0])
LBU  rd, offset(rs1)   # rd = ZeroExtend(Mem[rs1+offset][7:0])
LHU  rd, offset(rs1)   # rd = ZeroExtend(Mem[rs1+offset][15:0])
SB   rs2, offset(rs1)  # Mem[rs1+offset][7:0] = rs2[7:0]
SH   rs2, offset(rs1)  # Mem[rs1+offset][15:0] = rs2[15:0]
SW   rs2, offset(rs1)  # Mem[rs1+offset][31:0] = rs2[31:0]
```

在RV64中额外提供：
```assembly
LWU  rd, offset(rs1)   # 无符号加载32位
LD   rd, offset(rs1)   # 加载64位
SD   rs2, offset(rs1)  # 存储64位
```

---

## 3. 扩展指令集

### 3.1 M扩展 — 整数乘除法

提供硬件乘法和除法操作，避免用软件模拟：

```assembly
MUL    rd, rs1, rs2    # rd = (rs1 * rs2)[31:0]   乘法低32位
MULH   rd, rs1, rs2    # rd = (rs1 * rs2)[63:32]  有符号×有符号高32位
MULHSU rd, rs1, rs2    # rd = (rs1 * rs2)[63:32]  有符号×无符号高32位
MULHU  rd, rs1, rs2    # rd = (rs1 * rs2)[63:32]  无符号×无符号高32位
DIV    rd, rs1, rs2    # rd = rs1 / rs2 (有符号)
DIVU   rd, rs1, rs2    # rd = rs1 / rs2 (无符号)
REM    rd, rs1, rs2    # rd = rs1 % rs2 (有符号)
REMU   rd, rs1, rs2    # rd = rs1 % rs2 (无符号)
```

注意事项：
- 乘法结果分为低半部分（MUL）和高半部分（MULH等）
- 除以零不会产生异常，而是返回特定值（DIV返回-1，REM返回被除数）
- 在RV64中，还有 `MULW`、`DIVW` 等32位宽度变体

### 3.2 A扩展 — 原子操作

支持多处理器/多线程环境下的原子内存操作：

```assembly
LR.W      rd, (rs1)          # Load-Reserved，加载并标记
SC.W      rd, rs2, (rs1)     # Store-Conditional，条件存储
AMOSWAP.W rd, rs2, (rs1)     # 原子交换
AMOADD.W  rd, rs2, (rs1)     # 原子加
AMOAND.W  rd, rs2, (rs1)     # 原子与
AMOOR.W   rd, rs2, (rs1)     # 原子或
AMOXOR.W  rd, rs2, (rs1)     # 原子异或
AMOMAX.W  rd, rs2, (rs1)     # 原子取最大值(有符号)
AMOMINU.W rd, rs2, (rs1)     # 原子取最小值(无符号)
```

LR/SC模式实现自旋锁：

```assembly
# 获取锁 (a0 = 锁地址)
spin_lock:
    li    t0, 1
1:  lr.w  t1, (a0)          # 加载保留
    bnez  t1, 1b            # 非零则重试
    sc.w  t1, t0, (a0)      # 条件存储
    bnez  t1, 1b            # 失败则重试
    ret

# 释放锁
spin_unlock:
    sw    zero, (a0)        # 直接清零
    ret
```

### 3.3 C扩展 — 压缩指令

将常用指令编码为 **16位**（标准为32位），减少代码体积：

| 特点 | 说明 |
|------|------|
| 代码密度 | 平均减少25-30%代码大小 |
| 兼容性 | 与32位指令可自由混合 |
| 寄存器限制 | 部分指令仅能访问x8-x15（s0-s1, a0-a5） |
| 立即数范围 | 缩小的立即数范围 |

常见压缩指令示例：

```assembly
C.LI    rd, imm        # 加载小立即数 (-32~31)
C.MV    rd, rs2        # 寄存器移动
C.ADD   rd, rs2        # 寄存器加法
C.LW    rd, offset(rs1) # 加载字
C.SW    rs2, offset(rs1) # 存储字
C.BEQZ  rs1, offset    # 分支等于零
C.BNEZ  rs1, offset    # 分支不等于零
C.J     offset         # 无条件跳转
C.JR    rs1            # 寄存器跳转
C.JALR  rs1            # 跳转并链接
C.NOP                   # 空操作
```

### 3.4 F扩展 — 单精度浮点

提供32个32位浮点寄存器（f0-f31）和IEEE 754单精度运算：

```assembly
FADD.S   fd, fs1, fs2    # fd = fs1 + fs2
FSUB.S   fd, fs1, fs2    # fd = fs1 - fs2
FMUL.S   fd, fs1, fs2    # fd = fs1 * fs2
FDIV.S   fd, fs1, fs2    # fd = fs1 / fs2
FSQRT.S  fd, fs1         # fd = sqrt(fs1)
FMADD.S  fd, fs1, fs2, fs3  # fd = fs1*fs2 + fs3
FLW      fd, offset(rs1) # 加载单精度浮点
FSW      fs2, offset(rs1) # 存储单精度浮点
FCVT.S.W fd, rs1         # 整数转浮点
FCVT.W.S rd, fs1         # 浮点转整数
FMV.X.W  rd, fs1         # 浮点位模式移到整数寄存器
FMV.W.X  fd, rs1         # 整数位模式移到浮点寄存器
```

### 3.5 D扩展 — 双精度浮点

在F扩展基础上增加64位双精度支持（f0-f31扩展为64位）：

```assembly
FADD.D   fd, fs1, fs2
FSUB.D   fd, fs1, fs2
FMUL.D   fd, fs1, fs2
FDIV.D   fd, fs1, fs2
FSQRT.D  fd, fs1
FLD      fd, offset(rs1)  # 加载双精度
FSD      fs2, offset(rs1)  # 存储双精度
FCVT.D.S fd, fs1           # 单精度转双精度
FCVT.S.D fd, fs1           # 双精度转单精度
```

### 3.6 V扩展 — 向量扩展

RISC-V Vector（RVV）v1.0 是可变长度向量指令集，设计原则：

- **向量长度无关（VLA）**：代码在不同向量长度的硬件上都能运行
- **寄存器分组**：32个向量寄存器v0-v31，宽度由硬件决定（VLEN）
- **掩码操作**：支持逐元素掩码控制

核心指令：

```assembly
VSETVLI   rd, rs1, vtypei    # 设置向量长度和类型
VLE8.V    vd, (rs1)          # 向量加载8位元素
VLE16.V   vd, (rs1)          # 向量加载16位元素
VLE32.V   vd, (rs1)          # 向量加载32位元素
VSE32.V   vs3, (rs1)         # 向量存储
VADD.VV   vd, vs2, vs1       # 向量加 (向量+向量)
VADD.VX   vd, vs2, rs1       # 向量加 (向量+标量)
VMUL.VV   vd, vs2, vs1       # 向量乘
VSLL.VX   vd, vs2, rs1       # 向量左移
VMSEQ.VV  vd, vs2, vs1       # 向量比较等于
```

向量编程示例 — 向量点积：

```assembly
# a0 = 向量A地址, a1 = 向量B地址, a2 = 长度
vector_dot_product:
    vsetvli t0, a2, e32, m1   # 32位元素
    vle32.v v0, (a0)           # 加载向量A
    vle32.v v1, (a1)           # 加载向量B
    vmul.vv v2, v0, v1         # 逐元素相乘
    vredsum.vs v3, v2, v3      # 归约求和
    sub     a2, a2, t0         # 剩余长度
    slli    t0, t0, 2          # 字节偏移
    add     a0, a0, t0
    add     a1, a1, t0
    bnez    a2, vector_dot_product
    ret
```

---

## 4. 特权级

### 4.1 特权模式概述

RISC-V定义了三个主要特权级（从高到低）：

| 模式 | 缩写 | 编码 | 用途 |
|------|------|------|------|
| Machine Mode | M-mode | 11 | 最高权限，固件/Bootloader |
| Supervisor Mode | S-mode | 01 | 操作系统内核 |
| User Mode | U-mode | 00 | 用户应用程序 |

典型嵌入式系统可能仅使用M-mode，而运行Linux的系统需要M+S+U三级。

### 4.2 控制状态寄存器（CSR）

CSR是特权模式下的配置和状态寄存器，地址空间为12位（4096个CSR）：

#### M-mode核心CSR

| CSR | 地址 | 用途 |
|-----|------|------|
| `mvendorid` | 0xF11 | 厂商ID |
| `marchid` | 0xF12 | 架构ID |
| `mimpid` | 0xF13 | 实现ID |
| `mhartid` | 0xF14 | 硬件线程ID |
| `mstatus` | 0x300 | 机器状态寄存器 |
| `misa` | 0x301 | ISA支持信息 |
| `mie` | 0x304 | 中断使能 |
| `mtvec` | 0x305 | 陷阱向量基地址 |
| `mepc` | 0x341 | 异常PC |
| `mcause` | 0x342 | 陷阱原因 |
| `mtval` | 0x343 | 陷阱附加信息 |
| `mip` | 0x344 | 中断待处理 |
| `mscratch` | 0x340 | M-mode暂存寄存器 |
| `mcycle` | 0xB00 | 周期计数器 |
| `minstret` | 0xB02 | 指令计数器 |

#### mstatus寄存器关键位

```
Bit  名称      含义
3    MIE       M-mode中断全局使能
7    MPIE      进入异常前的MIE值
11   MPP[1:0]  进入M-mode前的特权级
17   MPRV      内存访问使用MPP指定的权限
```

#### S-mode核心CSR

| CSR | 地址 | 用途 |
|-----|------|------|
| `sstatus` | 0x100 | Supervisor状态 |
| `sie` | 0x104 | S-mode中断使能 |
| `stvec` | 0x105 | S-mode陷阱向量 |
| `sepc` | 0x141 | S-mode异常PC |
| `scause` | 0x142 | S-mode陷阱原因 |
| `stval` | 0x143 | S-mode陷阱附加信息 |
| `sip` | 0x144 | S-mode中断待处理 |
| `sscratch` | 0x140 | S-mode暂存 |
| `satp` | 0x180 | 地址转换与保护 |

### 4.3 CSR操作指令

```assembly
CSRRW  rd, csr, rs1    # rd = CSR; CSR = rs1 (原子读写)
CSRRS  rd, csr, rs1    # rd = CSR; CSR |= rs1 (原子读置位)
CSRRC  rd, csr, rs1    # rd = CSR; CSR &= ~rs1 (原子读清位)
CSRRWI rd, csr, uimm   # rd = CSR; CSR = uimm (立即数版本)
CSRRSI rd, csr, uimm   # rd = CSR; CSR |= uimm
CSRRCI rd, csr, uimm   # rd = CSR; CSR &= ~uimm
```

常用伪指令：

```assembly
CSRR  rd, csr        # 读CSR → 等价于 CSRRS rd, csr, x0
CSRW  csr, rs1       # 写CSR → 等价于 CSRRW x0, csr, rs1
CSRS  csr, rs1       # 置位CSR → 等价于 CSRRS x0, csr, rs1
CSRC  csr, rs1       # 清位CSR → 等价于 CSRRC x0, csr, rs1
```

---

## 5. 中断与异常

### 5.1 异常分类

RISC-V中，**异常（Exception）** 是指令执行产生的同步事件，**中断（Interrupt）** 是异步外部事件。

#### 异常原因码（mcause）

| 编码 | 类型 | 描述 |
|------|------|------|
| 0 |  | 指令地址未对齐 |
| 1 |  | 指令访问错误 |
| 2 |  | 非法指令 |
| 3 |  | 断点（EBREAK） |
| 4 |  | 加载地址未对齐 |
| 5 |  | 加载访问错误 |
| 6 |  | 存储地址未对齐 |
| 7 |  | 存储访问错误 |
| 8 |  | U-mode环境调用（ecall） |
| 9 |  | S-mode环境调用 |
| 11 |  | M-mode环境调用 |
| 12 |  | 指令页错误 |
| 13 |  | 加载页错误 |
| 15 |  | 存储页错误 |

中断原因码的最高位为1（有符号负数）：

| 编码（有符号） | 类型 | 描述 |
|------|------|------|
| -1 (0x80000000) |  | 软件中断（M-mode） |
| -3 (0x80000002) |  | 软件中断（S-mode） |
| -5 (0x80000004) |  | 定时器中断（M-mode） |
| -7 (0x80000006) |  | 定时器中断（S-mode） |
| -9 (0x80000008) |  | 外部中断（M-mode） |
| -11 (0x8000000A) |  | 外部中断（S-mode） |

### 5.2 CLINT — 核心本地中断器

CLINT（Core Local Interruptor）提供每个Hart（硬件线程）的本地中断：

| 组件 | 偏移 | 功能 |
|------|------|------|
| `msip` | 0x0000 | 软件中断待处理寄存器 |
| `mtimecmp` | 0x4000 | 定时器比较值（每个Hart一个） |
| `mtime` | 0xBFF8 | 全局计时器（64位） |

定时器中断触发条件：当 `mtime >= mtimecmp` 时触发。

#### 定时器中断配置示例

```c
// 设置定时器（以N个周期后触发为例）
#define CLINT_BASE    0x02000000UL
#define MTIME         (*(volatile uint64_t *)(CLINT_BASE + 0xBFF8))
#define MTIMECMP(hart) (*(volatile uint64_t *)(CLINT_BASE + 0x4000 + (hart)*8))

void setup_timer(uint64_t delay) {
    MTIMECMP(0) = MTIME + delay;  // 设置比较值
    // 使能M-mode定时器中断
    asm volatile("csrs mie, %0" :: "r"(1 << 7));  // MTIE
    asm volatile("csrs mstatus, %0" :: "r"(1 << 3)); // MIE
}
```

### 5.3 PLIC — 平台级中断控制器

PLIC管理外部设备中断，支持优先级仲裁：

| 组件 | 功能 |
|------|------|
| Priority Register | 每个中断源的优先级（0=禁用） |
| Pending Register | 中断待处理状态 |
| Enable Register | 每个Hart的中断使能 |
| Threshold Register | 优先级阈值（低于此值的中断不发送） |
| Claim/Complete | 中断认领和完成 |

典型PLIC地址映射（QEMU virt机器）：

```
0x0C000000 - 优先级寄存器
0x0C001000 - Pending位
0x0C002000 - Enable位
0x0C200000 - Threshold + Claim/Complete
```

#### 中断处理流程

```
外部设备中断
    |
    v
PLIC仲裁（优先级比较）
    |
    v
设置Hart的外部中断pending位
    |
    v
Hart检测到中断（mip.MEIP=1）
    |
    v
如果 mie.MEIP=1 且 mstatus.MIE=1：
    1. mepc ← PC（保存当前PC）
    2. mcause ← 中断原因码
    3. mstatus.MPIE ← mstatus.MIE
    4. mstatus.MIE ← 0（关中断）
    5. PC ← mtvec（跳转到中断向量）
    |
    v
中断处理程序
    1. 保存上下文
    2. claim = *(PLIC_CLAIM)  // 认领中断
    3. 处理中断
    4. *(PLIC_CLAIM) = claim  // 完成中断
    5. 恢复上下文
    6. MRET
    |
    v
MRET指令：
    1. PC ← mepc
    2. mstatus.MIE ← mstatus.MPIE
    3. mstatus.MPIE ← 1
```

### 5.4 mtvec中断向量模式

`mtvec`寄存器有两种模式：

```
mtvec[1:0] = 00: Direct模式 — 所有陷阱跳转到BASE地址
mtvec[1:0] = 01: Vectored模式 — 中断跳转到BASE+4*cause，异常跳转到BASE
```

Direct模式中断入口示例：

```assembly
.section .text
.align 2
trap_handler:
    # 保存上下文
    addi sp, sp, -32*8
    sd   ra, 0*8(sp)
    sd   t0, 1*8(sp)
    # ... 保存所有寄存器

    csrr t0, mcause
    bltz t0, handle_interrupt   # 最高位为1则为中断

handle_exception:
    # 处理异常
    j    restore_context

handle_interrupt:
    andi t0, t0, 0x3F           # 提取中断编号
    # 根据编号分发到具体处理函数

restore_context:
    ld   ra, 0*8(sp)
    ld   t0, 1*8(sp)
    # ... 恢复所有寄存器
    addi sp, sp, 32*8
    mret
```

---

## 6. 内存管理

### 6.1 PMP — 物理内存保护

PMP（Physical Memory Protection）是M-mode下用于限制其他模式内存访问的机制：

- 最多支持 **16个PMP区域**（pmp0cfg-pmp15cfg）
- 每个区域可配置：读(R)、写(W)、执行(X)权限
- 支持两种地址匹配模式：TOR（顶部范围）和 NAPOT（自然对齐的2的幂次方）

#### PMP配置寄存器

| CSR | 功能 |
|-----|------|
| `pmpcfg0-pmpcfg3` | PMP配置（每个寄存器包含4个8位配置） |
| `pmpaddr0-pmpaddr15` | PMP地址寄存器 |

每个PMP配置（8位）的格式：

```
Bit 7:   L (锁定，只能M-mode修改)
Bit 6:5: 保留
Bit 4:3: A (地址匹配模式: 00=关闭, 01=TOR, 10=NAPOT, 11=NA4)
Bit 2:   X (执行权限)
Bit 1:   W (写权限)
Bit 0:   R (读权限)
```

#### PMP配置示例

```c
// 配置pmp0: 保护0x80000000-0x8000FFFF (64KB)
void pmp_config(void) {
    // 设置地址范围 (NAPOT模式)
    // pmpaddr = (base >> 2) | ((size/2 - 1) >> 3)
    // 64KB @ 0x80000000 => pmpaddr = 0x20003FFF
    asm volatile("csrw pmpaddr0, %0" :: "r"(0x20003FFF));

    // 配置: NAPOT, R+W+X, 锁定
    asm volatile("csrw pmpcfg0, %0" :: "r"(0x9F)); // L=1, A=NAPOT, RWX=1
}
```

### 6.2 虚拟内存

RISC-V支持分页虚拟内存，有三种模式：

| 模式 | 级数 | 地址宽度 | 页大小 | 适用场景 |
|------|------|----------|--------|----------|
| Sv32 | 2级 | 32位 | 4KB | RV32嵌入式/小型OS |
| Sv39 | 3级 | 39位(512GB) | 4KB | RV64通用 |
| Sv48 | 4级 | 48位(256TB) | 4KB | RV64大内存 |

#### Sv32页表结构

```
虚拟地址 (32位):
+--------+----------+----------+
| VPN[1] | VPN[0]   | Offset   |
| 10 bits| 10 bits  | 12 bits  |
+--------+----------+----------+

页表项 (PTE, 32位):
+--------+----------+----------+
| PPN[1] | PPN[0]   | Flags    |
| 12 bits| 10 bits  | 10 bits  |
+--------+----------+----------+

Flags: V(RSW) D A G U X W R
V=有效, R=可读, W=可写, X=可执行
U=User可访问, G=全局, A=访问位, D=脏位
```

#### Sv39页表结构

```
虚拟地址 (39位):
+------+----------+----------+----------+
| VPN[2]| VPN[1]  | VPN[0]   | Offset   |
| 9 bits| 9 bits  | 9 bits   | 12 bits  |
+------+----------+----------+----------+

页表项 (PTE, 64位):
+--------+----------+----------+
| PPN[2] | PPN[1]   | Flags    |
| 26 bits| 9 bits   | 10 bits  |
+--------+----------+----------+
```

#### satp寄存器

```c
// Sv32: satp[31]=MODE, satp[30:22]=ASID, satp[21:0]=PPN(根页表)
// Sv39: satp[63:60]=MODE, satp[59:44]=ASID, satp[43:0]=PPN

#define SATP_MODE_SV32  (1UL << 31)
#define SATP_MODE_SV39  (9UL << 60)

// 启用Sv39分页
void enable_paging(uint64_t root_pte_addr) {
    uint64_t satp_val = SATP_MODE_SV39 | (root_pte_addr >> 12);
    asm volatile("csrw satp, %0" :: "r"(satp_val));
    asm volatile("sfence.vma");  // 刷新TLB
}
```

### 6.3 TLB

TLB（Translation Lookaside Buffer）缓存页表翻译结果：

- RISC-V不规定TLB的具体结构（关联度、大小等）
- 软件通过 `SFENCE.VMA` 指令管理TLB
- `SFENCE.VMA rs1, rs2`：刷新指定虚拟地址和ASID的TLB条目
- 若rs1=x0，刷新所有虚拟地址；若rs2=x0，刷新所有ASID

---

## 7. RISC-V vs ARM对比

### 7.1 指令集架构对比

| 特性 | RISC-V | ARM |
|------|--------|-----|
| 开放性 | 完全开源，免授权费 | 商业授权，需付许可费 |
| 指令格式 | 6种格式，简洁统一 | A64有固定4字节格式，A32格式复杂 |
| 条件执行 | 无（用分支指令） | A32支持条件执行，A64大幅简化 |
| 标志寄存器 | 无（比较结果写通用寄存器） | CPSR/SPSR状态寄存器 |
| 立即数 | 12位有符号（I型） | A64: 12位+移位，复杂编码 |
| SIMD/向量 | RVV可变长度向量 | NEON固定128位，SVE可变长度 |
| 条件分支 | 比较+分支两条指令 | CBZ/CBNZ可合并 |
| 代码密度 | C扩展达到类似Thumb水平 | Thumb/Thumb-2 |

### 7.2 生态对比

| 方面 | RISC-V | ARM |
|------|--------|-----|
| 成熟度 | 快速发展中 | 非常成熟 |
| 芯片数量 | 大量MCU，应用处理器较少 | 数千款SoC |
| 操作系统 | Linux主线支持 | 全平台支持 |
| 工具链 | GCC/LLVM完整支持 | GCC/LLVM/IAR/Keil全支持 |
| IDE | 各厂商IDE | Keil MDK, IAR, STM32CubeIDE |
| 调试器 | OpenOCD | J-Link, ST-Link, DAPLINK |
| RTOS | FreeRTOS, Zephyr, RT-Thread | 所有主流RTOS |
| 生态社区 | 快速增长 | 极其庞大 |

### 7.3 工具链对比

| 工具 | RISC-V | ARM |
|------|--------|-----|
| 编译器 | riscv64-unknown-elf-gcc | arm-none-eabi-gcc |
| 调试器 | OpenOCD + GDB | OpenOCD/J-Link GDB |
| 模拟器 | QEMU, Spike | QEMU, Renode |
| 构建系统 | CMake, PlatformIO | CMake, PlatformIO, Keil |
| SDK | 各厂商SDK | CMSIS, HAL |

### 7.4 性能对比

在相同工艺节点下：
- **相同复杂度的核心**：RISC-V和ARM性能相当
- **单周期执行**：两者都有简单的单周期实现
- **流水线深度**：类似（3-8级常见于嵌入式核心）
- **能效比**：RISC-V因精简设计略有优势（取决于实现）
- **成熟优化**：ARM经过多年积累，高性能核心优化更深

---

## 8. 常用RISC-V芯片

### 8.1 ESP32-C3/C6/H2 (Espressif)

ESP32系列中RISC-V核心的成员：

| 芯片 | 核心 | 频率 | 特性 |
|------|------|------|------|
| **ESP32-C3** | 单核RV32IMC | 160MHz | WiFi+BLE5, 400KB SRAM |
| **ESP32-C6** | 单核RV32IMAC | 160MHz | WiFi6+BLE5+802.15.4 |
| **ESP32-H2** | 单核RV32IMAC | 96MHz | BLE5+802.15.4(无WiFi) |
| **ESP32-C2** | 单核RV32IMC | 120MHz | 低成本WiFi+BLE |

ESP32-C3开发示例（ESP-IDF）：

```c
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

#define LED_GPIO  GPIO_NUM_2

void app_main(void) {
    gpio_reset_pin(LED_GPIO);
    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);

    while (1) {
        gpio_set_level(LED_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(500));
        gpio_set_level(LED_GPIO, 0);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
```

### 8.2 GD32VF103 (GigaDevice)

中国首款RISC-V通用MCU：

| 特性 | 参数 |
|------|------|
| 核心 | Nuclei Bumblebee (RV32IMAC) |
| 频率 | 108MHz |
| Flash | 128KB/256KB |
| SRAM | 32KB/48KB |
| 外设 | USB, CAN, SPI, I2C, UART, ADC, Timer |
| 开发板 | Longan Nano, Sipeed Longan |

### 8.3 CH32V系列 (WCH)

南京沁恒的RISC-V MCU系列：

| 芯片 | 核心 | 频率 | 特点 |
|------|------|------|------|
| **CH32V003** | 青稞RV32EC | 48MHz | 极低成本(<$0.10), 16KB Flash |
| **CH32V103** | 青稞RV32IMAC | 72MHz | 中端通用MCU |
| **CH32V203** | 青稞RV32IMAC | 144MHz | USB, CAN |
| **CH32V208** | 青稞RV32IMAC | 144MHz | BLE5.3, USB |
| **CH32V307** | 青稞RV4IMAC | 144MHz | 以太网, USB HS, CAN |
| **CH32V317** | 青稞RV4IMFC | 144MHz | 浮点, 以太网 |

### 8.4 K210 (Canaan)

| 特性 | 参数 |
|------|------|
| 核心 | 双核RV64IMAFDC (RV64GC) |
| 频率 | 400MHz |
| SRAM | 8MB |
| AI加速 | KPU神经网络加速器 |
| 特点 | 人脸检测、目标识别 |
| 开发板 | Sipeed Maix, Kendryte KD233 |

### 8.5 BL808 (Bouffalo Lab)

| 特性 | 参数 |
|------|------|
| 核心 | 三核异构：E907(M) + E907(M) + C906(A) |
| 频率 | E907@480MHz, C906@600MHz |
| 特点 | WiFi+BLE+802.15.4, 摄像头, 音频 |
| 开发板 | Sipeed M1s Dock |

### 8.6 其他值得关注的RISC-V芯片

| 芯片/SoC | 厂商 | 用途 |
|-----------|------|------|
| **SG2000/SG2002** | 算能(Sophgo) | AI视觉SoC, 平头哥C906 |
| **TH1520** | 平头哥(T-Head) | 四核C910, 笔记本/开发板 |
| **JH7110** | StarFive | 四核U74, RISC-V Linux SBC |
| **K230** | 嘉楠(Canaan) | 双核C908, AI视觉 |
| **HPM6000系列** | 先楫(HPMicro) | 高性能MCU, 600MHz+ |

---

## 9. RISC-V开发工具链

### 9.1 GCC工具链

#### 安装

```bash
# Ubuntu/Debian
sudo apt install gcc-riscv64-unknown-elf

# 或下载预编译工具链
# https://github.com/riscv-collab/riscv-gnu-toolchain

# Windows: 使用xPack或SiFive提供的预编译包
```

#### 命名约定

```
riscv{位数}-{厂商}-{os}-{abi}-gcc

示例:
riscv64-unknown-elf-gcc     # 64位裸机
riscv32-unknown-elf-gcc     # 32位裸机
riscv64-linux-gnu-gcc       # 64位Linux
```

#### 常用编译选项

```bash
# 基本编译
riscv32-unknown-elf-gcc -march=rv32imac -mabi=ilp32 -o output.elf main.c

# 关键选项说明
-march=rv32imac    # 指定ISA: RV32 + Integer + Multiply + Atomic + Compressed
-mabi=ilp32        # 指定ABI: 32位整数ABI
-mcmodel=medlow    # 代码模型: 中低地址范围
-O2                # 优化级别
-ffreestanding     # 裸机环境（无标准库）
-nostdlib          # 不链接标准库
-nostartfiles      # 不链接启动文件

# 反汇编
riscv32-unknown-elf-objdump -d output.elf

# 查看段信息
riscv32-unknown-elf-size output.elf

# 转为bin文件
riscv32-unknown-elf-objcopy -O binary output.elf output.bin
```

### 9.2 OpenOCD调试

#### 安装

```bash
# Ubuntu
sudo apt install openocd

# 或从源码编译（支持最新RISC-V调试规范）
git clone https://github.com/riscv/riscv-openocd.git
cd riscv-openocd
./bootstrap
./configure --enable-ftdi --enable-jlink
make -j$(nproc)
sudo make install
```

#### 配置文件示例

```tcl
# openocd.cfg - ESP32-C3
source [find interface/ftdi/esp32_devkitj_v1.cfg]
source [find target/esp32c3.cfg]

# openocd.cfg - 通用J-Link + RISC-V
source [find interface/jlink.cfg]
transport select jtag
adapter speed 4000

set _CHIPNAME riscv
jtag newtap $_CHIPNAME cpu -irlen 5

target create $_CHIPNAME.cpu riscv -chain-position $_CHIPNAME.cpu
$_CHIPNAME.cpu configure -work-area-phys 0x80000000 -work-area-size 10000

# 初始化
init
halt
```

#### GDB调试流程

```bash
# 终端1: 启动OpenOCD
openocd -f openocd.cfg

# 终端2: 启动GDB
riscv32-unknown-elf-gdb output.elf

# GDB命令
(gdb) target remote :3333    # 连接OpenOCD
(gdb) load                    # 下载程序
(gdb) break main             # 设置断点
(gdb) continue               # 继续运行
(gdb) step                   # 单步
(gdb) info registers         # 查看寄存器
(gdb) x/10x 0x80000000      # 查看内存
(gdb) monitor reset halt     # 复位并暂停
```

### 9.3 QEMU模拟

#### 安装

```bash
# Ubuntu
sudo apt install qemu-system-riscv32 qemu-system-riscv64
```

#### 运行裸机程序

```bash
# 运行RV32裸机程序
qemu-system-riscv32 -machine virt -nographic \
    -bios output.elf \
    -serial mon:stdio

# 运行RV64 Linux
qemu-system-riscv64 -machine virt -nographic \
    -kernel Image \
    -append "root=/dev/vda rw console=ttyS0" \
    -drive file=rootfs.img,format=raw,id=hd0 \
    -device virtio-blk-device,drive=hd0
```

#### QEMU GDB调试

```bash
# 终端1: 启动QEMU（等待GDB连接）
qemu-system-riscv32 -machine virt -nographic \
    -bios output.elf -S -s

# 终端2: GDB连接
riscv32-unknown-elf-gdb output.elf
(gdb) target remote :1234
(gdb) break main
(gdb) continue
```

#### QEMU常用机器类型

| 机器 | 说明 |
|------|------|
| `virt` | 通用虚拟机，推荐使用 |
| `sifive_e` | SiFive FE310模拟 |
| `sifive_u` | SiFive FU540模拟 |
| `spike` | RISC-V ISA参考模拟器 |

### 9.4 PlatformIO

```ini
; platformio.ini - ESP32-C3
[env:esp32-c3-devkitm-1]
platform = espressif32
board = esp32-c3-devkitm-1
framework = espidf

; platformio.ini - GD32VF103
[env:sipeed-longan-nano]
platform = gd32v
board = sipeed-longan-nano
framework = gd32vf103-sdk

; platformio.ini - CH32V003
[env:ch32v003f4p6]
platform = wch
board = ch32v003f4p6
framework = none
```

---

## 10. RISC-V汇编编程

### 10.1 汇编语法基础

RISC-V汇编使用GAS（GNU Assembler）语法：

```assembly
.section .text          # 代码段
.global _start          # 入口点声明
.align 2                # 4字节对齐

_start:
    li   a0, 42         # 加载立即数
    li   a1, 58
    add  a0, a0, a1     # a0 = 42 + 58 = 100

    # 无限循环
loop:
    j    loop

.section .data          # 数据段
.align 2
msg:
    .string "Hello RISC-V!\n"

.section .bss           # BSS段
.align 2
buffer:
    .space 256          # 分配256字节
```

### 10.2 伪指令

RISC-V有大量伪指令，简化编程：

| 伪指令 | 展开为 | 含义 |
|--------|--------|------|
| `nop` | `addi x0, x0, 0` | 空操作 |
| `li rd, imm` | 多条指令 | 加载立即数 |
| `mv rd, rs` | `addi rd, rs, 0` | 寄存器移动 |
| `not rd, rs` | `xori rd, rs, -1` | 按位取反 |
| `neg rd, rs` | `sub rd, x0, rs` | 取反 |
| `j offset` | `jal x0, offset` | 无条件跳转 |
| `jr rs` | `jalr x0, rs, 0` | 寄存器跳转 |
| `jal rs` | `jalr x1, rs, 0` | 跳转并链接 |
| `ret` | `jalr x0, x1, 0` | 函数返回 |
| `call offset` | `auipc x1, ...; jalr x1, x1, ...` | 远调用 |
| `tail offset` | `auipc x6, ...; jalr x0, x6, ...` | 尾调用 |
| `la rd, symbol` | `auipc rd, ...; addi rd, rd, ...` | 加载符号地址 |
| `csrr rd, csr` | `csrrs rd, csr, x0` | 读CSR |
| `csrw csr, rs` | `csrrw x0, csr, rs` | 写CSR |
| `csrc csr, rs` | `csrrc x0, csr, rs` | 清CSR位 |
| `csrs csr, rs` | `csrrs x0, csr, rs` | 置CSR位 |
| `fence` | 原指令 | 内存屏障 |
| `ecall` | 原指令 | 环境调用 |
| `ebreak` | 原指令 | 断点 |

### 10.3 函数调用约定

RISC-V标准调用约定（ILP32/LP64）：

```
参数传递：
  - 前8个整数参数：a0-a7
  - 前8个浮点参数：fa0-fa7
  - 超出部分通过栈传递

返回值：
  - 整数返回值：a0, a1（64位值在RV32中用两个寄存器）
  - 浮点返回值：fa0, fa1

调用者保存 (Caller-saved):
  ra, t0-t6, a0-a7

被调用者保存 (Callee-saved):
  sp, s0-s11

栈帧布局（从高地址到低地址）：
+------------------+ ← 调用者的栈顶
| 返回地址 (ra)     |
| 保存的s0-s11      |
| 局部变量          |
| 传出参数(>8个)    |
+------------------+ ← 当前sp
```

### 10.4 函数调用示例

#### 被调用函数的序言和尾声

```assembly
# int factorial(int n)
# a0 = n, 返回 a0 = n!
factorial:
    # 序言 (Prologue)
    addi sp, sp, -16       # 分配栈帧
    sd   ra, 8(sp)         # 保存返回地址
    sd   s0, 0(sp)         # 保存s0

    # 函数体
    mv   s0, a0            # s0 = n
    li   t0, 1
    ble  a0, t0, .base     # if n <= 1, 返回1

    addi a0, s0, -1        # a0 = n - 1
    call factorial          # 递归调用
    mul  a0, s0, a0        # a0 = n * factorial(n-1)
    j    .done

.base:
    li   a0, 1             # 返回1

.done:
    # 尾声 (Epilogue)
    ld   ra, 8(sp)         # 恢复返回地址
    ld   s0, 0(sp)         # 恢复s0
    addi sp, sp, 16        # 释放栈帧
    ret
```

#### 调用函数

```assembly
# 调用 factorial(10)
main:
    addi sp, sp, -16
    sd   ra, 8(sp)

    li   a0, 10            # 参数 n=10
    call factorial          # 调用，结果在a0中

    # a0 现在包含 10! = 3628800

    ld   ra, 8(sp)
    addi sp, sp, 16
    ret
```

### 10.5 常用汇编技巧

#### 加载32位常数

```assembly
# 加载 0x12345678 到 a0
lui  a0, 0x12345          # a0 = 0x12345000
addi a0, a0, 0x678        # a0 = 0x12345678

# 伪指令方式
li   a0, 0x12345678        # 编译器自动展开
```

#### 位操作

```assembly
# 提取位域 [15:8]
srli t0, a0, 8             # 右移8位
andi t0, t0, 0xFF          # 掩码取低8位

# 设置位 [5]
ori  a0, a0, (1 << 5)

# 清除位 [3]
andi a0, a0, ~(1 << 3)

# 判断某位是否为零
andi t0, a0, (1 << 5)
beqz t0, bit_not_set
```

---

## 11. 嵌入式RISC-V开发实战

### 11.1 裸机开发基础

#### 启动文件（startup.S）

```assembly
.section .text.start
.global _start
.align 2

_start:
    # 关闭全局中断
    csrw mstatus, zero
    csrw mie, zero

    # 设置栈指针
    la   sp, _stack_top

    # 清除BSS段
    la   t0, _bss_start
    la   t1, _bss_end
1:
    bgeu t0, t1, 2f
    sd   zero, 0(t0)
    addi t0, t0, 8
    j    1b
2:
    # 调用main函数
    call main

    # main返回后死循环
3:
    j    3b
```

#### 链接脚本（link.ld）

```ld
ENTRY(_start)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 256K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
}

SECTIONS
{
    .text : {
        *(.text.start)
        *(.text .text.*)
    } > FLASH

    .rodata : {
        *(.rodata .rodata.*)
    } > FLASH

    .data : {
        _data_start = .;
        *(.data .data.*)
        _data_end = .;
    } > RAM AT > FLASH

    .bss (NOLOAD) : {
        _bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        _bss_end = .;
    } > RAM

    .stack (NOLOAD) : {
        . = . + 4096;  /* 4KB栈 */
        _stack_top = .;
    } > RAM
}
```

#### 裸机LED闪烁（以GD32VF103为例）

```c
#include <stdint.h>

// 寄存器定义
#define RCU_BASE        0x40021000UL
#define GPIOA_BASE      0x40010800UL
#define RCU_APB2EN      (*(volatile uint32_t *)(RCU_BASE + 0x18))
#define GPIO_CTL0       (*(volatile uint32_t *)(GPIOA_BASE + 0x00))
#define GPIO_OCTL       (*(volatile uint32_t *)(GPIO_BASE + 0x0C))

// GPIO配置宏
#define GPIO_MODE_OUTPUT_PP_50MHZ  0x3

void delay(volatile uint32_t count) {
    while (count--) {
        __asm__ volatile("nop");
    }
}

int main(void) {
    // 使能GPIOA时钟
    RCU_APB2EN |= (1 << 2);

    // 配置PA1为推挽输出
    GPIO_CTL0 &= ~(0xF << 4);   // 清除PA1配置
    GPIO_CTL0 |= (GPIO_MODE_OUTPUT_PP_50MHZ << 4);

    while (1) {
        GPIO_OCTL |= (1 << 1);   // PA1高电平
        delay(500000);
        GPIO_OCTL &= ~(1 << 1);  // PA1低电平
        delay(500000);
    }

    return 0;
}
```

### 11.2 中断配置

#### 中断向量表

```assembly
.section .vectors
.align 2

# 标准RISC-V向量表
vector_table:
    j    _start              # 0: 复位
    j    default_handler     # 1: 保留
    j    nmi_handler         # 2: NMI
    j    default_handler     # 3: 硬件错误
    j    default_handler     # 4: 保留
    j    default_handler     # 5: 保留
    j    default_handler     # 6: 保留
    j    mtvec_handler       # 7: 定时器
    j    default_handler     # 8: 保留
    j    default_handler     # 9: 保留
    j    default_handler     # 10: 保留
    j    default_handler     # 11: 外部中断
    # ... 可继续扩展

.global default_handler
default_handler:
    j    default_handler

.global mtvec_handler
mtvec_handler:
    # 中断处理
    addi sp, sp, -32*4       # 保存上下文
    # ... 保存寄存器
    # ... 中断处理逻辑
    # ... 恢复寄存器
    addi sp, sp, 32*4
    mret
```

#### 中断初始化（C语言）

```c
#include <stdint.h>

// 中断控制器寄存器 (以CLIC为例)
#define CLIC_BASE        0x02800000UL
#define CLIC_INTIE(n)    (*(volatile uint8_t  *)(CLIC_BASE + 0x1000 + n))
#define CLIC_INTIP(n)    (*(volatile uint8_t  *)(CLIC_BASE + 0x0000 + n))
#define CLIC_INTATTR(n)  (*(volatile uint8_t  *)(CLIC_BASE + 0x1000 + n*4 + 2))
#define CLIC_INTCTL(n)   (*(volatile uint8_t  *)(CLIC_BASE + 0x1000 + n*4 + 3))

void interrupt_init(void) {
    // 设置mtvec指向中断向量表
    extern void vector_table(void);
    uint32_t mtvec_val = (uint32_t)vector_table | 0x1; // Vectored模式
    asm volatile("csrw mtvec, %0" :: "r"(mtvec_val));

    // 清除所有中断pending
    for (int i = 0; i < 64; i++) {
        CLIC_INTIP(i) = 0;
    }

    // 使能M-mode全局中断
    asm volatile("csrs mstatus, %0" :: "r"(1 << 3)); // MIE
}

void enable_irq(uint32_t irq_num, uint8_t priority) {
    CLIC_INTIE(irq_num) = 1;          // 使能中断
    CLIC_INTCTL(irq_num) = priority;   // 设置优先级
    CLIC_INTATTR(irq_num) = 0x03;      // 向量模式 + 可抢占
}

void disable_irq(uint32_t irq_num) {
    CLIC_INTIE(irq_num) = 0;
}
```

### 11.3 FreeRTOS移植要点

将FreeRTOS移植到RISC-V需要实现以下接口：

#### portmacro.h关键定义

```c
// 上下文保存/恢复的寄存器数量
#define portCONTEXT_SIZE    (30 * 4)  // RV32: 30个寄存器 x 4字节

// 临界区
extern uint32_t vPortEnterCritical(void);
extern void vPortExitCritical(uint32_t);

#define portENTER_CRITICAL()    vPortEnterCritical()
#define portEXIT_CRITICAL()     vPortExitCritical()

// 任务切换
#define portYIELD()             asm volatile("ecall")
#define portYIELD_FROM_ISR()    asm volatile("ecall")

// 时钟
#define configMTIME_CLOCK_HZ    (10000000UL)  // 10MHz
```

#### port.c — 上下文切换

```c
// 压栈顺序（StackType_t *pxPortInitialiseStack）
StackType_t *pxPortInitialiseStack(
    StackType_t *pxTopOfStack,
    TaskFunction_t pxCode,
    void *pvParameters)
{
    // 初始化栈帧，模拟中断发生后的状态
    pxTopOfStack -= 30;  // 30个寄存器空间

    // 通用寄存器
    pxTopOfStack[0]  = (StackType_t)pxCode;     // x1 (ra) = 入口地址
    pxTopOfStack[1]  = 0;                        // x5 (t0)
    pxTopOfStack[2]  = 0;                        // x6 (t1)
    pxTopOfStack[3]  = 0;                        // x7 (t2)
    pxTopOfStack[4]  = (StackType_t)pxTopOfStack + 30*4; // x8 (s0/fp)
    pxTopOfStack[5]  = 0;                        // x9 (s1)
    pxTopOfStack[6]  = (StackType_t)pvParameters;// x10 (a0) = 参数
    // ... 初始化其余寄存器为0

    return pxTopOfStack;
}

// 定时器中断处理
void vPortSysTickHandler(void) {
    // 清除定时器中断
    // MTIMECMP += tick周期

    if (xTaskIncrementTick() != pdFALSE) {
        vTaskSwitchContext();
    }
}
```

### 11.4 常见开发问题

#### 内存对齐

RISC-V要求自然对齐：
- `LW`/`SW`需要4字节对齐
- `LD`/`SD`需要8字节对齐
- 非对齐访问触发异常（除非硬件支持非对齐访问）

```c
// 强制对齐
__attribute__((aligned(4))) uint32_t aligned_var;

// 检查对齐
if ((addr & 0x3) != 0) {
    // 地址未对齐
}
```

#### 原子操作与内存屏障

```c
// 内存屏障
__asm__ volatile("fence" ::: "memory");     // 通用内存屏障
__asm__ volatile("fence rw, rw" ::: "memory"); // 读写屏障
__asm__ volatile("fence.i" ::: "memory");   // 指令缓存同步

// 原子操作 (A扩展)
uint32_t atomic_add(volatile uint32_t *ptr, uint32_t val) {
    uint32_t result;
    __asm__ volatile(
        "amoadd.w %0, %2, (%1)"
        : "=r"(result)
        : "r"(ptr), "r"(val)
        : "memory"
    );
    return result;
}
```

#### 编译器内联汇编

```c
// 读CSR
static inline uint32_t read_mstatus(void) {
    uint32_t val;
    __asm__ volatile("csrr %0, mstatus" : "=r"(val));
    return val;
}

// 写CSR
static inline void write_mstatus(uint32_t val) {
    __asm__ volatile("csrw mstatus, %0" :: "r"(val));
}

// 原子读-修改-写CSR
static inline void set_mie_bits(uint32_t mask) {
    __asm__ volatile("csrs mie, %0" :: "r"(mask));
}

static inline void clear_mie_bits(uint32_t mask) {
    __asm__ volatile("csrc mie, %0" :: "r"(mask));
}

// NOP和特殊指令
#define NOP()           __asm__ volatile("nop")
#define WFI()           __asm__ volatile("wfi")   // 等待中断（低功耗）
#define FENCE()         __asm__ volatile("fence" ::: "memory")
#define FENCE_I()       __asm__ volatile("fence.i" ::: "memory")
```

---

## 附录

### A. RISC-V规范参考

| 规范 | 版本 | 链接 |
|------|------|------|
| User ISA | 20191213 | riscv.org/technical/specifications |
| Privileged ISA | 20211203 | riscv.org/technical/specifications |
| Vector Extension | v1.0 | github.com/riscv/riscv-v-spec |
| Debug Spec | 0.13.2 | github.com/riscv/riscv-debug-spec |

### B. 常用地址空间（典型RISC-V SoC）

| 地址范围 | 用途 |
|----------|------|
| `0x0000_0000 - 0x0FFF_FFFF` | Flash/ROM |
| `0x2000_0000 - 0x2FFF_FFFF` | SRAM |
| `0x0200_0000 - 0x0200_FFFF` | CLINT |
| `0x0C00_0000 - 0x0FFF_FFFF` | PLIC |
| `0x4000_0000 - 0x4FFF_FFFF` | 外设寄存器 |
| `0x8000_0000 - 0xBFFF_FFFF` | 可缓存内存 |

### C. ABI速查表

| ABI名称 | 整数ABI | 浮点ABI | 用途 |
|---------|---------|---------|------|
| ilp32 | 32位整数 | 无 | RV32无FPU |
| ilp32f | 32位整数 | 单精度 | RV32有F单精度 |
| ilp32d | 32位整数 | 双精度 | RV32有F+D双精度 |
| lp64 | 64位整数 | 无 | RV64无FPU |
| lp64f | 64位整数 | 单精度 | RV64有F单精度 |
| lp64d | 64位整数 | 双精度 | RV64有F+D双精度 |

### D. 快速参考卡

```
指令总数: RV32I=47条, RV64I=59条 (基础整数)
寄存器: x0-x31 (32个通用), f0-f31 (32个浮点)
指令长度: 16位(C扩展), 32位(标准), 48/64位(实验性)
字节序: 小端 (Little-Endian, 标准)
内存模型: 弱一致性 (RVWMO)
特权级: M(11) > S(01) > U(00)
中断: M-mode: 7种, S-mode: 3种
CSR地址空间: 12位 (4096个)
页大小: 4KB (标准)
TLB管理: 软件管理 (SFENCE.VMA)
```

---

> 参考资源：
> - [RISC-V官方规范](https://riscv.org/technical/specifications/)
> - [RISC-V手册(Patterson & Waterman)](https://github.com/riscv/riscv-manual)
> - [SiFive RISC-V核心文档](https://www.sifive.com/documentation)
> - [Nuclei RISC-V处理器](https://www.nucleisys.com/)
> - [Espressif ESP32-C3技术参考手册](https://www.espressif.com/)
