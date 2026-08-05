# Track_Car：IMU660RB 零偏与陀螺仪循迹完善

- 时间：2026-07-25 01:01:08
- 项目：`E:\MCU\MSPM0\Contest\Track_Car`
- 分支：`agent/fix-host-responsive-charts`
- 基线提交：`f38e159 Replace ICM42688 with SeekFree IMU660RB`

## 本次目标

在 IMU660RB 驱动替换完成后，完善静止去零偏、航向积分、陀螺仪闭环转弯、直角弯捕线和短时丢线循迹，并保持 5 ms 裸机控制环非阻塞、传感器异常失效安全。

## 主要修改

- `BSP/Inc/bsp_imu660rb.h`、`BSP/Src/bsp_imu660rb.c`
  - 启动校准增加近 1 g 加速度和低角速度静止门限，运动样本拒绝次数有上限。
  - 使用 Welford 统计计算零偏和标准差，按噪声生成 0.05–0.50 dps 动态死区。
  - 电机禁用状态连续确认 100 个静止样本后，以限幅小步长跟踪零偏/温漂；运动授权时冻结零偏学习。
  - 航向通路增加一阶低通、死区和梯形积分；确认静止的样本不累计航向。
- `APP/Inc/app_imu.h`、`APP/Src/app_imu.c`、`main.c`
  - 新增静止更新接口，在 5 ms 主循环中仅于电机明确禁用时调用。
  - 校准日志输出 bias、noise、deadzone 和运动拒绝计数。
- `TASK/track.c`、`TASK/track.h`、`TASK/track_logic.h`
  - 正常循迹继续使用灰度 PID + IMU 角速度阻尼。
  - 丢线/无效帧冻结灰度 PID，降到低速，并以末次偏差 P + 最后有效航向 P + 角速度 D 短时找线。
  - 直角弯增加独立 12 s 总看门狗和最多 2 次阶段重试，超限立即停车并锁存安全故障。
  - 修复速度闭环模式下低速目标被 `TRACK_MOTOR_INNER_MIN=24` 强制抬高的问题。
- `APP/Inc/user_tuning.h`
  - 集中新增丢线航向恢复和直角弯总看门狗参数。
- `tests/test_imu_logic.py`、`tests/test_track_logic.py`
  - 覆盖运动校准拒绝、静止零偏自适应、运动冻结、航向恢复极性、直角弯总超时/重试/时钟回绕。
- `.claude/CLAUDE.md`
  - 记录新的 IMU 校准、漂移抑制、丢线航向保持和直角弯安全规则。

## 验证结果

- `python -m unittest discover -s tests -v`：250 项全部通过。
- `python -m compileall -q host tests`：通过。
- `git diff --check`：通过，仅出现 Git 的 LF/CRLF 提示。
- Keil MDK ARMClang 6.21：0 Error，0 Warning。
- 固件尺寸：Code 70500，RO-data 10288，RW-data 560，ZI-data 22616。

## 安全与后续

- 本次未烧录、未擦除，也未让电机动作。
- 上车前应架空车轮，确认左转时 `gyro_z > 0`，再做多次 ±90° 原地旋转和低速单弯/丢线捕线实测。
- 仓库中用户已有的 PDF/历史日志删除项及鱼眼资料目录、压缩包保持原状，未纳入修改。

