# PCB进阶设计

## 核心概念

- **阻抗控制** - 传输线设计
- **高速信号** - 信号完整性
- **RF设计** - 射频电路
- **电源完整性** - PDN设计

---

## 一、高速信号设计

### 1.1 传输线基础

```c
// 传输线参数
/*
 * 特性阻抗 Z₀:
 *   微带线(Microstrip): Z₀ ≈ (87/√(εr+1.41)) × ln(5.98h/(0.8w+t))
 *   带状线(Stripline): Z₀ ≈ (60/√εr) × ln(4h/(0.67π(0.8w+t)))
 *
 * 传播延迟:
 *   微带线: td ≈ 85√(0.475εr + 0.67) ps/inch
 *   带状线: td ≈ 85√εr ps/inch
 *
 * FR4参数:
 *   εr ≈ 4.4
 *   传播速度 ≈ 6 inch/ns (微带线)
 *   传播延迟 ≈ 170 ps/inch
 */

// 临界长度计算
/*
 * 当 trace_length > tr / (2 × td_per_inch) 时需要端接
 *
 * 例: tr = 1ns, td = 170ps/inch
 * 临界长度 = 1000ps / (2 × 170ps/inch) ≈ 2.9 inch ≈ 7.4cm
 */
```

---

### 1.2 阻抗计算

```c
// 微带线阻抗计算器
typedef struct {
    float width;      // 线宽(mil)
    float height;     // 介质厚度(mil)
    float thickness;  // 铜厚(mil)
    float er;         // 介电常数
    float zo;         // 特性阻抗(Ω)
} microstrip_params_t;

float calc_microstrip_z0(float w, float h, float t, float er) {
    // 有效介电常数
    float er_eff = (er + 1) / 2 + (er - 1) / 2 *
                   (1 / sqrt(1 + 12 * h / w));

    // 宽高比
    float ratio = w / h;

    // 阻抗计算
    float z0;
    if (ratio <= 1) {
        z0 = (60 / sqrt(er_eff)) * log(8 * h / w + w / (4 * h));
    } else {
        z0 = (120 * M_PI) / (sqrt(er_eff) * (ratio + 1.393 + 0.667 * log(ratio + 1.444)));
    }

    return z0;
}

// 差分阻抗
float calc_diff_z0(float z0_single, float s, float h) {
    float coupling = 1 - 0.347 * exp(-2.9 * s / h);
    return 2 * z0_single * (1 - coupling);
}
```

---

### 1.3 等长匹配

```c
// 蛇形走线间距计算
/*
 * 蛇形走线(用于等长匹配):
 *
 *   ┌─┐ ┌─┐ ┌─┐
 *   │ │ │ │ │ │
 *   │ └─┘ └─┘ │
 *   │         │
 *   └─────────┘
 *
 * 参数:
 *   W: 线宽
 *   S: 间距(≥3W)
 *   H: 介质厚度
 *
 * 注意:
 *   - 间距S应≥3W减少串扰
 *   - 弯角处做圆弧或45°处理
 *   - 蛇形走线不宜太密
 */

// 等长匹配规则
/*
 * DDR数据线: ±5mil
 * USB差分: ±5mil
 * 以太网差分: ±10mil
 * LVDS差分: ±5mil
 */
```

---

## 二、串扰分析

### 2.1 串扰机理

```c
// 串扰类型
/*
 * 1. 容性耦合(电场):
 *    Cm × dV/dt → 感应电流
 *    近端串扰(NEXT): 与信号同向
 *    远端串扰(FEXT): 与信号反向
 *
 * 2. 感性耦合(磁场):
 *    Lm × dI/dt → 感应电压
 *    近端串扰: 与信号反向
 *    远端串扰: 与信号同向
 */

// 3W规则
/*
 * 信号间距 ≥ 3 × 线宽 → 串扰降低70%
 * 信号间距 ≥ 5 × 线宽 → 串扰降低90%
 *
 * 例: 线宽5mil, 3W间距 = 15mil(线中心到线中心)
 */

// 串扰估算(微带线)
float estimate_crosstalk(float length_inch, float s, float h) {
    // 简化模型
    float coupling = exp(-2.9 * s / h);
    return coupling * length_inch * 0.1;  // 近似值
}
```

---

### 2.2 串扰抑制

```c
// 串扰抑制措施
/*
 * 1. 增加间距(3W/5W规则)
 * 2. 使用地平面参考
 * 3. 关键信号两侧加保护地线
 * 4. 减少平行长度
 * 5. 不同层走线正交
 * 6. 使用带状线(比微带线串扰小)
 */

// 保护走线
/*
 *   信号A ───────
 *   GND  ───────  保护线
 *   信号B ───────
 *
 * 保护线需多点接地(每隔λ/10打过孔)
 */
```

---

## 三、电源完整性

### 3.1 PDN设计

```c
// 电源分配网络(PDN)
/*
 * 目标阻抗:
 *   Ztarget = Vripple / Itransient
 *
 * 例: 3.3V, 允许5%纹波, 最大瞬态电流1A
 *   Ztarget = (3.3 × 0.05) / 1 = 0.165Ω
 */

// 去耦电容选择
/*
 * 频率范围          电容类型        容值
 * 低频(<100kHz)    电解电容        100-1000μF
 * 中频(100k-10MHz) 钽电容          1-10μF
 * 高频(10M-100MHz) 陶瓷电容(0402)  100nF
 * 超高频(>100MHz)  嵌入式电容      10nF
 */

// 电容并联阻抗
/*
 * Z_total = Z1 × Z2 / (Z1 + Z2)
 *
 * 并联不同容值可扩展去耦频率范围
 * 注意反谐振峰: 在两个电容谐振频率之间
 */
```

---

### 3.2 电源平面设计

```c
// 电源平面规则
/*
 * 1. 电源平面和地平面紧耦合(间距小)
 * 2. 避免电源平面开槽(切断回流路径)
 * 3. 不同电源域分区重叠
 * 4. 高速信号参考完整地平面
 *
 * 层叠示例(6层板):
 *   L1: Signal(Top)
 *   L2: GND(地平面)
 *   L3: Signal(内层)
 *   L4: Power(电源平面)
 *   L5: GND(地平面)
 *   L6: Signal(Bottom)
 */
```

---

## 四、RF设计

### 4.1 RF布局规则

```c
// RF布局原则
/*
 * 1. RF走线尽量短且直
 * 2. 50Ω阻抗控制
 * 3. RF区域与其他区域隔离
 * 4. RF走线避免跨分割
 * 5. 元件就近放置
 * 6. 匹配网络靠近芯片
 */

// RF层叠
/*
 * 推荐4层板:
 *   L1: RF信号 + 元件
 *   L2: GND(完整地平面)
 *   L3: 电源 + 低速信号
 *   L4: 低速信号
 */
```

---

### 4.2 天线匹配

```c
// 天线匹配网络
/*
 * π型匹配网络:
 *
 *  ──┤L├──┬── Antenna
 *   │     │
 *   C1    C2
 *   │     │
 *  GND   GND
 *
 * 匹配目标: 50Ω纯阻
 * 使用Smith圆图设计
 */

// 匹配元件值计算
/*
 * 工作频率: 2.4GHz
 * 天线阻抗: Ra + jXa
 *
 * 步骤:
 * 1. 测量天线阻抗(网络分析仪)
 * 2. 在Smith圆图上标出
 * 3. 设计匹配网络将阻抗变换到50Ω
 * 4. 验证带宽和回波损耗
 */
```

---

### 4.3 微带线滤波器

```c
// 低通滤波器(微带线实现)
/*
 * 阶梯阻抗低通滤波器:
 *
 *   50Ω ─┬─ 20Ω ─┬─ 80Ω ─┬─ 20Ω ─┬─ 50Ω
 *        │        │        │        │
 *        W1       W2       W1       W2
 *
 * 高阻抗线(窄): 等效串联电感
 * 低阻抗线(宽): 等效并联电容
 */
```

---

## 五、信号完整性仿真

### 5.1 眼图分析

```c
// 眼图参数
/*
 * 眼图: 示波器上重叠显示多个位周期
 *
 * 关键参数:
 *   眼高(Eye Height): 噪声容限
 *   眼宽(Eye Width): 时序容限
 *   抖动(Jitter): 时序不确定性
 *
 * 余量要求:
 *   眼高 > 信号幅度的20%
 *   眼宽 > 位周期的20%
 */

// 眼图余量计算
float calc_eye_margin(float eye_height, float signal_amplitude,
                      float eye_width, float bit_period) {
    float height_margin = eye_height / signal_amplitude * 100;
    float width_margin = eye_width / bit_period * 100;
    return fminf(height_margin, width_margin);
}
```

---

### 5.2 时序分析

```c
// 建立时间和保持时间
/*
 * 建立时间裕量:
 *   Tsetup_margin = Tclock - Tdata_delay - Tsetup
 *
 * 保持时间裕量:
 *   Thold_margin = Tdata_delay - Thold
 *
 * 时序约束:
 *   Tdata_delay(min) > Thold
 *   Tdata_delay(max) < Tclock - Tsetup
 */

// 传播延迟计算
float calc_propagation_delay(float length_inch, float velocity_factor) {
    // FR4: velocity_factor ≈ 0.5-0.6
    float speed = 11.8 * velocity_factor;  // inch/ns
    return length_inch / speed;  // ns
}
```

---

## 六、DFM设计

### 6.1 制造规则

```c
// 最小设计规则(标准工艺)
/*
 * 参数              常规      精密      HDI
 * 最小线宽         6mil      4mil      3mil
 * 最小间距         6mil      4mil      3mil
 * 最小过孔         0.3mm     0.2mm     0.1mm
 * 最小BGA间距      0.8mm     0.65mm    0.4mm
 * 铜厚(外层)      1oz       1oz       0.5oz
 * 铜厚(内层)      0.5oz     0.5oz     0.33oz
 */

// 焊盘设计
/*
 * BGA焊盘: 直径 = 球径 × 0.8
 * QFP焊盘: 长 = 引脚长 + 0.5mm
 * 过孔焊盘: 直径 = 孔径 + 0.5mm(单边0.25mm)
 */
```

---

### 6.2 可制造性检查

```c
// DFM检查清单
/*
 * □ 线宽/间距满足工艺要求
 * □ 过孔尺寸满足钻孔能力
 * □ 焊盘与阻焊开窗匹配
 * □ 丝印不覆盖焊盘
 * □ 板边间距足够(≥5mm)
 * □ 拼板方式合理
 * □ 基准点(Mark点)添加
 * □ 测试点预留
 */
```

---

## 七、热设计

### 7.1 散热计算

```c
// 热阻计算
/*
 * Tj = Ta + P × (θjc + θcs + θsa)
 *
 * Tj: 结温
 * Ta: 环境温度
 * P: 功耗(W)
 * θjc: 芯片到外壳热阻
 * θcs: 外壳到散热器热阻
 * θsa: 散热器到环境热阻
 */

// 散热面积估算
float calc_heatsink_area(float power_w, float max_temp_rise) {
    // 简化公式: A = P / (h × ΔT)
    // h: 对流换热系数(自然对流 ≈ 10 W/m²K)
    float h = 10.0f;
    return power_w / (h * max_temp_rise);
}
```

---

### 7.2 PCB散热

```c
// 散热过阵
/*
 * 在发热元件下方放置过阵:
 *   ┌─────────────────┐
 *   │  ○ ○ ○ ○ ○ ○  │
 *   │  ○ ○ ○ ○ ○ ○  │
 *   │  ○ ○ ○ ○ ○ ○  │
 *   │  ○ ○ ○ ○ ○ ○  │
 *   └─────────────────┘
 *
 * 过孔直径: 0.3mm
 * 间距: 1mm
 * 填充: 导热材料或电镀填孔
 */

// 铜皮散热
/*
 * 大面积铜皮连接发热元件
 * 内层铜皮作为热扩散层
 * 多层板可利用多层铜皮散热
 */
```

---

## 附录：PCB设计工具

| 工具 | 用途 | 特点 |
|------|------|------|
| Altium Designer | 全流程 | 功能强大 |
| KiCad | 开源 | 免费 |
| Allegro | 高速设计 | 企业级 |
| PADS | 中端 | 易用 |
| OrCAD | 原理图 | 经典 |

---

## 相关链接

- [[PCB设计基础]] - PCB基础
- [[EMC设计详解]] - EMC设计
- [[电路基础]] - 电路理论
