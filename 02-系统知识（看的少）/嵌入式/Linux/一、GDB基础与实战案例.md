# GDB 调试器 （程序崩溃的终极诊断工具）

## 核心概念

### 什么是 GDB？
- ==GNU Debugger== - GNU 项目开发的调试器
- ==崩溃定位神器== - 当程序崩溃时，GDB 能精确告诉你崩溃在哪一行代码
- ==调用栈追踪== - 显示函数调用链，帮你理解程序执行流程
- ==变量检查== - 查看崩溃时的变量值、内存状态

### 为什么需要 GDB？
- **printf 调试的局限**: 无法定位随机崩溃、内存错误
- **ACCESS VIOLATION**: Windows 异常码 0xC0000005，表示访问了非法内存
- **SEH 无法捕获**: 有些崩溃发生在 SDL/渲染线程中，`__try/__except` 无法捕获
- ==GDB 是最后手段==：当所有调试方法都失败时，GDB 能直接定位崩溃指令

---

## 一、GDB 基础概念与启动

### 1.1 安装与验证

**Windows MinGW 环境**:
```bash
# 检查 GDB 是否安装
where gdb
# 输出示例：
# E:\MCU\lvgl_tools\mingw64\mingw64\bin\gdb.exe
```

**编译时启用调试信息**:
```cmake
# CMakeLists.txt 添加调试选项
target_compile_options(your_target PRIVATE -g -O0)
target_link_options(your_target PRIVATE -g)
```

| 选项 | 说明 |
|------|------|
| `-g` | 生成调试信息（行号、变量名等） |
| `-O0` | 禁用优化，确保代码顺序不变 |

### 1.2 启动 GDB 的三种方式

**方式一：交互式调试**
```bash
gdb ./your_program.exe
# 进入 GDB 后输入命令
(gdb) run
(gdb) bt
(gdb) quit
```

**方式二：批处理模式（推荐用于崩溃诊断）**
```bash
gdb -batch -x commands.txt ./your_program.exe
```

**方式三：命令行直接指定**
```bash
gdb -batch -ex "set pagination off" -ex run -ex bt -ex quit ./your_program.exe
```

### 1.3 命令文件方式（推荐）

创建 `gdb_cmds.txt`:
```
set pagination off
run
bt
info registers
quit
```

运行：
```bash
gdb -batch -x gdb_cmds.txt ./your_program.exe
```

---

## 二、常用调试命令

### 2.1 执行控制命令

| 命令 | 缩写 | 说明 |
|------|------|------|
| `run` | `r` | 启动程序 |
| `continue` | `c` | 继续执行 |
| `next` | `n` | 单步执行（不进入函数） |
| `step` | `s` | 单步执行（进入函数） |
| `finish` | | 执行到当前函数返回 |
| `quit` | `q` | 退出 GDB |

### 2.2 崩溃诊断命令（核心）

| 命令 | 说明 | 输出示例 |
|------|------|----------|
| ==`bt`== | 显示调用栈（Backtrace） | `#0 function() at file.c:123` |
| `bt full` | 显示调用栈+局部变量 | 包含每个栈帧的变量值 |
| `frame N` | 切换到第 N 个栈帧 | `(gdb) frame 3` |
| `info registers` | 显示 CPU 寄存器 | `rax=0x0 rbx=0x123...` |
| `info locals` | 显示当前函数的局部变量 | |
| `info args` | 显示当前函数的参数 | |

### 2.3 变量与内存检查

| 命令 | 说明 |
|------|------|
| `print var_name` | 打印变量值 |
| `print *ptr` | 打印指针指向的值 |
| `print/x var` | 以十六进制打印 |
| `x/10x address` | 查看内存（10个十六进制值） |
| `ptype var` | 显示变量类型 |

### 2.4 断点命令

| 命令 | 说明 |
|------|------|
| `break main` | 在 main 函数设置断点 |
| `break file.c:123` | 在指定行设置断点 |
| `info breakpoints` | 显示所有断点 |
| `delete 1` | 删除 1 号断点 |

---

## 三、实战案例：修复 LVGL 鼠标点击崩溃

### 3.1 问题背景

**症状**:
- 程序启动后几秒内崩溃
- 退出码 `-1073741819` (0xC0000005 = ACCESS VIOLATION)
- `__try/__except` 无法捕获异常
- printf 调试无法定位具体崩溃位置

**失败的调试尝试**:
1. `SetUnhandledExceptionFilter()` - 未触发
2. `__try/__except` - 未捕获
3. 添加大量 `printf` - 崩溃位置不确定

### 3.2 GDB 诊断过程

**Step 1: 编译带调试信息的版本**
```cmake
# CMakeLists.txt
target_compile_options(garden_sim PRIVATE -g -O0)
target_link_options(garden_sim PRIVATE -g)
```

**Step 2: 创建 GDB 命令文件**
```
# gdb_cmds.txt
set pagination off
run
bt
info registers
quit
```

**Step 3: 运行 GDB**
```bash
gdb -batch -x gdb_cmds.txt ./garden_sim.exe
```

**Step 4: 分析 GDB 输出**
```
Thread 1 received signal SIGSEGV, Segmentation fault.
0x00007ff66dd2be97 in update_obj_state (obj=0x7ff66de39530, new_state=48) 
    at E:\MCU\...\lvgl\src\core\lv_obj.c:943
943     for(j = 0; tr->props[j] != 0 && tsi < STYLE_TRANSITION_MAX; j++) {

#0  0x00007ff66dd2be97 in update_obj_state at lv_obj.c:943
#1  0x00007ff66dd2a384 in lv_obj_add_state at lv_obj.c:310
#2  0x00007ff66dd2b3f8 in lv_obj_event at lv_obj.c:745
#5  0x00007ff66dd2e68e in lv_obj_send_event at lv_obj_event.c:67
#6  0x00007ff66dd54e50 in send_event (code=LV_EVENT_PRESSED) at lv_indev.c:1820
#7  0x00007ff66dd5377e in indev_proc_press at lv_indev.c:1262
```

### 3.3 定位根因

**从调用栈分析**:
1. 崩溃在 `lv_obj.c:943` → `tr->props[j] != 0`
2. `tr` 是 `LV_STYLE_TRANSITION` 属性的指针
3. 向上追溯：`lv_obj_add_state()` → `LV_EVENT_PRESSED` → 鼠标点击事件

**检查源码**:
```c
// lv_obj.c:938-943
if(lv_style_get_prop_inlined(obj_style->style, LV_STYLE_TRANSITION, &v) != LV_STYLE_RES_FOUND) continue;
const lv_style_transition_dsc_t * tr = v.ptr;  // tr 可能是 NULL!

for(j = 0; tr->props[j] != 0 && ...  // 解引用 NULL->props 崩溃！
```

**找到问题代码**:
```c
// ui_tabbar.c:124
lv_obj_set_style_transition(btn, NULL, 0);  // 设置 transition 为 NULL！
```

### 3.4 修复方案

**移除问题代码**:
```c
// 删除这行：
// lv_obj_set_style_transition(btn, NULL, 0);
```

**原因分析**:
- `lv_obj_remove_style_all(btn)` 已经移除了所有样式
- 再设置 `transition = NULL` 会导致样式系统存储 NULL 指针
- 当用户点击按钮时，LVGL 尝试添加 `LV_STATE_PRESSED` 状态
- `update_obj_state()` 遍历样式，找到 `LV_STYLE_TRANSITION`
- 解引用 `tr->props[j]` 时，`tr` 是 NULL → 崩溃！

### 3.5 验证修复

```bash
# 重新编译运行
cmake --build .
gdb -batch -x gdb_cmds.txt ./garden_sim.exe

# 输出：
# [Inferior 1 (process 64488) exited normally]
# ✅ 程序正常退出，无崩溃！
```

---

## 四、GDB 调试技巧总结

### 4.1 何时使用 GDB

| 场景 | 推荐方法 |
|------|----------|
| 逻辑错误、变量值不对 | printf / 日志 |
| 程序卡死、死锁 | printf + 超时检测 |
| ==随机崩溃、ACCESS VIOLATION== | ==GDB bt 命令== |
| 内存泄漏 | Valgrind / ASan |
| 性能问题 | Profiler |

### 4.2 GDB 调试流程

```
1. 编译带 -g 选项
       ↓
2. 创建 gdb_cmds.txt (run + bt + quit)
       ↓
3. gdb -batch -x gdb_cmds.txt ./program
       ↓
4. 分析 bt 输出，定位崩溃行号
       ↓
5. 检查该行代码的指针/数组访问
       ↓
6. 修复并验证
```

### 4.3 常见崩溃类型

| 异常码 | 含义 | 常见原因 |
|--------|------|----------|
| 0xC0000005 | ACCESS VIOLATION | 空指针解引用、数组越界 |
| 0xC00000FD | STACK_OVERFLOW | 无限递归、大局部变量 |
| 0xC000013A | Ctrl+C 终止 | 用户中断 |

---

## 附录：GDB 命令速查表

### 执行控制
| 命令 | 说明 |
|------|------|
| `run` | 启动程序 |
| `continue` | 继续执行 |
| `next` | 单步（不进入函数） |
| `step` | 单步（进入函数） |
| `quit` | 退出 |

### 崩溃诊断（最重要）
| 命令 | 说明 |
|------|------|
| ==`bt`== | 显示调用栈 |
| `bt full` | 调用栈+变量 |
| `frame N` | 切换栈帧 |
| `info registers` | CPU 寄存器 |
| `info locals` | 局部变量 |

### 变量检查
| 命令 | 说明 |
|------|------|
| `print var` | 打印变量 |
| `print *ptr` | 解引用指针 |
| `print/x var` | 十六进制打印 |
| `x/10x addr` | 查看内存 |

### 断点
| 命令 | 说明 |
|------|------|
| `break main` | 函数断点 |
| `break file.c:123` | 行断点 |
| `info break` | 显示断点 |
| `delete N` | 删除断点 |

---

## 相关链接

- [[ESP-IDF]] - ESP32 开发框架
- [[LVGL]] - 嵌入式图形库
- [[FreeRTOS]] - 实时操作系统

---

*创建时间: 2025-05-10*
*最后更新: 2025-05-10*
