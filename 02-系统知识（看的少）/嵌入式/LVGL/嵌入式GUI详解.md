# 嵌入式GUI详解

## 核心概念

- **LVGL** - 轻量级图形库
- **控件** - UI元素
- **事件** - 用户交互
- **样式** - 外观定制

---

## 一、LVGL架构

### 1.1 LVGL基础

```c
#include "lvgl.h"

// LVGL初始化
void lv_init(void);

// 显示缓冲区
static lv_color_t buf1[LV_HOR_RES_MAX * 10];
static lv_disp_draw_buf_t draw_buf;
lv_disp_draw_buf_init(&draw_buf, buf1, NULL, LV_HOR_RES_MAX * 10);

// 显示驱动
static lv_disp_drv_t disp_drv;
lv_disp_drv_init(&disp_drv);
disp_drv.draw_buf = &draw_buf;
disp_drv.flush_cb = my_flush_cb;
disp_drv.hor_res = 480;
disp_drv.ver_res = 320;
lv_disp_drv_register(&disp_drv);

// 输入驱动(触摸)
static lv_indev_drv_t indev_drv;
lv_indev_drv_init(&indev_drv);
indev_drv.type = LV_INDEV_TYPE_POINTER;
indev_drv.read_cb = my_touchpad_read;
lv_indev_drv_register(&indev_drv);

// 任务处理
while (1) {
    lv_task_handler();
    delay_ms(5);
}
```

### 1.2 显示刷新回调

```c
// 显示刷新
void my_flush_cb(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
    int x1 = area->x1;
    int y1 = area->y1;
    int x2 = area->x2;
    int y2 = area->y2;

    // 发送到LCD
    lcd_set_window(x1, y1, x2, y2);
    lcd_write_pixels((uint16_t *)color_p, (x2 - x1 + 1) * (y2 - y1 + 1));

    lv_disp_flush_ready(disp);
}

// 触摸读取
bool my_touchpad_read(lv_indev_drv_t *indev, lv_indev_data_t *data) {
    int x, y;
    bool pressed = touch_read(&x, &y);

    if (pressed) {
        data->point.x = x;
        data->point.y = y;
        data->state = LV_INDEV_STATE_PRESSED;
    } else {
        data->state = LV_INDEV_STATE_RELEASED;
    }

    return false;
}
```

---

## 二、控件

### 2.1 基本控件

```c
// 创建按钮
lv_obj_t *btn = lv_btn_create(lv_scr_act());
lv_obj_set_size(btn, 120, 40);
lv_obj_align(btn, LV_ALIGN_CENTER, 0, 0);

// 按钮标签
lv_obj_t *label = lv_label_create(btn);
lv_label_set_text(label, "Click Me");

// 按钮事件
lv_obj_add_event_cb(btn, btn_event_cb, LV_EVENT_CLICKED, NULL);

void btn_event_cb(lv_event_t *e) {
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_CLICKED) {
        printf("Button clicked!\n");
    }
}

// 创建标签
lv_obj_t *label = lv_label_create(lv_scr_act());
lv_label_set_text(label, "Hello LVGL!");
lv_obj_align(label, LV_ALIGN_TOP_MID, 0, 10);

// 创建滑块
lv_obj_t *slider = lv_slider_create(lv_scr_act());
lv_obj_set_width(slider, 200);
lv_obj_align(slider, LV_ALIGN_CENTER, 0, 30);
lv_slider_set_range(slider, 0, 100);
lv_slider_set_value(slider, 50, LV_ANIM_ON);

lv_obj_add_event_cb(slider, slider_event_cb, LV_EVENT_VALUE_CHANGED, NULL);

void slider_event_cb(lv_event_t *e) {
    lv_obj_t *slider = lv_event_get_target(e);
    int value = lv_slider_get_value(slider);
    printf("Slider value: %d\n", value);
}

// 创建开关
lv_obj_t *sw = lv_switch_create(lv_scr_act());
lv_obj_align(sw, LV_ALIGN_CENTER, 0, 70);
lv_obj_add_event_cb(sw, switch_event_cb, LV_EVENT_VALUE_CHANGED, NULL);

// 创建下拉列表
lv_obj_t *dd = lv_dropdown_create(lv_scr_act());
lv_dropdown_set_options(dd, "Option 1\nOption 2\nOption 3");
lv_obj_align(dd, LV_ALIGN_CENTER, 0, 110);

// 创建文本区域
lv_obj_t *ta = lv_textarea_create(lv_scr_act());
lv_textarea_set_one_line(ta, true);
lv_textarea_set_placeholder_text(ta, "Enter text...");
lv_obj_set_size(ta, 200, 40);
lv_obj_align(ta, LV_ALIGN_CENTER, 0, 150);
```

### 2.2 容器与布局

```c
// 创建容器
lv_obj_t *cont = lv_obj_create(lv_scr_act());
lv_obj_set_size(cont, 400, 280);
lv_obj_align(cont, LV_ALIGN_CENTER, 0, 0);

// Flex布局
lv_obj_set_flex_flow(cont, LV_FLEX_FLOW_COLUMN);
lv_obj_set_flex_align(cont, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);

// 添加子控件
for (int i = 0; i < 5; i++) {
    lv_obj_t *btn = lv_btn_create(cont);
    lv_obj_set_size(btn, 150, 35);

    lv_obj_t *label = lv_label_create(btn);
    lv_label_set_text_fmt(label, "Button %d", i + 1);
}

// Grid布局
static lv_coord_t col_dsc[] = {100, 100, 100, LV_GRID_TEMPLATE_LAST};
static lv_coord_t row_dsc[] = {50, 50, 50, LV_GRID_TEMPLATE_LAST};

lv_obj_set_grid_dsc_array(cont, col_dsc, row_dsc);
lv_obj_set_layout(cont, LV_LAYOUT_GRID);

// 滚动容器
lv_obj_t *scroll_cont = lv_obj_create(lv_scr_act());
lv_obj_set_size(scroll_cont, 300, 200);
lv_obj_set_scroll_dir(scroll_cont, LV_DIR_VER);
lv_obj_set_scrollbar_mode(scroll_cont, LV_SCROLLBAR_MODE_AUTO);

// 标签页
lv_obj_t *tabview = lv_tabview_create(lv_scr_act(), LV_DIR_TOP, 40);
lv_obj_t *tab1 = lv_tabview_add_tab(tabview, "Tab 1");
lv_obj_t *tab2 = lv_tabview_add_tab(tabview, "Tab 2");
lv_obj_t *tab3 = lv_tabview_add_tab(tabview, "Tab 3");

// 窗口
lv_obj_t *win = lv_win_create(lv_scr_act(), 40);
lv_win_add_title(win, "Window Title");
lv_obj_t *btn = lv_win_add_btn(win, LV_SYMBOL_CLOSE, 40);
lv_obj_add_event_cb(btn, close_btn_cb, LV_EVENT_CLICKED, win);
```

---

## 三、样式

### 3.1 样式定义

```c
// 创建样式
static lv_style_t style_btn;
lv_style_init(&style_btn);

// 设置样式属性
lv_style_set_bg_color(&style_btn, lv_color_hex(0x007BFF));
lv_style_set_bg_opa(&style_btn, LV_OPA_COVER);
lv_style_set_border_color(&style_btn, lv_color_hex(0x0056B3));
lv_style_set_border_width(&style_btn, 2);
lv_style_set_radius(&style_btn, 10);
lv_style_set_text_color(&style_btn, lv_color_white());
lv_style_set_text_font(&style_btn, &lv_font_montserrat_16);

// 应用样式
lv_obj_add_style(btn, &style_btn, LV_PART_MAIN | LV_STATE_DEFAULT);

// 状态样式
static lv_style_t style_btn_pressed;
lv_style_init(&style_btn_pressed);
lv_style_set_bg_color(&style_btn_pressed, lv_color_hex(0x0056B3));

lv_obj_add_style(btn, &style_btn_pressed, LV_PART_MAIN | LV_STATE_PRESSED);

// 渐变样式
lv_style_set_bg_grad_color(&style_btn, lv_color_hex(0x0056B3));
lv_style_set_bg_grad_dir(&style_btn, LV_GRAD_DIR_VER);

// 阴影
lv_style_set_shadow_color(&style_btn, lv_color_hex(0x000000));
lv_style_set_shadow_width(&style_btn, 10);
lv_style_set_shadow_ofs_x(&style_btn, 5);
lv_style_set_shadow_ofs_y(&style_btn, 5);

// 动画
lv_style_set_transition(&style_btn, &(lv_style_transition_dsc_t){
    .time = 300,
    .delay = 0,
    .prop_cnt = 1,
    .props = (lv_style_prop_t[]){LV_STYLE_BG_COLOR},
    .path = &lv_path_ease_in_out
});
```

### 3.2 主题定制

```c
// 自定义主题
static lv_theme_t my_theme;
lv_theme_t *my_theme_init(lv_disp_t *disp) {
    lv_theme_basic_init(&my_theme);

    // 设置默认样式
    lv_style_t *style;
    style = lv_theme_get_style(&my_theme, LV_THEME_DEFAULT);
    lv_style_set_bg_color(style, lv_color_hex(0xF5F5F5));

    // 按钮样式
    style = lv_theme_get_style(&my_theme, LV_THEME_BTN);
    lv_style_set_bg_color(style, lv_color_hex(0x2196F3));

    return &my_theme;
}

// 应用主题
lv_disp_set_theme(disp, my_theme_init(disp));
```

---

## 四、图表

### 4.1 图表控件

```c
// 创建图表
lv_obj_t *chart = lv_chart_create(lv_scr_act());
lv_obj_set_size(chart, 400, 250);
lv_obj_align(chart, LV_ALIGN_CENTER, 0, 0);

// 设置图表类型
lv_chart_set_type(chart, LV_CHART_TYPE_LINE);

// 设置点数
lv_chart_set_point_count(chart, 50);

// 添加数据系列
lv_chart_series_t *ser1 = lv_chart_add_series(chart, lv_color_hex(0xFF0000), LV_CHART_AXIS_PRIMARY_Y);
lv_chart_series_t *ser2 = lv_chart_add_series(chart, lv_color_hex(0x00FF00), LV_CHART_AXIS_SECONDARY_Y);

// 设置值
for (int i = 0; i < 50; i++) {
    lv_chart_set_next_value(chart, ser1, rand() % 100);
    lv_chart_set_next_value(chart, ser2, rand() % 50);
}

// 刷新图表
lv_chart_refresh(chart);

// 设置范围
lv_chart_set_range(chart, LV_CHART_AXIS_PRIMARY_Y, 0, 100);
lv_chart_set_range(chart, LV_CHART_AXIS_SECONDARY_Y, 0, 50);

// 网格线
lv_chart_set_grid_line(chart, true, true, true, true);

// 刻度
lv_chart_set_axis_tick(chart, LV_CHART_AXIS_PRIMARY_Y, 10, 5, 6, 2, true, 50);
```

### 4.2 仪表盘

```c
// 创建仪表盘
lv_obj_t *gauge = lv_gauge_create(lv_scr_act());
lv_obj_set_size(gauge, 200, 200);
lv_obj_align(gauge, LV_ALIGN_CENTER, 0, 0);

// 设置刻度
lv_gauge_set_scale(gauge, 270, 15, 10);

// 设置范围
lv_gauge_set_range(gauge, 0, 100);

// 设置值
lv_gauge_set_value(gauge, 0, 75);

// 设置颜色
lv_gauge_set_needle_count(gauge, 1, (lv_color_t[]){
    lv_color_hex(0xFF0000)
});

// 创建标签
lv_obj_t *gauge_label = lv_label_create(gauge);
lv_label_set_text(gauge_label, "75%");
lv_obj_align(gauge_label, LV_ALIGN_CENTER, 0, 30);
```

---

## 五、动画

### 5.1 动画系统

```c
// 动画变量
static lv_anim_t a;

// 动画回调
void anim_x_cb(void *var, int32_t value) {
    lv_obj_set_x((lv_obj_t *)var, value);
}

// 创建动画
lv_anim_init(&a);
lv_anim_set_var(&a, btn);
lv_anim_set_values(&a, 0, 200);
lv_anim_set_time(&a, 1000);
lv_anim_set_exec_cb(&a, (lv_anim_exec_xcb_t)anim_x_cb);
lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
lv_anim_set_playback_time(&a, 500);  // 回放
lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);  // 无限重复

lv_anim_start(&a);

// 预定义动画路径
lv_anim_set_path_cb(&a, lv_anim_path_linear);      // 线性
lv_anim_set_path_cb(&a, lv_anim_path_ease_in);      // 缓入
lv_anim_set_path_cb(&a, lv_anim_path_ease_out);     // 缓出
lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);  // 缓入缓出
lv_anim_set_path_cb(&a, lv_anim_path_overshoot);    // 超调
lv_anim_set_path_cb(&a, lv_anim_path_bounce);       // 弹跳

// 自定义路径
int32_t my_path_cb(const lv_anim_t *a, int32_t x) {
    // 自定义缓动函数
    float t = (float)x / a->end_value;
    return (int32_t)(a->end_value * sin(t * M_PI));
}

// 颜色动画
void anim_color_cb(void *var, int32_t value) {
    lv_obj_set_style_bg_color((lv_obj_t *)var, lv_color_hex(value), 0);
}

lv_anim_set_values(&a, 0xFF0000, 0x0000FF);
lv_anim_set_exec_cb(&a, anim_color_cb);

// 透明度动画
void anim_opa_cb(void *var, int32_t value) {
    lv_obj_set_style_opa((lv_obj_t *)var, value, 0);
}

lv_anim_set_values(&a, LV_OPA_TRANSP, LV_OPA_COVER);
lv_anim_set_exec_cb(&a, anim_opa_cb);
```

---

## 六、字体

### 6.1 字体配置

```c
// 内置字体
// lv_font_montserrat_14
// lv_font_montserrat_16
// lv_font_montserrat_20
// lv_font_montserrat_24
// lv_font_montserrat_28
// lv_font_montserrat_32

// 使用字体
lv_style_set_text_font(&style, &lv_font_montserrat_20);

// 自定义字体(使用工具生成)
// 在lv_conf.h中启用:
// #define LV_FONT_MONTSERRAT_14 1
// #define LV_FONT_CUSTOM_1 1

// 字体包含中文
// 使用LVGL字体工具生成包含中文字符的字体
// lv_font_conv --bpp 4 --size 16 --font NotoSansCJK-Regular.ttc
//              --range 0x4E00-0x9FFF --format lvgl
//              -o my_font_cn.c

// 使用中文字体
// extern const lv_font_t my_font_cn;
// lv_style_set_text_font(&style, &my_font_cn);
```

---

## 七、文件系统

### 7.1 文件系统接口

```c
// 文件系统驱动注册
lv_fs_drv_t drv;
lv_fs_drv_init(&drv);

drv.letter = 'S';  // 驱动字母
drv.open_cb = my_fs_open;
drv.close_cb = my_fs_close;
drv.read_cb = my_fs_read;
drv.write_cb = my_fs_write;
drv.seek_cb = my_fs_seek;
drv.tell_cb = my_fs_tell;

lv_fs_drv_register(&drv);

// 文件操作回调
void *my_fs_open(lv_fs_drv_t *drv, const char *path, lv_fs_mode_t mode) {
    const char *flags = (mode == LV_FS_MODE_WR) ? "wb" : "rb";
    return fopen(path, flags);
}

lv_fs_res_t my_fs_close(lv_fs_drv_t *drv, void *file_p) {
    fclose((FILE *)file_p);
    return LV_FS_RES_OK;
}

lv_fs_res_t my_fs_read(lv_fs_drv_t *drv, void *file_p, void *buf, uint32_t btr, uint32_t *br) {
    *br = fread(buf, 1, btr, (FILE *)file_p);
    return LV_FS_RES_OK;
}

// 使用文件系统
lv_file_t f;
lv_fs_res_t res = lv_fs_open(&f, "S:/data/config.bin", LV_FS_MODE_RD);
if (res == LV_FS_RES_OK) {
    uint8_t buf[64];
    uint32_t br;
    lv_fs_read(&f, buf, sizeof(buf), &br);
    lv_fs_close(&f);
}

// 图片文件
lv_img_set_src(img, "S:/images/logo.bin");
```

---

## 附录：LVGL配置

```c
// lv_conf.h 常用配置
// #define LV_COLOR_DEPTH          16
// #define LV_HOR_RES_MAX          480
// #define LV_VER_RES_MAX          320
// #define LV_FONT_MONTSERRAT_14   1
// #define LV_USE_THEME_DEFAULT    1
// #define LV_USE_THEME_BASIC      1
// #define LV_USE_BTN              1
// #define LV_USE_LABEL            1
// #define LV_USE_SLIDER           1
// #define LV_USE_CHART            1
// #define LV_USE_TEXTAREA         1
// #define LV_USE_DROPDOWN         1
// #define LV_USE_SWITCH           1
// #define LV_USE_ANIMATION        1
```

---

## 相关链接

- [[LVGL]] - LVGL基础
- [[嵌入式GUI技术]] - GUI技术
- [[ESP-IDF开发详解]] - ESP32开发
- [[嵌入式系统基础]] - 嵌入式系统
