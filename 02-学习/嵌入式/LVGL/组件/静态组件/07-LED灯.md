# LED灯 (lv_led)

> **重要性**: ★★★☆☆ (7/10) — 状态指示专用控件

## 概述
LED 是矩形/圆形控件，亮度可调。低亮度时颜色变暗。

## 部件与样式
| 部件 | 说明 |
|------|------|
| `LV_PART_MAIN` | 使用典型背景样式属性 |

## 核心 API

```c
lv_led_set_color(led, lv_color_hex(0xff0000));   // 设置颜色
lv_led_set_brightness(led, brightness);            // 亮度 0-255
lv_led_on(led);      // 设置为ON亮度（默认255）
lv_led_off(led);     // 设置为OFF亮度（默认80）
lv_led_toggle(led);  // 切换ON/OFF
```

## 事件与按键
- 无特殊事件，不处理按键

## 关键要点
- 状态指示灯（在线/离线、报警/正常）
- 比简单圆形更直观
- 亮度范围可通过 `LV_LED_BRIGHT_MAX/MIN` 自定义
