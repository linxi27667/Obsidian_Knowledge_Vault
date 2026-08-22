# 嵌入式Linux驱动详解

## 核心概念

- **设备树** - 硬件描述
- **Platform设备** - 总线驱动模型
- **字符设备** - 用户空间接口
- **中断处理** - 上半部/下半部

---

## 一、设备树(Device Tree)

### 1.1 设备树语法

```dts
// 设备树源文件(.dts)
/dts-v1/;
/ {
    model = "My Embedded Board";
    compatible = "myvendor,myboard";

    chosen {
        bootargs = "console=ttyS0,115200 root=/dev/mmcblk0p2";
    };

    memory {
        reg = <0x80000000 0x20000000>;  // 512MB
    };

    cpus {
        cpu@0 {
            compatible = "arm,cortex-a7";
            reg = <0>;
        };
    };

    // UART
    uart0: serial@01C28000 {
        compatible = "snps,dw-apb-uart";
        reg = <0x01C28000 0x400>;
        interrupts = <0 1 4>;
        clocks = <&ccu CLK_BUS_UART0>;
        status = "okay";
    };

    // GPIO
    gpio0: gpio@01C20800 {
        compatible = "allwinner,sun7i-a20-pinctrl";
        reg = <0x01C20800 0x400>;
        interrupts = <0 11 4>;
        gpio-controller;
        #gpio-cells = <3>;
    };

    // LED
    leds {
        compatible = "gpio-leds";

        led0 {
            label = "status";
            gpios = <&gpio0 1 0>;  // PA1
            default-state = "off";
        };
    };

    // I2C
    i2c0: i2c@01C2AC00 {
        compatible = "allwinner,sun7i-a20-i2c";
        reg = <0x01C2AC00 0x400>;
        interrupts = <0 7 4>;
        clocks = <&ccu CLK_BUS_I2C0>;
        status = "okay";

        sensor@48 {
            compatible = "ti,tmp102";
            reg = <0x48>;
        };
    };
};
```

---

### 1.2 设备树解析

```c
// 内核中解析设备树
#include <linux/of.h>
#include <linux/of_device.h>

// 获取设备树属性
static int my_driver_probe(struct platform_device *pdev) {
    struct device_node *np = pdev->dev.of_node;
    u32 reg_base;
    int irq;

    // 获取reg属性
    if (of_property_read_u32(np, "reg", &reg_base)) {
        dev_err(&pdev->dev, "Failed to get reg\n");
        return -EINVAL;
    }

    // 获取中断号
    irq = platform_get_irq(pdev, 0);
    if (irq < 0) {
        dev_err(&pdev->dev, "Failed to get irq\n");
        return irq;
    }

    // 获取GPIO
    struct gpio_desc *led_gpio = devm_gpiod_get(&pdev->dev, "led", GPIOD_OUT_LOW);
    if (IS_ERR(led_gpio)) {
        dev_err(&pdev->dev, "Failed to get GPIO\n");
        return PTR_ERR(led_gpio);
    }

    // 获取时钟
    struct clk *clk = devm_clk_get(&pdev->dev, NULL);
    if (IS_ERR(clk)) {
        dev_err(&pdev->dev, "Failed to get clock\n");
        return PTR_ERR(clk);
    }
    clk_prepare_enable(clk);

    return 0;
}

// 设备树匹配表
static const struct of_device_id my_driver_of_match[] = {
    { .compatible = "myvendor,mydevice", },
    { /* sentinel */ },
};
MODULE_DEVICE_TABLE(of, my_driver_of_match);

static struct platform_driver my_driver = {
    .probe = my_driver_probe,
    .remove = my_driver_remove,
    .driver = {
        .name = "my-driver",
        .of_match_table = my_driver_of_match,
    },
};
module_platform_driver(my_driver);
```

---

## 二、Platform设备驱动

### 2.1 驱动框架

```c
// Platform驱动完整框架
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/io.h>
#include <linux/interrupt.h>

struct my_device {
    void __iomem *base;
    int irq;
    struct device *dev;
    struct cdev cdev;
    dev_t devno;
};

// 中断处理(上半部)
static irqreturn_t my_irq_handler(int irq, void *data) {
    struct my_device *mydev = data;
    u32 status;

    status = readl(mydev->base + STATUS_REG);

    if (status & IRQ_PENDING) {
        // 清除中断
        writel(status, mydev->base + STATUS_REG);
        return IRQ_HANDLED;
    }

    return IRQ_NONE;
}

// 探测函数
static int my_probe(struct platform_device *pdev) {
    struct my_device *mydev;
    struct resource *res;
    int ret;

    // 分配设备结构
    mydev = devm_kzalloc(&pdev->dev, sizeof(*mydev), GFP_KERNEL);
    if (!mydev) return -ENOMEM;

    mydev->dev = &pdev->dev;
    platform_set_drvdata(pdev, mydev);

    // 获取IO内存资源
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    mydev->base = devm_ioremap_resource(&pdev->dev, res);
    if (IS_ERR(mydev->base)) return PTR_ERR(mydev->base);

    // 获取中断
    mydev->irq = platform_get_irq(pdev, 0);
    if (mydev->irq < 0) return mydev->irq;

    ret = devm_request_irq(&pdev->dev, mydev->irq, my_irq_handler,
                           0, "my-device", mydev);
    if (ret) {
        dev_err(&pdev->dev, "Failed to request IRQ\n");
        return ret;
    }

    // 注册字符设备
    ret = alloc_chrdev_region(&mydev->devno, 0, 1, "my-device");
    if (ret) return ret;

    cdev_init(&mydev->cdev, &my_fops);
    ret = cdev_add(&mydev->cdev, mydev->devno, 1);
    if (ret) goto err_cdev;

    // 创建设备节点
    device_create(my_class, &pdev->dev, mydev->devno, NULL, "my-device");

    dev_info(&pdev->dev, "My device probed\n");
    return 0;

err_cdev:
    unregister_chrdev_region(mydev->devno, 1);
    return ret;
}

// 移除函数
static int my_remove(struct platform_device *pdev) {
    struct my_device *mydev = platform_get_drvdata(pdev);

    device_destroy(my_class, mydev->devno);
    cdev_del(&mydev->cdev);
    unregister_chrdev_region(mydev->devno, 1);

    dev_info(&pdev->dev, "My device removed\n");
    return 0;
}
```

---

## 三、字符设备

### 3.1 文件操作

```c
// 字符设备文件操作
static int my_open(struct inode *inode, struct file *filp) {
    struct my_device *mydev = container_of(inode->i_cdev,
                                           struct my_device, cdev);
    filp->private_data = mydev;
    return 0;
}

static int my_release(struct inode *inode, struct file *filp) {
    return 0;
}

static ssize_t my_read(struct file *filp, char __user *buf,
                       size_t count, loff_t *f_pos) {
    struct my_device *mydev = filp->private_data;
    u32 data;

    // 从硬件读取
    data = readl(mydev->base + DATA_REG);

    // 复制到用户空间
    if (copy_to_user(buf, &data, sizeof(data))) {
        return -EFAULT;
    }

    return sizeof(data);
}

static ssize_t my_write(struct file *filp, const char __user *buf,
                        size_t count, loff_t *f_pos) {
    struct my_device *mydev = filp->private_data;
    u32 data;

    if (copy_from_user(&data, buf, sizeof(data))) {
        return -EFAULT;
    }

    // 写入硬件
    writel(data, mydev->base + DATA_REG);

    return sizeof(data);
}

static long my_ioctl(struct file *filp, unsigned int cmd, unsigned long arg) {
    struct my_device *mydev = filp->private_data;

    switch (cmd) {
        case MY_IOCTL_RESET:
            writel(RESET_BIT, mydev->base + CTRL_REG);
            break;
        case MY_IOCTL_SET_MODE:
            if (arg > MODE_MAX) return -EINVAL;
            writel(arg, mydev->base + MODE_REG);
            break;
        default:
            return -ENOTTY;
    }
    return 0;
}

// mmap实现(用户空间直接访问硬件)
static int my_mmap(struct file *filp, struct vm_area_struct *vma) {
    struct my_device *mydev = filp->private_data;
    unsigned long size = vma->vm_end - vma->vm_start;

    if (size > RESOURCE_SIZE) return -EINVAL;

    vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);

    if (io_remap_pfn_range(vma, vma->vm_start,
                           mydev->phys_base >> PAGE_SHIFT,
                           size, vma->vm_page_prot)) {
        return -EAGAIN;
    }

    return 0;
}

static const struct file_operations my_fops = {
    .owner = THIS_MODULE,
    .open = my_open,
    .release = my_release,
    .read = my_read,
    .write = my_write,
    .unlocked_ioctl = my_ioctl,
    .mmap = my_mmap,
};
```

---

## 四、中断处理

### 4.1 中断下半部

```c
// 工作队列(下半部)
static struct workqueue_struct *my_wq;
static struct work_struct my_work;

static void my_work_func(struct work_struct *work) {
    struct my_device *mydev = container_of(work, struct my_device, work);

    // 处理耗时操作
    process_data(mydev);
}

static irqreturn_t my_irq_handler(int irq, void *data) {
    struct my_device *mydev = data;

    // 上半部: 快速处理
    u32 status = readl(mydev->base + STATUS_REG);
    writel(status, mydev->base + STATUS_REG);  // 清除中断

    // 调度下半部
    queue_work(my_wq, &my_work);

    return IRQ_HANDLED;
}

// Tasklet(轻量级下半部)
static struct tasklet_struct my_tasklet;

static void my_tasklet_func(unsigned long data) {
    struct my_device *mydev = (struct my_device *)data;
    // 快速处理
}

static irqreturn_t my_irq_handler_tasklet(int irq, void *data) {
    struct my_device *mydev = data;

    tasklet_schedule(&my_tasklet);

    return IRQ_HANDLED;
}
```

---

## 五、DMA传输

### 5.1 DMA框架

```c
// DMA传输
#include <linux/dma-mapping.h>

struct my_dma_desc {
    dma_addr_t dma_handle;
    void *virt_addr;
    size_t size;
};

static int my_dma_init(struct my_device *mydev) {
    struct my_dma_desc *desc;

    desc = devm_kzalloc(mydev->dev, sizeof(*desc), GFP_KERNEL);

    // 分配DMA缓冲区
    desc->size = 4096;
    desc->virt_addr = dma_alloc_coherent(mydev->dev, desc->size,
                                          &desc->dma_handle, GFP_KERNEL);
    if (!desc->virt_addr) {
        dev_err(mydev->dev, "DMA alloc failed\n");
        return -ENOMEM;
    }

    return 0;
}

// DMA传输
static void my_dma_transfer(struct my_device *mydev,
                            dma_addr_t src, dma_addr_t dst, size_t len) {
    // 配置DMA控制器
    writel(src, mydev->base + DMA_SRC_REG);
    writel(dst, mydev->base + DMA_DST_REG);
    writel(len, mydev->base + DMA_LEN_REG);

    // 启动传输
    writel(DMA_START, mydev->base + DMA_CTRL_REG);
}

// SG-DMA(分散聚集)
static int my_sg_dma_transfer(struct my_device *mydev,
                              struct scatterlist *sg, int nents) {
    struct dma_chan *chan = mydev->dma_chan;
    struct dma_async_tx_descriptor *desc;
    dma_cookie_t cookie;

    desc = dmaengine_prep_slave_sg(chan, sg, nents,
                                   DMA_MEM_TO_DEV,
                                   DMA_PREP_INTERRUPT | DMA_CTRL_ACK);
    if (!desc) return -ENOMEM;

    cookie = dmaengine_submit(desc);
    dma_async_issue_pending(chan);

    return 0;
}
```

---

## 六、IIO子系统

### 6.1 IIO设备

```c
// IIO(Industrial I/O)设备驱动
#include <linux/iio/iio.h>
#include <linux/iio/sysfs.h>

static const struct iio_chan_spec my_iio_channels[] = {
    {
        .type = IIO_VOLTAGE,
        .indexed = 1,
        .channel = 0,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW),
        .info_mask_shared_by_type = BIT(IIO_CHAN_INFO_SCALE),
    },
    {
        .type = IIO_TEMP,
        .indexed = 1,
        .channel = 0,
        .info_mask_separate = BIT(IIO_CHAN_INFO_RAW) |
                              BIT(IIO_CHAN_INFO_OFFSET) |
                              BIT(IIO_CHAN_INFO_SCALE),
    },
};

static int my_iio_read_raw(struct iio_dev *indio_dev,
                           struct iio_chan_spec const *chan,
                           int *val, int *val2, long mask) {
    struct my_device *mydev = iio_priv(indio_dev);

    switch (mask) {
        case IIO_CHAN_INFO_RAW:
            *val = readl(mydev->base + DATA_REG);
            return IIO_VAL_INT;

        case IIO_CHAN_INFO_SCALE:
            *val = 3300;  // 3.3V
            *val2 = 12;   // 12位
            return IIO_VAL_FRACTIONAL_LOG2;

        case IIO_CHAN_INFO_OFFSET:
            *val = -500;  // 偏移量
            return IIO_VAL_INT;
    }

    return -EINVAL;
}

static const struct iio_info my_iio_info = {
    .read_raw = my_iio_read_raw,
};

static int my_iio_probe(struct platform_device *pdev) {
    struct iio_dev *indio_dev;
    struct my_device *mydev;

    indio_dev = devm_iio_device_alloc(&pdev->dev, sizeof(*mydev));
    if (!indio_dev) return -ENOMEM;

    mydev = iio_priv(indio_dev);
    indio_dev->name = "my-adc";
    indio_dev->info = &my_iio_info;
    indio_dev->channels = my_iio_channels;
    indio_dev->num_channels = ARRAY_SIZE(my_iio_channels);
    indio_dev->modes = INDIO_DIRECT_MODE;

    return devm_iio_device_register(&pdev->dev, indio_dev);
}
```

---

## 附录：内核API速查

| API | 用途 |
|-----|------|
| devm_kzalloc | 内存分配(设备管理) |
| devm_ioremap | IO内存映射 |
| platform_get_resource | 获取资源 |
| devm_request_irq | 申请中断 |
| dma_alloc_coherent | DMA缓冲区 |
| copy_to_user | 内核→用户 |
| copy_from_user | 用户→内核 |

---

## 相关链接

- [[Linux驱动开发]] - 驱动基础
- [[Linux基础]] - Linux系统
- [[操作系统原理]] - 内核原理
- [[嵌入式Linux]] - 嵌入式Linux
