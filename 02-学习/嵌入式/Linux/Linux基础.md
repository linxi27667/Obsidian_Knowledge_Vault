# Linux基础

## 核心概念

- **Linux** - 开源类Unix操作系统内核
- **Shell** - 命令行解释器
- **文件系统** - 层次化目录结构
- **权限管理** - 用户、组、权限位

---

## 一、Linux概述

### 1.1 Linux发展历史

| 时间 | 事件 |
|------|------|
| 1991 | Linus Torvalds发布Linux 0.01 |
| 1992 | 采用GPL许可证 |
| 1994 | Linux 1.0发布 |
| 2003 | Linux 2.6发布 |
| 2015 | Linux 4.0发布 |
| 2023 | Linux 6.x发布 |

---

### 1.2 Linux发行版

| 发行版 | 特点 | 应用场景 |
|--------|------|---------|
| Ubuntu | 易用、社区活跃 | 桌面、服务器 |
| Debian | 稳定、软件丰富 | 服务器 |
| CentOS/RHEL | 企业级、长期支持 | 企业服务器 |
| Arch Linux | 滚动更新、高度定制 | 桌面 |
| Alpine | 轻量、安全 | 容器 |
| Yocto/Buildroot | 定制化 | 嵌入式 |

---

### 1.3 Linux内核组成

```
┌─────────────────────────────────────┐
│           用户空间                   │
│  ┌─────┐ ┌─────┐ ┌─────┐          │
│  │应用程序│ │库  │ │Shell│          │
│  └─────┘ └─────┘ └─────┘          │
├─────────────────────────────────────┤
│           系统调用接口               │
├─────────────────────────────────────┤
│           内核空间                   │
│  ┌───────────────────────────────┐ │
│  │ 进程管理 │ 内存管理 │ 文件系统 │ │
│  ├───────────────────────────────┤ │
│  │ 网络协议栈│ 设备驱动│          │ │
│  └───────────────────────────────┘ │
├─────────────────────────────────────┤
│           硬件                       │
└─────────────────────────────────────┘
```

---

## 二、文件系统

### 2.1 目录结构

```
/                    # 根目录
├── bin              # 基本命令
├── boot             # 启动文件
├── dev              # 设备文件
├── etc              # 配置文件
├── home             # 用户主目录
├── lib              # 库文件
├── media            # 可移动媒体
├── mnt              # 挂载点
├── opt              # 可选软件
├── proc             # 进程信息
├── root             # root主目录
├── sbin             # 系统命令
├── sys              # 系统信息
├── tmp              # 临时文件
├── usr              # 用户程序
│   ├── bin          # 用户命令
│   ├── lib          # 用户库
│   ├── local        # 本地安装
│   └── share        # 共享数据
└── var              # 可变数据
    ├── log          # 日志文件
    └── tmp          # 临时文件
```

---

### 2.2 文件类型

| 类型 | 标识 | 说明 |
|------|------|------|
| 普通文件 | - | 文本、二进制 |
| 目录 | d | 文件夹 |
| 链接文件 | l | 符号链接 |
| 字符设备 | c | 按字符访问 |
| 块设备 | b | 按块访问 |
| 套接字 | s | 网络通信 |
| 管道 | p | 进程间通信 |

---

### 2.3 文件权限

**权限位：**
```
rwxrwxrwx
│││││││││
││││││└┴┴ 其他用户权限
│││└┴┴   组权限
└┴┴     所有者权限
```

**权限值：**
| 权限 | 值 | 说明 |
|------|-----|------|
| r | 4 | 读 |
| w | 2 | 写 |
| x | 1 | 执行 |

**chmod命令：**
```bash
chmod 755 file    # rwxr-xr-x
chmod u+x file    # 给所有者添加执行权限
chmod g-w file    # 移除组写权限
chmod o=r file    # 其他用户只读
```

---

### 2.4 硬链接与软链接

**硬链接：**
```bash
ln file1 file2    # 创建硬链接
```
- 共享同一inode
- 不能跨文件系统
- 不能链接目录

**软链接：**
```bash
ln -s file1 file2  # 创建软链接
```
- 独立inode
- 可以跨文件系统
- 可以链接目录

---

## 三、常用命令

### 3.1 文件操作

```bash
# 列出文件
ls -la            # 详细列表
ls -lh            # 人类可读大小

# 切换目录
cd /path          # 切换目录
cd ~              # 回到主目录
cd -              # 回到上次目录

# 创建/删除
mkdir dir         # 创建目录
mkdir -p dir/sub  # 递归创建
rmdir dir         # 删除空目录
rm -rf dir        # 递归删除

# 复制/移动
cp file1 file2    # 复制文件
cp -r dir1 dir2   # 递归复制目录
mv file1 file2    # 移动/重命名

# 查看文件
cat file          # 查看内容
less file         # 分页查看
head -n 10 file   # 查看前10行
tail -n 10 file   # 查看后10行
tail -f file      # 实时查看
```

---

### 3.2 文本处理

```bash
# 搜索
grep "pattern" file        # 搜索模式
grep -r "pattern" dir      # 递归搜索
grep -i "pattern" file     # 忽略大小写
grep -n "pattern" file     # 显示行号

# 排序
sort file                  # 排序
sort -n file               # 数字排序
sort -r file               # 逆序
sort -k2 file              # 按第2列排序

# 去重
sort file | uniq           # 去重

# 文本处理
awk '{print $1}' file      # 打印第1列
sed 's/old/new/g' file     # 替换
cut -d: -f1 /etc/passwd    # 提取字段

# 管道和重定向
command > file             # 输出重定向
command >> file            # 追加重定向
command < file             # 输入重定向
command1 | command2        # 管道
```

---

### 3.3 查找文件

```bash
# find命令
find /path -name "*.c"           # 按名查找
find /path -type f -size +1M     # 按大小查找
find /path -mtime -7             # 按修改时间查找
find /path -exec command {} \;   # 执行命令

# locate命令
locate filename                   # 快速查找
updatedb                         # 更新数据库

# which/whereis
which command                    # 查找命令位置
whereis command                  # 查找命令和手册
```

---

### 3.4 文件压缩

```bash
# tar
tar -czf archive.tar.gz dir/    # 创建gzip压缩包
tar -cjf archive.tar.bz2 dir/   # 创建bzip2压缩包
tar -xzf archive.tar.gz         # 解压gzip
tar -xjf archive.tar.bz2        # 解压bzip2
tar -xzf archive.tar.gz -C dir  # 解压到指定目录

# zip/unzip
zip -r archive.zip dir/         # 创建zip
unzip archive.zip               # 解压zip

# gzip/gunzip
gzip file                       # 压缩文件
gunzip file.gz                  # 解压文件
```

---

## 四、用户管理

### 4.1 用户相关文件

| 文件 | 说明 |
|------|------|
| /etc/passwd | 用户信息 |
| /etc/shadow | 密码信息 |
| /etc/group | 组信息 |

**passwd文件格式：**
```
username:x:UID:GID:comment:home:shell
```

---

### 4.2 用户操作

```bash
# 添加用户
useradd -m -s /bin/bash username
passwd username

# 删除用户
userdel -r username

# 修改用户
usermod -aG groupname username

# 切换用户
su - username
sudo command
```

---

### 4.3 组操作

```bash
# 添加组
groupadd groupname

# 删除组
groupdel groupname

# 添加用户到组
usermod -aG groupname username

# 查看组
groups username
id username
```

---

## 五、进程管理

### 5.1 进程概念

**进程状态：**
- R：运行
- S：睡眠
- D：不可中断睡眠
- Z：僵尸
- T：停止

---

### 5.2 进程操作

```bash
# 查看进程
ps aux                   # 所有进程
ps -ef                   # 完整格式
top                      # 实时监控
htop                     # 增强版top

# 终止进程
kill PID                 # 发送SIGTERM
kill -9 PID              # 发送SIGKILL
killall name             # 按名称终止

# 后台运行
command &                # 后台运行
nohup command &          # 后台运行，不受终端影响
jobs                     # 查看后台任务
fg %n                    # 调到前台
bg %n                    # 后台继续
```

---

### 5.3 系统监控

```bash
# CPU使用
top
vmstat 1
mpstat -P ALL 1

# 内存使用
free -h
cat /proc/meminfo

# 磁盘使用
df -h
du -sh *
iostat -x 1

# 网络
netstat -tuln
ss -tuln
iftop
```

---

## 六、Shell编程

### 6.1 基本语法

**变量：**
```bash
NAME="Linux"
echo $NAME
echo ${NAME}

# 特殊变量
$0    # 脚本名
$1    # 第1个参数
$#    # 参数个数
$@    # 所有参数
$?    # 上一条命令返回值
```

---

### 6.2 条件判断

```bash
# if语句
if [ condition ]; then
    # 代码
elif [ condition ]; then
    # 代码
else
    # 代码
fi

# 条件表达式
[ -f file ]      # 文件存在
[ -d dir ]       # 目录存在
[ -z string ]    # 字符串为空
[ -n string ]    # 字符串非空
[ a = b ]        # 字符串相等
[ a != b ]       # 字符串不等
[ num -eq num ]  # 数字相等
[ num -ne num ]  # 数字不等
[ num -gt num ]  # 大于
[ num -lt num ]  # 小于
```

---

### 6.3 循环

```bash
# for循环
for i in 1 2 3 4 5; do
    echo $i
done

for i in $(seq 1 10); do
    echo $i
done

for file in *.c; do
    echo $file
done

# while循环
while [ condition ]; do
    # 代码
done

# until循环
until [ condition ]; do
    # 代码
done
```

---

### 6.4 函数

```bash
# 定义函数
function greet() {
    echo "Hello, $1!"
    return 0
}

# 调用函数
greet "World"

# 获取返回值
greet "World"
echo $?
```

---

### 6.5 脚本示例

```bash
#!/bin/bash

# 备份脚本
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d)
SOURCE="/data"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 执行备份
tar -czf ${BACKUP_DIR}/backup_${DATE}.tar.gz ${SOURCE}

# 检查结果
if [ $? -eq 0 ]; then
    echo "备份成功"
else
    echo "备份失败"
    exit 1
fi

# 删除7天前的备份
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

exit 0
```

---

## 七、网络配置

### 7.1 网络命令

```bash
# 查看网络
ifconfig                  # 网络接口
ip addr                   # IP地址
ip route                  # 路由表
ping host                 # 测试连通性
traceroute host           # 路由跟踪
nslookup domain           # DNS查询
dig domain                # DNS查询

# 网络配置
ifconfig eth0 192.168.1.100 netmask 255.255.255.0
route add default gw 192.168.1.1

# 网络文件
/etc/network/interfaces   # Debian网络配置
/etc/sysconfig/network-scripts/ifcfg-eth0  # RHEL网络配置
/etc/resolv.conf          # DNS配置
/etc/hosts                # 主机名解析
```

---

### 7.2 防火墙

```bash
# iptables
iptables -L                        # 列出规则
iptables -A INPUT -p tcp --dport 22 -j ACCEPT  # 允许SSH
iptables -A INPUT -p tcp --dport 80 -j ACCEPT  # 允许HTTP
iptables -A INPUT -j DROP           # 拒绝其他

# firewalld
firewall-cmd --list-all
firewall-cmd --add-service=http --permanent
firewall-cmd --reload

# ufw (Ubuntu)
ufw status
ufw allow 22/tcp
ufw enable
```

---

## 八、软件包管理

### 8.1 Debian/Ubuntu (apt)

```bash
apt update                     # 更新软件列表
apt upgrade                    # 升级软件
apt install package            # 安装软件
apt remove package             # 卸载软件
apt search keyword             # 搜索软件
apt show package               # 显示软件信息
```

---

### 8.2 RHEL/CentOS (yum/dnf)

```bash
yum update                     # 更新
yum install package            # 安装
yum remove package             # 卸载
yum search keyword             # 搜索
yum info package               # 信息
```

---

### 8.3 源码编译安装

```bash
# 典型步骤
./configure --prefix=/usr/local
make
make install

# CMake项目
mkdir build && cd build
cmake ..
make
make install
```

---

## 九、系统服务

### 9.1 systemd

```bash
# 服务管理
systemctl start service        # 启动
systemctl stop service         # 停止
systemctl restart service      # 重启
systemctl status service       # 状态
systemctl enable service       # 开机启动
systemctl disable service      # 禁止开机启动

# 查看服务
systemctl list-units --type=service
systemctl list-unit-files --type=service
```

---

### 9.2 自定义服务

**服务文件：** `/etc/systemd/system/myservice.service`
```ini
[Unit]
Description=My Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/myservice
Restart=always
User=myuser

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl start myservice
systemctl enable myservice
```

---

## 十、Shell环境

### 10.1 环境变量

```bash
# 查看环境变量
env
printenv
echo $PATH

# 设置环境变量
export VAR="value"

# 永久设置
# ~/.bashrc 或 ~/.profile
export PATH=$PATH:/new/path
```

---

### 10.2 Shell配置文件

| 文件 | 说明 |
|------|------|
| /etc/profile | 系统级配置 |
| ~/.bash_profile | 用户级配置 |
| ~/.bashrc | 交互式Shell配置 |
| ~/.bash_logout | 退出时执行 |

---

### 10.3 别名

```bash
# 设置别名
alias ll='ls -la'
alias gs='git status'

# 永久设置
# 添加到 ~/.bashrc
```

---

## 十一、正则表达式

### 11.1 基本语法

| 符号 | 说明 |
|------|------|
| . | 任意字符 |
| * | 前一个字符0次或多次 |
| + | 前一个字符1次或多次 |
| ? | 前一个字符0次或1次 |
| ^ | 行首 |
| $ | 行尾 |
| [] | 字符类 |
| [^] | 否定字符类 |
| \d | 数字 |
| \w | 单词字符 |
| \s | 空白字符 |

---

### 11.2 示例

```bash
# 匹配IP地址
grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' file

# 匹配邮箱
grep -E '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' file

# 匹配日期
grep -E '[0-9]{4}-[0-9]{2}-[0-9]{2}' file
```

---

## 十二、嵌入式Linux

### 12.1 交叉编译

```bash
# 安装交叉编译工具链
sudo apt install gcc-arm-linux-gnueabihf

# 编译
arm-linux-gnueabihf-gcc main.c -o main

# 设置环境变量
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm
```

---

### 12.2 Bootloader (U-Boot)

```bash
# U-Boot命令
printenv                    # 查看环境变量
setenv bootargs "..."       # 设置启动参数
bootm addr                  # 启动内核
tftpboot addr file          # TFTP下载
```

---

### 12.3 内核编译

```bash
# 配置内核
make menuconfig

# 编译内核
make zImage
make dtbs
make modules

# 安装
make modules_install
make install
```

---

### 12.4 根文件系统

**目录结构：**
```
rootfs/
├── bin/
├── dev/
├── etc/
├── lib/
├── proc/
├── sbin/
├── sys/
├── tmp/
├── usr/
└── var/
```

**工具：**
- BusyBox：提供基本命令
- Buildroot：构建根文件系统
- Yocto：完整构建系统

---

## 附录：命令速查表

### 文件操作

| 命令 | 说明 |
|------|------|
| ls | 列出文件 |
| cd | 切换目录 |
| cp | 复制 |
| mv | 移动 |
| rm | 删除 |
| mkdir | 创建目录 |
| chmod | 修改权限 |
| chown | 修改所有者 |

### 文本处理

| 命令 | 说明 |
|------|------|
| cat | 查看文件 |
| grep | 搜索文本 |
| sort | 排序 |
| awk | 文本处理 |
| sed | 流编辑器 |

### 系统管理

| 命令 | 说明 |
|------|------|
| ps | 查看进程 |
| top | 系统监控 |
| kill | 终止进程 |
| df | 磁盘使用 |
| free | 内存使用 |

---

## 相关链接

- [[Shell编程]] - Shell脚本深入
- [[Linux系统编程]] - 系统调用
- [[Linux驱动开发]] - 内核驱动
- [[嵌入式Linux]] - 嵌入式实践
