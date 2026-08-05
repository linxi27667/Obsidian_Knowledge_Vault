# Shell编程详解

## 核心概念

- **Bash** - Bourne Again Shell
- **脚本** - 自动化命令序列
- **管道** - 命令间数据传递
- **正则表达式** - 文本匹配模式

---

## 一、Bash基础

### 1.1 变量

```bash
#!/bin/bash

# 变量赋值(等号两边不能有空格)
name="Linux"
version=5
pi=3.14159

# 使用变量
echo "System: $name"
echo "Version: ${version}"
echo "Pi: $pi"

# 只读变量
readonly name

# 删除变量(不能删除只读变量)
unset version

# 字符串操作
str="Hello World"
echo ${#str}          # 长度: 11
echo ${str:0:5}       # 子串: Hello
echo ${str/World/Bash} # 替换: Hello Bash
echo ${str^^}         # 大写: HELLO WORLD
echo ${str,,}         # 小写: hello world

# 数组
arr=(apple banana cherry)
echo ${arr[0]}        # 第一个元素
echo ${arr[@]}        # 所有元素
echo ${#arr[@]}       # 数组长度

# 关联数组(需要Bash 4+)
declare -A colors
colors[red]="#FF0000"
colors[green]="#00FF00"
colors[blue]="#0000FF"
echo ${colors[red]}

# 特殊变量
echo $0    # 脚本名称
echo $1    # 第一个参数
echo $#    # 参数个数
echo $@    # 所有参数
echo $?    # 上一个命令的退出状态
echo $$    # 当前进程ID
echo $!    # 后台最后一个进程ID
```

### 1.2 条件判断

```bash
#!/bin/bash

# if语句
if [ "$1" = "hello" ]; then
    echo "Hello!"
elif [ "$1" = "bye" ]; then
    echo "Goodbye!"
else
    echo "Unknown command"
fi

# 数值比较
# -eq  等于
# -ne  不等于
# -gt  大于
# -ge  大于等于
# -lt  小于
# -le  小于等于

if [ "$#" -eq 0 ]; then
    echo "No arguments"
fi

# 字符串比较
# =   等于
# !=  不等于
# -z  为空
# -n  不为空

if [ -z "$name" ]; then
    echo "Name is empty"
fi

# 文件测试
# -f  是文件
# -d  是目录
# -e  存在
# -r  可读
# -w  可写
# -x  可执行
# -s  非空

if [ -f "/etc/passwd" ]; then
    echo "File exists"
fi

if [ -d "/tmp" ]; then
    echo "Directory exists"
fi

# 逻辑运算
if [ "$age" -ge 18 ] && [ "$age" -le 65 ]; then
    echo "Working age"
fi

if [ "$role" = "admin" ] || [ "$role" = "root" ]; then
    echo "Privileged user"
fi

# case语句
case "$1" in
    start)
        echo "Starting..."
        ;;
    stop)
        echo "Stopping..."
        ;;
    restart)
        echo "Restarting..."
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac

# [[ ]] 扩展测试(Bash特有)
if [[ "$str" == Hello* ]]; then
    echo "Starts with Hello"
fi

if [[ "$num" =~ ^[0-9]+$ ]]; then
    echo "Is a number"
fi
```

### 1.3 循环

```bash
#!/bin/bash

# for循环
for i in 1 2 3 4 5; do
    echo "Number: $i"
done

# C风格for循环
for ((i=0; i<10; i++)); do
    echo "i = $i"
done

# 范围
for i in {1..10}; do
    echo $i
done

# 遍历文件
for file in *.txt; do
    echo "Processing: $file"
done

# 遍历数组
arr=(apple banana cherry)
for fruit in "${arr[@]}"; do
    echo "Fruit: $fruit"
done

# while循环
count=0
while [ $count -lt 10 ]; do
    echo "Count: $count"
    ((count++))
done

# 读取文件
while IFS= read -r line; do
    echo "Line: $line"
done < /etc/passwd

# until循环
until [ $count -eq 0 ]; do
    echo "Count: $count"
    ((count--))
done

# select菜单
echo "Select a color:"
select color in red green blue; do
    echo "You selected: $color"
    break
done

# break和continue
for i in {1..10}; do
    if [ $i -eq 5 ]; then
        continue  # 跳过5
    fi
    if [ $i -eq 8 ]; then
        break  # 到8停止
    fi
    echo $i
done
```

---

## 二、函数

### 2.1 函数定义

```bash
#!/bin/bash

# 函数定义
greet() {
    echo "Hello, $1!"
}

# 调用函数
greet "World"

# 带返回值
add() {
    local result=$(( $1 + $2 ))
    echo $result
}

sum=$(add 3 5)
echo "Sum: $sum"

# local变量
my_function() {
    local local_var="I'm local"
    global_var="I'm global"
    echo "$local_var"
}

my_function
echo "$global_var"  # 可以访问
# echo "$local_var"  # 不可以访问

# 递归
factorial() {
    if [ $1 -le 1 ]; then
        echo 1
    else
        local prev=$(factorial $(( $1 - 1 )))
        echo $(( $1 * prev ))
    fi
}

result=$(factorial 5)
echo "5! = $result"

# 函数作为参数
apply() {
    local func=$1
    shift
    $func "$@"
}

apply greet "Bash"
```

### 2.2 错误处理

```bash
#!/bin/bash

# 错误处理
set -e  # 遇到错误立即退出
set -u  # 使用未定义变量报错
set -o pipefail  # 管道中任意命令失败则失败

# trap捕获信号
cleanup() {
    echo "Cleaning up..."
    rm -f /tmp/tempfile
    exit 1
}

trap cleanup EXIT INT TERM

# 错误处理函数
error_handler() {
    echo "Error occurred at line $1"
    exit 1
}

trap 'error_handler $LINENO' ERR

# 自定义错误
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root"
        return 1
    fi
    return 0
}

if ! check_root; then
    exit 1
fi

# 并行错误处理
command1 &
pid1=$!
command2 &
pid2=$!

wait $pid1
status1=$?
wait $pid2
status2=$?

if [ $status1 -ne 0 ] || [ $status2 -ne 0 ]; then
    echo "One or more commands failed"
    exit 1
fi
```

---

## 三、文本处理

### 3.1 正则表达式

```bash
#!/bin/bash

# grep - 搜索文本
grep "pattern" file.txt
grep -i "pattern" file.txt     # 忽略大小写
grep -r "pattern" /path/       # 递归搜索
grep -n "pattern" file.txt     # 显示行号
grep -c "pattern" file.txt     # 计数
grep -v "pattern" file.txt     # 反向匹配
grep -E "regex" file.txt       # 扩展正则

# sed - 流编辑器
sed 's/old/new/' file.txt      # 替换第一个
sed 's/old/new/g' file.txt     # 替换所有
sed -i 's/old/new/g' file.txt  # 原地替换
sed '3d' file.txt              # 删除第3行
sed '/pattern/d' file.txt      # 删除匹配行
sed -n '5,10p' file.txt        # 打印5-10行

# awk - 文本处理
awk '{print $1}' file.txt      # 打印第一列
awk -F: '{print $1}' /etc/passwd  # 指定分隔符
awk '$3 > 100' file.txt        # 条件过滤
awk '{sum += $1} END {print sum}' file.txt  # 求和

# cut - 截取字段
cut -d: -f1 /etc/passwd        # 按:分割取第1列
cut -c1-10 file.txt            # 取前10个字符

# sort - 排序
sort file.txt                  # 字母排序
sort -n file.txt               # 数字排序
sort -r file.txt               # 逆序
sort -k2 file.txt              # 按第2列排序

# uniq - 去重
sort file.txt | uniq           # 去重
sort file.txt | uniq -c        # 计数

# tr - 字符转换
echo "hello" | tr 'a-z' 'A-Z'  # 转大写
echo "hello" | tr -d 'aeiou'   # 删除元音

# wc - 统计
wc -l file.txt                 # 行数
wc -w file.txt                 # 单词数
wc -c file.txt                 # 字节数
```

### 3.2 文本处理脚本

```bash
#!/bin/bash

# CSV处理
process_csv() {
    local file=$1
    local delimiter=${2:-,}

    while IFS="$delimiter" read -r col1 col2 col3 rest; do
        echo "Name: $col1, Age: $col2, City: $col3"
    done < "$file"
}

# JSON处理(使用jq)
process_json() {
    local file=$1

    # 读取字段
    local name=$(jq -r '.name' "$file")
    local age=$(jq -r '.age' "$file")
    echo "Name: $name, Age: $age"

    # 遍历数组
    jq -r '.items[] | "\(.id): \(.name)"' "$file"
}

# 日志分析
analyze_log() {
    local logfile=$1

    echo "=== Log Analysis ==="
    echo "Total lines: $(wc -l < "$logfile")"
    echo "Error count: $(grep -c 'ERROR' "$logfile")"
    echo "Warning count: $(grep -c 'WARN' "$logfile")"

    echo ""
    echo "Top 10 errors:"
    grep 'ERROR' "$logfile" | sort | uniq -c | sort -rn | head -10
}

# 批量重命名
batch_rename() {
    local pattern=$1
    local replacement=$2

    for file in *"$pattern"*; do
        local newname="${file/$pattern/$replacement}"
        mv "$file" "$newname"
        echo "Renamed: $file -> $newname"
    done
}
```

---

## 四、系统管理

### 4.1 进程管理

```bash
#!/bin/bash

# 进程信息
get_process_info() {
    local pid=$1
    ps -p $pid -o pid,ppid,user,%cpu,%mem,command
}

# 查找进程
find_process() {
    local name=$1
    pgrep -l "$name"
}

# 后台运行
run_background() {
    local cmd=$1
    nohup $cmd > /dev/null 2>&1 &
    echo "PID: $!"
}

# 等待进程
wait_for_process() {
    local pid=$1
    local timeout=${2:-30}

    local elapsed=0
    while kill -0 $pid 2>/dev/null; do
        if [ $elapsed -ge $timeout ]; then
            echo "Timeout reached"
            kill $pid
            return 1
        fi
        sleep 1
        ((elapsed++))
    done
    return 0
}

# 进程监控
monitor_process() {
    local pid=$1
    local interval=${2:-5}

    while kill -0 $pid 2>/dev/null; do
        local cpu=$(ps -p $pid -o %cpu | tail -1)
        local mem=$(ps -p $pid -o %mem | tail -1)
        echo "$(date): CPU=$cpu%, MEM=$mem%"
        sleep $interval
    done
}

# 杀死进程树
kill_tree() {
    local pid=$1
    local children=$(pgrep -P $pid)
    for child in $children; do
        kill_tree $child
    done
    kill $pid 2>/dev/null
}
```

### 4.2 系统信息

```bash
#!/bin/bash

# 系统信息
system_info() {
    echo "=== System Information ==="
    echo "Hostname: $(hostname)"
    echo "OS: $(uname -o)"
    echo "Kernel: $(uname -r)"
    echo "Arch: $(uname -m)"
    echo "Uptime: $(uptime -p)"
}

# CPU信息
cpu_info() {
    echo "=== CPU Information ==="
    echo "Model: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2)"
    echo "Cores: $(nproc)"
    echo "Usage: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%"
}

# 内存信息
memory_info() {
    echo "=== Memory Information ==="
    free -h
}

# 磁盘信息
disk_info() {
    echo "=== Disk Information ==="
    df -h
}

# 网络信息
network_info() {
    echo "=== Network Information ==="
    ip addr show
    echo ""
    echo "=== DNS ==="
    cat /etc/resolv.conf
}

# 系统负载
load_info() {
    echo "=== System Load ==="
    uptime
    echo ""
    echo "=== Top Processes ==="
    ps aux --sort=-%cpu | head -10
}
```

### 4.3 服务管理

```bash
#!/bin/bash

# systemd服务管理
service_start() {
    local service=$1
    sudo systemctl start "$service"
    echo "Started $service"
}

service_stop() {
    local service=$1
    sudo systemctl stop "$service"
    echo "Stopped $service"
}

service_restart() {
    local service=$1
    sudo systemctl restart "$service"
    echo "Restarted $service"
}

service_status() {
    local service=$1
    systemctl status "$service"
}

service_enable() {
    local service=$1
    sudo systemctl enable "$service"
    echo "Enabled $service"
}

service_disable() {
    local service=$1
    sudo systemctl disable "$service"
    echo "Disabled $service"
}

# 查看日志
view_logs() {
    local service=$1
    local lines=${2:-100}
    journalctl -u "$service" -n "$lines" --no-pager
}

# 服务监控
monitor_service() {
    local service=$1
    local interval=${2:-60}

    while true; do
        if ! systemctl is-active --quiet "$service"; then
            echo "$(date): $service is down, restarting..."
            sudo systemctl restart "$service"
        fi
        sleep "$interval"
    done
}
```

---

## 五、网络脚本

### 5.1 网络工具

```bash
#!/bin/bash

# 检查主机是否可达
check_host() {
    local host=$1
    local timeout=${2:-5}

    if ping -c 1 -W "$timeout" "$host" > /dev/null 2>&1; then
        echo "$host is reachable"
        return 0
    else
        echo "$host is unreachable"
        return 1
    fi
}

# 检查端口是否开放
check_port() {
    local host=$1
    local port=$2
    local timeout=${3:-5}

    if timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        echo "$host:$port is open"
        return 0
    else
        echo "$host:$port is closed"
        return 1
    fi
}

# HTTP请求
http_get() {
    local url=$1
    curl -s -o /dev/null -w "%{http_code}" "$url"
}

http_post() {
    local url=$1
    local data=$2
    curl -s -X POST -d "$data" "$url"
}

# 下载文件
download_file() {
    local url=$1
    local output=$2

    if command -v wget > /dev/null; then
        wget -O "$output" "$url"
    elif command -v curl > /dev/null; then
        curl -o "$output" "$url"
    else
        echo "Neither wget nor curl found"
        return 1
    fi
}

# 网络接口信息
get_ip() {
    local interface=${1:-eth0}
    ip addr show "$interface" | grep 'inet ' | awk '{print $2}' | cut -d/ -f1
}

# 端口扫描
port_scan() {
    local host=$1
    local start=${2:-1}
    local end=${3:-1024}

    for port in $(seq $start $end); do
        if check_port "$host" "$port" 1 > /dev/null 2>&1; then
            echo "Port $port is open"
        fi
    done
}
```

### 5.2 远程操作

```bash
#!/bin/bash

# SSH命令执行
remote_exec() {
    local host=$1
    local user=$2
    local command=$3

    ssh "$user@$host" "$command"
}

# SCP文件传输
remote_copy() {
    local source=$1
    local dest=$2

    scp -r "$source" "$dest"
}

# 批量执行
batch_exec() {
    local hosts_file=$1
    local command=$2

    while IFS= read -r host; do
        echo "=== $host ==="
        ssh "$host" "$command"
    done < "$hosts_file"
}

# SSH密钥生成
generate_ssh_key() {
    local email=$1
    ssh-keygen -t ed25519 -C "$email"
}

# SSH密钥分发
distribute_key() {
    local host=$1
    local user=$2

    ssh-copy-id "$user@$host"
}
```

---

## 六、实用脚本

### 6.1 备份脚本

```bash
#!/bin/bash

# 配置
BACKUP_DIR="/backup"
SOURCE_DIR="/data"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${DATE}.tar.gz"

# 创建备份
create_backup() {
    echo "Creating backup: $BACKUP_FILE"
    tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" -C "$(dirname $SOURCE_DIR)" "$(basename $SOURCE_DIR)"

    if [ $? -eq 0 ]; then
        echo "Backup created successfully"
        # 计算大小
        local size=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
        echo "Backup size: $size"
    else
        echo "Backup failed"
        return 1
    fi
}

# 清理旧备份
cleanup_old_backups() {
    echo "Cleaning up backups older than $RETENTION_DAYS days"
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
}

# 验证备份
verify_backup() {
    local backup_file=$1
    echo "Verifying backup: $backup_file"
    tar -tzf "$backup_file" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "Backup is valid"
        return 0
    else
        echo "Backup is corrupted"
        return 1
    fi
}

# 主流程
main() {
    create_backup
    verify_backup "${BACKUP_DIR}/${BACKUP_FILE}"
    cleanup_old_backups
}

main
```

### 6.2 监控脚本

```bash
#!/bin/bash

# 配置
ALERT_EMAIL="admin@example.com"
CPU_THRESHOLD=80
MEM_THRESHOLD=90
DISK_THRESHOLD=90

# CPU监控
check_cpu() {
    local usage=$(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d. -f1)
    if [ "$usage" -gt "$CPU_THRESHOLD" ]; then
        send_alert "CPU Alert" "CPU usage is ${usage}%"
    fi
}

# 内存监控
check_memory() {
    local usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    if [ "$usage" -gt "$MEM_THRESHOLD" ]; then
        send_alert "Memory Alert" "Memory usage is ${usage}%"
    fi
}

# 磁盘监控
check_disk() {
    while read -r line; do
        local usage=$(echo "$line" | awk '{print $5}' | sed 's/%//')
        local mount=$(echo "$line" | awk '{print $6}')
        if [ "$usage" -gt "$DISK_THRESHOLD" ]; then
            send_alert "Disk Alert" "Disk $mount is ${usage}% full"
        fi
    done < <(df -h | grep '^/dev/')
}

# 发送告警
send_alert() {
    local subject=$1
    local body=$2

    echo "$body" | mail -s "$subject" "$ALERT_EMAIL"
    echo "$(date): Alert sent - $subject"
}

# 主监控循环
monitor() {
    local interval=${1:-300}  # 默认5分钟

    while true; do
        check_cpu
        check_memory
        check_disk
        sleep "$interval"
    done
}

monitor
```

### 6.3 部署脚本

```bash
#!/bin/bash

# 配置
APP_NAME="myapp"
DEPLOY_DIR="/opt/$APP_NAME"
BACKUP_DIR="/opt/backup"
REPO_URL="https://github.com/user/repo.git"
BRANCH="main"

# 部署
deploy() {
    echo "Deploying $APP_NAME..."

    # 备份当前版本
    if [ -d "$DEPLOY_DIR" ]; then
        local backup_name="${APP_NAME}_$(date +%Y%m%d_%H%M%S)"
        cp -r "$DEPLOY_DIR" "${BACKUP_DIR}/${backup_name}"
        echo "Backup created: $backup_name"
    fi

    # 拉取最新代码
    if [ -d "$DEPLOY_DIR/.git" ]; then
        cd "$DEPLOY_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        git clone -b "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
    fi

    # 安装依赖
    install_dependencies

    # 构建
    build

    # 重启服务
    restart_service

    echo "Deployment completed"
}

# 安装依赖
install_dependencies() {
    cd "$DEPLOY_DIR"
    if [ -f "package.json" ]; then
        npm install --production
    elif [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    elif [ -f "Gemfile" ]; then
        bundle install --deployment
    fi
}

# 构建
build() {
    cd "$DEPLOY_DIR"
    if [ -f "Makefile" ]; then
        make build
    elif [ -f "CMakeLists.txt" ]; then
        mkdir -p build && cd build
        cmake .. && make
    fi
}

# 重启服务
restart_service() {
    if command -v systemctl > /dev/null; then
        sudo systemctl restart "$APP_NAME"
    elif command -v supervisorctl > /dev/null; then
        sudo supervisorctl restart "$APP_NAME"
    fi
}

# 回滚
rollback() {
    local backup_name=$1
    local backup_path="${BACKUP_DIR}/${backup_name}"

    if [ ! -d "$backup_path" ]; then
        echo "Backup not found: $backup_name"
        return 1
    fi

    echo "Rolling back to $backup_name..."
    rm -rf "$DEPLOY_DIR"
    cp -r "$backup_path" "$DEPLOY_DIR"
    restart_service
    echo "Rollback completed"
}

# 主流程
case "$1" in
    deploy)
        deploy
        ;;
    rollback)
        rollback "$2"
        ;;
    *)
        echo "Usage: $0 {deploy|rollback <version>}"
        exit 1
        ;;
esac
```

---

## 附录：常用命令速查

| 命令 | 说明 |
|------|------|
| `grep` | 搜索文本 |
| `sed` | 流编辑器 |
| `awk` | 文本处理 |
| `find` | 查找文件 |
| `xargs` | 参数传递 |
| `sort` | 排序 |
| `uniq` | 去重 |
| `cut` | 截取字段 |
| `tr` | 字符转换 |
| `wc` | 统计 |

---

## 相关链接

- [[Shell编程]] - Shell基础
- [[Linux基础]] - Linux
- [[Linux系统编程]] - 系统编程
- [[Makefile与CMake详解]] - 构建系统
