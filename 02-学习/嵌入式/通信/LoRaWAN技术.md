# LoRaWAN技术

## 核心概念

- **LoRa** - 远距离低功耗无线
- **LoRaWAN** - LoRa网络协议
- **ADR** - 自适应数据速率
- **Class A/B/C** - 设备工作模式

---

## 一、LoRa基础

### 1.1 LoRa参数

```c
// LoRa调制参数
typedef struct {
    uint32_t frequency;     // 频率(Hz)
    uint8_t spreading_factor; // 扩频因子(7-12)
    uint8_t bandwidth;       // 带宽(125/250/500 kHz)
    uint8_t coding_rate;     // 编码率(4/5, 4/6, 4/7, 4/8)
    int8_t tx_power;         // 发射功率(dBm)
} lora_config_t;

// 数据速率和距离
/*
 * SF7:  5.47kbps, 2km
 * SF8:  3.13kbps, 4km
 * SF9:  1.76kbps, 6km
 * SF10: 0.98kbps, 8km
 * SF11: 0.54kbps, 11km
 * SF12: 0.29kbps, 14km
 */

// 传输时间计算
float calc_airtime(lora_config_t *cfg, int payload_len) {
    // 符号时间
    float ts = (1 << cfg->spreading_factor) / (cfg->bandwidth * 1000.0f);

    // 前导码时间(8符号)
    float tpreamble = 8 * ts;

    // 负载符号数
    int de = (cfg->spreading_factor >= 11) ? 1 : 0;
    int cr = cfg->coding_rate - 4;
    int payload_sym_nb = 8 + (int)ceilf((8.0f * payload_len - 4 * cfg->spreading_factor + 28 + 16) /
                                         (4 * (cfg->spreading_factor - 2 * de))) * (cr + 4);

    return tpreamble + payload_sym_nb * ts;
}
```

---

### 1.2 SX1276驱动

```c
// SX1276寄存器
#define REG_FIFO 0x00
#define REG_OP_MODE 0x01
#define REG_FRF_MSB 0x06
#define REG_FRF_MID 0x07
#define REG_FRF_LSB 0x08
#define REG_PA_CONFIG 0x09
#define REG_MODEM_CONFIG1 0x1D
#define REG_MODEM_CONFIG2 0x1E
#define REG_PREAMBLE_MSB 0x20
#define REG_PREAMBLE_LSB 0x21
#define REG_PAYLOAD_LENGTH 0x22

void sx1276_init(lora_config_t *cfg) {
    // 进入LoRa模式
    spi_write_reg(REG_OP_MODE, 0x80);  // LoRa + Sleep
    vTaskDelay(pdMS_TO_TICKS(10));

    // 设置频率
    uint32_t frf = (uint32_t)((uint64_t)cfg->frequency << 2) / 15625;
    spi_write_reg(REG_FRF_MSB, (frf >> 16) & 0xFF);
    spi_write_reg(REG_FRF_MID, (frf >> 8) & 0xFF);
    spi_write_reg(REG_FRF_LSB, frf & 0xFF);

    // 配置调制参数
    uint8_t bw = (cfg->bandwidth == 125) ? 0x70 : (cfg->bandwidth == 250) ? 0x80 : 0x90;
    uint8_t cr = (cfg->coding_rate - 4) << 1;
    spi_write_reg(REG_MODEM_CONFIG1, bw | cr | 0x02);  // 显式头+CR

    uint8_t sf = cfg->spreading_factor << 4;
    spi_write_reg(REG_MODEM_CONFIG2, sf | 0x04);  // SF + CRC

    // 设置发射功率
    spi_write_reg(REG_PA_CONFIG, 0x80 | (cfg->tx_power - 2));  // PA_BOOST

    // 进入待机模式
    spi_write_reg(REG_OP_MODE, 0x81);  // LoRa + Standby
}

void sx1276_send(uint8_t *data, int len) {
    // 设置FIFO地址
    spi_write_reg(0x0E, 0x00);  // FIFO TX基地址
    spi_write_reg(0x0D, 0x00);  // FIFO地址指针

    // 写入数据
    for (int i = 0; i < len; i++) {
        spi_write_reg(REG_FIFO, data[i]);
    }

    // 设置负载长度
    spi_write_reg(REG_PAYLOAD_LENGTH, len);

    // 开始发送
    spi_write_reg(REG_OP_MODE, 0x83);  // LoRa + TX

    // 等待发送完成
    while (!(spi_read_reg(0x12) & 0x08));  // TxDone
    spi_write_reg(0x12, 0xFF);  // 清除中断
}
```

---

## 二、LoRaWAN协议

### 2.1 帧格式

```c
// LoRaWAN帧结构
/*
 * MHDR | FHDR | FPort | FRMPayload | MIC
 *
 * MHDR: 消息头(1字节)
 *   - MType: 消息类型(3位)
 *   - RFU: 保留(3位)
 *   - Major: 协议版本(2位)
 *
 * FHDR: 帧头(7字节)
 *   - DevAddr: 设备地址(4字节)
 *   - FCtrl: 帧控制(1字节)
 *   - FCnt: 帧计数(2字节)
 *
 * FPort: 端口(0或1字节)
 * FRMPayload: 负载(加密)
 * MIC: 完整性校验(4字节)
 */

typedef struct {
    uint8_t mhdr;
    uint32_t dev_addr;
    uint8_t f_ctrl;
    uint16_t f_cnt;
    uint8_t f_port;
    uint8_t payload[256];
    uint8_t payload_len;
    uint8_t mic[4];
} lorawan_frame_t;

// 消息类型
#define MTYPE_JOIN_REQUEST   0x00
#define MTYPE_JOIN_ACCEPT    0x20
#define MTYPE_UNCONFIRMED_UP 0x40
#define MTYPE_UNCONFIRMED_DOWN 0x60
#define MTYPE_CONFIRMED_UP   0x80
#define MTYPE_CONFIRMED_DOWN 0xA0
```

---

### 2.2 OTAA入网

```c
// OTAA(空中激活)入网
typedef struct {
    uint8_t dev_eui[8];    // 设备EUI
    uint8_t app_eui[8];    // 应用EUI
    uint8_t app_key[16];   // 应用密钥
} otaa_config_t;

void lorawan_join(otaa_config_t *cfg) {
    // 构建Join Request
    uint8_t join_req[23];
    join_req[0] = MTYPE_JOIN_REQUEST;  // MHDR

    // AppEUI(小端)
    for (int i = 0; i < 8; i++) join_req[1 + i] = cfg->app_eui[7 - i];

    // DevEUI(小端)
    for (int i = 0; i < 8; i++) join_req[9 + i] = cfg->dev_eui[7 - i];

    // DevNonce(随机)
    uint16_t dev_nonce = random_uint16();
    join_req[17] = dev_nonce & 0xFF;
    join_req[18] = (dev_nonce >> 8) & 0xFF;

    // 计算MIC
    uint8_t mic[4];
    aes_cmac(cfg->app_key, join_req, 19, mic);
    memcpy(&join_req[19], mic, 4);

    // 发送
    sx1276_send(join_req, 23);

    // 等待Join Accept
    uint8_t accept[64];
    int len = sx1276_receive(accept, sizeof(accept), 10000);

    if (len > 0 && (accept[0] & 0xE0) == MTYPE_JOIN_ACCEPT) {
        // 解密Join Accept
        uint8_t key[16];
        lorawan_derive_keys(cfg->app_key, dev_nonce, key);

        // 解析AppSKey, NwkSKey
        // ...
    }
}
```

---

### 2.3 数据收发

```c
// 上行数据发送
void lorawan_send(uint8_t port, uint8_t *data, uint8_t len, bool confirmed) {
    lorawan_frame_t frame;
    frame.mhdr = confirmed ? MTYPE_CONFIRMED_UP : MTYPE_UNCONFIRMED_UP;
    frame.dev_addr = device_address;
    frame.f_ctrl = 0x00;  // 无自适应，无确认请求
    frame.f_cnt = uplink_counter++;
    frame.f_port = port;
    memcpy(frame.payload, data, len);
    frame.payload_len = len;

    // 加密负载
    lorawan_encrypt(frame.payload, frame.payload_len, app_s_key,
                    frame.dev_addr, 0, frame.f_cnt);

    // 计算MIC
    lorawan_compute_mic(&frame, nwk_s_key);

    // 构建完整帧
    uint8_t buffer[256];
    int total_len = lorawan_serialize(&frame, buffer);

    // 发送(使用RX1窗口接收确认)
    sx1276_send(buffer, total_len);

    // 等待RX1窗口
    vTaskDelay(pdMS_TO_TICKS(1000));

    // 接收下行
    uint8_t rx[64];
    int rx_len = sx1276_receive(rx, sizeof(rx), 100);
    if (rx_len > 0) {
        lorawan_process_downlink(rx, rx_len);
    }
}
```

---

## 三、设备类别

### 3.1 Class A

```c
// Class A: 双向通信，发送后开接收窗口
/*
 * 特点:
 * - 最低功耗
 * - 发送后开两个接收窗口(RX1, RX2)
 * - 下行只能在接收窗口到达
 *
 * 时序:
 * TX → RX1(1s) → RX2(2s)
 */

void class_a_send_receive(uint8_t *data, int len) {
    // 发送上行
    sx1276_send(data, len);

    // RX1窗口(1秒后)
    vTaskDelay(pdMS_TO_TICKS(1000));
    uint8_t rx[64];
    int rx_len = sx1276_receive(rx, sizeof(rx), 50);

    if (rx_len == 0) {
        // RX2窗口(2秒后)
        vTaskDelay(pdMS_TO_TICKS(1000));
        rx_len = sx1276_receive(rx, sizeof(rx), 50);
    }

    if (rx_len > 0) {
        process_downlink(rx, rx_len);
    }
}
```

---

### 3.2 Class C

```c
// Class C: 持续接收
/*
 * 特点:
 * - 最高功耗
 * - 除发送外持续监听
 * - 最低延迟下行
 */

void class_c_init(void) {
    // 配置为连续接收模式
    sx1276_set_rx_continuous();

    // 创建接收任务
    xTaskCreate(class_c_rx_task, "RX", 1024, NULL, 2, NULL);
}

void class_c_rx_task(void *param) {
    uint8_t rx[64];
    while (1) {
        int len = sx1276_receive(rx, sizeof(rx), 1000);
        if (len > 0) {
            process_downlink(rx, len);
        }
    }
}
```

---

## 四、ADR自适应

### 4.1 ADR算法

```c
// ADR(自适应数据速率)
typedef struct {
    int8_t current_dr;     // 当前数据速率
    int8_t current_power;  // 当前发射功率
    int8_t snr_history[20]; // SNR历史
    int snr_index;
    uint16_t ack_fail_count;
} adr_state_t;

void adr_update(adr_state_t *adr, int8_t snr) {
    adr->snr_history[adr->snr_index] = snr;
    adr->snr_index = (adr->snr_index + 1) % 20;

    // 计算所需SNR边际
    int8_t required_snr = -20 + (12 - adr->current_dr) * 3;  // 简化
    int8_t max_snr = -128;
    for (int i = 0; i < 20; i++) {
        if (adr->snr_history[i] > max_snr) max_snr = adr->snr_history[i];
    }

    int8_t margin = max_snr - required_snr - 10;  // 10dB边际

    if (margin > 0 && adr->current_dr < 5) {
        // 可以提高数据速率
        adr->current_dr++;
    } else if (margin < -10 && adr->current_dr > 0) {
        // 需要降低数据速率
        adr->current_dr--;
    }

    // 调整发射功率
    if (margin > 15 && adr->current_power > 2) {
        adr->current_power -= 3;
    } else if (margin < -5 && adr->current_power < 14) {
        adr->current_power += 3;
    }
}
```

---

## 五、功耗优化

### 5.1 低功耗模式

```c
// LoRa低功耗配置
void lora_low_power(void) {
    // 进入睡眠模式
    spi_write_reg(REG_OP_MODE, 0x00);  // Sleep模式

    // 关闭TCXO(温补晶振)
    gpio_set_level(TCXO_EN_PIN, 0);
}

// 唤醒
void lora_wakeup(void) {
    // 启用TCXO
    gpio_set_level(TCXO_EN_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(5));

    // 进入待机模式
    spi_write_reg(REG_OP_MODE, 0x81);  // Standby模式
}

// 电池寿命计算
float calc_battery_life(float battery_mah, float tx_interval_sec,
                         float tx_current_ma, float sleep_current_ua) {
    float tx_time_sec = 0.1f;  // 发送时间约100ms
    float rx_time_sec = 0.05f; // 接收时间约50ms

    float duty = (tx_time_sec + rx_time_sec) / tx_interval_sec;
    float avg_current = tx_current_ma * duty + sleep_current_ua / 1000.0f;

    return battery_mah / avg_current / 24;  // 天
}
```

---

## 附录：LoRaWAN频段

| 区域 | 频段 | 说明 |
|------|------|------|
| 欧洲 | 868MHz | EU868 |
| 北美 | 915MHz | US915 |
| 中国 | 470MHz | CN470 |
| 亚洲 | 923MHz | AS923 |

---

## 相关链接

- [[无线通信技术]] - 无线通信
- [[物联网协议]] - 物联网协议
- [[功耗优化进阶]] - 低功耗设计
