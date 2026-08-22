# RTOS通信原语详解

## 核心概念

- **队列** - 任务间消息传递
- **信号量** - 同步与计数
- **互斥锁** - 互斥访问保护
- **事件组** - 多条件同步
- **流缓冲** - 字节流传输

---

## 一、队列(Queue)

### 1.1 队列实现

```c
// 环形队列
typedef struct {
    uint8_t *buffer;
    int item_size;
    int max_items;
    int head;
    int tail;
    int count;
    SemaphoreHandle_t mutex;
    SemaphoreHandle_t not_empty;
    SemaphoreHandle_t not_full;
} queue_t;

queue_t *queue_create(int max_items, int item_size) {
    queue_t *q = pvPortMalloc(sizeof(queue_t));
    q->buffer = pvPortMalloc(max_items * item_size);
    q->item_size = item_size;
    q->max_items = max_items;
    q->head = 0;
    q->tail = 0;
    q->count = 0;
    q->mutex = xSemaphoreCreateMutex();
    q->not_empty = xSemaphoreCreateCounting(max_items, 0);
    q->not_full = xSemaphoreCreateCounting(max_items, max_items);
    return q;
}

int queue_send(queue_t *q, const void *item, uint32_t timeout_ms) {
    if (xSemaphoreTake(q->not_full, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) {
        return -1;  // 满
    }
    xSemaphoreTake(q->mutex, portMAX_DELAY);

    memcpy(q->buffer + q->tail * q->item_size, item, q->item_size);
    q->tail = (q->tail + 1) % q->max_items;
    q->count++;

    xSemaphoreGive(q->mutex);
    xSemaphoreGive(q->not_empty);
    return 0;
}

int queue_receive(queue_t *q, void *item, uint32_t timeout_ms) {
    if (xSemaphoreTake(q->not_empty, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) {
        return -1;  // 空
    }
    xSemaphoreTake(q->mutex, portMAX_DELAY);

    memcpy(item, q->buffer + q->head * q->item_size, q->item_size);
    q->head = (q->head + 1) % q->max_items;
    q->count--;

    xSemaphoreGive(q->mutex);
    xSemaphoreGive(q->not_full);
    return 0;
}
```

---

### 1.2 队列应用模式

```c
// 生产者-消费者模式
typedef struct {
    uint32_t timestamp;
    float temperature;
    float humidity;
    uint8_t sensor_id;
} sensor_data_t;

QueueHandle_t sensor_queue;

void sensor_task(void *param) {
    sensor_data_t data;
    while (1) {
        data.temperature = read_temperature();
        data.humidity = read_humidity();
        data.timestamp = get_tick();

        xQueueSend(sensor_queue, &data, portMAX_DELAY);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void process_task(void *param) {
    sensor_data_t data;
    while (1) {
        if (xQueueReceive(sensor_queue, &data, pdMS_TO_TICKS(5000)) == pdTRUE) {
            printf("T=%.1f H=%.1f\n", data.temperature, data.humidity);
        }
    }
}

// 命令队列
typedef enum {
    CMD_LED_ON,
    CMD_LED_OFF,
    CMD_SET_PID,
    CMD_RESET,
} command_type_t;

typedef struct {
    command_type_t type;
    union {
        struct { float kp, ki, kd; } pid;
        uint32_t value;
    } params;
} command_t;

QueueHandle_t cmd_queue;

void cmd_handler_task(void *param) {
    command_t cmd;
    while (1) {
        if (xQueueReceive(cmd_queue, &cmd, portMAX_DELAY) == pdTRUE) {
            switch (cmd.type) {
                case CMD_LED_ON:
                    gpio_set_level(LED_PIN, 1);
                    break;
                case CMD_LED_OFF:
                    gpio_set_level(LED_PIN, 0);
                    break;
                case CMD_SET_PID:
                    pid_set_params(cmd.params.pid.kp,
                                   cmd.params.pid.ki,
                                   cmd.params.pid.kd);
                    break;
                case CMD_RESET:
                    esp_restart();
                    break;
            }
        }
    }
}
```

---

## 二、信号量(Semaphore)

### 2.1 二值信号量

```c
// 二值信号量用于同步
SemaphoreHandle_t sync_sem;

void producer_task(void *param) {
    while (1) {
        // 生产数据
        process_data();

        // 通知消费者
        xSemaphoreGive(sync_sem);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void consumer_task(void *param) {
    while (1) {
        // 等待通知
        if (xSemaphoreTake(sync_sem, portMAX_DELAY) == pdTRUE) {
            // 处理数据
            handle_data();
        }
    }
}
```

---

### 2.2 计数信号量

```c
// 计数信号量用于资源管理
SemaphoreHandle_t resource_pool;

#define POOL_SIZE 5

void init_resource_pool(void) {
    resource_pool = xSemaphoreCreateCounting(POOL_SIZE, POOL_SIZE);
}

void use_resource(int id) {
    // 获取资源
    if (xSemaphoreTake(resource_pool, pdMS_TO_TICKS(1000)) == pdTRUE) {
        printf("Task %d acquired resource\n", id);

        // 使用资源
        vTaskDelay(pdMS_TO_TICKS(500));

        // 释放资源
        xSemaphoreGive(resource_pool);
        printf("Task %d released resource\n", id);
    } else {
        printf("Task %d: no resource available\n", id);
    }
}

void resource_user_task(void *param) {
    int id = (int)param;
    while (1) {
        use_resource(id);
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}
```

---

## 三、互斥锁(Mutex)

### 3.1 互斥锁实现

```c
// 互斥锁保护共享资源
SemaphoreHandle_t i2c_mutex;

void i2c_read_safe(uint8_t addr, uint8_t reg, uint8_t *data, int len) {
    xSemaphoreTake(i2c_mutex, portMAX_DELAY);

    i2c_cmd_handle_t cmd = i2c_cmd_link_create();
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(cmd, &reg, 1, true);
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1) | I2C_MASTER_READ, true);
    i2c_master_read(cmd, data, len, I2C_MASTER_LAST_NACK);
    i2c_master_stop(cmd);
    i2c_master_cmd_begin(I2C_NUM_0, cmd, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(cmd);

    xSemaphoreGive(i2c_mutex);
}

// 多传感器共用I2C
void temp_sensor_task(void *param) {
    while (1) {
        uint8_t data[2];
        i2c_read_safe(0x48, 0x00, data, 2);
        int16_t raw = (data[0] << 8) | data[1];
        float temp = raw / 256.0f;
        printf("Temp: %.1f\n", temp);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void humidity_sensor_task(void *param) {
    while (1) {
        uint8_t data[2];
        i2c_read_safe(0x40, 0x01, data, 2);
        float humidity = ((data[0] << 8) | data[1]) * 100.0f / 65536.0f;
        printf("Humidity: %.1f\n", humidity);
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
```

---

### 3.2 递归互斥锁

```c
// 递归互斥锁(同一线程可多次获取)
SemaphoreHandle_t recursive_mutex;

void init_recursive_mutex(void) {
    recursive_mutex = xSemaphoreCreateRecursiveMutex();
}

void function_a(void) {
    xSemaphoreTakeRecursive(recursive_mutex, portMAX_DELAY);
    printf("Function A\n");
    function_b();  // 可以再次获取
    xSemaphoreGiveRecursive(recursive_mutex);
}

void function_b(void) {
    xSemaphoreTakeRecursive(recursive_mutex, portMAX_DELAY);
    printf("Function B\n");
    xSemaphoreGiveRecursive(recursive_mutex);
}
```

---

## 四、事件组(Event Group)

### 4.1 事件组同步

```c
// 事件位定义
#define EVT_WIFI_CONNECTED  (1 << 0)
#define EVT_MQTT_CONNECTED  (1 << 1)
#define EVT_SENSOR_READY    (1 << 2)
#define EVT_TIME_SYNCED     (1 << 3)

EventHandle_t event_group;

void wifi_task(void *param) {
    while (1) {
        if (wifi_connect() == WIFI_CONNECTED) {
            xEventGroupSetBits(event_group, EVT_WIFI_CONNECTED);
        }
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void mqtt_task(void *param) {
    // 等待WiFi连接
    xEventGroupWaitBits(event_group, EVT_WIFI_CONNECTED,
                        pdTRUE, pdTRUE, portMAX_DELAY);

    if (mqtt_connect() == MQTT_CONNECTED) {
        xEventGroupSetBits(event_group, EVT_MQTT_CONNECTED);
    }
    vTaskDelete(NULL);
}

void main_task(void *param) {
    // 等待所有条件满足
    EventBits_t bits = xEventGroupWaitBits(
        event_group,
        EVT_WIFI_CONNECTED | EVT_MQTT_CONNECTED | EVT_SENSOR_READY,
        pdTRUE,   // 清除位
        pdTRUE,   // 等待所有位
        pdMS_TO_TICKS(30000)
    );

    if ((bits & (EVT_WIFI_CONNECTED | EVT_MQTT_CONNECTED | EVT_SENSOR_READY))
        == (EVT_WIFI_CONNECTED | EVT_MQTT_CONNECTED | EVT_SENSOR_READY)) {
        printf("System ready!\n");
        start_normal_operation();
    } else {
        printf("Timeout waiting for initialization\n");
    }
}
```

---

### 4.2 事件组用于状态机

```c
// 状态机事件驱动
typedef enum {
    STATE_IDLE,
    STATE_RUNNING,
    STATE_PAUSED,
    STATE_ERROR,
} system_state_t;

EventHandle_t state_events;
#define EVT_START   (1 << 0)
#define EVT_STOP    (1 << 1)
#define EVT_PAUSE   (1 << 2)
#define EVT_RESUME  (1 << 3)
#define EVT_ERROR   (1 << 4)

system_state_t current_state = STATE_IDLE;

void state_machine_task(void *param) {
    while (1) {
        EventBits_t events = xEventGroupWaitBits(
            state_events,
            EVT_START | EVT_STOP | EVT_PAUSE | EVT_RESUME | EVT_ERROR,
            pdTRUE, pdFALSE, portMAX_DELAY);

        switch (current_state) {
            case STATE_IDLE:
                if (events & EVT_START) {
                    current_state = STATE_RUNNING;
                    start_operation();
                }
                break;
            case STATE_RUNNING:
                if (events & EVT_STOP) {
                    current_state = STATE_IDLE;
                    stop_operation();
                } else if (events & EVT_PAUSE) {
                    current_state = STATE_PAUSED;
                    pause_operation();
                } else if (events & EVT_ERROR) {
                    current_state = STATE_ERROR;
                    handle_error();
                }
                break;
            case STATE_PAUSED:
                if (events & EVT_RESUME) {
                    current_state = STATE_RUNNING;
                    resume_operation();
                } else if (events & EVT_STOP) {
                    current_state = STATE_IDLE;
                    stop_operation();
                }
                break;
            case STATE_ERROR:
                if (events & EVT_STOP) {
                    current_state = STATE_IDLE;
                    clear_error();
                }
                break;
        }
    }
}
```

---

## 五、流缓冲(Stream Buffer)

### 5.1 流缓冲实现

```c
// 字节流缓冲(用于UART等)
typedef struct {
    uint8_t *buffer;
    int size;
    int head;
    int tail;
    int count;
    SemaphoreHandle_t mutex;
    SemaphoreHandle_t data_available;
} stream_buffer_t;

stream_buffer_t *stream_create(int size) {
    stream_buffer_t *sb = pvPortMalloc(sizeof(stream_buffer_t));
    sb->buffer = pvPortMalloc(size);
    sb->size = size;
    sb->head = 0;
    sb->tail = 0;
    sb->count = 0;
    sb->mutex = xSemaphoreCreateMutex();
    sb->data_available = xSemaphoreCreateCounting(size, 0);
    return sb;
}

int stream_write(stream_buffer_t *sb, const uint8_t *data, int len) {
    xSemaphoreTake(sb->mutex, portMAX_DELAY);

    int written = 0;
    for (int i = 0; i < len && sb->count < sb->size; i++) {
        sb->buffer[sb->tail] = data[i];
        sb->tail = (sb->tail + 1) % sb->size;
        sb->count++;
        written++;
        xSemaphoreGive(sb->data_available);
    }

    xSemaphoreGive(sb->mutex);
    return written;
}

int stream_read(stream_buffer_t *sb, uint8_t *data, int max_len,
                uint32_t timeout_ms) {
    // 等待数据
    if (xSemaphoreTake(sb->data_available, pdMS_TO_TICKS(timeout_ms)) != pdTRUE) {
        return 0;
    }
    xSemaphoreTake(sb->mutex, portMAX_DELAY);

    int read = 0;
    for (int i = 0; i < max_len && sb->count > 0; i++) {
        data[i] = sb->buffer[sb->head];
        sb->head = (sb->head + 1) % sb->size;
        sb->count--;
        read++;
    }

    xSemaphoreGive(sb->mutex);
    return read;
}
```

---

### 5.2 UART流缓冲

```c
// UART接收流缓冲
stream_buffer_t *uart_rx_stream;

void uart_rx_isr(void *arg) {
    uint8_t data[128];
    int len = uart_read_bytes(UART_NUM_0, data, sizeof(data), 0);

    if (len > 0) {
        // 从中断发送到流缓冲
        xStreamBufferSendFromISR(uart_rx_stream, data, len, NULL);
    }
}

void uart_process_task(void *param) {
    uint8_t buf[256];
    while (1) {
        int len = stream_read(uart_rx_stream, buf, sizeof(buf),
                              pdMS_TO_TICKS(100));
        if (len > 0) {
            process_uart_data(buf, len);
        }
    }
}
```

---

## 六、任务通知(Task Notification)

### 6.1 轻量级同步

```c
// 任务通知替代信号量(更快)
TaskHandle_t notify_target;

void notifier_task(void *param) {
    while (1) {
        // 处理事件
        process_event();

        // 通知目标任务
        xTaskNotifyGive(notify_target);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void waiting_task(void *param) {
    while (1) {
        // 等待通知
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

        // 处理通知
        handle_notification();
    }
}

// 带值通知
void send_value_notification(TaskHandle_t task, uint32_t value) {
    xTaskNotify(task, value, eSetValueWithOverwrite);
}

uint32_t receive_value_notification(TaskHandle_t task) {
    uint32_t value;
    xTaskNotifyWait(0, 0xFFFFFFFF, &value, portMAX_DELAY);
    return value;
}
```

---

## 附录：通信原语对比

| 原语 | 用途 | 阻塞 | ISR安全 | 性能 |
|------|------|------|---------|------|
| 队列 | 消息传递 | 是 | 是 | 中 |
| 二值信号量 | 同步 | 是 | 是 | 高 |
| 计数信号量 | 资源计数 | 是 | 是 | 高 |
| 互斥锁 | 互斥访问 | 是 | 否 | 中 |
| 事件组 | 多条件同步 | 是 | 是 | 高 |
| 流缓冲 | 字节流 | 是 | 是 | 高 |
| 任务通知 | 轻量同步 | 是 | 是 | 最高 |

---

## 相关链接

- [[FreeRTOS基础]] - FreeRTOS基础
- [[FreeRTOS进阶]] - FreeRTOS进阶
- [[RTOS调度算法]] - 调度算法
- [[数据结构与算法]] - 队列数据结构
