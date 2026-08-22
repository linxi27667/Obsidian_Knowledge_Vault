# Linux驱动开发

## 核心概念

- **设备驱动** - 硬件与内核之间的接口
- **字符设备** - 按字节流访问的设备
- **块设备** - 按块访问的设备
- **网络设备** - 网络通信设备

---

## 一、驱动分类

### 1.1 设备类型

| 类型 | 说明 | 示例 |
|------|------|------|
| 字符设备 | 串行访问 | 串口、GPIO、LED |
| 块设备 | 随机访问 | 磁盘、Flash |
| 网络设备 | 网络通信 | 网卡、WiFi |

---

### 1.2 驱动框架

```
用户空间：应用程序
    │
    ↓ 系统调用
内核空间：VFS
    │
    ↓ 文件操作
设备驱动：file_operations
    │
    ↓ 寄存器操作
硬件：设备
```

---

## 二、字符设备驱动

### 2.1 基本框架

```c
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>

#define DEVICE_NAME "mydevice"
#define CLASS_NAME "myclass"

static dev_t dev_num;
static struct cdev my_cdev;
static struct class *my_class;
static struct device *my_device;

// 文件操作函数
static int my_open(struct inode *inode, struct file *filp) {
    printk(KERN_INFO "mydevice: opened\n");
    return 0;
}

static int my_release(struct inode *inode, struct file *filp) {
    printk(KERN_INFO "mydevice: closed\n");
    return 0;
}

static ssize_t my_read(struct file *filp, char __user *buf, 
                       size_t count, loff_t *f_pos) {
    // 读取数据
    copy_to_user(buf, data, count);
    return count;
}

static ssize_t my_write(struct file *filp, const char __user *buf,
                        size_t count, loff_t *f_pos) {
    // 写入数据
    copy_from_user(data, buf, count);
    return count;
}

// 文件操作结构体
static const struct file_operations my_fops = {
    .owner = THIS_MODULE,
    .open = my_open,
    .release = my_release,
    .read = my_read,
    .write = my_write,
};

// 模块初始化
static int __init my_init(void) {
    // 动态分配设备号
    alloc_chrdev_region(&dev_num, 0, 1, DEVICE_NAME);
    
    // 初始化字符设备
    cdev_init(&my_cdev, &my_fops);
    cdev_add(&my_cdev, dev_num, 1);
    
    // 创建设备类
    my_class = class_create(THIS_MODULE, CLASS_NAME);
    
    // 创建设备节点
    my_device = device_create(my_class, NULL, dev_num, NULL, DEVICE_NAME);
    
    printk(KERN_INFO "mydevice: initialized\n");
    return 0;
}

// 模块退出
static void __exit my_exit(void) {
    device_destroy(my_class, dev_num);
    class_destroy(my_class);
    cdev_del(&my_cdev);
    unregister_chrdev_region(dev_num, 1);
    
    printk(KERN_INFO "mydevice: exited\n");
}

module_init(my_init);
module_exit(my_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Author");
MODULE_DESCRIPTION("My Character Device Driver");
```

---

### 2.2 Makefile

```makefile
obj-m := mydevice.o

KDIR := /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean

install:
	sudo insmod mydevice.ko
	sudo mknod /dev/mydevice c $(shell cat /proc/devices | grep mydevice | awk '{print $$1}') 0

uninstall:
	sudo rmmod mydevice
	sudo rm /dev/mydevice
```

---

### 2.3 用户空间测试

```c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

int main() {
    int fd = open("/dev/mydevice", O_RDWR);
    if (fd < 0) {
        perror("open");
        return -1;
    }
    
    // 写入数据
    write(fd, "Hello", 5);
    
    // 读取数据
    char buf[10];
    read(fd, buf, sizeof(buf));
    printf("Read: %s\n", buf);
    
    close(fd);
    return 0;
}
```

---

## 三、设备树(Device Tree)

### 3.1 设备树语法

**DTS文件：**
```dts
/ {
    model = "My Board";
    compatible = "my,board";
    
    chosen {
        bootargs = "console=ttyS0,115200";
    };
    
    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x20000000>;  // 512MB
    };
    
    led {
        compatible = "my,led";
        gpios = <&gpio0 5 GPIO_ACTIVE_HIGH>;
        status = "okay";
    };
};
```

---

### 3.2 设备树属性

| 属性 | 说明 |
|------|------|
| compatible | 设备兼容字符串 |
| reg | 寄存器地址和大小 |
| interrupts | 中断号 |
| clocks | 时钟引用 |
| status | 设备状态 |
| gpios | GPIO引用 |

---

### 3.3 设备树绑定

```c
// 驱动中解析设备树
static int my_probe(struct platform_device *pdev) {
    struct device_node *np = pdev->dev.of_node;
    
    // 读取属性
    const char *str;
    of_property_read_string(np, "my,string", &str);
    
    // 读取整数
    u32 val;
    of_property_read_u32(np, "my,value", &val);
    
    // 读取GPIO
    int gpio = of_get_named_gpio(np, "my,gpio", 0);
    gpio_request(gpio, "my-gpio");
    gpio_direction_output(gpio, 0);
    
    return 0;
}

// 设备树匹配表
static const struct of_device_id my_of_match[] = {
    { .compatible = "my,device" },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, my_of_match);

// 平台驱动
static struct platform_driver my_driver = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my-driver",
        .of_match_table = my_of_match,
    },
};
module_platform_driver(my_driver);
```

---

## 四、平台设备驱动

### 4.1 平台设备

```c
// 定义平台设备
static struct resource my_resources[] = {
    {
        .start = 0x10000000,
        .end = 0x10000FFF,
        .flags = IORESOURCE_MEM,
    },
    {
        .start = 10,
        .end = 10,
        .flags = IORESOURCE_IRQ,
    },
};

static struct platform_device my_pdev = {
    .name = "my-device",
    .id = -1,
    .resource = my_resources,
    .num_resources = ARRAY_SIZE(my_resources),
};
```

---

### 4.2 平台驱动

```c
static int my_probe(struct platform_device *pdev) {
    // 获取资源
    struct resource *mem = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    struct resource *irq = platform_get_resource(pdev, IORESOURCE_IRQ, 0);
    
    // 映射寄存器
    void __iomem *base = ioremap(mem->start, resource_size(mem));
    
    // 注册中断
    request_irq(irq->start, my_irq_handler, 0, "my-device", NULL);
    
    return 0;
}

static int my_remove(struct platform_device *pdev) {
    // 释放资源
    free_irq(irq, NULL);
    iounmap(base);
    return 0;
}

static struct platform_driver my_driver = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my-device",
    },
};
module_platform_driver(my_driver);
```

---

## 五、中断处理

### 5.1 中断注册

```c
#include <linux/interrupt.h>

static irqreturn_t my_irq_handler(int irq, void *dev_id) {
    // 中断处理
    printk(KERN_INFO "Interrupt occurred\n");
    return IRQ_HANDLED;
}

// 注册中断
request_irq(irq_num, my_irq_handler, IRQF_SHARED, "my-device", dev_id);

// 释放中断
free_irq(irq_num, dev_id);
```

---

### 5.2 中断标志

| 标志 | 说明 |
|------|------|
| IRQF_SHARED | 共享中断 |
| IRQF_TRIGGER_RISING | 上升沿触发 |
| IRQF_TRIGGER_FALLING | 下降沿触发 |
| IRQF_TRIGGER_HIGH | 高电平触发 |
| IRQF_TRIGGER_LOW | 低电平触发 |

---

### 5.3 工作队列

```c
#include <linux/workqueue.h>

static struct work_struct my_work;

static void my_work_func(struct work_struct *work) {
    // 延后处理
    printk(KERN_INFO "Work executed\n");
}

// 初始化工作
INIT_WORK(&my_work, my_work_func);

// 调度工作
schedule_work(&my_work);

// 延时工作
static struct delayed_work my_delayed_work;
INIT_DELAYED_WORK(&my_delayed_work, my_work_func);
schedule_delayed_work(&my_delayed_work, HZ);  // 1秒后执行
```

---

### 5.4 任务队列

```c
#include <linux/timer.h>

static struct timer_list my_timer;

static void my_timer_func(struct timer_list *t) {
    // 定时处理
    printk(KERN_INFO "Timer expired\n");
    
    // 重新启动定时器
    mod_timer(&my_timer, jiffies + HZ);
}

// 初始化定时器
timer_setup(&my_timer, my_timer_func, 0);

// 启动定时器
mod_timer(&my_timer, jiffies + HZ);

// 删除定时器
del_timer(&my_timer);
```

---

## 六、内存管理

### 6.1 内核内存分配

```c
#include <linux/slab.h>

// 分配内存
void *ptr = kmalloc(size, GFP_KERNEL);
void *ptr = kzalloc(size, GFP_KERNEL);  // 清零

// 释放内存
kfree(ptr);

// 分配大块内存
void *ptr = vmalloc(size);
vfree(ptr);
```

---

### 6.2 GFP标志

| 标志 | 说明 |
|------|------|
| GFP_KERNEL | 可睡眠分配 |
| GFP_ATOMIC | 原子分配，不可睡眠 |
| GFP_DMA | DMA内存 |
| GFP_HIGHMEM | 高端内存 |

---

### 6.3 DMA内存

```c
#include <linux/dma-mapping.h>

// 分配DMA缓冲区
void *dma_buf = dma_alloc_coherent(&pdev->dev, size, &dma_handle, GFP_KERNEL);

// 释放DMA缓冲区
dma_free_coherent(&pdev->dev, size, dma_buf, dma_handle);

// DMA映射
dma_addr_t dma_addr = dma_map_single(&pdev->dev, buf, size, DMA_TO_DEVICE);
dma_unmap_single(&pdev->dev, dma_addr, size, DMA_TO_DEVICE);
```

---

## 七、GPIO操作

### 7.1 GPIO API

```c
#include <linux/gpio.h>

// 请求GPIO
gpio_request(gpio_num, "my-gpio");

// 设置方向
gpio_direction_output(gpio_num, value);
gpio_direction_input(gpio_num);

// 读写GPIO
gpio_set_value(gpio_num, value);
int value = gpio_get_value(gpio_num);

// 释放GPIO
gpio_free(gpio_num);
```

---

### 7.2 设备树GPIO

```c
#include <linux/of_gpio.h>

// 获取GPIO
int gpio = of_get_named_gpio(np, "my,gpio", 0);
if (!gpio_is_valid(gpio)) {
    return -ENODEV;
}

// 请求和配置
gpio_request(gpio, "my-gpio");
gpio_direction_output(gpio, 0);
```

---

## 八、I2C驱动

### 8.1 I2C客户端驱动

```c
#include <linux/i2c.h>

static int my_i2c_probe(struct i2c_client *client,
                        const struct i2c_device_id *id) {
    // 读取寄存器
    u8 reg = 0x00;
    i2c_master_send(client, &reg, 1);
    i2c_master_recv(client, &val, 1);
    
    return 0;
}

static int my_i2c_remove(struct i2c_client *client) {
    return 0;
}

static const struct i2c_device_id my_i2c_id[] = {
    { "my-device", 0 },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(i2c, my_i2c_id);

static struct i2c_driver my_i2c_driver = {
    .driver = {
        .name = "my-i2c-driver",
        .of_match_table = my_of_match,
    },
    .probe = my_i2c_probe,
    .remove = my_i2c_remove,
    .id_table = my_i2c_id,
};
module_i2c_driver(my_i2c_driver);
```

---

### 8.2 I2C传输

```c
// 写寄存器
static int my_i2c_write_reg(struct i2c_client *client, u8 reg, u8 val) {
    u8 buf[2] = { reg, val };
    return i2c_master_send(client, buf, 2);
}

// 读寄存器
static int my_i2c_read_reg(struct i2c_client *client, u8 reg, u8 *val) {
    struct i2c_msg msgs[2];
    
    msgs[0].addr = client->addr;
    msgs[0].flags = 0;
    msgs[0].len = 1;
    msgs[0].buf = &reg;
    
    msgs[1].addr = client->addr;
    msgs[1].flags = I2C_M_RD;
    msgs[1].len = 1;
    msgs[1].buf = val;
    
    return i2c_transfer(client->adapter, msgs, 2);
}
```

---

## 九、SPI驱动

### 9.1 SPI设备驱动

```c
#include <linux/spi/spi.h>

static int my_spi_probe(struct spi_device *spi) {
    // 配置SPI
    spi->mode = SPI_MODE_0;
    spi->bits_per_word = 8;
    spi->max_speed_hz = 10000000;
    spi_setup(spi);
    
    return 0;
}

static const struct spi_device_id my_spi_id[] = {
    { "my-device", 0 },
    { /* sentinel */ }
};
MODULE_DEVICE_TABLE(spi, my_spi_id);

static struct spi_driver my_spi_driver = {
    .driver = {
        .name = "my-spi-driver",
        .of_match_table = my_of_match,
    },
    .probe = my_spi_probe,
    .remove = my_spi_remove,
    .id_table = my_spi_id,
};
module_spi_driver(my_spi_driver);
```

---

### 9.2 SPI传输

```c
// 同步传输
static int my_spi_transfer(struct spi_device *spi, u8 *tx, u8 *rx, int len) {
    struct spi_transfer t = {
        .tx_buf = tx,
        .rx_buf = rx,
        .len = len,
    };
    struct spi_message m;
    
    spi_message_init(&m);
    spi_message_add_tail(&t, &m);
    return spi_sync(spi, &m);
}
```

---

## 十、调试技巧

### 10.1 printk日志

```c
// 日志级别
printk(KERN_EMERG "Emergency message\n");
printk(KERN_ALERT "Alert message\n");
printk(KERN_CRIT "Critical message\n");
printk(KERN_ERR "Error message\n");
printk(KERN_WARNING "Warning message\n");
printk(KERN_NOTICE "Notice message\n");
printk(KERN_INFO "Info message\n");
printk(KERN_DEBUG "Debug message\n");

// 动态调试
pr_debug("Debug message\n");
dev_dbg(&pdev->dev, "Device debug message\n");
```

---

### 10.2 proc文件系统

```c
#include <linux/proc_fs.h>

static ssize_t my_proc_read(struct file *file, char __user *buf,
                            size_t count, loff_t *ppos) {
    char *data = "Hello from proc\n";
    return simple_read_from_buffer(buf, count, ppos, data, strlen(data));
}

static const struct proc_ops my_proc_ops = {
    .proc_read = my_proc_read,
};

// 创建proc文件
proc_create("mydevice", 0444, NULL, &my_proc_ops);

// 删除proc文件
remove_proc_entry("mydevice", NULL);
```

---

### 10.3 sysfs属性

```c
static ssize_t my_attr_show(struct device *dev,
                            struct device_attribute *attr, char *buf) {
    return sprintf(buf, "%d\n", my_value);
}

static ssize_t my_attr_store(struct device *dev,
                             struct device_attribute *attr,
                             const char *buf, size_t count) {
    sscanf(buf, "%d", &my_value);
    return count;
}

static DEVICE_ATTR(my_attr, 0664, my_attr_show, my_attr_store);

// 创建属性
device_create_file(&pdev->dev, &dev_attr_my_attr);

// 删除属性
device_remove_file(&pdev->dev, &dev_attr_my_attr);
```

---

## 附录：内核API速查表

### 模块管理

| API | 说明 |
|-----|------|
| module_init | 模块初始化函数 |
| module_exit | 模块退出函数 |
| MODULE_LICENSE | 许可证声明 |

### 字符设备

| API | 说明 |
|-----|------|
| alloc_chrdev_region | 分配设备号 |
| cdev_init | 初始化字符设备 |
| cdev_add | 添加字符设备 |
| class_create | 创建设备类 |
| device_create | 创建设备节点 |

### 内存管理

| API | 说明 |
|-----|------|
| kmalloc | 内核内存分配 |
| kfree | 释放内核内存 |
| vmalloc | 虚拟内存分配 |
| ioremap | IO内存映射 |

### 中断

| API | 说明 |
|-----|------|
| request_irq | 注册中断 |
| free_irq | 释放中断 |

### GPIO

| API | 说明 |
|-----|------|
| gpio_request | 请求GPIO |
| gpio_free | 释放GPIO |
| gpio_set_value | 设置GPIO值 |
| gpio_get_value | 获取GPIO值 |

---

## 相关链接

- [[Linux基础]] - Linux基础知识
- [[Linux系统编程]] - 系统调用
- [[设备树]] - 设备树详解
