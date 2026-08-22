# Rust嵌入式开发

## 核心概念

- **Rust** - 系统级编程语言
- **所有权** - 内存安全保证
- **嵌入式HAL** - 硬件抽象层
- **no_std** - 无标准库环境

---

## 一、Rust嵌入式基础

### 1.1 为什么用Rust

```rust
// Rust优势
/*
 * 1. 内存安全(无GC)
 *    - 所有权系统
 *    - 借用检查器
 *    - 生命周期
 *
 * 2. 零成本抽象
 *    - 泛型
 *    - trait
 *    - 内联优化
 *
 * 3. 并发安全
 *    - 编译时数据竞争检测
 *    - Send/Sync trait
 *
 * 4. 与C互操作
 *    - FFI
 *    - 寄存器访问
 */

#![no_std]
#![no_main]

use cortex_m_rt::entry;
use panic_halt as _;

#[entry]
fn main() -> ! {
    // 初始化
    let dp = stm32f4::Peripherals::take().unwrap();

    // 配置GPIO
    dp.GPIOA.moder.modify(|_, w| w.moder5().output());
    dp.GPIOA.odr.modify(|_, w| w.odr5().set_bit());

    loop {
        // LED闪烁
        dp.GPIOA.odr.modify(|_, w| w.odr5().toggle());
        cortex_m::asm::delay(8_000_000);
    }
}
```

---

### 1.2 项目配置

```toml
# Cargo.toml
[package]
name = "embedded-app"
version = "0.1.0"
edition = "2021"

[dependencies]
cortex-m = "0.7"
cortex-m-rt = "0.7"
cortex-m-semihosting = "0.5"
panic-halt = "0.2"
stm32f4xx-hal = { version = "0.14", features = ["rt", "stm32f411"] }

[profile.release]
opt-level = "z"      # 优化大小
lto = true           # 链接时优化
codegen-units = 1    # 单编译单元
```

---

## 二、嵌入式HAL

### 2.1 GPIO操作

```rust
use stm32f4xx_hal::{prelude::*, gpio::*, pac};

fn gpio_example() {
    let dp = pac::Peripherals::take().unwrap();
    let gpioa = dp.GPIOA.split();

    // 输出
    let mut led = gpioa.pa5.into_push_pull_output();

    // 输入
    let button = gpioa.pa0.into_pull_up_input();

    loop {
        if button.is_high() {
            led.set_high();
        } else {
            led.set_low();
        }
    }
}

// 嵌入式HAL trait
use embedded_hal::digital::v2::{InputPin, OutputPin};

fn generic_gpio<P>(mut pin: P) where P: OutputPin {
    pin.set_high().ok();
    pin.set_low().ok();
}
```

---

### 2.2 定时器

```rust
use stm32f4xx_hal::{prelude::*, timer::*};

fn timer_example() {
    let dp = pac::Peripherals::take().unwrap();
    let rcc = dp.RCC.constrain();
    let clocks = rcc.cfgr.freeze();

    // 定时器
    let mut timer = dp.TIM2.counter_hz(&clocks);
    timer.start(1.Hz()).unwrap();

    loop {
        nb::block!(timer.wait()).unwrap();
        // 每秒执行
    }
}

// PWM输出
fn pwm_example() {
    let dp = pac::Peripherals::take().unwrap();
    let gpioa = dp.GPIOA.split();

    let pins = gpioa.pa0.into_alternate();

    let mut pwm = dp.TIM2.pwm_hz(pins, 1.kHz(), &clocks);
    pwm.enable();
    pwm.set_duty(pwm.get_max_duty() / 2);  // 50%占空比
}
```

---

### 2.3 I2C通信

```rust
use stm32f4xx_hal::{prelude::*, i2c::*};
use embedded_hal::blocking::i2c::{Write, WriteRead};

fn i2c_example() {
    let dp = pac::Peripherals::take().unwrap();

    let scl = gpioa.pb6.into_alternate().open_drain();
    let sda = gpioa.pb7.into_alternate().open_drain();

    let mut i2c = dp.I2C1.i2c((scl, sda), 400.kHz(), &clocks);

    // BMP280读取ID
    let mut buf = [0u8; 1];
    i2c.write_read(0x76, &[0xD0], &mut buf).unwrap();
    println!("BMP280 ID: 0x{:02X}", buf[0]);

    // 写入寄存器
    i2c.write(0x76, &[0xF4, 0x27]).unwrap();
}
```

---

### 2.4 SPI通信

```rust
use stm32f4xx_hal::{prelude::*, spi::*};

fn spi_example() {
    let dp = pac::Peripherals::take().unwrap();

    let sck = gpioa.pa5.into_alternate();
    let miso = gpioa.pa6.into_alternate();
    let mosi = gpioa.pa7.into_alternate();
    let mut cs = gpioa.pa4.into_push_pull_output();

    let mut spi = dp.SPI1.spi(
        (sck, miso, mosi),
        MODE_0,
        1.MHz(),
        &clocks,
    );

    // 发送接收
    cs.set_low();
    let data = spi.transfer(&mut [0x9F, 0x00, 0x00, 0x00]).unwrap();
    cs.set_high();

    println!("JEDEC ID: {:02X} {:02X} {:02X}", data[1], data[2], data[3]);
}
```

---

## 三、中断处理

### 3.1 中断配置

```rust
use cortex_m_rt::interrupt;
use stm32f4xx_hal::pac;

// 中断处理函数
#[interrupt]
fn EXTI0() {
    // 清除中断标志
    unsafe {
        (*pac::EXTI::ptr()).pr.modify(|_, w| w.pr0().set_bit());
    }

    // 处理中断
    // ...
}

// 中断配置
fn configure_interrupt() {
    let dp = unsafe { pac::Peripherals::steal() };

    // 使能SYSCFG时钟
    dp.RCC.apb2enr.modify(|_, w| w.syscfgen().set_bit());

    // 配置PA0为中断源
    dp.SYSCFG.exticr1.modify(|_, w| w.exti0().pa());

    // 配置下降沿触发
    dp.EXTI.ftsr.modify(|_, w| w.tr0().set_bit());

    // 使能中断
    dp.EXTI.imr.modify(|_, w| w.mr0().set_bit());

    // 使能NVIC
    unsafe {
        cortex_m::peripheral::NVIC::unmask(pac::Interrupt::EXTI0);
    }
}
```

---

## 四、DMA传输

### 4.1 DMA配置

```rust
use stm32f4xx_hal::{pac, dma::*};

fn dma_example() {
    let dp = pac::Peripherals::take().unwrap();

    // 配置DMA
    let streams = StreamsTuple::new(dp.DMA1);

    // 传输缓冲区
    let buffer = [0u8; 256];

    // 配置DMA流
    let config = DmaConfig::default()
        .transfer_complete_interrupt(true)
        .memory_increment(true)
        .peripheral_increment(false);

    // 启动传输
    let transfer = Transfer::init(
        streams.0,
        dp.USART1,
        buffer,
        None,
        config,
    );

    transfer.start(|_usart| {});
}

// DMA中断处理
#[interrupt]
fn DMA1_STREAM0() {
    // 处理传输完成
    // ...
}
```

---

## 五、异步嵌入式

### 5.1 async/await

```rust
// Embassy框架(异步嵌入式)
use embassy_executor::Spawner;
use embassy_time::{Duration, Timer};
use embassy_stm32::gpio::*;

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    let p = embassy_stm32::init(Default::default());

    let mut led = Output::new(p.PA5, Level::Low, Speed::Low);

    loop {
        led.toggle();
        Timer::after(Duration::from_millis(500)).await;
    }
}

// 异步任务
#[embassy_executor::task]
async fn sensor_task(mut pin: Input<'static, AnyPin>) {
    loop {
        pin.wait_for_rising_edge().await;
        // 处理传感器数据
    }
}
```

---

## 六、与C互操作

### 6.1 FFI调用

```rust
// 调用C函数
extern "C" {
    fn c_function(input: u32) -> u32;
}

// 导出给C调用
#[no_mangle]
pub extern "C" fn rust_function(input: u32) -> u32 {
    input * 2
}

// 寄存器访问
fn read_register(addr: u32) -> u32 {
    unsafe { core::ptr::read_volatile(addr as *const u32) }
}

fn write_register(addr: u32, value: u32) {
    unsafe { core::ptr::write_volatile(addr as *mut u32, value) }
}
```

---

## 七、错误处理

### 7.1 嵌入式错误处理

```rust
// 自定义错误类型
#[derive(Debug)]
enum MyError {
    SensorError,
    CommError,
    TimeoutError,
}

// Result类型
fn read_sensor() -> Result<f32, MyError> {
    let value = adc_read()?;
    if value > 4095 {
        return Err(MyError::SensorError);
    }
    Ok(value as f32 / 4095.0 * 3.3)
}

// 错误处理
fn process() -> Result<(), MyError> {
    let voltage = read_sensor()?;
    println!("Voltage: {:.2}V", voltage);
    Ok(())
}
```

---

## 附录：Rust嵌入式生态

| 库 | 用途 |
|------|------|
| cortex-m | ARM Cortex-M |
| cortex-m-rt | 启动代码 |
| embedded-hal | 硬件抽象 |
| stm32f4xx-hal | STM32F4 |
| esp-idf-svc | ESP32 |
| embassy | 异步框架 |
| defmt | 日志框架 |
| probe-rs | 调试工具 |

---

## 相关链接

- [[C语言深入]] - C语言基础
- [[STM32基础]] - STM32开发
- [[ESP-IDF开发详解]] - ESP32开发
