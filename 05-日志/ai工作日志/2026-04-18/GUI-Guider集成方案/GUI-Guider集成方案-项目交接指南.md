# ESP32-P4 LVGL GUI-Guider 项目交接指南

> 本文档帮助接手的 AI 快速了解项目架构、工作流、踩过的坑。

## 一、项目概览

| 项目 | 说明 |
|------|------|
| **硬件** | ESP32-P4 + 480x272 LCD 触摸屏 |
| **系统** | ESP-IDF v5.5.3 + LVGL v9.4.0 + FreeRTOS |
| **UI 设计工具** | NXP GUI Guider 1.10.1-GA |
| **GUI Guider 项目路径** | `E:\MCU\Gui-Guider\project\test\` |
| **ESP-IDF 项目路径** | `E:\MCU\esp32\p4\lvgl_gui\` |
| **ESP-IDF 环境** | `E:\MCU\esp32\.espressif\v5.5.3\` |
| **烧录串口** | COM28 |
| **显示** | 32MB PSRAM, 16MB Flash |
| **当前分支** | main |

## 二、目录架构

```
E:\MCU\esp32\p4\lvgl_gui\main\gui\
├── generated\          ← GUI Guider 导出代码（可完全覆盖）
│   ├── gui_guider.c/h
│   ├── events_init.c/h
│   ├── setup_scr_scr*.c      ← 各屏幕 UI 布局代码
│   ├── guider_fonts\          ← GUI Guider 生成的字体 C 文件
│   └── images\
├── custom\             ← GUI Guider 自定义代码（可完全覆盖）
│   ├── custom.c/h
│   └── lv_conf_ext.h
└── smart_home\         ← 业务适配层（⚠️ 不受 GUI Guider 重新导出影响）
    ├── gui_adapter.c/h  ← UI 初始化 + 周期更新 + 业务通知接口
    └── (其他业务相关文件)
```

**关键原则**：
- `generated/` 和 `custom/` 是 **可替换的**，GUI Guider 重新导出后直接覆盖
- `smart_home/` 是 **持久的**，永远不被覆盖，存放业务适配逻辑
- `gui_adapter.c` 是入口：`GUI_Adapter_Init()` 调用 `setup_ui()` + `custom_init()`

## 三、GUI Guider 代码替换流程

### 3.1 一键替换脚本

项目根目录有 `copy_gui.bat`，一键完成替换：

```bat
@echo off
set GUI_GUIDER_EXPORT=E:\MCU\Gui-Guider\project\test\c_code
set PROJECT_GUI=E:\MCU\esp32\p4\lvgl_gui\main\gui

rd /s /q "%PROJECT_GUI%\generated" 2>nul
mkdir "%PROJECT_GUI%\generated"
xcopy "%GUI_GUIDER_EXPORT%\generated" "%PROJECT_GUI%\generated\" /E /Q /Y >nul

rd /s /q "%PROJECT_GUI%\custom" 2>nul
mkdir "%PROJECT_GUI%\custom"
xcopy "%GUI_GUIDER_EXPORT%\custom" "%PROJECT_GUI%\custom\" /E /Q /Y >nul
```

### 3.2 完整操作流程

1. **在 GUI Guider 中修改 UI** → 保存到 `E:\MCU\Gui-Guider\project\test\`
2. **GUI Guider 导出** → Export 到 `E:\MCU\Gui-Guider\project\test\c_code`
3. **双击运行** `E:\MCU\esp32\p4\lvgl_gui\copy_gui.bat`
4. **编译**：在 CMD 中运行 `idf_build.bat`
5. **烧录**：`idf.py -p COM28 flash monitor`

### 3.3 中文显示方案

**当前方案（GUI Guider 图形化导入字体）**：
1. 将 TTF/OTF 中文字体文件放在 `E:\MCU\esp32\p4\lvgl_gui\fonts\`
2. 在 GUI Guider 中打开 Font 面板 → 点击 `+` → 选择字体文件
3. 设置字号（14px 推荐）
4. 将所有中文标签的字体改为新导入的字体
5. 导出 → 替换 → 编译 → 烧录，中文直接正确显示

**可用字体（已下载）**：
| 文件 | 大小 | 来源 |
|------|------|------|
| `fonts/SourceHanSansSC-Normal.otf` | 16MB | Adobe 思源黑体 |
| `fonts/NotoSansSC-Regular.ttf` | 2.3MB | Google Noto Sans SC |

## 四、GUI Adapter 当前状态（干净版）

`gui_adapter.c` 当前是极简干净版本，**不做任何字体替换**：

```c
void GUI_Adapter_Init(void)
{
    setup_ui(&guider_ui);           // GUI Guider 生成的 UI 初始化
    custom_init(&guider_ui);        // GUI Guider 自定义初始化
    s_periodic_timer = lv_timer_create(periodic_timer_cb, 1000, NULL); // 1s 周期更新
}
```

周期更新做的事：
- 更新日期时间标签
- 更新 WiFi 图标透明度
- 更新墨水余量进度条

**暴露的接口**：
```c
void GUI_Adapter_Init(void);                      // 初始化
void GUI_Adapter_Periodic_Update(void);           // 手动触发更新
void GUI_Adapter_Notify_Device_Changed(id);       // 设备状态变化通知
void GUI_Adapter_Notify_WiFi_State(connected);    // WiFi 状态变化通知
void GUI_Adapter_Notify_MQTT_State(connected);    // MQTT 状态变化通知
```

## 五、⚠️ 踩过的坑（重要！）

### 坑 1：不要创建自定义 UI 任务（Watchdog 崩溃）

**现象**：创建 `TaskUI` 调用 `lv_timer_handler()` → 烧录后一触摸就复位 → `MCAUSE: 0xdeadc0de` → `lv_inv_area` 崩溃

**根因**：`esp_lv_adapter` 组件已经内置了 LVGL 驱动任务，创建自定义 UI 任务会导致两个任务同时操作 LVGL，触发数据竞争和 watchdog。

**解决**：**永远不要**在 `main.c` 中创建 `TaskUI_Create()` 或任何调用 `lv_timer_handler()` 的自定义任务。LVGL 由 `esp_lv_adapter` 内置任务驱动。

### 坑 2：运行时字体替换不可用

**现象**：在 `gui_adapter.c` 中递归遍历控件替换字体 → 字体错位、点击组件闪退

**根因**：LVGL v9 的字体替换在运行时改变了控件的样式属性，导致内部布局缓存失效，触摸事件处理异常。

**解决**：**废弃运行时字体替换**。改为在 GUI Guider 中直接导入中文字体，导出代码即正确。

### 坑 3：CMake 需要包含正确的 include 路径

**现象**：`sys_task_manager.h: No such file or directory`

**根因**：`main/CMakeLists.txt` 的 `INCLUDE_DIRS` 没有包含 `APP/Inc`、`Tasks/Inc`、`BSP/Inc`

**已修复**：`main/CMakeLists.txt` 已配置正确。

### 坑 4：编译环境必须在 Windows CMD/PowerShell 中运行

**现象**：Git Bash 中 `source export.sh` → Python 虚拟环境路径解析错误 → `idf.py: command not found`

**根因**：ESP-IDF v5.5.3 的 Python 虚拟环境安装在 Windows 路径下，Git Bash 的 `export.sh` 无法正确激活。

**解决**：**使用 `idf_build.bat`**（本质是 call export.bat + idf.py build），或在 CMD/PowerShell 中操作。

### 坑 5：COM28 被 Python 进程占用

**现象**：烧录时报错 `PermissionError(13, 拒绝访问)`

**根因**：之前的 `idf.py monitor` 或 Python 脚本没有正确释放串口。

**解决**：`Stop-Process -Name python -Force` 杀死所有 Python 进程。

### 坑 6：CMakeCache.txt 来自不同项目

**现象**：CMake 报错 cache 来自不同项目目录

**解决**：删除 `build/CMakeCache.txt` 后重新编译。

## 六、构建和烧录命令

### 编译
```bat
cd E:\MCU\esp32\p4\lvgl_gui
idf_build.bat
```

### 烧录 + 监控
```bat
idf.py -p COM28 flash monitor
```

### 仅烧录
```bat
idf.py -p COM28 flash
```

### 清理重编译
```bat
idf.py fullclean
idf_build.bat
```

### 释放串口
```powershell
Stop-Process -Name python -Force
```

## 七、LVGL 屏幕信息

项目当前有 9 个屏幕（GUI Guider 生成）：
- `scrHome` — 主屏幕
- `scrCopy` — 复印菜单
- `scrCopy2` — 复印菜单 2
- `scrPrintMenu` — 打印菜单
- `scrPrintUSB` — USB 打印
- `scrPrintMobile` — 手机打印
- `scrSetup` — 设置
- `scrLoader` — 加载页面
- `scrFinished` — 完成页面

## 八、GUI Guider 项目中文字体导入步骤（图文指引）

1. **打开 GUI Guider**，加载项目 `E:\MCU\Gui-Guider\project\test\`
2. **进入 Font 面板**（通常在右侧属性面板）
3. **点击字体列表的 `+` 按钮**
4. **选择字体文件**：
   - `E:\MCU\esp32\p4\lvgl_gui\fonts\NotoSansSC-Regular.ttf`（推荐，2.3MB）
   - 或 `E:\MCU\esp32\p4\lvgl_gui\fonts\SourceHanSansSC-Normal.otf`（16MB）
5. **设置字号为 14px**（当前中文标签使用的字号）
6. **逐个选中中文标签** → 在属性面板中将 Font 改为新导入的中文字体
7. **保存并 Export** 到 `E:\MCU\Gui-Guider\project\test\c_code`
8. **运行 `copy_gui.bat`** → **编译** → **烧录**

## 九、关键文件清单

| 文件 | 作用 |
|------|------|
| `main/main.c` | 入口文件，调用 `GUI_Adapter_Init()` 和各任务创建 |
| `main/gui/smart_home/gui_adapter.c` | UI 初始化 + 周期更新 |
| `main/gui/smart_home/gui_adapter.h` | 接口声明 |
| `main/CMakeLists.txt` | 编译配置 |
| `copy_gui.bat` | 一键替换 GUI Guider 代码 |
| `idf_build.bat` | 一键编译脚本 |

## 十、总结：接手后的工作原则

1. **不动 `generated/` 和 `custom/`** — 这些是 GUI Guider 管理的，重新导出后会被覆盖
2. **业务逻辑写在 `smart_home/`** — 这是持久层，不受 GUI Guider 影响
3. **不创建 UI 任务** — `esp_lv_adapter` 已内置 LVGL 驱动
4. **不运行时替换字体** — 在 GUI Guider 中导入字体
5. **编译用 CMD/PowerShell** — 不用 Git Bash
6. **烧录前检查 COM28 是否被占用**
