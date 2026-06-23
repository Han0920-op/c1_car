# xflz_robot_car1 项目功能清单与目录结构

---

## 项目目录结构

```
xflz_robot_car1/
├── TODO.md                              # 本文件：功能清单与验证指南
├── tutorial.md                          # 教程文档
├── driver/                              # 硬件驱动层（Phase 1）
│   ├── car1_base_driver/                # STM32 板级驱动（串口通信）
│   ├── car1_base_driver_msgs/           # 板级驱动消息/服务定义
│   ├── car1_servo_controller/           # 总线舵机控制器（关节状态 + 轨迹动作）
│   ├── car1_servo_controller_msgs/      # 舵机控制器消息定义
│   ├── car1_chassis_controller/         # 底盘控制（麦轮运动学 + 里程计 + EKF）
│   └── car1_sdk/                        # 工具库（PID、通用函数）
├── peripherals/                         # 传感器集成（Phase 2）
│   └── car1_peripherals/                # 雷达、深度相机、遥控
├── slam/                                # SLAM 建图（Phase 3）
│   └── car1_slam/                       # slam_toolbox 2D 建图
├── navigation/                          # 自主导航（Phase 4）
│   └── car1_navigation/                 # Nav2 导航系统
├── app/                                 # 智能应用（Phase 5）
│   └── car1_app/                        # 巡线、追踪、手势、抓取等
├── arm/                                 # 机械臂相关
│   ├── kinematics/                      # car1_kinematics（正/逆运动学）
│   └── car1_arm_controller/             # 机械臂控制器（高层接口）
├── bringup/                             # 一键启动
│   └── launch/bringup.launch.py         # 主启动文件
└── simulations/                         # 仿真相关
    ├── car1_description/                # URDF 模型
    ├── car1_gazebo/                     # Gazebo 仿真
    └── car1_moveit_config/              # MoveIt2 配置
```

---

## 硬件驱动层（Phase 1）

### 硬件条件

| 项目 | 说明 |
|------|------|
| 下位机 | STM32F407VET6 控制板 |
| 通信方式 | 串口 1Mbps，协议帧：0xAA 0x55 \| Func \| Len \| Data \| CRC8 |
| 底盘 | 4 轮麦克纳姆（轮距 0.1946m，轮宽 0.2117m，轮径 0.097m） |
| 机械臂 | 5-DOF + 夹爪（总线舵机 ID 0~4 + 5） |
| 传感器 | 激光雷达、深度相机（HP60C）、IMU |

### 包依赖关系

```
car1_base_driver_msgs          car1_servo_controller_msgs
         │                              │
         ▼                              ▼
car1_base_driver ──────────▶ car1_servo_controller
         │                              │
         └──────────┬───────────────────┘
                    ▼
         car1_chassis_controller
                    │
                    ▼
              car1_bringup
```

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select \
  car1_base_driver_msgs \
  car1_servo_controller_msgs \
  car1_sdk \
  car1_base_driver \
  car1_servo_controller \
  car1_chassis_controller \
  car1_arm_controller
```

### 启动命令

```bash
# 完整启动（板级驱动 + 底盘控制器 + 舵机控制器）
ros2 launch car1_bringup bringup.launch.py

# 启动机械臂控制器（需要先启动 bringup）
ros2 launch car1_arm_controller arm_controller.launch.py

# 单独启动板级驱动
ros2 launch car1_base_driver base_driver.launch.py

# 单独启动底盘控制器
ros2 launch car1_chassis_controller chassis_controller.launch.py
```

### 验证要点

- [ ] 板级驱动连接 STM32 成功（串口通信正常）
- [ ] IMU 数据正常发布 (`ros2 topic echo /car1_base_driver/imu_raw`)
- [ ] 电机响应 cmd_vel 指令
- [ ] 里程计数据正常 (`ros2 topic echo /odom_raw`)
- [ ] EKF 融合输出正常 (`ros2 topic echo /odometry/filtered`)
- [ ] 舵机关节状态发布 (`ros2 topic echo /joint_states`)
- [ ] MoveIt2 轨迹执行正常（FollowJointTrajectory 动作）
- [ ] 机械臂控制器响应位姿指令
- [ ] 机械臂控制器响应关节指令
- [ ] 夹爪控制正常（张开/闭合）

---

## 机械臂控制（Phase 1.5）

### 功能说明

`car1_arm_controller` 提供高层机械臂控制接口，封装 IK 求解和舵机控制。

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_arm_controller
```

### 启动命令

```bash
# 需要先启动 bringup
ros2 launch car1_bringup bringup.launch.py

# 启动机械臂控制器
ros2 launch car1_arm_controller arm_controller.launch.py

# 运行演示
ros2 run car1_arm_controller arm_demo
```

### 控制接口

**话题**：
- `/arm_controller/target_pose` (geometry_msgs/PoseStamped) - 目标位姿（IK）
- `/arm_controller/joint_command` (sensor_msgs/JointState) - 关节角度指令

**服务**：
- `/arm_controller/set_gripper` (std_srvs/SetBool) - 夹爪控制
- `/arm_controller/go_home` (std_srvs/Trigger) - 回到零位

### 验证要点

- [ ] 机械臂控制器正常启动
- [ ] 关节角度控制响应正常
- [ ] IK 位姿控制响应正常
- [ ] 夹爪开合控制正常
- [ ] 回零位功能正常
- [ ] 演示脚本完整执行

---

## 传感器集成（Phase 2）

### 硬件条件

| 项目 | 说明 |
|------|------|
| 激光雷达 | 国科光芯 COIN-D6，串口 230400，范围 0.01-16m |
| 深度相机 | 安思疆 HP60C，USB，640x480@25fps |
| 遥控方式 | 键盘遥控（麦轮全向运动） |

### 包依赖关系

```
car1_peripherals
    ├── m1ct_d2 (COIN-D6 雷达驱动)
    └── ascamera (HP60C 相机驱动)
```

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_peripherals
```

### 启动命令

```bash
# 启动所有传感器（雷达 + 深度相机）
ros2 launch car1_peripherals peripherals.launch.py

# 单独启动雷达
ros2 launch car1_peripherals lidar.launch.py

# 单独启动深度相机
ros2 launch car1_peripherals depth_camera.launch.py

# 键盘遥控
ros2 launch car1_peripherals teleop_key.launch.py
```

### 验证要点

- [ ] 雷达数据正常发布 (`ros2 topic echo /scan`)
- [ ] 深度相机 RGB 图像正常 (`ros2 topic echo /depth_cam/rgb/image_raw`)
- [ ] 深度相机深度图正常 (`ros2 topic echo /depth_cam/depth/image_raw`)
- [ ] 点云数据正常 (`ros2 topic echo /depth_cam/depth/points`)
- [ ] 键盘遥控响应正常（w/s 前后，a/d 旋转，q/e 平移）

---

## SLAM 建图（Phase 3）

### 功能说明

使用 slam_toolbox 进行 2D 激光 SLAM 建图，支持实时定位与地图保存。

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_slam
```

### 启动命令

```bash
# 启动 SLAM（包含 bringup + 雷达 + slam_toolbox）
ros2 launch car1_slam slam.launch.py

# 启动 RViz 可视化
ros2 launch car1_slam rviz_slam.launch.py

# 保存地图
ros2 run car1_slam map_save map_01
```

### 验证要点

- [ ] slam_toolbox 节点正常启动
- [ ] 地图实时构建（RViz 中可见）
- [ ] 使用键盘遥控建图，地图质量良好
- [ ] 地图保存成功（生成 .pgm 和 .yaml 文件）

---

## 自主导航（Phase 4）

### 功能说明

基于 Nav2 的自主导航系统，支持 AMCL 定位、ThetaStar 全局规划、TEB 局部规划（全向运动）。

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_navigation
```

### 启动命令

```bash
# 启动导航（需指定地图文件）
ros2 launch car1_navigation navigation.launch.py map:=map_01

# 启动 RViz 导航可视化
ros2 launch car1_navigation rviz_navigation.launch.py
```

### 验证要点

- [ ] 地图加载成功
- [ ] AMCL 定位正常（机器人位姿与地图对齐）
- [ ] 在 RViz 中设置导航目标，机器人能自主规划路径
- [ ] 机器人能避障并到达目标点
- [ ] 麦轮全向运动正常（可横向平移）

---

## 智能应用（Phase 5）

### 功能列表

| 应用 | 功能 | 传感器 |
|------|------|--------|
| line_following | 巡线行驶 | 深度相机 RGB |
| object_tracking | 颜色目标追踪 | 深度相机 RGB |
| hand_gesture | 手势控制底盘 | 深度相机 RGB |
| lidar_controller | 雷达避障 | COIN-D6 雷达 |
| track_and_grab | 视觉识别+IK抓取 | 深度相机 RGB+Depth |

### 编译命令

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_app
```

### 启动命令

```bash
# 巡线
ros2 launch car1_app line_following.launch.py

# 颜色追踪
ros2 launch car1_app object_tracking.launch.py

# 手势控制
ros2 launch car1_app hand_gesture.launch.py

# 雷达避障
ros2 launch car1_app lidar_controller.launch.py

# 视觉抓取
ros2 launch car1_app track_and_grab.launch.py
```

### 验证要点

- [ ] 巡线：机器人能沿黑线行驶
- [ ] 颜色追踪：机器人能跟随指定颜色物体
- [ ] 手势控制：手势识别正常，底盘响应手势指令
- [ ] 雷达避障：检测到障碍物时自动避障
- [ ] 视觉抓取：识别目标物体，机械臂自动抓取

---

## 仿真功能验证（已实现）

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

- 控制器代码：`src/xflz_robot_car1/driver/car1_chassis_controller/`

### 涉及文件

| 文件 | 作用 |
|------|------|
| `config/ekf.yaml` | 扩展卡尔曼滤波配置 |
| `config/init_pose.yaml` | 机器人初始位置 |
| `launch/chassis_controller.launch.py` | 底盘控制器启动 |

### 操作命令

```bash
# 启动底盘控制器（包含在 bringup 中）
ros2 launch car1_bringup bringup.launch.py

# 或单独启动
ros2 launch car1_chassis_controller chassis_controller.launch.py
```

### 验证要点

- [ ] 机器人可响应运动指令 (`ros2 topic pub /controller/cmd_vel ...`)
- [ ] 里程计数据正常发布 (`ros2 topic echo /odom_raw`)
- [ ] EKF 融合输出正常 (`ros2 topic echo /odometry/filtered`)
- [ ] 坐标系变换正确 (`ros2 run tf2_tools view_frames`)

---

## 第四步：传感器集成（Phase 2）

### 目标

验证激光雷达和深度相机数据正常发布。

### 路径

- 传感器包：`src/xflz_robot_car1/peripherals/car1_peripherals/`

### 操作命令

```bash
# 启动所有传感器
ros2 launch car1_peripherals peripherals.launch.py

# 键盘遥控
ros2 launch car1_peripherals teleop_key.launch.py
```

### 验证要点

- [ ] 雷达数据正常 (`ros2 topic echo /scan`)
- [ ] 深度相机图像正常 (`ros2 topic echo /depth_cam/rgb/image_raw`)
- [ ] 键盘遥控响应正常

---

## 第五步：SLAM 建图（Phase 3）

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

## 第六步：导航验证（Phase 4）

### 目标

验证机器人能够使用已有地图进行自主导航。

### 路径

- 导航包：`src/xflz_robot_car1/navigation/car1_navigation/`

### 操作命令

```bash
# 2D 导航
ros2 launch car1_navigation navigation.launch.py map:=map_01
ros2 launch car1_navigation rviz_navigation.launch.py
```

### 验证要点

- [ ] 地图加载成功
- [ ] 定位正常（机器人模型与地图对齐）
- [ ] 路径规划正常
- [ ] 导航目标可正常下达
- [ ] 麦轮全向运动正常

---

## 第七步：智能应用验证（Phase 5）

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
# 0. 硬件驱动层（Phase 1）
ros2 launch car1_bringup bringup.launch.py

# 0.5 机械臂控制器（Phase 1.5）
ros2 launch car1_arm_controller arm_controller.launch.py
ros2 run car1_arm_controller arm_demo

# 1. URDF验证
ros2 launch car1_description display.launch.py

# 2. 运动学测试
ros2 launch car1_kinematics kinematics.launch.py
ros2 run car1_kinematics fk_demo
ros2 run car1_kinematics ik_demo

# 3. 传感器集成（Phase 2）
ros2 launch car1_peripherals peripherals.launch.py
ros2 launch car1_peripherals teleop_key.launch.py

# 4. SLAM建图（Phase 3）
ros2 launch car1_slam slam.launch.py
ros2 launch car1_slam rviz_slam.launch.py
ros2 run car1_slam map_save map_01

# 5. 导航（Phase 4）
ros2 launch car1_navigation navigation.launch.py map:=map_01
ros2 launch car1_navigation rviz_navigation.launch.py

# 6. 智能应用（Phase 5）
ros2 launch car1_app line_following.launch.py
ros2 launch car1_app object_tracking.launch.py
ros2 launch car1_app hand_gesture.launch.py
ros2 launch car1_app lidar_controller.launch.py
ros2 launch car1_app track_and_grab.launch.py

# 7. Gazebo 仿真
ros2 launch car1_gazebo gazebo_arm.launch.py
ros2 launch car1_gazebo grasp_demo.launch.py
ros2 launch car1_gazebo grasp_demo_vision.launch.py
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

通过深度相机识别红色立方体位置，动态计算抓取目标并执行抓取。

#### 路径

- 仿真代码：`src/xflz_robot_car1/simulations/car1_gazebo/`

#### 涉及技术

| 技术 | 说明 |
|------|------|
| RGB-D 相机 | Gazebo 中模拟安思疆 HP60C 深度相机 |
| 物体检测 | HSV 颜色分割 + 轮廓检测 |
| TF 坐标变换 | camera_depth_link → base_link |
| 深度定位 | 像素坐标 + 深度图 → 3D 坐标 |

#### 涉及文件

| 文件 | 作用 |
|------|------|
| `urdf/car1.gazebo.xacro` | 深度相机 Gazebo 传感器插件 |
| `launch/grasp_demo_vision.launch.py` | 视觉抓取启动文件 |
| `scripts/object_detector.py` | HSV 颜色检测 + 3D 定位节点 |
| `scripts/grasp_demo_vision.py` | 视觉引导抓取控制节点 |

#### 编译与运行

```bash
# 编译
colcon build --packages-select car1_gazebo car1_description

# 运行（默认立方体在 x=0.25, y=0.0）
ros2 launch car1_gazebo grasp_demo_vision.launch.py

# 指定立方体位置
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.22 cube_y:=0.03
```

#### 分层验证

**第1层：相机话题**

```bash
# 检查话题是否发布
ros2 topic list | grep camera
# 期望: /camera/image, /camera/depth, /camera/points, /camera/camera_info

# 检查帧率
ros2 topic hz /camera/image
# 期望: ~10-20 Hz
```

**第2层：图像可视化**

```bash
# 启动 rviz2，添加：
# - Image display → /camera/image（能看到红方块）
# - Image display → /detection_image（能看到绿色检测框）
# - PointCloud2 display → /camera/points
```

**第3层：物体检测**

```bash
# 检查检测结果
ros2 topic echo /detected_object_pose
# 期望: 输出 PoseStamped，position 接近物体实际位置

# 可视化标记（rviz2 中添加 Marker display → /detected_object_marker）
```

**第4层：动态抓取**

```bash
# 默认位置自动抓取
ros2 launch car1_gazebo grasp_demo_vision.launch.py

# 不同位置测试（3个位置，要求 3/3 成功）
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.25 cube_y:=0.0
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.22 cube_y:=0.03
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.20 cube_y:=-0.03
```

#### 故障定位

| 现象 | 检查命令 | 修复方向 |
|------|----------|----------|
| 无相机话题 | `ros2 topic list` | 检查 Gazebo 传感器插件是否加载、ros_gz_bridge 是否运行 |
| 图像全黑 | rviz2 Image display | 检查 sensor update_rate 和 clip near/far |
| 物体检测不到 | `ros2 run rqt_image_view rqt_image_view` 查看 /camera/image | 调整 object_detector.py 中 HSV 阈值 |
| 检测坐标跳动 | `ros2 topic hz /camera/depth` | 增大 depth_region_size 或加中值滤波 |
| 坐标明显偏移 | `ros2 run tf2_ros tf2_echo base_link camera_depth_link` | 检查 TF 链和相机内参 |
| 机械臂到达但没抓到 | `ros2 topic echo /detected_object_pose` | 检查深度 z 值是否合理，IK 参数 |
| 机械臂方向错误 | 对比 /detected_object_pose 与 Gazebo 实际位置 | 检查 base_footprint z 偏移和 IK 参数 |
| 抓取超时 | 查看日志 "超时，未检测到物体" | 确认立方体在相机视野和机械臂可达范围内 |

#### 验证要点

- [ ] 相机图像正常发布 (>10Hz)
- [ ] 物体检测准确（位置误差 < 1cm）
- [ ] 坐标变换正确（camera_depth_link → base_link）
- [ ] 能抓取默认位置的红色立方体
- [ ] 能抓取不同位置 (cube_x, cube_y 参数) 的立方体

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

---

## 借鉴 lander_pi 的建图导航优化计划（2026-06-23）

> 基于对 lander_pi 参考栈的深度分析,发现 car1 在校准机制、传感器配置、控制器架构等方面存在多项可优化点。
> 本节详细记录需要实施的优化项,按优先级分为 P0(必须)、P1(强烈建议)、P2(可选)三级。

### 优化背景

**当前问题诊断**（2026-06-23 SLAM 调试）:
- ✅ 机械臂抖动 → 已修复(删除冲突的 joint_state_publisher)
- ✅ 轮子显示异常 → 已修复(补齐缺失的轮子关节)
- ✅ robot_state_publisher 重复 → 已修复(统一单入口 slam.launch.py)
- ✅ slam_toolbox 延迟不足 → 已修复(3s → 10s)
- ❓ **静止时 odom 有 ~3.8° yaw 偏置** → 待定(可能是里程计角度系数未标定)
- ❓ **激光点云可能有轻微偏移** → 待定(需运动测试确认是 odom 漂移还是自遮挡)

**lander_pi 与 car1 核心差异对比**:

| 维度 | lander_pi | car1 | 差距 |
|------|-----------|------|------|
| **IMU 校准** | ✅ SM 矩阵 + bias 向量校准 | ❌ 完全未校准 | **关键缺失** |
| **里程计标定** | ✅ 实际标定值(linear=0.94) | ❌ 默认值 1.0(未标定) | **关键缺失** |
| **laser_filters** | ✅ 5种雷达配置 | ❌ 无 | **缺失** |
| **EKF 协方差动态** | ✅ 运动/静止两套 | ❌ 固定不变 | 可优化 |
| **地图保存服务** | ✅ 独立节点 | ❌ 手动 CLI | 便利性 |

---

### 🔴 P0 级优化（必须做,解决当前问题）

#### P0-1: 里程计标定（解决 3.8° yaw 偏置）

**问题**: 当前 `calibrate_params.yaml` 全是默认值 1.0,相当于从未标定。这很可能就是静止时 yaw 有固定偏置、运动时墙重影的根本原因。

**lander_pi 实际值**: `linear_correction_factor: 0.94`, `angular_correction_factor: 1.00`

**实施步骤**:

**第一步：线性标定（往返法 + 尺子测量）**

```bash
# === 终端 1: 启动底盘 ===
ros2 launch car1_bringup bringup.launch.py

# === 终端 2: 启动标定节点 ===
ros2 run calibration calibrate_linear

# === 终端 3: 启动参数调节界面 ===
rqt
# Plugins → Configuration → Dynamic Reconfigure → calibrate_linear
```

**标定流程（往返法）**:

1. **标记起点**
   - 用胶带/粉笔在地上标记小车中心初始位置（十字标记）

2. **第一次往返测试（系数 1.0）**
   ```bash
   # rqt 参数设置:
   # - test_distance: 1.0
   # - odom_linear_scale_correction: 1.0
   # - speed: 0.2
   # - 勾选 start_test → 小车前进 1m 停止
   
   # 切换方向倒车:
   # - test_distance: -1.0
   # - 勾选 start_test → 小车倒退 1m 停止
   ```

3. **用尺子测量偏差**
   - 小车停稳后，用尺子测量：车中心 到 起点十字标记 的距离
   - 例如：偏差 = 8cm（在标记后方）

4. **计算修正系数**
   ```
   单程误差 = 往返偏差 / 2 = 8 / 2 = 4cm
   实际走了 = 100 - 4 = 96cm（以为是100cm）
   修正系数 = 100 / 96 ≈ 1.042
   ```

5. **第二次往返验证（系数 1.042）**
   ```bash
   # 推车回起点十字标记
   # rqt: odom_linear_scale_correction = 1.042
   # 重复前进+倒退
   # 用尺子测量偏差，应该 < 2cm
   ```

6. **记录最终系数**（例如：1.042）

---

**第二步：角度标定（手机指南针 + 3次测量取中位数）**

```bash
# === 终端 2: 切换到角度标定 ===
# 按 Ctrl+C 停止 calibrate_linear
ros2 run calibration calibrate_angular

# === rqt 会自动刷新，切换到 calibrate_angular ===
```

**准备工作**:
1. 打开手机指南针 APP（iOS 自带"测距仪"或 Android "Compass"）
2. 校准指南针（按提示转动手机画"8"字）
3. 用胶带/橡皮筋把手机固定在车顶中央（或拿在手上贴着车头）

**标定流程（3次测量法）**:

| 次数 | 操作 | 记录 |
|------|------|------|
| **第1次** | rqt: test_angle=360, 系数=1.0, start_test<br>记录: 起始角度(如45°) → 结束角度(如28°) | 偏差 = 28-45 = **-17°** |
| **第2次** | 不动手机，再次 start_test<br>记录: 起始(28°) → 结束(如11°) | 偏差 = 11-28 = **-17°** |
| **第3次** | 再次 start_test<br>记录: 起始(11°) → 结束(如-6° 或 354°) | 偏差 = -6-11 = **-17°** |

**数据分析**:
```
3次偏差: -17°, -17°, -17° (一致性好)
取中位数: -17°

实际转角 = 360 + (-17) = 343°
修正系数 = 360 / 343 ≈ 1.050
```

**角度换算技巧**（跨越0°时）:
```python
# 如果直接相减结果 > 180° 或 < -180°，需要修正:
偏差 = (结束 - 起始 + 180) % 360 - 180

例如: 起始10°, 结束350°
偏差 = (350 - 10 + 180) % 360 - 180 = -20° (逆时针少转了20°)
```

**验证测试**:
```bash
# rqt: odom_angular_scale_correction = 1.050
# 再测 1 次，偏差应该 < 2°
```

---

**第三步：保存标定结果**

```bash
nano ~/ros2_ws/src/xflz_eai_car1/driver/controller/config/calibrate_params.yaml

# 修改为实测值:
/**:
  ros__parameters:
    linear_correction_factor: 1.042   # 你的线性系数
    angular_correction_factor: 1.050  # 你的角度系数

# 保存后重启
# 终端1 Ctrl+C
ros2 launch car1_bringup bringup.launch.py
```

---

**第四步：验证效果**

```bash
# 1. 静止 yaw 偏置测试
ros2 run tf2_ros tf2_echo odom base_footprint
# 观察 yaw 值，应该从 3.8° 降到 < 0.5°

# 2. 键盘遥控测试
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# - 前进2-3米，观察轨迹是否笔直
# - 原地转圈，观察是否回到起点朝向

# 3. SLAM 运动测试（判断是否需要 laser_filters）
ros2 launch car1_slam slam.launch.py
# 用键盘遥控直行1-2m + 原地转360°
# 盯着 RViz 里的墙:
# - 墙重影/糊开 → odom 标定不够准，继续微调
# - 墙清晰但机身附近有固定点 → 需要 P0-2: laser_filters
```

---

**注意事项**:

1. **往返法技巧**:
   - 如果倒车功能不可用（test_distance=-1.0 不响应），改用单程重复测试
   - 只测前进，手动推车回起点，多次测试看是否停在同一位置

2. **尺子测量技巧**:
   - 测量车中心到标记的距离（不是车头/车尾）
   - 如果偏差很小（<1cm），说明已经很准

3. **手机指南针技巧**:
   - 手机要远离电机（放车后部）避免磁干扰
   - 等小车完全停稳（5-10秒）再读数
   - 如果3次偏差相差>5°，说明地面打滑或磁干扰，需降速或换地面

4. **系数调整经验**:
   - 第一次粗调：按10%步长（0.9, 1.0, 1.1）
   - 接近目标后：按5%步长（1.05, 1.10）
   - 最后精调：按2%步长（1.08, 1.10）

**预期效果**:
- 静止时 yaw 偏置显著减少(< 0.5°)
- 运动时墙单层清晰,不重影
- SLAM 建图质量提升

**时间估计**: 30 分钟

**涉及文件**:
- `driver/controller/config/calibrate_params.yaml`
- `calibration/calibration/calibrate_linear.py`
- `calibration/calibration/calibrate_angular.py`

---

#### P0-2: laser_filters 集成（如需要,解决自遮挡）

**前置判断**: 先完成 P0-1 标定,再做**运动测试**判断是否需要。

**运动测试方法**:
```bash
# SLAM 运行中,用键盘遥控小车直行 1-2m 再原地转 360°
ros2 launch car1_slam slam.launch.py
# 新终端
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 盯着 RViz 里的墙:
# - 墙重影/糊开 → 是 odom 漂移,P0-1 解决
# - 墙清晰但机身附近有固定点跟着转 → 是自遮挡,需要 laser_filters
```

**如果确认需要 laser_filters**:

1. **安装软件包**
   ```bash
   sudo apt install ros-humble-laser-filters
   ```

2. **实测标定过滤角度**（**不能直接搬 lander_pi 数值**）
   
   lander_pi 用的是 0~2π 约定,COIN-D6 用的是 -π~π 约定,直接搬数值会错。
   
   ```bash
   # 启动雷达,对着空旷处
   ros2 launch car1_peripherals lidar.launch.py
   
   # 新终端,实时查看雷达数据
   ros2 topic echo /scan
   
   # 手动遮挡机身不同方向(后方/左后/右后),观察:
   # - 哪些角度索引的 ranges 值异常近(<0.2m)
   # - 记录这些索引,换算成弧度(-π~π)
   
   # 例如:索引 180-540(共 720 点) 有异常近距离读数
   # 换算:180/720*2π - π ≈ 0.57 rad
   #      540/720*2π - π ≈ 2.71 rad
   ```

3. **创建配置文件**
   ```bash
   # 已存在占位文件,需根据实测修改
   nano peripherals/car1_peripherals/config/laser_filters.yaml
   ```
   
   ```yaml
   /**:
     ros__parameters:
       filter1:
         name: angular_bounds_filter
         type: laser_filters/LaserScanAngularBoundsFilterInPlace
         params:
           lower_angle: 0.57   # 实测得出的起始角度(弧度)
           upper_angle: 2.71   # 实测得出的结束角度
       
       filter2:
         name: range_filter
         type: laser_filters/LaserScanRangeFilter
         params:
           use_message_range_limits: false
           lower_threshold: 0.10  # 忽略 <10cm 的点(肯定是机身)
           upper_threshold: 16.0
           lower_replacement_value: .nan
           upper_replacement_value: .inf
   ```

4. **集成到 lidar.launch.py**
   
   参照 lander_pi 的实现,在 `peripherals/car1_peripherals/launch/lidar.launch.py` 添加:
   
   ```python
   laser_filter_node = Node(
       package='laser_filters',
       executable='scan_to_scan_filter_chain',
       name='laser_filter',
       parameters=[os.path.join(peripherals_pkg, 'config', 'laser_filters.yaml')],
       remappings=[
           ('scan', 'scan_raw'),           # 输入:原始雷达数据
           ('scan_filtered', 'scan')       # 输出:过滤后数据
       ]
   )
   ```

5. **重启验证**
   ```bash
   # 重新编译(如果改了 launch)
   colcon build --packages-select car1_peripherals
   
   # 重启 SLAM
   ros2 launch car1_slam slam.launch.py
   
   # 观察 RViz,机身附近的固定假障碍应消失
   ```

**预期效果**:
- 机身附近不再有跟着车转的固定点云
- 地图中不再出现不存在的"假墙"
- 建图更准确

**时间估计**: 1-2 小时(含实测标定)

**涉及文件**:
- `peripherals/car1_peripherals/config/laser_filters.yaml`
- `peripherals/car1_peripherals/launch/lidar.launch.py`

---

### 🟡 P1 级优化（强烈建议,提升稳定性）

#### P1-1: IMU 偏置估计（简化方案）

**问题**: 当前 IMU 未校准,零偏和刻度误差会被 EKF 积分,导致姿态漂移。

**lander_pi 完整方案**: 用转台或 6 面静置法生成 SM 矩阵 + bias 向量,通过 `imu_calib` 节点先矫正再滤波。这需要专业工具,难度高。

**car1 简化方案**: 启用 Madgwick 滤波器的**自动偏置估计**功能。

**实施步骤**:

1. **修改 IMU 滤波器配置**
   
   编辑 `driver/controller/launch/chassis_controller.launch.py`:
   
   ```python
   imu_filter_node = Node(
       package='imu_filter_madgwick',
       executable='imu_filter_madgwick_node',
       name='imu_filter',
       parameters=[{
           'use_mag': False,
           'publish_tf': False,
           'world_frame': 'enu',
           'fixed_frame': 'base_link',
           'do_bias_estimation': True,     # 新增:启用偏置估计
           'bias_alpha': 0.01,              # 新增:偏置估计滤波系数
       }],
       remappings=[
           ('imu/data_raw', 'car1_base_driver/imu_raw'),
           ('imu/data', 'imu'),
       ],
       output='screen'
   )
   ```

2. **重新编译**
   ```bash
   colcon build --packages-select controller
   ```

3. **重启验证**
   ```bash
   # 重启 bringup
   ros2 launch car1_bringup bringup.launch.py
   
   # 查看 IMU 数据,静止时角速度应更接近 0
   ros2 topic echo /imu --once
   ```

**预期效果**:
- 滤波器自动学习并补偿陀螺零偏
- 静止时姿态更稳定
- 运动时累积误差减小

**效果评估**:
- 不如 SM 矩阵校准,但比完全不校准好很多
- 适合对精度要求不极端的场景

**时间估计**: 5 分钟

**涉及文件**:
- `driver/controller/launch/chassis_controller.launch.py`

---

#### P1-2: EKF 协方差动态调整

**问题**: 当前 EKF 的协方差矩阵固定不变,无法根据运动状态调整对里程计/IMU 的信任度。

**lander_pi 方案**: 针对运动/静止两种状态设置不同的协方差:
- 运动时:里程计置信度正常
- 静止时:里程计置信度极高(1e-9),强制 EKF 相信"车没动",抑制 IMU 漂移

**实施步骤**:

1. **修改 odom_publisher**
   
   编辑 `driver/controller/controller/odom_publisher_node.py`:
   
   在文件开头添加静止时的协方差常量:
   
   ```python
   ODOM_POSE_COVARIANCE_STOP = [
       1e-9, 0, 0, 0, 0, 0,
       0, 1e-9, 0, 0, 0, 0,
       0, 0, 1e6, 0, 0, 0,
       0, 0, 0, 1e6, 0, 0,
       0, 0, 0, 0, 1e6, 0,
       0, 0, 0, 0, 0, 1e-9
   ]
   
   ODOM_TWIST_COVARIANCE_STOP = [
       1e-9, 0, 0, 0, 0, 0,
       0, 1e-9, 0, 0, 0, 0,
       0, 0, 1e6, 0, 0, 0,
       0, 0, 0, 1e6, 0, 0,
       0, 0, 0, 0, 1e6, 0,
       0, 0, 0, 0, 0, 1e-9
   ]
   ```
   
   在 `_publish_odom()` 方法中,发布前添加判断:
   
   ```python
   # 判断是否静止(线速度和角速度都接近 0)
   if abs(self.linear_x) < 0.01 and abs(self.angular_z) < 0.01:
       self.odom_msg.pose.covariance = ODOM_POSE_COVARIANCE_STOP
       self.odom_msg.twist.covariance = ODOM_TWIST_COVARIANCE_STOP
   else:
       self.odom_msg.pose.covariance = ODOM_POSE_COVARIANCE
       self.odom_msg.twist.covariance = ODOM_TWIST_COVARIANCE
   ```

2. **重新编译**
   ```bash
   colcon build --packages-select controller --symlink-install
   ```

3. **重启验证**
   ```bash
   ros2 launch car1_bringup bringup.launch.py
   
   # 查看静止时的 odom 协方差
   ros2 topic echo /odom_raw --once | grep covariance
   ```

**预期效果**:
- 静止时 yaw 漂移进一步减小
- EKF 对静止状态的判断更准确

**时间估计**: 10 分钟

**涉及文件**:
- `driver/controller/controller/odom_publisher_node.py`

---

### 🟢 P2 级优化（可选,锦上添花）

#### P2-1: 地图保存服务节点

**当前方式**: 手动运行 CLI 命令
```bash
cd ~/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps
ros2 run nav2_map_server map_saver_cli -f "map_01" --ros-args -p map_subscribe_transient_local:=true
```

**lander_pi 方式**: 提供 ROS 服务接口,可通过 `ros2 service call` 或 RViz 插件保存。

**实施步骤**:

1. **创建地图保存节点**
   
   创建文件 `slam/car1_slam/car1_slam/map_save.py`:
   
   ```python
   #!/usr/bin/env python3
   import os
   import rclpy
   from rclpy.node import Node
   from std_srvs.srv import Trigger
   
   class MapSaveNode(Node):
       def __init__(self):
           super().__init__('map_save_node')
           self.create_service(Trigger, '~/save_map', self.save_map_callback)
           self.get_logger().info('Map save service ready')
       
       def save_map_callback(self, request, response):
           self.get_logger().info('Saving map...')
           map_dir = os.path.expanduser('~/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps')
           cmd = f'cd {map_dir} && ros2 run nav2_map_server map_saver_cli -f "map_01" --ros-args -p map_subscribe_transient_local:=true'
           ret = os.system(cmd)
           
           response.success = (ret == 0)
           response.message = 'Map saved successfully' if ret == 0 else 'Failed to save map'
           return response
   
   def main():
       rclpy.init()
       node = MapSaveNode()
       rclpy.spin(node)
       rclpy.shutdown()
   
   if __name__ == '__main__':
       main()
   ```

2. **修改 setup.py**
   
   在 `slam/car1_slam/setup.py` 的 `console_scripts` 中添加:
   
   ```python
   'map_save = car1_slam.map_save:main',
   ```

3. **重新编译**
   ```bash
   colcon build --packages-select car1_slam
   ```

4. **使用方式**
   ```bash
   # SLAM 运行中,新终端
   ros2 service call /map_save_node/save_map std_srvs/srv/Trigger
   ```

**预期效果**:
- 保存地图更方便
- 可集成到 GUI 或脚本中

**时间估计**: 20 分钟

**涉及文件**:
- `slam/car1_slam/car1_slam/map_save.py` (新建)
- `slam/car1_slam/setup.py`

---

#### P2-2: IMU SM 矩阵校准（完整方案,高精度需求）

**适用场景**: 对姿态精度要求极高的应用(如长时间 SLAM、多传感器融合)。

**前置条件**: 需要专业设备(三轴转台或精密水平台)。

**参考 lander_pi 实现**:
- 校准文件: `calibration/config/imu_calib.yaml`
- 校准节点: `imu_calib` (apply_calib)
- 滤波器: `imu_complementary_filter`

**SM 矩阵含义**:
```yaml
SM:  # 3x3 Scale-Misalignment 矩阵
  - 1.0028  -0.0108   0.0078    # 校正刻度误差和轴间串扰
  - -0.0020  1.0047  -0.0339
  - -0.0183 -0.0083   1.0035
bias:  # 零偏向量
  - 0.0505   0.2005  -0.0975
```

**校准方法**:
1. 六面静置法:IMU 每个面朝上静置 10 分钟,记录数据
2. 转台法:用三轴转台旋转 IMU,记录角速度
3. 用标定算法(如 Allan 方差)计算 SM 矩阵和 bias

**移植 lander_pi imu_calib**:
1. 复制 `imu_calib` 包到 car1 工作区
2. 修改话题 remap:`/ros_robot_controller/imu_raw` → `/car1_base_driver/imu_raw`
3. 生成 `imu_calib.yaml`(需专业工具)
4. 在 `chassis_controller.launch.py` 中插入 `imu_calib` 节点

**时间估计**: 数小时到数天(取决于设备和经验)

---

### 优化实施顺序建议

```
第 1 天(核心问题):
  1. P0-1: 里程计标定(30 分钟)
  2. 运动测试,判断是否需要 laser_filters
  3. 如需要,P0-2: laser_filters 集成(1-2 小时)

第 2 天(稳定性提升):
  4. P1-1: IMU 偏置估计(5 分钟)
  5. P1-2: EKF 协方差动态(10 分钟)
  6. 完整建图测试,验证效果

第 3 天(可选,按需):
  7. P2-1: 地图保存服务(20 分钟)
  8. P2-2: IMU SM 校准(如有设备和需求)
```

---

### 验收标准

**P0 级验收**:
- [ ] 里程计标定完成,`calibrate_params.yaml` 有实际值
- [ ] 静止时 odom yaw 偏置 < 0.5°
- [ ] 直行 1m 误差 < 3cm
- [ ] 原地转 360° 误差 < 5°
- [ ] 运动时墙不重影(或 laser_filters 后机身附近无假障碍)

**P1 级验收**:
- [ ] IMU 偏置估计启用,静止时角速度 < 0.001 rad/s
- [ ] EKF 协方差动态调整生效,静止时协方差为 1e-9

**P2 级验收**:
- [ ] 地图保存服务可调用
- [ ] (如做)IMU SM 校准文件存在且生效

---

### 相关代码参考

**lander_pi 关键文件**:
- 里程计标定: `src/lander_pi/calibration/calibration/calibrate_linear.py`, `calibrate_angular.py`
- IMU 校准: `src/lander_pi/calibration/config/imu_calib.yaml`
- IMU 滤波: `src/lander_pi/peripherals/launch/imu_filter.launch.py`
- laser_filters: `src/lander_pi/peripherals/config/lidar_filters_config_ld19.yaml`
- EKF 协方差: `src/lander_pi/driver/controller/controller/odom_publisher_node.py` (L16-46)
- 地图保存: `src/lander_pi/slam/slam/map_save.py`

**car1 待修改文件**:
- `driver/controller/config/calibrate_params.yaml`
- `driver/controller/launch/chassis_controller.launch.py`
- `driver/controller/controller/odom_publisher_node.py`
- `peripherals/car1_peripherals/config/laser_filters.yaml`
- `peripherals/car1_peripherals/launch/lidar.launch.py`
- `slam/car1_slam/car1_slam/map_save.py` (新建)

---

## 实机机械臂抓取实施计划（从简单到复杂）

> 参考 lander_pi 的实现路径，逐步实现实机机械臂抓取功能。
> 每个 Level 在前一个 Level 验证通过后再开始。

### 实施流程总览

```
Level 1: 运动学基础（纯计算验证）
    ↓
Level 2: 动作组控制（YAML 预录制动作回放）
    ↓
Level 3: IK 分步抓取（安全的实机 IK 控制）
    ↓
Level 4: 视觉 + IK 抓取（相机识别 + 自动抓取）
    ↓
Level 5: 导航 + 视觉 + 抓取（全自主任务）
```

---

### Level 1：运动学基础（纯计算验证）

#### 目标

验证 IK/FK 求解正确，补充角度↔PWM 转换，确保后续控制的数学基础正确。

#### 当前状态

- [x] `fk_demo.py` — 正运动学正解
- [x] `ik_demo.py` — 逆运动学解析解
- [x] `interactive_ik_test.py --direct` — 交互式 IK 测试（直连串口，实时计算+发送）
- [x] `angle2pulse` / `pulse2angle` 转换函数
- [x] IK 求解结果与实际舵机 PWM 的对应关系验证

#### 核心组件（已完成）

**1. Transform 模块** (`arm/kinematics/kinematics/transform.py`)
- ✅ PWM ↔ 角度转换函数：`pulse2angle()`, `angle2pulse_single()`, `pwm_array_to_angles()`, `angles_to_pwm_array()`
- ✅ 参数：270° 舵机，center=1500，PWM_TO_RAD=0.002356，direction=+1，offset=0
- ✅ TCP_OFFSET_Z = 0.0762m（tcp_link 相对 arm_link5）
- ✅ 限位检查：`check_pwm_limits()`, `check_angle_limits()`

**2. IK 求解器** (`arm/kinematics/kinematics/ik_analytical.py`)
- ✅ 解析解 IK（固定/自动/忽略俯仰角三种模式）
- ✅ `solution_to_pwm()` — 直接输出 PWM 值（集成 transform 层）
- ✅ `solution_to_dict()` — 输出关节角度字典

**3. Safe Arm Controller** (`arm/car1_arm_controller/car1_arm_controller/arm_controller.py`)
- ✅ `move_to_pose(x, y, z, pitch)` — 通过 `/arm_controller/target_pose` 话题
- ✅ `set_gripper(close)` — `/arm_controller/set_gripper` 服务
- ✅ `go_home()` — `/arm_controller/go_home` 服务
- ✅ `emergency_stop()` — `/arm_controller/emergency_stop` 服务
- ✅ `pick()` / `place()` — 高层抓取/放置服务
- ✅ `_move_stepwise()` — 分步移动（底座先转，臂后动）
- ✅ `_check_limits()` — 关节限位检查
- ✅ `_wait()` — 可中断等待（响应 emergency stop）

**4. 验证工具** (`arm/kinematics/kinematics/interactive_ik_test.py`)
- ✅ 交互式 IK 测试（输入目标 → IK 求解 → 显示 PWM → 可选发送）
- ✅ 两种模式：ROS2 模式（需 bringup）/ 直连串口模式（`--direct`）
- ✅ FK 验证（计算位置 vs 目标位置，误差检查）
- ✅ 闭环验证（发送后读取实际 PWM，对比目标）
- ✅ 覆盖 TODO 原 Phase 1-3 的全部验证功能

#### 验证方法

**使用 `interactive_ik_test.py` 进行完整验证**

此工具已集成 Phase 1-3 的所有验证功能，一站式完成：

```bash
cd ~/ros2_ws/src/xflz_robot_car1/arm/kinematics/kinematics

# ROS2 模式（需先启动 bringup）
ros2 launch car1_bringup bringup.launch.py
# 新终端
python3 interactive_ik_test.py

# 直连串口模式（需先停掉 bringup）
sudo chmod 666 /dev/ttyUSB0
python3 interactive_ik_test.py --direct
```

**测试流程**：
1. 输入目标 TCP 位置 (x, y, z) 和俯仰角
2. 自动计算 IK 解，显示关节角度和 PWM 值
3. FK 验证：显示计算位置 vs 目标位置的误差（应 < 1.5mm）
4. 限位检查：自动检查 PWM 是否在 500-2500 安全范围内
5. 确认后发送到实机执行
6. 读取舵机实际 PWM，对比目标 PWM（闭环验证）

**Phase 1: Transform 层验证** ✅
- 输入 PWM [1500, 1500, 1500, 1500, 1500]，验证角度全为 0
- 输入 PWM [1500, 1850, 2109, 1850, 1500]，验证角度转换正确
- 往返转换（PWM → 角度 → PWM）误差为 0

**Phase 2: IK 闭环验证** ✅
- 输入多个测试位置（如 [0.25, 0.0, 0.15]）
- IK 求解 → PWM → 发送 → 读取实际 PWM → 对比误差
- FK 验证误差 < 1.5mm

**Phase 3: 已知点验证** ✅
- 在桌面放置物理标记（用尺子测量坐标）
- 输入标记坐标，机械臂移动到该位置
- 人工目测 tcp_link 是否到达标记点

**Phase 4: 完整抓取序列** ✅
- 使用 `arm_controller` 的 `/arm_controller/pick` 和 `/arm_controller/place` 服务
- 或直接调用 `interactive_ik_test.py` 测试关键位置

#### 验证要点

- [x] **Transform 层准确**：PWM → 角度 → FK 计算的 tcp_link 位置与实际一致（误差<2cm）
- [x] **IK 控制准确**：目标 tcp_link 位置 → IK → PWM → 实际到达位置（误差<1.5cm）
- [ ] **可重复性**：同一位置重复5次，方差<1cm（需实机测试）
- [x] **分步移动安全**：底座先转，臂后动，无碰撞（代码已实现）
- [x] **紧急停止有效**：调用后立即停止所有运动（`/arm_controller/emergency_stop`）
- [x] **限位检查**：PWM 超出 500-2500 时拒绝执行并报错（`_check_limits()`）
- [x] **IK 无解处理**：目标不可达时返回错误信息而非执行（`_solve_or_raise()`）
- [x] **完整抓取序列**：可执行 approach → grasp → lift → home 流程（`_execute_pick()`）

---

### Level 2：动作组控制（YAML 预录制动作回放）

#### 目标

用 YAML 文件定义动作序列，安全地在实机上回放。这是最安全的实机控制方式，所有动作都是提前手动调试验证过的。

#### 当前状态

- [x] `action_group_controller.py` — 支持 YAML 格式回放
- [x] `test_servo_direct.py` — 交互式手动调试工具
- [x] YAML 格式动作文件支持
- [x] 预录制的安全动作集（归零、工作姿态、抓取、放置）

#### 需要实现

1. **YAML 动作文件格式定义**

```yaml
# config/actions/pick_and_place.yaml
name: pick_and_place
description: 简单抓取放置动作
actions:
  - name: home
    duration: 2.0
    positions: {0: 1500, 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500}

  - name: pre_grasp
    duration: 2.0
    positions: {0: 1500, 1: 1100, 2: 2200, 3: 1850, 4: 1500, 5: 1500}

  - name: grasp_down
    duration: 1.5
    positions: {0: 1500, 1: 1000, 2: 2300, 3: 1900, 4: 1500, 5: 1500}

  - name: gripper_close
    duration: 1.0
    positions: {5: 1800}

  - name: lift
    duration: 2.0
    positions: {0: 1500, 1: 1100, 2: 2200, 3: 1850, 4: 1500}

  - name: place
    duration: 2.0
    positions: {0: 1800, 1: 1100, 2: 2200, 3: 1850, 4: 1500}

  - name: gripper_open
    duration: 1.0
    positions: {5: 1500}

  - name: back_home
    duration: 2.0
    positions: {0: 1500, 1: 1500, 2: 1500, 3: 1500, 4: 1500, 5: 1500}
```

2. **YAML 动作回放节点**
   - 读取 YAML 动作文件
   - 逐步执行每个动作（带 duration 控制速度）
   - 支持暂停/停止/继续
   - 发布到 `/car1_base_driver/bus_servo/set_position`

3. **动作录制工具**
   - 基于 `test_servo_direct.py` 改造
   - 手动调试好的动作可以直接导出为 YAML 格式
   - 或者提供一个 ROS2 服务，记录当前舵机位置到 YAML

4. **预录制动作集**（用 `test_servo_direct.py` 调试后保存）
   - `home.yaml` — 归零姿态
   - `work_ready.yaml` — 工作准备姿态
   - `pick_front.yaml` — 正前方抓取
   - `place_left.yaml` — 左侧放置
   - `place_right.yaml` — 右侧放置

#### 验证方法

```bash
# 1. 用 test_servo_direct.py 手动调试动作，确认安全
python3 ~/ros2_ws/test_servo_direct.py

# 2. 将调试好的动作保存为 YAML

# 3. 回放 YAML 动作
ros2 run car1_arm_controller play_action --ros-args -p action_file:=pick_front.yaml

# 4. 验证动作是否与手动调试一致
```

#### 验证要点

- [x] YAML 文件格式正确，可被解析
- [x] 动作回放速度与 duration 一致
- [x] 支持单步执行（调试用）
- [x] 支持紧急停止
- [x] 预录制动作在实机上安全执行

---

### Level 3：IK 分步抓取（安全的实机 IK 控制）

#### 目标

为 Level 4（视觉抓取）提供可靠的、安全的、高层机械臂控制接口。使用 IK 求解控制机械臂，采用分步移动策略，确保安全。

**关键设计：**
- **末端控制目标**：tcp_link（位于 arm_link5 下方 76.2mm，实测 76.25mm）
- **抓取策略**：tcp_link 移动到物体顶部中心，指尖（tcp_link 下方 33mm）自然位于物体中部，适合抓取
- **无需预抓取偏移**：33mm 夹爪长度自适应 30-50mm 高度物体
- **坐标来源**：Level 4 通过深度相机（像素 + 深度）直接获取物体顶部中心 [x, y, z]

#### 当前状态

- [x] `arm_controller.py` — 有 IK 求解 + 关节控制
- [x] PWM ↔ 角度转换参数确定：direction=+1, offset=0（所有关节）
- [x] FK/IK 计算到 arm_link5（已验证）
- [x] tcp_link 偏移测量：0.0762m（76.25mm）
- [x] 指尖距离 tcp_link：33mm
- [x] Transform 层实现（PWM ↔ 角度转换）— `transform.py` 完整实现
- [x] 分步移动（先底座旋转，再臂移动）— `_move_stepwise()` 已实现
- [x] tcp_link 偏移补偿（接口层）— 已包含在 `a4` 参数中
- [x] 安全中断机制（emergency stop）— `/arm_controller/emergency_stop` 服务
- [x] 关节限位检查 — `_check_limits()` 已实现
- [x] 验证工具 — `interactive_ik_test.py` 已实现（覆盖 Phase 1-3 功能）

#### 核心组件

**1. Transform 模块** (`transform.py`)
- PWM ↔ 角度转换函数
- 参数：270° 舵机，center=1500，PWM_TO_RAD=0.002356，direction=+1，offset=0
- TCP_OFFSET_Z = 0.0762m（tcp_link 相对 arm_link5）

**2. Safe Arm Controller** (`safe_arm_controller.py`)
- `move_to_pose(x, y, z, pitch)` — 移动 tcp_link 到目标位置
- `set_gripper(close)` — 控制夹爪
- `go_home()` — 回到安全位置 [1500]*5
- `emergency_stop()` — 紧急停止
- `get_current_pose()` — 返回 tcp_link 当前位置

**3. 验证工具**
- `pwm_to_fk_demo.py` — PWM → FK → tcp_link 位置计算验证
- `ik_round_trip_test.py` — 完整闭环测试（目标 → IK → PWM → 移动 → 读取）
- Known-point test — 人工标记物理位置验证

#### 验证方法

**Phase 1: Transform 层验证**
```bash
# 测试 PWM → 角度 → FK → tcp_link 位置
ros2 run car1_kinematics pwm_to_fk_demo

# 测试用例 1: PWM [1500, 1500, 1500, 1500, 1500]
# 期望 tcp_link: [~0, ~0, ~0.506]m (垂直向上)

# 测试用例 2: PWM [1500, 1850, 2109, 1850, 1500]
# 用户目测验证计算位置与实际机械臂位置是否一致（误差<2cm）
```

**Phase 2: IK 闭环验证**
```bash
# 完整流程：目标位置 → IK → PWM → 移动 → 读取实际位置
ros2 run car1_arm_controller ik_round_trip_test

# 测试多个位置，记录误差（目标<1.5cm）
```

**Phase 3: 已知点验证**
```bash
# 在桌面放置物理标记（用尺子测量坐标）
# 例如：[0.25, 0.0, 0.15]
ros2 run car1_arm_controller known_point_test

# 输入标记坐标，机械臂移动 tcp_link 到该位置
# 人工目测验证是否到达
```

**Phase 4: 完整抓取序列**
```python
# 无视觉，用已知坐标测试完整流程
arm.move_to_pose(0.25, 0.0, 0.15)  # 接近
arm.move_to_pose(0.25, 0.0, 0.10)  # 下降到抓取点
arm.set_gripper(close=True)         # 抓取
arm.move_to_pose(0.25, 0.0, 0.15)  # 提升
arm.go_home()                       # 回撤
```

#### 验证要点

- [x] **IK→PWM 闭环验证**：`interactive_ik_test.py --direct` 发送 + 读回实际 PWM 正常工作。
      FK 误差 0.00mm；舵机回读 PWM 与目标基本一致。
      读取逻辑已对齐 `test_servo_direct.py`（只判 status==0，统一直连串口读取）
- [ ] **Transform 层准确**：PWM → 角度 → FK 计算的 tcp_link 位置与实际一致（误差<2cm，需尺子/目测）
- [ ] **IK 控制准确（物理位置）**：目标 tcp_link → 实际到达位置（误差<1.5cm，需已知点尺子测量）
- [ ] **可重复性**：同一位置重复5次，方差<1cm
- [ ] **分步移动安全**：底座先转，臂后动，无碰撞
- [ ] **紧急停止有效**：调用后立即停止所有运动
- [ ] **限位检查**：PWM 超出 500-2500 时拒绝执行并报错
- [ ] **IK 无解处理**：目标不可达时返回错误信息而非执行
- [ ] **完整抓取序列**：可执行 approach → grasp → lift → home 流程（无视觉，用已知坐标）

> **实测发现（2026-06-12）**：ID1(大臂) 稳定 +22~24 PWM (≈+4°)、ID2(小臂) 稳定 +13~14 PWM (≈+2.3°) 系统性偏移，
> ID0/3/4 基本准确。换算末端位置误差约 5~8mm。原因：机械装配/舵机中位校准/负载稳态误差。
> 暂不矫正，留待已知点测试 + Level 4 视觉闭环；如需补偿可在 `transform.py` 加 per-servo offset 或用 `#00xPSCK!` 硬件校中位。

#### 坐标系定义

```
base_link 原点（ROS 右手坐标系）:
  +X: 向前（机器人正前方）
  +Y: 向左
  +Z: 向上

tcp_link 位置:
  = arm_link5 位置 + [0, 0, 0.0762]m

指尖位置:
  = tcp_link 位置 - [0, 0, 0.033]m

抓取点定义（Level 4 提供）:
  物体顶部中心 [x, y, z] = tcp_link 目标位置
  指尖自动位于 [x, y, z - 0.033]，适合抓取 30-50mm 高物体
```

#### Level 3 → Level 4 接口

**Level 4 提供**：
```python
detected_object = {
    'grasp_point': [0.25, 0.0, 0.10],  # 物体顶部中心（深度相机检测）
    'confidence': 0.95
}
```

**Level 3 执行**：
```python
# 直接移动 tcp_link 到抓取点（无需偏移计算）
arm.move_to_pose(
    x=detected_object['grasp_point'][0],
    y=detected_object['grasp_point'][1],
    z=detected_object['grasp_point'][2],
    pitch=-π/2
)
arm.set_gripper(close=True)
arm.move_to_pose(x, y, z+0.05)  # 提升 5cm
arm.go_home()
```

---

### Level 4：视觉 + IK 抓取

#### 目标

通过深度相机识别目标物体位置，自动计算抓取位置并执行 IK 抓取。

#### 前置修复 (2026-06-12 调试中陆续发现并修复)

调试 Level 4 过程中,发现并修复了一连串底层 bug。按发现顺序:

- [x] **统一 240°/270° 转换** (`joint_position_controller.py`): servo_controller 用 240° 量程,transform.py 用 270°,差 12.5%。改 `RADIANS_PER_ENCODER_TICK` 为 0.002356(270°)
- [x] **joint_states 改实际回读** (`controller_manager_node.py`): 原发布指令值。改为通过 `get_state` 服务读舵机实际位置
- [x] **跨线程 spin 崩溃**: 第一版回读用后台线程 `spin_until_future_complete`,与主线程 executor 冲突崩溃。改为**主线程 timer + round-robin call_async + add_done_callback** 异步回读,每 tick 读一个舵机
- [x] **board_sdk 响应字节布局误解** (`board_sdk.py:_bus_servo_read`): `result[0]/result[1]` 语义反了(实际 `[0]`=请求ID回显, `[1]`=cmd回显),导致只有 ID5 凑巧能读到。修正后 6 个舵机全部能读
- [x] **读取路径误钳位** (`joint_position_controller.py:pos_pulse_to_rad`): 读回值被软件限位钳掉。读取方向去掉钳位(只发送方向保留)
- [x] **arm_controller IK 缺解**: 自带简化 IK 只有 acos 单解(elbow-up),且无 PHI 偏角补偿,(0.25,0,0.15) 这类目标报 limit violation。改为**复用 `ik_analytical.py`**(已拷贝到 car1_arm_controller 包内 + config.py)
- [x] **pitch 约定**: 删掉我误加的约定转换。统一为与 web_server/ik_analytical 一致: **0=朝上, 90=水平, 180=夹爪朝下**
- [x] **软件限位过紧** (`servo_controller.yaml`): J4 限位 max=2200 把 IK 解(PWM2295,107°)钳到 2200,夹爪到不了垂直。**所有 arm 关节限位放宽到 500-2500 硬件极限**(夹爪 r_joint 保持原样)
- [x] **相机 launch remap 改坏推流** (`depth_camera.launch.py`): ascamera 驱动用话题名子串 `"rgb0"/"depth0"` 判断流类型(`CameraPublisher.cpp:1394`),我的 remap 把话题改成 `/depth_cam/rgb/image_raw` 丢了 "0" → 驱动识别不出 → 永不推流。**去掉所有 remap 和自定义 node name**,用驱动原生话题
- [x] **RGB 第一帧黑帧**: 流启动后第 1 帧全黑(自动曝光未起),诊断脚本只抓首帧误判"无画面"。visual_grasp 加亮度检查跳过黑帧
- [x] **深度采样改整轮廓**: 原只采中心 5×5,中心落在深度空洞就失败。改为在整个红块轮廓内取有效深度中值

> **原因**: 相机挂在 arm_link4(eye-in-hand),TF `base_link→camera` 依赖 joint_states。
> 若 joint_states 是指令值,ID1/ID2 偏移会污染相机姿态,视觉定位不准。

#### 已验证通过的环节

- [x] 机械臂 IK 控制: pitch=180° 夹爪垂直向下,FK 误差 0.00mm,实物到位正确
- [x] joint_states 实际回读: 6 个舵机 20Hz 回读,反推 PWM 与直连串口一致(误差≤1)
- [x] 相机出图: RGB ~11Hz、Depth ~12Hz,内参 fx=594.5/fy=594.8/cx=350.3/cy=237.5
- [x] TF 链 `base_link → camera_depth_optical_frame` 完整,随机械臂姿态实时更新
- [x] HSV 红色检测: 能稳定检出红块轮廓(命中 ~5000 像素)

#### 当前卡点: 深度相机近距盲区 (未解决)

- [ ] **端到端抓取未通过** — 卡在深度定位

**现象**: 红块 HSV 检测成功,但红块所在像素位置**深度值全为 0**(空洞)。

**根因(已用数据确认,非代码问题)**: HP60C 深度图近距离质量极差。深度有效率热图呈对角分布——**左上(远处)有深度(0.6~1.1m),右下(近处)是大片空洞**。近距离段(200-400mm)有效像素仅占 1%。而 eye-in-hand 俯视抓取时,物体到相机距离正好落在 0.2~0.5m 这个空洞区。
- 整图有效深度: ~42%,但都在 0.6m 以上
- 红块中心周围 ±50px: 0% 有效深度
- 标称最小距离 0.2m,实际 0.5m 内基本不可用

**待定方案**(下次决定):
1. **已知平面射线投影(推荐)**: 物体与底座同高(z已知),用 RGB 像素 + 相机内参 + TF 反算光线与已知 z 平面的交点,**完全不用深度**。绕开近距盲区,只依赖最可靠的 RGB + 几何
2. 换观察姿态让物体落在相机远距有效区(但受机械臂工作空间限制,物体远了可能抓不到)
3. 物体垫高缩短到相机距离差(治标不治本)

#### 验证步骤(分步手动,便于排查)

```bash
# 终端1: bringup(含 servo_controller 回读修复)
ros2 launch car1_bringup bringup.launch.py

# 终端2: arm_controller(IK 控制,提供 /arm_controller/pick)
ros2 launch car1_arm_controller arm_controller.launch.py

# 终端3: 深度相机(原生话题,无 remap)
ros2 launch car1_peripherals depth_camera.launch.py

# 终端4: robot_state_publisher(发布 TF 树)
ros2 launch car1_app rsp_only.launch.py

# 终端5: 视觉抓取主节点
ros2 run car1_app visual_grasp
```

**逐环节验证命令**:
```bash
# joint_states 回读(应反映实际舵机位置)
ros2 topic echo /joint_states --once

# 相机出图(等够10秒看帧率)
ros2 topic hz /ascamera_hp60c/camera_publisher/rgb0/image
ros2 topic echo /ascamera_hp60c/camera_publisher/depth0/camera_info --once

# TF 链
ros2 run tf2_ros tf2_echo base_link camera_depth_optical_frame
```

#### 关键经验(避免重蹈覆辙)

1. **相机 launch 绝不能 remap 改话题名**: ascamera 靠话题名子串 `rgb0/depth0` 判断推流,改名即失效。话题用原生 `/ascamera_hp60c/camera_publisher/...`
2. **相机驱动按需推流**: `streamController` 线程每秒检查订阅者数,无订阅就 stop streaming(日志里的 stop 是正常的),有订阅 1~1.5 秒自动恢复
3. **虚拟环境 ros2_venv 缺 Qt**: rqt/rviz 报 PyQt5 缺失时,软链接系统 `/usr/lib/python3/dist-packages/PyQt5` 进 venv(勿用 pip 编译,会 OOM)
4. **这个 IK 的 pitch 约定**: 0=朝上, 90=水平, **180=夹爪朝下(抓取用这个)**
5. **PoseStamped YAML 冒号后必须有空格**: `{x: 0.25}` 不是 `{x:0.25}`

#### 注意事项

1. **前置修复需重启 bringup 生效**(改了 servo_controller)
2. **HSV 阈值调整**: 默认追红色,其他颜色改 `target_color_hsv_lower/upper`
3. **机械臂观察姿态抬不高**: 结构限制,相机最高约 z=0.25m

#### 原始验收目标(供完成后核对)

- [ ] 物体检测准确率 > 90%
- [ ] 3D 定位误差 < 1.5cm
- [ ] 坐标转换正确（相机→机械臂）
- [ ] 能抓取固定位置的物体
- [ ] 能抓取不同位置的物体（相机视野内）
- [ ] 抓取成功率 > 70%

> 注: 上面"需要实现"里提到的**手眼标定**当前未做——因为相机已通过 URDF(`camera_mount_joint` 挂在 arm_link4)+ robot_state_publisher 提供 TF,坐标变换走 TF 链,无需额外手眼标定。

---

### Level 5：导航 + 视觉 + 抓取（全自主任务）

#### 目标

机器人自主导航到目标区域，视觉识别物体，机械臂抓取，导航到放置区域，释放物体。

#### 当前状态

- [ ] 完整的任务状态机
- [ ] 导航 + 机械臂协调控制
- [ ] 多点巡航 + 抓取任务

#### 前置条件

- Level 4 验证通过（视觉抓取稳定）
- Nav2 导航正常工作（Phase 4 完成）
- 已有环境地图

#### 需要实现

1. **任务状态机**

```
IDLE → NAVIGATE_TO_PICK → DETECT_OBJECT → PICK → 
NAVIGATE_TO_PLACE → PLACE → NAVIGATE_TO_PICK (循环)
```

2. **导航 + 机械臂协调**
   - 导航时机械臂收回安全姿态（避免碰撞）
   - 到达目标点后切换到视觉抓取模式
   - 抓取完成后切换回导航模式

3. **任务配置**

```yaml
# config/transport_task.yaml
task:
  pick_point:
    x: 1.0
    y: 0.5
    theta: 0.0
  place_point:
    x: 2.0
    y: -0.5
    theta: 1.57
  target_color: red
  max_attempts: 3
```

4. **异常处理**
   - 导航失败：重试或报错
   - 检测不到物体：调整位置重试
   - 抓取失败：重试（最多 N 次）
   - 物体掉落：重新检测并抓取

#### 验证方法

```bash
# 完整任务测试
ros2 launch car1_app navigation_transport.launch.py \
  task_config:=transport_task.yaml
```

#### 验证要点

- [ ] 导航到抓取点准确（误差 < 5cm）
- [ ] 到达后自动切换到抓取模式
- [ ] 抓取成功后自动导航到放置点
- [ ] 放置后自动返回抓取点（循环）
- [ ] 异常情况能正确处理（重试/报错）
- [ ] 完整任务成功率 > 60%

---

### 虚实同步（辅助工具，贯穿所有 Level）

#### 目标

在 RViz 中实时显示实物机械臂的姿态，辅助调试和验证。

#### 需要实现

1. **实物 → RViz（状态同步）**
   - 读取实际舵机 PWM 位置（通过 STM32）
   - PWM 转换为关节角度（`pulse2angle`）
   - 发布 `/joint_states`
   - RViz 中的 URDF 模型实时跟随

2. **RViz → 实物（指令同步，可选）**
   - 在 RViz 中用 InteractiveMarker 设置目标位置
   - 显示 IK 求解结果（预览）
   - 用户确认后才发送给实机

#### 验证要点

- [ ] RViz 中模型姿态与实物一致
- [ ] 实时更新（延迟 < 200ms）
- [ ] 可用于辅助 Level 2-5 的调试
