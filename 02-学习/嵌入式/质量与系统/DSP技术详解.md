# DSP技术详解

## 核心概念

- **DSP** - 数字信号处理
- **滤波器** - 信号滤波
- **FFT** - 快速傅里叶变换
- **自适应滤波** - 自动调整参数

---

## 一、DSP基础

### 1.1 信号表示

```c
// 离散信号
typedef struct {
    float *samples;
    int length;
    float sample_rate;
} signal_t;

// 信号生成
void generate_sine(signal_t *sig, float freq, float amplitude, float phase) {
    for (int i = 0; i < sig->length; i++) {
        float t = (float)i / sig->sample_rate;
        sig->samples[i] = amplitude * sinf(2 * M_PI * freq * t + phase);
    }
}

// 信号叠加
void signal_add(signal_t *out, signal_t *a, signal_t *b) {
    for (int i = 0; i < out->length; i++) {
        out->samples[i] = a->samples[i] + b->samples[i];
    }
}
```

---

### 1.2 频谱分析

```c
// 功率谱密度
void power_spectrum(float *signal, int N, float *psd) {
    float real[N], imag[N];

    // FFT
    fft(signal, real, imag, N);

    // 计算功率谱
    for (int i = 0; i < N; i++) {
        psd[i] = (real[i] * real[i] + imag[i] * imag[i]) / N;
    }
}

// 频谱特征提取
typedef struct {
    float dominant_freq;
    float spectral_centroid;
    float bandwidth;
    float power;
} spectral_features_t;

spectral_features_t extract_features(float *psd, int N, float sample_rate) {
    spectral_features_t feat = {0};
    float total_power = 0;
    float weighted_sum = 0;

    for (int i = 0; i < N/2; i++) {
        float freq = (float)i * sample_rate / N;
        total_power += psd[i];
        weighted_sum += freq * psd[i];

        if (psd[i] > psd[(int)feat.dominant_freq]) {
            feat.dominant_freq = i;
        }
    }

    feat.dominant_freq = feat.dominant_freq * sample_rate / N;
    feat.spectral_centroid = weighted_sum / total_power;
    feat.power = total_power;

    return feat;
}
```

---

## 二、数字滤波器

### 2.1 FIR滤波器

```c
// FIR滤波器
typedef struct {
    float *coeffs;
    float *buffer;
    int order;
    int index;
} fir_filter_t;

void fir_init(fir_filter_t *fir, float *coeffs, int order) {
    fir->coeffs = coeffs;
    fir->order = order;
    fir->buffer = calloc(order + 1, sizeof(float));
    fir->index = 0;
}

float fir_filter(fir_filter_t *fir, float input) {
    // 存入缓冲区
    fir->buffer[fir->index] = input;

    // 卷积
    float output = 0;
    int idx = fir->index;
    for (int i = 0; i <= fir->order; i++) {
        output += fir->coeffs[i] * fir->buffer[idx];
        idx = (idx - 1 + fir->order + 1) % (fir->order + 1);
    }

    // 更新索引
    fir->index = (fir->index + 1) % (fir->order + 1);

    return output;
}

// FIR系数设计(窗函数法)
void design_lowpass_fir(float *coeffs, int order, float cutoff, float sample_rate) {
    float fc = cutoff / sample_rate;

    for (int i = 0; i <= order; i++) {
        int n = i - order / 2;
        if (n == 0) {
            coeffs[i] = 2 * fc;
        } else {
            coeffs[i] = sinf(2 * M_PI * fc * n) / (M_PI * n);
        }

        // Hamming窗
        float w = 0.54f - 0.46f * cosf(2 * M_PI * i / order);
        coeffs[i] *= w;
    }
}
```

---

### 2.2 IIR滤波器

```c
// IIR滤波器(直接II型)
typedef struct {
    float *a;  // 分母系数
    float *b;  // 分子系数
    float *w;  // 状态缓冲区
    int order;
} iir_filter_t;

void iir_init(iir_filter_t *iir, float *a, float *b, int order) {
    iir->a = a;
    iir->b = b;
    iir->order = order;
    iir->w = calloc(order + 1, sizeof(float));
}

float iir_filter(iir_filter_t *iir, float input) {
    // 计算新状态
    iir->w[0] = input;
    for (int i = 1; i <= iir->order; i++) {
        iir->w[0] -= iir->a[i] * iir->w[i];
    }

    // 计算输出
    float output = 0;
    for (int i = 0; i <= iir->order; i++) {
        output += iir->b[i] * iir->w[i];
    }

    // 更新状态
    for (int i = iir->order; i > 0; i--) {
        iir->w[i] = iir->w[i - 1];
    }

    return output;
}

// Butterworth低通滤波器系数
void design_butterworth_lowpass(float *a, float *b, int order,
                                 float cutoff, float sample_rate) {
    float wc = tanf(M_PI * cutoff / sample_rate);
    float wc2 = wc * wc;

    // 二阶Butterworth段
    if (order == 2) {
        float norm = 1 + sqrtf(2) * wc + wc2;
        b[0] = wc2 / norm;
        b[1] = 2 * wc2 / norm;
        b[2] = wc2 / norm;
        a[0] = 1;
        a[1] = 2 * (wc2 - 1) / norm;
        a[2] = (1 - sqrtf(2) * wc + wc2) / norm;
    }
}
```

---

## 三、FFT实现

### 3.1 基2 FFT

```c
// 基2 FFT(蝶形运算)
void fft_rad2(float *real, float *imag, int N) {
    // 位反转排列
    int bits = 0;
    int temp = N;
    while (temp >>= 1) bits++;

    for (int i = 0; i < N; i++) {
        int j = bit_reverse(i, bits);
        if (i < j) {
            float temp_r = real[i];
            float temp_i = imag[i];
            real[i] = real[j];
            imag[i] = imag[j];
            real[j] = temp_r;
            imag[j] = temp_i;
        }
    }

    // 蝶形运算
    for (int stage = 1; stage <= bits; stage++) {
        int m = 1 << stage;
        int half_m = m / 2;

        float w_r = 1, w_i = 0;
        float wm_r = cosf(M_PI / half_m);
        float wm_i = -sinf(M_PI / half_m);

        for (int k = 0; k < half_m; k++) {
            for (int j = k; j < N; j += m) {
                int idx = j + half_m;
                float t_r = w_r * real[idx] - w_i * imag[idx];
                float t_i = w_r * imag[idx] + w_i * real[idx];

                real[idx] = real[j] - t_r;
                imag[idx] = imag[j] - t_i;
                real[j] += t_r;
                imag[j] += t_i;
            }

            float new_w_r = w_r * wm_r - w_i * wm_i;
            w_i = w_r * wm_i + w_i * wm_r;
            w_r = new_w_r;
        }
    }
}

// 位反转
int bit_reverse(int x, int bits) {
    int result = 0;
    for (int i = 0; i < bits; i++) {
        result = (result << 1) | (x & 1);
        x >>= 1;
    }
    return result;
}
```

---

## 四、自适应滤波

### 4.1 LMS算法

```c
// LMS自适应滤波器
typedef struct {
    float *weights;
    float *buffer;
    int order;
    float mu;  // 步长
} lms_filter_t;

void lms_init(lms_filter_t *lms, int order, float mu) {
    lms->order = order;
    lms->mu = mu;
    lms->weights = calloc(order, sizeof(float));
    lms->buffer = calloc(order, sizeof(float));
}

float lms_filter(lms_filter_t *lms, float input, float desired) {
    // 移入新样本
    for (int i = lms->order - 1; i > 0; i--) {
        lms->buffer[i] = lms->buffer[i - 1];
    }
    lms->buffer[0] = input;

    // 计算输出
    float output = 0;
    for (int i = 0; i < lms->order; i++) {
        output += lms->weights[i] * lms->buffer[i];
    }

    // 计算误差
    float error = desired - output;

    // 更新权重
    for (int i = 0; i < lms->order; i++) {
        lms->weights[i] += 2 * lms->mu * error * lms->buffer[i];
    }

    return output;
}

// 归一化LMS(NLMS)
float nlms_filter(lms_filter_t *lms, float input, float desired) {
    // 移入新样本
    for (int i = lms->order - 1; i > 0; i--) {
        lms->buffer[i] = lms->buffer[i - 1];
    }
    lms->buffer[0] = input;

    // 计算输出
    float output = 0;
    float norm = 0;
    for (int i = 0; i < lms->order; i++) {
        output += lms->weights[i] * lms->buffer[i];
        norm += lms->buffer[i] * lms->buffer[i];
    }

    // 计算误差
    float error = desired - output;

    // 更新权重(归一化)
    float step = lms->mu / (norm + 1e-10f);
    for (int i = 0; i < lms->order; i++) {
        lms->weights[i] += step * error * lms->buffer[i];
    }

    return output;
}
```

---

## 五、语音处理

### 5.1 MFCC特征

```c
// MFCC提取
typedef struct {
    float mfcc[13];
    float delta[13];
    float delta2[13];
} mfcc_features_t;

void extract_mfcc(float *audio, int sample_rate, int frame_size,
                  mfcc_features_t *feat) {
    // 1. 预加重
    float pre_emphasis = 0.97f;
    for (int i = frame_size - 1; i > 0; i--) {
        audio[i] -= pre_emphasis * audio[i - 1];
    }

    // 2. 分帧加窗
    float windowed[frame_size];
    for (int i = 0; i < frame_size; i++) {
        float w = 0.54f - 0.46f * cosf(2 * M_PI * i / (frame_size - 1));
        windowed[i] = audio[i] * w;
    }

    // 3. FFT
    float real[frame_size], imag[frame_size];
    memcpy(real, windowed, sizeof(float) * frame_size);
    memset(imag, 0, sizeof(float) * frame_size);
    fft_rad2(real, imag, frame_size);

    // 4. 功率谱
    float power[frame_size / 2 + 1];
    for (int i = 0; i <= frame_size / 2; i++) {
        power[i] = (real[i] * real[i] + imag[i] * imag[i]) / frame_size;
    }

    // 5. 梅尔滤波器组
    float mel_energies[26];
    mel_filterbank(power, mel_energies, 26, sample_rate, frame_size);

    // 6. DCT
    for (int i = 0; i < 13; i++) {
        float sum = 0;
        for (int j = 0; j < 26; j++) {
            sum += logf(mel_energies[j] + 1e-10f) *
                   cosf(M_PI * i * (j + 0.5f) / 26.0f);
        }
        feat->mfcc[i] = sum;
    }
}
```

---

## 附录：DSP库

| 库 | 平台 | 特点 |
|------|------|------|
| CMSIS-DSP | ARM | 硬件加速 |
| ESP-DSP | ESP32 | 优化实现 |
| KissFFT | 通用 | 轻量级 |
| FFTW | 通用 | 高性能 |
| NumPy | Python | 科学计算 |

---

## 相关链接

- [[信号处理基础]] - 信号处理基础
- [[音频处理技术]] - 音频处理
- [[传感器融合]] - 传感器融合
