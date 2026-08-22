# 嵌入式AI框架

## 核心概念

- **TFLite Micro** - TensorFlow Lite Micro
- **ONNX Runtime** - 跨平台推理
- **模型优化** - 量化、剪枝、蒸馏
- **边缘推理** - 实时AI推理

---

## 一、TFLite Micro

### 1.1 模型部署

```c
// TFLite Micro推理流程
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

// 模型数据(编译时嵌入)
alignas(16) const uint8_t model_data[] = {
    // 模型二进制数据
};

// 内存池(推理用)
constexpr int kTensorArenaSize = 32 * 1024;
alignas(16) uint8_t tensor_arena[kTensorArenaSize];

// 推理引擎
tflite::MicroInterpreter *interpreter = nullptr;
TfLiteTensor *input = nullptr;
TfLiteTensor *output = nullptr;

void ai_init(void) {
    // 加载模型
    const tflite::Model *model = tflite::GetModel(model_data);

    // 注册算子
    static tflite::MicroMutableOpResolver<10> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddFullyConnected();
    resolver.AddSoftmax();
    resolver.AddReshape();
    resolver.AddQuantize();
    resolver.AddDequantize();

    // 创建解释器
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    // 分配张量
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
        printf("Inference failed\n");
        return -1;
    }

    // 读取输出
    return output->data.f[0];
}
```

---

### 1.2 INT8量化推理

```c
// INT8量化模型推理
typedef struct {
    float scale;
    int32_t zero_point;
} quant_params_t;

// 量化输入
int8_t quantize_input(float value, quant_params_t *params) {
    int32_t quantized = (int32_t)(value / params->scale) + params->zero_point;
    if (quantized > 127) quantized = 127;
    if (quantized < -128) quantized = -128;
    return (int8_t)quantized;
}

// 反量化输出
float dequantize_output(int8_t value, quant_params_t *params) {
    return (value - params->zero_point) * params->scale;
}

// INT8推理
int8_t ai_predict_int8(int8_t *input_data, int input_size) {
    // 输入量化参数
    quant_params_t input_params = {
        .scale = input->params.scale,
        .zero_point = input->params.zero_point,
    };

    // 填充INT8输入
    for (int i = 0; i < input_size; i++) {
        input->data.int8[i] = input_data[i];
    }

    // 推理
    interpreter->Invoke();

    // 输出反量化
    quant_params_t output_params = {
        .scale = output->params.scale,
        .zero_point = output->params.zero_point,
    };

    return output->data.int8[0];
}
```

---

## 二、CMSIS-NN

### 2.1 ARM优化推理

```c
// CMSIS-NN加速
#include "arm_nnfunctions.h"

// INT8卷积
arm_status arm_convolve_s8(const int8_t *input,
                           const uint16_t input_x, const uint16_t input_y,
                           const uint16_t input_ch,
                           const int8_t *kernel,
                           const uint16_t output_ch,
                           const uint16_t kernel_x, const uint16_t kernel_y,
                           const uint16_t pad_x, const uint16_t pad_y,
                           const uint16_t stride_x, const uint16_t stride_y,
                           const int32_t *bias,
                           int8_t *output,
                           const int32_t *output_shift,
                           const int32_t *output_mult,
                           const int32_t output_offset,
                           const int32_t input_offset,
                           const int32_t output_activation_min,
                           const int32_t output_activation_max,
                           const uint16_t output_x, const uint16_t output_y,
                           int16_t *buffer_a);

// 全连接层
arm_status arm_fully_connected_s8(const int8_t *input,
                                  const int8_t *weights,
                                  const uint16_t col_dim,
                                  const uint16_t row_dim,
                                  const int32_t *bias,
                                  int8_t *output,
                                  const int32_t *output_shift,
                                  const int32_t *output_mult,
                                  const int32_t output_offset,
                                  const int32_t input_offset,
                                  const int32_t output_activation_min,
                                  const int32_t output_activation_max,
                                  int16_t *buffer_a);

// 性能对比
/*
 * TFLite Micro (软件): ~10ms/推理
 * CMSIS-NN (ARM优化): ~2ms/推理
 * NPU (专用硬件): ~0.5ms/推理
 */
```

---

## 三、ESP-DL

### 3.1 ESP32-S3 AI加速

```c
// ESP-DL深度学习框架
#include "dl_layer.hpp"
#include "dl_layer_conv2d.hpp"
#include "dl_layer_dense.hpp"

// 模型定义
class MyModel : public dl::Model {
private:
    dl::Conv2D<int8_t> conv1;
    dl::Dense<int8_t> dense1;

public:
    MyModel() : conv1(1, 3, 3, 16, {1, 1}, {1, 1}),
                dense1(16, 10) {}

    void build() {
        conv1.build({28, 28, 1});
        dense1.build({16});
    }

    dl::Tensor<int8_t> *forward(dl::Tensor<int8_t> *input) {
        auto *x = conv1.forward(input);
        x = dense1.forward(x);
        return x;
    }
};

// 推理
void esp_dl_inference(int8_t *image_data) {
    static MyModel model;
    model.build();

    dl::Tensor<int8_t> input({28, 28, 1}, image_data);
    dl::Tensor<int8_t> *output = model.forward(&input);

    // 获取预测结果
    int max_idx = 0;
    int8_t max_val = output->data[0];
    for (int i = 1; i < 10; i++) {
        if (output->data[i] > max_val) {
            max_val = output->data[i];
            max_idx = i;
        }
    }

    printf("Predicted: %d (confidence: %d)\n", max_idx, max_val);
}
```

---

## 四、模型优化技术

### 4.1 知识蒸馏

```c
// 知识蒸馏(Teacher → Student)
typedef struct {
    float temperature;   // 温度参数
    float alpha;         // 平衡系数
} distillation_config_t;

// 蒸馏损失
float distillation_loss(float *student_logits, float *teacher_logits,
                        int *true_labels, int num_classes,
                        distillation_config_t *config) {
    float soft_loss = 0;
    float hard_loss = 0;

    // 软标签损失(KL散度)
    for (int i = 0; i < num_classes; i++) {
        float s = student_logits[i] / config->temperature;
        float t = teacher_logits[i] / config->temperature;

        soft_loss += expf(t) * (t - s);
    }
    soft_loss *= config->temperature * config->temperature;

    // 硬标签损失(交叉熵)
    for (int i = 0; i < num_classes; i++) {
        float target = (i == true_labels[0]) ? 1.0f : 0.0f;
        hard_loss -= target * logf(student_logits[i] + 1e-10f);
    }

    return config->alpha * soft_loss + (1 - config->alpha) * hard_loss;
}
```

---

### 4.2 模型剪枝

```c
// 结构化剪枝(通道剪枝)
typedef struct {
    float *importance;   // 通道重要性
    int num_channels;
    float prune_ratio;   // 剪枝比例
} channel_pruner_t;

void prune_channels(channel_pruner_t *pruner, float *weights,
                   int channels, int kernel_size) {
    // 计算每个通道的L1范数
    for (int c = 0; c < channels; c++) {
        float norm = 0;
        for (int k = 0; k < kernel_size; k++) {
            norm += fabsf(weights[c * kernel_size + k]);
        }
        pruner->importance[c] = norm;
    }

    // 排序找到阈值
    float *sorted = malloc(channels * sizeof(float));
    memcpy(sorted, pruner->importance, channels * sizeof(float));
    qsort(sorted, channels, sizeof(float), compare_float);

    int prune_count = (int)(channels * pruner->prune_ratio);
    float threshold = sorted[prune_count];

    // 剪枝(将不重要的通道置零)
    for (int c = 0; c < channels; c++) {
        if (pruner->importance[c] < threshold) {
            memset(&weights[c * kernel_size], 0, kernel_size * sizeof(float));
        }
    }
}
```

---

## 五、嵌入式视觉AI

### 5.1 目标检测

```c
// YOLO后处理
typedef struct {
    float x, y, w, h;   // 边界框
    float confidence;    // 置信度
    int class_id;        // 类别
} detection_t;

// NMS(非极大值抑制)
void nms(detection_t *dets, int num_dets, float iou_threshold,
         detection_t *result, int *num_result) {
    // 按置信度排序
    qsort(dets, num_dets, sizeof(detection_t), compare_confidence);

    *num_result = 0;
    bool suppressed[num_dets];
    memset(suppressed, 0, sizeof(suppressed));

    for (int i = 0; i < num_dets; i++) {
        if (suppressed[i]) continue;

        result[(*num_result)++] = dets[i];

        for (int j = i + 1; j < num_dets; j++) {
            if (suppressed[j]) continue;
            if (dets[i].class_id != dets[j].class_id) continue;

            float iou = calc_iou(&dets[i], &dets[j]);
            if (iou > iou_threshold) {
                suppressed[j] = true;
            }
        }
    }
}

// 边界框解码
void decode_bbox(float *raw_output, int grid_x, int grid_y,
                 int anchor_w, int anchor_h,
                 detection_t *det) {
    float cx = (raw_output[0] * 2 - 0.5 + grid_x) * 32;  // 假设stride=32
    float cy = (raw_output[1] * 2 - 0.5 + grid_y) * 32;
    float w = powf(raw_output[2] * 2, 2) * anchor_w;
    float h = powf(raw_output[3] * 2, 2) * anchor_h;

    det->x = cx - w / 2;
    det->y = cy - h / 2;
    det->w = w;
    det->h = h;
    det->confidence = raw_output[4];
}
```

---

## 六、语音AI

### 6.1 关键词检测

```c
// 关键词检测流程
typedef struct {
    float mfcc_features[49][13];  // MFCC特征
    int model_output;             // 模型输出
    char keyword[32];             // 检测到的关键词
} keyword_detector_t;

// 音频处理流程
void keyword_detect_process(keyword_detector_t *kd, int16_t *audio,
                            int sample_rate, int frame_size) {
    // 1. 预加重
    for (int i = frame_size - 1; i > 0; i--) {
        audio[i] -= 0.97f * audio[i - 1];
    }

    // 2. 分帧加窗
    float windowed[frame_size];
    for (int i = 0; i < frame_size; i++) {
        float w = 0.54f - 0.46f * cosf(2 * M_PI * i / (frame_size - 1));
        windowed[i] = audio[i] * w;
    }

    // 3. 提取MFCC
    extract_mfcc(windowed, sample_rate, frame_size, kd->mfcc_features);

    // 4. 模型推理
    kd->model_output = ai_predict_mfcc(kd->mfcc_features);

    // 5. 解码结果
    if (kd->model_output >= 0) {
        const char *keywords[] = {"hello", "stop", "go", "yes", "no"};
        strcpy(kd->keyword, keywords[kd->model_output]);
        printf("Detected: %s\n", kd->keyword);
    }
}
```

---

## 附录：嵌入式AI框架对比

| 框架 | 平台 | 特点 |
|------|------|------|
| TFLite Micro | 通用 | Google官方 |
| CMSIS-NN | ARM | 硬件优化 |
| ESP-DL | ESP32 | 乐鑫优化 |
| ONNX Runtime | 通用 | 跨平台 |
| TVM | 通用 | 自动优化 |

---

## 相关链接

- [[TinyML详解]] - TinyML基础
- [[ESP-DL]] - ESP32 AI
- [[机器学习基础]] - ML基础
- [[DSP技术详解]] - 信号处理
