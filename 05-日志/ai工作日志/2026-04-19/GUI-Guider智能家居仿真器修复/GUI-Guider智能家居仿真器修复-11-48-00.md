# GUI-Guider智能家居仿真器修复

## 2026-04-19 11:48:00

### 背景
GUI-Guider 1.10.1-GA IDE 在点击"生成C代码"时卡死，无法正常生成代码。用户要求修复 smart_home2.guiguider 项目模板文件。

### 项目信息
- **项目路径**: E:\MCU\Gui-Guider\project\smart_home2.0
- **模板文件**: E:\MCU\Gui-Guider\project\test - 副本\smart_home2.txt → smart_home2_fixed.txt
- **参考模板**: E:\MCU\Gui-Guider\project\test - 副本\test.txt（正常工作的模板）
- **技术栈**: LVGL v9.3.0 + GUI-Guider 1.10.1-GA

### 工作内容

#### 1. JSON结构对比分析
- 操作: 对比 test.txt 和 smart_home2.txt 的顶层 keys、projectSettings、Application、FrontJson 结构
- 状态: ✅ 完成
- 结果: 顶层 keys 完全匹配，但 Application.screen 条目结构严重不完整

#### 2. 发现关键差异
- 操作: 深入比较 Application.screen[0] 的结构
- 状态: ✅ 完成
- 结果:
  - **test.txt**: 每个 screen 包含 `name`, `id`, `type`, `version`, `scrollbar_mode`, `customer_code`, `width`, `height`, `visible`, `flag`, `rm_flag`, `size`, `style`, `widgets`, `event` 共15个字段
  - **smart_home2.txt**: 每个 screen 只有 `id` 和 `name` 2个字段，完全缺少 widgets 定义

#### 3. 生成修复后的模板
- 操作: 从 FrontJson 数据派生填充 Application.screen，生成完整的 widget 定义
- 状态: ✅ 完成
- 结果: 生成了 smart_home2_fixed.txt（2.1MB, 38831行）
- 验证: Application.screen keys 完全匹配 ✓，widget keys 完全匹配 ✓

#### 4. 修复内容详情
- 为每个屏幕生成了完整的 `widgets` 数组，包含：
  - `pos` [x, y]（从 left/top 转换）
  - `size` [w, h]（从 width/height 转换）
  - `style` 数组（从 FrontJson style 转换，补充缺失字段）
  - `child` 递归转换子 widget
  - `visible`, `scrollbar_mode`, `default_style`, `flag`, `rm_flag`
  - 类型特定字段（label 的 text/long_mode/is_static，img 的 image_path 等）
- 为每个屏幕添加了屏幕级 `style`、`event`、`customer_code`、`size` 等

### 修改文件清单
| 文件 | 修改类型 | 说明 |
|------|----------|------|
| E:\MCU\Gui-Guider\project\test - 副本\smart_home2_fixed.txt | 新增 | 修复后的完整模板，2.1MB |
| E:\MCU\Gui-Guider\project\temp_fix\smart_home2_fixed.txt | 新增 | 中间生成文件 |

### 关键决策
- 从 FrontJson 派生 Application.screen 数据而非手动编写，确保数据一致性
- 使用随机 ID 生成（8位字母数字），与 GUI-Guider 格式一致

### 遇到的问题
- **问题**: Bash heredoc 中单引号导致语法错误
- **解决**: 将 Python 脚本写入 /tmp/fix.py 后再执行

### 待办事项
- [ ] 用户将 smart_home2_fixed.txt 重命名为 smart_home2.guiguider 替换原文件
- [ ] 在 GUI-Guider 中打开项目测试生成C代码是否成功
- [x] 分析 JSON 结构差异
- [x] 生成修复后的模板文件

### 下次会话须知
> 修复后的文件位于 E:\MCU\Gui-Guider\project\test - 副本\smart_home2_fixed.txt
> 需要用户手动替换 smart_home2.guiguider 文件后在 GUI-Guider 中测试
> 如果仍然卡死，可能需要检查是否有背景图片引用触发了已知 Bug LGLGUIB-4404

---

## 2026-04-19 12:00:00

### 背景
用户反馈点击 Generate C Code 仍然卡死，但 MicroPython 代码可以正常生成。

### 工作内容

#### 1. 逆向分析 GUI-Guider 代码生成逻辑
- 操作: 提取 GUI-Guider asar 包，分析 main.js 中 C 代码和 MicroPython 代码生成路径差异
- 状态: ✅ 完成
- 结果: C 代码生成路径为 `pm → Wg → (Pp图片转换, Qp, qp字体转换, Gp widget代码生成)`，而 MicroPython 直接调用 `gm` 完全跳过图片和字体转换

#### 2. 定位卡死根因
- 操作: 检查项目字体配置和字体文件大小
- 状态: ✅ 完成
- 结果: **找到根因！**
  - `SourceHanSansSC-Regular.ttf` 文件大小为 **23.3 MB**
  - C 代码生成需要为 10 个不同尺寸（12,13,14,15,16,18,20,22,32,56px）调用 `lv_font_conv` 转换器
  - 每次转换都要读取整个 23MB 字体文件，这是同步阻塞操作
  - MicroPython 跳过此路径所以不卡

#### 3. 确认关键文件缺失
- 操作: 检查 import/font/ 目录
- 状态: ✅ 完成
- 结果: `FontAwesome5.woff` 和 `custom_content.json` 不存在（qp 函数会检查这两个文件）

### 关键发现
| 项目 | 值 |
|------|-----|
| 中文字体文件大小 | SourceHanSansSC-Regular.ttf: 23.3MB |
| 需要转换的字体/大小组合 | 12个（10个中文字体+2个montserrat） |
| 字体转换库 | lv_font_conv v1.5.3 |
| C代码生成函数链 | pm → Wg → (Pp图片, qp字体, Gp widget) |
| MicroPython生成函数 | gm（跳过图片和字体转换） |

### 待办事项
- [ ] 向用户确认等待时间（可能需要5-30分钟）
- [ ] 检查 generated/guider_fonts/ 是否有部分字体文件已生成
- [ ] 考虑优化方案：减少字体大小数量、使用子集字体、或改用预编译字体
- [x] 逆向分析 GUI-Guider 代码生成逻辑
- [x] 定位 C 代码生成卡死根因

### 下次会话须知
> C 代码生成卡死的根因是 23MB 中文字体的 lv_font_conv 转换极慢。
> 用户可能等待时间不够长（需要5-30分钟），需要确认。
> GUI-Guider 日志位于 C:\Users\30817\AppData\Roaming\gui-guider\logs\GuiGuider.log
