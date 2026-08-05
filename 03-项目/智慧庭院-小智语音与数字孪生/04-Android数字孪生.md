---
created: 2026-07-17 14:00
updated: 2026-07-17 14:00
tags: [Android, Filament, 数字孪生, Kotlin]
project_root: E:/MCU/APP源码 (2)/APP源码
---

# Android 数字孪生 App

## 核心概念

- ==App 是状态镜像与交互壳，安全熔断在 MCU==。
- ==3D 模型是沙盘可视化，设备用坐标锚点绑定==。
- 与固件协议对齐：MQTT 状态、能耗、chat、紧急事件。

## 一、工程信息

| 项 | 值 |
|---|---|
| 路径 | `E:/MCU/APP源码 (2)/APP源码` |
| 类型 | Android Gradle/Kotlin |
| 包名 | `com.example.iot` |
| 3D | Filament / SceneView，`models/garden.glb` |
| 模型来源 | 124 STL → Blender 装配脚本 → GLB |

## 二、包结构

```text
com.example.iot
├─ mqtt/                 MQTT 连接与消息分发
├─ data/model            设备、传感器、能耗模型
├─ data/repository       数据汇聚
├─ filament/             SceneviewGardenModel、设备特效
├─ viewmodel/            DashboardViewModel 等
├─ ui/screens            主界面
├─ ui/components         左环境面板、紧急覆盖层等
└─ service/              前台/后台相关（若启用）
```

## 三、核心能力（已实现 vs 缺口）

对照 `docs/unimplemented-features.md` 与固件：

| 能力 | 状态 | 说明 |
|---|---|---|
| 设备控制 | 有 | 顺序控制、场景切换 |
| 能耗展示 | 有 | 对接 energy Topic |
| AI 对话转发 | 有 | `xiaozhi/garden/chat` |
| 火灾/求助显示 | 代码层有 | 告警动画/震动可再增强 |
| 假光照 lux | **应删除** | 固件已移除光传感器 |
| 3D 场景特效 | 有 | 雾/水/光/扇/UV 等 ViewNode |

## 四、3D 与设备绑定

| 组件 | 作用 |
|---|---|
| `SceneviewGardenModel.kt` | 加载 GLB，挂设备特效与标签 |
| `DeviceConfig.kt` | `DevicePosition(x,y,z)` 锚点 |
| Blender 脚本 | `scripts/convert_garden_to_glb.py` 等 |

可视化链路：

```text
MQTT 状态变化
→ ViewModel
→ 2D 面板刷新 + 3D 节点状态（灯亮/水/雾）
```

## 五、与 MCU 的契约

1. **Topic 一致**：energy retained、sensor、emergency。  
2. **功率表一致**：App 与 MCU 额定功率常量同步。  
3. **不发明传感器**：无光传感就不要显示 lux。  
4. **紧急 UI 不阻塞**：显示告警，但复位/恢复以 MCU 命令为准。

## 六、简历怎么写 App 部分

> 独立完成 Android 数字孪生客户端：Kotlin + Filament 加载园林 GLB 模型，经 MQTT 订阅设备状态、能耗与 AI 对话流，实现 3D 沙盘与控制面板联动；明确安全决策下沉 MCU，App 仅做可视化与便捷操作。

## 七、演示顺序建议

1. 3D 总览旋转/标签  
2. App 开关一个灯，观察 3D 与从机同步  
3. 场景切换  
4. 能耗页/卡片  
5.（可选）模拟 rain/fire 看告警 UI  
