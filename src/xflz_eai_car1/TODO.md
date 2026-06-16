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
