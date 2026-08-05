# GUI-Guider智能家居仿真器修复 - 中文字体转换提速方案

## 2026-04-19 12:10:00

### 背景
C代码生成卡死的根因是23.3MB思源黑体字体通过lv_font_conv转换极慢。用户需要保持中文显示但要求提速。

### 项目信息
- **项目路径**: E:\MCU\Gui-Guider\project\smart_home2.0
- **GUI-Guider版本**: 1.10.1-GA
- **LVGL版本**: v9.3.0
- **中文字体**: SourceHanSansSC-Regular.ttf (23.3MB)
- **字体转换库**: lv_font_conv v1.5.3

### 完整踩坑记录

#### 坑1: Application.screen结构不完整导致代码生成卡死
- **现象**: 点击Generate C Code卡死，无任何输出
- **根因**: smart_home2.guiguider的Application.screen每个条目只有id和name两个字段，缺少widgets、style等完整定义
- **解决**: 从FrontJson派生填充Application.screen，使其结构与正常模板一致
- **结果**: 结构修复后仍然卡死（说明这只是必要条件，不是充分条件）

#### 坑2: 23MB中文字体lv_font_conv转换极慢（当前根因）
- **现象**: 代码生成显示"Generating C code..."后完全卡住，GUI无响应
- **根因**: qp函数调用Bp=require("lv_font_conv/lib/convert")为每个字体/大小组合生成C文件
  - SourceHanSansSC-Regular.ttf: 23.3MB（含2万+中文字符）
  - 需要转换10个尺寸：12,13,14,15,16,18,20,22,32,56px
  - 每次转换都是同步阻塞操作，GUI完全冻结
  - lv_font_conv处理大字体文件极慢（Python实现的node模块）
- **对比**: MicroPython跳过整个Wg→qp路径，所以瞬间生成

#### 坑3: FontAwesome5.woff和custom_content.json缺失
- **现象**: qp函数会检查这两个文件是否存在
- **根因**: 这是GUI-Guider内置字体，smart_home2项目没有
- **解决**: 从test项目复制或创建空文件（但即使有也无法解决字体转换慢的问题）

#### 坑4: 之前尝试过的无效方案
- 手动编写generate_screens.py生成setup_scr_*.c（能编译但不能通过GUI-Guider生成）
- 只修复JSON结构不填充Application.screen（仍卡死）
- 添加Application、version等字段（仍卡死）

### 提速方案对比

#### 方案A: 使用字体子集（推荐⭐⭐⭐⭐⭐）
- **原理**: 将23MB全量字体裁剪为仅包含项目实际使用字符的子集字体
- **实现**: 提取所有label的text字段，用fonttools/pyftsubset裁剪字体
- **预期效果**: 23MB → 几百KB，转换时间从分钟级降到秒级
- **风险**: 低，只要提取完整就不会缺字

#### 方案B: 使用LVGL内置字体+外部中文字体文件
- **原理**: 不在lv_font_conv中转换中文字体，改用LV_FONT_MONTSERRAT_*内置字体+运行时加载CFF/BIN字体
- **实现**: 修改lv_conf.h启用内置字体，中文字体用bin格式
- **预期效果**: 完全跳过中文字体转换
- **风险**: 中，需要改架构

#### 方案C: 减少字体尺寸数量
- **原理**: 10个尺寸→3-4个尺寸，减少70%转换次数
- **实现**: 统一项目中使用的字体大小
- **预期效果**: 转换时间减少70%，但单次仍慢
- **风险**: 低

#### 方案D: 预编译字体文件
- **原理**: 手动提前运行lv_font_conv生成所有字体.c文件，放到generated/guider_fonts/
- **实现**: 用脚本批量转换，GUI-Guider检测到已存在文件会跳过
- **预期效果**: GUI-Guider生成瞬间完成
- **风险**: 低，但需要维护

### 推荐方案: A（字体子集）+ D（预编译）组合
1. 提取项目所有用到的中文字符
2. 用pyftsubset裁剪23MB字体为子集（预计<1MB）
3. 用裁剪后的字体替换原字体
4. 预先生成字体.c文件放到generated/guider_fonts/
5. GUI-Guider生成时检测到已有文件直接跳过

### 待办事项
- [ ] 实施方案A：提取字符→裁剪字体→替换
- [ ] 实施方案D：预编译字体.c文件
- [ ] 验证裁剪后字体是否缺字
- [x] 逆向分析GUI-Guider代码生成逻辑
- [x] 定位C代码生成卡死根因
- [x] 修复Application.screen结构

### 下次会话须知
> 根因已确认：23MB SourceHanSansSC字体通过lv_font_conv转换10个尺寸导致GUI卡死
> 推荐方案：字体子集裁剪(pyftsubset) + 预编译字体.c文件
> 需要提取的字体尺寸：12,13,14,15,16,18,20,22,32,56px
> GUI-Guider日志：C:\Users\30817\AppData\Roaming\gui-guider\logs\GuiGuider.log
> GUI-Guider源码已提取到：E:\MCU\Gui-Guider\app_extracted\
