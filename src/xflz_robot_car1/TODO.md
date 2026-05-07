# ROS2 机器人 URDF 模型全功能验证指南

本文档描述基于新 URDF 模型进行全功能验证的标准流程。

---

## 概述

| 项目 | 说明 |
|------|------|
| 验证目标 | 确保新 URDF 模型可正常运行所有功能 |
| 适用产品 | xflz_robot_car1 (car1_description) |
| 依赖环境 | ROS2 Jazzy + 本项目代码 |
| 验证方式 | 从底层到顶层，逐层验证 |

---

## 验证流程总览

```
新URDF模型
    ↓
① URDF验证 (Rviz)
    ↓
② 运动学配置与测试
    ↓
③ 控制器配置与测试
    ↓
④ SLAM建图
    ↓
⑤ 导航验证
    ↓
⑥ 视觉功能
    ↓
⑦ 应用功能
    ↓
⑧ Bringup启动 (一键启动)
    ↓
⑨ Gazebo 仿真抓取验证（阶段1~5）
```

---

## 第一步：URDF 模型验证

### 目标

确保机器人 3D 模型在 Rviz 中正确显示，关节连杆关系正确。

### 路径

- URDF文件：`src/xflz_robot_car1/simulations/urdf/`

### 涉及文件

| 文件 | 作用 |
|------|------|
| `car1.urdf` | 主入口，机器人完整模型 |
| `car1.csv` | 机器人模型参数数据 |

### 操作命令

```bash
# 启动 Rviz 可视化
ros2 launch car1_description display.launch.py

### 验证要点

- [ ] 机器人模型完整显示
- [ ] 各关节连接关系正确
- [ ] 关节可自由拖动
- [ ] TF 坐标系正确发布

### 常见问题

- 如遇 `MACHINE_TYPE` 未设置错误：设置环境变量
- 如遇路径错误：确保在项目根目录运行

---

## 第二步：运动学配置与测试

### 目标

验证机械臂正逆运动学求解正确，确保末端可到达目标位置。

### 路径

- 运动学代码：`src/xflz_robot_car1/arm/kinematics/`

### 涉及文件

| 文件 | 作用 |
|------|------|
| `kinematics/fk_demo.py` | 正运动学正解Demo |
| `kinematics/ik_demo.py` | 逆运动学解析解Demo |
| `car1.urdf` | 机械臂模型（来自 simulations 包） |

### 操作命令

```bash
# 编译
colcon build --packages-select car1_kinematics

# 运行正运动学正解Demo
ros2 launch car1_kinematics kinematics.launch.py

# 或使用 ros2 run
ros2 run car1_kinematics fk_demo

# 运行逆运动学解析解Demo
ros2 run car1_kinematics ik_demo
```

### 机械臂关节信息

基于 car1.urdf 的机械臂结构：

| 关节名称 | 类型 | 父连杆 | 子连杆 | 限位 (rad) |
|----------|------|--------|--------|-------------|
| arm_base_joint | fixed | base_link | arm_base_link | - |
| arm_joint1 | revolute | arm_base_link | arm_link1 | [-3.14, 3.14] |
| arm_joint2 | revolute | arm_link1 | arm_link2 | [-3.14, 3.14] |
| arm_joint3 | revolute | arm_link2 | arm_link3 | [-3.14, 3.14] |
| arm_joint4 | revolute | arm_link3 | arm_link4 | [-3.14, 3.14] |
| arm_joint5 | revolute | arm_link4 | arm_link5 | [-3.14, 3.14] |
| arm_joint6 | fixed | arm_link5 | arm_link6 | - |

**机械臂自由度：5 (DOF)**

### 验证要点

- [ ] 正运动学：给定关节角度，末端位置计算正确
- [ ] 逆运动学：给定目标位置，能求出有效关节角度（解析解）
- [ ] 关节范围不超出机械结构限制
- [ ] 连杆长度与实际模型一致

### 机械臂参数

基于 car1.urdf 提取的连杆参数：

| 参数 | 说明 | 值 (m) |
|------|------|--------|
| d1 | 底座高度 | 0.0435 |
| a2 | 大臂长度 | 0.12614 |
| a3 | 小臂长度 | 0.12614 |
| a4 | 腕部长度 | 0.074395 |
| 自由度 | DOF | 5 |

### 注意事项

- 270度舵机建议限位：±120度（约±2.09弧度）
- 设置90%~95%的最大角度作为安全限位

---

## 第三步：控制器配置

### 目标

确保机器人底盘运动控制正常工作。

### 路径

- 控制器代码：`src/xflz_robot_car1/arm/controller/`
- 配置文件：`src/xflz_robot_car1/arm/controller/config/`

### 涉及文件

| 文件 | 作用 |
|------|------|
| `config/init_pose.yaml` | 机器人初始位置 |
| `config/ekf.yaml` | 扩展卡尔曼滤波配置 |
| `config/calibrate_params.yaml` | 校准参数 |
| `controller/ackermann.py` | 阿克曼底盘控制 |
| `controller/mecanum.py` | 麦克纳姆轮控制 |

### 操作命令

```bash
# 启动控制器
ros2 launch controller controller.launch.py
```

### 验证要点

- [ ] 机器人可响应运动指令
- [ ] 里程计数据正常发布
- [ ] 坐标系变换正确

---

## 第四步：SLAM 建图

### 目标

验证机器人能够构建环境地图。

### 路径

- SLAM包：`src/slam/`

### 操作命令

```bash
# 2D 建图
ros2 launch slam slam.launch.py
ros2 launch slam rviz_slam.launch.py

# 3D 建图（需要深度相机）
ros2 launch slam rtabmap_slam.launch.py
ros2 launch slam rviz_rtabmap.launch.py
```

### 验证要点

- [ ] 地图构建正常
- [ ] 实时定位准确
- [ ] 可保存地图文件

### 保存地图

```bash
cd ~/ros2_ws/src/slam/maps
ros2 run nav2_map_server map_saver_cli -f "map_01" --ros-args -p map_subscribe_transient_local:=true
```

---

## 第五步：导航验证

### 目标

验证机器人能够使用已有地图进行自主导航。

### 路径

- 导航包：`src/navigation/`

### 操作命令

```bash
# 2D 导航
ros2 launch navigation rviz_navigation.launch.py
ros2 launch navigation navigation.launch.py map:=map_01

# 3D 导航
ros2 launch navigation rtabmap_navigation.launch.py
ros2 launch navigation rviz_rtabmap_navigation.launch.py
```

### 验证要点

- [ ] 地图加载成功
- [ ] 定位正常（机器人模型与地图对齐）
- [ ] 路径规划正常
- [ ] 导航目标可正常下达

---

## 第六步：视觉功能验证

### 目标

验证基于摄像头的视觉功能正常工作。

### 路径

- 视觉代码：`src/example/example/`

### 功能列表与命令

| 功能 | 命令 |
|------|------|
| 颜色检测 | `ros2 launch example color_detect.launch.py` |
| 颜色追踪 | `ros2 launch example color_track_node.launch.py` |
| 手部追踪 | `ros2 launch example hand_track_node.launch.py` |
| 目标分类 | `ros2 launch example object_classification.launch.py` |
| 目标抓取 | `ros2 launch example track_and_grab.launch.py` |

### 验证要点

- [ ] 摄像头数据正常
- [ ] 颜色/目标检测准确
- [ ] 机械臂响应视觉反馈

### 无硬件时

可使用：
- USB 摄像头
- 视频文件输入
- ROS bag 回放数据

---

## 第七步：应用功能验证

### 目标

验证完整的上层应用功能。

### 路径

- 应用代码：`src/app/`

### 功能列表与命令

| 功能 | 命令 |
|------|------|
| 巡线 | `ros2 launch app line_following_node.launch.py` |
| 目标跟踪 | `ros2 launch app object_tracking_node.launch.py` |
| 手势控制 | `ros2 launch app hand_gesture_node.launch.py` |
| 雷达避障 | `ros2 launch app lidar_node.launch.py` |

### 验证要点

- [ ] 各功能模块正常运行
- [ ] 传感器数据融合正确
- [ ] 机器人行为符合预期

---

## 第八步：Bringup 启动

### 目标

一键启动机器人的所有核心功能（控制器、传感器、应用），实现完整功能验证。

### 路径

- Bringup 包：`src/xflz_robot_car1/bringup/`

### 涉及文件

| 文件 | 作用 |
|------|------|
| `bringup/bringup.launch.py` | 主启动文件，一键启动所有功能 |
| `bringup/package.xml` | 包定义 |

### 操作命令

```bash
# 一键启动
ros2 launch car1_bringup bringup.launch.py
```

### 启动内容

| 模块 | 说明 |
|------|------|
| 控制器 | 底盘运动控制 |
| 传感器 | 相机、雷达等 |
| 应用 | 巡线、跟踪等功能 |
| Web服务 | rosbridge、视频服务 |

### 验证要点

- [ ] 所有模块正常启动
- [ ] 机器人可响应控制指令
- [ ] 传感器数据正常

---

## 环境变量汇总

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `need_compile` | 编译模式 | `True`（已编译）/ `False`（源码） |
| `ROS_DOMAIN_ID` | ROS域ID | 用于多机器人区分 |

---

## 快速启动命令汇总

```bash
# 1. URDF验证
ros2 launch car1_description display.launch.py

# 2. 运动学测试
ros2 launch car1_kinematics kinematics.launch.py
ros2 run car1_kinematics fk_demo
ros2 run car1_kinematics ik_demo

# 3. 控制器配置
ros2 launch controller controller.launch.py

# 4. SLAM建图
ros2 launch slam slam.launch.py
ros2 launch slam rviz_slam.launch.py

# 5. 导航
ros2 launch navigation rviz_navigation.launch.py
ros2 launch navigation navigation.launch.py map:=map_01

# 6. 视觉功能
ros2 launch example color_detect.launch.py
ros2 launch example color_track_node.launch.py

# 7. 应用功能
ros2 launch app line_following_node.launch.py
ros2 launch app object_tracking_node.launch.py

# 8. Bringup一键启动
ros2 launch car1_bringup bringup.launch.py
```

---

## Gazebo 仿真抓取验证（从易到难）

基于 Gazebo 物理仿真环境，逐步实现机械臂抓取功能。所有代码位于 `simulations/car1_gazebo/` 目录下。

### 验证流程总览

```
Gazebo 基础仿真（已完成）
    ↓
阶段1：固定位置抓取（纯运动学）
    ↓
阶段2：视觉感知 + 坐标变换
    ↓
阶段3：运动规划（避障 + 路径优化）
    ↓
阶段4：闭环控制（视觉伺服）
    ↓
阶段5：多物体分类抓取（完整场景）
```

---

### 阶段 1：固定位置抓取（纯运动学）

#### 目标

在已知物体位置的情况下，完成完整的抓取-放置流程。

#### 路径

- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`
- 运动学参考：`src/xflz_robot_car1/arm/kinematics/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| 正运动学（FK） | 给定关节角度 → 计算末端位置 |
| 逆运动学（IK） | 给定目标位置 → 计算关节角度 |
| 轨迹插值 | 平滑地从当前位置移动到目标位置 |
| JointTrajectoryController | 通过 ros2_control 发送关节轨迹 |

#### 实现步骤

1. 在 Gazebo 中放置一个固定位置的物体（立方体）
2. 编写 IK 求解器（基于已有的解析解方案）
3. 编写抓取序列脚本：
   - 移动到物体上方（pre-grasp）
   - 下降到抓取高度
   - 闭合夹爪
   - 提升物体
   - 移动到目标放置位置
   - 松开夹爪
   - 回到初始位置

#### 涉及文件

| 文件 | 作用 |
|------|------|
| `worlds/grasp_demo.sdf` | 包含桌面和目标物体的仿真世界 |
| `scripts/grasp_demo.py` | 抓取序列控制节点 |
| `launch/grasp_demo.launch.py` | 启动仿真 + 抓取节点 |

#### 验证要点

- [ ] Gazebo 中物体正确生成
- [ ] IK 求解结果正确（末端到达目标位置）
- [ ] 夹爪能稳定夹住物体
- [ ] 物体能被提起并移动到目标位置
- [ ] 放置后物体稳定

---

### 阶段 2：视觉感知 + 坐标变换

#### 目标

通过相机识别物体位置，动态计算抓取目标。

#### 路径

- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| RGB-D 相机 | Gazebo 中模拟深度相机 |
| 物体检测 | HSV 颜色分割 / 深度学习 |
| TF 坐标变换 | camera_frame → base_link → arm_base_link |
| 深度估计 | 从深度图获取物体 3D 位置 |

#### 实现步骤

1. 在 URDF 中添加 RGB-D 相机（如 Realsense D435）
2. 在 Gazebo 中配置相机插件
3. 编写物体检测节点（HSV 颜色分割 + 轮廓检测）
4. 使用 `tf2` 将物体坐标从 camera_frame 转换到 arm_base_link
5. 调用阶段 1 的抓取逻辑

#### 验证要点

- [ ] 相机图像正常发布
- [ ] 物体检测准确（位置误差 < 1cm）
- [ ] 坐标变换正确
- [ ] 能抓取随机位置的彩色物体

---

### 阶段 3：运动规划（避障 + 路径优化）

#### 目标

在有障碍物的环境中安全规划抓取路径。

#### 路径

- MoveIt2 配置：`src/xflz_robot_car1/simulations/car1_moveit_config/`
- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| MoveIt2 | 运动规划框架 |
| RRT/RRT* | 随机采样路径规划算法 |
| PlanningScene | 碰撞检测与场景管理 |
| MoveGroupInterface | MoveIt2 编程接口 |

#### 实现步骤

1. 配置 MoveIt2 与 Gazebo 联合仿真
2. 在 Gazebo 中添加障碍物（桌子、墙壁）
3. 将障碍物同步到 MoveIt2 的 PlanningScene
4. 使用 MoveGroupInterface 规划无碰撞路径
5. 执行规划的轨迹

#### 验证要点

- [ ] MoveIt2 与 Gazebo 控制器正确对接
- [ ] 障碍物正确加载到 PlanningScene
- [ ] 规划路径无碰撞
- [ ] 机械臂按规划路径运动

---

### 阶段 4：闭环控制（视觉伺服）

#### 目标

实时调整抓取姿态，提高抓取成功率和鲁棒性。

#### 路径

- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| IBVS/PBVS | 基于图像/位置的视觉伺服 |
| 实时反馈控制 | 闭环调整末端位姿 |
| 抓取检测 | 夹爪位置反馈判断是否抓取成功 |

#### 实现步骤

1. 在接近物体时切换到视觉伺服模式
2. 实时计算图像误差（物体中心 vs 图像中心）
3. 调整末端位置直到误差 < 阈值
4. 闭合夹爪并检测是否抓取成功（夹爪位置反馈）
5. 如果失败，重新尝试

#### 验证要点

- [ ] 视觉伺服收敛（误差持续减小）
- [ ] 对位置偏差有鲁棒性
- [ ] 抓取成功率 > 90%
- [ ] 失败后能自动重试

---

### 阶段 5：多物体分类抓取（完整场景）

#### 目标

识别多个物体，按类别分类放置到不同区域。

#### 路径

- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| 实例分割 | Mask R-CNN / YOLO |
| 任务规划 | 状态机或行为树 |
| 多目标排序 | 最近优先、颜色优先等策略 |
| 场景状态管理 | 跟踪已抓取/未抓取物体 |

#### 实现步骤

1. 检测场景中所有物体（类别 + 位置）
2. 根据任务需求排序（如"红色放左边，蓝色放右边"）
3. 循环执行抓取-放置
4. 更新场景状态（已抓取的物体从列表移除）
5. 处理异常（物体掉落、抓取失败等）

#### 验证要点

- [ ] 多物体检测准确
- [ ] 分类逻辑正确
- [ ] 能完成"将 5 个不同颜色方块分类放入对应区域"
- [ ] 异常处理有效

---

## 注意事项

1. **编译模式**：使用 `--symlink-install` 可实现源码修改即时生效
2. **硬件依赖**：部分功能（雷达、摄像头、机械臂）需要实际硬件
3. **安全限位**：机械臂关节角度建议设置为最大值的90%~95%
4. **坐标系**：确保 TF 树结构正确，避免定位失败
