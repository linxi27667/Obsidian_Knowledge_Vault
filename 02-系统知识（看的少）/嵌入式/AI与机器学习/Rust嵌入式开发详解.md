# Rust 嵌入式开发详解

## 1. Rust 嵌入式概述

### 1.1 为什么用 Rust 做嵌入式

Rust 在嵌入式领域的崛起并非偶然，它解决了传统 C/C++ 嵌入式开发中长期存在的痛点：

**内存安全（Memory Safety）**
- Rust 的所有权系统在编译期消除空指针解引用、悬垂指针、数据竞争等内存错误
- 嵌入式系统中，内存错误往往导致难以调试的硬件级故障，Rust 从源头杜绝此类问题
- 无需垃圾回收器（GC），不引入运行时开销

**零成本抽象（Zero-Cost Abstractions）**
- 泛型、trait、迭代器等高级抽象在编译后与手写底层代码性能一致
- 编译器深度优化，抽象层不产生额外的运行时开销
- 允许开发者编写高层级、可读性强的代码，同时保持裸金属性能

**无 GC（No Garbage Collector）**
- 嵌入式系统通常没有足够的资源运行 GC
- Rust 通过所有权和生命周期机制在编译期管理内存，运行时无额外开销
- 内存分配和释放时机完全可预测

**现代工具链**
- Cargo 包管理器统一管理依赖、构建、测试
- rustup 工具链管理器支持多目标交叉编译
- 内置测试框架，支持在主机上运行单元测试

### 1.2 Rust vs C 嵌入式对比

| 特性 | Rust | C |
|------|------|---|
| 内存安全 | 编译期保证 | 手动管理，易出错 |
| 抽象能力 | trait/泛型/宏，零成本 | 宏/函数指针，有限 |
| 并发安全 | 类型系统保证 | 依赖开发者纪律 |
| 包管理 | Cargo 生态成熟 | 手动管理或 CMake |
| 编译速度 | 较慢（增量编译改善中） | 快 |
| 生态成熟度 | 快速增长中 | 非常成熟 |
| 学习曲线 | 陡峭（所有权概念） | 相对平缓 |
| 现有代码库 | 新建项目为主 | 海量存量代码 |
| 调试工具 | probe-rs/defmt | J-Link/OpenOCD + GDB |
| 代码体积 | 与 C 相当 | 基准 |

### 1.3 典型应用场景

- **物联网设备**：低功耗传感器节点、网关
- **可穿戴设备**：手环、智能手表
- **工业控制**：PLC、电机驱动
- **汽车电子**：ECU、车载传感器
- **航空航天**：飞控、卫星载荷

---

## 2. Rust 基础回顾

### 2.1 所有权（Ownership）

所有权是 Rust 最核心的概念，每个值都有唯一的所有者：

```rust
fn main() {
    let s1 = String::from("hello"); // s1 拥有这个字符串
    let s2 = s1;                     // 所有权转移到 s2
    // println!("{}", s1);           // 编译错误：s1 已失效
    println!("{}", s2);              // 正常
}
```

**所有权规则：**
1. 每个值有且仅有一个所有者
2. 同一时刻只能有一个所有者
3. 所有者离开作用域时，值被自动释放

### 2.2 借用（Borrowing）

借用允许在不转移所有权的情况下使用值：

```rust
fn calculate_length(s: &String) -> usize {
    s.len() // 不可变借用
}

fn append_world(s: &mut String) {
    s.push_str(" world"); // 可变借用
}

fn main() {
    let mut s = String::from("hello");
    let len = calculate_length(&s);     // 不可变借用
    append_world(&mut s);               // 可变借用
    println!("{}: {}", s, len);
}
```

**借用规则：**
- 同一时刻可以有多个不可变借用（`&T`）或一个可变借用（`&mut T`），但不能同时存在
- 借用必须始终有效（不能悬垂引用）

### 2.3 生命周期（Lifetimes）

生命周期标注确保引用的有效性：

```rust
// 显式生命周期标注
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

// 结构体中的生命周期
struct SensorReading<'a> {
    name: &'a str,
    value: f32,
}

impl<'a> SensorReading<'a> {
    fn new(name: &'a str, value: f32) -> Self {
        SensorReading { name, value }
    }

    fn display(&self) {
        println!("{}: {:.2}", self.name, self.value);
    }
}
```

### 2.4 模式匹配（Pattern Matching）

模式匹配在嵌入式中常用于解析寄存器值和状态机：

```rust
enum DeviceState {
    Idle,
    Running { speed: u32 },
    Error { code: u16 },
    Shutdown,
}

fn handle_state(state: DeviceState) {
    match state {
        DeviceState::Idle => println!("设备空闲"),
        DeviceState::Running { speed } if speed > 1000 => {
            println!("高速运行: {} RPM", speed);
        }
        DeviceState::Running { speed } => {
            println!("正常运行: {} RPM", speed);
        }
        DeviceState::Error { code } => {
            println!("错误代码: 0x{:04X}", code);
        }
        DeviceState::Shutdown => println!("设备关闭"),
    }
}

// if let 简化单分支匹配
fn read_register_value(val: Option<u32>) {
    if let Some(reg_val) = val {
        println!("寄存器值: 0x{:08X}", reg_val);
    }
}
```

### 2.5 Trait 系统

Trait 定义共享行为，是嵌入式 HAL 抽象的基础：

```rust
// 定义 trait
trait Sensor {
    type Error;
    fn read(&mut self) -> Result<f32, Self::Error>;
    fn name(&self) -> &str;
}

// 实现 trait
struct TemperatureSensor {
    pin: u8,
}

impl Sensor for TemperatureSensor {
    type Error = &'static str;

    fn read(&mut self) -> Result<f32, Self::Error> {
        Ok(25.0) // 简化示例
    }

    fn name(&self) -> &str {
        "温度传感器"
    }
}

// trait 作为参数
fn print_reading<S: Sensor>(sensor: &mut S) {
    match sensor.read() {
        Ok(val) println!("{}: {:.1}°C", sensor.name(), val),
        Err(e) => println!("读取失败: {}", e),
    }
}
```

### 2.6 错误处理（Result / Option）

嵌入式开发中错误处理至关重要：

```rust
use core::fmt;

// 自定义错误类型
#[derive(Debug)]
enum SpiError {
    BusBusy,
    ChipSelectFailed,
    TransferTimeout,
    InvalidData,
}

impl fmt::Display for SpiError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SpiError::BusBusy => write!(f, "SPI 总线忙"),
            SpiError::ChipSelectFailed => write!(f, "片选失败"),
            SpiError::TransferTimeout => write!(f, "传输超时"),
            SpiError::InvalidData => write!(f, "数据无效"),
        }
    }
}

// 使用 Result 传播错误
fn spi_transfer(data: &[u8]) -> Result<Vec<u8>, SpiError> {
    if data.is_empty() {
        return Err(SpiError::InvalidData);
    }
    // ... 执行传输
    Ok(vec![0x00; data.len()])
}

// ? 操作符简化错误传播
fn read_sensor_register(reg: u8) -> Result<u8, SpiError> {
    let cmd = [reg, 0x00];
    let response = spi_transfer(&cmd)?;
    Ok(response[1])
}

// Option 处理可能不存在的值
fn find_sensor_by_id(id: u8) -> Option<&'static str> {
    match id {
        0x01 => Some("BME280"),
        0x02 => Some("MPU6050"),
        0x03 => Some("SSD1306"),
        _ => None,
    }
}
```

---

## 3. 嵌入式 Rust 生态

### 3.1 no_std 环境

嵌入式 Rust 运行在 `no_std` 环境中，不依赖标准库（std）：

```rust
// 禁用标准库，使用核心库
#![no_std]
// 禁用标准入口点
#![no_main]

use core::panic::PanicInfo;

// 必须定义 panic 处理函数
#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        // 硬件复位或 LED 闪烁指示错误
    }
}

// 入口点
#[entry]
fn main() -> ! {
    loop {
        // 主循环
    }
}
```

**no_std 可用的核心库：**
- `core`：语言核心库，始终可用（Option、Result、Iterator 等）
- `alloc`：堆分配库，需要提供全局分配器
- `alloc-cortex-m`：Cortex-M 平台的堆分配器实现

### 3.2 embedded-hal 抽象层

`embedded-hal` 定义了硬件抽象的统一接口，实现跨平台可移植性：

```rust
use embedded_hal::digital::{InputPin, OutputPin};
use embedded_hal::i2c::I2c;
use embedded_hal::spi::SpiDevice;
use embedded_hal::serial::{Read, Write};

// 基于 trait 的设备驱动（平台无关）
struct Bme280Driver<I2C> {
    i2c: I2C,
    address: u8,
}

impl<I2C: I2c> Bme280Driver<I2C> {
    fn new(i2c: I2C, address: u8) -> Self {
        Self { i2c, address }
    }

    fn read_temperature(&mut self) -> Result<f32, I2C::Error> {
        let mut buf = [0u8; 3];
        self.i2c.write_read(self.address, &[0xFA], &mut buf)?;
        let raw = ((buf[0] as u32) << 12) | ((buf[1] as u32) << 4) | ((buf[2] as u32) >> 4);
        Ok(raw as f32 / 100.0)
    }

    fn read_pressure(&mut self) -> Result<f32, I2C::Error> {
        let mut buf = [0u8; 3];
        self.i2c.write_read(self.address, &[0xF7], &mut buf)?;
        let raw = ((buf[0] as u32) << 12) | ((buf[1] as u32) << 4) | ((buf[2] as u32) >> 4);
        Ok(raw as f32 / 256.0)
    }
}
```

**embedded-hal 版本演进：**
- `embedded-hal 0.2`：基于 `&mut self` 的阻塞式 trait
- `embedded-hal 1.0`：稳定版，基于所有权转移的设计
- `embedded-hal-async`：异步版本的 trait
- `embedded-hal-nb`：非阻塞（non-blocking）版本

### 3.3 probe-rs 调试

probe-rs 是 Rust 原生的嵌入式调试工具：

```bash
# 安装 probe-rs
cargo install probe-rs-tools

# 查看连接的调试探针
probe-rs list

# 烧录固件
probe-rs run --chip STM32F411CEUx target/thumbv7em-none-eabihf/release/my_firmware

# 实时查看 RTT 日志
probe-rs attach --chip STM32F411CEUx

# GDB 调试
probe-rs debug --chip STM32F411CEUx

# 擦除芯片
probe-rs erase --chip STM32F411CEUx
```

**probe-rs 配置文件（`Embed.toml`）：**
```toml
[default.probe]
protocol = "Swd"
speed = 20000

[default.flashing]
enabled = true
restore_unwritten_bytes = false

[default.general]
chip = "STM32F411CEUx"
log_level = "WARN"

[default.rtt]
enabled = true
channels = []
timeout = 3000
show_timestamps = true
```

### 3.4 defmt 日志框架

defmt（deferred formatting）是专为嵌入式设计的高效日志框架：

```rust
use defmt::{info, warn, error, debug, trace, println};

fn init_system() {
    info!("系统初始化开始");
    debug!("时钟频率: {} MHz", 72);

    if !check_power() {
        error!("电源检测失败");
        return;
    }

    info!("系统初始化完成");
}

fn read_sensor(id: u8, value: f32) {
    // defmt 格式化在主机端完成，不消耗目标设备资源
    trace!("传感器 {}: {:.2}°C", id, value);

    if value > 80.0 {
        warn!("传感器 {} 温度过高: {:.1}°C", id, value);
    }
}
```

**Cargo.toml 配置：**
```toml
[dependencies]
defmt = "0.3"
defmt-rtt = "0.4"
panic-probe = { version = "0.3", features = ["print-defmt"] }
```

---

## 4. GPIO 操作

### 4.1 InputPin / OutputPin trait

```rust
use embedded_hal::digital::{InputPin, OutputPin, StatefulOutputPin};

// LED 控制器
struct Led<PIN: OutputPin> {
    pin: PIN,
}

impl<PIN: OutputPin> Led<PIN> {
    fn new(pin: PIN) -> Self {
        let mut led = Self { pin };
        led.off();
        led
    }

    fn on(&mut self) {
        let _ = self.pin.set_high();
    }

    fn off(&mut self) {
        let _ = self.pin.set_low();
    }

    fn toggle(&mut self)
    where
        PIN: StatefulOutputPin,
    {
        let _ = self.pin.toggle();
    }
}

// 按钮读取器
struct Button<PIN: InputPin> {
    pin: PIN,
    debounce_ms: u32,
}

impl<PIN: InputPin> Button<PIN> {
    fn new(pin: PIN, debounce_ms: u32) -> Self {
        Self { pin, debounce_ms }
    }

    fn is_pressed(&self) -> bool {
        self.pin.is_low().unwrap_or(false)
    }

    fn is_released(&self) -> bool {
        self.pin.is_high().unwrap_or(false)
    }
}
```

### 4.2 中断配置

```rust
use cortex_m::peripheral::NVIC;
use stm32f4xx_hal::gpio::{Edge, Input, PullUp, PA0};

fn configure_button_interrupt(
    button_pin: PA0<Input<PullUp>>,
    exti: &mut stm32f4xx_hal::syscfg::SYSCFG,
    nvic: &mut NVIC,
) {
    // 配置外部中断
    button_pin.make_interrupt_source(exti);
    button_pin.trigger_on_edge(Edge::Falling);
    button_pin.enable_interrupt();

    // 在 NVIC 中使能中断
    unsafe {
        NVIC::unmask(stm32f4xx_hal::pac::Interrupt::EXTI0);
    }
}

// 中断处理函数
#[interrupt]
fn EXTI0() {
    // 清除中断标志
    unsafe {
        (*stm32f4xx_hal::pac::EXTI::ptr())
            .pr
            .modify(|_, w| w.pr0().set_bit());
    }

    // 设置事件标志（在主循环中处理）
    cortex_m::interrupt::free(|cs| {
        if let Some(flag) = BUTTON_PRESSED.borrow(cs).borrow_mut().as_mut() {
            **flag = true;
        }
    });
}
```

### 4.3 消抖（Debounce）

```rust
use embedded_hal::digital::InputPin;

struct Debouncer<PIN: InputPin> {
    pin: PIN,
    state: bool,
    counter: u8,
    threshold: u8,
}

impl<PIN: InputPin> Debouncer<PIN> {
    fn new(pin: PIN, threshold: u8) -> Self {
        Self {
            pin,
            state: false,
            counter: 0,
            threshold,
        }
    }

    /// 每次调用更新一次，返回状态是否变化
    fn update(&mut self) -> Option<bool> {
        let raw = self.pin.is_low().unwrap_or(false);

        if raw == self.state {
            self.counter = 0;
            return None;
        }

        self.counter += 1;
        if self.counter >= self.threshold {
            self.counter = 0;
            self.state = raw;
            return Some(self.state);
        }

        None
    }

    fn is_active(&self) -> bool {
        self.state
    }
}

// 使用示例
fn process_buttons<P1: InputPin, P2: InputPin>(
    btn1: &mut Debouncer<P1>,
    btn2: &mut Debouncer<P2>,
) {
    if let Some(pressed) = btn1.update() {
        if pressed {
            defmt::info!("按钮 1 按下");
        }
    }

    if let Some(pressed) = btn2.update() {
        if pressed {
            defmt::info!("按钮 2 按下");
        }
    }
}
```

---

## 5. 通信接口

### 5.1 I2C 通信

```rust
use embedded_hal::i2c::I2c;

// I2C 设备扫描
fn scan_i2c_bus<I2C: I2c>(i2c: &mut I2C) {
    defmt::info!("I2C 总线扫描开始");
    for addr in 0x08..=0x77 {
        if i2c.write(addr, &[]).is_ok() {
            defmt::info!("发现设备: 0x{:02X}", addr);
        }
    }
}

// I2C 设备驱动示例 - AHT20 温湿度传感器
struct Aht20<I2C> {
    i2c: I2C,
    address: u8,
}

impl<I2C: I2c> Aht20<I2C> {
    const ADDR: u8 = 0x38;

    fn new(i2c: I2C) -> Self {
        Self {
            i2c,
            address: Self::ADDR,
        }
    }

    fn init(&mut self) -> Result<(), I2C::Error> {
        // 等待上电稳定
        cortex_m::asm::delay(400_000);

        // 发送初始化命令
        self.i2c.write(self.address, &[0xBE, 0x08, 0x00])?;
        cortex_m::asm::delay(100_000);

        Ok(())
    }

    fn read(&mut self) -> Result<(f32, f32), I2C::Error> {
        // 触发测量
        self.i2c.write(self.address, &[0xAC, 0x33, 0x00])?;

        // 等待测量完成
        cortex_m::asm::delay(800_000);

        // 读取数据
        let mut buf = [0u8; 6];
        self.i2c.read(self.address, &mut buf)?;

        // 解析湿度
        let hum_raw = ((buf[1] as u32) << 12)
            | ((buf[2] as u32) << 4)
            | ((buf[3] as u32) >> 4);
        let humidity = (hum_raw as f32) / 1048576.0 * 100.0;

        // 解析温度
        let temp_raw = (((buf[3] & 0x0F) as u32) << 16)
            | ((buf[4] as u32) << 8)
            | (buf[5] as u32);
        let temperature = (temp_raw as f32) / 1048576.0 * 200.0 - 50.0;

        Ok((temperature, humidity))
    }
}
```

### 5.2 SPI 通信

```rust
use embedded_hal::spi::SpiDevice;

// SPI 设备驱动 - W25Q Flash
struct W25q<SPI> {
    spi: SPI,
}

impl<SPI: SpiDevice> W25q<SPI> {
    fn new(spi: SPI) -> Self {
        Self { spi }
    }

    fn read_jedec_id(&mut self) -> Result<[u8; 3], SPI::Error> {
        let mut buf = [0u8; 4];
        self.spi.transfer_in_place(&mut [0x9F, 0, 0, 0])?;
        Ok([buf[1], buf[2], buf[3]])
    }

    fn read_data(&mut self, addr: u32, data: &mut [u8]) -> Result<(), SPI::Error> {
        let cmd = [
            0x03,
            (addr >> 16) as u8,
            (addr >> 8) as u8,
            addr as u8,
        ];
        self.spi.transfer_in_place(&mut [])?;
        // 实际实现中需要先发送命令再读取数据
        Ok(())
    }

    fn write_enable(&mut self) -> Result<(), SPI::Error> {
        self.spi.write(&[0x06])
    }

    fn erase_sector(&mut self, addr: u32) -> Result<(), SPI::Error> {
        self.write_enable()?;
        let cmd = [
            0x20,
            (addr >> 16) as u8,
            (addr >> 8) as u8,
            addr as u8,
        ];
        self.spi.write(&cmd)
    }

    fn busy(&mut self) -> Result<bool, SPI::Error> {
        let mut buf = [0x05, 0x00];
        self.spi.transfer_in_place(&mut buf)?;
        Ok(buf[1] & 0x01 != 0)
    }
}
```

### 5.3 UART 通信

```rust
use embedded_hal_nb::serial::{Read, Write};

// UART 数据帧协议
struct UartFramed<UART> {
    uart: UART,
    rx_buf: [u8; 256],
    rx_pos: usize,
}

#[derive(Debug)]
enum FrameError {
    BufferOverflow,
    CrcError,
    IoError,
}

impl<UART: Read<u8> + Write<u8>> UartFramed<UART> {
    fn new(uart: UART) -> Self {
        Self {
            uart,
            rx_buf: [0u8; 256],
            rx_pos: 0,
        }
    }

    fn poll_rx(&mut self) -> Result<Option<&[u8]>, FrameError> {
        loop {
            match self.uart.read() {
                Ok(byte) => {
                    if self.rx_pos >= self.rx_buf.len() {
                        self.rx_pos = 0;
                        return Err(FrameError::BufferOverflow);
                    }

                    self.rx_buf[self.rx_pos] = byte;
                    self.rx_pos += 1;

                    // 检测帧结束（简单换行符检测）
                    if byte == b'\n' {
                        let frame = &self.rx_buf[..self.rx_pos];
                        self.rx_pos = 0;
                        return Ok(Some(frame));
                    }
                }
                Err(nb::Error::WouldBlock) => {
                    return Ok(None);
                }
                Err(nb::Error::Other(_)) => {
                    return Err(FrameError::IoError);
                }
            }
        }
    }

    fn send(&mut self, data: &[u8]) -> Result<(), FrameError> {
        for &byte in data {
            loop {
                match self.uart.write(byte) {
                    Ok(_) => break,
                    Err(nb::Error::WouldBlock) => continue,
                    Err(_) => return Err(FrameError::IoError),
                }
            }
        }
        Ok(())
    }
}
```

### 5.4 设备驱动模式

```rust
// 驱动模式：使用 trait 实现可替换的传输层

trait Transfer {
    type Error;
    fn write(&mut self, addr: u8, data: &[u8]) -> Result<(), Self::Error>;
    fn read(&mut self, addr: u8, buf: &mut [u8]) -> Result<(), Self::Error>;
    fn write_read(&mut self, addr: u8, wr: &[u8], rd: &mut [u8]) -> Result<(), Self::Error>;
}

// I2C 适配器
struct I2cAdapter<I2C: embedded_hal::i2c::I2c> {
    bus: I2C,
}

impl<I2C: embedded_hal::i2c::I2c> Transfer for I2cAdapter<I2C> {
    type Error = I2C::Error;

    fn write(&mut self, addr: u8, data: &[u8]) -> Result<(), Self::Error> {
        self.bus.write(addr, data)
    }

    fn read(&mut self, addr: u8, buf: &mut [u8]) -> Result<(), Self::Error> {
        self.bus.read(addr, buf)
    }

    fn write_read(&mut self, addr: u8, wr: &[u8], rd: &mut [u8]) -> Result<(), Self::Error> {
        self.bus.write_read(addr, wr, rd)
    }
}

// 通用传感器驱动
struct SensorDriver<T: Transfer> {
    transport: T,
    address: u8,
}

impl<T: Transfer> SensorDriver<T> {
    fn new(transport: T, address: u8) -> Self {
        Self { transport, address }
    }

    fn read_register(&mut self, reg: u8) -> Result<u8, T::Error> {
        let mut buf = [0u8; 1];
        self.transport.write_read(self.address, &[reg], &mut buf)?;
        Ok(buf[0])
    }

    fn write_register(&mut self, reg: u8, value: u8) -> Result<(), T::Error> {
        self.transport.write(self.address, &[reg, value])
    }
}
```

---

## 6. 中断处理

### 6.1 cortex-m-rt 中断向量

```rust
#![no_std]
#![no_main]

use cortex_m::peripheral::NVIC;
use cortex_m_rt::{entry, exception, interrupt};
use stm32f4xx_hal::pac;

// 全局可变状态（中断安全）
use core::cell::RefCell;
use cortex_m::interrupt::Mutex;

static COUNTER: Mutex<RefCell<u32>> = Mutex::new(RefCell::new(0));
static LED_STATE: Mutex<RefCell<bool>> = Mutex::new(RefCell::new(false));

#[entry]
fn main() -> ! {
    let dp = pac::Peripherals::take().unwrap();

    // 配置 SysTick 定时器
    let mut cp = cortex_m::Peripherals::take().unwrap();
    cp.SYST.set_reload(168_000 - 1); // 1ms @ 168MHz
    cp.SYST.enable_interrupt();
    cp.SYST.enable_counter();

    // 使能 TIM2 中断
    unsafe {
        NVIC::unmask(pac::Interrupt::TIM2);
    }

    loop {
        // 主循环处理非时间关键任务
        cortex_m::asm::wfi(); // 等待中断
    }
}

// SysTick 异常处理
#[exception]
fn SysTick() {
    cortex_m::interrupt::free(|cs| {
        let mut counter = COUNTER.borrow(cs).borrow_mut();
        *counter += 1;
    });
}

// TIM2 中断处理
#[interrupt]
fn TIM2() {
    cortex_m::interrupt::free(|cs| {
        let mut led = LED_STATE.borrow(cs).borrow_mut();
        *led = !*led;
    });

    // 清除中断标志
    unsafe {
        let tim2 = &*pac::TIM2::ptr();
        tim2.sr.modify(|_, w| w.uif().clear_bit());
    }
}

// 硬件错误处理
#[exception]
fn HardFrame(_frame: &cortex_m_rt::ExceptionFrame) -> ! {
    // 记录错误信息
    loop {
        cortex_m::asm::bkpt();
    }
}

#[exception]
fn DefaultHandler(irqn: i16) {
    panic!("未处理的中断: {}", irqn);
}
```

### 6.2 Critical Section

```rust
use cortex_m::interrupt;

// 临界区保护共享数据
fn safe_counter_increment() {
    interrupt::free(|_cs| {
        // 在此区间内，所有中断被禁用
        // 适合保护非常短的临界区
        // 不要在这里做耗时操作
    });
}

// 使用 Mutex 进行中断间通信
static SHARED_DATA: Mutex<RefCell<[u8; 64]>> = Mutex::new(RefCell::new([0; 64]));
static DATA_READY: Mutex<RefCell<bool>> = Mutex::new(RefCell::new(false));

fn write_data(data: &[u8]) {
    interrupt::free(|cs| {
        let mut buf = SHARED_DATA.borrow(cs).borrow_mut();
        let len = data.len().min(64);
        buf[..len].copy_from_slice(&data[..len]);

        let mut ready = DATA_READY.borrow(cs).borrow_mut();
        *ready = true;
    });
}

fn read_data() -> Option<[u8; 64]> {
    interrupt::free(|cs| {
        let mut ready = DATA_READY.borrow(cs).borrow_mut();
        if *ready {
            *ready = false;
            let buf = SHARED_DATA.borrow(cs).borrow();
            Some(*buf)
        } else {
            None
        }
    })
}
```

### 6.3 RTIC 实时中断驱动并发框架

RTIC（Real-Time Interrupt-driven Concurrency）提供编译期保证的并发安全：

```rust
#![no_std]
#![no_main]

use rtic::app;
use stm32f4xx_hal::pac;
use defmt_rtt as _;

#[app(device = stm32f4xx_hal::pac, peripherals = true)]
mod app {
    use super::*;
    use cortex_m::asm;
    use rtic_monotonics::systick::Systick;
    use rtic_monotonics::Monotonic;

    // 共享资源
    #[shared]
    struct Shared {
        temperature: f32,
        humidity: f32,
    }

    // 本地资源
    #[local]
    struct Local {
        led: bool,
        sensor_count: u32,
    }

    // 初始化任务
    #[init]
    fn init(ctx: init::Context) -> (Shared, Local) {
        let dp = ctx.device;

        // 配置时钟
        // ...

        // 启动 SysTick 单调时钟
        Systick::start(ctx.core.SYST, 168_000_000);

        defmt::info!("RTIC 系统初始化完成");

        (
            Shared {
                temperature: 0.0,
                humidity: 0.0,
            },
            Local {
                led: false,
                sensor_count: 0,
            },
        )
    }

    // 传感器读取任务 - 每 1 秒执行一次
    #[task(shared = [temperature, humidity], priority = 1)]
    async fn read_sensor(mut ctx: read_sensor::Context) {
        loop {
            let temp = 25.0; // 实际读取传感器
            let hum = 60.0;

            ctx.shared.temperature.lock(|t| *t = temp);
            ctx.shared.humidity.lock(|h| *h = hum);

            defmt::info!("温度: {:.1}°C, 湿度: {:.1}%", temp, hum);

            Systick::delay(1000.millis()).await;
        }
    }

    // LED 闪烁任务 - 优先级 2
    #[task(local = [led], priority = 2)]
    async fn blink_led(mut ctx: blink_led::Context) {
        loop {
            *ctx.local.led = !*ctx.local.led;
            Systick::delay(500.millis()).await;
        }
    }

    // 外部中断任务 - 最高优先级
    #[task(binds = EXTI0, priority = 3)]
    fn button_press(ctx: button_press::Context) {
        defmt::info!("按钮按下！");
        // 清除中断标志
    }

    // 空闲任务
    #[idle]
    fn idle(_ctx: idle::Context) -> ! {
        loop {
            asm::wfi();
        }
    }
}
```

**RTIC 优势：**
- 编译期死锁检测
- 优先级调度保证
- 静态资源分配，零运行时开销
- 基于 monotonic 的精确延时

---

## 7. 定时器

### 7.1 Timer trait

```rust
use embedded_hal::timer::{CountDown, Periodic};

struct TimerManager<TIMER: CountDown + Periodic> {
    timer: TIMER,
    tick_ms: u32,
}

impl<TIMER: CountDown + Periodic> TimerManager<TIMER> {
    fn new(timer: TIMER, tick_ms: u32) -> Self {
        Self { timer, tick_ms }
    }

    fn start_periodic(&mut self, period_ms: u32) {
        self.timer.start(period_ms.millis());
    }

    fn wait(&mut self) -> nb::Result<(), void::Void> {
        self.timer.wait()
    }
}

// 软件定时器
struct SoftTimer {
    start_tick: u64,
    duration_ms: u64,
}

impl SoftTimer {
    fn new(duration_ms: u64) -> Self {
        Self {
            start_tick: get_tick(),
            duration_ms,
        }
    }

    fn expired(&self) -> bool {
        (get_tick() - self.start_tick) >= self.duration_ms
    }

    fn reset(&mut self) {
        self.start_tick = get_tick();
    }
}

fn get_tick() -> u64 {
    // 从全局 tick 计数器获取
    0 // 占位
}
```

### 7.2 PWM 输出

```rust
use embedded_hal::pwm::SetDutyCycle;

struct PwmLed<PWM: SetDutyCycle> {
    pwm: PWM,
    brightness: u16,
}

impl<PWM: SetDutyCycle> PwmLed<PWM> {
    fn new(mut pwm: PWM) -> Self {
        let _ = pwm.set_duty_cycle(0);
        Self { pwm, brightness: 0 }
    }

    fn set_brightness(&mut self, percent: u8) {
        self.brightness = (percent as u16) * 100;
        let _ = self.pwm.set_duty_cycle_fraction(self.brightness, 10000);
    }

    fn fade_in(&mut self, steps: u32, delay_ms: u32) {
        for i in 0..=steps {
            let duty = (i as u16 * 10000) / steps as u16;
            let _ = self.pwm.set_duty_cycle(duty);
            cortex_m::asm::delay(delay_ms * 168_000);
        }
    }

    fn fade_out(&mut self, steps: u32, delay_ms: u32) {
        for i in (0..=steps).rev() {
            let duty = (i as u16 * 10000) / steps as u16;
            let _ = self.pwm.set_duty_cycle(duty);
            cortex_m::asm::delay(delay_ms * 168_000);
        }
    }

    fn off(&mut self) {
        let _ = self.pwm.set_duty_cycle(0);
    }
}

// 电机 PWM 控制
struct Motor<PWM: SetDutyCycle> {
    pwm: PWM,
    max_duty: u16,
}

impl<PWM: SetDutyCycle> Motor<PWM> {
    fn new(pwm: PWM) -> Self {
        Self { pwm, max_duty: 10000 }
    }

    fn set_speed_percent(&mut self, percent: u8) {
        let duty = (percent.min(100) as u16 * self.max_duty) / 100;
        let _ = self.pwm.set_duty_cycle(duty);
    }

    fn stop(&mut self) {
        let _ = self.pwm.set_duty_cycle(0);
    }
}
```

### 7.3 输入捕获

```rust
use embedded_hal::timer::CountDown;

/// 输入捕获 - 测量脉冲宽度
struct InputCapture<TIMER> {
    timer: TIMER,
    last_capture: u32,
    overflow_count: u32,
}

#[derive(Debug)]
struct PulseMeasurement {
    period_us: u32,
    duty_cycle: f32,
    frequency_hz: f32,
}

impl<TIMER> InputCapture<TIMER> {
    fn new(timer: TIMER, timer_freq_hz: u32) -> Self {
        Self {
            timer,
            last_capture: 0,
            overflow_count: 0,
        }
    }

    fn process_capture(&mut self, capture_value: u32) -> Option<PulseMeasurement> {
        let period_ticks = if capture_value >= self.last_capture {
            capture_value - self.last_capture
        } else {
            (0xFFFF - self.last_capture) + capture_value + 1
        };

        self.last_capture = capture_value;

        // 假设定时器频率为 1MHz (1 tick = 1us)
        let period_us = period_ticks;
        if period_us > 0 {
            Some(PulseMeasurement {
                period_us,
                duty_cycle: 0.0, // 需要额外的上升沿/下降沿测量
                frequency_hz: 1_000_000.0 / period_us as f32,
            })
        } else {
            None
        }
    }
}

// 超声波测距（HC-SR04）
struct UltrasonicSensor<TIMER> {
    capture: InputCapture<TIMER>,
}

impl<TIMER> UltrasonicSensor<TIMER> {
    fn measure_distance_cm(&mut self) -> Option<f32> {
        // 发送 10us 触发脉冲
        // 等待回波捕获
        // distance = (pulse_width_us * 0.0343) / 2.0
        None // 占位
    }
}
```

---

## 8. 异步编程

### 8.1 async/await in no_std

```rust
#![no_std]
#![no_main]

use core::future::Future;
use core::pin::Pin;
use core::task::{Context, Poll};

// 自定义 Future
struct Delay {
    target_tick: u64,
}

impl Future for Delay {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output> {
        if get_current_tick() >= self.target_tick {
            Poll::Ready(())
        } else {
            // 注册唤醒器，让 executor 在下次 tick 时重新 poll
            cx.waker().wake_by_ref();
            Poll::Pending
        }
    }
}

fn delay_ms(ms: u64) -> Delay {
    Delay {
        target_tick: get_current_tick() + ms,
    }
}

// 简单的异步任务
async fn blink() {
    loop {
        set_led(true);
        delay_ms(500).await;
        set_led(false);
        delay_ms(500).await;
    }
}

async fn read_sensor_loop() {
    loop {
        let value = read_adc().await;
        defmt::info!("ADC 值: {}", value);
        delay_ms(1000).await;
    }
}

fn get_current_tick() -> u64 { 0 }
fn set_led(_state: bool) {}
async fn read_adc() -> u16 { 0 }
```

### 8.2 Embassy 异步嵌入式框架

Embassy 是目前最流行的异步嵌入式框架：

```rust
#![no_std]
#![no_main]

use embassy_executor::Spawner;
use embassy_stm32::gpio::{Level, Output, Speed};
use embassy_stm32::i2c::I2c;
use embassy_stm32::time::Hertz;
use embassy_stm32::usart::{BufferedUart, Config as UartConfig};
use embassy_time::{Duration, Timer};
use {defmt_rtt as _, panic_probe as _};

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_stm32::init(Default::default());

    // LED 任务
    let led = Output::new(p.PA5, Level::High, Speed::Low);
    spawner.spawn(blink_led(led)).unwrap();

    // I2C 传感器任务
    let i2c = I2c::new(
        p.I2C1,
        p.PB8,
        p.PB9,
        Hertz(400_000),
        Default::default(),
    );
    spawner.spawn(read_sensors(i2c)).unwrap();

    // UART 通信任务
    let mut tx_buf = [0u8; 256];
    let mut rx_buf = [0u8; 256];
    let uart = BufferedUart::new(
        p.USART1,
        p.PA10,
        p.PA9,
        &mut tx_buf,
        &mut rx_buf,
        UartConfig::default(),
    )
    .unwrap();
    spawner.spawn(uart_handler(uart)).unwrap();

    // 主任务
    loop {
        Timer::after(Duration::from_secs(1)).await;
        defmt::info!("主任务心跳");
    }
}

#[embassy_executor::task]
async fn blink_led(mut led: Output<'static>) {
    loop {
        led.set_high();
        Timer::after(Duration::from_millis(500)).await;
        led.set_low();
        Timer::after(Duration::from_millis(500)).await;
    }
}

#[embassy_executor::task]
async fn read_sensors(mut i2c: I2c<'static, embassy_stm32::mode::Async>) {
    loop {
        // 读取传感器数据
        let mut buf = [0u8; 6];
        if i2c.write_read(0x38, &[0xAC, 0x33, 0x00], &mut buf).await.is_ok() {
            defmt::info!("传感器数据: {:?}", buf);
        }
        Timer::after(Duration::from_secs(2)).await;
    }
}

#[embassy_executor::task]
async fn uart_handler(mut uart: BufferedUart<'static>) {
    use embassy_stm32::usart::Instance;
    loop {
        let mut buf = [0u8; 128];
        match uart.read(&mut buf).await {
            Ok(n) => {
                defmt::info!("收到 {} 字节", n);
                let _ = uart.write(&buf[..n]).await;
            }
            Err(e) => {
                defmt::error!("UART 错误: {:?}", e);
            }
        }
    }
}
```

### 8.3 Executor 原理

```rust
use core::future::Future;
use core::pin::Pin;
use core::task::{Context, Poll, RawWaker, RawWakerVTable, Waker};

// 简单的单任务 executor
struct Executor {
    task: Option<Pin<Box<dyn Future<Output = ()>>>>,
}

impl Executor {
    fn new() -> Self {
        Self { task: None }
    }

    fn spawn(&mut self, future: impl Future<Output = ()> + 'static) {
        self.task = Some(Box::pin(future));
    }

    fn run(&mut self) -> ! {
        let waker = dummy_waker();
        let mut cx = Context::from_waker(&waker);

        loop {
            if let Some(task) = &mut self.task {
                if task.as_mut().poll(&mut cx).is_ready() {
                    self.task = None;
                }
            }

            // 低功耗等待
            cortex_m::asm::wfi();
        }
    }
}

fn dummy_waker() -> Waker {
    fn no_op(_: *const ()) {}
    fn clone(p: *const ()) -> RawWaker {
        RawWaker::new(p, &VTABLE)
    }

    static VTABLE: RawWakerVTable = RawWakerVTable::new(clone, no_op, no_op, no_op);
    unsafe { Waker::from_raw(RawWaker::new(core::ptr::null(), &VTABLE)) }
}
```

---

## 9. 内存管理

### 9.1 静态分配

```rust
#![no_std]

use core::sync::atomic::{AtomicU32, Ordering};

// 静态分配 - 编译时确定大小和地址
static mut BUFFER: [u8; 1024] = [0; 1024];
static COUNTER: AtomicU32 = AtomicU32::new(0);

// 使用 static 初始化的全局外设引用
use cortex_m::interrupt::Mutex;
use core::cell::UnsafeCell;

struct StaticBuffer {
    data: UnsafeCell<[u8; 4096]>,
    len: UnsafeCell<usize>,
}

unsafe impl Sync for StaticBuffer {}

impl StaticBuffer {
    const fn new() -> Self {
        Self {
            data: UnsafeCell::new([0; 4096]),
            len: UnsafeCell::new(0),
        }
    }

    fn push(&self, byte: u8) -> bool {
        cortex_m::interrupt::free(|_| {
            unsafe {
                let len = *self.len.get();
                if len < 4096 {
                    (*self.data.get())[len] = byte;
                    *self.len.get() = len + 1;
                    true
                } else {
                    false
                }
            }
        })
    }
}

static RING_BUF: StaticBuffer = StaticBuffer::new();
```

### 9.2 借用检查器在嵌入式中的作用

```rust
use cortex_m::interrupt;

// 借用检查器防止数据竞争
// 以下代码编译不通过：
// static mut SHARED: u32 = 0;
//
// #[interrupt]
// fn TIM2() {
//     unsafe { SHARED += 1; } // 危险！可能被另一个中断打断
// }
//
// #[interrupt]
// fn TIM3() {
//     unsafe { SHARED += 1; } // 数据竞争！
// }

// 正确的做法：使用 Mutex
static SHARED: interrupt::Mutex<core::cell::Cell<u32>> =
    interrupt::Mutex::new(core::cell::Cell::new(0));

#[interrupt]
fn TIM2() {
    interrupt::free(|cs| {
        let val = SHARED.borrow(cs).get();
        SHARED.borrow(cs).set(val + 1);
    });
}

#[interrupt]
fn TIM3() {
    interrupt::free(|cs| {
        let val = SHARED.borrow(cs).get();
        SHARED.borrow(cs).set(val + 1);
    });
}

// 生命周期确保 DMA 缓冲区有效性
struct DmaBuffer<'a> {
    data: &'a mut [u8],
}

impl<'a> DmaBuffer<'a> {
    fn new(data: &'a mut [u8]) -> Self {
        Self { data }
    }

    fn as_ptr(&self) -> *const u8 {
        self.data.as_ptr()
    }

    fn len(&self) -> usize {
        self.data.len()
    }
}

// 借用检查器确保 DmaBuffer 的生命周期覆盖整个 DMA 传输
fn start_dma_transfer(buf: DmaBuffer<'_>) {
    // 启动 DMA...
    // buf 必须在整个传输期间保持有效
    // Rust 的借用检查器保证了这一点
}
```

### 9.3 DMA 安全缓冲区

```rust
use core::marker::PhantomPinned;
use core::pin::Pin;

/// DMA 安全缓冲区 - 确保内存地址固定且对齐
#[repr(C, align(4))]
struct DmaSafeBuffer<const N: usize> {
    data: [u8; N],
    _pin: PhantomPinned,
}

impl<const N: usize> DmaSafeBuffer<N> {
    fn new() -> Self {
        Self {
            data: [0; N],
            _pin: PhantomPinned,
        }
    }

    /// 获取缓冲区指针（必须在 pin 之后使用）
    fn as_ptr(self: Pin<&Self>) -> *const u8 {
        self.data.as_ptr()
    }

    fn as_mut_ptr(self: Pin<&mut Self>) -> *mut u8 {
        // Safety: 我们不移动数据
        unsafe { self.get_unchecked_mut().data.as_mut_ptr() }
    }

    fn len() -> usize {
        N
    }
}

// 使用示例
fn dma_transfer_example() {
    let mut buf = DmaSafeBuffer::<256>::new();
    let pinned = unsafe { Pin::new_unchecked(&mut buf) };

    // 填充数据
    unsafe {
        let ptr = pinned.get_unchecked_mut().data.as_mut_ptr();
        for i in 0..256 {
            *ptr.add(i) = i as u8;
        }
    }

    // 配置 DMA 传输
    // dma.start_transfer(pinned.as_ptr(), 256);

    // buf 在此作用域内无法被移动（Pin 保证）
}

/// 双缓冲 DMA
struct DoubleBuffer {
    buf0: DmaSafeBuffer<1024>,
    buf1: DmaSafeBuffer<1024>,
    active: usize,
}

impl DoubleBuffer {
    fn new() -> Self {
        Self {
            buf0: DmaSafeBuffer::new(),
            buf1: DmaSafeBuffer::new(),
            active: 0,
        }
    }

    fn active_buffer_ptr(&self) -> *const u8 {
        if self.active == 0 {
            self.buf0.data.as_ptr()
        } else {
            self.buf1.data.as_ptr()
        }
    }

    fn swap(&mut self) {
        self.active = 1 - self.active;
    }
}
```

### 9.4 堆分配器（可选）

```rust
#![no_std]
#![no_main]

extern crate alloc;

use alloc_cortex_m::CortexMHeap;
use core::alloc::Layout;

// 全局堆分配器
#[global_allocator]
static ALLOCATOR: CortexMHeap = CortexMHeap::empty();

// 堆大小定义
const HEAP_SIZE: usize = 1024 * 16; // 16KB

#[entry]
fn main() -> ! {
    // 初始化堆
    unsafe {
        ALLOCATOR.init(
            cortex_m_rt::heap_start() as usize,
            HEAP_SIZE,
        );
    }

    // 现在可以使用 Vec、String、Box 等
    let mut v = alloc::vec::Vec::new();
    v.push(1);
    v.push(2);
    v.push(3);

    loop {}
}

#[alloc_error_handler]
fn alloc_error(_layout: Layout) -> ! {
    panic!("堆分配失败");
}
```

---

## 10. 常用芯片支持

### 10.1 nRF52 系列（Nordic Semiconductor）

```toml
# Cargo.toml
[dependencies]
nrf52840-hal = "0.16"
nrf-softdevice = { version = "0.1", features = ["s140", "nrf52840"] }
```

```rust
use nrf52840_hal::pac;
use nrf52840_hal::prelude::*;

fn nrf52_init() {
    let dp = pac::Peripherals::take().unwrap();

    // 配置时钟
    let clocks = dp.CLOCK;
    clocks.tasks_hfclkstart.write(|w| w.tasks_hfclkstart().set_bit());
    while clocks.events_hfclkstarted.read().bits() == 0 {}
    clocks.events_hfclkstarted.write(|w| w);

    // 配置 GPIO
    let p0 = nrf52840_hal::gpio::p0::Parts::new(dp.P0);
    let mut led = p0.p0_13.into_push_pull_output(nrf52840_hal::gpio::Level::Low);

    // LED 闪烁
    loop {
        led.set_high().unwrap();
        cortex_m::asm::delay(16_000_000);
        led.set_low().unwrap();
        cortex_m::asm::delay(16_000_000);
    }
}
```

**nRF52 特性：**
- BLE 5.0 支持（通过 nrf-softdevice）
- NFC-A 标签支持
- 低功耗模式（System ON/OFF）
- EasyDMA 硬件加速

### 10.2 STM32 系列（STMicroelectronics）

```toml
# Cargo.toml（以 STM32F4 为例）
[dependencies]
stm32f4xx-hal = { version = "0.21", features = ["stm32f411"] }
cortex-m = "0.7"
cortex-m-rt = "0.7"
```

```rust
use stm32f4xx_hal::{pac, prelude::*, gpio, timer};

fn stm32f4_main() {
    let dp = pac::Peripherals::take().unwrap();

    // 配置时钟树
    let rcc = dp.RCC.constrain();
    let clocks = rcc
        .cfgr
        .use_hse(8.MHz())
        .sysclk(168.MHz())
        .pclk1(42.MHz())
        .pclk2(84.MHz())
        .freeze();

    // 配置 GPIO
    let gpioa = dp.GPIOA.split();
    let mut led = gpioa.pa5.into_push_pull_output();

    // 配置定时器
    let mut timer = dp.TIM2.counter_hz(&clocks);
    timer.start(1.Hz()).unwrap();

    loop {
        nb::block!(timer.wait()).unwrap();
        led.toggle().unwrap();
    }
}

// STM32 DMA 示例
fn dma_transfer_example(dp: &pac::Peripherals) {
    let dma1 = &dp.DMA1;

    // 配置 DMA Stream 0
    // 通道 4 (USART1_RX)
    dma1.s0cr.modify(|_, w| {
        w.en().disabled();
        w.chsel().bits(4);
        w.dir().peripheral_to_memory();
        w.minc().increment();
        w.pinc().fixed();
        w.msize().bits8();
        w.psize().bits8();
        w.circ().enabled();
        w.en().enabled()
    });
}
```

**STM32 系列支持：**
- STM32F0/F1/F2/F3/F4/F7 通用系列
- STM32G0/G4 系列
- STM32H7 高性能系列
- STM32L0/L4/L5 低功耗系列
- STM32WB 无线系列（BLE）

### 10.3 ESP32 系列（Espressif）

```toml
# Cargo.toml
[dependencies]
esp32c3 = "0.25"
esp-hal = { version = "0.21", features = ["esp32c3"] }
esp-wifi = { version = "0.9", features = ["wifi", "ble"] }
```

```rust
#![no_std]
#![no_main]

use esp_hal::prelude::*;
use esp_hal::gpio::Io;
use esp_hal::timer::timg::TimerGroup;

#[entry]
fn main() -> ! {
    let peripherals = esp_hal::init(esp_hal::Config::default());

    let timg0 = TimerGroup::new(peripherals.TIMG0);
    esp_hal_embassy::init(timg0.timer0);

    let io = Io::new(peripherals.GPIO, peripherals.IO_MUX);
    let mut led = io.pins.gpio2.into_push_pull_output();

    loop {
        led.toggle();
        esp_hal::delay::Delay::new().delay_millis(500);
    }
}
```

**ESP32 特性：**
- Wi-Fi + BLE 双模
- ESP32-C3/RISC-V 架构
- ESP32-S3 双核 + AI 加速
- ESP-IDF 兼容层（esp-idf-sys）

### 10.4 RP2040（Raspberry Pi）

```toml
# Cargo.toml
[dependencies]
rp-pico = "0.9"
rp2040-hal = "0.10"
```

```rust
#![no_std]
#![no_main]

use rp_pico::entry;
use rp_pico::hal::pac;
use rp_pico::hal::prelude::*;

#[entry]
fn main() -> ! {
    let mut pac = pac::Peripherals::take().unwrap();
    let mut watchdog = pac.WATCHDOG;
    let sio = rp_pico::hal::Sio::new(pac.SIO);

    let clocks = rp_pico::hal::clocks::init_clocks_and_plls(
        rp_pico::XOSC_CRYSTAL_FREQ,
        pac.XOSC,
        pac.CLOCKS,
        pac.PLL_SYS,
        pac.PLL_USB,
        &mut pac.RESETS,
        &mut watchdog,
    )
    .ok()
    .unwrap();

    let pins = rp_pico::Pins::new(
        pac.IO_BANK0,
        pac.PADS_BANK0,
        sio.gpio_bank0,
        &mut pac.RESETS,
    );

    let mut led_pin = pins.led.into_push_pull_output();

    let timer = rp_pico::hal::Timer::new(pac.TIMER, &mut pac.RESETS);

    loop {
        led_pin.set_high().unwrap();
        timer.delay_ms(500);
        led_pin.set_low().unwrap();
        timer.delay_ms(500);
    }
}
```

**RP2040 特性：**
- 双核 ARM Cortex-M0+
- PIO（Programmable I/O）状态机
- 264KB SRAM
- USB 1.1 设备/主机

---

## 11. 实战项目

### 11.1 LED 控制

```rust
#![no_std]
#![no_main]

use cortex_m_rt::entry;
use defmt_rtt as _;
use panic_probe as _;
use stm32f4xx_hal::{pac, prelude::*, gpio::PinState};

#[entry]
fn main() -> ! {
    let dp = pac::Peripherals::take().unwrap();
    let rcc = dp.RCC.constrain();
    let clocks = rcc.cfgr.sysclk(168.MHz()).freeze();

    let gpioa = dp.GPIOA.split();

    // 基础 LED 控制
    let mut led_green = gpioa.pa5.into_push_pull_output();
    let mut led_red = gpioa.pa6.into_push_pull_output();

    // LED 呼吸灯（PWM）
    let mut pwm = dp.TIM2.pwm_hz(
        gpioa.pa0.into_alternate(),
        1.kHz(),
        &clocks,
    );
    pwm.enable();

    let max_duty = pwm.get_max_duty();
    let mut brightness: i32 = 0;
    let mut direction: i32 = 100;

    let mut timer = dp.TIM3.counter_ms(&clocks);
    timer.start(10.millis()).unwrap();

    loop {
        nb::block!(timer.wait()).unwrap();

        // 呼吸效果
        brightness += direction;
        if brightness >= max_duty as i32 {
            brightness = max_duty as i32;
            direction = -100;
        } else if brightness <= 0 {
            brightness = 0;
            direction = 100;
        }
        pwm.set_duty(brightness as u16);

        // LED 交替闪烁
        led_green.toggle().unwrap();
        led_red.toggle().unwrap();
    }
}
```

### 11.2 传感器读取（BME280）

```rust
use embedded_hal::i2c::I2c;

struct Bme280<I2C> {
    i2c: I2C,
    addr: u8,
    calib: CalibrationData,
}

#[derive(Default)]
struct CalibrationData {
    dig_t1: u16,
    dig_t2: i16,
    dig_t3: i16,
    dig_p1: u16,
    dig_p2: i16,
    // ... 更多校准参数
}

#[derive(Debug, defmt::Format)]
struct WeatherData {
    temperature: f32,
    pressure: f32,
    humidity: f32,
    altitude: f32,
}

impl<I2C: I2c> Bme280<I2C> {
    fn new(i2c: I2C, addr: u8) -> Self {
        Self {
            i2c,
            addr,
            calib: CalibrationData::default(),
        }
    }

    fn init(&mut self) -> Result<(), I2C::Error> {
        // 软复位
        self.i2c.write(self.addr, &[0xE0, 0xB6])?;
        cortex_m::asm::delay(100_000);

        // 读取芯片 ID
        let mut id = [0u8; 1];
        self.i2c.write_read(self.addr, &[0xD0], &mut id)?;
        assert_eq!(id[0], 0x60, "BME280 芯片 ID 不匹配");

        // 读取校准数据
        self.read_calibration()?;

        // 配置：温度 x16, 压力 x16, 湿度 x1
        self.i2c.write(self.addr, &[0xF2, 0x05])?; // ctrl_hum
        self.i2c.write(self.addr, &[0xF4, 0xB7])?; // ctrl_meas
        self.i2c.write(self.addr, &[0xF5, 0xA0])?; // config

        Ok(())
    }

    fn read_calibration(&mut self) -> Result<(), I2C::Error> {
        let mut buf = [0u8; 26];
        self.i2c.write_read(self.addr, &[0x88], &mut buf)?;

        self.calib.dig_t1 = u16::from_le_bytes([buf[0], buf[1]]);
        self.calib.dig_t2 = i16::from_le_bytes([buf[2], buf[3]]);
        self.calib.dig_t3 = i16::from_le_bytes([buf[4], buf[5]]);
        self.calib.dig_p1 = u16::from_le_bytes([buf[6], buf[7]]);
        self.calib.dig_p2 = i16::from_le_bytes([buf[8], buf[9]]);

        Ok(())
    }

    fn read(&mut self) -> Result<WeatherData, I2C::Error> {
        let mut buf = [0u8; 8];
        self.i2c.write_read(self.addr, &[0xF7], &mut buf)?;

        let press_raw = ((buf[0] as u32) << 12) | ((buf[1] as u32) << 4) | ((buf[2] as u32) >> 4);
        let temp_raw = ((buf[3] as u32) << 12) | ((buf[4] as u32) << 4) | ((buf[5] as u32) >> 4);
        let hum_raw = ((buf[6] as u32) << 8) | (buf[7] as u32);

        let temp = self.compensate_temperature(temp_raw as i32);
        let press = self.compensate_pressure(press_raw as i32);
        let hum = self.compensate_humidity(hum_raw as i32);

        // 海拔计算
        let altitude = 44330.0 * (1.0 - (press / 101325.0).powf(0.1903));

        Ok(WeatherData {
            temperature: temp,
            pressure: press,
            humidity: hum,
            altitude,
        })
    }

    fn compensate_temperature(&self, raw: i32) -> f32 {
        let var1 = (raw as f32 / 16384.0 - self.calib.dig_t1 as f32 / 1024.0) * self.calib.dig_t2 as f32;
        let var2 = ((raw as f32 / 131072.0 - self.calib.dig_t1 as f32 / 8192.0).powi(2))
            * self.calib.dig_t3 as f32;
        (var1 + var2) / 5120.0
    }

    fn compensate_pressure(&self, raw: i32) -> f32 {
        // 简化计算
        raw as f32 / 256.0
    }

    fn compensate_humidity(&self, raw: i32) -> f32 {
        raw as f32 / 1024.0
    }
}
```

### 11.3 UART 通信协议

```rust
use embedded_hal_nb::serial::{Read, Write};

/// 简单的请求-响应协议
#[derive(Debug, defmt::Format)]
enum Command {
    ReadSensor { id: u8 },
    SetLed { state: bool },
    GetVersion,
    Reboot,
}

#[derive(Debug, defmt::Format)]
enum Response {
    SensorData { id: u8, value: f32 },
    Ack,
    Version { major: u8, minor: u8, patch: u8 },
    Error { code: u16 },
}

struct ProtocolHandler<UART> {
    uart: UART,
    rx_buf: [u8; 64],
    rx_pos: usize,
}

impl<UART: Read<u8> + Write<u8>> ProtocolHandler<UART> {
    fn new(uart: UART) -> Self {
        Self {
            uart,
            rx_buf: [0; 64],
            rx_pos: 0,
        }
    }

    fn poll(&mut self) -> Option<Command> {
        loop {
            match self.uart.read() {
                Ok(byte) => {
                    if self.rx_pos >= self.rx_buf.len() {
                        self.rx_pos = 0;
                        return None;
                    }

                    self.rx_buf[self.rx_pos] = byte;
                    self.rx_pos += 1;

                    // 帧结束检测
                    if byte == b'\n' {
                        let cmd = self.parse_frame();
                        self.rx_pos = 0;
                        return cmd;
                    }
                }
                Err(nb::Error::WouldBlock) => return None,
                Err(_) => {
                    self.rx_pos = 0;
                    return None;
                }
            }
        }
    }

    fn parse_frame(&self) -> Option<Command> {
        let frame = &self.rx_buf[..self.rx_pos];
        if frame.len() < 2 {
            return None;
        }

        match frame[0] {
            b'R' => Some(Command::ReadSensor { id: frame[1] }),
            b'L' => Some(Command::SetLed { state: frame[1] != 0 }),
            b'V' => Some(Command::GetVersion),
            b'X' => Some(Command::Reboot),
            _ => None,
        }
    }

    fn send_response(&mut self, resp: &Response) -> Result<(), nb::Error<void::Void>> {
        let bytes = match resp {
            Response::SensorData { id, value } => {
                let mut buf = [0u8; 8];
                buf[0] = b'S';
                buf[1] = *id;
                buf[2..6].copy_from_slice(&value.to_le_bytes());
                buf[6] = b'\n';
                buf[..7].to_vec()
            }
            Response::Ack => vec![b'O', b'K', b'\n'],
            Response::Version { major, minor, patch } => {
                vec![b'V', *major, *minor, *patch, b'\n']
            }
            Response::Error { code } => {
                let bytes = code.to_le_bytes();
                vec![b'E', bytes[0], bytes[1], b'\n']
            }
        };

        for &byte in &bytes {
            nb::block!(self.uart.write(byte))?;
        }
        Ok(())
    }
}
```

### 11.4 BLE 外设（nRF52 + nrf-softdevice）

```rust
#![no_std]
#![no_main]

use nrf_softdevice::ble::{gatt_server, peripheral};
use nrf_softdevice::{raw, Softdevice};

#[nrf_softdevice::gatt_service(uuid = "180a")]
struct DeviceInfoService {
    #[characteristic(uuid = "2a29", read)]
    manufacturer: heapless::String<32>,

    #[characteristic(uuid = "2a24", read)]
    model: heapless::String<32>,
}

#[nrf_softdevice::gatt_service(uuid = "180f")]
struct BatteryService {
    #[characteristic(uuid = "2a19", read, notify)]
    battery_level: u8,
}

#[nrf_softdevice::gatt_server]
struct Server {
    device_info: DeviceInfoService,
    battery: BatteryService,
}

fn softdevice_config() -> nrf_softdevice::Config {
    nrf_softdevice::Config {
        clock: Some(raw::nrf_clock_lf_cfg_t {
            source: raw::NRF_CLOCK_LF_SRC_RC as u8,
            rc_ctiv: 16,
            rc_temp_ctiv: 2,
            accuracy: raw::NRF_CLOCK_LF_ACCURACY_250_PPM as u8,
        }),
        conn_gap: Some(raw::ble_gap_conn_cfg_t {
            conn_count: 2,
            event_length: 24,
        }),
        conn_gatt: Some(raw::ble_gatt_conn_cfg_t {
            att_mtu: 256,
        }),
        gatts_attr_tab_size: Some(raw::ble_gatts_cfg_attr_tab_size_t {
            attr_tab_size: 32768,
        }),
        gap_role_count: Some(raw::ble_gap_cfg_role_count_t {
            adv_set_count: 1,
            periph_role_count: 3,
        }),
        ..Default::default()
    }
}

#[embassy_executor::task]
async fn softdevice_task(sd: &'static Softdevice) {
    sd.run().await;
}

#[embassy_executor::task]
async fn ble_advertise(
    sd: &'static Softdevice,
    server: Server,
) {
    let adv_data = &[
        0x02, 0x01, 0x06, // Flags
        0x06, 0x09, b'M', b'y', b'D', b'e', b'v', // Name
    ];

    loop {
        let adv = peripheral::ConnectableAdvertisement::ScannableUndirected {
            adv_data,
            scan_data: &[],
        };

        let conn = peripheral::advertise_connectable(sd, adv, &peripheral::Config::default())
            .await
            .unwrap();

        defmt::info!("BLE 已连接");

        // 处理 GATT 事件
        let _ = gatt_server::run(&conn, &server, |e| match e {
            ServerEvent::Battery(e) => match e {
                BatteryServiceEvent::BatteryLevelCccdWrite { notifications } => {
                    defmt::info!("电池通知: {}", notifications);
                }
            },
            _ => {}
        })
        .await;

        defmt::info!("BLE 断开连接");
    }
}
```

---

## 12. Rust vs C 嵌入式开发深入对比

### 12.1 开发效率

| 维度 | Rust | C |
|------|------|---|
| 代码复用 | trait 抽象 + Cargo 依赖管理，高度可复用 | 手动复制或有限的宏/函数指针 |
| 编译时检查 | 类型系统 + 所有权系统捕获大量错误 | 仅基础类型检查，许多错误运行时暴露 |
| 构建系统 | Cargo 统一管理，开箱即用 | Makefile / CMake / 各厂商 IDE，碎片化 |
| 依赖管理 | crates.io 生态，版本锁定 | 手动下载、集成，版本冲突常见 |
| 重构安全 | 编译器保证重构不破坏语义 | 重构风险高，依赖手动测试 |
| 测试 | 内置 #[test]，可在主机运行 | 需要额外框架（Unity、CUnit） |
| 文档 | rustdoc 从注释生成，支持示例代码测试 | Doxygen，配置复杂 |

### 12.2 安全性

```rust
// Rust 编译期防止的常见 C 嵌入式错误：

// 1. 缓冲区溢出
fn safe_copy(dst: &mut [u8], src: &[u8]) {
    let len = dst.len().min(src.len());
    dst[..len].copy_from_slice(&src[..len]);
    // Rust 自动边界检查，越界会 panic 而非写坏内存
}

// 2. 空指针解引用
fn process(data: Option<&[u8]>) {
    match data {
        Some(bytes) => { /* 安全使用 */ }
        None => { /* 处理空值 */ }
    }
    // 没有 null，必须显式处理 None
}

// 3. 数据竞争
// #[interrupt] fn TIM2() { shared += 1; } // 编译错误！
// 必须使用 Mutex 保护共享数据

// 4. Use-After-Free
fn no_uaf() {
    let s = String::from("hello");
    let r = &s;
    drop(s); // 编译错误：不能在借用存在时 drop
    // println!("{}", r);
}

// 5. Double Free
fn no_double_free() {
    let s = String::from("hello");
    let s2 = s;
    // drop(s); // 编译错误：s 已移动
    drop(s2); // 正确
}
```

### 12.3 性能对比

```c
// C 代码
void process_buffer(uint8_t* buf, size_t len) {
    for (size_t i = 0; i < len; i++) {
        buf[i] = buf[i] * 2 + 1;
    }
}
```

```rust
// Rust 代码 - 性能完全相同
fn process_buffer(buf: &mut [u8]) {
    for byte in buf.iter_mut() {
        *byte = byte.wrapping_mul(2).wrapping_add(1);
    }
}

// Rust 迭代器版本 - 编译器优化后性能相同
fn process_buffer_iter(buf: &mut [u8]) {
    buf.iter_mut().for_each(|b| {
        *b = b.wrapping_mul(2).wrapping_add(1);
    });
}
```

**性能特点：**
- 零成本抽象：泛型/迭代器/闭包编译后等价于手写循环
- LLVM 后端优化：与 C 共享相同的优化能力
- 内联优化：小函数自动内联
- 无隐式开销：无 GC 暂停、无引用计数（除非显式使用 Arc/Rc）

### 12.4 生态成熟度

| 工具/库 | Rust | C |
|---------|------|---|
| 调试器 | probe-rs, probe-rs-cli | J-Link, OpenOCD + GDB |
| IDE 支持 | VS Code + rust-analyzer, CLion | VS Code, Keil, IAR, STM32CubeIDE |
| HAL 层 | embedded-hal（统一 trait） | 各厂商 HAL（不统一） |
| RTOS | RTIC, Embassy（异步） | FreeRTOS, Zephyr, ThreadX |
| 包管理 | Cargo + crates.io | vcpkg / 手动 |
| 代码分析 | clippy, rustfmt | cppcheck, clang-tidy |
| CI/CD | GitHub Actions 生态成熟 | 成熟但需更多配置 |
| 学习资源 | 快速增长（The Embedded Rust Book） | 极其丰富（数十年积累） |
| 社区规模 | 快速增长中 | 非常大 |
| 商业支持 | 初创公司推动 | 所有芯片厂商 |

### 12.5 何时选择 Rust vs C

**选择 Rust：**
- 新项目，无历史代码包袱
- 对内存安全要求高（医疗、航空、汽车）
- 团队愿意投入学习曲线
- 需要长期维护的项目
- 依赖多个第三方库的项目

**选择 C：**
- 已有大型 C 代码库
- 芯片厂商仅提供 C SDK
- 团队 Rust 经验不足，项目时间紧
- 资源极受限（< 16KB Flash）
- 需要使用特定厂商工具链

**混合方案：**
- 新模块用 Rust，已有 C 代码通过 FFI 集成
- 关键安全模块用 Rust，其他保持 C
- 使用 `bindgen` 自动生成 C 绑定

```rust
// Rust 调用 C 函数
extern "C" {
    fn c_legacy_function(input: u32) -> u32;
}

// C 调用 Rust 函数
#[no_mangle]
pub extern "C" fn rust_function(input: u32) -> u32 {
    input.wrapping_mul(2)
}

// bindgen 自动生成绑定
// build.rs 中调用 bindgen::Builder
```

---

## 附录

### A. 常用 Cargo 命令

```bash
# 创建新项目
cargo new my_embedded_project --bin

# 添加依赖
cargo add cortex-m cortex-m-rt defmt defmt-rtt panic-probe

# 交叉编译
cargo build --target thumbv7em-none-eabihf --release

# 烧录运行
cargo run --target thumbv7em-none-eabihf --release

# 检查代码
cargo clippy --target thumbv7em-none-eabihf

# 格式化
cargo fmt

# 生成文档
cargo doc --open
```

### B. 常用 target triple

| Target | 架构 | 示例芯片 |
|--------|------|----------|
| `thumbv6m-none-eabi` | ARMv6-M (Cortex-M0/M0+) | nRF51822, RP2040 |
| `thumbv7m-none-eabi` | ARMv7-M (Cortex-M3) | STM32F103 |
| `thumbv7em-none-eabi` | ARMv7E-M (Cortex-M4/M7 无 FPU) | STM32F401 |
| `thumbv7em-none-eabihf` | ARMv7E-M (Cortex-M4/M7 有 FPU) | STM32F411, nRF52840 |
| `thumbv8m.main-none-eabihf` | ARMv8-M (Cortex-M33) | nRF5340 |
| `riscv32imc-unknown-none-elf` | RISC-V | ESP32-C3 |
| `xtensa-esp32-none-elf` | Xtensa | ESP32 |

### C. 推荐学习资源

1. **The Embedded Rust Book**：https://docs.rust-embedded.org/book/
2. **Discovery Book**：https://docs.rust-embedded.org/discovery/
3. **embedded-hal 文档**：https://docs.rs/embedded-hal/
4. **Embassy 文档**：https://embassy.dev/
5. **probe-rs 文档**：https://probe.rs/
6. **Rust Embedded 社区**：https://matrix.to/#/#rust-embedded:matrix.org
7. **Awesome Embedded Rust**：https://github.com/rust-embedded/awesome-embedded-rust

### D. 常见错误与解决

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `error[E0599]: no method named 'xxx'` | HAL 版本不匹配 | 检查 Cargo.lock，统一 HAL 版本 |
| `error: could not compile` | 缺少 target | `rustup target add thumbv7em-none-eabihf` |
| `HardFault` at startup | 时钟配置错误 | 检查 RCC 配置，确保 HSE 频率正确 |
| `linking with cc failed` | 缺少链接脚本 | 添加 memory.x 或 build.rs 配置 |
| `overflow of 16 bits` | 中断向量表溢出 | 检查 .cargo/config.toml 的 target 设置 |
| RTT 无输出 | 未初始化 RTT | 确保 `defmt-rtt` 和 `panic-probe` 已添加 |

---

*最后更新：2026-06-21*
