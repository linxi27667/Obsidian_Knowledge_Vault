# Linux内核详解

## 核心概念

- **进程管理** - 进程调度、上下文切换
- **内存管理** - 虚拟内存、页表
- **文件系统** - VFS、inode
- **设备驱动** - 字符/块设备

---

## 一、内核架构

### 1.1 内核子系统

```
┌─────────────────────────────────────────┐
│           用户空间                       │
│  应用程序、库函数                        │
├─────────────────────────────────────────┤
│           系统调用接口                   │
│  open, read, write, ioctl, mmap         │
├─────────────────────────────────────────┤
│           内核空间                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │进程管理  │ │内存管理  │ │文件系统  │  │
│  │调度器   │ │页表管理  │ │VFS     │  │
│  └─────────┘ └─────────┘ └─────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │设备驱动  │ │网络协议栈│ │安全模块  │  │
│  │字符/块  │ │TCP/IP   │ │SELinux  │  │
│  └─────────┘ └─────────┘ └─────────┘  │
├─────────────────────────────────────────┤
│           硬件抽象层                     │
│  体系结构相关代码                        │
├─────────────────────────────────────────┤
│           硬件                           │
└─────────────────────────────────────────┘
```

### 1.2 内核配置

```bash
# 内核配置
make menuconfig     # 文本界面
make xconfig        # 图形界面(KDE)
make gconfig        # 图形界面(GTK)

# 配置选项
# CONFIG_MODULES - 可加载模块支持
# CONFIG_SMP - 多处理器支持
# CONFIG_PREEMPT - 内核抢占
# CONFIG_HZ_1000 - 1000Hz时钟频率
# CONFIG_DEBUG_INFO - 调试信息

# 编译内核
make -j$(nproc)
make modules
make modules_install
make install

# 内核模块
lsmod                 # 列出模块
modprobe module_name  # 加载模块
rmmod module_name     # 卸载模块
modinfo module_name   # 模块信息
```

---

## 二、进程管理

### 2.1 进程描述符

```c
// 任务结构体(简化)
struct task_struct {
    volatile long state;        // 进程状态
    pid_t pid;                  // 进程ID
    pid_t tgid;                 // 线程组ID

    struct task_struct *parent; // 父进程
    struct list_head children;  // 子进程链表
    struct list_head sibling;   // 兄弟进程链表

    // 调度
    int prio;                   // 优先级
    int static_prio;            // 静态优先级
    unsigned int policy;        // 调度策略
    unsigned int rt_priority;   // 实时优先级

    // 内存
    struct mm_struct *mm;       // 内存描述符

    // 文件
    struct fs_struct *fs;       // 文件系统信息
    struct files_struct *files; // 打开文件表

    // 信号
    struct signal_struct *signal;
    sigset_t blocked;

    // 时间
    u64 start_time;             // 启动时间
    u64 utime;                  // 用户态时间
    u64 stime;                  // 内核态时间
};

// 进程状态
#define TASK_RUNNING            0
#define TASK_INTERRUPTIBLE      1
#define TASK_UNINTERRUPTIBLE    2
#define __TASK_STOPPED          4
#define __TASK_TRACED           8
#define EXIT_ZOMBIE             16
#define EXIT_DEAD               32
```

### 2.2 进程调度

```c
// CFS调度器(完全公平调度)
struct sched_entity {
    struct rb_node run_node;    // 红黑树节点
    unsigned int on_rq;         // 是否在运行队列
    u64 exec_start;             // 开始执行时间
    u64 sum_exec_runtime;       // 总执行时间
    u64 vruntime;               // 虚拟运行时间
    u64 prev_sum_exec_runtime;  // 上次总执行时间
};

// 调度类
struct sched_class {
    struct sched_class *next;

    void (*enqueue_task) (struct rq *rq, struct task_struct *p, int flags);
    void (*dequeue_task) (struct rq *rq, struct task_struct *p, int flags);
    void (*yield_task)   (struct rq *rq);

    void (*check_preempt_curr)(struct rq *rq, struct task_struct *p, int flags);

    struct task_struct * (*pick_next_task)(struct rq *rq);
    void (*put_prev_task)(struct rq *rq, struct task_struct *p);

    void (*set_curr_task)(struct rq *rq);
    void (*task_tick)    (struct rq *rq, struct task_struct *p, int queued);
};

// CFS调度器实现
static void enqueue_task_fair(struct rq *rq, struct task_struct *p, int flags) {
    struct cfs_rq *cfs_rq = cfs_rq_of(se);
    struct sched_entity *se = &p->se;

    // 更新虚拟运行时间
    update_curr(cfs_rq);

    // 添加到红黑树
    __enqueue_entity(cfs_rq, se);
    cfs_rq->nr_running++;
}

static struct task_struct *pick_next_task_fair(struct rq *rq) {
    struct cfs_rq *cfs_rq = &rq->cfs;
    struct sched_entity *se;

    // 选择最左节点(vruntime最小)
    se = __pick_first_entity(cfs_rq);
    if (!se) return NULL;

    return container_of(se, struct task_struct, se);
}

// 虚拟运行时间计算
static void update_curr(struct cfs_rq *cfs_rq) {
    struct sched_entity *curr = cfs_rq->curr;
    u64 now = rq_clock_task(rq_of(cfs_rq));
    u64 delta_exec = now - curr->exec_start;

    curr->sum_exec_runtime += delta_exec;
    curr->exec_start = now;

    // vruntime = 实际时间 * NICE_0_LOAD / 权重
    curr->vruntime += calc_delta_fair(delta_exec, curr);
}
```

### 2.3 系统调用

```c
// 系统调用表
asmlinkage long sys_read(unsigned int fd, char __user *buf, size_t count);
asmlinkage long sys_write(unsigned int fd, const char __user *buf, size_t count);
asmlinkage long sys_open(const char __user *filename, int flags, umode_t mode);
asmlinkage long sys_close(unsigned int fd);
asmlinkage long sys_ioctl(unsigned int fd, unsigned int cmd, unsigned long arg);

// 系统调用实现示例
SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count) {
    struct fd f = fdget_pos(fd);
    if (!f.file) return -EBADF;

    // 权限检查
    if (!(f.file->f_mode & FMODE_READ)) {
        fdput_pos(f);
        return -EBADF;
    }

    // 调用文件操作
    ssize_t ret = vfs_read(f.file, buf, count, &f.file->f_pos);

    fdput_pos(f);
    return ret;
}

// 用户空间到内核空间复制
static inline long copy_from_user(void *to, const void __user *from, unsigned long n) {
    if (access_ok(VERIFY_READ, from, n)) {
        return __copy_from_user(to, from, n);
    }
    return n;
}

// 内核空间到用户空间复制
static inline long copy_to_user(void __user *to, const void *from, unsigned long n) {
    if (access_ok(VERIFY_WRITE, to, n)) {
        return __copy_to_user(to, from, n);
    }
    return n;
}
```

---

## 三、内存管理

### 3.1 页表管理

```c
// 页表项
typedef struct {
    unsigned long pte;  // 页表项值
} pte_t;

// 页全局目录(PGD)
typedef struct {
    unsigned long pgd;
} pgd_t;

// 虚拟地址结构(4级页表)
// PGD(9位) | PMD(9位) | PTE(9位) | Offset(12位)

// 页表操作
static inline int pte_present(pte_t pte) {
    return pte.pte & _PAGE_PRESENT;
}

static inline int pte_write(pte_t pte) {
    return pte.pte & _PAGE_RW;
}

static inline int pte_user(pte_t pte) {
    return pte.pte & _PAGE_USER;
}

// 地址转换
unsigned long virt_to_phys(unsigned long virt) {
    pgd_t *pgd;
    pmd_t *pmd;
    pte_t *pte;

    pgd = pgd_offset(current->mm, virt);
    if (pgd_none(*pgd)) return 0;

    pmd = pmd_offset(pgd, virt);
    if (pmd_none(*pmd)) return 0;

    pte = pte_offset_map(pmd, virt);
    if (!pte_present(*pte)) return 0;

    return (pte_val(*pte) & PAGE_MASK) | (virt & ~PAGE_MASK);
}

// 页面分配
struct page *alloc_pages(gfp_t gfp_mask, unsigned int order) {
    return __alloc_pages(gfp_mask, order, &contig_page_data.node_zonelists[gfp_to_alloc_flags(gfp_mask)]);
}

// 页面释放
void __free_pages(struct page *page, unsigned int order) {
    if (put_page_testzero(page)) {
        free_pages_prepare(page, order);
        free_one_page(page_to_nid(page), page, order);
    }
}
```

### 3.2 虚拟内存管理

```c
// 内存描述符
struct mm_struct {
    struct vm_area_struct *mmap;        // VMA链表
    struct rb_root mm_rb;               // VMA红黑树
    pgd_t *pgd;                         // 页全局目录

    unsigned long start_code, end_code; // 代码段
    unsigned long start_data, end_data; // 数据段
    unsigned long start_brk, brk;       // 堆
    unsigned long start_stack;          // 栈

    unsigned long total_vm;             // 总页面数
    unsigned long locked_vm;            // 锁定页面数
    unsigned long pinned_vm;            // 固定页面数
    unsigned long data_vm;              // 数据页面数
    unsigned long exec_vm;              // 可执行页面数
};

// 虚拟内存区域
struct vm_area_struct {
    unsigned long vm_start;     // 起始地址
    unsigned long vm_end;       // 结束地址
    pgprot_t vm_page_prot;      // 页面保护
    unsigned long vm_flags;     // 标志

    struct rb_node vm_rb;       // 红黑树节点
    struct mm_struct *vm_mm;    // 所属mm
    struct vm_area_struct *vm_next; // 链表指针

    // 操作
    const struct vm_operations_struct *vm_ops;
};

// 缺页处理
static int handle_pte_fault(struct mm_struct *mm, struct vm_area_struct *vma,
                            unsigned long address, pte_t *pte, pmd_t *pmd,
                            unsigned int flags) {
    pte_t entry;

    if (!pte_present(*pte)) {
        if (pte_none(*pte)) {
            // 匿名页面
            return do_anonymous_page(mm, vma, address, pte, pmd, flags);
        }
        // 按需加载
        return do_fault(mm, vma, address, pte, pmd, flags, entry);
    }

    // 写时复制(COW)
    if (flags & FAULT_FLAG_WRITE) {
        if (!pte_write(*pte)) {
            return do_wp_page(mm, vma, address, pte, pmd, pte);
        }
    }

    return 0;
}
```

### 3.3 Slab分配器

```c
// Slab缓存
struct kmem_cache {
    struct kmem_cache_cpu __percpu *cpu_slab;
    unsigned long flags;
    unsigned long min_partial;
    int size;               // 对象大小
    int object_size;        // 实际对象大小
    int offset;             // 偏移
    struct kmem_cache_order_objects oo;
    struct kmem_cache_node *node[MAX_NUMNODES];
};

// 创建Slab缓存
struct kmem_cache *kmem_cache_create(const char *name, size_t size,
                                      size_t align, unsigned long flags,
                                      void (*ctor)(void *)) {
    struct kmem_cache *s;

    s = kmem_cache_zalloc(kmem_cache_cache, GFP_KERNEL);
    s->name = name;
    s->size = size;
    s->object_size = size;
    s->align = align;

    // 初始化CPU slab
    init_kmem_cache_nodes(s);

    return s;
}

// 分配对象
void *kmem_cache_alloc(struct kmem_cache *s, gfp_t gfpflags) {
    void *object;
    struct kmem_cache_cpu *c;

    // 从CPU slab分配
    c = raw_cpu_ptr(s->cpu_slab);
    if (c->freelist) {
        object = c->freelist;
        c->freelist = object_next(object);
        return object;
    }

    // 从node slab分配
    return __slab_alloc(s, gfpflags, NUMA_NO_NODE, _RET_IP_, size);
}

// 释放对象
void kmem_cache_free(struct kmem_cache *s, void *x) {
    struct kmem_cache_cpu *c;
    void **object = (void **)x;

    c = raw_cpu_ptr(s->cpu_slab);
    if (c->freelist) {
        object_next(object) = c->freelist;
        c->freelist = object;
    }
}
```

---

## 四、文件系统

### 4.1 VFS层

```c
// 超级块
struct super_block {
    struct list_head s_list;
    dev_t s_dev;
    unsigned long s_blocksize;
    loff_t s_maxbytes;
    struct file_system_type *s_type;
    const struct super_operations *s_op;
    struct dentry *s_root;
    struct mutex s_lock;
};

// 超级块操作
struct super_operations {
    struct inode *(*alloc_inode)(struct super_block *sb);
    void (*destroy_inode)(struct inode *);
    void (*dirty_inode)(struct inode *, int flags);
    int (*write_inode)(struct inode *, struct writeback_control *wbc);
    void (*evict_inode)(struct inode *);
    void (*put_super)(struct super_block *);
    int (*sync_fs)(struct super_block *sb, int wait);
};

// 索引节点
struct inode {
    umode_t i_mode;         // 文件类型和权限
    unsigned short i_opflags;
    kuid_t i_uid;           // 所有者
    kgid_t i_gid;           // 组
    unsigned int i_flags;
    const struct inode_operations *i_op;
    struct super_block *i_sb;
    struct address_space *i_mapping;
    unsigned long i_ino;    // inode号
    loff_t i_size;          // 文件大小
    struct timespec i_atime; // 访问时间
    struct timespec i_mtime; // 修改时间
    struct timespec i_ctime; // 状态改变时间
};

// inode操作
struct inode_operations {
    struct dentry * (*lookup)(struct inode *, struct dentry *, unsigned int);
    int (*permission)(struct inode *, int);
    int (*create)(struct inode *, struct dentry *, umode_t, bool);
    int (*link)(struct dentry *, struct inode *, struct dentry *);
    int (*unlink)(struct inode *, struct dentry *);
    int (*mkdir)(struct inode *, struct dentry *, umode_t);
    int (*rmdir)(struct inode *, struct dentry *);
};

// 目录项
struct dentry {
    unsigned int d_flags;
    seqcount_t d_seq;
    struct hlist_bl_node d_hash;
    struct dentry *d_parent;
    struct qstr d_name;
    struct inode *d_inode;
    const struct dentry_operations *d_op;
    struct super_block *d_sb;
};

// 文件
struct file {
    union {
        struct llist_node f_llist;
        struct rcu_head f_rcuhead;
    };
    struct path f_path;
    struct inode *f_inode;
    const struct file_operations *f_op;
    atomic_long_t f_count;
    unsigned int f_flags;
    fmode_t f_mode;
    loff_t f_pos;
    struct mutex f_pos_lock;
};
```

### 4.2 设备驱动框架

```c
// 字符设备
struct cdev {
    struct kobject kobj;
    struct module *owner;
    const struct file_operations *ops;
    struct list_head list;
    dev_t dev;
    unsigned int count;
};

// 注册字符设备
int cdev_add(struct cdev *p, dev_t dev, unsigned count) {
    p->dev = dev;
    p->count = count;
    return kobj_map(cdev_map, dev, count, NULL, exact_match, exact_lock, p);
}

// 文件操作
static const struct file_operations my_fops = {
    .owner = THIS_MODULE,
    .open = my_open,
    .release = my_release,
    .read = my_read,
    .write = my_write,
    .unlocked_ioctl = my_ioctl,
    .mmap = my_mmap,
    .poll = my_poll,
};

// 设备注册
static int __init my_init(void) {
    dev_t dev;
    int ret;

    // 分配设备号
    ret = alloc_chrdev_region(&dev, 0, 1, "my_device");
    if (ret < 0) return ret;

    // 初始化cdev
    cdev_init(&my_cdev, &my_fops);
    my_cdev.owner = THIS_MODULE;

    // 添加cdev
    ret = cdev_add(&my_cdev, dev, 1);
    if (ret < 0) goto err_cdev;

    // 创建设备类
    my_class = class_create(THIS_MODULE, "my_class");

    // 创建设备节点
    device_create(my_class, NULL, dev, NULL, "my_device");

    return 0;

err_cdev:
    unregister_chrdev_region(dev, 1);
    return ret;
}

static void __exit my_exit(void) {
    device_destroy(my_class, my_dev);
    class_destroy(my_class);
    cdev_del(&my_cdev);
    unregister_chrdev_region(my_dev, 1);
}

module_init(my_init);
module_exit(my_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Developer");
MODULE_DESCRIPTION("My Character Device");
```

---

## 五、中断处理

### 5.1 中断管理

```c
// 中断描述符
struct irq_desc {
    irq_flow_handler_t handle_irq;
    struct irq_chip *chip;
    struct irqaction *action;
    unsigned int irq;
    unsigned int depth;
    unsigned int irq_count;
    const char *name;
};

// 中断处理程序
typedef irqreturn_t (*irq_handler_t)(int irq, void *dev_id);

// 注册中断
int request_irq(unsigned int irq, irq_handler_t handler,
                unsigned long flags, const char *name, void *dev) {
    struct irqaction *action;

    action = kzalloc(sizeof(struct irqaction), GFP_KERNEL);
    if (!action) return -ENOMEM;

    action->handler = handler;
    action->flags = flags;
    action->name = name;
    action->dev_id = dev;

    return setup_irq(irq, action);
}

// 中断处理
irqreturn_t my_irq_handler(int irq, void *dev_id) {
    // 读取中断状态
    u32 status = readl(base + IRQ_STATUS);

    // 处理中断
    if (status & IRQ_DATA_READY) {
        // 数据就绪
        wake_up_interruptible(&wait_queue);
    }

    // 清除中断
    writel(status, base + IRQ_CLEAR);

    return IRQ_HANDLED;
}

// 上半部/下半部
// 上半部: 快速处理，关中断
// 下半部: 延迟处理，开中断

// 软中断
static void my_softirq_handler(struct softirq_action *h) {
    // 处理延迟工作
}

open_softirq(MY_SOFTIRQ, my_softirq_handler);

// 任务队列
static void my_work_handler(struct work_struct *work) {
    // 处理工作
}

DECLARE_WORK(my_work, my_work_handler);
schedule_work(&my_work);

// Tasklet
static void my_tasklet_handler(unsigned long data) {
    // 处理任务
}

DECLARE_TASKLET(my_tasklet, my_tasklet_handler, 0);
tasklet_schedule(&my_tasklet);
```

---

## 六、内核同步

### 6.1 同步原语

```c
// 自旋锁
spinlock_t my_lock;
spin_lock_init(&my_lock);

spin_lock(&my_lock);
// 临界区
spin_unlock(&my_lock);

// 读写锁
rwlock_t my_rwlock;
rwlock_init(&my_rwlock);

read_lock(&my_rwlock);
// 读临界区
read_unlock(&my_rwlock);

write_lock(&my_rwlock);
// 写临界区
write_unlock(&my_rwlock);

// 互斥锁
struct mutex my_mutex;
mutex_init(&my_mutex);

mutex_lock(&my_mutex);
// 临界区
mutex_unlock(&my_mutex);

// 信号量
struct semaphore my_sem;
sema_init(&my_sem, 1);

down(&my_sem);
// 临界区
up(&my_sem);

// RCU(读-复制-更新)
rcu_read_lock();
// 读临界区
rcu_read_unlock();

// 更新
rcu_assign_pointer(ptr, new_ptr);
synchronize_rcu();  // 等待所有读者完成
kfree(old_ptr);

// 原子操作
atomic_t count = ATOMIC_INIT(0);
atomic_inc(&count);
atomic_dec(&count);
atomic_add(5, &count);
int val = atomic_read(&count);

// 位操作
unsigned long flags;
set_bit(0, &flags);
clear_bit(0, &flags);
test_bit(0, &flags);
```

---

## 七、内核调试

### 7.1 调试技术

```c
// printk日志级别
printk(KERN_EMERG   "Emergency\n");
printk(KERN_ALERT   "Alert\n");
printk(KERN_CRIT    "Critical\n");
printk(KERN_ERR     "Error\n");
printk(KERN_WARNING "Warning\n");
printk(KERN_NOTICE  "Notice\n");
printk(KERN_INFO    "Info\n");
printk(KERN_DEBUG   "Debug\n");

// 动态调试
pr_debug("Debug message\n");
dev_dbg(dev, "Device debug\n");

// 内核Oops
// 当内核崩溃时会打印Oops信息
// 包含: 寄存器值、调用栈、内存映射

// Kprobes(动态探针)
static int handler_pre(struct kprobe *p, struct pt_regs *regs) {
    printk("pre_handler: p->addr = 0x%p\n", p->addr);
    return 0;
}

static struct kprobe kp = {
    .symbol_name = "do_fork",
    .pre_handler = handler_pre,
};

register_kprobe(&kp);

// ftrace(函数跟踪)
// echo function > /sys/kernel/debug/tracing/current_tracer
// echo 1 > /sys/kernel/debug/tracing/tracing_on

// 内核内存检测
// KASAN(内核地址消毒器)
// CONFIG_KASAN=y
```

---

## 附录：内核模块命令

| 命令 | 说明 |
|------|------|
| `insmod` | 加载模块 |
| `rmmod` | 卸载模块 |
| `modprobe` | 加载模块(自动处理依赖) |
| `lsmod` | 列出已加载模块 |
| `modinfo` | 显示模块信息 |
| `depmod` | 生成模块依赖 |

---

## 相关链接

- [[Linux基础]] - Linux基础
- [[Linux驱动开发]] - 驱动开发
- [[操作系统原理]] - 操作系统
- [[嵌入式Linux驱动详解]] - 嵌入式驱动
