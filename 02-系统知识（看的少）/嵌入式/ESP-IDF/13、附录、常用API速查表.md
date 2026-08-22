# ESP-IDF 附录 - 常用API速查表

## 目录

- [GPIO API](#gpio-api)
- [任务管理API](#任务管理api)
- [队列与信号量API](#队列与信号量api)
- [定时器API](#定时器api)
- [UART API](#uart-api)
- [I2C API](#i2c-api)
- [SPI API](#spi-api)
- [WiFi API](#wifi-api)
- [NVS API](#nvs-api)
- [OTA API](#ota-api)
- [事件循环API](#事件循环api)
- [错误码速查](#错误码速查)

---

## GPIO API

### 基础配置

| API | 说明 | 示例 |
|-----|------|------|
| `gpio_config()` | 配置GPIO | `gpio_config(&io_conf)` |
| `gpio_set_direction()` | 设置方向 | `gpio_set_direction(GPIO_NUM_2, GPIO_MODE_OUTPUT)` |
| `gpio_set_level()` | 设置电平 | `gpio_set_level(GPIO_NUM_2, 1)` |
| `gpio_get_level()` | 读取电平 | `int level = gpio_get_level(GPIO_NUM_4)` |
| `gpio_set_pull_mode()` | 设置上下拉 | `gpio_set_pull_mode(GPIO_NUM_0, GPIO_PULLUP_ONLY)` |

### 中断管理

| API | 说明 |
|-----|------|
| `gpio_install_isr_service()` | 安装ISR服务 |
| `gpio_uninstall_isr_service()` | 卸载ISR服务 |
| `gpio_isr_handler_add()` | 添加中断处理 |
| `gpio_isr_handler_remove()` | 移除中断处理 |
| `gpio_wakeup_enable()` | 启用唤醒功能 |

### 常用宏

```c
GPIO_NUM_0 ~ GPIO_NUM_39      // GPIO编号
GPIO_MODE_INPUT               // 输入模式
GPIO_MODE_OUTPUT              // 输出模式
GPIO_MODE_INPUT_OUTPUT        // 输入输出模式
GPIO_MODE_OUTPUT_OD           // 开漏输出
GPIO_PULLUP_ENABLE            // 上拉使能
GPIO_PULLDOWN_ENABLE          // 下拉使能
GPIO_INTR_NEGEDGE             // 下降沿触发
GPIO_INTR_POSEDGE             // 上升沿触发
GPIO_INTR_ANYEDGE             // 任意边沿触发
```

---

## 任务管理API

### FreeRTOS任务

| API | 说明 |
|-----|------|
| `xTaskCreate()` | 创建任务（任意核心） |
| `xTaskCreatePinnedToCore()` | 创建任务（指定核心） |
| `vTaskDelete()` | 删除任务 |
| `vTaskDelay()` | 相对延时 |
| `vTaskDelayUntil()` | 绝对延时 |
| `vTaskSuspend()` | 挂起任务 |
| `vTaskResume()` | 恢复任务 |
| `vTaskPrioritySet()` | 设置优先级 |
| `uxTaskPriorityGet()` | 获取优先级 |
| `xTaskGetTickCount()` | 获取tick计数 |

### 任务通知

| API | 说明 |
|-----|------|
| `xTaskNotifyGive()` | 发送通知 |
| `ulTaskNotifyTake()` | 接收通知 |
| `vTaskNotifyGiveFromISR()` | ISR中发送通知 |

### 常用宏

```c
pdMS_TO_TICKS(ms)             // 毫秒转tick
portTICK_PERIOD_MS            // tick周期（默认10ms）
portMAX_DELAY                 // 无限等待
configMAX_PRIORITIES          // 最大优先级数
```

---

## 队列与信号量API

### 队列操作

| API | 说明 |
|-----|------|
| `xQueueCreate()` | 创建队列 |
| `xQueueSend()` | 发送到队列 |
| `xQueueReceive()` | 从队列接收 |
| `xQueuePeek()` | 查看队列 |
| `xQueueSendFromISR()` | ISR中发送 |
| `uxQueueMessagesWaiting()` | 获取消息数 |
| `vQueueDelete()` | 删除队列 |

### 信号量

| API | 说明 |
|-----|------|
| `xSemaphoreCreateBinary()` | 创建二值信号量 |
| `xSemaphoreCreateCounting()` | 创建计数信号量 |
| `xSemaphoreCreateMutex()` | 创建互斥锁 |
| `xSemaphoreGive()` | 释放信号量 |
| `xSemaphoreTake()` | 获取信号量 |
| `xSemaphoreGiveFromISR()` | ISR中释放 |
| `vSemaphoreDelete()` | 删除信号量 |

---

## 定时器API

### FreeRTOS延时

| API | 说明 |
|-----|------|
| `vTaskDelay()` | 相对延时 |
| `vTaskDelayUntil()` | 绝对延时（周期任务） |
| `xTaskGetTickCount()` | 获取当前tick |

### GPTimer

| API | 说明 |
|-----|------|
| `gptimer_new_timer()` | 创建定时器 |
| `gptimer_del_timer()` | 删除定时器 |
| `gptimer_set_alarm_action()` | 配置报警 |
| `gptimer_register_event_callbacks()` | 注册回调 |
| `gptimer_enable()` | 使能定时器 |
| `gptimer_start()` | 启动定时器 |
| `gptimer_stop()` | 停止定时器 |
| `gptimer_get_raw_count()` | 获取计数值 |
| `gptimer_set_raw_count()` | 设置计数值 |

### esp_timer

| API | 说明 |
|-----|------|
| `esp_timer_create()` | 创建软件定时器 |
| `esp_timer_start_once()` | 启动单次定时器 |
| `esp_timer_start_periodic()` | 启动周期定时器 |
| `esp_timer_stop()` | 停止定时器 |
| `esp_timer_delete()` | 删除定时器 |
| `esp_timer_get_time()` | 获取系统运行时间 |

---

## UART API

### 配置

| API | 说明 |
|-----|------|
| `uart_param_config()` | 配置UART参数 |
| `uart_set_pin()` | 设置UART引脚 |
| `uart_set_baudrate()` | 设置波特率 |
| `uart_driver_install()` | 安装驱动 |
| `uart_driver_delete()` | 卸载驱动 |

### 数据收发

| API | 说明 |
|-----|------|
| `uart_write_bytes()` | 发送数据 |
| `uart_read_bytes()` | 接收数据 |
| `uart_flush()` | 清空缓冲区 |
| `uart_wait_tx_done()` | 等待发送完成 |
| `uart_get_buffered_data_len()` | 获取接收缓冲数据量 |

### 流控

| API | 说明 |
|-----|------|
| `uart_set_hw_flow_ctrl()` | 设置硬件流控 |
| `uart_set_mode()` | 设置UART模式 |
| `uart_set_rs485_pins()` | 设置RS485引脚 |

### 常用宏

```c
UART_NUM_0 / UART_NUM_1 / UART_NUM_2    // UART端口号
UART_DATA_8_BITS                        // 8数据位
UART_PARITY_DISABLE                     // 无校验
UART_STOP_BITS_1                        // 1停止位
UART_HW_FLOWCTRL_DISABLE                // 无流控
115200 / 9600                           // 常用波特率
```

---

## I2C API

### 新驱动API（推荐）

| API | 说明 |
|-----|------|
| `i2c_new_master_bus()` | 创建I2C主设备 |
| `i2c_del_master_bus()` | 删除I2C主设备 |
| `i2c_master_bus_add_device()` | 添加从设备 |
| `i2c_master_bus_rm_device()` | 移除从设备 |
| `i2c_master_transmit()` | 发送数据 |
| `i2c_master_receive()` | 接收数据 |
| `i2c_master_transmit_receive()` | 发送后接收 |

### 传统驱动API

| API | 说明 |
|-----|------|
| `i2c_param_config()` | 配置I2C参数 |
| `i2c_driver_install()` | 安装驱动 |
| `i2c_cmd_link_create()` | 创建命令链接 |
| `i2c_master_start()` | 起始位 |
| `i2c_master_stop()` | 停止位 |
| `i2c_master_write()` | 写数据 |
| `i2c_master_read()` | 读数据 |
| `i2c_master_cmd_begin()` | 执行命令 |

### 常用宏

```c
I2C_NUM_0 / I2C_NUM_1         // I2C端口号
I2C_MODE_MASTER               // 主设备模式
I2C_ADDR_BIT_LEN_7            // 7位地址
I2C_ADDR_BIT_LEN_10           // 10位地址
100000 / 400000               // 常用频率(Hz)
```

---

## SPI API

### 总线管理

| API | 说明 |
|-----|------|
| `spi_bus_initialize()` | 初始化SPI总线 |
| `spi_bus_free()` | 释放SPI总线 |
| `spi_bus_add_device()` | 添加设备 |
| `spi_bus_remove_device()` | 移除设备 |

### 数据传输

| API | 说明 |
|-----|------|
| `spi_device_transmit()` | 同步传输 |
| `spi_device_queue_trans()` | 排队传输（异步） |
| `spi_device_get_trans_result()` | 获取传输结果 |
| `spi_device_polling_transmit()` | 轮询传输 |

### 从机模式

| API | 说明 |
|-----|------|
| `spi_slave_initialize()` | 初始化从机 |
| `spi_slave_free()` | 释放从机 |
| `spi_slave_transmit()` | 从机传输 |

### 常用宏

```c
SPI2_HOST / SPI3_HOST         // SPI主机编号
SPI_DMA_CH_AUTO               // 自动DMA通道
SPI_TRANS_USE_RXDATA          // 使用内联接收数据
SPI_TRANS_USE_TXDATA          // 使用内联发送数据
SPI_TRANS_CS_KEEP_ACTIVE      // 保持CS有效
```

---

## WiFi API

### 初始化

| API | 说明 |
|-----|------|
| `esp_wifi_init()` | 初始化WiFi |
| `esp_wifi_deinit()` | 反初始化 |
| `esp_wifi_set_mode()` | 设置模式 |
| `esp_wifi_get_mode()` | 获取模式 |
| `esp_wifi_start()` | 启动WiFi |
| `esp_wifi_stop()` | 停止WiFi |

### 连接管理

| API | 说明 |
|-----|------|
| `esp_wifi_connect()` | 连接AP |
| `esp_wifi_disconnect()` | 断开连接 |
| `esp_wifi_set_config()` | 设置配置（v5.5+：连接阶段调用会返回错误） |
| `esp_wifi_get_config()` | 获取配置 |
| `esp_wifi_scan_start()` | 开始扫描 |
| `esp_wifi_scan_get_ap_records()` | 获取扫描结果 |
| `esp_wifi_set_ps()` | 设置省电模式 |

> **v5.5+ 注意事项**：`esp_wifi_set_config()` 在WiFi连接阶段调用会返回错误，需要先断开连接或等待超时。

### 信息获取

| API | 说明 |
|-----|------|
| `esp_wifi_sta_get_ap_info()` | 获取已连接AP信息 |
| `esp_wifi_ap_get_sta_list()` | 获取已连接设备列表 |
| `esp_wifi_get_mac()` | 获取MAC地址 |
| `esp_wifi_set_mac()` | 设置MAC地址 |

### 事件处理

| API | 说明 |
|-----|------|
| `esp_event_handler_register()` | 注册事件处理 |
| `esp_event_handler_unregister()` | 注销事件处理 |
| `esp_event_loop_create_default()` | 创建默认事件循环 |

### 常用宏

```c
WIFI_MODE_NULL                // 空模式
WIFI_MODE_STA                 // STA模式
WIFI_MODE_AP                  // AP模式
WIFI_MODE_APSTA               // AP+STA模式
WIFI_AUTH_OPEN                // 开放认证
WIFI_AUTH_WPA2_PSK            // WPA2-PSK
WIFI_PS_NONE                  // 无省电模式
```

---

## NVS API

### 初始化

| API | 说明 |
|-----|------|
| `nvs_flash_init()` | 初始化NVS |
| `nvs_flash_init_partition()` | 初始化指定分区 |
| `nvs_flash_erase()` | 擦除默认分区 |
| `nvs_flash_erase_partition()` | 擦除指定分区 |

### 句柄管理

| API | 说明 |
|-----|------|
| `nvs_open()` | 打开命名空间 |
| `nvs_close()` | 关闭句柄 |

### 写入操作

| API | 说明 |
|-----|------|
| `nvs_set_i8/i16/i32/i64()` | 写入有符号整数 |
| `nvs_set_u8/u16/u32/u64()` | 写入无符号整数 |
| `nvs_set_str()` | 写入字符串 |
| `nvs_set_blob()` | 写入二进制数据 |
| `nvs_commit()` | 提交更改 |

### 读取操作

| API | 说明 |
|-----|------|
| `nvs_get_i8/i16/i32/i64()` | 读取有符号整数 |
| `nvs_get_u8/u16/u32/u64()` | 读取无符号整数 |
| `nvs_get_str()` | 读取字符串 |
| `nvs_get_blob()` | 读取二进制数据 |

### 管理操作

| API | 说明 |
|-----|------|
| `nvs_erase_key()` | 删除键 |
| `nvs_erase_all()` | 删除所有键 |
| `nvs_entry_find(partition, namespace, type, &it)` | 查找条目（v5.0+：返回esp_err_t，传入&it） |
| `nvs_entry_next(&it)` | 下一个条目（v5.0+：返回esp_err_t，传入&it） |
| `nvs_release_iterator(it)` | 释放迭代器 |
| `nvs_get_stats()` | 获取统计信息 |

### 常用宏

```c
NVS_READONLY                  // 只读模式
NVS_READWRITE                 // 读写模式
NVS_TYPE_I8/U8/I16/U16/I32/U32/I64/U64  // 数据类型
NVS_TYPE_STR                  // 字符串类型
NVS_TYPE_BLOB                 // 二进制类型
NVS_TYPE_ANY                  // 任意类型
```

### v5.0+ 迭代器使用示例

```c
// v5.0+ 新的迭代器API
nvs_iterator_t it = NULL;  // 必须初始化为NULL
esp_err_t res = nvs_entry_find("nvs", "namespace", NVS_TYPE_ANY, &it);

while (res == ESP_OK) {
    nvs_entry_info_t info;
    nvs_entry_info(it, &info);
    ESP_LOGI(TAG, "Key: %s, Type: %d", info.key, info.type);
    res = nvs_entry_next(&it);  // 传入&it
}
nvs_release_iterator(it);
```

---

## OTA API

### OTA操作

| API | 说明 |
|-----|------|
| `esp_https_ota()` | 简化OTA接口 |
| `esp_https_ota_begin()` | 开始OTA |
| `esp_https_ota_perform()` | 执行OTA |
| `esp_https_ota_finish()` | 完成OTA |
| `esp_https_ota_abort()` | 中止OTA |
| `esp_https_ota_get_image_len_read()` | 获取已下载大小 |
| `esp_https_ota_get_image_size()` | 获取固件总大小 |

### 分区操作

| API | 说明 |
|-----|------|
| `esp_ota_get_running_partition()` | 获取当前运行分区 |
| `esp_ota_get_next_update_partition()` | 获取下一个更新分区 |
| `esp_ota_set_boot_partition()` | 设置启动分区 |
| `esp_ota_get_boot_partition()` | 获取启动分区 |

### 回滚操作

| API | 说明 |
|-----|------|
| `esp_ota_mark_app_valid_cancel_rollback()` | 标记有效，取消回滚 |
| `esp_ota_mark_app_invalid_rollback_and_reboot()` | 标记无效，回滚重启 |
| `esp_ota_get_state_partition()` | 获取分区OTA状态 |

---

## 事件循环API

### 事件循环管理

| API | 说明 |
|-----|------|
| `esp_event_loop_create()` | 创建事件循环 |
| `esp_event_loop_create_default()` | 创建默认事件循环 |
| `esp_event_loop_delete()` | 删除事件循环 |
| `esp_event_loop_run()` | 运行事件循环 |

### 事件处理器

| API | 说明 |
|-----|------|
| `esp_event_handler_register()` | 注册处理器（默认循环） |
| `esp_event_handler_register_with()` | 注册处理器（指定循环） |
| `esp_event_handler_unregister()` | 注销处理器 |
| `esp_event_handler_instance_register()` | 注册实例（推荐） |

### 事件发送

| API | 说明 |
|-----|------|
| `esp_event_post()` | 发送事件（默认循环） |
| `esp_event_post_to()` | 发送事件（指定循环） |
| `esp_event_isr_post()` | 从ISR发送事件 |

### 事件组

| API | 说明 |
|-----|------|
| `xEventGroupCreate()` | 创建事件组 |
| `xEventGroupSetBits()` | 设置位 |
| `xEventGroupClearBits()` | 清除位 |
| `xEventGroupWaitBits()` | 等待位 |
| `xEventGroupSync()` | 同步点 |
| `xEventGroupGetBits()` | 获取位值 |
| `xEventGroupSetBitsFromISR()` | ISR中设置位 |

### 常用宏

```c
ESP_EVENT_DECLARE_BASE()      // 声明事件基
ESP_EVENT_DEFINE_BASE()       // 定义事件基
BIT0 ~ BIT31                  // 位掩码
```

---

## 错误码速查

### 通用错误码

| 错误码 | 值 | 说明 |
|--------|-----|------|
| `ESP_OK` | 0 | 成功 |
| `ESP_FAIL` | -1 | 通用失败 |
| `ESP_ERR_NO_MEM` | 0x101 | 内存不足 |
| `ESP_ERR_INVALID_ARG` | 0x102 | 无效参数 |
| `ESP_ERR_INVALID_STATE` | 0x103 | 无效状态 |
| `ESP_ERR_INVALID_SIZE` | 0x104 | 无效大小 |
| `ESP_ERR_NOT_FOUND` | 0x105 | 未找到 |
| `ESP_ERR_NOT_SUPPORTED` | 0x106 | 不支持 |
| `ESP_ERR_TIMEOUT` | 0x107 | 超时 |
| `ESP_ERR_INVALID_RESPONSE` | 0x108 | 无效响应 |
| `ESP_ERR_INVALID_CRC` | 0x109 | CRC错误 |
| `ESP_ERR_INVALID_VERSION` | 0x10A | 版本错误 |
| `ESP_ERR_INVALID_MAC` | 0x10B | MAC地址错误 |

### NVS错误码

| 错误码 | 说明 |
|--------|------|
| `ESP_ERR_NVS_NOT_FOUND` | 键不存在 |
| `ESP_ERR_NVS_NO_FREE_PAGES` | 无空闲页面 |
| `ESP_ERR_NVS_INVALID_NAME` | 无效命名空间 |
| `ESP_ERR_NVS_INVALID_LENGTH` | 长度无效 |
| `ESP_ERR_NVS_READ_ONLY` | 只读模式 |

### WiFi错误码

| 错误码 | 说明 |
|--------|------|
| `ESP_ERR_WIFI_NOT_INIT` | WiFi未初始化 |
| `ESP_ERR_WIFI_NOT_STARTED` | WiFi未启动 |
| `ESP_ERR_WIFI_NOT_STOPPED` | WiFi未停止 |
| `ESP_ERR_WIFI_CONN` | WiFi连接失败 |
| `ESP_ERR_WIFI_SSID` | SSID无效 |

### 转换函数

```c
// 错误码转字符串
const char *esp_err_to_name(esp_err_t code);

// 错误码转描述
const char *esp_err_to_name_r(esp_err_t code, char *buf, size_t buflen);
```

---

## 快速参考：常见任务代码模板

### 1. GPIO初始化模板

```c
gpio_config_t io_conf = {
    .pin_bit_mask = (1ULL << GPIO_NUM_X),
    .mode = GPIO_MODE_OUTPUT,
    .pull_up_en = GPIO_PULLUP_DISABLE,
    .pull_down_en = GPIO_PULLDOWN_DISABLE,
    .intr_type = GPIO_INTR_DISABLE,
};
gpio_config(&io_conf);
```

### 2. 任务创建模板

```c
void task_func(void *pvParameters)
{
    while (1) {
        // 任务代码
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
xTaskCreate(task_func, "task_name", 2048, NULL, 5, NULL);
```

### 3. 队列使用模板

```c
QueueHandle_t queue = xQueueCreate(10, sizeof(int));
int data = 100;
xQueueSend(queue, &data, portMAX_DELAY);
int recv;
xQueueReceive(queue, &recv, portMAX_DELAY);
```

### 4. WiFi STA模板

```c
esp_netif_init();
esp_event_loop_create_default();
esp_netif_create_default_wifi_sta();
wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
esp_wifi_init(&cfg);
wifi_config_t wifi_config = {
    .sta = {.ssid = "SSID", .password = "PASS"},
};
esp_wifi_set_mode(WIFI_MODE_STA);
esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
esp_wifi_start();
esp_wifi_connect();
```

### 5. NVS读写模板

```c
nvs_handle_t handle;
nvs_open("namespace", NVS_READWRITE, &handle);
nvs_set_i32(handle, "key", value);
nvs_commit(handle);
nvs_close(handle);
```
