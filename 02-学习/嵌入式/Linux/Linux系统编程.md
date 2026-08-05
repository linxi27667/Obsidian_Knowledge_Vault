# Linux系统编程

## 核心概念

- **系统调用** - 用户程序请求内核服务的接口
- **进程** - 程序的执行实例
- **线程** - 轻量级进程，共享地址空间
- **IPC** - 进程间通信机制

---

## 一、文件I/O

### 1.1 文件描述符

| 描述符 | 说明 |
|--------|------|
| 0 | stdin |
| 1 | stdout |
| 2 | stderr |

---

### 1.2 基本文件操作

```c
#include <fcntl.h>
#include <unistd.h>

// 打开文件
int fd = open("file.txt", O_RDONLY);
if (fd == -1) {
    perror("open");
    return -1;
}

// 读取文件
char buf[1024];
ssize_t n = read(fd, buf, sizeof(buf));

// 写入文件
ssize_t n = write(fd, "Hello", 5);

// 定位文件
off_t pos = lseek(fd, 0, SEEK_SET);

// 关闭文件
close(fd);
```

---

### 1.3 文件状态

```c
#include <sys/stat.h>

struct stat st;
stat("file.txt", &st);

// 文件类型
if (S_ISREG(st.st_mode))  // 普通文件
if (S_ISDIR(st.st_mode))  // 目录
if (S_ISCHR(st.st_mode))  // 字符设备

// 文件权限
if (st.st_mode & S_IRUSR)  // 所有者可读
if (st.st_mode & S_IWUSR)  // 所有者可写
```

---

### 1.4 文件锁

```c
#include <fcntl.h>

struct flock fl;
fl.l_type = F_WRLCK;      // 写锁
fl.l_whence = SEEK_SET;
fl.l_start = 0;
fl.l_len = 0;             // 整个文件

fcntl(fd, F_SETLKW, &fl); // 阻塞等待锁
```

---

## 二、进程管理

### 2.1 进程创建

```c
#include <unistd.h>

pid_t pid = fork();

if (pid == 0) {
    // 子进程
    printf("Child PID: %d\n", getpid());
} else if (pid > 0) {
    // 父进程
    printf("Parent PID: %d, Child PID: %d\n", getpid(), pid);
} else {
    // 错误
    perror("fork");
}
```

---

### 2.2 进程执行

```c
// exec系列
execl("/bin/ls", "ls", "-l", NULL);
execlp("ls", "ls", "-l", NULL);
execv("/bin/ls", argv);
execvp("ls", argv);
```

---

### 2.3 进程等待

```c
#include <sys/wait.h>

int status;
pid_t pid = wait(&status);

if (WIFEXITED(status)) {
    printf("Exited with status %d\n", WEXITSTATUS(status));
} else if (WIFSIGNALED(status)) {
    printf("Killed by signal %d\n", WTERMSIG(status));
}
```

---

### 2.4 进程状态

| 状态 | 说明 |
|------|------|
| R | 运行中 |
| S | 睡眠 |
| D | 不可中断睡眠 |
| Z | 僵尸进程 |
| T | 停止 |

---

## 三、线程

### 3.1 线程创建

```c
#include <pthread.h>

void* thread_func(void* arg) {
    printf("Thread ID: %lu\n", pthread_self());
    return NULL;
}

pthread_t thread;
pthread_create(&thread, NULL, thread_func, NULL);
pthread_join(thread, NULL);
```

---

### 3.2 线程同步

**互斥锁：**
```c
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

pthread_mutex_lock(&mutex);
// 临界区
pthread_mutex_unlock(&mutex);
```

**条件变量：**
```c
pthread_cond_t cond = PTHREAD_COND_INITIALIZER;

// 等待
pthread_mutex_lock(&mutex);
while (!condition) {
    pthread_cond_wait(&cond, &mutex);
}
pthread_mutex_unlock(&mutex);

// 通知
pthread_cond_signal(&cond);      // 唤醒一个
pthread_cond_broadcast(&cond);   // 唤醒所有
```

**读写锁：**
```c
pthread_rwlock_t rwlock = PTHREAD_RWLOCK_INITIALIZER;

// 读锁
pthread_rwlock_rdlock(&rwlock);
// 读操作
pthread_rwlock_unlock(&rwlock);

// 写锁
pthread_rwlock_wrlock(&rwlock);
// 写操作
pthread_rwlock_unlock(&rwlock);
```

---

### 3.3 线程属性

```c
pthread_attr_t attr;
pthread_attr_init(&attr);
pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
pthread_attr_setstacksize(&attr, 1024 * 1024);  // 1MB栈

pthread_create(&thread, &attr, thread_func, NULL);

pthread_attr_destroy(&attr);
```

---

## 四、进程间通信(IPC)

### 4.1 管道

**匿名管道：**
```c
int pipefd[2];
pipe(pipefd);

// pipefd[0] - 读端
// pipefd[1] - 写端

if (fork() == 0) {
    // 子进程写
    close(pipefd[0]);
    write(pipefd[1], "Hello", 5);
    close(pipefd[1]);
} else {
    // 父进程读
    close(pipefd[1]);
    char buf[10];
    read(pipefd[0], buf, sizeof(buf));
    close(pipefd[0]);
}
```

**命名管道(FIFO)：**
```c
mkfifo("/tmp/myfifo", 0666);

// 写进程
int fd = open("/tmp/myfifo", O_WRONLY);
write(fd, "Hello", 5);
close(fd);

// 读进程
int fd = open("/tmp/myfifo", O_RDONLY);
char buf[10];
read(fd, buf, sizeof(buf));
close(fd);
```

---

### 4.2 消息队列

```c
#include <mqueue.h>

// 创建消息队列
mqd_t mq = mq_open("/myqueue", O_CREAT | O_WRONLY, 0644, NULL);

// 发送消息
mq_send(mq, "Hello", 5, 0);

// 接收消息
char buf[10];
unsigned int prio;
mq_receive(mq, buf, sizeof(buf), &prio);

// 关闭和删除
mq_close(mq);
mq_unlink("/myqueue");
```

---

### 4.3 共享内存

```c
#include <sys/shm.h>

// 创建共享内存
int shmid = shmget(IPC_PRIVATE, 4096, IPC_CREAT | 0666);

// 附加共享内存
char *shm = (char*)shmat(shmid, NULL, 0);

// 使用共享内存
strcpy(shm, "Hello");

// 分离共享内存
shmdt(shm);

// 删除共享内存
shmctl(shmid, IPC_RMID, NULL);
```

**POSIX共享内存：**
```c
#include <sys/mman.h>

// 创建
int fd = shm_open("/myshm", O_CREAT | O_RDWR, 0666);
ftruncate(fd, 4096);

// 映射
char *shm = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

// 使用
strcpy(shm, "Hello");

// 清理
munmap(shm, 4096);
close(fd);
shm_unlink("/myshm");
```

---

### 4.4 信号量

```c
#include <semaphore.h>

sem_t sem;
sem_init(&sem, 0, 0);  // 初始值0

// 等待
sem_wait(&sem);

// 发送
sem_post(&sem);

// 销毁
sem_destroy(&sem);
```

---

### 4.5 信号

```c
#include <signal.h>

void signal_handler(int signo) {
    printf("Received signal %d\n", signo);
}

// 注册信号处理
signal(SIGINT, signal_handler);
signal(SIGTERM, signal_handler);

// 发送信号
kill(pid, SIGINT);
raise(SIGINT);  // 发送给自己

// 信号集
sigset_t set;
sigemptyset(&set);
sigaddset(&set, SIGINT);
sigprocmask(SIG_BLOCK, &set, NULL);  // 阻塞信号
```

---

## 五、内存管理

### 5.1 虚拟内存

```
虚拟地址空间：
┌─────────────┐ 高地址
│    栈       │ ← 向下增长
├─────────────┤
│     ↓       │
│             │
│     ↑       │
├─────────────┤
│    堆       │ ← 向上增长
├─────────────┤
│   BSS段     │
├─────────────┤
│   数据段    │
├─────────────┤
│   代码段    │
└─────────────┘ 低地址
```

---

### 5.2 内存映射

```c
#include <sys/mman.h>

// 映射文件
int fd = open("file.txt", O_RDWR);
char *addr = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

// 使用
addr[0] = 'A';

// 解除映射
munmap(addr, 4096);
close(fd);
```

---

### 5.3 动态内存

```c
#include <stdlib.h>

// 分配
void *ptr = malloc(1024);
void *ptr = calloc(10, 1024);  // 初始化为0
void *ptr = realloc(ptr, 2048);

// 释放
free(ptr);
```

---

## 六、Socket编程

### 6.1 TCP Socket

```c
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

// 创建socket
int sockfd = socket(AF_INET, SOCK_STREAM, 0);

// 绑定地址
struct sockaddr_in addr;
addr.sin_family = AF_INET;
addr.sin_port = htons(8080);
addr.sin_addr.s_addr = INADDR_ANY;
bind(sockfd, (struct sockaddr*)&addr, sizeof(addr));

// 监听
listen(sockfd, 5);

// 接受连接
int clientfd = accept(sockfd, NULL, NULL);

// 读写
char buf[1024];
read(clientfd, buf, sizeof(buf));
write(clientfd, "Hello", 5);

// 关闭
close(clientfd);
close(sockfd);
```

---

### 6.2 UDP Socket

```c
// 创建socket
int sockfd = socket(AF_INET, SOCK_DGRAM, 0);

// 绑定地址
struct sockaddr_in addr;
addr.sin_family = AF_INET;
addr.sin_port = htons(8080);
addr.sin_addr.s_addr = INADDR_ANY;
bind(sockfd, (struct sockaddr*)&addr, sizeof(addr));

// 发送
struct sockaddr_in dest;
dest.sin_family = AF_INET;
dest.sin_port = htons(8081);
inet_pton(AF_INET, "127.0.0.1", &dest.sin_addr);
sendto(sockfd, "Hello", 5, 0, (struct sockaddr*)&dest, sizeof(dest));

// 接收
char buf[1024];
struct sockaddr_in src;
socklen_t len = sizeof(src);
recvfrom(sockfd, buf, sizeof(buf), 0, (struct sockaddr*)&src, &len);
```

---

## 七、多路复用

### 7.1 select

```c
#include <sys/select.h>

fd_set readfds;
FD_ZERO(&readfds);
FD_SET(fd1, &readfds);
FD_SET(fd2, &readfds);

struct timeval tv;
tv.tv_sec = 5;
tv.tv_usec = 0;

int ret = select(maxfd + 1, &readfds, NULL, NULL, &tv);

if (FD_ISSET(fd1, &readfds)) {
    // fd1可读
}
```

---

### 7.2 poll

```c
#include <poll.h>

struct pollfd fds[2];
fds[0].fd = fd1;
fds[0].events = POLLIN;
fds[1].fd = fd2;
fds[1].events = POLLIN;

int ret = poll(fds, 2, 5000);  // 5秒超时

if (fds[0].revents & POLLIN) {
    // fd1可读
}
```

---

### 7.3 epoll

```c
#include <sys/epoll.h>

// 创建epoll
int epfd = epoll_create1(0);

// 添加fd
struct epoll_event ev;
ev.events = EPOLLIN;
ev.data.fd = fd;
epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &ev);

// 等待事件
struct epoll_event events[10];
int n = epoll_wait(epfd, events, 10, 5000);

for (int i = 0; i < n; i++) {
    if (events[i].events & EPOLLIN) {
        // 可读
    }
}
```

---

## 八、定时器

### 8.1 alarm

```c
#include <unistd.h>

alarm(5);  // 5秒后发送SIGALRM
```

---

### 8.2 setitimer

```c
#include <sys/time.h>

struct itimerval timer;
timer.it_value.tv_sec = 5;      // 首次5秒
timer.it_value.tv_usec = 0;
timer.it_interval.tv_sec = 1;   // 之后每1秒
timer.it_interval.tv_usec = 0;

setitimer(ITIMER_REAL, &timer, NULL);
```

---

### 8.3 timerfd

```c
#include <sys/timerfd.h>

int tfd = timerfd_create(CLOCK_MONOTONIC, 0);

struct itimerspec ts;
ts.it_value.tv_sec = 5;
ts.it_value.tv_nsec = 0;
ts.it_interval.tv_sec = 1;
ts.it_interval.tv_nsec = 0;

timerfd_settime(tfd, 0, &ts, NULL);

// 读取定时器事件
uint64_t exp;
read(tfd, &exp, sizeof(exp));
```

---

## 九、日志系统

### 9.1 syslog

```c
#include <syslog.h>

openlog("myapp", LOG_PID, LOG_USER);
syslog(LOG_INFO, "Application started");
syslog(LOG_ERR, "Error: %s", strerror(errno));
closelog();
```

---

### 9.2 自定义日志

```c
#include <stdio.h>
#include <time.h>

#define LOG(level, fmt, ...) do { \
    time_t now = time(NULL); \
    struct tm *tm = localtime(&now); \
    printf("[%04d-%02d-%02d %02d:%02d:%02d] [%s] " fmt "\n", \
           tm->tm_year+1900, tm->tm_mon+1, tm->tm_mday, \
           tm->tm_hour, tm->tm_min, tm->tm_sec, \
           level, ##__VA_ARGS__); \
} while(0)

#define LOG_INFO(fmt, ...) LOG("INFO", fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...) LOG("ERROR", fmt, ##__VA_ARGS__)
```

---

## 十、守护进程

### 10.1 创建守护进程

```c
#include <unistd.h>
#include <sys/stat.h>

void daemonize() {
    // 创建子进程
    pid_t pid = fork();
    if (pid > 0) exit(0);
    
    // 创建新会话
    setsid();
    
    // 改变工作目录
    chdir("/");
    
    // 重设文件权限掩码
    umask(0);
    
    // 关闭标准文件描述符
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
}
```

---

## 附录：系统调用速查表

### 文件操作

| 调用 | 说明 |
|------|------|
| open | 打开文件 |
| read | 读取文件 |
| write | 写入文件 |
| close | 关闭文件 |
| lseek | 定位文件 |
| stat | 获取文件状态 |

### 进程控制

| 调用 | 说明 |
|------|------|
| fork | 创建进程 |
| exec | 执行程序 |
| wait | 等待子进程 |
| exit | 退出进程 |

### 线程

| 调用 | 说明 |
|------|------|
| pthread_create | 创建线程 |
| pthread_join | 等待线程 |
| pthread_mutex_lock | 加锁 |
| pthread_mutex_unlock | 解锁 |

### IPC

| 调用 | 说明 |
|------|------|
| pipe | 创建管道 |
| shmget | 创建共享内存 |
| shmat | 附加共享内存 |
| mq_open | 打开消息队列 |
| sem_init | 初始化信号量 |

---

## 相关链接

- [[Linux基础]] - Linux基础命令
- [[Linux驱动开发]] - 内核驱动开发
- [[嵌入式Linux]] - 嵌入式Linux实践
