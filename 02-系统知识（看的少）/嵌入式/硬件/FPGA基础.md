# FPGA基础

## 核心概念

- **FPGA** - 现场可编程门阵列
- **HDL** - 硬件描述语言
- **逻辑单元** - 可编程逻辑块
- **时序约束** - 时钟和延迟要求

---

## 一、FPGA架构

### 1.1 FPGA组成

```
┌─────────────────────────────────────┐
│         FPGA架构                    │
│                                     │
│  ┌─────┐  ┌─────┐  ┌─────┐        │
│  │ CLB │  │ CLB │  │ CLB │  ...   │
│  └─────┘  └─────┘  └─────┘        │
│                                     │
│  ┌─────────────────────────────┐   │
│  │       可编程互连资源         │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────┐  ┌─────┐  ┌─────┐        │
│  │ BRAM │  │ DSP │  │ PLL │        │
│  └─────┘  └─────┘  └─────┘        │
│                                     │
│  ┌─────────────────────────────┐   │
│  │         IO块                 │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

### 1.2 CLB(可配置逻辑块)

```c
// CLB组成
/*
 * - LUT(查找表): 实现组合逻辑
 *   - 4输入LUT: 16种组合
 *   - 6输入LUT: 64种组合
 *
 * - FF(触发器): 实现时序逻辑
 *   - D触发器
 *   - 带使能和复位
 *
 * - 进位链: 实现加法器
 * - MUX: 数据选择器
 */

// LUT实现逻辑
/*
 * 4输入LUT: F(A,B,C,D)
 * 16位存储: 实现任意4输入逻辑函数
 *
 * 例: F = A&B|C^D
 * 存储: 根据真值表填充16位
 */
```

---

## 二、Verilog HDL

### 2.1 基础语法

```verilog
// 模块定义
module counter (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    output reg  [7:0]  count
);

// 时序逻辑
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        count <= 8'd0;
    end else if (en) begin
        count <= count + 8'd1;
    end
end

endmodule
```

---

### 2.2 组合逻辑

```verilog
// 多路选择器
module mux4to1 (
    input  wire [1:0] sel,
    input  wire [3:0] in,
    output reg        out
);

always @(*) begin
    case (sel)
        2'b00: out = in[0];
        2'b01: out = in[1];
        2'b10: out = in[2];
        2'b11: out = in[3];
        default: out = 1'b0;
    endcase
end

endmodule

// 优先编码器
module priority_encoder (
    input  wire [7:0] in,
    output reg  [2:0] out,
    output reg        valid
);

always @(*) begin
    valid = 1'b1;
    casex (in)
        8'b1xxxxxxx: out = 3'd7;
        8'b01xxxxxx: out = 3'd6;
        8'b001xxxxx: out = 3'd5;
        8'b0001xxxx: out = 3'd4;
        8'b00001xxx: out = 3'd3;
        8'b000001xx: out = 3'd2;
        8'b0000001x: out = 3'd1;
        8'b00000001: out = 3'd0;
        default: begin
            out = 3'd0;
            valid = 1'b0;
        end
    endcase
end

endmodule
```

---

### 2.3 状态机

```verilog
// 有限状态机
module traffic_light (
    input  wire       clk,
    input  wire       rst_n,
    output reg  [1:0] light  // 00=红, 01=黄, 10=绿
);

// 状态定义
localparam [1:0] RED    = 2'b00;
localparam [1:0] YELLOW = 2'b01;
localparam [1:0] GREEN  = 2'b10;

reg [1:0] state, next_state;
reg [3:0] timer;

// 状态寄存器
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= RED;
        timer <= 4'd0;
    end else begin
        if (timer == 4'd9) begin
            state <= next_state;
            timer <= 4'd0;
        end else begin
            timer <= timer + 4'd1;
        end
    end
end

// 次态逻辑
always @(*) begin
    case (state)
        RED:    next_state = GREEN;
        GREEN:  next_state = YELLOW;
        YELLOW: next_state = RED;
        default: next_state = RED;
    endcase
end

// 输出逻辑
always @(*) begin
    case (state)
        RED:    light = 2'b00;
        YELLOW: light = 2'b01;
        GREEN:  light = 2'b10;
        default: light = 2'b00;
    endcase
end

endmodule
```

---

## 三、FPGA设计流程

### 3.1 设计流程

```
1. 设计输入
   ├── Verilog/VHDL代码
   ├── 原理图
   └── IP核

2. 功能仿真
   ├── Testbench
   ├── ModelSim
   └── 验证功能正确性

3. 综合
   ├── 逻辑优化
   ├── 技术映射
   └── 生成网表

4. 实现
   ├── 布局布线
   ├── 时序优化
   └── 生成比特流

5. 下载验证
   ├── JTAG下载
   ├── 在线调试
   └── 时序分析
```

---

### 3.2 时序约束

```tcl
# SDC时序约束
# 时钟定义
create_clock -period 10 -name clk [get_ports clk]

# 输入延迟
set_input_delay -clock clk -max 2 [get_ports data_in]

# 输出延迟
set_output_delay -clock clk -max 2 [get_ports data_out]

# 虚假路径
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]

# 多周期路径
set_multicycle_path -from [get_pins reg1/Q] -to [get_pins reg2/D] 2
```

---

## 四、FPGA外设

### 4.1 UART控制器

```verilog
// UART发送器
module uart_tx (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output reg        tx,
    output wire       tx_busy
);

parameter CLK_FREQ = 50000000;
parameter BAUD_RATE = 115200;
parameter CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

reg [15:0] clk_count;
reg [3:0]  bit_index;
reg [9:0]  tx_shift;
reg        sending;

assign tx_busy = sending;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        tx <= 1'b1;
        sending <= 1'b0;
        clk_count <= 16'd0;
        bit_index <= 4'd0;
    end else begin
        if (tx_start && !sending) begin
            tx_shift <= {1'b1, tx_data, 1'b0};  // 停止位+数据+起始位
            sending <= 1'b1;
            clk_count <= 16'd0;
            bit_index <= 4'd0;
        end else if (sending) begin
            if (clk_count == CLKS_PER_BIT - 1) begin
                clk_count <= 16'd0;
                tx <= tx_shift[bit_index];
                if (bit_index == 4'd9) begin
                    sending <= 1'b0;
                end else begin
                    bit_index <= bit_index + 4'd1;
                end
            end else begin
                clk_count <= clk_count + 16'd1;
            end
        end
    end
end

endmodule
```

---

### 4.2 SPI控制器

```verilog
// SPI主机
module spi_master (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [7:0] mosi_data,
    output reg  [7:0] miso_data,
    output reg        sclk,
    output reg        mosi,
    input  wire       miso,
    output reg        cs_n,
    output wire       busy
);

parameter CLK_DIV = 4;  // SCLK = CLK / CLK_DIV

reg [3:0] clk_count;
reg [2:0] bit_count;
reg       sending;

assign busy = sending;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        sclk <= 1'b0;
        cs_n <= 1'b1;
        sending <= 1'b0;
    end else begin
        if (start && !sending) begin
            cs_n <= 1'b0;
            sending <= 1'b1;
            clk_count <= 4'd0;
            bit_count <= 3'd0;
            mosi <= mosi_data[7];
        end else if (sending) begin
            if (clk_count == CLK_DIV - 1) begin
                clk_count <= 4'd0;
                sclk <= ~sclk;

                if (sclk) begin
                    // 下降沿: 采样MISO
                    miso_data[bit_count] <= miso;
                end else begin
                    // 上升沿: 更新MOSI
                    if (bit_count == 3'd7) begin
                        sending <= 1'b0;
                        cs_n <= 1'b1;
                    end else begin
                        bit_count <= bit_count + 3'd1;
                        mosi <= mosi_data[6 - bit_count];
                    end
                end
            end else begin
                clk_count <= clk_count + 4'd1;
            end
        end
    end
end

endmodule
```

---

## 五、FPGA与MCU对比

| 特性 | FPGA | MCU |
|------|------|-----|
| 并行性 | 真并行 | 串行 |
| 实时性 | 确定性 | 不确定 |
| 灵活性 | 硬件可重构 | 软件可编程 |
| 功耗 | 中等 | 低-中 |
| 开发难度 | 高 | 中 |
| 成本 | 高 | 低 |
| 适用场景 | 高速处理 | 控制逻辑 |

---

## 附录：FPGA厂商

| 厂商 | 系列 | 特点 |
|------|------|------|
| Xilinx | Artix/Kintex/Versal | 主流 |
| Intel(Altera) | Cyclone/Stratix | 主流 |
| Lattice | ECP5/CrossLink | 低功耗 |
| Gowin | GW1N | 国产 |
| 安路 | EF/SF | 国产 |

---

## 相关链接

- [[数字电子技术]] - 数字电路
- [[计算机组成原理]] - 计算机架构
- [[Verilog HDL]] - HDL语言
