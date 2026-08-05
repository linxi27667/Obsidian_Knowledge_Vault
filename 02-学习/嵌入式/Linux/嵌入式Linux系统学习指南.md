# 嵌入式Linux系统学习指南

> **核心概念**：内核架构、设备驱动、设备树、构建系统、U-Boot、根文件系统、交叉编译、调试
>
> 本笔记覆盖嵌入式Linux开发全流程，从内核基础到驱动开发、构建系统、调试技巧，适合系统性学习与日常查阅。

---

## 目录

- [[#1. Linux内核基础]]
- [[#2. 字符设备驱动]]
- [[#3. 设备树(Device Tree)]]
- [[#4. 中断处理]]
- [[#5. 并发与同步]]
- [[#6. 内存管理]]
- [[#7. 构建系统]]
- [[#8. Linux内核调试]]
- [[#9. 常用外设驱动框架]]
- [[#10. 嵌入式Linux常用平台]]
- [[#11. 开发流程总结]]

---

## 1. Linux内核基础

### 1.1 内核架构

#### 宏内核 vs 微内核

| 特性 | 宏内核 (Monolithic) | 微内核 (Microkernel) |
|------|---------------------|---------------------|
| 代表 | Linux | QNX, Minix, Zircon |
| 内核空间 | 所有核心服务运行在内核态 | 仅最基础服务在内核态 |
| 性能 | 高（无频繁上下文切换） | 相对较低（IPC开销） |
| 稳定性 | 一个模块崩溃可能影响整个内核 | 模块隔离，故障恢复能力强 |
| 可扩展性 | 通过LKM动态加载 | 天然模块化 |
| 实际应用 | 最广泛的嵌入式/服务器OS | 安全关键系统、航空航天 |

> Linux采用宏内核架构，但通过可加载内核模块(LKM)机制获得了类似微内核的灵活性。

#### 用户空间与内核空间

```
┌─────────────────────────────────────────┐
│            用户空间 (User Space)          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ 应用程序 │ │  库函数  │ │  Shell  │   │
│  └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │         │
│  ═════╪═══════════╪═══════════╪══════   │  ← 系统调用接口 (System Call Interface)
│       │           │           │         │
│  ┌────┴───────────┴───────────┴────┐    │
│  │         内核空间 (Kernel Space)   │    │
│  │  ┌──────────┐  ┌──────────┐    │    │
│  │  │ 进程调度  │  │ 内存管理  │    │    │
│  │  ├──────────┤  ├──────────┤    │    │
│  │  │ 文件系统  │  │ 设备驱动  │    │    │
│  │  ├──────────┤  ├──────────┤    │    │
│  │  │ 网络协议栈│  │ 中断处理  │    │    │
│  │  └──────────┘  └──────────┘    │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**地址空间划分**（以32位ARM为例）：
- 用户空间：0x00000000 - 0xBFFFFFFF（3GB）
- 内核空间：0xC0000000 - 0xFFFFFFFF（1GB）

**保护机制**：
- CPU运行级别区分（ARM的PL0/PL1，x86的Ring0/Ring3）
- MMU页表权限位控制
- 用户态无法直接访问内核态内存

#### 系统调用接口

系统调用是用户空间访问内核服务的唯一合法途径：

```c
// 系统调用示例：write
#include <unistd.h>

ssize_t ret = write(fd, buf, count);
// 实际执行过程：
// 1. 将系统调用号放入寄存器(r7 for ARM, eax for x86)
// 2. 参数放入指定寄存器
// 3. 执行特殊指令触发软中断(svc #0 for ARM, int 0x80 for x86)
// 4. CPU切换到内核态，跳转到系统调用处理函数
// 5. 内核执行对应服务例程
// 6. 返回用户空间
```

**常用系统调用分类**：

| 类别 | 系统调用 |
|------|---------|
| 文件操作 | open, close, read, write, lseek, ioctl, mmap |
| 进程管理 | fork, exec, exit, wait, kill, getpid |
| 内存管理 | brk, mmap, munmap, mprotect |
| 网络 | socket, bind, listen, accept, connect, send, recv |
| 时间 | clock_gettime, nanosleep, timer_create |
| 信号 | signal, sigaction, sigprocmask |

#### 内核子系统概览

**进程管理**：
- 进程描述符 `task_struct`（定义在 `include/linux/sched.h`）
- CFS调度器（完全公平调度）
- 实时调度策略：SCHED_FIFO, SCHED_RR
- 进程状态：TASK_RUNNING, TASK_INTERRUPTIBLE, TASK_UNINTERRUPTIBLE, TASK_STOPPED, TASK_ZOMBIE

**内存管理**：
- 页式内存管理（4KB标准页，支持大页）
- 伙伴系统（Buddy System）管理物理页
- SLAB/SLUB分配器管理小对象
- 虚拟内存映射（vmalloc, kmalloc区别）
- 页表管理（PGD/PUD/PMD/PTE四级页表）

**文件系统**：
- VFS（虚拟文件系统）层抽象
- 支持ext4, btrfs, squashfs, jffs2, yaffs2, tmpfs等
- 嵌入式常用：squashfs（只读压缩）、jffs2/yaffs2（Flash友好）、ext4（eMMC/SSD）

**网络协议栈**：
- Socket层 → 传输层(TCP/UDP) → 网络层(IP) → 链路层
- Netfilter框架（防火墙、NAT）
- 网络设备驱动

### 1.2 内核模块

#### 可加载内核模块(LKM)概念

内核模块是运行在内核空间的代码，可以在运行时动态加载和卸载，无需重新编译整个内核。

**优势**：
- 减小内核镜像体积（对嵌入式至关重要）
- 开发调试效率高（不需要每次重启）
- 按需加载，节省内存

**劣势**：
- 模块代码与内核耦合，版本不匹配会出问题
- 增加系统攻击面

#### 模块基础代码结构

```c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>

// 模块初始化函数
static int __init my_module_init(void)
{
    pr_info("my_module: loaded\n");
    return 0;  // 返回0表示成功，非0表示失败
}

// 模块退出函数
static void __exit my_module_exit(void)
{
    pr_info("my_module: unloaded\n");
}

module_init(my_module_init);
module_exit(my_module_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("A simple kernel module");
MODULE_VERSION("1.0");
```

**关键宏说明**：

| 宏 | 作用 |
|---|------|
| `__init` | 标记初始化函数，加载完成后释放该函数占用的内存 |
| `__exit` | 标记退出函数，静态编译进内核时忽略此函数 |
| `module_init()` | 注册模块入口点 |
| `module_exit()` | 注册模块出口点 |
| `MODULE_LICENSE()` | 声明许可证，GPL许可证才能使用EXPORT_SYMBOL_GPL导出的符号 |

#### 模块参数

```c
#include <moduleparam.h>

static int count = 1;
module_param(count, int, 0644);
MODULE_PARM_DESC(count, "Number of devices to create");

static char *name = "default";
module_param(name, charp, 0644);
MODULE_PARM_DESC(name, "Device name");

static int arr[3] = {1, 2, 3};
module_param_array(arr, int, NULL, 0644);
MODULE_PARM_DESC(arr, "Array of values");
```

**权限说明**：
- `0644`：所有者可读写，其他人只读（出现在 `/sys/module/<name>/parameters/`）
- `0444`：只读
- `0666`：所有人可读写（不推荐）

#### 模块编译Makefile

**单文件模块**：

```makefile
obj-m := my_module.o

KDIR := /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean
```

**多文件模块**：

```makefile
obj-m := my_driver.o
my_driver-objs := main.o helper.o utils.o

KDIR := /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean
```

**交叉编译模块**：

```makefile
obj-m := my_module.o

KDIR := /path/to/kernel/source  # 目标板内核源码路径

ARCH := arm64
CROSS_COMPILE := aarch64-linux-gnu-

all:
	make -C $(KDIR) M=$(PWD) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) modules

clean:
	make -C $(KDIR) M=$(PWD) clean
```

#### 模块管理命令

```bash
# 加载模块
insmod my_module.ko
insmod my_module.ko count=5 name="mydev"

# 卸载模块
rmmod my_module

# 查看已加载模块
lsmod
# 输出格式：Module  Size  Used by
# Used by列显示哪些模块依赖此模块

# 自动加载（处理依赖关系）
modprobe my_module
# 会自动加载依赖模块，查找 /lib/modules/<version>/ 目录

# 卸载（自动处理依赖）
modprobe -r my_module

# 查看模块信息
modinfo my_module.ko

# 查看模块参数
cat /sys/module/my_module/parameters/count

# 运行时修改参数
echo 10 > /sys/module/my_module/parameters/count
```

### 1.3 内核源码目录结构

```
linux/
├── arch/           # 体系结构相关代码（arm, arm64, x86等）
├── block/          # 块设备层
├── crypto/         # 加密算法
├── Documentation/  # 内核文档
├── drivers/        # 设备驱动（最大的目录）
│   ├── gpio/
│   ├── i2c/
│   ├── spi/
│   ├── input/
│   ├── net/
│   ├── gpu/
│   └── ...
├── fs/             # 文件系统
├── include/        # 头文件
│   ├── linux/
│   ├── asm-generic/
│   └── uapi/
├── init/           # 内核初始化代码
├── ipc/            # 进程间通信
├── kernel/         # 核心子系统（调度、信号等）
├── lib/            # 内核库函数
├── mm/             # 内存管理
├── net/            # 网络协议栈
├── scripts/        # 构建脚本、工具
├── security/       # 安全模块（SELinux等）
├── sound/          # 音频子系统
├── tools/          # 用户空间工具
├── usr/            # initramfs相关
├── virt/           # 虚拟化支持
├── Kconfig         # 顶层Kconfig
├── Makefile        # 顶层Makefile
└── .config         # 当前内核配置
```

---

## 2. 字符设备驱动

### 2.1 设备号

#### 主设备号与次设备号

Linux通过设备号标识设备：
- **主设备号(major)**：标识设备类型/驱动程序
- **次设备号(minor)**：标识同一驱动下的具体设备实例

设备号类型为 `dev_t`（32位），高12位为主设备号，低20位为次设备号：

```c
#include <linux/kdev_t.h>

dev_t devno = MKDEV(major, minor);  // 组合
int major_num = MAJOR(devno);       // 提取主设备号
int minor_num = MINOR(devno);       // 提取次设备号
```

#### 设备号分配

**静态分配**（指定设备号）：

```c
dev_t devno = MKDEV(200, 0);
int ret = register_chrdev_region(devno, count, "my_device");
// count: 设备数量（连续的次设备号）
// 成功返回0，失败返回负错误码
```

**动态分配**（推荐）：

```c
dev_t devno;
int ret = alloc_chrdev_region(&devno, 0, count, "my_device");
// 第二个参数：起始次设备号
// 内核自动分配一个未使用的主设备号
// 查看分配结果：cat /proc/devices
```

**释放设备号**：

```c
unregister_chrdev_region(devno, count);
```

### 2.2 字符设备注册

#### cdev结构体

```c
#include <linux/cdev.h>

struct cdev {
    struct kobject kobj;           // 内嵌kobject
    struct module *owner;          // 所属模块
    const struct file_operations *ops;  // 文件操作集
    struct list_head list;         // 设备链表
    dev_t dev;                     // 设备号
    unsigned int count;            // 设备数量
};
```

#### file_operations结构体

```c
struct file_operations {
    struct module *owner;
    loff_t (*llseek)(struct file *, loff_t, int);
    ssize_t (*read)(struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write)(struct file *, const char __user *, size_t, loff_t *);
    __poll_t (*poll)(struct file *, struct poll_table_struct *);
    long (*unlocked_ioctl)(struct file *, unsigned int, unsigned long);
    int (*mmap)(struct file *, struct vm_area_struct *);
    int (*open)(struct inode *, struct file *);
    int (*release)(struct inode *, struct file *);
    int (*fasync)(int, struct file *, int);
    // ... 更多字段
};
```

#### 注册流程

```c
#include <linux/cdev.h>
#include <linux/fs.h>

static dev_t devno;
static struct cdev my_cdev;

static const struct file_operations my_fops = {
    .owner = THIS_MODULE,
    .open = my_open,
    .release = my_release,
    .read = my_read,
    .write = my_write,
    .unlocked_ioctl = my_ioctl,
};

static int __init my_init(void)
{
    int ret;

    // 1. 分配设备号
    ret = alloc_chrdev_region(&devno, 0, 1, "my_device");
    if (ret < 0) {
        pr_err("alloc_chrdev_region failed\n");
        return ret;
    }

    // 2. 初始化cdev
    cdev_init(&my_cdev, &my_fops);
    my_cdev.owner = THIS_MODULE;

    // 3. 添加cdev到内核
    ret = cdev_add(&my_cdev, devno, 1);
    if (ret < 0) {
        pr_err("cdev_add failed\n");
        goto err_cdev_add;
    }

    pr_info("my_device: registered with major %d\n", MAJOR(devno));
    return 0;

err_cdev_add:
    unregister_chrdev_region(devno, 1);
    return ret;
}

static void __exit my_exit(void)
{
    cdev_del(&my_cdev);
    unregister_chrdev_region(devno, 1);
}
```

#### 设备节点创建

**手动创建**：

```bash
# 查看主设备号
cat /proc/devices | grep my_device

# 创建设备节点
mknod /dev/my_device c 200 0
# c: 字符设备, 200: 主设备号, 0: 次设备号
```

**自动创建（推荐）**：

```c
#include <linux/device.h>

static struct class *my_class;
static struct device *my_device;

static int __init my_init(void)
{
    // ... 前面的设备号分配和cdev注册 ...

    // 创建设备类
    my_class = class_create(THIS_MODULE, "my_class");
    if (IS_ERR(my_class)) {
        ret = PTR_ERR(my_class);
        goto err_class;
    }

    // 创建设备节点（自动创建/dev/my_device）
    my_device = device_create(my_class, NULL, devno, NULL, "my_device");
    if (IS_ERR(my_device)) {
        ret = PTR_ERR(my_device);
        goto err_device;
    }

    return 0;

err_device:
    class_destroy(my_class);
err_class:
    cdev_del(&my_cdev);
    unregister_chrdev_region(devno, 1);
    return ret;
}

static void __exit my_exit(void)
{
    device_destroy(my_class, devno);
    class_destroy(my_class);
    cdev_del(&my_cdev);
    unregister_chrdev_region(devno, 1);
}
```

**class_create / device_create 对应关系**：

```
/sys/class/my_class/          ← class_create 创建
/sys/class/my_class/my_device ← device_create 创建（符号链接到设备）
/dev/my_device                ← device_create 自动创建
```

### 2.3 重要file_operations详解

#### open / release

```c
static int my_open(struct inode *inode, struct file *filp)
{
    struct my_device *dev;

    // 从inode获取cdev，再获取自定义设备结构体
    dev = container_of(inode->i_cdev, struct my_device, cdev);
    filp->private_data = dev;  // 保存到file的私有数据

    // 初始化设备、加锁等
    pr_info("my_device: opened\n");
    return 0;
}

static int my_release(struct inode *inode, struct file *filp)
{
    pr_info("my_device: closed\n");
    return 0;
}
```

#### read / write

```c
static ssize_t my_read(struct file *filp, char __user *buf,
                        size_t count, loff_t *f_pos)
{
    struct my_device *dev = filp->private_data;
    ssize_t ret = 0;

    // 参数检查
    if (count == 0)
        return 0;

    // 从设备读取数据到内核缓冲区
    // ...

    // 将数据拷贝到用户空间
    if (copy_to_user(buf, dev->buffer + *f_pos, count)) {
        ret = -EFAULT;
        goto out;
    }

    *f_pos += count;
    ret = count;

out:
    return ret;
}

static ssize_t my_write(struct file *filp, const char __user *buf,
                         size_t count, loff_t *f_pos)
{
    struct my_device *dev = filp->private_data;
    ssize_t ret = 0;

    if (count == 0)
        return 0;

    // 从用户空间拷贝数据到内核缓冲区
    if (copy_from_user(dev->buffer + *f_pos, buf, count)) {
        ret = -EFAULT;
        goto out;
    }

    *f_pos += count;
    ret = count;

out:
    return ret;
}
```

**关键要点**：
- 用户空间指针不能直接解引用，必须用 `copy_to_user` / `copy_from_user`
- 这两个函数会检查指针合法性，并处理页缺失
- 返回值：成功返回实际传输字节数，失败返回负错误码

#### unlocked_ioctl

```c
// 定义ioctl命令
#define MY_IOC_MAGIC 'k'
#define MY_IOCRESET    _IO(MY_IOC_MAGIC, 0)
#define MY_IOCSETVAL   _IOW(MY_IOC_MAGIC, 1, int)
#define MY_IOCGETVAL   _IOR(MY_IOC_MAGIC, 2, int)
#define MY_IOCXCHGVAL  _IOWR(MY_IOC_MAGIC, 3, int)

static long my_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
    struct my_device *dev = filp->private_data;
    int val, ret = 0;

    // 检查magic number
    if (_IOC_TYPE(cmd) != MY_IOC_MAGIC)
        return -ENOTTY;

    switch (cmd) {
    case MY_IOCRESET:
        dev->value = 0;
        break;

    case MY_IOCSETVAL:
        if (copy_from_user(&val, (int __user *)arg, sizeof(val)))
            return -EFAULT;
        dev->value = val;
        break;

    case MY_IOCGETVAL:
        val = dev->value;
        if (copy_to_user((int __user *)arg, &val, sizeof(val)))
            return -EFAULT;
        break;

    case MY_IOCXCHGVAL:
        if (copy_from_user(&val, (int __user *)arg, sizeof(val)))
            return -EFAULT;
        ret = dev->value;
        dev->value = val;
        if (copy_to_user((int __user *)arg, &ret, sizeof(ret)))
            return -EFAULT;
        break;

    default:
        return -ENOTTY;
    }

    return 0;
}
```

**ioctl命令编码规则**：

```
bits 31-30: 方向（_IOC_NONE=0, _IOC_WRITE=1, _IOC_READ=2, _IOC_READ|_IOC_WRITE=3）
bits 29-16: 数据大小
bits 15-8:  类型(magic number)
bits 7-0:   命令序号
```

**ioctl宏**：

| 宏 | 用途 |
|----|------|
| `_IO(type, nr)` | 无数据传输 |
| `_IOW(type, nr, datatype)` | 写数据到内核 |
| `_IOR(type, nr, datatype)` | 从内核读数据 |
| `_IOWR(type, nr, datatype)` | 双向数据传输 |

#### poll

```c
static __poll_t my_poll(struct file *filp, poll_table *wait)
{
    struct my_device *dev = filp->private_data;
    __poll_t mask = 0;

    // 将等待队列加入poll_table
    poll_wait(filp, &dev->wait_queue, wait);

    // 检查是否有数据可读
    if (dev->data_ready)
        mask |= POLLIN | POLLRDNORM;

    // 检查是否可写
    if (dev->writable)
        mask |= POLLOUT | POLLWRNORM;

    return mask;
}
```

#### mmap

```c
static int my_mmap(struct file *filp, struct vm_area_struct *vma)
{
    struct my_device *dev = filp->private_data;
    unsigned long size = vma->vm_end - vma->vm_start;

    if (size > dev->buffer_size)
        return -EINVAL;

    // 将内核物理内存映射到用户空间
    if (remap_pfn_range(vma, vma->vm_start,
                        virt_to_phys(dev->buffer) >> PAGE_SHIFT,
                        size, vma->vm_page_prot)) {
        return -EAGAIN;
    }

    return 0;
}
```

### 2.4 完整代码示例

#### 最简字符设备驱动

```c
/*
 * minimal_chardev.c - 最简字符设备驱动
 * 功能：支持open/close/read/write，使用内核缓冲区
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/uaccess.h>

#define DEVICE_NAME "minimal_chardev"
#define BUFFER_SIZE 1024

static dev_t devno;
static struct cdev cdev;
static struct class *cls;
static struct device *dev;
static char buffer[BUFFER_SIZE];
static size_t data_len;

static int my_open(struct inode *inode, struct file *filp)
{
    return 0;
}

static int my_release(struct inode *inode, struct file *filp)
{
    return 0;
}

static ssize_t my_read(struct file *filp, char __user *buf,
                       size_t count, loff_t *f_pos)
{
    if (*f_pos >= data_len)
        return 0;

    if (*f_pos + count > data_len)
        count = data_len - *f_pos;

    if (copy_to_user(buf, buffer + *f_pos, count))
        return -EFAULT;

    *f_pos += count;
    return count;
}

static ssize_t my_write(struct file *filp, const char __user *buf,
                        size_t count, loff_t *f_pos)
{
    if (count > BUFFER_SIZE)
        count = BUFFER_SIZE;

    if (copy_from_user(buffer, buf, count))
        return -EFAULT;

    data_len = count;
    *f_pos = 0;
    return count;
}

static const struct file_operations fops = {
    .owner   = THIS_MODULE,
    .open    = my_open,
    .release = my_release,
    .read    = my_read,
    .write   = my_write,
};

static int __init minimal_init(void)
{
    int ret;

    ret = alloc_chrdev_region(&devno, 0, 1, DEVICE_NAME);
    if (ret)
        return ret;

    cdev_init(&cdev, &fops);
    ret = cdev_add(&cdev, devno, 1);
    if (ret)
        goto err_cdev;

    cls = class_create(THIS_MODULE, DEVICE_NAME);
    if (IS_ERR(cls)) {
        ret = PTR_ERR(cls);
        goto err_class;
    }

    dev = device_create(cls, NULL, devno, NULL, DEVICE_NAME);
    if (IS_ERR(dev)) {
        ret = PTR_ERR(dev);
        goto err_device;
    }

    pr_info("%s: loaded\n", DEVICE_NAME);
    return 0;

err_device:
    class_destroy(cls);
err_class:
    cdev_del(&cdev);
err_cdev:
    unregister_chrdev_region(devno, 1);
    return ret;
}

static void __exit minimal_exit(void)
{
    device_destroy(cls, devno);
    class_destroy(cls);
    cdev_del(&cdev);
    unregister_chrdev_region(devno, 1);
    pr_info("%s: unloaded\n", DEVICE_NAME);
}

module_init(minimal_init);
module_exit(minimal_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Minimal character device driver");
```

**用户空间测试程序**：

```c
/* test_chardev.c */
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

int main(void)
{
    int fd;
    char buf[64];

    fd = open("/dev/minimal_chardev", O_RDWR);
    if (fd < 0) {
        perror("open");
        return 1;
    }

    write(fd, "Hello Kernel!", 13);

    lseek(fd, 0, SEEK_SET);

    read(fd, buf, sizeof(buf));
    printf("Read from kernel: %s\n", buf);

    close(fd);
    return 0;
}
```

---

## 3. 设备树(Device Tree)

### 3.1 设备树基础

#### 什么是设备树

设备树是一种描述硬件拓扑的数据结构，来源于Open Firmware(OF)标准。它将硬件信息从内核源码中分离出来，以二进制格式传递给内核。

**三种文件形式**：

| 文件类型 | 扩展名 | 说明 |
|----------|--------|------|
| DTS | `.dts` | Device Tree Source，人类可读的源文件 |
| DTSI | `.dtsi` | Device Tree Source Include，可被其他dts包含的头文件 |
| DTB | `.dtb` | Device Tree Blob，编译后的二进制文件 |
| DTC | — | Device Tree Compiler，编译工具 |

**编译流程**：

```bash
# DTS → DTB
dtc -I dts -O dtb -o output.dtb input.dts

# DTB → DTS（反编译）
dtc -I dtb -O dts -o output.dts input.dtb

# 内核构建系统会自动编译DTS
make dtbs
```

#### 设备树的必要性

**Before Device Tree**（ARM Linux 3.x之前）：
- 板级信息写在C代码中（`arch/arm/mach-xxx/`）
- 每新增一块板子就要修改内核源码
- 大量重复代码，维护困难

**After Device Tree**：
- 硬件描述与内核代码完全分离
- 同一内核镜像支持多种板子
- 只需修改DTS文件即可适配新硬件

#### 设备树语法

```dts
/ {
    /* 根节点 */
    model = "My Board";
    compatible = "vendor,my-board";

    chosen {
        bootargs = "console=ttyS0,115200 root=/dev/mmcblk0p2";
    };

    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x40000000>;  /* 1GB */
    };

    cpus {
        #address-cells = <1>;
        #size-cells = <0>;

        cpu@0 {
            device_type = "cpu";
            compatible = "arm,cortex-a53";
            reg = <0>;
        };

        cpu@1 {
            device_type = "cpu";
            compatible = "arm,cortex-a53";
            reg = <1>;
        };
    };

    /* 使用标签引用 */
    aliases {
        serial0 = &uart0;
        spi0 = &spi0;
    };

    /* 外设节点 */
    soc {
        compatible = "simple-bus";
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;

        uart0: serial@01c28000 {
            compatible = "snps,dw-apb-uart";
            reg = <0x0 0x01c28000 0x0 0x400>;
            interrupts = <GIC_SPI 1 IRQ_TYPE_LEVEL_HIGH>;
            clocks = <&ccu CLK_BUS_UART0>;
            status = "okay";
        };
    };
};
```

**语法要点**：

| 元素 | 说明 | 示例 |
|------|------|------|
| 节点 | 用 `{}` 包围，格式 `node-name@unit-address` | `serial@01c28000 {}` |
| 属性 | `name = value;` | `reg = <0x01c28000 0x400>;` |
| 标签 | `label: node-name {}` | `uart0: serial@01c28000 {}` |
| 引用 | `&label` | `&uart0` |
| compatible | 字符串或字符串列表 | `"vendor,device"` |
| reg | 地址+大小（取决于#address-cells和#size-cells） | `<0x01c28000 0x400>` |
| status | 设备状态 | `"okay"` / `"disabled"` |

**属性值类型**：

```dts
/* 空属性 */
boot-active;

/* 字符串 */
compatible = "vendor,device";

/* 字符串列表 */
compatible = "vendor,device-v2", "vendor,device";

/* 32位整数 */
#address-cells = <1>;

/* 32位整数数组 */
reg = <0x80000000 0x40000000>;

/* 字节数组 */
local-mac-address = [00 11 22 33 44 55];

/* 混合类型 */
mixed = "string", <0x1234>, [aa bb];
```

#### compatible属性匹配机制

compatible是设备树中最关键的属性，它决定了哪个驱动程序将处理该设备：

```
设备树节点                          内核驱动
compatible = "vendor,device-v2"    ←→  .of_match_table
         "vendor,device"           ←→  匹配项列表
```

```c
/* 驱动中的匹配表 */
static const struct of_device_id my_driver_of_match[] = {
    { .compatible = "vendor,device-v2", },
    { .compatible = "vendor,device", },
    { /* sentinel */ },
};
MODULE_DEVICE_TABLE(of, my_driver_of_match);

static struct platform_driver my_driver = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my_driver",
        .of_match_table = my_driver_of_match,
    },
};
```

**匹配规则**：
1. 内核遍历设备树中的所有节点
2. 对每个节点的compatible属性，查找匹配的驱动
3. 优先匹配列表中靠前的compatible字符串
4. 一个节点可以有多个compatible，一个驱动也可以匹配多个compatible

### 3.2 设备树常用节点

#### chosen节点

```dts
chosen {
    bootargs = "console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait earlycon";
    stdout-path = &uart0;
    # 自定义属性也可传递
    my-param = "value";
};
```

**bootargs常用参数**：

| 参数 | 说明 |
|------|------|
| `console=ttyS0,115200` | 控制台串口及波特率 |
| `root=/dev/mmcblk0p2` | 根文件系统设备 |
| `rootwait` | 等待根设备就绪 |
| `earlycon` | 早期控制台（调试用） |
| `init=/sbin/init` | 指定init程序 |
| `mem=512M` | 限制可用内存 |
| `loglevel=7` | 内核日志级别 |

#### pinctrl节点

```dts
pinctrl: pinctrl@01c20800 {
    compatible = "allwinner,sun50i-h616-pinctrl";
    reg = <0x0 0x01c20800 0x0 0x400>;

    uart0_pins: uart0-pins {
        pins = "PH0", "PH1";
        function = "uart0";
        bias-pull-up;
    };

    spi0_pins: spi0-pins {
        pins = "PC0", "PC1", "PC2", "PC3";
        function = "spi0";
        drive-strength = <10>;  /* mA */
    };

    i2c0_pins: i2c0-pins {
        pins = "PH4", "PH5";
        function = "i2c0";
        bias-pull-up;
    };
};
```

#### GPIO控制器节点

```dts
gpio: gpio@01c20000 {
    compatible = "allwinner,sun50i-h616-pinctrl";
    reg = <0x0 0x01c20000 0x0 0x400>;
    interrupts = <GIC_SPI 51 IRQ_TYPE_LEVEL_HIGH>;
    gpio-controller;
    #gpio-cells = <3>;  /* bank, pin, flags */
    interrupt-controller;
    #interrupt-cells = <3>;
};
```

#### 常用外设节点示例

```dts
/* UART */
uart1: serial@01c28400 {
    compatible = "snps,dw-apb-uart";
    reg = <0x0 0x01c28400 0x0 0x400>;
    interrupts = <GIC_SPI 2 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&ccu CLK_BUS_UART1>;
    pinctrl-names = "default";
    pinctrl-0 = <&uart1_pins>;
    status = "disabled";
};

/* SPI */
spi0: spi@01c68000 {
    compatible = "allwinner,sun50i-h616-spi";
    reg = <0x0 0x01c68000 0x0 0x1000>;
    interrupts = <GIC_SPI 12 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&ccu CLK_BUS_SPI0>, <&ccu CLK_SPI0>;
    clock-names = "ahb", "mod";
    pinctrl-names = "default";
    pinctrl-0 = <&spi0_pins>;
    #address-cells = <1>;
    #size-cells = <0>;
    status = "disabled";

    /* SPI设备 */
    flash@0 {
        compatible = "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <50000000>;
        #address-cells = <1>;
        #size-cells = <1>;
    };
};

/* I2C */
i2c0: i2c@01c2ac00 {
    compatible = "allwinner,sun50i-h616-i2c";
    reg = <0x0 0x01c2ac00 0x0 0x400>;
    interrupts = <GIC_SPI 6 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&ccu CLK_BUS_I2C0>;
    pinctrl-names = "default";
    pinctrl-0 = <&i2c0_pins>;
    #address-cells = <1>;
    #size-cells = <0>;
    status = "disabled";

    /* I2C设备 */
    rtc@51 {
        compatible = "haoyu,hy5063";
        reg = <0x51>;
    };
};

/* GPIO按键 */
gpio-keys {
    compatible = "gpio-keys";
    status = "okay";

    key-0 {
        label = "KEY_POWER";
        linux,code = <KEY_POWER>;  /* input-event-codes.h */
        gpios = <&gpio 0 6 GPIO_ACTIVE_LOW>;  /* PH6 */
        debounce-interval = <50>;
        wakeup-source;
    };
};

/* LED */
leds {
    compatible = "gpio-leds";

    led-0 {
        label = "power";
        gpios = <&gpio 0 8 GPIO_ACTIVE_HIGH>;  /* PH8 */
        default-state = "on";
    };

    led-1 {
        label = "heartbeat";
        gpios = <&gpio 0 9 GPIO_ACTIVE_HIGH>;  /* PH9 */
        linux,default-trigger = "heartbeat";
    };
};
```

### 3.3 设备树操作API

#### 常用of函数

```c
#include <linux/of.h>
#include <linux/of_gpio.h>
#include <linux/of_irq.h>

/* 查找节点 */
struct device_node *of_find_node_by_name(struct device_node *from, const char *name);
struct device_node *of_find_compatible_node(struct device_node *from,
                                             const char *type, const char *compat);
struct device_node *of_find_node_by_path(const char *path);

/* 读取属性 */
int of_property_read_u32(const struct device_node *np, const char *propname, u32 *out);
int of_property_read_u32_array(const struct device_node *np, const char *propname,
                                u32 *out, size_t sz);
int of_property_read_string(const struct device_node *np, const char *propname,
                             const char **out);
int of_property_read_string_array(const struct device_node *np, const char *propname,
                                   const char **out, size_t sz);
bool of_property_read_bool(const struct device_node *np, const char *propname);

/* GPIO相关 */
int of_get_named_gpio(struct device_node *np, const char *propname, int index);

/* 中断相关 */
int of_irq_get(struct device_node *dev, int index);
unsigned int irq_of_parse_and_map(struct device_node *dev, int index);
```

**使用示例**：

```c
static int my_probe(struct platform_device *pdev)
{
    struct device_node *np = pdev->dev.of_node;
    u32 reg_base, irq;
    const char *label;
    int gpio;

    /* 读取属性 */
    if (of_property_read_u32(np, "vendor,reg-base", &reg_base)) {
        dev_err(&pdev->dev, "missing vendor,reg-base\n");
        return -EINVAL;
    }

    of_property_read_string(np, "label", &label);

    /* 获取GPIO */
    gpio = of_get_named_gpio(np, "reset-gpios", 0);
    if (gpio < 0) {
        dev_err(&pdev->dev, "failed to get reset gpio\n");
        return gpio;
    }

    /* 获取中断 */
    irq = irq_of_parse_and_map(np, 0);
    if (!irq) {
        dev_err(&pdev->dev, "failed to get irq\n");
        return -EINVAL;
    }

    /* 检查布尔属性 */
    if (of_property_read_bool(np, "vendor,feature-enabled")) {
        /* 启用特殊功能 */
    }

    return 0;
}
```

### 3.4 Pinctrl子系统

Pinctrl子系统管理芯片引脚的复用和电气配置：

```dts
/* 设备节点中引用pinctrl */
my_device {
    compatible = "vendor,my-device";
    pinctrl-names = "default", "sleep";
    pinctrl-0 = <&my_pins_default>;
    pinctrl-1 = <&my_pins_sleep>;
};
```

```c
/* 驱动中自动应用pinctrl */
/* pinctrl会在probe时自动根据pinctrl-names="default"应用 */
/* 手动切换 */
struct pinctrl *pinctrl;
struct pinctrl_state *state_sleep;

pinctrl = devm_pinctrl_get(&pdev->dev);
state_sleep = pinctrl_lookup_state(pinctrl, "sleep");
pinctrl_select_state(pinctrl, state_sleep);
```

### 3.5 GPIO子系统

#### 现代GPIO描述符API（推荐）

```c
#include <linux/gpio/consumer.h>

/* 获取GPIO */
struct gpio_desc *gpiod = devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_LOW);
/* 参数：设备、con_id（对应设备树中xxx-gpios的xxx部分）、初始方向和值 */

/* 设置值 */
gpiod_set_value(gpiod, 1);  /* 高电平 */
gpiod_set_value(gpiod, 0);  /* 低电平 */

/* 读取值 */
int val = gpiod_get_value(gpiod);

/* 从设备树获取并设置方向 */
gpiod_direction_output(gpiod, 0);
gpiod_direction_input(gpiod);

/* 作为中断 */
int irq = gpiod_to_irq(gpiod);

/* 释放（使用devm前缀则自动释放） */
gpiod_put(gpiod);
```

**设备树对应关系**：

```dts
my_device {
    /* con_id = "reset"，对应属性名 "reset-gpios" */
    reset-gpios = <&gpio 0 10 GPIO_ACTIVE_HIGH>;
    /* bank=0, pin=10, flags=GPIO_ACTIVE_HIGH */
};
```

---

## 4. 中断处理

### 4.1 中断注册

#### request_irq / devm_request_irq

```c
#include <linux/interrupt.h>

/* 注册中断 */
int request_irq(unsigned int irq,
                irq_handler_t handler,
                unsigned long flags,
                const char *name,
                void *dev);

/* 设备管理版本（推荐，自动释放） */
int devm_request_irq(struct device *dev,
                      unsigned int irq,
                      irq_handler_t handler,
                      unsigned long flags,
                      const char *name,
                      void *dev_id);
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `irq` | 中断号 |
| `handler` | 中断处理函数 |
| `flags` | 中断标志 |
| `name` | 中断名称（显示在/proc/interrupts） |
| `dev_id` | 传给handler的私有数据，共享中断时用于区分设备 |

**中断标志**：

| 标志 | 说明 |
|------|------|
| `IRQF_SHARED` | 共享中断 |
| `IRQF_TRIGGER_RISING` | 上升沿触发 |
| `IRQF_TRIGGER_FALLING` | 下降沿触发 |
| `IRQF_TRIGGER_HIGH` | 高电平触发 |
| `IRQF_TRIGGER_LOW` | 低电平触发 |

#### 中断处理函数

```c
static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    struct my_device *dev = dev_id;

    /* 确认是否是本设备产生的中断 */
    if (!is_my_device_interrupt(dev))
        return IRQ_NONE;  /* 不是本设备的中断 */

    /* 读取/清除中断状态 */
    // ...

    /* 保存数据、唤醒等待队列等 */
    dev->data_ready = 1;
    wake_up_interruptible(&dev->wait_queue);

    return IRQ_HANDLED;  /* 中断已处理 */
}
```

**返回值**：
- `IRQ_HANDLED`：中断已处理
- `IRQ_NONE`：不是本设备的中断（共享中断时）

### 4.2 延后机制

中断处理函数运行在中断上下文，有严格限制：
- 不能睡眠
- 不能调用可能睡眠的函数（kmalloc GFP_KERNEL, mutex_lock等）
- 应该尽快完成

因此需要延后机制处理耗时的工作：

#### tasklet

```c
#include <linux/interrupt.h>

static void my_tasklet_func(unsigned long data);
DECLARE_TASKLET(my_tasklet, my_tasklet_func, 0);

static void my_tasklet_func(unsigned long data)
{
    /* 在软中断上下文执行，不能睡眠 */
    /* 处理中断的下半部工作 */
}

static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    /* 顶半部：快速处理 */
    // ...

    /* 调度tasklet */
    tasklet_schedule(&my_tasklet);

    return IRQ_HANDLED;
}
```

#### workqueue

```c
#include <linux/workqueue.h>

static struct work_struct my_work;

static void my_work_func(struct work_struct *work)
{
    /* 在进程上下文执行，可以睡眠 */
    /* 使用kmalloc, msleep等 */
}

/* 初始化 */
INIT_WORK(&my_work, my_work_func);

static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    /* 顶半部 */
    // ...

    /* 调度work */
    schedule_work(&my_work);

    return IRQ_HANDLED;
}
```

#### threaded_irq

```c
/* 使用线程化中断（推荐） */
static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    /* 在中断上下文执行 */
    /* 只做最少量的工作 */
    return IRQ_WAKE_THREAD;
}

static irqreturn_t my_threaded_handler(int irq, void *dev_id)
{
    /* 在内核线程中执行，可以睡眠 */
    /* 处理大部分工作 */
    return IRQ_HANDLED;
}

devm_request_threaded_irq(&pdev->dev, irq,
                           my_irq_handler,     /* 顶半部 */
                           my_threaded_handler, /* 底半部（线程） */
                           IRQF_TRIGGER_RISING,
                           "my_device", dev);
```

#### 延后机制对比

| 机制 | 执行上下文 | 能否睡眠 | 适用场景 |
|------|-----------|---------|---------|
| tasklet | 软中断 | 不能 | 轻量级、快速的底半部 |
| workqueue | 内核线程 | 能 | 需要睡眠的底半部 |
| threaded_irq | 内核线程 | 能 | 驱动中断处理（推荐） |
| softirq | 软中断 | 不能 | 内核核心子系统（不推荐驱动使用） |

---

## 5. 并发与同步

### 5.1 并发场景

嵌入式Linux中常见的并发场景：
- 多核CPU同时访问共享资源
- 中断处理函数与进程上下文并发
- 多个进程/线程同时操作同一设备
- 内核抢占导致的并发

### 5.2 原子操作

```c
#include <linux/atomic.h>

atomic_t counter = ATOMIC_INIT(0);

atomic_set(&counter, 10);           /* 设置 */
int val = atomic_read(&counter);     /* 读取 */
atomic_inc(&counter);               /* 加1 */
atomic_dec(&counter);               /* 减1 */
atomic_add(5, &counter);            /* 加5 */
atomic_sub(3, &counter);            /* 减3 */

/* 原子比较并交换 */
int old = atomic_cmpxchg(&counter, expected, new);

/* 原子位操作 */
set_bit(0, &flags);
clear_bit(0, &flags);
test_bit(0, &flags);
```

### 5.3 自旋锁(spinlock)

```c
#include <linux/spinlock.h>

spinlock_t my_lock;
spin_lock_init(&my_lock);

/* 获取锁（会忙等待，不能睡眠） */
spin_lock(&my_lock);
/* 临界区 */
spin_unlock(&my_lock);

/* 禁中断版本（用于中断处理函数中） */
spin_lock_irqsave(&my_lock, flags);
/* 临界区 */
spin_unlock_irqrestore(&my_lock, flags);

/* 禁下半部 */
spin_lock_bh(&my_lock);
/* 临界区 */
spin_unlock_bh(&my_lock);
```

**使用原则**：
- 持有自旋锁时不能睡眠
- 临界区应尽可能短
- 多核环境下会真正自旋等待
- 单核环境下只禁止抢占

### 5.4 互斥锁(mutex)

```c
#include <linux/mutex.h>

struct mutex my_mutex;
mutex_init(&my_mutex);

/* 获取锁（可能会睡眠） */
mutex_lock(&my_mutex);
/* 临界区 */
mutex_unlock(&my_mutex);

/* 尝试获取（不等待） */
if (mutex_trylock(&my_mutex)) {
    /* 获取成功 */
    mutex_unlock(&my_mutex);
}

/* 可中断版本 */
if (mutex_lock_interruptible(&my_mutex)) {
    /* 被信号中断 */
    return -ERESTARTSYS;
}
```

### 5.5 信号量(semaphore)

```c
#include <linux/semaphore.h>

struct semaphore my_sem;
sema_init(&my_sem, 1);  /* 初始值1 = 互斥锁 */

down(&my_sem);         /* 获取（不可中断） */
/* 临界区 */
up(&my_sem);           /* 释放 */

down_interruptible(&my_sem);  /* 可中断版本 */
down_trylock(&my_sem);        /* 尝试获取 */
```

### 5.6 读写锁

```c
#include <linux/rwlock.h>

rwlock_t my_rwlock;
rwlock_init(&my_rwlock);

/* 读锁（多个读者可并发） */
read_lock(&my_rwlock);
/* 读操作 */
read_unlock(&my_rwlock);

/* 写锁（独占） */
write_lock(&my_rwlock);
/* 写操作 */
write_unlock(&my_rwlock);

/* 读写信号量 */
#include <linux/rwsem.h>

struct rw_semaphore my_rwsem;
init_rwsem(&my_rwsem);

down_read(&my_rwsem);
/* 读操作 */
up_read(&my_rwsem);

down_write(&my_rwsem);
/* 写操作 */
up_write(&my_rwsem);
```

### 5.7 RCU机制

RCU(Read-Copy-Update)是一种无锁同步机制，适合读多写少的场景：

```c
#include <linux/rcupdate.h>

/* 读端 */
rcu_read_lock();
ptr = rcu_dereference(global_ptr);
/* 使用ptr（不能睡眠，不能阻塞） */
rcu_read_unlock();

/* 写端 */
new_ptr = kmalloc(...);
*new_ptr = *old_ptr;    /* Copy */
/* 修改new_ptr */       /* Update */
rcu_assign_pointer(global_ptr, new_ptr);
synchronize_rcu();      /* 等待所有读者完成 */
kfree(old_ptr);         /* 安全释放旧数据 */
```

### 5.8 completion

```c
#include <linux/completion.h>

struct completion my_comp;
init_completion(&my_comp);

/* 等待完成 */
wait_for_completion(&my_comp);
wait_for_completion_interruptible(&my_comp);
wait_for_completion_timeout(&my_comp, msecs_to_jiffies(5000));

/* 触发完成 */
complete(&my_comp);       /* 唤醒一个等待者 */
complete_all(&my_comp);   /* 唤醒所有等待者 */
```

### 5.9 同步机制选择指南

| 场景 | 推荐机制 |
|------|---------|
| 中断上下文中的短临界区 | spinlock + irqsave |
| 进程上下文中的长临界区 | mutex |
| 读多写少 | RCU 或 rwlock |
| 中断与进程间同步 | spinlock + irqsave 或 completion |
| 生产者-消费者 | wait_queue + completion |
| 单次初始化 | DEFINE_MUTEX 或 atomic |

---

## 6. 内存管理

### 6.1 内核空间内存分配

#### kmalloc / kfree

```c
#include <linux/slab.h>

/* 分配物理连续内存 */
void *ptr = kmalloc(size, GFP_KERNEL);
void *ptr = kzalloc(size, GFP_KERNEL);  /* 分配并清零 */

kfree(ptr);
```

**GFP标志**：

| 标志 | 说明 | 使用场景 |
|------|------|---------|
| `GFP_KERNEL` | 可能睡眠等待 | 进程上下文（最常用） |
| `GFP_ATOMIC` | 不睡眠，可能失败 | 中断上下文、持有自旋锁时 |
| `GFP_DMA` | DMA可访问内存 | DMA缓冲区 |
| `GFP_USER` | 用户空间可访问 | — |

**kmalloc限制**：
- 最大通常128KB（取决于页分配器）
- 分配的是物理连续内存
- 适合小块内存分配

#### vmalloc

```c
#include <linux/vmalloc.h>

/* 分配虚拟连续但物理不一定连续的内存 */
void *ptr = vmalloc(size);
vfree(ptr);
```

**vmalloc vs kmalloc**：

| 特性 | kmalloc | vmalloc |
|------|---------|---------|
| 物理连续 | 是 | 否 |
| 虚拟连续 | 是 | 是 |
| 最大大小 | ~128KB | 很大(GB级) |
| 性能 | 高（直接映射） | 低（需要修改页表） |
| 使用场景 | DMA、小分配 | 大块内存、不需物理连续 |

#### get_free_pages

```c
#include <linux/gfp.h>

/* 分配2^n个页面 */
unsigned long addr = __get_free_pages(GFP_KERNEL, order);
/* order=0: 1页(4KB), order=1: 2页(8KB), ... */

free_pages(addr, order);

/* 单页分配 */
struct page *page = alloc_page(GFP_KERNEL);
__free_page(page);
```

### 6.2 DMA内存

```c
#include <linux/dma-mapping.h>

/* 分配DMA一致性内存（coherent） */
void *vaddr = dma_alloc_coherent(&pdev->dev, size, &dma_handle, GFP_KERNEL);
/* vaddr: CPU访问的虚拟地址 */
/* dma_handle: DMA总线地址 */

dma_free_coherent(&pdev->dev, size, vaddr, dma_handle);

/* DMA流式映射 */
dma_addr_t dma_addr = dma_map_single(&pdev->dev, buf, size, DMA_TO_DEVICE);
/* 使用dma_addr进行DMA传输 */
dma_unmap_single(&pdev->dev, dma_addr, size, DMA_TO_DEVICE);
```

### 6.3 I/O内存映射

```c
#include <linux/io.h>

/* 映射设备寄存器到内核虚拟地址 */
void __iomem *base = ioremap(phys_addr, size);

/* 读写寄存器 */
u32 val = readl(base + REG_OFFSET);
writel(val, base + REG_OFFSET);

u16 val16 = readw(base + REG_OFFSET);
writew(val16, base + REG_OFFSET);

u8 val8 = readb(base + REG_OFFSET);
writeb(val8, base + REG_OFFSET);

/* 批量读写 */
ioread32(base + REG_OFFSET);
iowrite32(val, base + REG_OFFSET);

/* 取消映射 */
iounmap(base);
```

**使用devm版本（推荐）**：

```c
void __iomem *base = devm_ioremap_resource(&pdev->dev, res);
/* 自动管理生命周期，驱动卸载时自动iounmap */
```

---

## 7. 构建系统

### 7.1 交叉编译工具链

#### 什么是交叉编译

在x86主机上编译运行在ARM等目标平台的代码。

#### 常用工具链

| 工具链 | 说明 |
|--------|------|
| `aarch64-linux-gnu-gcc` | ARM64 Linux GNU工具链（Debian/Ubuntu提供） |
| `arm-linux-gnueabihf-gcc` | ARM32 硬浮点工具链 |
| `gcc-aarch64-linux-gnu` | Ubuntu包名 |
| Linaro GCC | 社区优化版本 |
| 厂商SDK工具链 | 如全志Tina SDK的工具链 |

#### 安装与配置

```bash
# Ubuntu/Debian
sudo apt install gcc-aarch64-linux-gnu
sudo apt install gcc-arm-linux-gnueabihf

# 验证
aarch64-linux-gnu-gcc --version

# 编译
aarch64-linux-gnu-gcc -o hello hello.c

# 查看编译结果
file hello
# hello: ELF 64-bit LSB executable, ARM aarch64...
```

#### sysroot概念

sysroot是目标系统的根文件系统副本，包含头文件和库：

```bash
# 指定sysroot编译
aarch64-linux-gnu-gcc --sysroot=/path/to/sysroot -o hello hello.c

# 典型sysroot结构
sysroot/
├── usr/
│   ├── include/     # 头文件
│   └── lib/         # 库文件
├── lib/
└── etc/
```

### 7.2 U-Boot

#### U-Boot简介

U-Boot(Universal Boot Loader)是嵌入式Linux最常用的引导加载程序，支持多种CPU架构。

#### U-Boot启动流程

```
┌──────────────────┐
│  ROM Code (BL1)  │  ← 芯片固化代码，加载SPL
├──────────────────┤
│  SPL (BL2)       │  ← 初始化DDR，加载U-Boot
├──────────────────┤
│  U-Boot (BL31)   │  ← 初始化外设，加载内核
├──────────────────┤
│  Linux Kernel    │  ← 内核启动
├──────────────────┤
│  Root Filesystem │  ← 挂载根文件系统
├──────────────────┤
│  User Application│  ← 应用程序
└──────────────────┘
```

#### U-Boot命令

```bash
# 查看环境变量
printenv
printenv bootargs bootcmd

# 设置环境变量
setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait"
setenv bootcmd "load mmc 0:1 0x40008000 Image; load mmc 0:1 0x43000000 dtb; booti 0x40008000 - 0x43000000"
saveenv  # 保存到Flash

# 加载文件
load mmc 0:1 0x40008000 Image      # 从eMMC分区1加载内核
load mmc 0:1 0x43000000 board.dtb  # 加载设备树

# TFTP加载（开发阶段常用）
setenv ipaddr 192.168.1.100
setenv serverip 192.168.1.1
tftp 0x40008000 Image
tftp 0x43000000 board.dtb

# 启动内核
bootm 0x40008000 - 0x43000000       # uImage格式
booti 0x40008000 - 0x43000000       # Image格式

# 设备树操作
fdt addr 0x43000000
fdt print /chosen
fdt set /chosen bootargs "console=ttyS0,115200"

# 查看存储设备
mmc list
mmc info
mmc part

# 查看文件系统
ext4ls mmc 0:2 /
fatls mmc 0:1 /

# 内存操作
md 0x40008000 0x10    # 查看内存
mw 0x40008000 0 0x10  # 写内存
cp 0x40008000 0x41000000 0x100000  # 内存拷贝
```

#### U-Boot环境变量详解

```bash
# bootargs: 传递给内核的命令行参数
setenv bootargs \
    "console=ttyS0,115200 \      # 控制台
     root=/dev/mmcblk0p2 \       # 根文件系统
     rootwait \                   # 等待根设备
     rootfstype=ext4 \           # 文件系统类型
     panic=10 \                   # panic后10秒重启
     loglevel=7"                  # 日志级别

# bootcmd: 自动启动命令（倒计时结束后执行）
setenv bootcmd \
    "load mmc 0:1 0x40008000 Image; \
     load mmc 0:1 0x43000000 sun50i-h616-board.dtb; \
     booti 0x40008000 - 0x43000000"

# bootdelay: 启动倒计时（秒）
setenv bootdelay 3
```

### 7.3 Buildroot

#### Buildroot简介

Buildroot是一个轻量级的嵌入式Linux构建系统，生成完整的根文件系统、内核镜像、工具链等。

#### 架构

```
Buildroot/
├── board/             # 板级配置
├── boot/              # 引导加载器（U-Boot等）
├── configs/           # defconfig文件
├── dl/                # 下载的源码包
├── docs/
├── fs/                # 文件系统框架
├── linux/             # 内核配置
├── output/            # 构建输出
│   ├── build/         # 构建目录
│   ├── host/          # 主机工具
│   ├── images/        # 最终镜像
│   ├── staging/       # 交叉编译sysroot
│   └── target/        # 根文件系统
├── package/           # 所有软件包
├── support/
├── Makefile
└── .config            # 当前配置
```

#### 使用流程

```bash
# 1. 下载Buildroot
wget https://buildroot.org/downloads/buildroot-2024.02.tar.gz
tar xzf buildroot-2024.02.tar.gz
cd buildroot-2024.02

# 2. 选择默认配置
make list_defconfigs | grep aarch64
make qemu_aarch64_virt_defconfig

# 3. 配置
make menuconfig
# Target options → Target Architecture (AArch64)
# Toolchain → Toolchain type (Buildroot toolchain)
# System configuration → Root password
# Kernel → 内核版本和配置
# Target packages → 选择需要的软件包
# Filesystem images → 选择镜像格式(ext4, squashfs等)

# 4. 编译
make -j$(nproc)
# 首次编译较长（1-2小时），后续增量编译快

# 5. 输出
ls output/images/
# Image(内核)  rootfs.ext4  rootfs.tar  *.dtb
```

#### 自定义包(package)

```makefile
# package/my-app/my-app.mk
MY_APP_VERSION = 1.0
MY_APP_SITE = $(TOPDIR)/../my-app-source
MY_APP_SITE_METHOD = local

define MY_APP_BUILD_CMDS
    $(MAKE) CC="$(TARGET_CC)" -C $(@D)
endef

define MY_APP_INSTALL_TARGET_CMDS
    $(INSTALL) -D -m 0755 $(@D)/my-app $(TARGET_DIR)/usr/bin/my-app
endef

$(eval $(generic-package))
```

```ini
# package/my-app/Config.in
config BR2_PACKAGE_MY_APP
    bool "my-app"
    help
        My custom application.
```

#### 外部树(External Tree)

将自定义配置、包、板级支持放在Buildroot外部：

```
my-project/
├── board/
│   └── my-board/
│       ├── defconfig
│       ├── genimage.cfg
│       ├── overlay/          # 根文件系统覆盖
│       │   └── etc/
│       └── post-build.sh
├── configs/
│   └── my-board_defconfig
├── external.desc
├── external.mk
├── package/
│   └── my-app/
└── Config.in
```

```bash
# 使用外部树
make BR2_EXTERNAL=/path/to/my-project my-board_defconfig
```

### 7.4 Yocto

#### Yocto vs Buildroot对比

| 特性 | Buildroot | Yocto |
|------|-----------|-------|
| 复杂度 | 简单 | 复杂 |
| 构建系统 | Make | BitBake |
| 包管理 | 基础 | 完整(opkg/rpm/deb) |
| 镜像大小 | 小 | 相对较大 |
| 学习曲线 | 平缓 | 陡峭 |
| 社区支持 | 好 | 非常好(商业支持) |
| 适用场景 | 小型产品、原型 | 大型产品、需要长期维护 |
| 增量构建 | 支持 | 支持（更完善） |
| 许可证管理 | 基础 | 完善 |
| 图形支持 | 有限 | 完整(Qt, GTK+) |

#### BitBake基础

```bash
# 构建镜像
bitbake core-image-minimal

# 构建单个包
bitbake my-app

# 清理
bitbake -c clean my-app
bitbake -c cleansstate my-app

# 查看依赖关系
bitbake -g my-app
dot -Tpng task-depends.dot -o deps.png

# 开发shell
bitbake -c devshell my-app
```

#### Recipe(.bb)文件

```bitbake
# recipes-app/my-app/my-app_1.0.bb
SUMMARY = "My Application"
DESCRIPTION = "A custom embedded application"
HOMEPAGE = "https://example.com"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=..."

SRC_URI = "git://github.com/example/my-app.git;branch=main;protocol=https"
SRCREV = "abc123def456"

S = "${WORKDIR}/git"

inherit cmake

EXTRA_OECMAKE = "-DCMAKE_INSTALL_PREFIX=/usr"

do_install:append() {
    install -d ${D}${sysconfdir}
    install -m 0644 ${S}/config/my-app.conf ${D}${sysconfdir}/
}

FILES:${PN} += "${sysconfdir}/my-app.conf"
```

#### Layer概念

Layer是Yocto的模块化组织方式：

```
meta-my-board/
├── conf/
│   ├── layer.conf
│   └── machine/
│       └── my-board.conf
├── recipes-bsp/
│   └── u-boot/
│       └── u-boot_%.bbappend
├── recipes-core/
│   └── images/
│       └── my-image.bb
├── recipes-kernel/
│   ├── linux/
│   │   └── linux-%.bbappend
│   └── linux/linux-my-board_5.15.bb
└── recipes-app/
    └── my-app/
```

### 7.5 根文件系统

#### 标准目录结构

```
/
├── bin/        # 基本命令（BusyBox提供）
├── sbin/       # 系统管理命令
├── etc/        # 系统配置文件
├── lib/        # 共享库
├── usr/        # 用户程序
│   ├── bin/
│   ├── lib/
│   └── share/
├── var/        # 可变数据
├── tmp/        # 临时文件（tmpfs）
├── proc/       # 进程信息（procfs虚拟文件系统）
├── sys/        # 设备信息（sysfs虚拟文件系统）
├── dev/        # 设备节点（devtmpfs）
├── mnt/        # 挂载点
├── opt/        # 可选软件
├── root/       # root用户home目录
└── run/        # 运行时数据
```

#### BusyBox

BusyBox将常用Unix工具集成到一个二进制文件：

```bash
# 配置BusyBox
make menuconfig
# 选择需要的applet（shell, coreutils, util-linux等）

# 编译
make -j$(nproc)
make install  # 安装到 _install/
```

**BusyBox init**：
- `/etc/inittab` 配置
- 支持运行级别
- 轻量级，适合小型系统

#### systemd vs SysVinit

| 特性 | SysVinit | systemd |
|------|----------|---------|
| 启动方式 | 串行脚本 | 并行化 |
| 依赖管理 | 手动排序 | 自动依赖 |
| 服务文件 | Shell脚本(/etc/init.d/) | Unit文件(.service) |
| 资源占用 | 小 | 相对大 |
| 功能 | 基础 | 丰富(journal, timers, etc.) |
| 适用场景 | 资源受限的嵌入式 | 功能丰富的嵌入式/桌面 |

**systemd service文件示例**：

```ini
# /etc/systemd/system/my-app.service
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/my-app --config /etc/my-app.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 管理服务
systemctl enable my-app
systemctl start my-app
systemctl status my-app
journalctl -u my-app
```

#### 根文件系统构建方法

**方法一：手动构建**

```bash
mkdir rootfs
cd rootfs
mkdir -p bin sbin etc lib usr/bin usr/lib proc sys dev tmp

# 安装BusyBox
make -C busybox CONFIG_PREFIX=/path/to/rootfs install

# 安装库
cp /path/to/sysroot/lib/*.so* lib/

# 创建设备节点
sudo mknod dev/console c 5 1
sudo mknod dev/null c 1 3

# 创建/etc配置文件
# inittab, fstab, passwd, group, resolv.conf, etc.
```

**方法二：Buildroot自动生成**（推荐）

```bash
# Buildroot自动构建完整的根文件系统
make -j$(nproc)
ls output/images/rootfs.ext4
```

**方法三：debootstrap**

```bash
# 构建Debian/Ubuntu风格的根文件系统
sudo debootstrap --arch=arm64 buster rootfs http://deb.debian.org/debian
```

---

## 8. Linux内核调试

### 8.1 打印调试

#### printk

```c
#include <linux/printk.h>

/* 八个日志级别 */
#define KERN_EMERG   "0"  /* 系统不可用 */
#define KERN_ALERT   "1"  /* 需要立即处理 */
#define KERN_CRIT    "2"  /* 临界条件 */
#define KERN_ERR     "3"  /* 错误 */
#define KERN_WARNING "4"  /* 警告 */
#define KERN_NOTICE  "5"  /* 正常但重要 */
#define KERN_INFO    "6"  /* 信息 */
#define KERN_DEBUG   "7"  /* 调试 */

printk(KERN_ERR "my_driver: error %d occurred\n", err);
```

#### dev_xxx系列（推荐）

```c
/* 使用设备相关的打印函数，自动包含设备名称 */
dev_err(&pdev->dev, "failed to request irq: %d\n", ret);
dev_warn(&pdev->dev, "using default value\n");
dev_info(&pdev->dev, "device probed successfully\n");
dev_dbg(&pdev->dev, "debug info: val=%d\n", val);

/* 输出格式：my_device: failed to request irq: -22 */
```

#### dynamic_debug

动态控制pr_debug/dev_dbg的输出：

```bash
# 启用所有pr_debug
echo 'file my_driver.c +p' > /sys/kernel/debug/dynamic_debug/control

# 启用特定函数的调试
echo 'func my_probe +p' > /sys/kernel/debug/dynamic_debug/control

# 启用特定模块
echo 'module my_driver +p' > /sys/kernel/debug/dynamic_debug/control

# 禁用
echo 'file my_driver.c -p' > /sys/kernel/debug/dynamic_debug/control

# 内核启动参数
# dyndbg="file my_driver.c +p; file another.c +p"
```

### 8.2 调试工具

#### strace

跟踪系统调用：

```bash
# 基本使用
strace ./my_app

# 跟踪特定系统调用
strace -e trace=open,read,write ./my_app

# 跟踪已运行的进程
strace -p <pid>

# 输出到文件
strace -o output.txt ./my_app

# 统计系统调用
strace -c ./my_app
```

#### gdb / gdbserver 远程调试

**内核调试**：

```bash
# 编译内核时启用调试
# CONFIG_DEBUG_INFO=y
# CONFIG_GDB_SCRIPTS=y

# 启动QEMU带GDB server
qemu-system-aarch64 -machine virt -cpu cortex-a53 \
    -kernel Image -append "nokaslr" \
    -S -s  # -S: 暂停启动, -s: 开启GDB server(端口1234)

# GDB连接
aarch64-linux-gnu-gdb vmlinux
(gdb) target remote :1234
(gdb) break start_kernel
(gdb) continue
```

**用户空间程序调试**：

```bash
# 目标板运行gdbserver
gdbserver :1234 ./my_app

# 主机GDB连接
aarch64-linux-gnu-gdb ./my_app
(gdb) target remote 192.168.1.100:1234
(gdb) break main
(gdb) continue
(gdb) next
(gdb) print variable
```

#### perf 性能分析

```bash
# 采样CPU使用
perf record -g ./my_app
perf report

# 实时查看
perf top

# 统计特定事件
perf stat -e cache-misses,cache-references ./my_app

# 内核性能分析
perf record -a -g sleep 10  # 全系统采样10秒
perf report
```

#### ftrace / trace-cmd

```bash
# 使用trace-cmd（ftrace的前端）
# 记录内核函数跟踪
trace-cmd record -p function_graph -g my_function
trace-cmd report

# 跟踪特定进程
trace-cmd record -p function -P <pid>
trace-cmd report

# 事件跟踪
trace-cmd record -e sched_switch
trace-cmd report

# 查看所有可用跟踪事件
cat /sys/kernel/debug/tracing/available_events

# 使用ftrace直接操作
echo function > /sys/kernel/debug/tracing/current_tracer
echo my_function > /sys/kernel/debug/tracing/set_ftrace_filter
echo 1 > /sys/kernel/debug/tracing/tracing_on
cat /sys/kernel/debug/tracing/trace
```

### 8.3 常见问题分析

#### Oops / Panic分析

**Oops示例**：

```
Unable to handle kernel NULL pointer dereference at virtual address 0000000000000010
...
PC is at my_driver_write+0x48/0x100 [my_driver]
LR is at my_driver_write+0x40/0x100 [my_driver]
...
Call trace:
 my_driver_write+0x48/0x100 [my_driver]
 vfs_write+0xb0/0x1c0
 ksys_write+0x68/0xf0
 __arm64_sys_write+0x1c/0x28
 el0_svc_common.constprop.0+0x64/0x158
 do_el0_svc+0x38/0xa0
 el0_svc+0x14/0x50
 el0t_64_sync_handler+0x10c/0x130
 el0t_64_sync+0x1a4/0x1a8
```

**分析步骤**：
1. 查看PC指针位置：`my_driver_write+0x48/0x100`
2. 使用addr2line定位源码行：`aarch64-linux-gnu-addr2line -e my_driver.ko 0x48`
3. 使用objdump查看反汇编：`aarch64-linux-gnu-objdump -dS my_driver.ko | less`
4. 检查NULL指针：地址0x10说明在NULL指针偏移0x10处访问了成员

#### 内存泄漏检测(kmemleak)

```bash
# 启用kmemleak
# CONFIG_DEBUG_KMEMLEAK=y
# CONFIG_DEBUG_KMEMLEAK_DEFAULT_OFF=n

# 扫描
echo scan > /sys/kernel/debug/kmemleak

# 查看结果
cat /sys/kernel/debug/kmemleak

# 清除
echo clear > /sys/kernel/debug/kmemleak
```

#### 死锁检测(lockdep)

```bash
# 启用lockdep
# CONFIG_PROVE_LOCKING=y
# CONFIG_DEBUG_LOCK_ALLOC=y

# lockdep会在运行时检测潜在的死锁
# 输出在dmesg中
dmesg | grep -i lockdep
```

#### 内核崩溃栈回溯

```c
/* 在代码中触发栈回溯 */
#include <linux/stacktrace.h>
#include <linux/sched.h>

dump_stack();  /* 打印当前调用栈 */
```

---

## 9. 常用外设驱动框架

### 9.1 Platform驱动

Platform总线用于连接没有可枚举总线的设备（如SoC内部外设）：

```c
#include <linux/platform_device.h>
#include <linux/of.h>

static int my_probe(struct platform_device *pdev)
{
    struct resource *res;
    void __iomem *base;
    int irq;

    /* 获取内存资源 */
    res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
    if (!res) {
        dev_err(&pdev->dev, "no memory resource\n");
        return -ENODEV;
    }

    /* 映射寄存器 */
    base = devm_ioremap_resource(&pdev->dev, res);
    if (IS_ERR(base))
        return PTR_ERR(base);

    /* 获取中断 */
    irq = platform_get_irq(pdev, 0);
    if (irq < 0)
        return irq;

    /* 注册中断 */
    devm_request_irq(&pdev->dev, irq, my_irq_handler,
                      0, "my_device", priv);

    /* 从设备树获取自定义属性 */
    u32 val;
    of_property_read_u32(pdev->dev.of_node, "vendor,my-prop", &val);

    /* 获取GPIO */
    int gpio = devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_LOW);

    /* 获取时钟 */
    struct clk *clk = devm_clk_get(&pdev->dev, NULL);
    clk_prepare_enable(clk);

    /* 获取pinctrl */
    /* （通常由设备树自动处理） */

    /* 注册字符设备/其他子系统 */
    // ...

    platform_set_drvdata(pdev, priv);
    return 0;
}

static int my_remove(struct platform_device *pdev)
{
    /* 清理资源 */
    return 0;
}

static const struct of_device_id my_of_match[] = {
    { .compatible = "vendor,my-device", },
    { /* sentinel */ },
};
MODULE_DEVICE_TABLE(of, my_of_match);

static struct platform_driver my_driver = {
    .probe = my_probe,
    .remove = my_remove,
    .driver = {
        .name = "my_driver",
        .of_match_table = my_of_match,
    },
};
module_platform_driver(my_driver);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("My Platform Driver");
```

**设备树节点**：

```dts
my_device@01c20000 {
    compatible = "vendor,my-device";
    reg = <0x0 0x01c20000 0x0 0x1000>;
    interrupts = <GIC_SPI 10 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&ccu CLK_BUS_MY>;
    reset-gpios = <&gpio 0 10 GPIO_ACTIVE_LOW>;
    vendor,my-prop = <42>;
    status = "okay";
};
```

**probe函数调用时机**：
1. 内核解析设备树，创建platform_device
2. 内核注册platform_driver
3. 如果platform_device的compatible与driver的of_match_table匹配，调用probe

### 9.2 I2C子系统

```c
#include <linux/i2c.h>

/* I2C驱动 */
static int my_i2c_probe(struct i2c_client *client,
                         const struct i2c_device_id *id)
{
    /* 读取设备信息 */
    dev_info(&client->dev, "address: 0x%02x\n", client->addr);

    /* 使用i2c_transfer */
    u8 reg = 0x00;
    u8 val;
    struct i2c_msg msgs[2] = {
        {
            .addr = client->addr,
            .flags = 0,           /* 写 */
            .len = 1,
            .buf = &reg,
        },
        {
            .addr = client->addr,
            .flags = I2C_M_RD,    /* 读 */
            .len = 1,
            .buf = &val,
        },
    };

    int ret = i2c_transfer(client->adapter, msgs, 2);
    if (ret < 0) {
        dev_err(&client->dev, "i2c transfer failed\n");
        return ret;
    }

    return 0;
}

static const struct of_device_id my_i2c_of_match[] = {
    { .compatible = "vendor,my-i2c-device", },
    { }
};
MODULE_DEVICE_TABLE(of, my_i2c_of_match);

static const struct i2c_device_id my_i2c_id[] = {
    { "my_i2c_device", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, my_i2c_id);

static struct i2c_driver my_i2c_driver = {
    .driver = {
        .name = "my_i2c_device",
        .of_match_table = my_i2c_of_match,
    },
    .probe = my_i2c_probe,
    .id_table = my_i2c_id,
};
module_i2c_driver(my_i2c_driver);
```

**设备树**：

```dts
&i2c0 {
    status = "okay";

    my_sensor@48 {
        compatible = "vendor,my-i2c-device";
        reg = <0x48>;
    };
};
```

#### regmap API（推荐）

regmap提供统一的寄存器访问接口，支持I2C、SPI等：

```c
#include <linux/regmap.h>

static const struct regmap_config my_regmap_config = {
    .reg_bits = 8,
    .val_bits = 8,
    .max_register = 0xFF,
};

static int my_probe(struct i2c_client *client)
{
    struct regmap *regmap;

    regmap = devm_regmap_init_i2c(client, &my_regmap_config);
    if (IS_ERR(regmap))
        return PTR_ERR(regmap);

    /* 读写寄存器 */
    unsigned int val;
    regmap_read(regmap, 0x00, &val);
    regmap_write(regmap, 0x01, 0xAB);
    regmap_update_bits(regmap, 0x02, 0x0F, 0x05);  /* 位操作 */

    return 0;
}
```

### 9.3 SPI子系统

```c
#include <linux/spi/spi.h>

static int my_spi_probe(struct spi_device *spi)
{
    /* 配置SPI */
    spi->mode = SPI_MODE_0;  /* CPOL=0, CPHA=0 */
    spi->max_speed_hz = 10000000;  /* 10MHz */
    spi->bits_per_word = 8;

    int ret = spi_setup(spi);
    if (ret < 0)
        return ret;

    /* 简单读写 */
    u8 tx_buf[] = {0x9F, 0x00, 0x00, 0x00};
    u8 rx_buf[4];

    ret = spi_write_then_read(spi, tx_buf, 1, rx_buf + 1, 3);
    if (ret < 0)
        return ret;

    /* 完整的传输（更灵活） */
    struct spi_transfer xfer = {
        .tx_buf = tx_buf,
        .rx_buf = rx_buf,
        .len = sizeof(tx_buf),
        .speed_hz = 5000000,
    };
    struct spi_message msg;
    spi_message_init(&msg);
    spi_message_add_tail(&xfer, &msg);
    ret = spi_sync(spi, &msg);

    return 0;
}

static const struct of_device_id my_spi_of_match[] = {
    { .compatible = "vendor,my-spi-device", },
    { }
};

static struct spi_driver my_spi_driver = {
    .driver = {
        .name = "my_spi_device",
        .of_match_table = my_spi_of_match,
    },
    .probe = my_spi_probe,
};
module_spi_driver(my_spi_driver);
```

### 9.4 输入子系统

```c
#include <linux/input.h>

static int my_input_probe(struct platform_device *pdev)
{
    struct input_dev *input;

    /* 分配输入设备 */
    input = devm_input_allocate_device(&pdev->dev);
    if (!input)
        return -ENOMEM;

    /* 设置设备信息 */
    input->name = "my-keys";
    input->phys = "my-keys/input0";
    input->id.bustype = BUS_HOST;
    input->id.vendor = 0x0001;
    input->id.product = 0x0001;
    input->id.version = 0x0100;

    /* 设置支持的事件类型和按键码 */
    set_bit(EV_KEY, input->evbit);
    set_bit(KEY_POWER, input->keybit);
    set_bit(KEY_VOLUMEUP, input->keybit);

    /* 注册输入设备 */
    int ret = input_register_device(input);
    if (ret)
        return ret;

    /* 在中断处理中报告事件 */
    input_report_key(input, KEY_POWER, 1);   /* 按下 */
    input_sync(input);                        /* 同步 */
    input_report_key(input, KEY_POWER, 0);   /* 释放 */
    input_sync(input);

    return 0;
}
```

**设备树（GPIO按键）**：

```dts
gpio-keys {
    compatible = "gpio-keys";

    power-key {
        label = "Power";
        linux,code = <KEY_POWER>;
        gpios = <&gpio 0 6 GPIO_ACTIVE_LOW>;
        debounce-interval = <50>;
        wakeup-source;
    };
};
```

### 9.5 PWM子系统

```c
#include <linux/pwm.h>

static int my_pwm_probe(struct platform_device *pdev)
{
    struct pwm_device *pwm;
    struct pwm_state state;

    /* 获取PWM设备 */
    pwm = devm_pwm_get(&pdev->dev, NULL);
    if (IS_ERR(pwm))
        return PTR_ERR(pwm);

    /* 配置PWM */
    pwm_init_state(pwm, &state);
    state.period = 1000000;    /* 1ms = 1kHz */
    state.duty_cycle = 500000; /* 50%占空比 */
    state.enabled = true;

    int ret = pmw_apply_state(pwm, &state);
    if (ret)
        return ret;

    /* 动态调整 */
    pwm_set_relative_duty_cycle(pwm, 75, 100); /* 75% */
    pwm_enable(pwm);
    pwm_disable(pwm);

    return 0;
}
```

**设备树**：

```dts
pwmleds {
    compatible = "pwm-leds";

    led-0 {
        label = "PWM_LED";
        pwms = <&pwm0 0 1000000 PWM_POLARITY_INVERTED>;
        max-brightness = <255>;
    };
};
```

---

## 10. 嵌入式Linux常用平台

### 10.1 全志(Allwinner)

#### 常用型号

| 型号 | CPU | GPU | 特点 |
|------|-----|-----|------|
| H616 | 4x Cortex-A53 | Mali-G31 MP2 | 低成本4K解码 |
| H618 | 4x Cortex-A53 | Mali-G31 MP2 | H616增强版 |
| T527 | 4x A55 + 4x A55 | Mali-G57 MC2 | 高性能、NPU |
| V853 | A7 + RISC-V E907 | — | 低功耗、AI视觉 |

#### 生态特点

- 社区支持活跃（linux-sunxi社区）
- Tina SDK（基于OpenWrt/Buildroot）
- 主线Linux支持较好
- 文档相对开放（但部分仍受限）

### 10.2 瑞芯微(Rockchip)

| 型号 | CPU | GPU | 特点 |
|------|-----|-----|------|
| RK3568 | 4x A55 | Mali-G52 | 工业主流、PCIe 3.0 |
| RK3588 | 4x A76 + 4x A55 | Mali-G610 | 旗舰级、8K视频、6TOPS NPU |
| RK3566 | 4x A55 | Mali-G52 | 低成本版本 |
| RK3576 | 4x A72 + 4x A53 | Mali-G52 | 工业应用 |

#### 生态特点

- SDK完善（Rockchip SDK基于Buildroot）
- 主线Linux支持在改善
- NPU SDK（RKNN）功能强大
- 资料丰富、社区活跃

### 10.3 STM32MP1/MP2

| 型号 | CPU | 特点 |
|------|-----|------|
| STM32MP157 | 2x A7 + M4 | Cortex-M4处理实时任务 |
| STM32MP257 | 2x A35 + M33 | 新一代、NPU、PCIe |

#### 生态特点

- ST官方支持强大
- STM32CubeMX配置工具
- OpenSTLinux发行版
- A7跑Linux + M4跑裸机/FreeRTOS（异构架构）
- 工业级可靠性

### 10.4 NXP i.MX

| 型号 | CPU | 特点 |
|------|-----|------|
| i.MX6ULL | 1x A7 | 超低功耗、入门级 |
| i.MX8M Plus | 4x A53 + M7 | NPU、ISP、音频 |
| i.MX93 | 2x A55 + M33 | 低功耗AI、Ethos-U65 NPU |
| i.MX8ULP | 2x A35 + 1x A35 | 超低功耗 |

#### 生态特点

- 商业级支持
- Yocto BSP成熟
- 文档详尽
- 社区资源丰富（NXP社区、Toradex等）

### 10.5 平台选择建议

| 需求 | 推荐平台 |
|------|---------|
| 低成本消费电子 | Allwinner H616/H618 |
| 工业控制 | Rockchip RK3568 |
| 高性能/AI | Rockchip RK3588 |
| 工业可靠性 | STM32MP1/MP2 |
| 低功耗AI | NXP i.MX93 |
| 实时+Linux | STM32MP1(M4+Linux) |
| 商业产品长期支持 | NXP i.MX系列 |

---

## 11. 开发流程总结

### 11.1 从零搭建嵌入式Linux开发环境

```
┌──────────────────────────────────────────────────┐
│                  开发环境搭建                       │
├──────────────────────────────────────────────────┤
│                                                    │
│  1. 安装交叉编译工具链                               │
│     sudo apt install gcc-aarch64-linux-gnu         │
│                                                    │
│  2. 获取内核源码                                     │
│     git clone https://git.kernel.org/.../linux.git │
│                                                    │
│  3. 获取/安装Buildroot或Yocto                       │
│                                                    │
│  4. 获取芯片厂商BSP                                  │
│                                                    │
│  5. 配置TFTP/NFS服务器（开发阶段）                    │
│     sudo apt install tftpd-hpa nfs-kernel-server   │
│                                                    │
│  6. 安装串口终端工具                                  │
│     sudo apt install minicom picocom               │
│     或使用MobaXterm / PuTTY                        │
│                                                    │
│  7. 准备硬件（开发板、调试器、串口线等）                │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 11.2 驱动开发流程

```
1. 分析硬件
   ├── 阅读芯片数据手册
   ├── 了解外设寄存器
   ├── 确定接口类型（I2C/SPI/GPIO/Platform等）
   └── 确定中断、DMA需求

2. 编写设备树节点
   ├── 添加设备节点
   ├── 配置pinctrl
   ├── 配置时钟
   └── 设置status = "okay"

3. 编写驱动程序
   ├── 注册驱动（module_platform_driver等）
   ├── 实现probe/remove
   ├── 实现文件操作（read/write/ioctl等）
   ├── 处理中断
   └── 处理并发（锁、同步）

4. 编写Makefile/Kconfig
   ├── obj-m := my_driver.o
   └── 配置内核config

5. 编译与测试
   ├── 编译模块
   ├── insmod加载
   ├── 检查dmesg日志
   ├── 测试设备节点
   └── 用户空间程序测试

6. 调试与优化
   ├── printk / dynamic_debug
   ├── strace分析系统调用
   ├── 性能分析（perf）
   └── 内存检查（kmemleak）

7. 稳定性测试
   ├── 长时间运行测试
   ├── 压力测试
   ├── 冷热重启测试
   └── 异常断电测试
```

### 11.3 应用开发流程

```
1. 需求分析
   └── 确定功能、性能、接口需求

2. 选择开发框架
   ├── 纯C + POSIX API（最小依赖）
   ├── Qt（图形界面）
   ├── LVGL（嵌入式图形）
   └── GTK+（桌面级图形）

3. 交叉编译
   ├── 配置CMake/Makefile
   ├── 指定工具链
   └── 处理库依赖（静态/动态链接）

4. 部署与测试
   ├── SCP/ADB传输到目标板
   ├── 测试基本功能
   └── 性能测试

5. 系统集成
   ├── 编写systemd service文件
   ├── 配置开机自启
   └── 日志管理
```

### 11.4 系统集成与部署

```
1. 配置Buildroot/Yocto
   ├── 选择目标平台defconfig
   ├── 添加自定义包
   ├── 配置内核（设备树、驱动）
   └── 配置根文件系统

2. 构建镜像
   ├── 编译内核 + DTB
   ├── 编译U-Boot
   ├── 构建根文件系统
   └── 打包最终镜像

3. 烧录镜像
   ├── SD卡烧录（dd命令）
   ├── USB烧录（厂商工具）
   ├── 网络烧录（TFTP/NFS）
   └── OTA升级

4. 系统配置
   ├── 网络配置
   ├── 自启动服务
   ├── 看门狗配置
   └── 日志轮转

5. 量产准备
   ├── 烧录脚本
   ├── 自动化测试
   ├── 固件版本管理
   └── 安全加固（签名、加密）
```

---

## 附录

### A. 常用内核配置项

| 配置项 | 说明 |
|--------|------|
| `CONFIG_MODULES` | 支持可加载模块 |
| `CONFIG_OF` | 设备树支持 |
| `CONFIG_I2C` | I2C子系统 |
| `CONFIG_SPI` | SPI子系统 |
| `CONFIG_GPIO_CDEV` | 字符设备GPIO接口 |
| `CONFIG_INPUT` | 输入子系统 |
| `CONFIG_PWM` | PWM子系统 |
| `CONFIG_DEBUG_INFO` | 调试信息（GDB需要） |
| `CONFIG_KGDB` | 内核GDB调试 |
| `CONFIG_FTRACE` | 函数跟踪 |
| `CONFIG_DEBUG_KMEMLEAK` | 内存泄漏检测 |
| `CONFIG_PROVE_LOCKING` | 死锁检测(lockdep) |

### B. 常用调试命令

```bash
# 查看内核版本
uname -a

# 查看设备树
ls /sys/firmware/devicetree/base/
dtc -I fs /sys/firmware/devicetree/base

# 查看设备
cat /proc/devices
cat /proc/interrupts
cat /proc/meminfo
cat /proc/iomem

# 查看模块
lsmod
cat /proc/modules

# 查看GPIO状态
cat /sys/kernel/debug/gpio
cat /sys/class/gpio/gpiochip0/label

# 查看I2C总线
i2cdetect -l
i2cdetect -y 0        # 扫描I2C bus 0
i2cget -y 0 0x48 0x00 # 读I2C设备

# 查看SPI设备
ls /dev/spidev*

# 查看内核日志
dmesg
dmesg -w               # 实时查看
dmesg -l err           # 只看错误
```

### C. 参考资料

| 资源 | 链接/说明 |
|------|----------|
| 内核文档 | https://www.kernel.org/doc/html/latest/ |
| LDD3 | Linux Device Drivers 3rd Edition（经典教材，免费） |
| 设备树规范 | https://www.devicetree.org/specifications/ |
| Buildroot手册 | https://buildroot.org/downloads/manual/manual.html |
| Yocto文档 | https://docs.yoctoproject.org/ |
| Bootlin文档 | https://bootlin.com/docs/ |
| elixir.bootlin.com | 在线内核源码浏览 |
| CNX Software | 嵌入式Linux新闻与评测 |

---

> **学习建议**：
> 1. 先掌握C语言和Linux基本操作
> 2. 从内核模块开始，理解内核编程的基本模式
> 3. 学习设备树语法，理解硬件描述方式
> 4. 阅读一个完整的Platform驱动，掌握probe/remove流程
> 5. 动手实践：点灯 → 按键 → I2C设备 → SPI设备
> 6. 学习Buildroot，构建自己的Linux系统
> 7. 阅读内核源码（drivers/目录），学习优秀驱动的写法
