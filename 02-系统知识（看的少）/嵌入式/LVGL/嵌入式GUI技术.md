# 嵌入式GUI技术

## 核心概念

- **LVGL** - 轻量级图形库
- **帧缓冲** - 显存管理
- **控件** - UI元素
- **事件驱动** - 用户交互

---

## 一、LVGL基础

### 1.1 LVGL架构

```
┌─────────────────────────────┐
│         应用层              │
│    (控件、事件、动画)        │
├─────────────────────────────┤
│         LVGL核心            │
│  (绘图引擎、对象系统、样式)  │
├─────────────────────────────┤
│         显示驱动            │
│    (帧缓冲、刷新回调)       │
├─────────────────────────────┤
│         硬件层              │
│    (LCD控制器、SPI/RGB)     │
└─────────────────────────────┘
```

---

### 1.2 LVGL移植

```c
#include "lvgl.h"
#include "lv_port_disp.h"

// 显示缓冲区
static lv_disp_draw_buf_t disp_buf;
static lv_color_t buf1[MY_DISP_HOR_RES * 10];
static lv_color_t buf2[MY_DISP_HOR_RES * 10];

// 显示驱动回调
static void disp_flush(lv_disp_drv_t *drv, const lv_area_t *area, lv_color_t *color_p) {
    int32_t x, y;
    for (y = area->y1; y <= area->y2; y++) {
        for (x = area->x1; x <= area->x2; x++) {
            lcd_set_pixel(x, y, color_p->full);
            color_p++;
        }
    }
    lv_disp_flush_ready(drv);
}

// 初始化
void lv_port_disp_init(void) {
    lv_init();

    lv_disp_draw_buf_init(&disp_buf, buf1, buf2, MY_DISP_HOR_RES * 10);

    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init(&disp_drv);
    disp_drv.draw_buf = &disp_buf;
    disp_drv.flush_cb = disp_flush;
    disp_drv.hor_res = MY_DISP_HOR_RES;
    disp_drv.ver_res = MY_DISP_VER_RES;
    lv_disp_drv_register(&disp_drv);
}
```

---

### 1.3 输入设备驱动

```c
// 触摸屏驱动
static void touchpad_read(lv_indev_drv_t *drv, lv_indev_data_t *data) {
    static int16_t last_x = 0, last_y = 0;

    if (touch_is_pressed()) {
        data->state = LV_INDEV_STATE_PRESSED;
        touch_get_xy(&last_x, &last_y);
    } else {
        data->state = LV_INDEV_STATE_RELEASED;
    }

    data->point.x = last_x;
    data->point.y = last_y;
}

// 编码器输入
static void encoder_read(lv_indev_drv_t *drv, lv_indev_data_t *data) {
    data->enc_diff = encoder_get_diff();
    data->state = encoder_is_pressed() ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}

void lv_port_indev_init(void) {
    static lv_indev_drv_t touch_drv;
    lv_indev_drv_init(&touch_drv);
    touch_drv.type = LV_INDEV_TYPE_POINTER;
    touch_drv.read_cb = touchpad_read;
    lv_indev_drv_register(&touch_drv);
}
```

---

## 二、LVGL控件

### 2.1 基础控件

```c
// 标签
void create_label(void) {
    lv_obj_t *label = lv_label_create(lv_scr_act());
    lv_label_set_text(label, "Hello LVGL!");
    lv_obj_set_style_text_font(label, &lv_font_montserrat_16, 0);
    lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);
}

// 按钮
void create_button(void) {
    lv_obj_t *btn = lv_btn_create(lv_scr_act());
    lv_obj_set_size(btn, 120, 40);
    lv_obj_align(btn, LV_ALIGN_CENTER, 0, 50);

    lv_obj_t *label = lv_label_create(btn);
    lv_label_set_text(label, "Click Me");

    lv_obj_add_event_cb(btn, btn_event_cb, LV_EVENT_CLICKED, NULL);
}

static void btn_event_cb(lv_event_t *e) {
    lv_event_code_t code = lv_event_get_code(e);
    if (code == LV_EVENT_CLICKED) {
        printf("Button clicked!\n");
    }
}
```

---

### 2.2 滑块和进度条

```c
// 滑块
void create_slider(void) {
    lv_obj_t *slider = lv_slider_create(lv_scr_act());
    lv_obj_set_width(slider, 200);
    lv_obj_align(slider, LV_ALIGN_CENTER, 0, 0);
    lv_slider_set_range(slider, 0, 100);
    lv_slider_set_value(slider, 50, LV_ANIM_ON);

    lv_obj_add_event_cb(slider, slider_event_cb, LV_EVENT_VALUE_CHANGED, NULL);

    // 值标签
    lv_obj_t *label = lv_label_create(lv_scr_act());
    lv_obj_align_to(label, slider, LV_ALIGN_OUT_BOTTOM_MID, 0, 10);
    lv_label_set_text(label, "50%");
}

static void slider_event_cb(lv_event_t *e) {
    lv_obj_t *slider = lv_event_get_target(e);
    int32_t val = lv_slider_get_value(slider);
    char buf[8];
    snprintf(buf, sizeof(buf), "%ld%%", val);
    // 更新标签
}

// 进度条
void create_bar(void) {
    lv_obj_t *bar = lv_bar_create(lv_scr_act());
    lv_obj_set_size(bar, 200, 20);
    lv_obj_align(bar, LV_ALIGN_CENTER, 0, 0);
    lv_bar_set_range(bar, 0, 100);
    lv_bar_set_value(bar, 70, LV_ANIM_ON);
}
```

---

### 2.3 列表和下拉菜单

```c
// 列表
void create_list(void) {
    lv_obj_t *list = lv_list_create(lv_scr_act());
    lv_obj_set_size(list, 200, 300);
    lv_obj_align(list, LV_ALIGN_CENTER, 0, 0);

    lv_obj_t *btn;
    btn = lv_list_add_btn(list, LV_SYMBOL_WIFI, "WiFi");
    lv_obj_add_event_cb(btn, list_event_cb, LV_EVENT_CLICKED, (void*)"wifi");

    btn = lv_list_add_btn(list, LV_SYMBOL_BLUETOOTH, "Bluetooth");
    lv_obj_add_event_cb(btn, list_event_cb, LV_EVENT_CLICKED, (void*)"bt");

    btn = lv_list_add_btn(list, LV_SYMBOL_SETTINGS, "Settings");
    lv_obj_add_event_cb(btn, list_event_cb, LV_EVENT_CLICKED, (void*)"settings");
}

// 下拉菜单
void create_dropdown(void) {
    lv_obj_t *dd = lv_dropdown_create(lv_scr_act());
    lv_dropdown_set_options(dd, "Option 1\nOption 2\nOption 3");
    lv_obj_align(dd, LV_ALIGN_CENTER, 0, 0);
    lv_obj_add_event_cb(dd, dd_event_cb, LV_EVENT_VALUE_CHANGED, NULL);
}
```

---

### 2.4 图表

```c
// 实时数据图表
static lv_obj_t *chart;
static lv_chart_series_t *ser1;

void create_chart(void) {
    chart = lv_chart_create(lv_scr_act());
    lv_obj_set_size(chart, 300, 200);
    lv_obj_align(chart, LV_ALIGN_CENTER, 0, 0);
    lv_chart_set_type(chart, LV_CHART_TYPE_LINE);
    lv_chart_set_point_count(chart, 50);
    lv_chart_set_range(chart, LV_CHART_AXIS_PRIMARY_Y, 0, 100);

    ser1 = lv_chart_add_series(chart, lv_palette_main(LV_PALETTE_RED), LV_CHART_AXIS_PRIMARY_Y);
    lv_chart_refresh(chart);
}

// 更新图表数据
void chart_update(float value) {
    lv_chart_set_next_value(chart, ser1, (int16_t)value);
}
```

---

## 三、样式系统

### 3.1 样式定义

```c
// 创建样式
static lv_style_t style_btn;
static lv_style_t style_card;

void init_styles(void) {
    // 按钮样式
    lv_style_init(&style_btn);
    lv_style_set_radius(&style_btn, 10);
    lv_style_set_bg_color(&style_btn, lv_palette_main(LV_PALETTE_BLUE));
    lv_style_set_bg_opa(&style_btn, LV_OPA_COVER);
    lv_style_set_border_width(&style_btn, 0);
    lv_style_set_text_color(&style_btn, lv_color_white());

    // 卡片样式
    lv_style_init(&style_card);
    lv_style_set_radius(&style_card, 12);
    lv_style_set_bg_color(&style_card, lv_color_white());
    lv_style_set_bg_opa(&style_card, LV_OPA_COVER);
    lv_style_set_shadow_width(&style_card, 20);
    lv_style_set_shadow_color(&style_card, lv_color_make(0, 0, 0));
    lv_style_set_shadow_opa(&style_card, LV_OPA_20);
}

// 应用样式
lv_obj_add_style(btn, &style_btn, 0);
```

---

### 3.2 主题定制

```c
// 自定义主题
void custom_theme_init(void) {
    lv_theme_t *th = lv_theme_default_init(
        lv_disp_get_default(),
        lv_palette_main(LV_PALETTE_BLUE),
        lv_palette_main(LV_PALETTE_RED),
        true,  // dark mode
        LV_FONT_DEFAULT
    );
    lv_disp_set_theme(lv_disp_get_default(), th);
}
```

---

## 四、动画系统

### 4.1 基础动画

```c
// 动画回调
static void anim_x_cb(void *var, int32_t v) {
    lv_obj_set_x((lv_obj_t *)var, v);
}

// 创建动画
void animate_button(void) {
    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, btn);
    lv_anim_set_values(&a, 0, 200);
    lv_anim_set_time(&a, 500);
    lv_anim_set_exec_cb(&a, anim_x_cb);
    lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out);
    lv_anim_start(&a);
}

// 弹簧动画路径
static int32_t anim_path_spring(const lv_anim_t *a) {
    int32_t t = lv_anim_path_linear(a);
    float f = (float)t / LV_ANIM_RESOLUTION;
    float spring = sinf(f * 3.14f * 3) * (1.0f - f);
    return (int32_t)(spring * LV_ANIM_RESOLUTION);
}
```

---

### 4.2 加载动画

```c
// 旋转加载
void create_spinner(void) {
    lv_obj_t *spinner = lv_spinner_create(lv_scr_act(), 1000, 60);
    lv_obj_set_size(spinner, 60, 60);
    lv_obj_align(spinner, LV_ALIGN_CENTER, 0, 0);
}

// 进度动画
void create_loading_bar(void) {
    lv_obj_t *bar = lv_bar_create(lv_scr_act());
    lv_obj_set_size(bar, 200, 10);
    lv_bar_set_mode(bar, LV_BAR_MODE_INDICATOR);

    lv_anim_t a;
    lv_anim_init(&a);
    lv_anim_set_var(&a, bar);
    lv_anim_set_values(&a, 0, 100);
    lv_anim_set_time(&a, 2000);
    lv_anim_set_repeat_count(&a, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_exec_cb(&a, (lv_anim_exec_xcb_t)lv_bar_set_value);
    lv_anim_start(&a);
}
```

---

## 五、布局系统

### 5.1 Flex布局

```c
// Flex容器
void create_flex_layout(void) {
    lv_obj_t *cont = lv_obj_create(lv_scr_act());
    lv_obj_set_size(cont, 300, 200);
    lv_obj_align(cont, LV_ALIGN_CENTER, 0, 0);

    // 设置Flex布局
    lv_obj_set_flex_flow(cont, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_flex_align(cont, LV_FLEX_ALIGN_SPACE_EVENLY, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_set_style_pad_all(cont, 10, 0);
    lv_obj_set_style_pad_gap(cont, 10, 0);

    // 添加子元素
    for (int i = 0; i < 6; i++) {
        lv_obj_t *btn = lv_btn_create(cont);
        lv_obj_set_size(btn, 80, 40);

        lv_obj_t *label = lv_label_create(btn);
        char buf[8];
        snprintf(buf, sizeof(buf), "Btn %d", i);
        lv_label_set_text(label, buf);
    }
}
```

---

### 5.2 Grid布局

```c
// Grid布局
static lv_coord_t col_dsc[] = {LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};
static lv_coord_t row_dsc[] = {LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_FR(1), LV_GRID_TEMPLATE_LAST};

void create_grid_layout(void) {
    lv_obj_t *cont = lv_obj_create(lv_scr_act());
    lv_obj_set_size(cont, 300, 300);
    lv_obj_set_layout(cont, LV_LAYOUT_GRID);
    lv_obj_set_grid_dsc_array(cont, col_dsc, row_dsc);

    for (int i = 0; i < 9; i++) {
        lv_obj_t *btn = lv_btn_create(cont);
        lv_obj_set_grid_cell(btn, LV_GRID_ALIGN_STRETCH, i % 3, 1,
                             LV_GRID_ALIGN_STRETCH, i / 3, 1);
    }
}
```

---

## 六、LVGL多页面

### 6.1 页面切换

```c
// 页面管理器
static lv_obj_t *pages[3];
static int current_page = 0;

void page_manager_init(void) {
    pages[0] = create_home_page();
    pages[1] = create_settings_page();
    pages[2] = create_about_page();

    // 隐藏所有页面
    for (int i = 0; i < 3; i++) {
        lv_obj_add_flag(pages[i], LV_OBJ_FLAG_HIDDEN);
    }

    // 显示首页
    lv_obj_clear_flag(pages[0], LV_OBJ_FLAG_HIDDEN);
}

void switch_page(int page) {
    if (page == current_page) return;

    lv_obj_add_flag(pages[current_page], LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(pages[page], LV_OBJ_FLAG_HIDDEN);
    current_page = page;
}

// 首页
lv_obj_t *create_home_page(void) {
    lv_obj_t *page = lv_obj_create(lv_scr_act());
    lv_obj_set_size(page, LV_PCT(100), LV_PCT(100));

    lv_obj_t *title = lv_label_create(page);
    lv_label_set_text(title, "Home");
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

    return page;
}
```

---

## 七、字体管理

### 7.1 自定义字体

```c
// 在lv_conf.h中启用
// #define LV_FONT_MONTSERRAT_16 1

// 使用中文字体(需要转换工具)
// lv_font_conv --bpp 4 --size 16 --font SimSun.ttf -r 0x20-0x7F,0x4E00-0x9FFF --format lvgl -o my_font.c

// 使用自定义字体
LV_FONT_DECLARE(my_chinese_font);

void create_chinese_label(void) {
    lv_obj_t *label = lv_label_create(lv_scr_act());
    lv_obj_set_style_text_font(label, &my_chinese_font, 0);
    lv_label_set_text(label, "你好世界");
    lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);
}
```

---

## 八、性能优化

### 8.1 渲染优化

```c
// 部分刷新(只刷新变化区域)
lv_obj_invalidate(obj);  // 标记需要刷新的对象

// 减少重绘
lv_obj_clear_flag(obj, LV_OBJ_FLAG_CLICKABLE);  // 不可点击的对象不响应事件

// 缓存
lv_obj_add_flag(obj, LV_OBJ_FLAG_EVENT_BUBBLE);  // 事件冒泡

// 使用双缓冲
static lv_color_t buf1[DISP_HOR_RES * DISP_VER_RES / 10];
static lv_color_t buf2[DISP_HOR_RES * DISP_VER_RES / 10];
lv_disp_draw_buf_init(&disp_buf, buf1, buf2, sizeof(buf1)/sizeof(buf1[0]));
```

---

### 8.2 内存优化

```c
// 内存配置(lv_conf.h)
// #define LV_MEM_CUSTOM 0
// #define LV_MEM_SIZE (32 * 1024)  // 32KB

// 减少控件数量
// 使用图片数组而非位图

// 图片压缩
// 使用LV_IMG_CF_TRUE_COLOR_ALPHA而非LV_IMG_CF_TRUE_COLOR
```

---

## 九、文件系统集成

### 9.1 文件浏览器

```c
// 文件系统驱动
void lv_port_fs_init(void) {
    static lv_fs_drv_t fs_drv;
    lv_fs_drv_init(&fs_drv);
    fs_drv.letter = 'S';  // SPIFFS驱动器号
    fs_drv.open_cb = fs_open;
    fs_drv.read_cb = fs_read;
    fs_drv.write_cb = fs_write;
    fs_drv.close_cb = fs_close;
    fs_drv.seek_cb = fs_seek;
    fs_drv.tell_cb = fs_tell;
    lv_fs_drv_register(&fs_drv);
}

// 加载文件图片
void load_image_from_file(void) {
    lv_obj_t *img = lv_img_create(lv_scr_act());
    lv_img_set_src(img, "S:/img/logo.bin");
    lv_obj_align(img, LV_ALIGN_CENTER, 0, 0);
}
```

---

## 附录：LVGL配置

### 常用配置项(lv_conf.h)

```c
// 颜色深度
#define LV_COLOR_DEPTH 16

// 显示分辨率
#define MY_DISP_HOR_RES 320
#define MY_DISP_VER_RES 240

// 内存大小
#define LV_MEM_SIZE (32 * 1024)

// 启用控件
#define LV_USE_LABEL 1
#define LV_USE_BTN 1
#define LV_USE_SLIDER 1
#define LV_USE_CHART 1
#define LV_USE_LIST 1

// 动画
#define LV_USE_ANIMATION 1

// 字体
#define LV_FONT_MONTSERRAT_16 1
```

---

## 相关链接

- [[ESP-IDF开发详解]] - ESP32开发
- [[图像处理技术]] - 图像处理
- [[STM32基础]] - STM32开发
