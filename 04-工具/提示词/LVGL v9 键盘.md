**【角色与任务】** 你现在是顶级 LVGL v9 专家。之前你使用 Flex 弹簧空间导致原生键盘被挤出屏幕外（完全不可见），且页面切换逻辑混乱。现在，我们需要严格按照以下规范，重构一个**完全独立的全屏键盘输入页面 (`ui_page_keyboard.c`)**。

**【核心布局：严格使用 Grid 替代 Flex】** 为了防止键盘被挤压，当前屏幕（键盘页）必须使用 `LV_LAYOUT_GRID`，分为固定的三行：

1. **行 0 (高度 60px)：** 顶部导航栏。包含左侧“返回”按钮 和居中的标题 (Title)。
    
2. **行 1 (高度 80px)：** 中间文本显示区。放置一个撑满宽度的 `lv_textarea`，**必须禁用其自带键盘关联**。
    
3. **行 2 (高度 撑满剩余空间 `LV_GRID_FR(1)`)：** 底部键盘区。放置原生 `lv_keyboard`，并使其宽/高 100% 撑满该 Grid Cell。调用 `lv_keyboard_set_textarea` 绑定到行 1 的 textarea。
    

**【数据同步与生命周期（关键）】** 不要再写多余的 apply/cancel 页面，遵循以下数据流：

1. **暴露入口 API：** 提供一个函数 `ui_keyboard_page_open(lv_obj_t* source_ta, const char* title, lv_keyboard_mode_t mode)`。
    
2. **打开时：** 创建键盘页面，将 `source_ta` (如 Login 页的用户名输入框) 中已有的文本，复制到键盘页的 textarea 中。
    
3. **确认时：** 监听键盘的 `LV_EVENT_READY` (回车/确认键)。触发时，将键盘页 textarea 的最终文本写回 `source_ta`，然后执行退出动画。
    
4. **取消时：** 监听顶部返回按钮或键盘的 `LV_EVENT_CANCEL`。触发时，不保存文本，直接执行退出动画。
    
5. **过渡动画：** 使用 `lv_screen_load_anim`。打开时用 `LV_SCR_LOAD_ANIM_MOVE_LEFT`，返回时用 `LV_SCR_LOAD_ANIM_MOVE_RIGHT`。
    

**【执行要求】** 请不要分析，直接根据上述 100% 确定的规范，输出 `ui_page_keyboard.c` 和 `ui_page_keyboard.h` 的完整代码。确保包含 `ui_keyboard_page_open` 接口。

---

### 💡 为什么这么写能成功？

1. **封杀了 Flex 布局的自适应黑洞：** 强制它用 `Grid` 并用 `LV_GRID_FR(1)`，这样 LVGL 的底层渲染引擎就会明确知道：“键盘区域的高度 = 屏幕总高度 - 60 - 80”，键盘绝对不会再跑出屏幕。
    
2. **明确了 API 接口设计：** 之前 AI 搞不定是因为它不知道怎么把 Login 页面的数据传给 Keyboard 页面，再传回来。这个提示词给它规定了 `source_ta` 指针传递法，它就不会乱发挥了。
    
3. **状态机的闭环：** 明确告诉它捕捉 `READY` 和 `CANCEL` 事件，并在此时做数据回写和页面销毁，防止内存泄漏。