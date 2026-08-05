# GIF动图 (lv_gif)

> **重要性**: ★★☆☆☆ (6/10) — 简单动画展示

## 概述
GIF 控件使用 AnimatedGIF 库加载和播放 GIF 动画。

## 部件与样式
| 部件 | 说明 |
|------|------|
| `LV_PART_MAIN` | 背景 |

## 核心 API

```c
lv_obj_t *gif = lv_gif_create(parent);
lv_gif_set_color_format(gif, LV_COLOR_FORMAT_ARGB8888);  // 在 set_src 之前调用
lv_gif_set_src(gif, src);  // 支持 C 数组和文件
```

### 颜色格式
| 格式 | 像素大小 | 说明 |
|------|---------|------|
| RGB565 | 2 | 省内存，无透明 |
| RGB888 | 3 | - |
| ARGB8888 | 4 | 默认，支持透明 |

### 来源
```c
// C 数组
LV_IMAGE_DECLARE(my_gif_array);
lv_gif_set_src(gif, &my_gif_array);

// 文件
lv_gif_set_src(gif, "S:path/to/anim.gif");
```

## 内存需求
- 基础: ~25 kB RAM
- 额外: `(像素大小 + 1) × 宽 × 高`

## 事件
- `LV_EVENT_READY` — 动画完成最后一帧时

## 关键要点
- 简单动画、加载动画、状态动画
- 需在 `lv_conf.h` 中启用 `LV_USE_GIF`
- ARGB8888 支持透明但内存最大
- 转换脚本: `scripts/LVGLImage.py --cf RAW --ofmt C input.gif`
