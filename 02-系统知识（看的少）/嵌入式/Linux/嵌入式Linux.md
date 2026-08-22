# 嵌入式Linux

## 核心概念

- **嵌入式Linux** - 运行在嵌入式设备上的Linux系统
- **Bootloader** - 引导加载程序(U-Boot)
- **根文件系统(RootFS)** - 系统文件集合
- **交叉编译** - 在x86上编译ARM程序

---

## 一、嵌入式Linux架构

### 1.1 系统组成

```
┌─────────────────────────────────┐
│           应用程序               │
├─────────────────────────────────┤
│         C库(glibc/musl)         │
├─────────────────────────────────┤
│         Linux内核               │
├─────────────────────────────────┤
│         Bootloader(U-Boot)      │
├─────────────────────────────────┤
│         硬件(ARM/RISC-V)        │
└─────────────────────────────────┘
```

---

### 1.2 启动流程

```
上电 → BootROM → U-Boot → Linux内核 → 根文件系统 → 应用程序
```

| 阶段 | 说明 |
|------|------|
| BootROM | 芯片固化代码，加载U-Boot |
| U-Boot | 初始化硬件，加载内核 |
| Linux内核 | 初始化驱动，挂载文件系统 |
| 根文件系统 | 挂载rootfs，启动init进程 |
| 应用程序 | 用户程序 |

---

## 二、交叉编译工具链

### 2.1 工具链安装

```bash
# Ubuntu安装ARM工具链
sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
sudo apt install gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf

# 验证
aarch64-linux-gnu-gcc --version
arm-linux-gnueabihf-gcc --version
```

---

### 2.2 交叉编译

```bash
# 编译
aarch64-linux-gnu-gcc -o hello hello.c

# 编译内核模块
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules

# 文件信息
file hello
# hello: ELF 64-bit LSB executable, ARM aarch64...
```

---

### 2.3 工具链组成

| 工具 | 说明 |
|------|------|
| gcc/g++ | 编译器 |
| ld | 链接器 |
| gdb | 调试器 |
| objdump | 反汇编 |
| readelf | 查看ELF |
| strip | 去除符号 |

---

## 三、U-Boot

### 3.1 U-Boot基础

**常用命令：**
```bash
# 查看环境变量
printenv

# 设置环境变量
setenv bootargs console=ttyS0,115200 root=/dev/mmcblk0p2

# 保存环境变量
saveenv

# 从SD卡加载内核
load mmc 0:1 0x80000000 Image
load mmc 0:1 0x83000000 dtb

# 启动内核
booti 0x80000000 - 0x83000000

# TFTP下载
tftp 0x80000000 Image

# NFS挂载
setenv bootargs console=ttyS0 root=/dev/nfs nfsroot=192.168.1.100:/rootfs ip=dhcp
```

---

### 3.2 U-Boot环境变量

| 变量 | 说明 |
|------|------|
| bootargs | 内核启动参数 |
| bootcmd | 自动启动命令 |
| ipaddr | 设备IP |
| serverip | TFTP服务器IP |
| bootdelay | 启动延时 |

**bootargs参数：**
```
console=ttyS0,115200    # 控制台
root=/dev/mmcblk0p2     # 根文件系统位置
rootfstype=ext4         # 文件系统类型
init=/sbin/init         # init程序
ip=dhcp                 # 网络配置
```

---

## 四、Linux内核

### 4.1 内核配置

```bash
# 查看默认配置
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig

# 菜单配置
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig

# 编译内核
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image -j$(nproc)

# 编译设备树
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- dtbs

# 编译模块
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules -j$(nproc)
```

---

### 4.2 内核模块

```c
// hello.c
#include <linux/module.h>
#include <linux/init.h>

static int __init hello_init(void) {
    pr_info("Hello, kernel!\n");
    return 0;
}

static void __exit hello_exit(void) {
    pr_info("Goodbye, kernel!\n");
}

module_init(hello_init);
module_exit(hello_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Author");
MODULE_DESCRIPTION("Hello Module");
```

**Makefile：**
```makefile
obj-m += hello.o

KDIR ?= /path/to/kernel

all:
	make -C $(KDIR) M=$(PWD) modules

clean:
	make -C $(KDIR) M=$(PWD) clean
```

---

### 4.3 内核启动参数

| 参数 | 说明 |
|------|------|
| console | 控制台设备 |
| root | 根文件系统 |
| rootfstype | 文件系统类型 |
| init | init程序路径 |
| mem | 内存大小 |
| ip | 网络配置 |
| quiet | 减少输出 |

---

## 五、根文件系统

### 5.1 文件系统类型

| 类型 | 说明 | 应用 |
|------|------|------|
| ext4 | 日志文件系统 | SD卡/eMMC |
| squashfs | 只读压缩 | 固件 |
| jffs2 | 日志闪存 | NOR Flash |
| ubifs | 闪存优化 | NAND Flash |
| tmpfs | 内存文件系统 | 临时文件 |
| procfs | 进程信息 | /proc |
| sysfs | 设备信息 | /sys |

---

### 5.2 根文件系统结构

```
/
├── bin/        # 基本命令
├── sbin/       # 系统命令
├── lib/        # 共享库
├── etc/        # 配置文件
├── dev/        # 设备节点
├── proc/       # 进程信息
├── sys/        # 系统信息
├── tmp/        # 临时文件
├── var/        # 可变数据
├── usr/        # 用户程序
└── opt/        # 可选软件
```

---

### 5.3 BusyBox

```bash
# 下载BusyBox
wget https://busybox.net/downloads/busybox-1.36.0.tar.bz2
tar xjf busybox-1.36.0.tar.bz2

# 配置
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig

# 编译
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc)

# 安装
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- install
# 输出到 _install 目录
```

**创建目录结构：**
```bash
cd _install
mkdir -p dev etc proc sys tmp lib
cat > etc/init.d/rcS << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /tmp
echo "Welcome to Embedded Linux!"
/bin/sh
EOF
chmod +x etc/init.d/rcS
```

---

## 六、Buildroot

### 6.1 Buildroot基础

```bash
# 下载
git clone https://github.com/buildroot/buildroot.git
cd buildroot

# 配置
make menuconfig

# 编译
make -j$(nproc)
```

**menuconfig选项：**
| 选项 | 说明 |
|------|------|
| Target Architecture | 目标架构 |
| Toolchain | 工具链 |
| System configuration | 系统配置 |
| Kernel | 内核配置 |
| Target packages | 软件包 |
| Filesystem images | 文件系统格式 |
| Bootloader | U-Boot配置 |

---

### 6.2 Buildroot配置示例

```bash
# 选择目标架构
Target options → Target Architecture → AArch64

# 选择工具链
Toolchain → Toolchain type → Buildroot toolchain

# 配置内核
Kernel → Linux Kernel → [*] Enable

# 添加软件包
Target packages → Networking applications → [*] openssh
Target packages → Interpreter languages → [*] python3

# 文件系统
Filesystem images → [*] ext2/3/4 → ext4
Filesystem images → [*] tar the root filesystem
```

---

### 6.3 自定义包

```bash
# package/myapp/myapp.mk
MYAPP_VERSION = 1.0
MYAPP_SITE = $(TOPDIR)/../myapp
MYAPP_SITE_METHOD = local

define MYAPP_BUILD_CMDS
    $(MAKE) CC="$(TARGET_CC)" -C $(@D)
endef

define MYAPP_INSTALL_TARGET_CMDS
    $(INSTALL) -D -m 0755 $(@D)/myapp $(TARGET_DIR)/usr/bin/myapp
endef

$(eval $(generic-package))
```

```bash
# package/myapp/Config.in
config BR2_PACKAGE_MYAPP
    bool "myapp"
    help
        My custom application.
```

---

## 七、Yocto

### 7.1 Yocto基础

**Yocto vs Buildroot：**
| 特性 | Yocto | Buildroot |
|------|-------|-----------|
| 复杂度 | 高 | 低 |
| 灵活性 | 高 | 中 |
| 包管理 | opkg/dpkg | 简单 |
| 镜像大小 | 较大 | 较小 |
| 学习曲线 | 陡峭 | 平缓 |
| 适用场景 | 产品级 | 原型/简单产品 |

---

### 7.2 Yocto构建

```bash
# 获取Poky
git clone https://git.yoctoproject.org/poky
cd poky

# 初始化构建环境
source oe-init-build-env build

# 配置
conf/local.conf:
  MACHINE = "qemux86-64"
  DISTRO = "poky"

# 构建镜像
bitbake core-image-minimal

# 运行QEMU
runqemu qemux86-64
```

---

### 7.3 Yocto层(Layer)

```bash
# 创建层
bitbake-layers create-layer meta-mylayer

# 添加层
bitbake-layers add-layer meta-mylayer

# 层结构
meta-mylayer/
├── conf/
│   └── layer.conf
├── recipes-example/
│   └── example/
│       └── example_0.1.bb
└── README
```

---

## 八、系统部署

### 8.1 SD卡制作

```bash
# 分区
sudo fdisk /dev/sdX
# 创建2个分区: boot(FAT32) + rootfs(ext4)

# 格式化
sudo mkfs.vfat -F 32 /dev/sdX1
sudo mkfs.ext4 /dev/sdX2

# 挂载
sudo mount /dev/sdX1 /mnt/boot
sudo mount /dev/sdX2 /mnt/rootfs

# 拷贝文件
sudo cp Image *.dtb /mnt/boot/
sudo tar xpf rootfs.tar -C /mnt/rootfs/

# 安装U-Boot
sudo dd if=u-boot-sunxi-with-spl.bin of=/dev/sdX bs=1024 seek=8
```

---

### 8.2 NFS根文件系统

```bash
# 服务器配置
sudo apt install nfs-kernel-server
echo "/path/to/rootfs *(rw,sync,no_root_squash)" | sudo tee -a /etc/exports
sudo exportfs -a

# U-Boot设置
setenv bootargs console=ttyS0,115200 root=/dev/nfs nfsroot=192.168.1.100:/path/to/rootfs ip=dhcp
```

---

### 8.3 系统更新

**SWUpdate：**
```bash
# 构建SWUpdate
make BR2_PACKAGE_SWUPDATE=y

# 制作SWU包
swu_desc="software = { images: ({filename: "rootfs.ext4.gz", device: "/dev/mmcblk0p2"}); };"
```

**RAUC：**
```bash
# 配置槽位
[system]
compatible=MyBoard

[slot.rootfs.0]
device=/dev/mmcblk0p2
type=ext4

[slot.rootfs.1]
device=/dev/mmcblk0p3
type=ext4
```

---

## 九、系统调试

### 9.1 串口调试

```bash
# minicom
minicom -D /dev/ttyUSB0 -b 115200

# screen
screen /dev/ttyUSB0 115200

# picocom
picocom -b 115200 /dev/ttyUSB0
```

---

### 9.2 GDB远程调试

```bash
# 目标板运行gdbserver
gdbserver :1234 ./application

# 主机连接
aarch64-linux-gnu-gdb ./application
(gdb) target remote 192.168.1.200:1234
(gdb) break main
(gdb) continue
```

---

### 9.3 strace

```bash
# 跟踪系统调用
strace ./application

# 跟踪特定调用
strace -e trace=open,read,write ./application

# 跟踪进程
strace -p 1234
```

---

### 9.4 性能分析

```bash
# perf
perf stat ./application
perf record ./application
perf report

# top/htop
top -p 1234

# 内存分析
valgrind --leak-check=full ./application
```

---

## 十、嵌入式Linux应用

### 10.1 守护进程

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <signal.h>

void daemonize(void) {
    pid_t pid = fork();
    if (pid > 0) exit(0);  // 父进程退出
    if (pid < 0) exit(1);

    setsid();  // 创建新会话

    pid = fork();
    if (pid > 0) exit(0);
    if (pid < 0) exit(1);

    umask(0);
    chdir("/");

    // 关闭标准IO
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
}

int main(void) {
    daemonize();

    while (1) {
        // 主循环
        sleep(1);
    }
    return 0;
}
```

---

### 10.2 systemd服务

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/myapp
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
systemctl enable myapp
systemctl start myapp
systemctl status myapp
journalctl -u myapp -f
```

---

## 附录：常用命令

### 系统信息

| 命令 | 说明 |
|------|------|
| uname -a | 内核信息 |
| cat /proc/cpuinfo | CPU信息 |
| cat /proc/meminfo | 内存信息 |
| df -h | 磁盘使用 |
| free -m | 内存使用 |
| lsmod | 已加载模块 |
| dmesg | 内核日志 |

### 网络命令

| 命令 | 说明 |
|------|------|
| ifconfig | 网络接口 |
| ip addr | IP地址 |
| ping | 网络测试 |
| netstat | 网络状态 |
| scp | 远程拷贝 |
| ssh | 远程登录 |

---

## 相关链接

- [[Linux基础]] - Linux基础命令
- [[Linux系统编程]] - 系统编程
- [[Linux驱动开发]] - 驱动开发
- [[Makefile与CMake]] - 构建系统
