# RISC-V开发详解

## 核心概念

- **RISC-V** - 开源指令集架构
- **RV32I** - 基础整数指令集
- **特权模式** - Machine/Supervisor/User
- **CSR** - 控制状态寄存器

---

## 一、RISC-V架构

### 1.1 指令集模块

| 模块 | 说明 | 基本指令数 |
|------|------|-----------|
| RV32I | 基础整数 | 47 |
| M | 乘除法 | 8 |
| A | 原子操作 | 11 |
| F | 单精度浮点 | 26 |
| D | 双精度浮点 | 26 |
| C | 压缩指令 | 46 |
| V | 向量 | - |

---

### 1.2 寄存器

| 寄存器 | ABI名 | 用途 |
|--------|--------|------|
| x0 | zero | 硬编码0 |
| x1 | ra | 返回地址 |
| x2 | sp | 栈指针 |
| x3 | gp | 全局指针 |
| x4 | tp | 线程指针 |
| x5-x7 | t0-t2 | 临时寄存器 |
| x8 | s0/fp | 保存/帧指针 |
| x9 | s1 | 保存寄存器 |
| x10-x11 | a0-a1 | 参数/返回值 |
| x12-x17 | a2-a7 | 参数寄存器 |
| x18-x27 | s2-s11 | 保存寄存器 |
| x28-x31 | t3-t6 | 临时寄存器 |

---

### 1.3 指令格式

```
R-type: | funct7 | rs2 | rs1 | funct3 | rd | opcode |
I-type: | imm[11:0] | rs1 | funct3 | rd | opcode |
S-type: | imm[11:5] | rs2 | rs1 | funct3 | imm[4:0] | opcode |
B-type: | imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode |
U-type: | imm[31:12] | rd | opcode |
J-type: | imm[20|10:1|11|19:12] | rd | opcode |
```

---

## 二、基础指令

### 2.1 算术指令

```assembly
# RV32I算术指令
add   rd, rs1, rs2    # rd = rs1 + rs2
addi  rd, rs1, imm    # rd = rs1 + imm
sub   rd, rs1, rs2    # rd = rs1 - rs2
lui   rd, imm         # rd = imm << 12
auipc rd, imm         # rd = pc + (imm << 12)

# 乘除法(M扩展)
mul    rd, rs1, rs2   # rd = rs1 * rs2 (低32位)
mulh   rd, rs1, rs2   # rd = (rs1 * rs2) >> 32 (有符号)
div    rd, rs1, rs2   # rd = rs1 / rs2 (有符号)
rem    rd, rs1, rs2   # rd = rs1 % rs2 (有符号)
```

---

### 2.2 逻辑指令

```assembly
and   rd, rs1, rs2    # rd = rs1 & rs2
andi  rd, rs1, imm    # rd = rs1 & imm
or    rd, rs1, rs2    # rd = rs1 | rs2
ori   rd, rs1, imm    # rd = rs1 | imm
xor   rd, rs1, rs2    # rd = rs1 ^ rs2
xori  rd, rs1, imm    # rd = rs1 ^ imm
sll   rd, rs1, rs2    # rd = rs1 << rs2
srl   rd, rs1, rs2    # rd = rs1 >> rs2 (逻辑)
sra   rd, rs1, rs2    # rd = rs1 >> rs2 (算术)
```

---

### 2.3 访存指令

```assembly
# 加载
lb    rd, imm(rs1)    # rd = *(int8_t*)(rs1 + imm)
lbu   rd, imm(rs1)    # rd = *(uint8_t*)(rs1 + imm)
lh    rd, imm(rs1)    # rd = *(int16_t*)(rs1 + imm)
lhu   rd, imm(rs1)    # rd = *(uint16_t*)(rs1 + imm)
lw    rd, imm(rs1)    # rd = *(int32_t*)(rs1 + imm)

# 存储
sb    rs2, imm(rs1)   # *(int8_t*)(rs1 + imm) = rs2
sh    rs2, imm(rs1)   # *(int16_t*)(rs1 + imm) = rs2
sw    rs2, imm(rs1)   # *(int32_t*)(rs1 + imm) = rs2
```

---

### 2.4 分支指令

```assembly
beq   rs1, rs2, label  # if (rs1 == rs2) goto label
bne   rs1, rs2, label  # if (rs1 != rs2) goto label
blt   rs1, rs2, label  # if (rs1 < rs2) goto label (有符号)
bge   rs1, rs2, label  # if (rs1 >= rs2) goto label (有符号)
bltu  rs1, rs2, label  # if (rs1 < rs2) goto label (无符号)
bgeu  rs1, rs2, label  # if (rs1 >= rs2) goto label (无符号)

# 跳转
jal   rd, label        # rd = pc + 4; goto label
jalr  rd, rs1, imm     # rd = pc + 4; goto rs1 + imm
```

---

## 三、CSR操作

### 3.1 CSR寄存器

| CSR | 地址 | 说明 |
|-----|------|------|
| mstatus | 0x300 | 机器状态 |
| mtvec | 0x305 | 陷阱向量基址 |
| mepc | 0x341 | 异常PC |
| mcause | 0x342 | 陷阱原因 |
| mtval | 0x343 | 陷阱值 |
| mie | 0x304 | 中断使能 |
| mip | 0x344 | 中断挂起 |

---

### 3.2 CSR指令

```assembly
csrr  rd, csr        # rd = csr
csrw  csr, rs        # csr = rs
csrs  csr, rs        # csr |= rs
csrc  csr, rs        # csr &= ~rs
csrrwi rd, csr, imm  # rd = csr; csr = imm
csrrsi rd, csr, imm  # rd = csr; csr |= imm
csrrci rd, csr, imm  # rd = csr; csr &= ~imm
```

---

### 3.3 CSR操作C代码

```c
// 读CSR
#define read_csr(reg) ({ \
    unsigned long __tmp; \
    __asm__ volatile ("csrr %0, " #reg : "=r"(__tmp)); \
    __tmp; \
})

// 写CSR
#define write_csr(reg, val) ({ \
    __asm__ volatile ("csrw " #reg ", %0" :: "rK"(val)); \
})

// 置位CSR
#define set_csr(reg, bit) ({ \
    __asm__ volatile ("csrs " #reg ", %0" :: "rK"(bit)); \
})

// 清除CSR
#define clear_csr(reg, bit) ({ \
    __asm__ volatile ("csrc " #reg ", %0" :: "rK"(bit)); \
})

// 使用示例
void enable_interrupts(void) {
    set_csr(mstatus, 0x8);  // MIE位
}

void disable_interrupts(void) {
    clear_csr(mstatus, 0x8);
}
```

---

## 四、中断处理

### 4.1 中断向量表

```c
// 中断向量表
__attribute__((section(".vectors")))
const uint32_t vectors[] = {
    (uint32_t)&_estack,         // 初始栈
    (uint32_t)trap_handler,     // 所有陷阱入口
};

// 陷阱处理
__attribute__((interrupt))
void trap_handler(void) {
    uint32_t mcause = read_csr(mcause);
    uint32_t mepc = read_csr(mepc);
    uint32_t mtval = read_csr(mtval);

    if (mcause & 0x80000000) {
        // 中断
        uint32_t irq = mcause & 0x7FFFFFFF;
        switch (irq) {
            case 3:  // 软件中断
                software_irq_handler();
                break;
            case 7:  // 定时器中断
                timer_irq_handler();
                break;
            case 11: // 外部中断
                external_irq_handler();
                break;
        }
    } else {
        // 异常
        switch (mcause) {
            case 0:  // 指令地址不对齐
            case 1:  // 指令访问错误
            case 2:  // 非法指令
            case 11: // 环境调用
                // 处理异常
                break;
        }
    }
}
```

---

### 4.2 定时器中断

```c
// CLINT定时器
#define CLINT_BASE      0x02000000
#define CLINT_MTIME     (CLINT_BASE + 0xBFF8)
#define CLINT_MTIMECMP  (CLINT_BASE + 0x4000)

volatile uint64_t *mtime = (uint64_t *)CLINT_MTIME;
volatile uint64_t *mtimecmp = (uint64_t *)CLINT_MTIMECMP;

void timer_init(uint64_t interval) {
    *mtimecmp = *mtime + interval;
    set_csr(mie, 0x80);  // 使能定时器中断
}

void timer_irq_handler(void) {
    uint64_t interval = 1000000;  // 1MHz时钟，1秒
    *mtimecmp = *mtime + interval;

    // 定时器处理
    system_tick++;
}
```

---

## 五、ESP32-C3开发

### 5.1 ESP32-C3特性

| 特性 | 说明 |
|------|------|
| 核心 | 单核RISC-V (160MHz) |
| 内存 | 400KB SRAM |
| Flash | 4MB |
| WiFi | 2.4GHz 802.11 b/g/n |
| BLE | Bluetooth 5.0 |
| GPIO | 22个 |
| 外设 | UART, SPI, I2C, ADC, PWM |

---

### 5.2 ESP32-C3项目

```c
#include "esp_system.h"
#include "esp_log.h"

static const char *TAG = "main";

void app_main(void) {
    ESP_LOGI(TAG, "ESP32-C3 RISC-V");

    // GPIO配置
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << GPIO_NUM_2),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io_conf);

    while (1) {
        gpio_set_level(GPIO_NUM_2, 1);
        vTaskDelay(pdMS_TO_TICKS(500));
        gpio_set_level(GPIO_NUM_2, 0);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
```

---

### 5.3 RISC-V汇编集成

```c
// 内联汇编
static inline uint32_t get_mcycle(void) {
    uint32_t cycle;
    __asm__ volatile ("csrr %0, mcycle" : "=r"(cycle));
    return cycle;
}

// 纯汇编函数
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
        "sw sp, 0(a0)\n"    // 保存旧SP
        "lw sp, 0(a1)\n"    // 加载新SP

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

## 六、RISC-V调试

### 6.1 调试接口

| 接口 | 说明 |
|------|------|
| JTAG | 标准调试接口 |
| cJTAG | 紧凑JTAG |
| SWD | 串行线调试 |

---

### 6.2 OpenOCD配置

```cfg
# ESP32-C3 OpenOCD配置
source [find interface/esp_usb_jtag.cfg]
source [find target/esp32c3.cfg]

adapter speed 4000
```

---

## 七、RISC-V vs ARM

| 特性 | RISC-V | ARM |
|------|--------|-----|
| 授权 | 开源 | 商业 |
| 指令集 | 简洁 | 复杂 |
| 扩展性 | 模块化 | 固定 |
| 生态 | 发展中 | 成熟 |
| 应用 | 新兴 | 广泛 |

---

## 附录：RISC-V指令速查

### 算术

| 指令 | 操作 |
|------|------|
| add rd, rs1, rs2 | rd = rs1 + rs2 |
| addi rd, rs1, imm | rd = rs1 + imm |
| sub rd, rs1, rs2 | rd = rs1 - rs2 |
| lui rd, imm | rd = imm << 12 |

### 逻辑

| 指令 | 操作 |
|------|------|
| and rd, rs1, rs2 | rd = rs1 & rs2 |
| or rd, rs1, rs2 | rd = rs1 \| rs2 |
| xor rd, rs1, rs2 | rd = rs1 ^ rs2 |

### 访存

| 指令 | 操作 |
|------|------|
| lw rd, imm(rs1) | rd = mem[rs1+imm] |
| sw rs2, imm(rs1) | mem[rs1+imm] = rs2 |

### 分支

| 指令 | 操作 |
|------|------|
| beq rs1, rs2, label | if (rs1==rs2) goto label |
| bne rs1, rs2, label | if (rs1!=rs2) goto label |
| jal rd, label | rd=pc+4; goto label |

---

## 相关链接

- [[计算机组成原理]] - CPU架构
- [[ESP-IDF开发详解]] - ESP32开发
- [[GCC与链接脚本]] - 编译工具链
