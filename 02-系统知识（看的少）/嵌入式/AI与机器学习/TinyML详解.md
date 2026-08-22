# TinyML详解

## 核心概念

- **TinyML** - 微型机器学习
- **量化** - 降低模型精度
- **推理引擎** - 模型执行环境
- **边缘AI** - 设备端智能

---

## 一、TinyML概述

### 1.1 TinyML vs 传统ML

| 特性 | 传统ML | TinyML |
|------|--------|--------|
| 平台 | 服务器/GPU | MCU/NPU |
| 内存 | GB级 | KB级 |
| 功耗 | 百瓦级 | 毫瓦级 |
| 延迟 | 依赖网络 | 本地实时 |
| 模型 | 大模型 | 微型模型 |

---

### 1.2 典型应用

| 应用 | 传感器 | 模型 | 平台 |
|------|--------|------|------|
| 关键词检测 | 麦克风 | DNN/CNN | ESP32 |
| 手势识别 | IMU | CNN | STM32 |
| 异常检测 | 振动 | AutoEncoder | ESP32 |
| 人脸检测 | 摄像头 | MobileNet | ESP32-S3 |
| 跌倒检测 | 加速度计 | LSTM | nRF52 |

---

## 二、模型量化

### 2.1 量化类型

```c
// 量化类型对比
/*
 * 类型        精度    大小    速度    精度损失
 * FP32       32位    大      慢      无
 * FP16       16位    中      中      极小
 * INT8       8位     小      快      小
 * INT4       4位     极小    极快    中
 */

// 量化公式
// real_value = (quant_value - zero_point) * scale
// quant_value = round(real_value / scale) + zero_point
```

---

### 2.2 INT8量化实现

```c
// 量化参数
typedef struct {
    float scale;
    int8_t zero_point;
} quant_params_t;

// 权重量化
int8_t quantize_weight(float value, float scale, int8_t zero_point) {
    int32_t q = (int32_t)round(value / scale) + zero_point;
    if (q > 127) q = 127;
    if (q < -128) q = -128;
    return (int8_t)q;
}

// 反量化
float dequantize(int8_t q_value, float scale, int8_t zero_point) {
    return (q_value - zero_point) * scale;
}

// INT8矩阵乘法
void matmul_int8(const int8_t *A, const int8_t *B, int32_t *C,
                 int M, int N, int K,
                 float scale_a, float scale_b, float scale_c) {
    for (int i = 0; i < M; i++) {
        for (int j = 0; j < N; j++) {
            int32_t sum = 0;
            for (int k = 0; k < K; k++) {
                sum += (int32_t)A[i*K+k] * (int32_t)B[k*N+j];
            }
            C[i*N+j] = sum;
        }
    }
}
```

---

### 2.3 量化感知训练

```c
// 伪量化节点(训练时模拟量化误差)
float fake_quantize(float x, float scale, int8_t zero_point) {
    float q = round(x / scale) + zero_point;
    q = fminf(fmaxf(q, -128), 127);
    return (q - zero_point) * scale;
}

// 直通估计器(Straight-Through Estimator)
// 前向: 使用伪量化
// 反向: 梯度直接传递(忽略round操作)
```

---

## 三、TFLite Micro

### 3.1 模型转换

```python
# Python: TensorFlow → TFLite → C数组
import tensorflow as tf

# 加载模型
model = tf.keras.models.load_model('model.h5')

# 转换为TFLite(量化)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.int8]
tflite_model = converter.convert()

# 保存
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)

# 转换为C数组
import numpy as np
with open('model.h', 'w') as f:
    f.write('const unsigned char model[] = {\n')
    for i, byte in enumerate(tflite_model):
        f.write(f'0x{byte:02x},')
        if (i + 1) % 12 == 0:
            f.write('\n')
    f.write('\n};\n')
    f.write(f'const unsigned int model_len = {len(tflite_model)};\n')
```

---

### 3.2 TFLite Micro推理

```c
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

// 模型数据(由Python脚本生成)
#include "model.h"

// 内存池
constexpr int kTensorArenaSize = 32 * 1024;
uint8_t tensor_arena[kTensorArenaSize];

// 推理引擎
const tflite::Model *model = nullptr;
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *input = nullptr;
TfLiteTensor *output = nullptr;

void ai_init(void) {
    // 加载模型
    model = tflite::GetModel(model);

    // 注册算子
    static tflite::MicroMutableOpResolver<10> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddFullyConnected();
    resolver.AddSoftmax();
    resolver.AddReshape();

    // 创建解释器
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    // 分配内存
    interpreter->AllocateTensors();

    // 获取输入输出
    input = interpreter->input(0);
    output = interpreter->output(0);
}

// 推理
float ai_predict(float *input_data, int input_size) {
    // 填充输入
    for (int i = 0; i < input_size; i++) {
        input->data.f[i] = input_data[i];
    }

    // 执行推理
    TfLiteStatus status = interpreter->Invoke();
    if (status != kTfLiteOk) {
        printf("Inference failed!\n");
        return -1;
    }

    // 读取输出
    return output->data.f[0];
}
```

---

### 3.3 INT8推理

```c
// INT8量化推理
int8_t ai_predict_int8(int8_t *input_data, int input_size,
                       float input_scale, int8_t input_zero_point) {
    // 量化输入(如果输入是float)
    for (int i = 0; i < input_size; i++) {
        input->data.int8[i] = input_data[i];
    }

    // 执行推理
    interpreter->Invoke();

    // 获取输出(需要反量化)
    int8_t q_output = output->data.int8[0];
    float output_scale = output->params.scale;
    int8_t output_zp = output->params.zero_point;

    return q_output;
}
```

---

## 四、ESP-DL

### 4.1 ESP-DL概述

```c
// ESP-DL: 乐鑫官方深度学习框架
// 支持ESP32-S3 (向量加速器)

#include "dl_model.hpp"
#include "dl_layer.hpp"

// 模型加载
#include "model_coefficients.hpp"

static dl::Model *model = nullptr;

void esp_dl_init(void) {
    // 创建模型
    model = new dl::Model(model_coefficients, dl::MEMORY_INTERNAL);
}

// 推理
std::vector<float> esp_dl_infer(std::vector<float> &input) {
    // 设置输入
    model->set_input(input);

    // 执行推理
    model->run();

    // 获取输出
    return model->get_output();
}
```

---

### 4.2 ESP-DL CNN示例

```c
#include "dl_layer_conv2d.hpp"
#include "dl_layer_maxpool2d.hpp"
#include "dl_layer_fully_connected.hpp"
#include "dl_layer_softmax.hpp"

// 网络定义
class SimpleCNN : public dl::Model {
public:
    dl::Conv2D conv1;
    dl::MaxPool2D pool1;
    dl::Conv2D conv2;
    dl::MaxPool2D pool2;
    dl::FullyConnected fc1;
    dl::Softmax softmax;

    SimpleCNN() :
        conv1(dl::Conv2D(32, 3, 1, "relu")),
        pool1(dl::MaxPool2D(2, 2)),
        conv2(dl::Conv2D(64, 3, 1, "relu")),
        pool2(dl::MaxPool2D(2, 2)),
        fc1(dl::FullyConnected(10)),
        softmax(dl::Softmax())
    {}

    void forward() {
        auto x = conv1.forward(input);
        x = pool1.forward(x);
        x = conv2.forward(x);
        x = pool2.forward(x);
        x = fc1.forward(x);
        output = softmax.forward(x);
    }
};
```

---

## 五、模型优化

### 5.1 知识蒸馏

```c
// 知识蒸馏: 大模型(Teacher) → 小模型(Student)
/*
 * 损失函数:
 * L = α * L_hard + (1-α) * L_soft
 *
 * L_hard: 学生预测 vs 真实标签(硬标签)
 * L_soft: 学生预测 vs 教师预测(软标签)
 *
 * 软标签: teacher_output / T (T为温度参数)
 */

// 蒸馏训练伪代码
void distillation_train(float *student_pred, float *teacher_pred,
                        float *true_label, float alpha, float T) {
    // 硬标签损失(CrossEntropy)
    float L_hard = cross_entropy(student_pred, true_label);

    // 软标签损失(KL散度)
    float soft_teacher[10], soft_student[10];
    softmax_temperature(teacher_pred, soft_teacher, 10, T);
    softmax_temperature(student_pred, soft_student, 10, T);
    float L_soft = kl_divergence(soft_student, soft_teacher) * (T * T);

    // 总损失
    float loss = alpha * L_hard + (1 - alpha) * L_soft;
}
```

---

### 5.2 剪枝

```c
// 非结构化剪枝(按权重大小)
void prune_weights(float *weights, int size, float threshold) {
    for (int i = 0; i < size; i++) {
        if (fabsf(weights[i]) < threshold) {
            weights[i] = 0.0f;
        }
    }
}

// 结构化剪枝(按通道重要性)
void prune_channels(float *weights, int channels, int channel_size,
                    float *importance, float threshold) {
    for (int c = 0; c < channels; c++) {
        if (importance[c] < threshold) {
            // 将整个通道权重置零
            memset(&weights[c * channel_size], 0, channel_size * sizeof(float));
        }
    }
}

// 计算通道重要性(L1范数)
void compute_importance(float *weights, int channels, int channel_size,
                        float *importance) {
    for (int c = 0; c < channels; c++) {
        float sum = 0;
        for (int i = 0; i < channel_size; i++) {
            sum += fabsf(weights[c * channel_size + i]);
        }
        importance[c] = sum / channel_size;
    }
}
```

---

### 5.3 模型压缩比

```c
// 压缩效果评估
typedef struct {
    int original_params;
    int compressed_params;
    float original_size_kb;
    float compressed_size_kb;
    float accuracy_loss;
} compression_stats_t;

compression_stats_t evaluate_compression(int orig_params, int comp_params,
                                          float orig_acc, float comp_acc) {
    compression_stats_t stats;
    stats.original_params = orig_params;
    stats.compressed_params = comp_params;
    stats.original_size_kb = orig_params * 4.0f / 1024.0f;  // FP32
    stats.compressed_size_kb = comp_params * 1.0f / 1024.0f; // INT8
    stats.accuracy_loss = orig_acc - comp_acc;
    return stats;
}
```

---

## 六、音频关键词检测

### 6.1 MFCC特征提取

```c
// MFCC特征(用于关键词检测)
typedef struct {
    float mfcc[13];      // 13个MFCC系数
    int frame_count;
} mfcc_feature_t;

void extract_mfcc(float *audio, int sample_rate, int frame_size,
                  mfcc_feature_t *features) {
    // 1. 预加重
    float pre_emphasis = 0.97f;
    for (int i = frame_size - 1; i > 0; i--) {
        audio[i] -= pre_emphasis * audio[i - 1];
    }

    // 2. 分帧加窗
    float windowed[frame_size];
    for (int i = 0; i < frame_size; i++) {
        float w = 0.54f - 0.46f * cosf(2 * M_PI * i / (frame_size - 1)); // Hamming
        windowed[i] = audio[i] * w;
    }

    // 3. FFT
    float fft_out[frame_size];
    fft(windowed, fft_out, frame_size);

    // 4. 梅尔滤波器组
    float mel_energies[26];
    mel_filterbank(fft_out, mel_energies, 26, sample_rate, frame_size);

    // 5. DCT → MFCC
    for (int i = 0; i < 13; i++) {
        float sum = 0;
        for (int j = 0; j < 26; j++) {
            sum += logf(mel_energies[j] + 1e-10f) * cosf(M_PI * i * (j + 0.5f) / 26.0f);
        }
        features->mfcc[i] = sum;
    }
}
```

---

### 6.2 关键词检测模型

```c
// 简单关键词检测
typedef enum {
    KW_UNKNOWN = 0,
    KW_WAKE_WORD,    // 唤醒词
    KW_COMMAND_1,    // 命令1
    KW_COMMAND_2,    // 命令2
} keyword_t;

keyword_t detect_keyword(float *mfcc_features, int feature_size) {
    // 运行TFLite模型
    float output[4];
    run_model(mfcc_features, feature_size, output, 4);

    // 找最大概率
    int max_idx = 0;
    float max_prob = output[0];
    for (int i = 1; i < 4; i++) {
        if (output[i] > max_prob) {
            max_prob = output[i];
            max_idx = i;
        }
    }

    // 置信度阈值
    if (max_prob > 0.7f) {
        return (keyword_t)max_idx;
    }
    return KW_UNKNOWN;
}
```

---

## 七、异常检测

### 7.1 自编码器

```c
// 自编码器异常检测
typedef struct {
    float encoder_weights[64][32];
    float decoder_weights[32][64];
    float threshold;
} autoencoder_t;

float detect_anomaly(autoencoder_t *ae, float *input, int size) {
    // 编码
    float encoded[32];
    for (int i = 0; i < 32; i++) {
        float sum = 0;
        for (int j = 0; j < size; j++) {
            sum += input[j] * ae->encoder_weights[j][i];
        }
        encoded[i] = relu(sum);
    }

    // 解码
    float decoded[64];
    for (int i = 0; i < size; i++) {
        float sum = 0;
        for (int j = 0; j < 32; j++) {
            sum += encoded[j] * ae->decoder_weights[j][i];
        }
        decoded[i] = sum;
    }

    // 计算重构误差
    float error = 0;
    for (int i = 0; i < size; i++) {
        float diff = input[i] - decoded[i];
        error += diff * diff;
    }
    error = sqrtf(error / size);

    return error;
}
```

---

### 7.2 统计异常检测

```c
// 基于统计的异常检测
typedef struct {
    float mean;
    float std;
    float threshold;  // 通常3σ
} stats_detector_t;

void stats_detector_init(stats_detector_t *det, float *data, int count, float threshold) {
    float sum = 0, sum_sq = 0;
    for (int i = 0; i < count; i++) {
        sum += data[i];
        sum_sq += data[i] * data[i];
    }
    det->mean = sum / count;
    det->std = sqrtf(sum_sq / count - det->mean * det->mean);
    det->threshold = threshold;
}

bool stats_detect(stats_detector_t *det, float value) {
    float z_score = fabsf(value - det->mean) / (det->std + 1e-10f);
    return z_score > det->threshold;
}
```

---

## 八、性能优化

### 8.1 内存优化

```c
// 内存池管理
typedef struct {
    uint8_t *pool;
    size_t size;
    size_t used;
} memory_pool_t;

void *pool_alloc(memory_pool_t *pool, size_t size) {
    size = (size + 3) & ~3;  // 4字节对齐
    if (pool->used + size > pool->size) return NULL;
    void *ptr = pool->pool + pool->used;
    pool->used += size;
    return ptr;
}

void pool_reset(memory_pool_t *pool) {
    pool->used = 0;
}
```

---

### 8.2 计算优化

```c
// 使用DSP加速(ARM CMSIS-DSP)
#include "arm_math.h"

void fft_accelerated(float *input, float *output, int size) {
    arm_rfft_fast_instance_f32 fft_instance;
    arm_rfft_fast_init_f32(&fft_instance, size);
    arm_rfft_fast_f32(&fft_instance, input, output, 0);
}

// 矩阵乘法加速
void matmul_accelerated(const float *A, const float *B, float *C,
                        int M, int N, int K) {
    arm_matrix_instance_f32 matA, matB, matC;
    arm_mat_init_f32(&matA, M, K, (float*)A);
    arm_mat_init_f32(&matB, K, N, (float*)B);
    arm_mat_init_f32(&matC, M, N, C);
    arm_mat_mult_f32(&matA, &matB, &matC);
}
```

---

## 附录：TinyML平台对比

| 平台 | CPU | 内存 | AI加速 | 功耗 |
|------|-----|------|--------|------|
| ESP32-S3 | 240MHz | 512KB | 向量指令 | 100mW |
| STM32H7 | 480MHz | 1MB | 无 | 200mW |
| nRF5340 | 128MHz | 1MB | 无 | 10mW |
| K210 | 400MHz | 8MB | KPU | 300mW |
| MAX78000 | 100MHz | 512KB | CNN加速 | 1mW |

---

## 相关链接

- [[机器学习基础]] - ML基础
- [[深度学习进阶]] - 深度学习
- [[ESP-DL]] - ESP深度学习
- [[信号处理基础]] - 信号处理
