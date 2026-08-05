# PID控制器详解

## 核心概念

- **PID** - 比例-积分-微分控制
- **反馈控制** - 闭环控制系统
- **稳定性** - 系统响应特性
- **调参** - 参数整定方法

---

## 一、PID基础

### 1.1 PID控制器

```c
// PID控制器结构
typedef struct {
    // 参数
    float Kp;           // 比例系数
    float Ki;           // 积分系数
    float Kd;           // 微分系数

    // 状态
    float setpoint;     // 目标值
    float integral;     // 积分累积
    float prev_error;   // 上次误差
    float prev_measurement; // 上次测量值

    // 输出限制
    float output_min;
    float output_max;

    // 积分限制
    float integral_min;
    float integral_max;

    // 时间
    float dt;           // 采样周期
} pid_controller_t;

// 初始化PID
void pid_init(pid_controller_t *pid, float Kp, float Ki, float Kd, float dt) {
    pid->Kp = Kp;
    pid->Ki = Ki;
    pid->Kd = Kd;
    pid->dt = dt;

    pid->setpoint = 0;
    pid->integral = 0;
    pid->prev_error = 0;
    pid->prev_measurement = 0;

    pid->output_min = -1000;
    pid->output_max = 1000;
    pid->integral_min = -500;
    pid->integral_max = 500;
}

// 位置式PID
float pid_compute_position(pid_controller_t *pid, float measurement) {
    float error = pid->setpoint - measurement;

    // 比例项
    float P = pid->Kp * error;

    // 积分项
    pid->integral += error * pid->dt;
    // 积分限幅
    if (pid->integral > pid->integral_max) pid->integral = pid->integral_max;
    if (pid->integral < pid->integral_min) pid->integral = pid->integral_min;
    float I = pid->Ki * pid->integral;

    // 微分项
    float derivative = (error - pid->prev_error) / pid->dt;
    float D = pid->Kd * derivative;

    // 输出
    float output = P + I + D;

    // 输出限幅
    if (output > pid->output_max) output = pid->output_max;
    if (output < pid->output_min) output = pid->output_min;

    // 保存状态
    pid->prev_error = error;

    return output;
}

// 增量式PID
float pid_compute_incremental(pid_controller_t *pid, float measurement) {
    float error = pid->setpoint - measurement;

    // 增量计算
    float delta_P = pid->Kp * (error - pid->prev_error);
    float delta_I = pid->Ki * error * pid->dt;
    float delta_D = pid->Kd * (error - 2 * pid->prev_error + pid->prev_measurement) / pid->dt;

    float delta_output = delta_P + delta_I + delta_D;

    // 保存状态
    pid->prev_error = error;
    pid->prev_measurement = measurement;

    return delta_output;
}
```

### 1.2 PID变种

```c
// 抗积分饱和PID
typedef struct {
    float Kp, Ki, Kd;
    float integral;
    float prev_error;
    float output_min, output_max;
    float dt;
    bool anti_windup;
} pid_anti_windup_t;

float pid_compute_anti_windup(pid_anti_windup_t *pid, float measurement) {
    float error = pid->setpoint - measurement;

    float P = pid->Kp * error;

    // 积分项（带抗饱和）
    pid->integral += error * pid->dt;

    float I = pid->Ki * pid->integral;

    // 微分项
    float derivative = (error - pid->prev_error) / pid->dt;
    float D = pid->Kd * derivative;

    float output = P + I + D;

    // 抗积分饱和
    if (pid->anti_windup) {
        if (output > pid->output_max) {
            output = pid->output_max;
            // 回退积分
            pid->integral -= error * pid->dt;
        } else if (output < pid->output_min) {
            output = pid->output_min;
            pid->integral -= error * pid->dt;
        }
    } else {
        if (output > pid->output_max) output = pid->output_max;
        if (output < pid->output_min) output = pid->output_min;
    }

    pid->prev_error = error;
    return output;
}

// 微分先行PID
typedef struct {
    float Kp, Ki, Kd;
    float integral;
    float prev_error;
    float prev_measurement;
    float dt;
    float alpha;  // 滤波系数
} pid_derivative_filter_t;

float pid_compute_derivative_on_measurement(pid_derivative_filter_t *pid, float measurement) {
    float error = pid->setpoint - measurement;

    float P = pid->Kp * error;

    pid->integral += error * pid->dt;
    float I = pid->Ki * pid->integral;

    // 微分作用于测量值而非误差
    float derivative = -(measurement - pid->prev_measurement) / pid->dt;

    // 低通滤波
    static float filtered_derivative = 0;
    filtered_derivative = pid->alpha * derivative + (1 - pid->alpha) * filtered_derivative;

    float D = pid->Kd * filtered_derivative;

    float output = P + I + D;

    pid->prev_error = error;
    pid->prev_measurement = measurement;

    return output;
}

// 增量式PID（带限幅）
typedef struct {
    float Kp, Ki, Kd;
    float prev_error;
    float prev_prev_error;
    float prev_output;
    float output_min, output_max;
    float delta_max;  // 增量限幅
    float dt;
} pid_incremental_limited_t;

float pid_compute_incremental_limited(pid_incremental_limited_t *pid, float measurement) {
    float error = pid->setpoint - measurement;

    float delta_P = pid->Kp * (error - pid->prev_error);
    float delta_I = pid->Ki * error * pid->dt;
    float delta_D = pid->Kd * (error - 2 * pid->prev_error + pid->prev_prev_error) / pid->dt;

    float delta = delta_P + delta_I + delta_D;

    // 增量限幅
    if (delta > pid->delta_max) delta = pid->delta_max;
    if (delta < -pid->delta_max) delta = -pid->delta_max;

    float output = pid->prev_output + delta;

    // 输出限幅
    if (output > pid->output_max) output = pid->output_max;
    if (output < pid->output_min) output = pid->output_min;

    pid->prev_prev_error = pid->prev_error;
    pid->prev_error = error;
    pid->prev_output = output;

    return output;
}
```

---

## 二、PID调参

### 2.1 Ziegler-Nichols方法

```c
// 临界比例度法
typedef struct {
    float Ku;   // 临界增益
    float Tu;   // 临界周期
} zn_params_t;

// Ziegler-Nichols整定
typedef struct {
    float Kp, Ki, Kd;
} pid_gains_t;

pid_gains_t zn_tune_pid(zn_params_t *zn, const char *type) {
    pid_gains_t gains;

    if (strcmp(type, "P") == 0) {
        gains.Kp = 0.5f * zn->Ku;
        gains.Ki = 0;
        gains.Kd = 0;
    } else if (strcmp(type, "PI") == 0) {
        gains.Kp = 0.45f * zn->Ku;
        gains.Ki = 0.54f * zn->Ku / zn->Tu;
        gains.Kd = 0;
    } else if (strcmp(type, "PID") == 0) {
        gains.Kp = 0.6f * zn->Ku;
        gains.Ki = 1.2f * zn->Ku / zn->Tu;
        gains.Kd = 0.075f * zn->Ku * zn->Tu;
    }

    return gains;
}

// Cohen-Coon整定
pid_gains_t cohen_coon_tune(float K, float L, float T) {
    pid_gains_t gains;

    float r = L / T;

    gains.Kp = (1.0f / K) * (1.0f + 0.35f * r / (1 - r));
    gains.Ki = gains.Kp / (L * (2.5f - 2.0f * r) / (1.0f + 0.39f * r));
    gains.Kd = gains.Kp * L * (0.37f - 0.37f * r) / (1.0f - 0.81f * r);

    return gains;
}

// 自动整定（继电反馈法）
typedef struct {
    float amplitude;    // 继电幅值
    float hysteresis;   // 迟滞宽度
    float period;       // 振荡周期
    float amplitude_osc; // 振荡幅值
    bool tuning;
} auto_tune_t;

void auto_tune_start(auto_tune_t *tuner, float amplitude, float hysteresis) {
    tuner->amplitude = amplitude;
    tuner->hysteresis = hysteresis;
    tuner->tuning = true;
    tuner->period = 0;
    tuner->amplitude_osc = 0;
}

float auto_tune_relay(auto_tune_t *tuner, float measurement, float setpoint) {
    static float last_cross = 0;
    static int cross_count = 0;
    static bool above = true;

    float error = setpoint - measurement;

    if (!tuner->tuning) return 0;

    // 继电控制
    if (error > tuner->hysteresis) {
        above = true;
        return tuner->amplitude;
    } else if (error < -tuner->hysteresis) {
        above = false;
        return -tuner->amplitude;
    }

    // 检测过零
    if ((error > 0 && !above) || (error < 0 && above)) {
        float now = get_time();
        if (last_cross > 0) {
            tuner->period = 2.0f * (now - last_cross);
        }
        last_cross = now;
        cross_count++;
    }

    // 收集足够周期后结束
    if (cross_count >= 6) {
        tuner->tuning = false;
        // 计算振荡幅值
        tuner->amplitude_osc = tuner->amplitude;  // 简化
    }

    return above ? tuner->amplitude : -tuner->amplitude;
}
```

### 2.2 自适应PID

```c
// 自适应PID
typedef struct {
    float Kp, Ki, Kd;
    float integral;
    float prev_error;
    float dt;

    // 自适应参数
    float learning_rate;
    float *gradient_Kp;
    float *gradient_Ki;
    float *gradient_Kd;
} adaptive_pid_t;

// 梯度下降自适应
void adaptive_pid_update(adaptive_pid_t *pid, float error, float output) {
    // 计算梯度（简化）
    float gradient_Kp = error * error;
    float gradient_Ki = pid->integral * error;
    float gradient_Kd = (error - pid->prev_error) / pid->dt * error;

    // 更新参数
    pid->Kp -= pid->learning_rate * gradient_Kp;
    pid->Ki -= pid->learning_rate * gradient_Ki;
    pid->Kd -= pid->learning_rate * gradient_Kd;

    // 参数限幅
    if (pid->Kp < 0) pid->Kp = 0;
    if (pid->Ki < 0) pid->Ki = 0;
    if (pid->Kd < 0) pid->Kd = 0;
}

// 模糊PID
typedef struct {
    float Kp, Ki, Kd;
    float prev_error;
    float prev_delta_error;
    float dt;
} fuzzy_pid_t;

// 模糊规则表
typedef struct {
    float Kp_delta;
    float Ki_delta;
    float Kd_delta;
} fuzzy_output_t;

// 模糊化
typedef struct {
    float NM;  // 负中
    float NS;  // 负小
    float ZO;  // 零
    float PS;  // 正小
    float PM;  // 正中
} fuzzy_membership_t;

fuzzy_membership_t fuzzify(float value, float range) {
    fuzzy_membership_t m = {0};
    float nv = value / range;  // 归一化

    if (nv <= -1.0f) {
        m.NM = 1.0f;
    } else if (nv <= -0.5f) {
        m.NM = (-0.5f - nv) * 2;
        m.NS = (nv + 1.0f) * 2;
    } else if (nv <= 0) {
        m.NS = (0 - nv) * 2;
        m.ZO = (nv + 0.5f) * 2;
    } else if (nv <= 0.5f) {
        m.ZO = (0.5f - nv) * 2;
        m.PS = nv * 2;
    } else if (nv <= 1.0f) {
        m.PS = (1.0f - nv) * 2;
        m.PM = (nv - 0.5f) * 2;
    } else {
        m.PM = 1.0f;
    }

    return m;
}

// 模糊PID计算
fuzzy_output_t fuzzy_pid_evaluate(float error, float delta_error) {
    fuzzy_membership_t e_m = fuzzify(error, 100.0f);
    fuzzy_membership_t de_m = fuzzify(delta_error, 50.0f);

    fuzzy_output_t output = {0};

    // 模糊规则（简化示例）
    // IF error=NM AND delta=NM THEN Kp=PM, Ki=ZO, Kd=PS
    // ... 完整规则表需要64条规则

    // 去模糊化（重心法）
    float total_weight = 0;
    float sum_Kp = 0, sum_Ki = 0, sum_Kd = 0;

    // 简化：只用误差和变化率的主要隶属度
    float w1 = e_m.NM * de_m.NM;
    sum_Kp += w1 * 0.3f; sum_Ki += w1 * 0; sum_Kd += w1 * 0.1f;
    total_weight += w1;

    float w2 = e_m.PM * de_m.PM;
    sum_Kp += w2 * 0.3f; sum_Ki += w2 * 0; sum_Kd += w2 * 0.1f;
    total_weight += w2;

    if (total_weight > 0) {
        output.Kp_delta = sum_Kp / total_weight;
        output.Ki_delta = sum_Ki / total_weight;
        output.Kd_delta = sum_Kd / total_weight;
    }

    return output;
}
```

---

## 三、PID应用

### 3.1 电机速度控制

```c
// 电机PID控制
typedef struct {
    pid_controller_t pid;
    float rpm_setpoint;
    float rpm_actual;
    float pwm_output;
    float encoder_count;
    uint32_t last_time;
} motor_pid_t;

void motor_pid_init(motor_pid_t *motor) {
    pid_init(&motor->pid, 2.0f, 0.5f, 0.1f, 0.01f);
    motor->pid.output_min = -100;
    motor->pid.output_max = 100;
    motor->rpm_setpoint = 0;
    motor->rpm_actual = 0;
    motor->pwm_output = 0;
    motor->encoder_count = 0;
    motor->last_time = 0;
}

// 更新转速
void motor_update_rpm(motor_pid_t *motor, int32_t encoder_delta, uint32_t time_delta) {
    // 计算RPM
    float pulses_per_rev = 1000;  // 编码器脉冲/转
    motor->rpm_actual = (encoder_delta / pulses_per_rev) / (time_delta / 60000.0f);
}

// PID控制循环
void motor_control_loop(motor_pid_t *motor) {
    motor->pid.setpoint = motor->rpm_setpoint;
    motor->pwm_output = pid_compute_position(&motor->pid, motor->rpm_actual);

    // 设置PWM
    if (motor->pwm_output >= 0) {
        motor_set_direction(MOTOR_FORWARD);
        motor_set_pwm((uint32_t)motor->pwm_output);
    } else {
        motor_set_direction(MOTOR_REVERSE);
        motor_set_pwm((uint32_t)(-motor->pwm_output));
    }
}
```

### 3.2 温度控制

```c
// 温度PID控制
typedef struct {
    pid_controller_t pid;
    float temp_setpoint;
    float temp_actual;
    float heater_output;
    float temp_history[100];
    int history_index;
} temp_control_t;

void temp_control_init(temp_control_t *ctrl) {
    pid_init(&ctrl->pid, 10.0f, 0.1f, 1.0f, 1.0f);
    ctrl->pid.output_min = 0;
    ctrl->pid.output_max = 100;
    ctrl->temp_setpoint = 25.0f;
    ctrl->temp_actual = 25.0f;
    ctrl->heater_output = 0;
    ctrl->history_index = 0;
}

// 温度控制循环
void temp_control_loop(temp_control_t *ctrl) {
    // 读取温度
    ctrl->temp_actual = read_temperature_sensor();

    // 记录历史
    ctrl->temp_history[ctrl->history_index] = ctrl->temp_actual;
    ctrl->history_index = (ctrl->history_index + 1) % 100;

    // PID计算
    ctrl->pid.setpoint = ctrl->temp_setpoint;
    ctrl->heater_output = pid_compute_position(&ctrl->pid, ctrl->temp_actual);

    // 设置加热器
    heater_set_power(ctrl->heater_output);
}

// 温度曲线跟踪
typedef struct {
    float *temp_profile;
    float *time_profile;
    int profile_length;
    int current_segment;
    float start_time;
} temp_profile_t;

float temp_profile_get_setpoint(temp_profile_t *profile, float current_time) {
    float elapsed = current_time - profile->start_time;

    // 查找当前段
    for (int i = 0; i < profile->profile_length - 1; i++) {
        if (elapsed >= profile->time_profile[i] && elapsed < profile->time_profile[i + 1]) {
            // 线性插值
            float t = (elapsed - profile->time_profile[i]) /
                      (profile->time_profile[i + 1] - profile->time_profile[i]);
            return profile->temp_profile[i] +
                   t * (profile->temp_profile[i + 1] - profile->temp_profile[i]);
        }
    }

    return profile->temp_profile[profile->profile_length - 1];
}
```

### 3.3 平衡车控制

```c
// 平衡车PID
typedef struct {
    // 姿态环
    pid_controller_t angle_pid;
    float angle_setpoint;
    float angle_actual;

    // 速度环
    pid_controller_t speed_pid;
    float speed_setpoint;
    float speed_actual;

    // 输出
    float left_motor;
    float right_motor;
} balance_pid_t;

void balance_pid_init(balance_pid_t *balance) {
    // 姿态环（快环）
    pid_init(&balance->angle_pid, 50.0f, 0, 20.0f, 0.005f);
    balance->angle_pid.output_min = -100;
    balance->angle_pid.output_max = 100;

    // 速度环（慢环）
    pid_init(&balance->speed_pid, 0.5f, 0.01f, 0, 0.01f);
    balance->speed_pid.output_min = -30;
    balance->speed_pid.output_max = 30;
}

// 平衡控制
void balance_control(balance_pid_t *balance) {
    // 速度环（外环）
    balance->speed_pid.setpoint = balance->speed_setpoint;
    float speed_output = pid_compute_position(&balance->speed_pid, balance->speed_actual);

    // 姿态环（内环）
    balance->angle_pid.setpoint = balance->angle_setpoint + speed_output;
    balance->angle_pid.setpoint = constrain(balance->angle_pid.setpoint, -30, 30);

    balance->angle_actual = read_imu_angle();
    float angle_output = pid_compute_position(&balance->angle_pid, balance->angle_actual);

    // 电机输出
    balance->left_motor = angle_output;
    balance->right_motor = angle_output;

    // 差速转向
    float turn_output = read_gyro_z() * 0.1f;
    balance->left_motor += turn_output;
    balance->right_motor -= turn_output;

    // 设置电机
    motor_set_left(balance->left_motor);
    motor_set_right(balance->right_motor);
}
```

---

## 四、数字PID

### 4.1 离散化方法

```c
// 双线性变换（Tustin）
typedef struct {
    float a0, a1, a2;
    float b0, b1, b2;
    float x[3];  // 输入历史
    float y[3];  // 输出历史
} digital_filter_t;

// 将连续PID转换为离散PID
void discretize_pid(float Kp, float Ki, float Kd, float dt,
                    float *a0, float *a1, float *a2,
                    float *b0, float *b1, float *b2) {
    // 双线性变换: s = 2/T * (z-1)/(z+1)
    float K = 2.0f / dt;

    // 连续传递函数: C(s) = Kp + Ki/s + Kd*s
    // 离散化后
    *a0 = Kp + Ki * dt / 2 + Kd * K;
    *a1 = -2 * Kp + Ki * dt - 2 * Kd * K;
    *a2 = Kp + Ki * dt / 2 + Kd * K;
    *b0 = 1;
    *b1 = -2;
    *b2 = 1;
}

// 应用数字滤波器
float digital_filter_apply(digital_filter_t *filter, float input) {
    // 移位
    filter->x[2] = filter->x[1];
    filter->x[1] = filter->x[0];
    filter->x[0] = input;

    filter->y[2] = filter->y[1];
    filter->y[1] = filter->y[0];

    // 差分方程
    filter->y[0] = filter->a0 * filter->x[0] +
                   filter->a1 * filter->x[1] +
                   filter->a2 * filter->x[2] -
                   filter->b1 * filter->y[1] -
                   filter->b2 * filter->y[2];

    return filter->y[0];
}
```

### 4.2 增量式PID优化

```c
// 增量式PID（无积分饱和）
typedef struct {
    float Kp, Ki, Kd;
    float error[3];  // 当前、上次、上上次
    float output;
    float output_min, output_max;
    float dt;
} pid_incremental_opt_t;

float pid_incremental_compute(pid_incremental_opt_t *pid, float measurement) {
    // 更新误差历史
    pid->error[2] = pid->error[1];
    pid->error[1] = pid->error[0];
    pid->error[0] = pid->setpoint - measurement;

    // 增量计算
    float delta = pid->Kp * (pid->error[0] - pid->error[1])
                + pid->Ki * pid->error[0] * pid->dt
                + pid->Kd * (pid->error[0] - 2 * pid->error[1] + pid->error[2]) / pid->dt;

    pid->output += delta;

    // 输出限幅
    if (pid->output > pid->output_max) pid->output = pid->output_max;
    if (pid->output < pid->output_min) pid->output = pid->output_min;

    return pid->output;
}
```

---

## 五、PID调试

### 5.1 响应分析

```c
// 阶跃响应分析
typedef struct {
    float rise_time;      // 上升时间
    float overshoot;      // 超调量
    float settling_time;  // 稳定时间
    float steady_state;   // 稳态值
    float peak_value;     // 峰值
    float peak_time;      // 峰值时间
} step_response_t;

step_response_t analyze_step_response(float *response, int length, float setpoint) {
    step_response_t result = {0};

    // 找峰值
    result.peak_value = response[0];
    result.peak_time = 0;
    for (int i = 1; i < length; i++) {
        if (response[i] > result.peak_value) {
            result.peak_value = response[i];
            result.peak_time = i;
        }
    }

    // 计算超调量
    result.overshoot = (result.peak_value - setpoint) / setpoint * 100;

    // 找稳态值（最后10%的平均值）
    int steady_start = length * 9 / 10;
    float sum = 0;
    for (int i = steady_start; i < length; i++) {
        sum += response[i];
    }
    result.steady_state = sum / (length - steady_start);

    // 上升时间（10%到90%）
    float target_10 = setpoint * 0.1f;
    float target_90 = setpoint * 0.9f;
    int t10 = 0, t90 = 0;
    for (int i = 0; i < length; i++) {
        if (response[i] >= target_10 && t10 == 0) t10 = i;
        if (response[i] >= target_90 && t90 == 0) t90 = i;
    }
    result.rise_time = t90 - t10;

    // 稳定时间（进入±2%范围）
    float band = setpoint * 0.02f;
    for (int i = length - 1; i >= 0; i--) {
        if (fabs(response[i] - setpoint) > band) {
            result.settling_time = i + 1;
            break;
        }
    }

    return result;
}
```

### 5.2 PID调参建议

```c
// PID调参规则
typedef struct {
    float overshoot;
    float rise_time;
    float settling_time;
    const char *adjustment;
} tuning_rule_t;

const tuning_rule_t tuning_rules[] = {
    {10, 0, 0, "Kp过大，减小Kp"},
    {0, 10, 0, "Kp过小，增大Kp"},
    {10, 10, 0, "Ki过大，减小Ki"},
    {0, 0, 10, "Kd过大，减小Kd"},
    {5, 5, 5, "参数基本合适"},
};

// 自动调参建议
const char *auto_tune_suggest(step_response_t *resp, float setpoint) {
    float overshoot_pct = resp->overshoot;
    float rise_ratio = resp->rise_time;
    float settle_ratio = resp->settling_time;

    if (overshoot_pct > 20) {
        return "超调过大：减小Kp或增大Kd";
    } else if (overshoot_pct < 5 && rise_ratio > 2) {
        return "响应过慢：增大Kp或Ki";
    } else if (settle_ratio > 5) {
        return "稳定时间过长：调整Kd";
    } else {
        return "参数较为理想";
    }
}
```

---

## 附录：PID参数整定表

| 控制对象 | Kp | Ki | Kd | 说明 |
|----------|-----|-----|-----|------|
| 温度控制 | 10-50 | 0.1-1 | 1-10 | 惯性大 |
| 电机速度 | 1-5 | 0.1-1 | 0.01-0.1 | 响应快 |
| 位置控制 | 1-10 | 0-0.1 | 0.1-1 | 精度高 |
| 液位控制 | 1-5 | 0.01-0.1 | 0.1-1 | 滞后大 |
| 压力控制 | 1-10 | 0.1-1 | 0.1-1 | 响应快 |

---

## 相关链接

- [[电机控制技术]] - 电机控制
- [[传感器融合]] - 姿态解算
- [[嵌入式系统基础]] - 嵌入式系统
- [[STM32基础]] - MCU开发
