# FPGA开发入门与实战

> **FPGA（Field-Programmable Gate Array）** 现场可编程门阵列，是一种可编程的集成电路。用户可以通过硬件描述语言（HDL）对其内部逻辑进行配置，实现定制化的数字电路功能。

---

## 目录

1. [[#FPGA基础]]
2. [[#主流FPGA厂商对比]]
3. [[#Verilog HDL基础]]
4. [[#组合逻辑设计]]
5. [[#时序逻辑设计]]
6. [[#时序约束]]
7. [[#IP核使用]]
8. [[#FPGA调试]]
9. [[#Zynq SoC开发]]
10. [[#FPGA vs MCU vs ASIC对比]]
11. [[#常见应用]]
12. [[#参考资源]]

---

## FPGA基础

### 可编程逻辑器件演进

可编程逻辑器件（PLD）的发展历程：

| 阶段 | 器件 | 特点 | 典型容量 |
|------|------|------|----------|
| 第一代 | **PAL（可编程阵列逻辑）** | 与阵列可编程，或阵列固定 | 几十门 |
| 第二代 | **GAL（通用阵列逻辑）** | 输出逻辑宏单元（OLMC）可编程 | 几百门 |
| 第三代 | **CPLD（复杂可编程逻辑器件）** | 多个PAL块通过可编程互连矩阵连接 | 几千~几万门 |
| 第四代 | **FPGA（现场可编程门阵列）** | 基于LUT+布线通道，密度极高 | 几万~几千万门 |

**PAL vs CPLD vs FPGA：**

```
PAL: 简单逻辑，一次性编程（OTP），适合地址译码、状态机
CPLD: 组合逻辑强，非易失性，上电即可工作，延迟可预测
FPGA: 时序逻辑强，SRAM配置，需外部Flash加载，资源丰富
```

### FPGA内部结构

现代FPGA主要由以下核心模块组成：

#### 1. 可配置逻辑块（CLB / Logic Block）

每个CLB包含：
- **LUT（查找表）**：实现组合逻辑，常用4输入或6输入LUT
- **触发器（FF）**：实现时序逻辑，每个LUT后通常跟随一个D触发器
- **进位链（Carry Chain）**：高效实现加法、减法运算
- **多路选择器（MUX）**：用于数据路径选择

```
6输入LUT工作原理：
- 有6个输入端口（I0~I5）
- 内部有 2^6 = 64 个存储位
- 输入作为地址，查表输出结果
- 可实现任意6输入组合逻辑函数
```

#### 2. 块RAM（BRAM / Block RAM）

- 专用存储器模块，通常18Kb或36Kb大小
- 支持双端口访问（True Dual Port）
- 可配置为RAM、ROM、FIFO
- 例化为 `RAMB36E1`（Xilinx）或 `M10K`（Intel）

```verilog
// BRAM例化示例（Xilinx 7系列）
(* ram_style = "block" *)
reg [7:0] bram [0:1023];

always @(posedge clk) begin
    if (we)
        bram[addr] <= din;
    dout <= bram[addr];
end
```

#### 3. DSP切片（DSP Slice）

专用硬件乘法器/累加器，典型功能：
- 18×18或25×18有符号乘法
- 48位累加器
- 预加器、逻辑单元
- 支持SIMD模式

```verilog
// DSP推断示例
always @(posedge clk) begin
    dsp_out <= a * b + c;  // 综合为DSP48
end
```

#### 4. 可编程IO块（IOB）

- 支持多种IO标准（LVTTL、LVCMOS、LVDS、HSTL等）
- 可配置输入/输出延迟（IDELAY/ODELAY）
- 支持IO寄存器（输入FF、输出FF）
- 支持三态控制

#### 5. 时钟资源

- **全局时钟网络（Global Clock）**：低偏斜、高扇出
- **区域时钟网络（Regional Clock）**：限制在特定时钟区域
- **MMCM/PLL**：时钟倍频、分频、相位调整
- **时钟缓冲器（BUFG/BUFH/BUFR）**

#### 6. 布线资源

- **本地布线**：CLB内部互连
- **行列布线**：水平/垂直方向的长线
- **全局布线**：跨芯片的高速信号线
- **专用布线**：进位链、时钟树等

### FPGA工作流程

```
设计输入 → 综合 → 实现（布局布线） → 生成比特流 → 下载配置

详细步骤：
1. 设计输入：Verilog/VHDL代码、IP核、原理图
2. 功能仿真：验证逻辑正确性（ModelSim/Vivado Simulator）
3. 综合：将HDL转换为门级网表（Synplify/Vivado Synthesis）
4. 实现：
   a. 映射（Map）：将网表映射到FPGA资源
   b. 布局（Place）：确定每个资源的位置
   c. 布线（Route）：连接各资源之间的信号
5. 时序仿真：验证时序是否满足要求
6. 生成比特流：生成配置文件（.bit）
7. 下载配置：通过JTAG/Flash加载到FPGA
```

---

## 主流FPGA厂商对比

### Xilinx / AMD（市场份额第一）

#### 7系列FPGA（28nm工艺）

| 系列 | 定位 | 代表型号 | LUT数量 | BRAM | DSP | 应用场景 |
|------|------|----------|---------|------|-----|----------|
| **Artix-7** | 低成本、低功耗 | XC7A35T~XC7A200T | 33K~215K | 1.8Mb~13Mb | 90~740 | 消费电子、医疗、汽车 |
| **Kintex-7** | 高性能 | XC7K70T~XC7K480T | 67K~478K | 4.9Mb~34Mb | 240~1920 | 通信、雷达、无线 |
| **Virtex-7** | 超高端 | XC7V585T~XC7V2000T | 585K~2M | 38Mb~46Mb | 1260~3600 | 数据中心、航空航天 |
| **Zynq-7000** | SoC | Z-7010~Z-7100 | 53K~505K | 2.1Mb~26.5Mb | 120~2020 | 嵌入式视觉、ADAS |

#### UltraScale/UltraScale+（20nm/16nm工艺）

| 系列 | 特点 | 代表型号 |
|------|------|----------|
| **Kintex UltraScale** | 高性能逻辑 | KU035~KU115 |
| **Virtex UltraScale** | 超大规模 | VU065~VU19P |
| **Kintex UltraScale+** | 性价比高 | KU3P~KU5P |
| **Virtex UltraScale+** | 旗舰级 | VU3P~VU13P |
| **Zynq UltraScale+ MPSoC** | 四核A53+双核R5 | ZU3EG~ZU19EG |
| **Zynq UltraScale+ RFSoC** | 集成RF ADC/DAC | ZU25DR~ZU49DR |

#### Versal（7nm ACAP）

- **AI Core系列**：集成AI Engine（向量处理器阵列）
- **AI Edge系列**：边缘AI推理
- **Prime系列**：通用计算加速
- **Premium系列**：高性能数据处理
- **HBM系列**：集成HBM2存储器

### Intel / Altera（市场份额第二）

#### 主流系列

| 系列 | 工艺 | 特点 | 应用 |
|------|------|------|------|
| **Cyclone IV/V/10** | 60nm/28nm | 低成本、低功耗 | 视频处理、协议桥接 |
| **Arria V/10** | 28nm/20nm | 中端性能 | 无线、广播 |
| **Stratix V/10** | 28nm/14nm | 高性能 | 数据中心、5G |
| **Agilex** | 10nm/7nm | 最新架构 | AI、网络、云计算 |
| **MAX V/CPLD** | - | 非易失性 | 胶合逻辑、上电复位 |

#### Intel SoC FPGA

- **Cyclone V SoC**：双核A9 + FPGA
- **Arria 10 SoC**：双核A9 + 高性能FPGA
- **Stratix 10 SoC**：四核A53 + 高性能FPGA
- **Agilex SoC**：最新架构SoC FPGA

### Lattice（市场份额第三）

| 系列 | 特点 | 应用 |
|------|------|------|
| **iCE40** | 超低功耗、极小封装 | 移动设备、IoT |
| **ECP5/ECP5-5G** | 中端、低成本 | 视频桥接、通信 |
| **CrossLink/NX** | 视频接口桥接 | MIPI、HDMI转换 |
| **Nexus** | 28nm平台 | 机器学习推理 |
| **CertusPro-NX** | 高性能通用 | 工业、通信 |

### 国产FPGA

| 厂商 | 代表系列 | 特点 |
|------|----------|------|
| **紫光同创** | Logos/PGL系列 | 国产最大规模FPGA，有PCIe硬核 |
| **安路科技** | EF/SF系列 | 国产中低端FPGA，软件易用 |
| **高云半导体** | GW1N/GW2A系列 | 低密度FPGA，有集成Flash |
| **京微齐力** | HME系列 | 融合FPGA+MCU |
| **复旦微** | FM系列 | 航天级FPGA，抗辐射 |
| **成都华微** | HW系列 | 航空航天、国防应用 |

---

## Verilog HDL基础

### 模块（Module）基本结构

```verilog
module module_name #(
    parameter DATA_WIDTH = 8,     // 参数化设计
    parameter DEPTH = 16
)(
    // 端口声明
    input  wire                    clk,        // 时钟
    input  wire                    rst_n,      // 异步复位（低有效）
    input  wire [DATA_WIDTH-1:0]  data_in,    // 数据输入
    input  wire                    valid_in,   // 有效信号
    output reg  [DATA_WIDTH-1:0]  data_out,   // 数据输出
    output reg                     valid_out   // 输出有效
);

// 内部信号声明
wire [DATA_WIDTH-1:0] intermediate;
reg  [7:0]            counter;

// 组合逻辑
assign intermediate = data_in + 1;

// 时序逻辑
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        data_out  <= {DATA_WIDTH{1'b0}};
        valid_out <= 1'b0;
        counter   <= 8'd0;
    end else begin
        data_out  <= intermediate;
        valid_out <= valid_in;
        if (valid_in)
            counter <= counter + 1;
    end
end

endmodule
```

### 数据类型

#### 线网类型（Net Types）

```verilog
wire [7:0] data_bus;          // 最常用，组合逻辑输出
wire       single_bit;        // 单bit线网
tri  [7:0] tri_state_bus;     // 三态总线
wand       wired_and;         // 线与
wor        wired_or;          // 线或
```

#### 寄存器类型（Register Types）

```verilog
reg  [7:0] data_reg;          // 最常用，过程赋值目标
reg  [7:0] mem [0:255];       // 存储器数组
integer    i;                 // 整数（仿真用）
real       r;                 // 实数（仿真用）
time       t;                 // 时间（仿真用）
```

#### 向量与位选择

```verilog
reg [7:0] byte_data;          // 8位向量 [MSB:LSB]
reg [0:7] reversed;           // 逆序声明

// 位选择
wire bit0 = byte_data[0];     // 取第0位
wire bit7 = byte_data[7];     // 取第7位

// 部分选择
wire [3:0] low_nibble = byte_data[3:0];   // 低4位
wire [3:0] high_nibble = byte_data[7:4];  // 高4位

// 非常量索引（综合为MUX）
wire selected = byte_data[addr];  // addr为变量时，综合为多路选择器
```

### 运算符

#### 算术运算符

```verilog
wire [7:0] sum   = a + b;      // 加法
wire [7:0] diff  = a - b;      // 减法
wire [15:0] prod = a * b;      // 乘法（综合为乘法器）
wire [7:0] quot  = a / b;      // 除法（慎用，资源大）
wire [7:0] rem   = a % b;      // 取模
```

#### 位运算符

```verilog
wire [7:0] and_out  = a & b;   // 按位与
wire [7:0] or_out   = a | b;   // 按位或
wire [7:0] xor_out  = a ^ b;   // 按位异或
wire [7:0] not_out  = ~a;      // 按位取反
wire [7:0] nand_out = ~(a & b); // 按位与非
```

#### 逻辑运算符

```verilog
wire and_result = a && b;      // 逻辑与（结果为1bit）
wire or_result  = a || b;      // 逻辑或
wire not_result = !a;          // 逻辑非
```

#### 移位运算符

```verilog
wire [7:0] left_shift  = a << 2;   // 逻辑左移（补0）
wire [7:0] right_shift = a >> 3;   // 逻辑右移（补0）
wire [7:0] arith_right = a >>> 2;  // 算术右移（补符号位）
```

#### 关系运算符

```verilog
wire eq  = (a == b);   // 等于
wire neq = (a != b);   // 不等于
wire gt  = (a > b);    // 大于
wire lt  = (a < b);    // 小于
wire gte = (a >= b);   // 大于等于
wire lte = (a <= b);   // 小于等于
```

#### 拼接与复制运算符

```verilog
// 拼接
wire [15:0] concat = {a, b};           // {8bit, 8bit} = 16bit
wire [11:0] mixed  = {a[3:0], b[7:0]}; // 部分位拼接

// 复制
wire [7:0] all_ones  = {8{1'b1}};      // 8个1
wire [23:0] pattern  = {3{8'hA5}};     // 3个0xA5
wire [31:0] extended = {{24{a[7]}}, a}; // 符号扩展
```

#### 条件运算符

```verilog
wire [7:0] result = sel ? a : b;  // 三目运算符
wire [7:0] max_val = (a > b) ? a : b;
wire [7:0] min_val = (a < b) ? a : b;
```

### always块

#### 组合逻辑always块

```verilog
// 敏感列表使用 *
always @(*) begin
    case (sel)
        2'b00: out = a;
        2'b01: out = b;
        2'b10: out = c;
        default: out = d;
    endcase
end

// 等价写法（SystemVerilog）
always_comb begin
    out = (sel == 2'b00) ? a :
          (sel == 2'b01) ? b :
          (sel == 2'b10) ? c : d;
end
```

#### 时序逻辑always块

```verilog
// 带异步复位
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        q <= 1'b0;
    end else begin
        q <= d;
    end
end

// 带同步复位
always @(posedge clk) begin
    if (!rst_n) begin
        q <= 1'b0;
    end else begin
        q <= d;
    end
end

// 带使能
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        q <= 1'b0;
    else if (en)
        q <= d;
end
```

### assign语句

```verilog
// 连续赋值（组合逻辑）
assign out = a & b;
assign result = sel ? a : b;

// 三态门
assign bus = oe ? data : 8'bz;

// 多驱动（线与/线或）
assign tri_bus = sel1 ? data1 : 8'bz;
assign tri_bus = sel2 ? data2 : 8'bz;

// 条件赋值
assign sum = cin ? (a + b + 1) : (a + b);
```

### 参数化设计

```verilog
module counter #(
    parameter MAX_COUNT = 255,           // 普通参数
    parameter WIDTH = $clog2(MAX_COUNT+1) // 计算位宽
)(
    input  wire             clk,
    input  wire             rst_n,
    output reg [WIDTH-1:0]  count,
    output wire             done
);

// localparam（模块内部常量）
localparam HALF_MAX = MAX_COUNT / 2;

assign done = (count == MAX_COUNT);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        count <= {WIDTH{1'b0}};
    else if (count == MAX_COUNT)
        count <= {WIDTH{1'b0}};
    else
        count <= count + 1;
end

endmodule

// 实例化时参数覆盖
counter #(
    .MAX_COUNT(999),
    .WIDTH(10)
) u_counter (
    .clk(clk),
    .rst_n(rst_n),
    .count(count_out),
    .done(done_out)
);
```

---

## 组合逻辑设计

### 多路选择器（MUX）

```verilog
// 2选1 MUX
module mux2to1 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire       sel,
    output wire [7:0] out
);
    assign out = sel ? b : a;
endmodule

// 4选1 MUX
module mux4to1 (
    input  wire [7:0] a, b, c, d,
    input  wire [1:0] sel,
    output reg  [7:0] out
);
    always @(*) begin
        case (sel)
            2'b00: out = a;
            2'b01: out = b;
            2'b10: out = c;
            2'b11: out = d;
        endcase
    end
endmodule

// 参数化 MUX
module mux #(
    parameter DATA_WIDTH = 8,
    parameter SEL_WIDTH = 3,
    parameter NUM_INPUTS = 2**SEL_WIDTH
)(
    input  wire [NUM_INPUTS*DATA_WIDTH-1:0] data_in,  // 打包输入
    input  wire [SEL_WIDTH-1:0]             sel,
    output wire [DATA_WIDTH-1:0]            data_out
);
    // 使用位选择实现
    assign data_out = data_in[sel*DATA_WIDTH +: DATA_WIDTH];
endmodule
```

### 编码器（Encoder）

```verilog
// 8-3优先编码器
module priority_encoder (
    input  wire [7:0] in,
    output reg  [2:0] code,
    output reg        valid
);
    always @(*) begin
        valid = 1'b1;
        casex (in)
            8'b1xxxxxxx: code = 3'd7;
            8'b01xxxxxx: code = 3'd6;
            8'b001xxxxx: code = 3'd5;
            8'b0001xxxx: code = 3'd4;
            8'b00001xxx: code = 3'd3;
            8'b000001xx: code = 3'd2;
            8'b0000001x: code = 3'd1;
            8'b00000001: code = 3'd0;
            default: begin
                code = 3'd0;
                valid = 1'b0;
            end
        endcase
    end
endmodule

// 使用循环实现的优先编码器（综合友好）
module priority_encoder_loop (
    input  wire [7:0] in,
    output reg  [2:0] code,
    output reg        valid
);
    integer i;
    always @(*) begin
        code = 3'd0;
        valid = 1'b0;
        for (i = 7; i >= 0; i = i - 1) begin
            if (in[i]) begin
                code = i[2:0];
                valid = 1'b1;
            end
        end
    end
endmodule
```

### 译码器（Decoder）

```verilog
// 3-8译码器
module decoder3to8 (
    input  wire [2:0] in,
    output reg  [7:0] out
);
    always @(*) begin
        out = 8'b0;
        out[in] = 1'b1;  // 动态索引
    end
endmodule

// 3-8译码器（case写法）
module decoder3to8_case (
    input  wire [2:0] in,
    output reg  [7:0] out
);
    always @(*) begin
        case (in)
            3'd0: out = 8'b0000_0001;
            3'd1: out = 8'b0000_0010;
            3'd2: out = 8'b0000_0100;
            3'd3: out = 8'b0000_1000;
            3'd4: out = 8'b0001_0000;
            3'd5: out = 8'b0010_0000;
            3'd6: out = 8'b0100_0000;
            3'd7: out = 8'b1000_0000;
        endcase
    end
endmodule

// BCD-7段译码器
module bcd7seg (
    input  wire [3:0] bcd,
    output reg  [6:0] seg  // {a,b,c,d,e,f,g}
);
    always @(*) begin
        case (bcd)
            4'd0: seg = 7'b1111110;
            4'd1: seg = 7'b0110000;
            4'd2: seg = 7'b1101101;
            4'd3: seg = 7'b1111001;
            4'd4: seg = 7'b0110011;
            4'd5: seg = 7'b1011011;
            4'd6: seg = 7'b1011111;
            4'd7: seg = 7'b1110000;
            4'd8: seg = 7'b1111111;
            4'd9: seg = 7'b1111011;
            default: seg = 7'b0000000;
        endcase
    end
endmodule
```

### 加法器

```verilog
// 4位行波进位加法器（Ripple Carry Adder）
module rca_4bit (
    input  wire [3:0] a, b,
    input  wire       cin,
    output wire [3:0] sum,
    output wire       cout
);
    wire [3:0] carry;

    full_adder fa0 (.a(a[0]), .b(b[0]), .cin(cin),      .sum(sum[0]), .cout(carry[0]));
    full_adder fa1 (.a(a[1]), .b(b[1]), .cin(carry[0]), .sum(sum[1]), .cout(carry[1]));
    full_adder fa2 (.a(a[2]), .b(b[2]), .cin(carry[1]), .sum(sum[2]), .cout(carry[2]));
    full_adder fa3 (.a(a[3]), .b(b[3]), .cin(carry[2]), .sum(sum[3]), .cout(carry[3]));

    assign cout = carry[3];
endmodule

// 全加器模块
module full_adder (
    input  wire a, b, cin,
    output wire sum, cout
);
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (a & cin) | (b & cin);
endmodule

// 超前进位加法器（Carry Look-Ahead Adder）
module cla_4bit (
    input  wire [3:0] a, b,
    input  wire       cin,
    output wire [3:0] sum,
    output wire       cout
);
    wire [3:0] g, p, c;

    // 生成和传播信号
    assign g = a & b;      // 生成
    assign p = a ^ b;      // 传播

    // 超前进位逻辑
    assign c[0] = cin;
    assign c[1] = g[0] | (p[0] & cin);
    assign c[2] = g[1] | (p[1] & g[0]) | (p[1] & p[0] & cin);
    assign c[3] = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & cin);
    assign cout = g[3] | (p[3] & c[3]);

    // 求和
    assign sum = p ^ c;
endmodule

// 直接使用 + 运算符（推荐，综合工具会优化）
module adder_direct (
    input  wire [7:0] a, b,
    input  wire       cin,
    output wire [7:0] sum,
    output wire       cout
);
    wire [8:0] result = a + b + cin;
    assign sum  = result[7:0];
    assign cout = result[8];
endmodule
```

### 比较器

```verilog
// 8位无符号比较器
module comparator_unsigned (
    input  wire [7:0] a, b,
    output wire       gt,   // a > b
    output wire       eq,   // a == b
    output wire       lt    // a < b
);
    assign gt = (a > b);
    assign eq = (a == b);
    assign lt = (a < b);
endmodule

// 8位有符号比较器
module comparator_signed (
    input  signed [7:0] a, b,
    output wire         gt,
    output wire         eq,
    output wire         lt
);
    assign gt = (a > b);
    assign eq = (a == b);
    assign lt = (a < b);
endmodule

// 参数化比较器
module comparator #(
    parameter WIDTH = 8
)(
    input  wire [WIDTH-1:0] a, b,
    output wire             gt, eq, lt
);
    assign gt = (a > b);
    assign eq = (a == b);
    assign lt = (a < b);
endmodule
```

---

## 时序逻辑设计

### 触发器（Flip-Flop）

```verilog
// D触发器（异步复位）
module dff_async (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 1'b0;
        else
            q <= d;
    end
endmodule

// D触发器（同步复位）
module dff_sync (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_n)
            q <= 1'b0;
        else
            q <= d;
    end
endmodule

// 带使能的D触发器
module dff_en (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire d,
    output reg  q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 1'b0;
        else if (en)
            q <= d;
    end
endmodule

// T触发器（翻转触发器）
module tff (
    input  wire clk,
    input  wire rst_n,
    input  wire t,
    output reg  q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 1'b0;
        else if (t)
            q <= ~q;
    end
endmodule

// JK触发器
module jkff (
    input  wire clk,
    input  wire rst_n,
    input  wire j, k,
    output reg  q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 1'b0;
        else begin
            case ({j, k})
                2'b00: q <= q;       // 保持
                2'b01: q <= 1'b0;    // 复位
                2'b10: q <= 1'b1;    // 置位
                2'b11: q <= ~q;      // 翻转
            endcase
        end
    end
endmodule

// 移位寄存器
module shift_register #(
    parameter WIDTH = 8
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    input  wire             sin,   // 串行输入
    output wire [WIDTH-1:0] q,
    output wire             sout   // 串行输出
);
    reg [WIDTH-1:0] shift_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            shift_reg <= {WIDTH{1'b0}};
        else if (en)
            shift_reg <= {shift_reg[WIDTH-2:0], sin};
    end

    assign q = shift_reg;
    assign sout = shift_reg[WIDTH-1];
endmodule
```

### 计数器

```verilog
// 自由运行计数器
module counter_free #(
    parameter WIDTH = 8
)(
    input  wire             clk,
    input  wire             rst_n,
    output reg [WIDTH-1:0]  count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= {WIDTH{1'b0}};
        else
            count <= count + 1;
    end
endmodule

// 模N计数器
module counter_mod_n #(
    parameter N = 100
)(
    input  wire             clk,
    input  wire             rst_n,
    output reg [$clog2(N)-1:0] count,
    output wire             pulse
);
    localparam MAX = N - 1;
    localparam WIDTH = $clog2(N);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= {WIDTH{1'b0}};
        else if (count == MAX)
            count <= {WIDTH{1'b0}};
        else
            count <= count + 1;
    end

    assign pulse = (count == MAX);
endmodule

// 可逆计数器（上下计数器）
module counter_updown #(
    parameter WIDTH = 8
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    input  wire             up_down,  // 1=上计数，0=下计数
    output reg [WIDTH-1:0]  count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= {WIDTH{1'b0}};
        else if (en) begin
            if (up_down)
                count <= count + 1;
            else
                count <= count - 1;
        end
    end
endmodule

// BCD计数器
module counter_bcd (
    input  wire       clk,
    input  wire       rst_n,
    output reg [3:0]  bcd,
    output wire       carry
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            bcd <= 4'd0;
        else if (bcd == 4'd9)
            bcd <= 4'd0;
        else
            bcd <= bcd + 1;
    end

    assign carry = (bcd == 4'd9);
endmodule

// 60进制计数器（秒计数器）
module counter_60 (
    input  wire       clk,
    input  wire       rst_n,
    output reg [3:0]  ten,     // 十位
    output reg [3:0]  one,     // 个位
    output wire       carry
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ten <= 4'd0;
            one <= 4'd0;
        end else begin
            if (one == 4'd9) begin
                one <= 4'd0;
                if (ten == 4'd5)
                    ten <= 4'd0;
                else
                    ten <= ten + 1;
            end else begin
                one <= one + 1;
            end
        end
    end

    assign carry = (ten == 4'd5 && one == 4'd9);
endmodule
```

### 状态机（FSM）三段式写法

```verilog
// 三段式状态机示例：序列检测器（检测1011）
module seq_detector_1011 (
    input  wire clk,
    input  wire rst_n,
    input  wire din,
    output wire detected
);

// 状态定义（独热码编码）
localparam [3:0] S_IDLE = 4'b0001;
localparam [3:0] S_1    = 4'b0010;
localparam [3:0] S_10   = 4'b0100;
localparam [3:0] S_101  = 4'b1000;

reg [3:0] current_state, next_state;

// 第一段：状态寄存器（时序逻辑）
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        current_state <= S_IDLE;
    else
        current_state <= next_state;
end

// 第二段：次态逻辑（组合逻辑）
always @(*) begin
    next_state = S_IDLE;
    case (current_state)
        S_IDLE: begin
            if (din)
                next_state = S_1;
            else
                next_state = S_IDLE;
        end
        S_1: begin
            if (din)
                next_state = S_1;
            else
                next_state = S_10;
        end
        S_10: begin
            if (din)
                next_state = S_101;
            else
                next_state = S_IDLE;
        end
        S_101: begin
            if (din)
                next_state = S_1;
            else
                next_state = S_10;
        end
        default: next_state = S_IDLE;
    endcase
end

// 第三段：输出逻辑（组合逻辑）
assign detected = (current_state == S_101) && din;

endmodule

// 三段式状态机：交通灯控制器
module traffic_light (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       emergency,  // 紧急车辆
    output reg [1:0]  light_ns,   // 南北方向灯 00=红,01=黄,10=绿
    output reg [1:0]  light_ew    // 东西方向灯
);

// 状态定义
localparam S_NS_GREEN  = 3'd0;
localparam S_NS_YELLOW = 3'd1;
localparam S_EW_GREEN  = 3'd2;
localparam S_EW_YELLOW = 3'd3;
localparam S_EMERGENCY = 3'd4;

// 参数
localparam GREEN_TIME  = 30;  // 绿灯时间（秒）
localparam YELLOW_TIME = 5;   // 黄灯时间

reg [2:0] current_state, next_state;
reg [5:0] timer;
reg       timer_done;

// 第一段：状态寄存器 + 定时器
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        current_state <= S_NS_GREEN;
        timer <= 6'd0;
    end else begin
        current_state <= next_state;
        if (current_state != next_state)
            timer <= 6'd0;
        else
            timer <= timer + 1;
    end
end

// 定时器完成信号
always @(*) begin
    timer_done = 1'b0;
    case (current_state)
        S_NS_GREEN, S_EW_GREEN:
            timer_done = (timer == GREEN_TIME - 1);
        S_NS_YELLOW, S_EW_YELLOW:
            timer_done = (timer == YELLOW_TIME - 1);
        S_EMERGENCY:
            timer_done = (timer == 10);  // 紧急状态10秒
        default: timer_done = 1'b0;
    endcase
end

// 第二段：次态逻辑
always @(*) begin
    next_state = current_state;
    if (emergency && current_state != S_EMERGENCY)
        next_state = S_EMERGENCY;
    else if (timer_done) begin
        case (current_state)
            S_NS_GREEN:  next_state = S_NS_YELLOW;
            S_NS_YELLOW: next_state = S_EW_GREEN;
            S_EW_GREEN:  next_state = S_EW_YELLOW;
            S_EW_YELLOW: next_state = S_NS_GREEN;
            S_EMERGENCY: next_state = S_NS_GREEN;
            default:     next_state = S_NS_GREEN;
        endcase
    end
end

// 第三段：输出逻辑
always @(*) begin
    light_ns = 2'b00;  // 默认红灯
    light_ew = 2'b00;
    case (current_state)
        S_NS_GREEN:  light_ns = 2'b10;
        S_NS_YELLOW: light_ns = 2'b01;
        S_EW_GREEN:  light_ew = 2'b10;
        S_EW_YELLOW: light_ew = 2'b01;
        S_EMERGENCY: begin
            light_ns = 2'b00;
            light_ew = 2'b00;
        end
    endcase
end

endmodule
```

---

## 时序约束

### 建立时间与保持时间

```
时序分析基础概念：

Setup Time（建立时间）：
- 数据必须在时钟沿到来之前稳定的最短时间
- 违例意味着数据到达太晚

Hold Time（保持时间）：
- 数据必须在时钟沿之后保持稳定的最短时间
- 违例意味着数据变化太快

时序路径延迟 = Tco（时钟到输出） + Tlogic（逻辑延迟） + Trouting（布线延迟）

建立时间检查：Tclk > Tco + Tlogic + Trouting + Tsetup
保持时间检查：Thold < Tco + Tlogic + Trouting
```

### SDC时序约束

```tcl
# ============================================
# 时钟约束
# ============================================

# 主时钟定义
create_clock -period 10.000 -name sys_clk [get_ports clk]
# 10ns = 100MHz

# 生成时钟（PLL输出）
create_generated_clock -name pll_clk \
    -source [get_pins pll/CLKIN] \
    -master_clock sys_clk \
    [get_pins pll/CLKOUT]

# 虚拟时钟（用于IO约束）
create_clock -period 10.000 -name virtual_clk

# 时钟不确定性
set_clock_uncertainty -setup 0.500 [get_clocks sys_clk]
set_clock_uncertainty -hold  0.100 [get_clocks sys_clk]

# 时钟延迟
set_clock_latency -source -max 2.000 [get_clocks sys_clk]
set_clock_latency -source -min 1.000 [get_clocks sys_clk]

# ============================================
# IO约束
# ============================================

# 输入延迟
set_input_delay -clock sys_clk -max 3.000 [get_ports data_in*]
set_input_delay -clock sys_clk -min 1.000 [get_ports data_in*]

# 输出延迟
set_output_delay -clock sys_clk -max 3.000 [get_ports data_out*]
set_output_delay -clock sys_clk -min 1.000 [get_ports data_out*]

# ============================================
# 跨时钟域约束
# ============================================

# 异步时钟域
set_clock_groups -asynchronous \
    -group [get_clocks sys_clk] \
    -group [get_clocks adc_clk]

# 假路径
set_false_path -from [get_clocks clk_a] -to [get_clocks clk_b]
set_false_path -from [get_ports reset]

# 多周期路径
set_multicycle_path -setup 2 -from [get_cells slow_reg] -to [get_cells fast_reg]
set_multicycle_path -hold  1 -from [get_cells slow_reg] -to [get_cells fast_reg]

# ============================================
# 最大延迟约束
# ============================================

# 异步FIFO格雷码指针
set_max_delay -datapath_only 5.000 \
    -from [get_cells fifo/wr_ptr*] \
    -to   [get_cells fifo/rd_ptr_sync*]

# ============================================
# 物理约束
# ============================================

# 位置约束
set_property PACKAGE_PIN F22 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]

# 引脚位置
set_property PACKAGE_PIN Y21 [get_ports {data_in[0]}]
set_property PACKAGE_PIN Y20 [get_ports {data_in[1]}]

# IO标准
set_property IOSTANDARD LVCMOS18 [get_ports data_in*]
set_property IOSTANDARD LVDS [get_ports {data_p data_n}]
```

### 时序报告解读

```tcl
# Vivado时序报告示例
# ============================================
# Setup Time Report
# ============================================
# 
# Slack (MET) : 0.523ns
#   (MET means timing is met, VIOLATED means timing fails)
#
# Source:     u_data/reg_data_reg[0]/C  (rising edge-triggered flip-flop)
# Destination: u_data/reg_out_reg[3]/D  (rising edge-triggered flip-flop)
#
# Path Type:  Max (Slow Process Corner)
#
# Requirement:          10.000ns  (100MHz clock)
# Data Path Delay:       9.477ns  (logic 3.200ns, route 6.277ns)
# Logic Levels:          4
# Clock Path Skew:      -0.152ns
# Clock Uncertainty:     0.500ns
#
# ============================================
# 关键指标解读：
# - Slack > 0: 时序满足
# - Slack < 0: 时序违例，需要优化
# - Data Path Delay: 数据路径总延迟
# - Logic: 逻辑单元延迟（LUT、FF等）
# - Route: 布线延迟（互连线延迟）
# - Logic Levels: 逻辑级数（越少越好）
# ============================================

# 常见时序优化方法：
# 1. 增加流水线级数
# 2. 减少逻辑级数
# 3. 使用更快的速度等级器件
# 4. 优化布局布线约束
# 5. 使用寄存器复制（Register Duplication）
# 6. 手动布局关键路径
```

---

## IP核使用

### PLL/MMCM（时钟管理）

```verilog
// Xilinx MMCM例化
// 生成100MHz、50MHz、25MHz三个时钟
mmcm_clk_gen u_mmcm (
    .clk_in1    (sys_clk_100m),    // 100MHz输入
    .clk_out1   (clk_100m),        // 100MHz输出
    .clk_out2   (clk_50m),         // 50MHz输出
    .clk_out3   (clk_25m),         // 25MHz输出
    .reset      (sys_rst),
    .locked     (pll_locked)       // PLL锁定信号
);

// 使用锁定信号作为复位
wire sys_rst_n = pll_locked & ~sys_rst;

// Intel PLL例化
pll_clk_gen u_pll (
    .areset     (sys_rst),
    .inclk0     (sys_clk_50m),
    .c0         (clk_100m),
    .c1         (clk_25m),
    .locked     (pll_locked)
);
```

### FIFO

```verilog
// 同步FIFO
sync_fifo #(
    .DATA_WIDTH(8),
    .FIFO_DEPTH(16)
) u_sync_fifo (
    .clk        (clk),
    .rst_n      (rst_n),
    .wr_en      (fifo_wr_en),
    .wr_data    (fifo_wr_data),
    .rd_en      (fifo_rd_en),
    .rd_data    (fifo_rd_data),
    .full       (fifo_full),
    .empty      (fifo_empty),
    .data_count (fifo_count)
);

// 异步FIFO（跨时钟域）
async_fifo #(
    .DATA_WIDTH(16),
    .ADDR_WIDTH(8)  // 深度256
) u_async_fifo (
    .wr_clk     (wr_clk),
    .wr_rst_n   (wr_rst_n),
    .wr_en      (wr_en),
    .wr_data    (wr_data),
    .wr_full    (wr_full),
    .rd_clk     (rd_clk),
    .rd_rst_n   (rd_rst_n),
    .rd_en      (rd_en),
    .rd_data    (rd_data),
    .rd_empty   (rd_empty)
);

// Xilinx FIFO IP例化
fifo_generator_0 u_fifo (
    .clk        (clk),
    .srst       (rst),
    .din        (fifo_din),
    .wr_en      (fifo_wr_en),
    .rd_en      (fifo_rd_en),
    .dout       (fifo_dout),
    .full       (fifo_full),
    .empty      (fifo_empty),
    .data_count (fifo_count)
);
```

### RAM

```verilog
// 单端口RAM
single_port_ram #(
    .DATA_WIDTH(8),
    .ADDR_WIDTH(10)  // 1024深度
) u_ram (
    .clk   (clk),
    .we    (ram_we),
    .addr  (ram_addr),
    .din   (ram_din),
    .dout  (ram_dout)
);

// 双端口RAM
dual_port_ram #(
    .DATA_WIDTH(16),
    .ADDR_WIDTH(9)
) u_dpram (
    .clk_a  (clk_a),
    .we_a   (we_a),
    .addr_a (addr_a),
    .din_a  (din_a),
    .dout_a (dout_a),
    .clk_b  (clk_b),
    .we_b   (we_b),
    .addr_b (addr_b),
    .din_b  (din_b),
    .dout_b (dout_b)
);

// ROM实现
module rom_lookup_table (
    input  wire [3:0] addr,
    output reg  [7:0] data
);
    always @(*) begin
        case (addr)
            4'd0:  data = 8'h00;
            4'd1:  data = 8'h03;
            4'd2:  data = 8'h06;
            4'd3:  data = 8'h09;
            // ... 查找表数据
            default: data = 8'h00;
        endcase
    end
endmodule
```

### UART IP

```verilog
// UART发送模块
module uart_tx #(
    parameter CLK_FREQ  = 50_000_000,  // 50MHz
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data_in,
    input  wire       start,
    output reg        txd,
    output wire       busy
);
    localparam BAUD_CNT = CLK_FREQ / BAUD_RATE;

    reg [15:0] baud_cnt;
    reg [3:0]  bit_cnt;
    reg [9:0]  shift_reg;
    reg        tx_active;

    assign busy = tx_active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            txd <= 1'b1;
            baud_cnt <= 16'd0;
            bit_cnt <= 4'd0;
            shift_reg <= 10'h3FF;
            tx_active <= 1'b0;
        end else begin
            if (start && !tx_active) begin
                tx_active <= 1'b1;
                shift_reg <= {1'b1, data_in, 1'b0};  // 停止位+数据+起始位
                bit_cnt <= 4'd0;
                baud_cnt <= 16'd0;
            end else if (tx_active) begin
                if (baud_cnt == BAUD_CNT - 1) begin
                    baud_cnt <= 16'd0;
                    txd <= shift_reg[0];
                    shift_reg <= {1'b1, shift_reg[9:1]};
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 4'd9) begin
                        tx_active <= 1'b0;
                        txd <= 1'b1;
                    end
                end else begin
                    baud_cnt <= baud_cnt + 1;
                end
            end
        end
    end
endmodule

// UART接收模块
module uart_rx #(
    parameter CLK_FREQ  = 50_000_000,
    parameter BAUD_RATE = 115200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rxd,
    output reg  [7:0] data_out,
    output reg        valid
);
    localparam BAUD_CNT = CLK_FREQ / BAUD_RATE;
    localparam HALF_BAUD = BAUD_CNT / 2;

    reg [15:0] baud_cnt;
    reg [3:0]  bit_cnt;
    reg [7:0]  shift_reg;
    reg        rx_active;
    reg [1:0]  rxd_sync;

    // 同步器（消除亚稳态）
    always @(posedge clk) begin
        rxd_sync <= {rxd_sync[0], rxd};
    end

    // 起始位检测
    wire start_bit = !rxd_sync[1] && !rx_active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            baud_cnt <= 16'd0;
            bit_cnt <= 4'd0;
            shift_reg <= 8'd0;
            rx_active <= 1'b0;
            data_out <= 8'd0;
            valid <= 1'b0;
        end else begin
            valid <= 1'b0;
            if (start_bit) begin
                rx_active <= 1'b1;
                baud_cnt <= HALF_BAUD;  // 采样中间点
                bit_cnt <= 4'd0;
            end else if (rx_active) begin
                if (baud_cnt == BAUD_CNT - 1) begin
                    baud_cnt <= 16'd0;
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 4'd0) begin
                        // 起始位验证
                        if (rxd_sync[1]) rx_active <= 1'b0;
                    end else if (bit_cnt <= 4'd8) begin
                        shift_reg <= {rxd_sync[1], shift_reg[7:1]};
                    end else begin
                        // 停止位
                        if (rxd_sync[1]) begin
                            data_out <= shift_reg;
                            valid <= 1'b1;
                        end
                        rx_active <= 1'b0;
                    end
                end else begin
                    baud_cnt <= baud_cnt + 1;
                end
            end
        end
    end
endmodule
```

### SPI IP

```verilog
// SPI Master
module spi_master #(
    parameter CLK_DIV = 4  // 时钟分频
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] tx_data,
    input  wire       start,
    output reg  [7:0] rx_data,
    output reg        done,
    // SPI接口
    output reg        sclk,
    output reg        mosi,
    input  wire       miso,
    output reg        cs_n
);
    reg [3:0]  clk_cnt;
    reg [3:0]  bit_cnt;
    reg [7:0]  tx_shift;
    reg [7:0]  rx_shift;
    reg        active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk <= 1'b0;
            mosi <= 1'b0;
            cs_n <= 1'b1;
            done <= 1'b0;
            active <= 1'b0;
            clk_cnt <= 4'd0;
            bit_cnt <= 4'd0;
        end else begin
            done <= 1'b0;
            if (start && !active) begin
                active <= 1'b1;
                cs_n <= 1'b0;
                tx_shift <= tx_data;
                bit_cnt <= 4'd0;
                clk_cnt <= 4'd0;
            end else if (active) begin
                if (clk_cnt == CLK_DIV - 1) begin
                    clk_cnt <= 4'd0;
                    sclk <= ~sclk;
                    if (sclk) begin
                        // 下降沿：发送数据
                        mosi <= tx_shift[7];
                        tx_shift <= {tx_shift[6:0], 1'b0};
                    end else begin
                        // 上升沿：接收数据
                        rx_shift <= {rx_shift[6:0], miso};
                        bit_cnt <= bit_cnt + 1;
                        if (bit_cnt == 4'd7) begin
                            active <= 1'b0;
                            cs_n <= 1'b1;
                            rx_data <= {rx_shift[6:0], miso};
                            done <= 1'b1;
                        end
                    end
                end else begin
                    clk_cnt <= clk_cnt + 1;
                end
            end
        end
    end
endmodule
```

### I2C IP

```verilog
// I2C Master
module i2c_master (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [6:0] slave_addr,
    input  wire [7:0] data_in,
    input  wire       rw,        // 0=写, 1=读
    input  wire       start,
    output reg  [7:0] data_out,
    output reg        done,
    output reg        ack_error,
    // I2C接口
    output reg        scl,
    inout  wire       sda
);
    // 状态定义
    localparam [3:0] S_IDLE     = 4'd0;
    localparam [3:0] S_START    = 4'd1;
    localparam [3:0] S_ADDR     = 4'd2;
    localparam [3:0] S_RW       = 4'd3;
    localparam [3:0] S_ACK1     = 4'd4;
    localparam [3:0] S_DATA     = 4'd5;
    localparam [3:0] S_ACK2     = 4'd6;
    localparam [3:0] S_STOP     = 4'd7;

    reg [3:0]  state;
    reg [3:0]  bit_cnt;
    reg [7:0]  shift_reg;
    reg        sda_out;
    reg        sda_oe;  // 输出使能

    assign sda = sda_oe ? sda_out : 1'bz;

    // 时钟分频（假设50MHz -> 100KHz I2C）
    localparam CLK_DIV = 250;
    reg [7:0] clk_cnt;
    reg       i2c_clk_en;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_cnt <= 8'd0;
            i2c_clk_en <= 1'b0;
        end else begin
            if (clk_cnt == CLK_DIV - 1) begin
                clk_cnt <= 8'd0;
                i2c_clk_en <= 1'b1;
            end else begin
                clk_cnt <= clk_cnt + 1;
                i2c_clk_en <= 1'b0;
            end
        end
    end

    // 主状态机
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            scl <= 1'b1;
            sda_out <= 1'b1;
            sda_oe <= 1'b1;
            done <= 1'b0;
            ack_error <= 1'b0;
            bit_cnt <= 4'd0;
        end else if (i2c_clk_en) begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    scl <= 1'b1;
                    sda_out <= 1'b1;
                    if (start) begin
                        state <= S_START;
                        sda_out <= 1'b0;  // SDA下降沿
                    end
                end
                S_START: begin
                    scl <= 1'b0;  // SCL下降沿
                    shift_reg <= {slave_addr, rw};
                    bit_cnt <= 4'd0;
                    state <= S_ADDR;
                end
                S_ADDR: begin
                    sda_out <= shift_reg[7];
                    shift_reg <= {shift_reg[6:0], 1'b0};
                    scl <= 1'b1;
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 4'd7)
                        state <= S_RW;
                    else
                        scl <= 1'b0;
                end
                S_RW: begin
                    scl <= 1'b0;
                    sda_oe <= 1'b0;  // 释放SDA，等待ACK
                    state <= S_ACK1;
                end
                S_ACK1: begin
                    ack_error <= sda;  // 0=ACK, 1=NACK
                    scl <= 1'b1;
                    shift_reg <= data_in;
                    bit_cnt <= 4'd0;
                    state <= S_DATA;
                    scl <= 1'b0;
                end
                S_DATA: begin
                    sda_oe <= 1'b1;
                    sda_out <= shift_reg[7];
                    shift_reg <= {shift_reg[6:0], 1'b0};
                    scl <= 1'b1;
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 4'd7) begin
                        state <= S_ACK2;
                        sda_oe <= 1'b0;
                    end else begin
                        scl <= 1'b0;
                    end
                end
                S_ACK2: begin
                    scl <= 1'b1;
                    state <= S_STOP;
                end
                S_STOP: begin
                    sda_oe <= 1'b1;
                    sda_out <= 1'b0;
                    scl <= 1'b1;
                    sda_out <= 1'b1;  // SDA上升沿
                    done <= 1'b1;
                    state <= S_IDLE;
                end
            endcase
        end
    end
endmodule
```

---

## FPGA调试

### ILA（Integrated Logic Analyzer）

```tcl
# Vivado ILA设置
# 1. 在代码中插入ILA核
ila_0 u_ila (
    .clk    (sys_clk),
    .probe0 (data_in),
    .probe1 (state),
    .probe2 (valid),
    .probe3 (ready)
);

# 2. 或者通过GUI添加ILA
# Flow Navigator → IP Catalog →ILA

# 3. ILA触发设置
# 触发条件：state == 3 && valid == 1
# 采样深度：4096
# 触发位置：Pre-trigger 50%
```

### VIO（Virtual Input/Output）

```verilog
// VIO用于动态控制和监视
vio_0 u_vio (
    .clk        (sys_clk),
    .probe_in0  (counter),      // 读取计数器值
    .probe_in1  (state),        // 读取状态机状态
    .probe_out0 (enable),       // 控制使能
    .probe_out1 (test_mode)     // 控制测试模式
);

// 在代码中使用VIO输出
always @(posedge clk) begin
    if (enable)
        counter <= counter + 1;
end
```

### ChipScope / SignalTap

```tcl
# Xilinx ChipScope（旧版本）
# 1. 创建CDC（ChipScope Design Flow）
# 2. 添加ILA和ICON核
# 3. 连接信号到ILA端口
# 4. 生成比特流并下载
# 5. 打开ChipScope Analyzer设置触发

# Intel SignalTap
# 1. Tools → SignalTap II Logic Analyzer
# 2. 添加采样时钟和信号
# 3. 设置触发条件
# 4. 编译并下载
# 5. 运行采集
```

### 调试技巧

```verilog
// 1. 使用LED显示状态
assign led[3:0] = state;
assign led[7:4] = error_code;

// 2. 使用计数器测量频率
reg [31:0] freq_cnt;
reg [31:0] freq_result;
reg        meas_done;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        freq_cnt <= 32'd0;
        freq_result <= 32'd0;
        meas_done <= 1'b0;
    end else begin
        if (1s_pulse) begin  // 1秒脉冲
            freq_result <= freq_cnt;
            freq_cnt <= 32'd0;
            meas_done <= 1'b1;
        end else begin
            freq_cnt <= freq_cnt + 1;
            meas_done <= 1'b0;
        end
    end
end

// 3. 使用标志信号捕获毛刺
reg glitch_flag;
always @(posedge clk) begin
    if (unexpected_condition)
        glitch_flag <= 1'b1;
end
// 用ILA触发glitch_flag上升沿

// 4. 使用虚拟IO控制测试
wire test_enable = vio_enable;
wire [7:0] test_data = vio_data;
```

---

## Zynq SoC开发

### PS + PL 架构

```
Zynq-7000 SoC架构：

PS（Processing System）：
- 双核ARM Cortex-A9（最高1GHz）
- L1 Cache（32KB I-Cache + 32KB D-Cache / 核）
- L2 Cache（512KB，共享）
- DDR3/DDR3L控制器
- 外设：USB、Ethernet、SDIO、SPI、I2C、UART、GPIO
- DMA控制器
- OCM（On-Chip Memory，256KB）

PL（Programmable Logic）：
- 与7系列FPGA相同的架构
- CLB、BRAM、DSP、IOB等
- 通过AXI总线与PS连接

互连：
- AXI_HP（高性能端口）：4个，64位，用于大数据量传输
- AXI_ACP（加速器一致性端口）：1个，64位，支持缓存一致性
- AXI_GP（通用端口）：4个，32位，用于控制和状态
```

### AXI总线协议

```verilog
// AXI4-Lite接口（简化版，用于寄存器访问）
module axi4_lite_slave (
    input  wire        s_axi_aclk,
    input  wire        s_axi_aresetn,

    // 写地址通道
    input  wire [31:0] s_axi_awaddr,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,

    // 写数据通道
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,

    // 写响应通道
    output wire [1:0]  s_axi_bresp,
    output wire        s_axi_bvalid,
    input  wire        s_axi_bready,

    // 读地址通道
    input  wire [31:0] s_axi_araddr,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,

    // 读数据通道
    output wire [31:0] s_axi_rdata,
    output wire [1:0]  s_axi_rresp,
    output wire        s_axi_rvalid,
    input  wire        s_axi_rready
);

    // 内部寄存器
    reg [31:0] reg_control;
    reg [31:0] reg_status;
    reg [31:0] reg_data_in;
    reg [31:0] reg_data_out;

    // 写逻辑
    reg [1:0]  write_state;
    reg [31:0] write_addr;

    localparam W_IDLE = 2'd0;
    localparam W_ADDR = 2'd1;
    localparam W_DATA = 2'd2;
    localparam W_RESP = 2'd3;

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            write_state <= W_IDLE;
            write_addr <= 32'd0;
            reg_control <= 32'd0;
            reg_data_out <= 32'd0;
        end else begin
            case (write_state)
                W_IDLE: begin
                    if (s_axi_awvalid) begin
                        write_addr <= s_axi_awaddr;
                        write_state <= W_DATA;
                    end
                end
                W_DATA: begin
                    if (s_axi_wvalid) begin
                        case (write_addr[7:0])
                            8'h00: reg_control <= s_axi_wdata;
                            8'h08: reg_data_out <= s_axi_wdata;
                        endcase
                        write_state <= W_RESP;
                    end
                end
                W_RESP: begin
                    if (s_axi_bready)
                        write_state <= W_IDLE;
                end
            endcase
        end
    end

    assign s_axi_awready = (write_state == W_IDLE);
    assign s_axi_wready = (write_state == W_DATA);
    assign s_axi_bvalid = (write_state == W_RESP);
    assign s_axi_bresp = 2'b00;  // OKAY

    // 读逻辑
    reg [1:0]  read_state;
    reg [31:0] read_data;

    localparam R_IDLE = 2'd0;
    localparam R_ADDR = 2'd1;
    localparam R_DATA = 2'd2;

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            read_state <= R_IDLE;
            read_data <= 32'd0;
        end else begin
            case (read_state)
                R_IDLE: begin
                    if (s_axi_arvalid) begin
                        case (s_axi_araddr[7:0])
                            8'h00: read_data <= reg_control;
                            8'h04: read_data <= reg_status;
                            8'h08: read_data <= reg_data_in;
                            default: read_data <= 32'd0;
                        endcase
                        read_state <= R_DATA;
                    end
                end
                R_DATA: begin
                    if (s_axi_rready)
                        read_state <= R_IDLE;
                end
            endcase
        end
    end

    assign s_axi_arready = (read_state == R_IDLE);
    assign s_axi_rvalid = (read_state == R_DATA);
    assign s_axi_rdata = read_data;
    assign s_axi_rresp = 2'b00;  // OKAY

endmodule
```

### PS控制PL示例

```c
// C代码示例：PS通过AXI控制PL
#include "xparameters.h"
#include "xil_io.h"

// 基地址（在Vivado中分配）
#define PL_BASE_ADDR    0x43C00000
#define REG_CONTROL     0x00
#define REG_STATUS      0x04
#define REG_DATA_IN     0x08
#define REG_DATA_OUT    0x0C

// 初始化PL
void pl_init(void) {
    // 复位PL
    Xil_Out32(PL_BASE_ADDR + REG_CONTROL, 0x00000001);
    usleep(1000);
    Xil_Out32(PL_BASE_ADDR + REG_CONTROL, 0x00000000);
}

// 写数据到PL
void pl_write_data(uint32_t data) {
    Xil_Out32(PL_BASE_ADDR + REG_DATA_OUT, data);
    // 触发处理
    Xil_Out32(PL_BASE_ADDR + REG_CONTROL, 0x00000002);
}

// 从PL读取数据
uint32_t pl_read_data(void) {
    // 等待数据就绪
    while (!(Xil_In32(PL_BASE_ADDR + REG_STATUS) & 0x01));
    return Xil_In32(PL_BASE_ADDR + REG_DATA_IN);
}

// 检查PL状态
uint32_t pl_get_status(void) {
    return Xil_In32(PL_BASE_ADDR + REG_STATUS);
}
```

### Linux on Zynq

```bash
# 1. 使用PetaLinux创建工程
petalinux-create --type project --template zynq --name my_zynq

# 2. 导入硬件描述（XSA文件）
petalinux-config --get-hw-description=./hw_platform.xsa

# 3. 配置Linux内核
petalinux-config -c kernel

# 4. 配置设备树
# project-spec/meta-user/recipes-bsp/device-tree/files/system-user.dtsi
# 添加自定义设备节点

# 5. 构建
petalinux-build

# 6. 生成启动镜像
petalinux-package --boot --fsbl images/linux/zynq_fsbl.elf \
    --fpga images/linux/system.bit --u-boot

# 7. 烧写到SD卡
# 将BOOT.BIN和image.ub复制到SD卡

# 设备树示例（添加自定义IP）
/ {
    my_custom_ip@43C00000 {
        compatible = "xlnx,my-custom-ip";
        reg = <0x43C00000 0x10000>;
        interrupts = <0 29 1>;  // SPI中断
    };
};
```

---

## FPGA vs MCU vs ASIC对比

| 特性 | FPGA | MCU | ASIC |
|------|------|-----|------|
| **灵活性** | 可重复编程 | 软件可改 | 固定 |
| **性能** | 并行处理，高吞吐 | 顺序执行 | 最高性能 |
| **功耗** | 中等 | 低~中 | 最低 |
| **成本（小批量）** | 高（芯片贵） | 低 | 极高（NRE） |
| **成本（大批量）** | 高 | 低 | 最低 |
| **开发周期** | 中等 | 短 | 长（数月~年） |
| **上市时间** | 快 | 最快 | 慢 |
| **设计复杂度** | 高 | 低 | 极高 |
| **适用场景** | 原型、小批量、高性能 | 控制、低功耗 | 大批量、极致性能 |
| **典型应用** | 通信、图像、AI加速 | 嵌入式控制 | 手机SoC、CPU |
| **开发语言** | Verilog/VHDL | C/C++ | Verilog/VHDL |
| **调试方式** | ILA/SignalTap | JTAG/SWD | 仿真+后仿 |
| **升级方式** | 重新配置Flash | 更新固件 | 重新流片 |

### 选择指南

```
选择FPGA的场景：
✓ 需要大量并行处理（图像、信号处理）
✓ 需要自定义接口协议
✓ 需要亚纳秒级延迟
✓ 产品还在验证阶段，需要灵活性
✓ 小批量生产，NRE成本不划算
✓ 需要硬件加速（AI、加密）

选择MCU的场景：
✓ 控制类应用（电机、温控）
✓ 成本敏感
✓ 功耗敏感（电池供电）
✓ 开发周期短
✓ 复杂算法用软件实现更方便

选择ASIC的场景：
✓ 大批量生产（>100K）
✓ 极致性能要求
✓ 极致功耗要求
✓ 成本敏感（大批量）
✓ 产品已经定型
```

---

## 常见应用

### 图像处理

```verilog
// 图像灰度转换
module rgb2gray (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [23:0] rgb_in,    // {R,G,B}
    input  wire        valid_in,
    output reg  [7:0]  gray_out,
    output reg         valid_out
);
    // 灰度 = 0.299*R + 0.587*G + 0.114*B
    // 简化：Gray = (R*77 + G*150 + B*29) >> 8
    reg [15:0] r_mult, g_mult, b_mult;
    reg [15:0] gray_sum;

    always @(posedge clk) begin
        r_mult <= rgb_in[23:16] * 8'd77;
        g_mult <= rgb_in[15:8]  * 8'd150;
        b_mult <= rgb_in[7:0]   * 8'd29;
        gray_sum <= r_mult + g_mult + b_mult;
        gray_out <= gray_sum[15:8];
        valid_out <= valid_in;
    end
endmodule

// 3x3 Sobel边缘检测
module sobel_3x3 (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] pixel_in,
    input  wire       valid_in,
    output reg  [7:0] edge_out,
    output reg        valid_out
);
    // 行缓冲
    reg [7:0] line_buf [0:2][0:1023];  // 3行缓冲
    reg [9:0] col_cnt;
    reg [1:0] row_cnt;

    // 3x3窗口
    wire [7:0] window [0:2][0:2];

    // Sobel算子
    // Gx = [-1 0 1; -2 0 2; -1 0 1]
    // Gy = [-1 -2 -1; 0 0 0; 1 2 1]

    reg signed [10:0] gx, gy;
    reg [10:0] abs_gx, abs_gy;
    reg [10:0] edge_sum;

    always @(posedge clk) begin
        // 计算梯度
        gx <= -window[0][0] + window[0][2] 
              - 2*window[1][0] + 2*window[1][2] 
              - window[2][0] + window[2][2];
        gy <= -window[0][0] - 2*window[0][1] - window[0][2] 
              + window[2][0] + 2*window[2][1] + window[2][2];

        // 取绝对值
        abs_gx <= gx[10] ? -gx : gx;
        abs_gy <= gy[10] ? -gy : gy;

        // 边缘强度 = |Gx| + |Gy|
        edge_sum <= abs_gx + abs_gy;
        edge_out <= edge_sum > 255 ? 8'd255 : edge_sum[7:0];
    end
endmodule
```

### 通信基带

```verilog
// BPSK调制器
module bpsk_modulator (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       data_in,      // 基带数据
    input  wire       valid_in,
    output reg signed [15:0] i_out,  // I路输出
    output reg signed [15:0] q_out,  // Q路输出
    output reg        valid_out
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i_out <= 16'd0;
            q_out <= 16'd0;
            valid_out <= 1'b0;
        end else begin
            valid_out <= valid_in;
            if (data_in)
                i_out <= 16'sd16384;   // +1
            else
                i_out <= -16'sd16384;  // -1
            q_out <= 16'sd0;
        end
    end
endmodule

// 16QAM映射
module qam16_mapper (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [3:0] data_in,       // 4bit输入
    input  wire       valid_in,
    output reg signed [15:0] i_out,
    output reg signed [15:0] q_out,
    output reg        valid_out
);
    // 16QAM星座图映射
    // 数据bit[3:2] → I路，bit[1:0] → Q路
    // 00→-3, 01→-1, 11→+1, 10→+3

    function signed [15:0] map_axis;
        input [1:0] bits;
        begin
            case (bits)
                2'b00: map_axis = -16'sd24576;  // -3
                2'b01: map_axis = -16'sd8192;   // -1
                2'b11: map_axis =  16'sd8192;   // +1
                2'b10: map_axis =  16'sd24576;  // +3
            endcase
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i_out <= 16'd0;
            q_out <= 16'd0;
            valid_out <= 1'b0;
        end else begin
            valid_out <= valid_in;
            i_out <= map_axis(data_in[3:2]);
            q_out <= map_axis(data_in[1:0]);
        end
    end
endmodule
```

### 电机控制

```verilog
// PWM生成器
module pwm_generator #(
    parameter COUNTER_WIDTH = 12
)(
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [COUNTER_WIDTH-1:0] duty,       // 占空比
    input  wire [COUNTER_WIDTH-1:0] period,     // 周期
    output reg                      pwm_out
);
    reg [COUNTER_WIDTH-1:0] counter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= {COUNTER_WIDTH{1'b0}};
            pwm_out <= 1'b0;
        end else begin
            if (counter >= period)
                counter <= {COUNTER_WIDTH{1'b0}};
            else
                counter <= counter + 1;
            pwm_out <= (counter < duty);
        end
    end
endmodule

// 三相PWM生成（用于BLDC/PMSM）
module three_phase_pwm (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [11:0] duty_a,
    input  wire [11:0] duty_b,
    input  wire [11:0] duty_c,
    output wire        pwm_a,
    output wire        pwm_b,
    output wire        pwm_c,
    output wire        pwm_a_n,
    output wire        pwm_b_n,
    output wire        pwm_c_n
);
    localparam PERIOD = 12'd4095;

    pwm_generator #(.COUNTER_WIDTH(12)) pwm_gen_a (
        .clk(clk), .rst_n(rst_n),
        .duty(duty_a), .period(PERIOD),
        .pwm_out(pwm_a)
    );

    pwm_generator #(.COUNTER_WIDTH(12)) pwm_gen_b (
        .clk(clk), .rst_n(rst_n),
        .duty(duty_b), .period(PERIOD),
        .pwm_out(pwm_b)
    );

    pwm_generator #(.COUNTER_WIDTH(12)) pwm_gen_c (
        .clk(clk), .rst_n(rst_n),
        .duty(duty_c), .period(PERIOD),
        .pwm_out(pwm_c)
    );

    // 互补输出（带死区）
    assign pwm_a_n = ~pwm_a;
    assign pwm_b_n = ~pwm_b;
    assign pwm_c_n = ~pwm_c;
endmodule
```

### 高速数据采集

```verilog
// ADC数据采集模块
module adc_acquisition #(
    parameter ADC_WIDTH = 14,
    parameter FIFO_DEPTH = 1024
)(
    input  wire                    adc_clk,
    input  wire                    sys_clk,
    input  wire                    rst_n,
    input  wire [ADC_WIDTH-1:0]    adc_data,
    input  wire                    adc_valid,
    // AXI Stream接口
    output wire [31:0]             m_axis_tdata,
    output wire                    m_axis_tvalid,
    input  wire                    m_axis_tready,
    output wire                    m_axis_tlast
);
    // 跨时钟域FIFO
    wire fifo_full, fifo_empty;
    wire [ADC_WIDTH-1:0] fifo_dout;

    async_fifo #(
        .DATA_WIDTH(ADC_WIDTH),
        .ADDR_WIDTH($clog2(FIFO_DEPTH))
    ) u_fifo (
        .wr_clk    (adc_clk),
        .wr_rst_n  (rst_n),
        .wr_en     (adc_valid && !fifo_full),
        .wr_data   (adc_data),
        .rd_clk    (sys_clk),
        .rd_rst_n  (rst_n),
        .rd_en     (m_axis_tready && !fifo_empty),
        .rd_data   (fifo_dout)
    );

    // 数据打包（14bit -> 32bit）
    reg [1:0] pack_cnt;
    reg [31:0] pack_data;

    always @(posedge sys_clk or negedge rst_n) begin
        if (!rst_n) begin
            pack_cnt <= 2'd0;
            pack_data <= 32'd0;
        end else if (m_axis_tready && !fifo_empty) begin
            case (pack_cnt)
                2'd0: pack_data[13:0] <= fifo_dout;
                2'd1: pack_data[27:14] <= fifo_dout;
                2'd2: begin
                    pack_data[31:28] <= fifo_dout[3:0];
                end
            endcase
            pack_cnt <= pack_cnt + 1;
        end
    end

    assign m_axis_tdata = pack_data;
    assign m_axis_tvalid = (pack_cnt == 2'd2) && !fifo_empty;
    assign m_axis_tlast = 1'b0;

endmodule
```

---

## 参考资源

### 学习资料

| 类别 | 资源 | 说明 |
|------|------|------|
| **入门书籍** | 《Verilog数字系统设计教程》夏宇闻 | 经典入门教材 |
| **进阶书籍** | 《FPGA原理和结构》天野英晴 | 深入理解FPGA架构 |
| **实战书籍** | 《FPGA设计实战》 | 工程实践指南 |
| **官方文档** | Xilinx UG472/UG473/UG474 | 7系列FPGA时钟/SelectIO/配置 |
| **官方文档** | Xilinx UG901 | Vivado综合指南 |
| **在线课程** | Nandland FPGA入门 | 免费英文教程 |
| **在线课程** | FPGA4Fun | 实用项目示例 |

### 常用工具

```
Xilinx/AMD:
- Vivado Design Suite（综合、实现、调试）
- Vitis HLS（高层次综合）
- PetaLinux（嵌入式Linux）
- ModelSim/QuestaSim（仿真）

Intel/Altera:
- Quartus Prime（综合、实现）
- Platform Designer（Qsys，系统集成）
- ModelSim（仿真）

第三方：
- ModelSim（仿真，支持多厂商）
- Synplify（第三方综合工具）
- Verilator（开源仿真器）
- GTKWave（开源波形查看器）
- cocotb（Python仿真框架）
```

### Verilog编码规范

```verilog
// 1. 信号命名
wire clk_100m;           // 时钟信号，带频率后缀
wire rst_n;              // 低有效复位，_n后缀
reg  [7:0] data_reg;     // 寄存器，_reg后缀
wire [7:0] data_next;    // 次态信号，_next后缀

// 2. 模块实例化
module_name #(
    .PARAM1(value1),
    .PARAM2(value2)
) u_instance_name (
    .port_name(signal_name),
    ...
);

// 3. 状态机命名
localparam [2:0] S_IDLE  = 3'd0;
localparam [2:0] S_START = 3'd1;
localparam [2:0] S_DATA  = 3'd2;
localparam [2:0] S_STOP  = 3'd3;

// 4. 注释规范
// 模块功能描述
// 端口说明
// 修改历史

// 5. 代码组织
// 参数定义
// 端口声明
// 内部信号
// 组合逻辑
// 时序逻辑
// 子模块实例化
```

---

## 附录：常用Verilog模板

### 模板1：带使能的寄存器

```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        data_reg <= DEFAULT_VALUE;
    else if (en)
        data_reg <= data_next;
end
```

### 模板2：计数器

```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        cnt <= {WIDTH{1'b0}};
    else if (cnt == MAX_VALUE)
        cnt <= {WIDTH{1'b0}};
    else if (en)
        cnt <= cnt + 1'b1;
end
```

### 模板3：状态机

```verilog
// 第一段
always @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        current_state <= S_IDLE;
    else
        current_state <= next_state;
end

// 第二段
always @(*) begin
    next_state = current_state;
    case (current_state)
        S_IDLE: if (start) next_state = S_RUN;
        S_RUN:  if (done)  next_state = S_IDLE;
        default: next_state = S_IDLE;
    endcase
end

// 第三段
always @(*) begin
    output_signal = DEFAULT;
    case (current_state)
        S_RUN: output_signal = VALUE;
    endcase
end
```

### 模板4：跨时钟域同步器

```verilog
// 单bit同步器
reg [1:0] sync_reg;
always @(posedge clk_dst) begin
    sync_reg <= {sync_reg[0], signal_src};
end
assign signal_dst = sync_reg[1];

// 脉冲同步器
reg pulse_toggle;
always @(posedge clk_src) begin
    if (pulse_in)
        pulse_toggle <= ~pulse_toggle;
end

reg [2:0] sync_toggle;
always @(posedge clk_dst) begin
    sync_toggle <= {sync_toggle[1:0], pulse_toggle};
end
assign pulse_out = sync_toggle[2] ^ sync_toggle[1];
```

### 模板5：参数化FIFO

```verilog
module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter FIFO_DEPTH = 16,
    parameter ADDR_WIDTH = $clog2(FIFO_DEPTH)
)(
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    wr_en,
    input  wire [DATA_WIDTH-1:0]   wr_data,
    input  wire                    rd_en,
    output wire [DATA_WIDTH-1:0]   rd_data,
    output wire                    full,
    output wire                    empty,
    output wire [ADDR_WIDTH:0]     data_count
);
    reg [DATA_WIDTH-1:0] mem [0:FIFO_DEPTH-1];
    reg [ADDR_WIDTH:0] wr_ptr, rd_ptr;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= {ADDR_WIDTH+1{1'b0}};
            rd_ptr <= {ADDR_WIDTH+1{1'b0}};
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr[ADDR_WIDTH-1:0]] <= wr_data;
                wr_ptr <= wr_ptr + 1;
            end
            if (rd_en && !empty) begin
                rd_ptr <= rd_ptr + 1;
            end
        end
    end

    assign rd_data = mem[rd_ptr[ADDR_WIDTH-1:0]];
    assign full = (wr_ptr[ADDR_WIDTH] != rd_ptr[ADDR_WIDTH]) &&
                  (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]);
    assign empty = (wr_ptr == rd_ptr);
    assign data_count = wr_ptr - rd_ptr;
endmodule
```

---

> **总结**：FPGA开发是一项综合性技能，需要掌握硬件描述语言、数字电路原理、时序分析、系统架构等多方面知识。通过不断实践和项目积累，可以逐步提升FPGA开发能力。

---

*最后更新：2026-06-21*
*作者：AI助手*
*标签：#FPGA #嵌入式 #数字电路 #Verilog #硬件设计*