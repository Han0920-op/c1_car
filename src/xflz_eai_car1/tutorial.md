# xflz_robot_car1 上手教程

> 本教程面向学习者，从易到难介绍如何使用 xflz_robot_car1 机器人平台。

---

## 目录

- [项目概述](#项目概述)
- [环境准备](#环境准备)
- [学习路径](#学习路径)
  - [Level 0: 仿真验证（无需硬件）](#level-0-仿真验证无需硬件)
  - [Level 1: 硬件驱动层](#level-1-硬件驱动层)
  - [Level 2: 传感器集成](#level-2-传感器集成)
  - [Level 3: SLAM 建图](#level-3-slam-建图)
  - [Level 4: 自主导航](#level-4-自主导航)
  - [Level 5: 智能应用](#level-5-智能应用)
- [常见问题](#常见问题)

---

## 项目概述

### 项目简介

xflz_robot_car1 是一个基于 ROS2 的移动机械臂平台，具备以下功能：

- **移动底盘**：麦克纳姆轮全向移动
- **机械臂**：5 自由度机械臂 + 夹爪
- **感知**：激光雷达 + 深度相机
- **导航**：SLAM 建图 + 自主导航
- **应用**：巡线、追踪、手势控制、视觉抓取

### 硬件配置

| 硬件 | 型号 | 说明 |
|------|------|------|
| 主控 | STM32F407VET6 | 串口 1Mbps |
| 底盘 | 麦克纳姆轮 × 4 | 全向移动 |
| 机械臂 | 5-DOF + 夹爪 | 总线舵机 |
| 雷达 | 国科光芯 COIN-D6 | 串口 230400，0.01-16m |
| 相机 | 安思疆 HP60C | USB，640×480@25fps |
| IMU | BMI088 | 六轴姿态传感器 |

### 项目结构

```
xflz_robot_car1/
├── driver/                    # Phase 1: 硬件驱动层
│   ├── car1_base_driver/      # STM32 板级驱动
│   ├── car1_chassis_controller/ # 底盘控制器
│   └── car1_servo_controller/ # 舵机控制器
├── arm/                       # 机械臂
│   ├── kinematics/            # 正/逆运动学
│   └── car1_arm_controller/   # 机械臂控制器
├── peripherals/               # Phase 2: 传感器集成
│   └── car1_peripherals/      # 雷达、相机、遥控
├── slam/                      # Phase 3: SLAM 建图
│   └── car1_slam/             # slam_toolbox
├── navigation/                # Phase 4: 自主导航
│   └── car1_navigation/       # Nav2 导航
├── app/                       # Phase 5: 智能应用
│   └── car1_app/              # 巡线、追踪、抓取等
├── simulations/               # 仿真
│   ├── car1_description/      # URDF 模型
│   ├── car1_gazebo/           # Gazebo 仿真
│   └── car1_moveit_config/    # MoveIt2 配置
└── bringup/                   # 启动配置
```

---

## 环境准备

### 系统要求

- **操作系统**：Ubuntu 22.04(开发板) / 24.04(宿主机验证版本)
- **ROS2 版本**：Humble(开发板) 或 Jazzy(宿主机验证版本)
- **Gazebo 版本**：Harmonic (gz-sim)

### 基础依赖安装

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 ROS2 Jazzy（如已安装可跳过）
# 参考：https://docs.ros.org/en/jazzy/Installation.html

# 安装基础工具
sudo apt install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    git
```

### 项目依赖安装

```bash
# ROS2 核心包
sudo apt install -y \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-tf2-tools

# 仿真相关（Level 0 需要）
sudo apt install -y \
    ros-${ROS_DISTRO}-ros-gz-sim \
    ros-${ROS_DISTRO}-ros-gz-bridge \
    ros-${ROS_DISTRO}-ros-gz-interfaces \
    ros-${ROS_DISTRO}-gz-ros2-control \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-controller-manager \
    ros-${ROS_DISTRO}-joint-trajectory-controller

# 导航相关（Level 3-4 需要）
sudo apt install -y \
    ros-${ROS_DISTRO}-slam-toolbox \
    ros-${ROS_DISTRO}-nav2-bringup \
    ros-${ROS_DISTRO}-navigation2 \
    ros-${ROS_DISTRO}-teb-local-planner \
    ros-${ROS_DISTRO}-imu-filter-madgwick \
    ros-${ROS_DISTRO}-robot-localization \
    ros-${ROS_DISTRO}-control-msgs \
    ros-${ROS_DISTRO}-teleop-twist-keyboard

# 视觉相关（Level 5 需要）
sudo apt install -y \
    ros-${ROS_DISTRO}-vision-opencv \
    ros-${ROS_DISTRO}-cv-bridge \
    ros-${ROS_DISTRO}-image-transport \
    python3-opencv

# Python 依赖
pip3 install numpy opencv-python
```

### 编译项目

```bash
# 克隆项目（假设已克隆）
cd ~/xflz_robot_car1_ros2_ws/src

# 编译所有包
cd ~/xflz_robot_car1_ros2_ws
colcon build --symlink-install

# 加载环境变量
source install/setup.bash

# 建议添加到 ~/.bashrc
echo "source ~/xflz_robot_car1_ros2_ws/install/setup.bash" >> ~/.bashrc
```

---

## 学习路径

### 学习建议

1. **按顺序学习**：从 Level 0 开始，逐步进阶
2. **先仿真后实物**：Level 0 无需硬件，可先熟悉操作
3. **遇到问题先查看"常见问题"章节**
4. **每个 Level 完成后再进入下一个**

---

## Level 0: 仿真验证（无需硬件）

> **目标**：在仿真环境中熟悉机器人模型和控制方法  
> **所需时间**：1-2 小时  
> **硬件要求**：无

### 0.1 URDF 模型可视化

**目标**：在 RViz 中查看机器人 3D 模型，理解机器人结构。

```bash
# 启动 URDF 可视化
ros2 launch car1_description display.launch.py
```

**操作说明**：
1. 启动后会打开两个窗口：
   - **Joint State Publisher GUI**：滑块控制关节
   - **RViz2**：显示机器人 3D 模型

2. 尝试拖动滑块：
   - `arm_joint1` ~ `arm_joint5`：机械臂关节
   - `r_joint`：夹爪开合
   - `wheel_*`：车轮旋转

**验证要点**：
- [ ] 机器人模型完整显示
- [ ] 拖动滑块，模型相应运动
- [ ] TF 坐标系正确显示

**可能的问题**：
- **模型不显示**：检查 RViz 左侧 "RobotModel" 是否勾选
- **滑块无响应**：重启 Joint State Publisher GUI

---

### 0.2 MoveIt2 运动规划

**目标**：使用 MoveIt2 进行机械臂运动规划。

```bash
# 启动 MoveIt2
ros2 launch car1_moveit_config demo.launch.py
```

**操作说明**：
1. RViz 中会出现 **MotionPlanning** 面板
2. 在 **Planning** 标签页：
   - **Planning Group** 选择 `arm`（机械臂）或 `gripper`（夹爪）
   - 拖动末端执行器（橙色球）到目标位置
   - 点击 **Plan & Execute** 执行规划

3. 预设位姿：
   - 在 **Goal State** 下拉菜单选择：
     - `home`：零位
     - `open`：夹爪张开
     - `close`：夹爪闭合

**验证要点**：
- [ ] 能拖动末端执行器
- [ ] 规划路径显示（绿色轨迹）
- [ ] 机械臂按规划运动
- [ ] 预设位姿正常切换

**可能的问题**：
- **规划失败**：目标位置超出工作空间，调整到机械臂可达范围
- **碰撞检测报错**：目标位置与机器人自身碰撞，调整位置

---

### 0.3 Gazebo 物理仿真

**目标**：在 Gazebo 中仿真机器人物理交互。

#### 0.3.1 基础仿真

```bash
# 启动 Gazebo 仿真
ros2 launch car1_gazebo gazebo_arm.launch.py
```

**操作说明**：
1. Gazebo 启动后，机器人会出现在仿真世界中
2. 打开新终端，测试控制器：

```bash
# 检查控制器状态
ros2 control list_controllers

# 应该看到 3 个 active 控制器：
# - joint_state_broadcaster
# - arm_controller
# - gripper_controller
```

3. 测试机械臂运动：

```bash
# 移动机械臂
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['arm_joint1', 'arm_joint2', 'arm_joint3', 'arm_joint4', 'arm_joint5'],
  points: [{
    positions: [0.5, 0.3, 0.3, 0.2, 0.0],
    time_from_start: {sec: 2}
  }]
}" --once

# 回到零位
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['arm_joint1', 'arm_joint2', 'arm_joint3', 'arm_joint4', 'arm_joint5'],
  points: [{
    positions: [0.0, 0.0, 0.0, 0.0, 0.0],
    time_from_start: {sec: 2}
  }]
}" --once
```

4. 测试夹爪：

```bash
# 张开夹爪
ros2 topic pub /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['r_joint'],
  points: [{
    positions: [0.5],
    time_from_start: {sec: 1}
  }]
}" --once

# 闭合夹爪
ros2 topic pub /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['r_joint'],
  points: [{
    positions: [0.0],
    time_from_start: {sec: 1}
  }]
}" --once
```

**验证要点**：
- [ ] Gazebo 正常启动
- [ ] 机器人模型正确加载
- [ ] 控制器状态为 active
- [ ] 机械臂响应指令运动
- [ ] 夹爪开合正常

**可能的问题**：
- **Gazebo 启动慢**：首次启动需下载模型，耐心等待
- **控制器未激活**：等待几秒后重新检查
- **模型不显示**：检查终端错误信息，可能是 mesh 文件路径问题

#### 0.3.2 固定位置抓取演示

**目标**：在 Gazebo 中完成自动抓取演示。

```bash
# 启动抓取演示（默认使用 IK）
ros2 launch car1_gazebo grasp_demo.launch.py

# 或使用手动模式（预设关节角度）
ros2 launch car1_gazebo grasp_demo.launch.py mode:=manual

# 或仅启动环境（用于手动控制）
ros2 launch car1_gazebo grasp_demo.launch.py mode:=none
```

**操作说明**：
- **mode:=ik**（默认）：使用逆运动学自动计算关节角度
- **mode:=manual**：使用预设关节角度
- **mode:=none**：仅启动环境，不执行抓取

**演示流程**：
1. 张开夹爪
2. 移动到抓取位置上方（pre-grasp）
3. 下降到抓取高度
4. 闭合夹爪
5. 提升物体
6. 移动到放置位置
7. 释放物体
8. 回到零位

**验证要点**：
- [ ] 红色方块正确生成
- [ ] 机械臂自动执行抓取流程
- [ ] 夹爪能稳定夹住方块
- [ ] 方块被成功搬运到目标位置

**可能的问题**：
- **抓取失败**：方块位置或夹爪力度问题，多尝试几次
- **IK 无解**：目标位置不可达，检查方块位置参数

#### 0.3.3 视觉引导抓取演示

**目标**：通过深度相机识别物体位置，动态抓取。

```bash
# 启动视觉抓取（默认位置）
ros2 launch car1_gazebo grasp_demo_vision.launch.py

# 指定方块位置
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.22 cube_y:=0.03
```

**分层验证**：

**第 1 层：相机话题**
```bash
# 检查话题
ros2 topic list | grep camera
# 期望输出：/camera/image, /camera/depth, /camera/points

# 检查帧率
ros2 topic hz /camera/image
# 期望：~10-20 Hz
```

**第 2 层：图像可视化**
```bash
# 启动 rviz2，添加 Image display
# 话题选择 /camera/image，应能看到红色方块
# 话题选择 /detection_image，应能看到绿色检测框
```

**第 3 层：物体检测**
```bash
# 检查检测结果
ros2 topic echo /detected_object_pose
# 应输出 PoseStamped，position 接近方块实际位置
```

**第 4 层：动态抓取**
```bash
# 测试不同位置
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.25 cube_y:=0.0
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.22 cube_y:=0.03
ros2 launch car1_gazebo grasp_demo_vision.launch.py cube_x:=0.20 cube_y:=-0.03
```

**验证要点**：
- [ ] 相机图像正常发布
- [ ] 物体检测准确（位置误差 < 1cm）
- [ ] 能抓取默认位置的方块
- [ ] 能抓取不同位置的方块

**可能的问题**：
| 现象 | 检查方法 | 解决方案 |
|------|---------|---------|
| 无相机话题 | `ros2 topic list` | 检查 ros_gz_bridge 是否运行 |
| 图像全黑 | rviz2 查看 | 检查 Gazebo 传感器插件配置 |
| 检测不到物体 | 查看 /camera/image | 调整 HSV 阈值 |
| 坐标跳动 | `ros2 topic hz /camera/depth` | 增大深度采样区域 |
| 抓取超时 | 查看日志 | 确认方块在相机视野内 |

---

### Level 0 小结

完成 Level 0 后，你应该：
- ✅ 理解机器人的结构和自由度
- ✅ 掌握 RViz 和 Gazebo 的基本操作
- ✅ 了解机械臂运动规划的基本概念
- ✅ 能在仿真中完成抓取任务

**下一步**：如果有实际硬件，进入 Level 1；否则可继续深入学习仿真功能。

---

## Level 1: 硬件驱动层

> **目标**：启动实际硬件，验证底盘和机械臂基本控制  
> **所需时间**：1-2 小时  
> **硬件要求**：STM32 控制板、电机、舵机

### 1.1 硬件连接

**连接清单**：
1. STM32 控制板通过 USB 连接到电脑
2. 确认串口设备：`ls /dev/ttyUSB*` 或 `ls /dev/ttyACM*`
3. 给机器人上电（注意电源电压）

**串口权限设置**：
```bash
# 添加当前用户到 dialout 组
sudo usermod -aG dialout $USER

# 重新登录或重启生效
# 或临时授权：
sudo chmod 666 /dev/ttyUSB0  # 替换为实际设备号
```

### 1.2 启动驱动层

```bash
# 编译驱动层包
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select \
  car1_base_driver_msgs \
  car1_servo_controller_msgs \
  car1_sdk \
  car1_base_driver \
  car1_servo_controller \
  car1_chassis_controller \
  car1_arm_controller \
  car1_bringup

source install/setup.bash

# 启动完整驱动
ros2 launch car1_bringup bringup.launch.py
```

**启动内容**：
- 板级驱动（STM32 串口通信）
- 底盘控制器（运动学 + 里程计 + EKF）
- 舵机控制器（关节状态 + 轨迹执行）

### 1.3 验证底盘控制

**检查话题**：
```bash
# 检查 IMU 数据
ros2 topic echo /car1_base_driver/imu_raw

# 检查里程计
ros2 topic echo /odom_raw
ros2 topic echo /odometry/filtered  # EKF 融合后

# 检查 TF 树
ros2 run tf2_tools view_frames
# 生成 frames.pdf，检查坐标系关系
```

**测试底盘运动**：
```bash
# 前进
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}" --once

# 后退
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.1}}" --once

# 左转
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}" --once

# 右转
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{angular: {z: -0.5}}" --once

# 左平移（麦轮特有）
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.1}}" --once

# 停止
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{}" --once
```

**验证要点**：
- [ ] 串口连接成功（无报错）
- [ ] IMU 数据正常发布（~100 Hz）
- [ ] 里程计数据正常发布（~50 Hz）
- [ ] 底盘响应 cmd_vel 指令
- [ ] 麦轮全向运动正常

**可能的问题**：
- **串口打不开**：检查设备号和权限
- **IMU 数据异常**：检查 STM32 固件版本
- **底盘不动**：检查电机接线和电源
- **里程计漂移**：需要校准轮径和轮距参数

### 1.4 启动机械臂控制器

```bash
# 新终端，启动机械臂控制器
ros2 launch car1_arm_controller arm_controller.launch.py
```

**测试机械臂**：
```bash
# 回到零位
ros2 service call /arm_controller/go_home std_srvs/srv/Trigger

# 移动到指定关节角度
ros2 topic pub /arm_controller/joint_command sensor_msgs/msg/JointState "{
  name: ['arm_joint1', 'arm_joint2', 'arm_joint3', 'arm_joint4', 'arm_joint5'],
  position: [0.0, -1.0, -1.0, -1.0, 0.0],
  effort: [2.0]
}" --once

# 张开夹爪
ros2 service call /arm_controller/set_gripper std_srvs/srv/SetBool "{data: true}"

# 闭合夹爪
ros2 service call /arm_controller/set_gripper std_srvs/srv/SetBool "{data: false}"
```

**运行演示**：
```bash
# 自动演示（抓取流程）
ros2 run car1_arm_controller arm_demo
```

**验证要点**：
- [ ] 舵机控制器正常启动
- [ ] 关节状态正常发布（`ros2 topic echo /joint_states`）
- [ ] 机械臂响应关节指令
- [ ] 夹爪开合正常
- [ ] 演示脚本完整执行

**可能的问题**：
- **舵机不动**：检查舵机 ID 和供电
- **舵机抖动**：检查舵机负载和电源电流
- **IK 无解**：目标位置超出工作空间

### 1.5 机械臂舵机零位校准（可选）

> **是否需要校准**：如果你的机械臂上电后姿态正常，IK 求解准确，**可以跳过这一步**。只有在发现以下问题时才需要校准：
> - 上电后机械臂姿态明显歪斜（某个关节偏了 5° 以上）
> - IK 求解后实际位置与预期不符
> - 抓取任务经常失败

#### 什么是舵机零位校准？

**问题**：舵机安装时存在机械误差，导致"理论零位"（PWM 1500）与"实际零位"不一致。

**例子**：
- 理论零位：PWM 1500（所有舵机上电后的默认位置）
- 实际零位：由于机械误差，可能需要 PWM 1450 才能真正"垂直"
- offset = 1450 - 1500 = -50

**解决方案**：记录每个舵机的 offset，软件层自动补偿。

#### 校准步骤（3 步完成）

**Step 1：启动校准工具**

```bash
cd ~/ros2_ws/src/xflz_robot_car1
source /opt/ros/${ROS_DISTRO}/setup.bash
colcon build --packages-select calibration
source install/setup.bash

# 启动舵机校准（会启动板级驱动 + 校准节点）
ros2 launch calibration servo_calib.launch.py
```

**Step 2：移动到理论零位并微调**

```bash
# 所有舵机移动到 PWM 1500（理论零位）
ros2 service call /calibrate_servo/move_to_center std_srvs/srv/Trigger
```

观察机械臂姿态，如果某个关节不在理想位置，通过命令行微调：

```bash
# 例如：调整 servo 1（大臂）到垂直位置
# 如果 1500 时不垂直，尝试 1450
ros2 topic pub /car1_base_driver/bus_servo/set_position car1_base_driver_msgs/msg/ServosPosition "{
  duration: 1.0,
  position: [{id: 1, position: 1450}]
}" --once

# 继续微调，直到目测垂直
ros2 topic pub /car1_base_driver/bus_servo/set_position car1_base_driver_msgs/msg/ServosPosition "{
  duration: 1.0,
  position: [{id: 1, position: 1455}]
}" --once

# 依次调整其他舵机...
ros2 topic pub /car1_base_driver/bus_servo/set_position car1_base_driver_msgs/msg/ServosPosition "{
  duration: 1.0,
  position: [{id: 2, position: 1530}]
}" --once
```

**Step 3：保存 offset**

```bash
# 保存当前位置作为 offset
ros2 service call /calibrate_servo/save_offsets std_srvs/srv/Trigger
```

**保存后会生成**：
- `calibration/config/servo_offsets.yaml` 配置文件
- 下次启动 `car1_base_driver` 时会自动加载并应用这些 offset

**验证**：

```bash
# 重启驱动以加载新的 offset
# Ctrl+C 停止当前的 servo_calib.launch.py
ros2 launch car1_bringup bringup.launch.py

# 新终端，启动机械臂控制器
ros2 launch car1_arm_controller arm_controller.launch.py

# 回到零位，确认姿态正确
ros2 service call /arm_controller/go_home std_srvs/srv/Trigger
```

#### 常见问题

**Q: 为什么不写入舵机 EEPROM？**
- EEPROM 写入次数有限（约 10 万次），频繁写入会损坏舵机
- 软件层补偿更安全，出问题只需修改配置文件
- 参考 lander_pi 的实现，也是用软件层补偿

**Q: 校准后重启机器人，offset 会丢失吗？**
- 不会。offset 保存在 `servo_offsets.yaml` 配置文件中
- `car1_base_driver` 启动时会自动加载并应用这些 offset

**Q: 如何查看当前的 offset 值？**
```bash
# 查看配置文件
cat ~/ros2_ws/src/xflz_robot_car1/calibration/config/servo_offsets.yaml
```

**Q: 如何手动修改 offset？**
```bash
# 直接编辑配置文件
nano ~/ros2_ws/src/xflz_robot_car1/calibration/config/servo_offsets.yaml

# 修改后重启 car1_base_driver 生效
ros2 launch car1_bringup bringup.launch.py
```

**Q: 校准后 IK 求解还是不准怎么办？**
- 检查 URDF 模型中的连杆长度参数是否正确
- 检查舵机 ID 是否与 URDF 中的关节顺序一致
- 确认校准时定义的零位姿态与 URDF 中的零位定义一致

---

### 1.6 机械臂动作录制与回放

> **目标**：使用交互工具调试机械臂动作，录制为 YAML 文件，通过 ROS2 回放  
> **所需时间**：30-60 分钟  
> **硬件要求**：机械臂舵机正常工作

#### 概述

机械臂动作控制分为两个阶段：
1. **录制阶段**：通过 `test_servo_direct.py` 交互式调试，将动作导出为 YAML 文件
2. **回放阶段**：通过 `action_player` ROS2 节点回放 YAML 动作文件

已有的动作文件（位于 `arm/car1_arm_controller/config/actions/`）：

| 文件 | 说明 |
|------|------|
| `home.yaml` | 所有关节回中位（1500） |
| `work_ready.yaml` | 工作准备姿态（臂前伸，夹爪张开） |
| `pick_and_place.yaml` | 完整抓取放置动作 |

#### Step 1：启动交互调试工具

```bash
# 先确保 bringup 没有运行（避免串口冲突）
# 确认串口权限
sudo chmod 666 /dev/ttyUSB0

# 启动交互工具
python3 ~/ros2_ws/test_servo_direct.py
```

选择 `1` 进入交互模式：

```
选择模式:
  1. 交互模式 - 手动输入PWM值调试
  2. 回放模式 - 执行 ACTIONS 列表

输入 1 或 2: 1
```

#### Step 2：交互模式命令说明

| 命令 | 说明 | 示例 |
|------|------|------|
| `1500 1100 2200 1850 1500` | 同时控制 5 个关节（J0~J4）PWM | 直接输入 5 个数字 |
| `g <pwm>` | 控制夹爪（ID=5） | `g 1800`（闭合） / `g 1000`（张开） |
| `s <id> <pwm>` | 单独控制某个舵机 | `s 1 1050`（只动 J1） |
| `home` | 所有关节回中位 1500 | |
| `work` | 进入默认工作姿态 | |
| `list` | 查看已保存的动作 | |
| `del <n>` | 删除第 n 个动作 | `del 3` |
| `play` | 回放所有已保存的动作 | |
| `yaml` | 导出为 YAML 文件 | |
| `quit` | 退出 | |

舵机 PWM 范围：500~2500，中位 1500。

#### Step 3：录制动作（以抓取放置为例）

完整操作示例：

```
> work
  保存? 输入名称(回车跳过): pre_grasp

> g 1000
  保存? 输入名称(回车跳过): gripper_open

> 1500 2000 1800 2020 1500
  保存? 输入名称(回车跳过): grasp_down

> g 1500
  保存? 输入名称(回车跳过): gripper_close

> 2000 1800 2000 2000 1500
  保存? 输入名称(回车跳过): lift

> g 1000
  保存? 输入名称(回车跳过): gripper_open

> 1500 1100 2200 1850 1500
  保存? 输入名称(回车跳过): back_work
```

**调试技巧**：

- 每步执行后观察机械臂姿态，不满意则**直接回车跳过**（不保存），重新输入 PWM 值
- 用 `s <id> <pwm>` 微调单个关节，找到合适位置后再输入完整的 5 关节值保存
- 用 `list` 随时查看已保存的动作列表
- 用 `del <n>` 删除录错的步骤
- 用 `play` 完整回放一次，确认动作连贯

```
# 微调示例：发现 J1 还不够低
> s 1 2050
# 观察到位后，输入完整值保存
> 1500 2050 1800 2020 1500
  保存? 输入名称(回车跳过): grasp_down
```

#### Step 4：导出 YAML 文件

确认动作无误后，输入 `yaml`：

```
> yaml
  动作组名称 (如 pick_front): pick_and_place
  描述 (回车跳过): 完整抓取放置动作

  已导出到: .../config/actions/pick_and_place.yaml
  动作步数: 7

  使用方法:
    ros2 run car1_arm_controller action_player --ros-args -p action_file:=pick_and_place
```

导出的 YAML 文件格式：

```yaml
name: pick_and_place
description: 完整抓取放置动作
actions:
- name: pre_grasp
  duration: 2.0
  servos: {0: 1500, 1: 1100, 2: 2200, 3: 1850, 4: 1500}
- name: gripper_open
  duration: 1.0
  servos: {5: 1000}
- name: grasp_down
  duration: 2.0
  servos: {0: 1500, 1: 2000, 2: 1800, 3: 2020, 4: 1500}
# ... 后续步骤
```

#### Step 5：通过 ROS2 回放

```bash
# 编译（安装新的 YAML 文件）
cd ~/ros2_ws
colcon build --packages-select car1_arm_controller
source install/setup.bash

# 启动 bringup（提供串口通信）
ros2 launch car1_bringup bringup.launch.py

# 另一个终端，回放动作
ros2 launch car1_arm_controller action_player.launch.py action:=pick_and_place
```

**回放模式选项**：

```bash
# 普通模式（自动连续执行）
ros2 launch car1_arm_controller action_player.launch.py action:=pick_and_place

# 单步模式（每步等待确认）
ros2 launch car1_arm_controller action_player.launch.py action:=pick_and_place step_mode:=true

# 循环模式
ros2 launch car1_arm_controller action_player.launch.py action:=pick_and_place loop:=true

# 不自动开始（手动触发）
ros2 launch car1_arm_controller action_player.launch.py action:=pick_and_place auto_play:=false
```

**运行时控制**（另开终端）：

```bash
# 紧急停止
ros2 service call /action_player/stop std_srvs/srv/Trigger

# 手动触发播放（auto_play:=false 时使用）
ros2 service call /action_player/play std_srvs/srv/Trigger

# 单步推进（step_mode 时使用）
ros2 service call /action_player/next std_srvs/srv/Trigger
```

#### 验证要点

- [ ] `test_servo_direct.py` 能正常连接串口并控制舵机
- [ ] 录制的动作可通过 `play` 完整回放
- [ ] 导出的 YAML 文件格式正确
- [ ] `action_player` 节点正常启动并执行动作
- [ ] 紧急停止功能有效
- [ ] 单步模式正常工作

#### 常见问题

**Q: 串口打不开**
```bash
# 确认 bringup 已停止（会占用串口）
# 检查设备
ls /dev/ttyUSB*
# 授权
sudo chmod 666 /dev/ttyUSB0
```

**Q: 舵机不动**
- 检查电源是否接通
- 检查舵机 ID 是否正确（0~4 关节，5 夹爪）
- 用 `s 0 1500` 测试单个舵机

**Q: action_player 找不到 YAML 文件**
- 确认已重新编译：`colcon build --packages-select car1_arm_controller`
- 确认已 source：`source install/setup.bash`
- 或使用绝对路径：`action_file:=/full/path/to/file.yaml`

**Q: 动作太快/太慢**
- 直接编辑 YAML 文件中每步的 `duration` 值（单位：秒）
- 建议：大幅度运动 2.0~3.0s，小幅度 1.0~1.5s，夹爪 0.5~1.0s

---

### 1.7 交互式 IK 求解测试

> **目标**：交互式输入目标位置，实时计算 IK 解并可选发送到实机  
> **所需时间**：15 分钟  
> **硬件要求**：机械臂舵机（可选，纯计算模式无需硬件）

`interactive_ik_test.py` 是一个交互式 IK 测试工具，支持两种模式：

- **ROS2 模式**：通过 `/car1_base_driver/bus_servo/set_position` 话题发送指令（需先启动 bringup）
- **直连串口模式（`--direct`）**：直接通过串口发送指令，绕开 ROS2，适合底层调试

#### 启动方式

```bash
cd ~/ros2_ws/src/xflz_robot_car1/arm/kinematics/kinematics

# ROS2 模式（需先 ros2 launch car1_bringup bringup.launch.py）
python3 interactive_ik_test.py

# 直连串口模式（需先停掉 bringup，避免串口冲突）
sudo chmod 666 /dev/ttyUSB0
python3 interactive_ik_test.py --direct
```

#### 操作流程

1. **输入目标 TCP 位置**：
   ```
   输入目标 TCP 位置 (输入 'q' 退出)
   ----------------------------------------------------------------------
   X 坐标 (米) [默认: 0.25]: 0.22
   Y 坐标 (米) [默认: 0.0]: 0.03
   Z 坐标 (米) [默认: 0.15]: 0.12
   俯仰角 (度) [默认: 0]: -90
   ```

2. **查看 IK 求解结果**：
   - 显示关节角度（弧度/角度）
   - 显示 PWM 值（发送到舵机）
   - FK 验证：计算位置 vs 目标位置的误差

3. **发送到实机（可选）**：
   ```
   是否发送到实机? (y/n) [n]: y
   运动时长 (秒) [默认: 2.0]: 3.0
   ```

4. **读取实际 PWM（验证）**：
   ```
   是否读取舵机实际 PWM? (y/n) [y]: y
   等待运动完成 (3.3s)...
   
   读取舵机实际位置:
   ----------------------------------------------------------------------
     关节          ID    目标PWM   实际PWM   误差
     J1-底座旋转    0     1523      1525      +2
     J2-大臂       1     1850      1848      -2
     ...
   ```

#### 功能特点

| 功能 | 说明 |
|------|------|
| **IK 求解** | 解析解 IK，快速计算（~0.05ms） |
| **FK 验证** | 自动计算 FK 并显示误差（应 < 1.5mm） |
| **限位检查** | 自动检查 PWM 是否在 500-2500 安全范围 |
| **PWM 转换** | 直接显示发送到舵机的 PWM 值 |
| **闭环验证** | 发送后读取实际 PWM，对比目标值 |
| **两种模式** | ROS2 模式（需 bringup）/ 直连串口模式（独立） |

#### 坐标系说明

```
base_link 原点（ROS 右手坐标系）:
  +X: 向前（机器人正前方）
  +Y: 向左
  +Z: 向上

tcp_link 位置:
  = arm_link5 位置 + [0, 0, 0.0762]m

指尖位置:
  = tcp_link 位置 - [0, 0, 0.033]m

俯仰角 (pitch):
  0°: 水平向前
  -90°: 垂直向下（抓取姿态）
  +90°: 垂直向上
```

#### 测试用例

**测试 1：中位姿态验证**
```
X: 0.25
Y: 0.0
Z: 0.15
俯仰角: 0
```
期望：机械臂水平前伸，FK 误差 < 1.5mm

**测试 2：抓取姿态**
```
X: 0.22
Y: 0.03
Z: 0.10
俯仰角: -90
```
期望：机械臂向下，适合抓取桌面物体

**测试 3：偏侧位置**
```
X: 0.20
Y: -0.05
Z: 0.12
俯仰角: -45
```
期望：测试 Y 轴偏移和斜向俯仰

#### 验证要点

- [x] IK 求解成功（误差 < 1.5mm）
- [x] 计算结果在舵机安全范围内（PWM 500-2500）
- [x] （实机模式）发送后机械臂正确到达目标位置（已通过直连串口模式闭环验证）
- [x] （实机模式）实际 PWM 与目标 PWM 误差 < 30（系统性偏移见下方说明）

#### 实测系统性偏移（2026-06-12 验证发现）

在直连串口模式下做闭环验证（发送目标 PWM → 读回实际 PWM）时,发现两个关节存在稳定的系统性偏移:

| 关节 | 目标→实际 PWM 偏差 | 角度偏差 | 末端位置影响 |
|------|------------------|---------|-------------|
| ID0 J1-底座旋转 | ±1 | ~0° | 可忽略 |
| **ID1 J2-大臂** | **+22~24** | **+4°** | 5~8mm |
| **ID2 J3-小臂** | **+13~14** | **+2.3°** | 2~3mm |
| ID3 J4-腕部 | 0 | 0° | 无 |
| ID4 J5-末端旋转 | 0 | 0° | 无 |

**原因**：机械装配偏差 + 舵机中位校准 + 负载稳态误差。这是物理特性,不是代码问题。

**处理方式**：
- ✅ **推荐**：通过 Level 4 视觉闭环自动补偿（相机看到的物体位置反映真实姿态,无需手动矫正）
- ⚠️ **可选**：在 `transform.py` 添加 per-servo offset 做软件补偿
- ⚠️ **可选**：用舵机协议 `#001PSCK!` 命令重新校准舵机硬件中位

对于一般抓取任务（30~50mm 物体）,5~8mm 末端误差在夹爪容错范围内,**不必矫正即可进入 Level 4**。

#### 常见问题

**Q: IK 求解失败，提示 "target unreachable"**
- 目标位置超出工作空间
- 检查距离：最大伸展 ~0.4m，最小距离 ~0.1m
- 减小 X 或增大 Z 坐标

**Q: FK 验证误差过大（> 5mm）**
- 检查 URDF 模型参数是否正确
- 检查 transform.py 中的转换参数
- 可能是舵机零位偏移，需要校准（参考 1.5 节）

**Q: 直连串口模式无法打开串口**
```bash
# 确保 bringup 已停止
pkill -f bringup

# 授权串口
sudo chmod 666 /dev/ttyUSB0

# 检查设备
ls -l /dev/ttyUSB0
```

**Q: ROS2 模式发送后无响应**
- 确认 bringup 正在运行：`ros2 node list | grep base_driver`
- 检查话题：`ros2 topic echo /car1_base_driver/bus_servo/set_position`

**Q: 读取实际 PWM 失败或数据错位**

**现象**：ROS2 模式下读取 PWM 时，数值明显错位（如 ID1 显示 1500，ID2 显示 1870，实际应该是 ID1=1870, ID2=2094）

**原因**：`board_sdk` 的消息队列机制导致：
- 发送"读位置"命令后，串口缓冲区可能有其他消息（IMU、电池电压、其他舵机响应）
- ROS2 服务调用时，响应被队列中的消息干扰，读到的是错位数据
- 这是 `car1_base_driver` 串口通信架构的已知限制

**解决方案**：
- ✅ **推荐**：使用 `--direct` 直连串口模式进行验证
  - 直连模式会先清空串口缓冲区，然后只接收 `func=0x05` 的响应包
  - 成功率 >95%，数据准确
  
- ⚠️ **不推荐**：ROS2 模式下读取 PWM
  - 仅用于发送指令，不要依赖读取功能
  - 如必须使用 ROS2 模式，只关注 FK 验证误差（< 1.5mm），忽略 PWM 读取结果

**验证建议**：
```bash
# 停掉 bringup
pkill -f bringup

# 使用直连串口模式
sudo chmod 666 /dev/ttyUSB0
python3 interactive_ik_test.py --direct
```

#### Level 3 完整验证

此工具是 Level 3（IK 分步抓取）的核心验证工具，覆盖以下验证点：

1. **Transform 层验证** — PWM ↔ 角度转换准确性
2. **IK 闭环验证** — 目标 → IK → PWM → 发送 → 读取 → 对比
3. **已知点验证** — 输入物理标记坐标，人工目测到达
4. **FK 验证** — 计算位置与目标位置误差 < 1.5mm

完成验证后，可进入 Level 4（视觉 + IK 抓取）。

---

## Level 2: 传感器集成

> **目标**：启动雷达和深度相机，实现键盘遥控  
> **所需时间**：30 分钟  
> **硬件要求**：COIN-D6 雷达、HP60C 深度相机

### 2.1 依赖安装

```bash
# 雷达驱动（m1ct_d2）和相机驱动（ascamera）需单独安装
# 假设已安装在工作空间中
```

### 2.2 启动传感器

```bash
# 编译传感器包
colcon build --packages-select car1_peripherals
source install/setup.bash

# 启动所有传感器
ros2 launch car1_peripherals peripherals.launch.py
```

**验证雷达**：
```bash
# 检查雷达数据
ros2 topic echo /scan
ros2 topic hz /scan  # 应为 ~10 Hz

# 在 RViz 中可视化
rviz2
# 添加 LaserScan display，话题选择 /scan
```

**验证深度相机**：
```bash
# 检查相机话题
ros2 topic list | grep depth_cam
# 应有：/depth_cam/rgb/image_raw, /depth_cam/depth/image_raw, /depth_cam/depth/points

# 查看图像
ros2 run rqt_image_view rqt_image_view
# 选择 /depth_cam/rgb/image_raw
```

**验证要点**：
- [ ] 雷达数据正常发布
- [ ] 雷达扫描范围正确（0.01-16m）
- [ ] 深度相机 RGB 图像正常
- [ ] 深度图正常
- [ ] 点云数据正常

**可能的问题**：
- **雷达无数据**：检查串口设备和波特率（230400）
- **相机无图像**：检查 USB 连接和驱动
- **点云数据异常**：检查相机内参配置

### 2.2.1 单独验证 HP60C 深度相机（厂商原始案例）

> 上面的 `peripherals.launch.py` 是项目集成入口。如果只想**单独验证相机硬件本身**，可直接用厂商自带的 ascamera 案例启动，这条路径已实测可用。

**首次使用前：配置 udev 权限 + 编译**

```bash
# 1. USB 设备授权（首次必做）
cd ~/ros2_ws/src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/scripts
sudo ./create_udev_rules.sh

# 2. 编译并 source
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ascamera
source install/setup.bash
```

> **编译说明**：原始 CMakeLists 只安装可执行文件、不安装厂商 SDK 动态库，启动会报
> `libAngstrongCameraSdk.so: cannot open shared object file`（退出码 127）。
> 已在 `CMakeLists.txt` 修复：把 `libs/lib/<arch>/*.so` 一并装进可执行文件同目录，
> 并给 `ascamera_node` 设 `INSTALL_RPATH "$ORIGIN"`。重新编译即可正常启动。

**启动相机**

```bash
ros2 launch ascamera hp60c.launch.py
```

启动成功的标志：日志依次出现 `attached` → `camera opened` → `start streaming`。
末尾出现 `stop streaming` 是**正常**的——相机按需推流，没有订阅者时自动停流省资源，
一旦有节点订阅（如下面的 rqt）会自动重新 `start streaming`。
中途的 `getMjpegSize ... failed` 紧跟着 `mjpeg size:640x480`，走了 fallback，可忽略。

**用 rqt_image_view 查看图像（已验证可用）**

```bash
# 另开一个终端
cd ~/ros2_ws
source install/setup.bash
ros2 run rqt_image_view rqt_image_view
```

在 rqt 窗口左上角的话题下拉框中选择：

| 话题 | 内容 |
|------|------|
| `/ascamera_hp60c/camera_publisher/rgb0/image` | RGB 彩色图 |
| `/ascamera_hp60c/camera_publisher/depth0/image_raw` | 深度图（16UC1，单位 mm，0=无效） |

> **话题命名空间是 `ascamera_hp60c`**（不是项目集成版的 `/depth_cam/...`）。
> 厂商驱动靠话题名里的 `rgb0`/`depth0` 子串决定开哪路数据流，**切勿 remap 话题名**。

**验证要点**：
- [ ] `ros2 launch ascamera hp60c.launch.py` 正常启动（出现 `start streaming`）
- [ ] rqt_image_view 能显示 RGB 图像
- [ ] rqt_image_view 能显示深度图（近处灰、远处亮，近距 <0.5m 有空洞属正常硬件盲区）

### 2.2.2 HP60C 深度相机 Web 查看器（局域网浏览器）

> 位于 `test/camera_web_viewer/`。它把 HP60C 的 RGB / 深度 / 点云通过浏览器实时显示，
> 局域网内任何设备（手机、平板、另一台电脑）打开网页即可查看，无需在本机装 RViz/rqt。
> 支持 2D 双画面、3D 点云、深度点击测距。

**功能一览**：

| 功能 | 说明 |
|------|------|
| 2D 视图 | RGB（左）+ Depth（右）并排实时显示，各自带 FPS |
| 3D 视图 | 点云渲染（Three.js），鼠标可旋转/缩放，支持重置视角、调点大小 |
| 深度测距 | 点击 Depth 画面任意点，显示该像素 `X / Y / 深度(m)`，并随画面持续刷新；右键清除 |
| 深度可视化 | TURBO 伪彩色，量程 0–5m |
| FPS 监控 | 侧边栏显示 RGB / Depth / 点云 / Web 接收四路帧率 |

**一次性依赖安装**（Web 框架）：

```bash
# 注意：要装到运行 ROS 节点的同一个 Python。launch 入口脚本使用 /usr/bin/python3，
# 所以这里用系统 python 安装，避免启动时报 ModuleNotFoundError: flask
/usr/bin/python3 -m pip install flask flask-socketio simple-websocket
```

> 前端依赖（three.js r128、OrbitControls、pako、socket.io）已随包打包在
> `static/libs/`，局域网内**无需联网**即可加载。

**编译**：

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select camera_web_viewer --symlink-install
source install/setup.bash
```

**启动**（一条命令同时拉起相机驱动 + Web 服务）：

```bash
ros2 launch camera_web_viewer camera_viewer.launch.py
```

启动后日志会打印监听地址，例如：

```
Web server: http://0.0.0.0:8000  (LAN accessible)
 * Running on http://10.1.134.42:8000      ← 当前网卡 IP（会随网络变化）
```

`0.0.0.0` 表示监听所有网卡，局域网其他设备用**本机当前 IP** 访问即可：

```
http://<本机IP>:8000
```

本机 IP 用 `hostname -I` 或 `ip addr` 查询。

> **相机话题**：launch 里启用了 `color_pcl:=True`（点云带 RGB 上色），
> Web 服务订阅的是相机**原生话题**（带 `camera_publisher` 段，切勿 remap）：
> ```
> /ascamera_hp60c/camera_publisher/rgb0/image
> /ascamera_hp60c/camera_publisher/depth0/image_raw
> /ascamera_hp60c/camera_publisher/depth0/points
> ```

**验证要点**：

- [ ] 浏览器打开 `http://<本机IP>:8000`，左 RGB 右 Depth 实时显示
- [ ] 点击 Depth 画面，标签显示 `X / Y / 深度`，且数值随画面刷新
- [ ] 深度无效区域（太近/太远/空洞）标签显示红色"无效"
- [ ] 切到 3D 标签能看到点云，鼠标可旋转缩放
- [ ] 侧边栏四路 FPS 正常跳动

**常见问题**：

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| `Address already in use` / `Port 8000 is in use` | 上次的服务进程没退干净 | `ss -ltnp \| grep :8000` 查 PID，`kill -9 <pid>` |
| `ModuleNotFoundError: flask` | flask 没装到 `/usr/bin/python3` | 用 `/usr/bin/python3 -m pip install flask flask-socketio simple-websocket` |
| 网页打开但无画面 | 相机话题没数据 / 订阅错话题 | `ros2 topic hz /ascamera_hp60c/camera_publisher/rgb0/image`（等≥10s）确认有数据 |
| 延迟好几秒 | QoS 队列堆积 | 已用 sensor_data QoS（best_effort + keep_last 1）修复；如自行改过订阅需保持 |
| 深度值不刷新 | — | 已实现"粘性追踪点"，点击后每帧更新；右键可清除 |
| 局域网其他设备打不开 | 防火墙挡了 8000 端口 | 放行 8000：`sudo ufw allow 8000`（如启用了 ufw） |

> **停止服务**：`Ctrl+C`，或后台运行时 `pkill -f "launch camera_web_viewer"`。

> **另一个 Web 工具**：`test/car1_web_server/` 是纯静态的 URDF 浏览器查看器
> （`python3 server_cors.py [端口]` 启动，默认 8080，访问 `http://<IP>:端口/viewer/`），
> 用于在浏览器里查看机器人 URDF 模型，与相机查看器互不相关。

### 2.3 键盘遥控

```bash
# 启动键盘遥控
ros2 launch car1_peripherals teleop_key.launch.py
```

**控制键位**：
- `w` / `s` — 前进 / 后退
- `a` / `d` — 左转 / 右转
- `q` / `e` — 左平移 / 右平移（麦轮）
- `空格` — 停止
- `Ctrl+C` — 退出

**验证要点**：
- [ ] 键盘控制响应灵敏
- [ ] 麦轮全向运动正常
- [ ] 速度平滑无突变

---

## Level 3: SLAM 建图

> **目标**：使用雷达进行 SLAM 建图  
> **所需时间**：30 分钟  
> **硬件要求**：雷达 + 底盘  
> **前置条件**：必须先完成底盘校准（见下方 3.0 节）

### 3.0 底盘里程计校准（SLAM 前必做）

> **为什么必须先校准**：不准确的里程计会导致 SLAM 地图变形、重影、回环检测失败。这是 SLAM 建图的前置条件，必须在建图前完成。

> 🧭 **SLAM 前必做校准清单**（缺一不可，详见对应小节）：
> 1. **线速度标定**（3.0.1）→ `linear_correction_factor`
> 2. **角速度标定**（3.0.2）→ `angular_correction_factor`
> 3. **IMU 校准与航向验证**（3.10）→ 麦轮原地转打滑严重，**航向完全靠 IMU**，IMU/EKF 不正确会直接导致地图航向漂移（曾漂 162°）。**务必在建图前先看 3.10 完成验证，不要看完 3.4 就直接建图。**
>
> 校准系数文件统一在：`~/ros2_ws/src/xflz_eai_car1/driver/controller/config/calibrate_params.yaml`

> 🔴 **重要前置（2026-06-23 排查确认）**：校准前必须确保底层速度单位正确，否则标的是错的。
> 历史上曾出现「小车超速 3.98 倍 / 指令转 1 圈实际转 3.75 圈」的问题，**根因不是校准，而是固件与 ROS 的速度单位错配**：
> - **ROS 端** `mecanum.py` 原本经 `speed_to_rps` 发 **rps**，但 STM32 固件 raw 逐轮模式期望 **轮缘线速度 m/s**。
> - **固件端** `kinematics.h` 的 `MEC_WHEEL_DIAMETER` 原为 0.08（真实 0.097），编码器反馈换算偏差。
> - **已修复**：`mecanum.py` 直接发 m/s；固件 `kinematics.h` 轮径改 0.097、轮距/轴距改 0.1946/0.2117（需 Windows Keil 重新编译烧录）。
> - 修复后残留误差仅约 6%，正是 `correction_factor` 该补偿的量级。
>
> **如果你的小车出现「速度异常快 / 转好几圈才停」，先检查上述两处是否已修复，不要急着调校准系数。**
> 直连下位机验证工具见 `calibration/scripts/chassis_serial_test.py`（绕过 ROS，复刻 board_sdk 协议：查表 CRC8、开串口前 rts/dtr=False、先发 set_motor_type 初始化）。

> ⚠️ **rqt_reconfigure 不是必需的**。若环境未装（`Package 'rqt_reconfigure' not found`），
> 直接用 `ros2 param set` 命令行设置参数即可，效果完全一样。本节用命令行方式。

#### 3.0.1 线速度校准

**原理**：让机器人前进一段，对比里程计报告值与尺子实测值，得出修正系数（乘在 odom 输出上，让 odom 报告匹配真实距离）。

**校准脚本说明（2026-06-23 重写）**：
- `calibrate_linear` 读 `/odom_raw`（纯轮式里程），累加行进里程，**单向前进**到目标就停。
- 不再用「欧氏距离 + 正负 error 闭环」（那会因 sqrt 永远为正导致小车前后横跳）。

**准备工作**：
1. 在车头正下方某点贴胶带/粉笔做起点标记
2. 确保地面平整，轮子不打滑（瓷砖偶有打滑，属正常随机误差）

**操作步骤**：

```bash
# 终端1：启动底盘
ros2 launch car1_bringup bringup.launch.py

# 终端2：启动直线校准节点
ros2 run calibration calibrate_linear

# 终端3：用命令行设参数并触发
ros2 param set /calibrate_linear test_distance 1.0
ros2 param set /calibrate_linear speed 0.2
ros2 param set /calibrate_linear odom_linear_scale_correction 1.0
ros2 param set /calibrate_linear start_test true
```

小车自动前进，odom 判断走够 1m 就停，终端2 打印 `finish: odom 行进 X.XXX m`。

**用尺子量实际距离**，然后计算修正系数：

```
linear_correction_factor = 实际距离 / odom报告距离
```

> ⚠️ **方向别搞反**：系数 = 真实 / odom报告（不是目标/实际）。
> 例：odom 报告 0.978m，尺子实测 0.94m → 系数 = 0.94 / 0.978 ≈ 0.961。
> 含义：odom 多报了，要乘 0.961 把数字缩小到匹配真实。

**反复验证**：

```bash
# 填入算出的系数再测一次
ros2 param set /calibrate_linear odom_linear_scale_correction 0.961
ros2 param set /calibrate_linear start_test true
# 这次尺子实测应接近 1.0m（误差 <3cm 合格）
```

> 实测案例：系数 0.961 验证后实际走 0.995m，误差 0.5%。

#### 3.0.1.1 速度依赖性（重要！）

**实测发现**：标定速度影响校准结果，**必须用建图实际使用的速度标定**。

实测案例（轮径 0.0935m，轮距 0.216m 实测值更新后）：

| 标定速度 | odom 报告 | 实际距离 | 偏差 | 推荐系数 |
|---------|---------|---------|------|---------|
| 0.2 m/s | 0.993 m | 1.10 m | +10% | 1.108 |
| 0.3 m/s | 0.993 m | 1.04 m | +4% | 1.04 |
| 0.5 m/s | （未测） | （未测） | — | — |

**原因分析**：
- ROS odom 是**开环积分** cmd_vel（不读编码器），见 `odom_publisher_node.py:_odom_loop`
- 不同速度下加速段/减速段占比不同，引入非线性误差：
  - 低速时加速段占比大，加速期间命令已发但实际未到速 → odom 多报
  - 高速时减速段惯性大，停车后还会滑行 → 实际多走
- 二者方向相反，部分抵消，导致系数随速度变化

**推荐做法**：
1. **决定你建图常用速度**（推荐 0.3 m/s，平衡建图质量和效率）
2. **用该速度标定**，得到对应系数
3. **建图时保持同样速度**，标定才有意义

> 速度依赖性是开环 odom 的固有局限。长期修复方案：固件上报编码器实测轮速，
> ROS 端 odom 改用编码器反馈而非命令积分。当前 ~5% 残余误差对 SLAM 足够。

#### 3.0.1.2 完整验证流程（带几何参数修改）

如果你刚修改了麦轮几何参数（轮径/轮距/轴距），旧标定系数**全部失效**，必须重做。

**完整步骤**：

```bash
# Step 1: 确认参数已更新
# - ROS 端 mecanum.py / odom_publisher_node.py 改了几何参数
# - 固件 kinematics.h MEC_ACLE_BASE / MEC_WHEEL_DIAMETER 改了且重烧
# - calibrate_params.yaml 系数先临时设为 1.0（清空旧标定）

# Step 2: 编译并重启 bringup
cd ~/ros2_ws
colcon build --packages-select controller car1_base_driver --symlink-install
source install/setup.bash
ros2 launch car1_bringup bringup.launch.py

# Step 3: 确认系数加载
# 另开终端
ros2 param get /odom_publisher linear_correction_factor
# 应显示 1.0（未标定状态）

# Step 4: 启动标定节点
ros2 run calibration calibrate_linear

# Step 5: 设置参数（用你建图速度）
ros2 param set /calibrate_linear test_distance 1.0
ros2 param set /calibrate_linear speed 0.3   # ← 建图速度
ros2 param set /calibrate_linear odom_linear_scale_correction 1.0
ros2 topic pub /set_odom geometry_msgs/msg/Pose2D "{x: 0.0, y: 0.0, theta: 0.0}" --once

# Step 6: 触发测试
ros2 param set /calibrate_linear start_test true

# Step 7: 量实际距离，计算系数
# 公式：factor = 实际距离 / odom报告
# 例：odom 报 0.993, 实际 1.04 → factor = 1.04 / 0.993 ≈ 1.047

# Step 8: 保存到配置文件
nano ~/ros2_ws/src/xflz_eai_car1/driver/controller/config/calibrate_params.yaml
# 填入算出的系数

# Step 9: 重启 bringup 使生效
# Ctrl+C 停掉 bringup，重新启动
ros2 launch car1_bringup bringup.launch.py

# Step 10: 验证（关键！）
# 重新启动标定节点（这次脚本内系数设 1.0，验证 odom 单独效果）
ros2 run calibration calibrate_linear
ros2 param set /calibrate_linear speed 0.3
ros2 param set /calibrate_linear odom_linear_scale_correction 1.0
ros2 topic pub /set_odom geometry_msgs/msg/Pose2D "{x: 0.0, y: 0.0, theta: 0.0}" --once
ros2 param set /calibrate_linear start_test true

# Step 10 预期结果：
# - odom 报告 ≈ 0.97~0.99m（受 tolerance=0.03m 影响，提前停止）
# - 实际距离 ≈ odom 报告（两者吻合 = 标定成功）
# 例：odom 报 0.98m，实际量 0.98m → ✅ 完全吻合
```

**双系数说明（避免混淆）**：

| 系数 | 位置 | 作用 | 标定时 | 验证时 |
|------|------|------|--------|--------|
| `linear_correction_factor` | calibrate_params.yaml<br/>(odom_publisher) | 放大 odom 输出，全局生效 | 暂设 1.0 | 填实测值 |
| `odom_linear_scale_correction` | calibrate_linear 脚本运行时参数 | 脚本内部判断距离 | 暂设 1.0 | 暂设 1.0 |

⚠️ **两个系数会叠加**：脚本系数 × odom_publisher 系数。验证时脚本系数必须设 1.0，否则会双重修正。

**验证通过判据**：odom 报告值 ≈ 实际尺子量值（误差 <3cm 优秀，<5cm 合格）。

**随时停车**（任意时刻）：
```bash
ros2 param set /calibrate_linear start_test false
# 或兜底： pkill -f calibrate_linear
```

**保存结果**：

```bash
nano ~/ros2_ws/src/xflz_eai_car1/driver/controller/config/calibrate_params.yaml
```

```yaml
/**:
  ros__parameters:
    linear_correction_factor: 0.961   # ← 填入你的校准值
    angular_correction_factor: 1.00
```

> 保存后**重启 bringup** 即生效（yaml 启动时被读取，无需编译）。

#### 3.0.2 角速度校准

**原理**：让机器人原地旋转，用手机指南针量真实转角，对比里程计报告。

**校准脚本说明（2026-06-23 修复）**：
- `calibrate_angular` 读 `/odom_raw` 纯轮式 yaw，**累加旋转幅度（绝对值）单向旋转**到目标就停。
- 修复了两个历史 bug：① 度/弧度单位混用导致转不停；② odom yaw 符号与命令方向相反引发正反馈发散（实测转 3+ 圈）。
- `angular_correction_factor` 已在 `odom_publisher_node.py:186` 接线生效（yaw 增量乘该系数）。

**准备工作**：
1. 手机打开指南针 APP，固定在车上（放车后部，远离电机避免磁干扰）
2. 记录起始朝向
3. 确保四轮均匀接地

**操作步骤**：

```bash
# 终端2：停掉直线校准，启动角度校准
pkill -f calibrate_linear
ros2 run calibration calibrate_angular

# 终端3：设参数并触发
ros2 param set /calibrate_angular test_angle 360.0
ros2 param set /calibrate_angular speed 0.3
ros2 param set /calibrate_angular odom_angular_scale_correction 1.0
ros2 param set /calibrate_angular start_test true
```

小车自动旋转，odom 判断转够 360° 就停。

> ⚠️ **关键**：脚本「转够」的判断基于 odom，odom 本身可能不准，所以**停车 ≠ 真转了 360°**。
> **必须用指南针量真实转角**，不能信脚本。

**计算修正系数**：

```
angular_correction_factor = 真实转角 / 360
```

> 例：脚本停车时指南针显示实际转了 347°（少转 13°）→ 系数 = 347 / 360 ≈ 0.964。

**跨 0° 换算**（指南针跨越 360/0 边界时）：
```
偏差 = (结束角度 - 起始角度 + 180) % 360 - 180
```

**反复验证**：

```bash
ros2 param set /calibrate_angular odom_angular_scale_correction 0.964
ros2 param set /calibrate_angular start_test true
# 指南针量真实转角，应接近 360°
```

> 实测案例：系数 0.964 验证后残留均值约 4°（1.1%）。残留在 2~10° 间随机跳动，
> 是**起步惯性 + 瓷砖打滑 + 指南针精度** 的随机误差，不是系数问题，不必强求归零。

**保存结果**：

```yaml
# driver/controller/config/calibrate_params.yaml
/**:
  ros__parameters:
    linear_correction_factor: 0.961
    angular_correction_factor: 0.964   # ← 填入你的校准值
```

#### 3.0.3 校准验证

完成校准后，**重启 bringup** 让系数生效，确认参数被读取：

```bash
ros2 launch car1_bringup bringup.launch.py

# 确认两个系数已加载
ros2 param get /odom_publisher linear_correction_factor    # 应为 0.961
ros2 param get /odom_publisher angular_correction_factor   # 应为 0.964
```

**验证要点**：
- [ ] `ros2 param get` 返回标定值（非默认 1.0）
- [ ] 线速度：走 1m，尺子实测误差 < 3cm
- [ ] 角速度：转 360°，指南针真实转角误差 < 5°

**常见问题**：
- **速度异常快 / 转好几圈才停**：底层单位错配，检查固件轮径(0.097)和 mecanum.py(发m/s)是否已修复，见本节顶部前置说明
- **小车前后横跳不停**：旧版 calibrate_linear 闭环震荡 bug，已重写为单向前进；确认已重新编译 calibration 包并重启节点
- **每次结果不同（误差 2~10° 跳动）**：瓷砖打滑 + 起步惯性 + 指南针精度的随机误差，正常，取多次均值
- **`rqt_reconfigure` 找不到**：用 `ros2 param set` 命令行替代，见上方步骤

---

### 3.1 依赖确认

```bash
# 确保以下依赖已安装
sudo apt install -y \
    ros-${ROS_DISTRO}-slam-toolbox \
    ros-${ROS_DISTRO}-imu-filter-madgwick \
    ros-${ROS_DISTRO}-robot-localization \
    ros-${ROS_DISTRO}-control-msgs \
    ros-${ROS_DISTRO}-teleop-twist-keyboard \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-robot-state-publisher
```

### 3.2 编译相关包

```bash
cd ~/ros2_ws

# 编译雷达驱动（从源码编译，确保兼容 ROS2 参数传递）
source /opt/ros/${ROS_DISTRO}/setup.bash
colcon build --packages-select m1ct_d2 --cmake-args -DCMAKE_BUILD_TYPE=Release \
    --build-base src/xflz_robot_car1/build --install-base install

# 编译 SLAM 及依赖包
colcon build --packages-select \
    car1_base_driver_msgs \
    car1_servo_controller_msgs \
    car1_sdk \
    car1_base_driver \
    car1_servo_controller \
    car1_chassis_controller \
    car1_bringup \
    car1_peripherals \
    car1_description \
    car1_slam \
    --symlink-install

source install/setup.bash
```

### 3.3 串口配置

机器人有两个 USB 串口（均为 CH340 芯片），需要正确识别：

- `/dev/ttyUSB0`：STM32 底盘控制板（波特率 1000000，协议头 `0xAA 0x55`）
- `/dev/ttyUSB1`：COIN-D6 激光雷达（波特率 230400）

**确认方法**：
```bash
# 运行识别脚本，通过数据特征区分
sudo python3 -c "
import serial, time
for port in ['/dev/ttyUSB0', '/dev/ttyUSB1']:
    try:
        ser = serial.Serial(port, 1000000, timeout=2)
        time.sleep(0.5)
        data = b''
        start = time.time()
        while time.time() - start < 2:
            if ser.in_waiting > 0:
                data += ser.read(ser.in_waiting)
            time.sleep(0.1)
        ser.close()
        if b'\xaa\x55' in data:
            print(f'{port}: STM32 底盘 (检测到 0xAA 0x55 协议头)')
        elif len(data) == 0:
            print(f'{port}: 无数据 (可能是雷达，需要初始化命令)')
        else:
            print(f'{port}: 未知设备 ({len(data)} bytes)')
    except Exception as e:
        print(f'{port}: 错误 - {e}')
"
```

**修改配置文件**（如果串口分配与默认不同）：
- 底盘串口：`driver/car1_base_driver/config/base_driver.yaml` 中的 `serial_port`
- 雷达串口：`peripherals/car1_peripherals/launch/lidar.launch.py` 中的 `port` 参数

### 3.4 启动 SLAM

```bash
source ~/ros2_ws/install/setup.bash

# 启动 SLAM（包含底盘驱动 + 雷达 + URDF TF + slam_toolbox + RViz）
ros2 launch car1_slam slam.launch.py
```

**启动内容**：
- `car1_bringup`：底盘驱动（STM32 通信 + IMU 滤波 + 里程计 + EKF + 舵机控制）
- `m1ct_d2`：COIN-D6 雷达驱动
- `robot_state_publisher`：从 URDF 发布完整 TF 树
- `joint_state_publisher`：发布关节状态（用于 RViz 模型显示）
- `slam_toolbox`：SLAM 建图（延迟 3 秒启动，等待传感器稳定）
- `rviz2`：可视化界面（自动加载保存的配置）

### 3.5 RViz 显示设置

如果 RViz 没有自动加载配置，手动设置：

1. **Fixed Frame**：设为 `map`
2. **Add → By topic → /scan → LaserScan**
   - Topic → Reliability 改为 **Best Effort**（雷达使用 SensorDataQoS）
3. **Add → By topic → /map → Map**
   - Topic → Reliability: `Reliable`
   - Topic → Durability: `Transient Local`
4. **Add → By display type → RobotModel**
   - Description Topic: `/robot_description`
5. **Add → By display type → TF**

设置完成后保存配置：File → Save Config As → `src/xflz_robot_car1/slam/car1_slam/rviz/slam.rviz`

### 3.6 建图操作

**启动键盘遥控**（新终端）：
```bash
source ~/ros2_ws/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> **注意**：SSH 远程连接时 teleop_twist_keyboard 可能无法捕获按键。替代方案：
> ```bash
> # 前进 3 秒
> timeout 3 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
>
> # 左转 2 秒
> timeout 2 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.3}}" --rate 10
>
> # 右转 2 秒
> timeout 2 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: -0.3}}" --rate 10
>
> # 左平移（麦轮）
> timeout 2 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.3, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}" --rate 10
> ```

**建图技巧**：
- 速度与标定速度保持一致（linear ≈ 0.3 m/s，angular ≤ 0.3 rad/s）。**标定速度=建图速度**，否则线速度系数失效（见 3.0.1.1）
- 匀速移动，避免急加速和急转弯
- 尽量覆盖整个环境
- 走闭环（回到起点），slam_toolbox 会自动做回环检测优化地图
- 避免长走廊等特征稀少的环境

### 3.7 保存地图

```bash
# 建图完成后保存
ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/xflz_robot_car1/slam/car1_slam/maps/my_map
```

保存后会生成两个文件：
- `my_map.pgm`：地图栅格图像
- `my_map.yaml`：地图元数据（分辨率、原点等）

### 3.8 验证要点

- [ ] 所有节点正常启动（无 SIGSEGV 或串口错误）
- [ ] RViz 中能看到机器人模型、激光点云、TF 树
- [ ] 移动机器人后地图实时构建
- [ ] 地图质量良好（无重影、墙壁清晰）
- [ ] 地图保存成功

### 3.9 常见问题

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| `No such file: /dev/car1_board` | 串口设备名不对 | 运行串口识别脚本，修改 `base_driver.yaml` |
| `imu_filter_madgwick` not found | 依赖未安装 | `sudo apt install ros-${ROS_DISTRO}-imu-filter-madgwick` |
| `No module named 'control_msgs'` | 依赖未安装 | `sudo apt install ros-${ROS_DISTRO}-control-msgs` |
| m1ct_d2 崩溃 (exit code -6) | 旧版二进制不支持 ROS2 参数 | 从源码重新编译 m1ct_d2 |
| RViz 中 LaserScan 无显示 | QoS 不匹配 | LaserScan 的 Reliability 改为 Best Effort |
| Map 显示 "No map received" | slam_toolbox 未处理 scan | 确认 `transform_timeout` ≥ 1.0（在 `slam.yaml` 中） |
| RobotModel 不显示 | 缺少 joint_states | 确认 `joint_state_publisher` 节点在运行 |
| 轮子不停 | cmd_vel 超时未停止 | 系统已内置 0.5 秒超时自动停止 |
| 地图重影 | 移动速度过快或与标定速度不符 | 匀速 ≈ 0.3 m/s（与标定一致），angular ≤ 0.3 |
| 定位丢失 | 环境特征不足 | 增加环境特征物，避免空旷区域 |

### 3.10 IMU 校准与航向验证（关键经验，2026-06）

> 本节记录一次完整的航向问题排查。麦轮原地转打滑严重（实测 ~45%），**航向必须靠 IMU**，
> 因此 IMU 链路 + EKF 融合是 SLAM 成败的核心。曾出现建图航向漂移 162°，根因是下面 5 个 bug 叠加。

#### 3.10.1 航向问题的 5 个根因（全部已修复）

| # | 问题 | 现象 | 修复 |
|---|------|------|------|
| 1 | IMU gyro scale 2× 过报告 | 转 1 圈 IMU 积分报 2 圈 | 固件 bmi088.c：soft-reset 后加 `HAL_Delay(30)` + 0x0F 回读校验 |
| 2 | IMU 协方差全 0 | EKF 静默丢弃 IMU 数据 | base_driver_node.py：填非零协方差（角速度对角 0.0025） |
| 3 | imu0_relative=true | vyaw 被减去初值 | ekf.yaml：改 `imu0_relative: false` |
| 4 | **缺 base_link→imu_link TF** | EKF 无法变换 IMU 坐标（主因） | bringup.launch.py：加 robot_state_publisher |
| 5 | 轮速 vyaw 与 IMU vyaw 冲突 | 打滑轮速污染航向 | ekf.yaml：odom0 关 vyaw，航向只用 IMU |

#### 3.10.2 IMU scale 验证（转动法）

```bash
# 停掉 ROS，直接串口测（脚本独占串口，不能开 bringup）
python3 src/xflz_eai_car1/test/imu_chassis_test.py
```

判读"缩小倍数"：
- ~1.0 → IMU 正常（本项目实测转 300° / IMU 积分 303°，1.01×）
- ~2.0 → scale 错误（量程寄存器问题）

#### 3.10.3 EKF 融合 IMU 验证（分步排查）

```bash
ros2 launch car1_bringup bringup.launch.py

# 1. IMU 链路三段验证
ros2 topic hz /car1_base_driver/imu_raw   # STM32 源头，~10 Hz
ros2 topic hz /imu                         # 滤波输出，~10 Hz
ros2 node info /ekf_filter_node | grep -A5 Subscribers  # 含 /imu

# 2. 协方差非零（关键！）
ros2 topic echo /imu --once --field angular_velocity_covariance
# 应为 [0.0025, 0, 0, 0, 0.0025, 0, 0, 0, 0.0025]，全 0 则 EKF 丢弃

# 3. TF 链完整（关键！）
ros2 run tf2_ros tf2_echo base_link imu_link
# 应看到静态变换，"frame does not exist" 说明缺 robot_state_publisher

# 4. 核心：转动时 EKF 角速度是否跟随
#    终端A
ros2 topic echo /odometry/filtered --field twist.twist.angular.z
#    终端B
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}" -r 20
# 车转时终端A应显示 ~0.5（恒为 0 = EKF 没用 IMU）
```

#### 3.10.4 航向闭环验证（最终判据）

```bash
# 终端A：监控航向
ros2 run tf2_ros tf2_echo odom base_footprint
# 记录起始 yaw(degree)

# 终端B：原地转整数圈（0.5 rad/s 转一圈约 12.5s）
ros2 topic pub /controller/cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}" -r 20
# 目视转回原朝向后 Ctrl+C
```

**判据**：转 N 整圈后 yaw 回到起始值。本项目实测闭环误差 **0.25°/圈**（合格线 <5°）。

#### 3.10.5 常见陷阱

| 陷阱 | 说明 |
|------|------|
| imu_chassis_test.py 与 bringup 抢串口 | 两者都占 /dev/ttyUSB0，必须先停 bringup 再跑脚本 |
| bringup 缺 robot_state_publisher | 修复后已加入 bringup；EKF 依赖 base_link→imu_link TF |
| 协方差全 0 | robot_localization 无法求逆 → 静默丢弃，必须填非零 |
| tf2_echo 时序误判 | 静止/转动日志要严格对齐时间，否则误判"yaw 不变" |
| cmd_vel 持续发布转太多圈 | `-r 20` 不会自动停，用 `timeout 12.5` 控制圈数 |

---

## Level 4: 自主导航

> **目标**：使用已有地图进行自主导航  
> **所需时间**：30 分钟  
> **硬件要求**：雷达 + 底盘 + 已保存的地图

### 4.1 编译导航包

```bash
cd ~/ros2_ws
colcon build --packages-select car1_navigation
source install/setup.bash
```

### 4.2 启动导航系统

#### 方式 1：完整启动（推荐，包含所有组件）

```bash
# 终端 1：启动导航（默认地图为 slam_map）
ros2 launch car1_navigation navigation.launch.py map:=slam_map

# 如果使用其他地图
# ros2 launch car1_navigation navigation.launch.py map:=my_map
```

**此命令会自动启动**：
- 底盘驱动（bringup）
- 激光雷达（lidar）
- 定位系统（AMCL + map_server，地图自动加载）
- 导航服务器（planner、controller、bt_navigator）
- RViz 可视化界面（如果 `use_rviz:=true`，默认启用）

**验证地图加载成功**：
```bash
# 查看日志，应该看到：
# [map_server]: Loading yaml file: .../slam_map.yaml
# [map_server]: Loaded map with size: XX x YY
# [amcl]: Received a XX X YY map @ 0.050 m/pix

# 或通过话题验证
ros2 topic echo /map --once
```

> **✅ 修复说明**（2026-07-06）：地图加载问题已解决，`map_server` 现在会自动加载地图，无需手动调用服务。

### 4.3 RViz 配置

如果 RViz 显示不正常，按以下步骤配置：

1. **设置 Fixed Frame**：
   - 左上角 **Global Options → Fixed Frame** 设为 `map`

2. **添加地图**：
   - 点击左下角 **Add** 按钮
   - 选择 **By topic** → `/map` → **Map**
   - 展开 Map 设置，确保：
     - **Topic** → **Reliability**: `Reliable`
     - **Topic** → **Durability**: `Transient Local`

3. **添加激光扫描**：
   - **Add** → **By topic** → `/scan` → **LaserScan**
   - 设置 **Reliability** 为 `Best Effort`

4. **添加 AMCL 粒子云**：
   - **Add** → **By display type** → **PoseArray**
   - 展开 PoseArray，设置 **Topic** 为 `/particle_cloud`

5. **添加机器人模型**：
   - **Add** → **By display type** → **RobotModel**
   - **Description Topic** 设为 `/robot_description`

6. **添加路径规划显示**（可选）：
   - **Add** → **By topic** → `/plan` → **Path**（全局路径）
   - **Add** → **By topic** → `/local_plan` → **Path**（局部路径）

7. **添加代价地图**（可选）：
   - **Add** → **By topic** → `/global_costmap/costmap` → **Map**
   - **Add** → **By topic** → `/local_costmap/costmap` → **Map**

### 4.4 导航操作步骤

#### 步骤 1：设置初始位姿

机器人需要知道自己在地图上的初始位置。

1. 在 RViz 顶部工具栏点击 **2D Pose Estimate** 按钮
2. 在地图上**点击**机器人的当前实际位置
3. **按住鼠标拖动**设置机器人的朝向（箭头方向）
4. 释放鼠标

**验证定位成功**：
- AMCL 粒子云（绿色箭头）应该快速收敛到机器人周围
- 机器人模型应该与实际位置对齐
- 激光扫描点云应该与地图墙体重合

> **提示**：如果定位不准，可以多次设置初始位姿，或者稍微移动机器人让 AMCL 重新收敛。

#### 步骤 2：发送导航目标

1. 在 RViz 顶部工具栏点击 **2D Goal Pose** 按钮
2. 在地图上**点击**目标位置
3. **按住鼠标拖动**设置目标朝向
4. 释放鼠标

**观察导航过程**：
- **绿色路径**：全局规划路径（从起点到终点的完整路径）
- **红色路径**：局部规划路径（当前实时跟随的路径）
- **蓝色/紫色区域**：代价地图（障碍物膨胀区域）
- 机器人会自动沿路径导航到目标点

#### 步骤 3：取消导航（如需要）

如果想中途取消导航：
```bash
# 新终端
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{}" --feedback
# 按 Ctrl+C 取消
```

或者在 RViz 中重新设置一个新的目标位置。

### 4.5 验证要点

完成以下验证项：

- [ ] **地图加载成功**：RViz 中能看到地图
- [ ] **AMCL 定位正常**：粒子云收敛，机器人位姿与地图对齐
- [ ] **路径规划成功**：设置目标后能看到绿色全局路径
- [ ] **机器人移动**：机器人沿路径自动移动
- [ ] **到达目标点**：机器人能准确到达目标位置（误差 <10cm）
- [ ] **自动避障**：路径上放置障碍物，机器人能自动绕开

### 4.6 常见问题与解决

#### 问题 1：定位不准确

**现象**：机器人模型与实际位置不对齐，粒子云发散。

**解决**：
1. 重新设置初始位姿，尽量准确
2. 移动机器人让 AMCL 重新收敛
3. 检查激光扫描是否正常：`ros2 topic echo /scan`
4. 检查 TF 树是否完整：`ros2 run tf2_tools view_frames`

#### 问题 2：路径规划失败

**现象**：设置目标后没有绿色路径，或显示 "Goal is not reachable"。

**解决**：
1. 确认目标点不在障碍物内（不要设在黑色区域）
2. 确认目标点在地图范围内
3. 尝试设置更近的目标点
4. 检查全局代价地图：`ros2 run rviz2 rviz2`，添加 `/global_costmap/costmap`

#### 问题 3：机器人不移动

**现象**：路径规划成功，但机器人静止不动。

**解决**：
1. 检查 `controller_server` 是否运行：
   ```bash
   ros2 node list | grep controller_server
   ```
2. 检查 `/cmd_vel_nav` 话题是否有数据：
   ```bash
   ros2 topic echo /cmd_vel_nav
   ```
3. 检查底盘驱动是否正常：
   ```bash
   ros2 topic echo /odom
   ```

#### 问题 4：导航震荡或抖动

**现象**：机器人在原地震荡，或路径跟随不稳定。

**解决**：
1. 调整控制器参数（`nav2_params.yaml` 中的 DWB 参数）
2. 检查里程计数据质量
3. 降低速度限制

#### 问题 5：地图未加载（已修复）

**现象**：AMCL 显示 "Waiting for map"，RViz 中看不到地图。

**解决**：
- ✅ **此问题已在 2026-07-06 修复**，地图现在会自动加载
- 如果仍遇到此问题，检查：
  1. 地图文件是否存在：`ls ~/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps/slam_map.*`
  2. map_server 节点是否运行：`ros2 node list | grep map_server`
  3. 查看 map_server 日志：检查是否有加载错误

### 4.7 多点导航（Python API）

如果需要让机器人自动巡逻多个点，可以使用 Python API：

```python
from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import rclpy

rclpy.init()
navigator = BasicNavigator()

# 等待导航系统准备就绪
navigator.waitUntilNav2Active()

# 定义多个目标点
goal_poses = []

# 目标点 1
goal_pose1 = PoseStamped()
goal_pose1.header.frame_id = 'map'
goal_pose1.header.stamp = navigator.get_clock().now().to_msg()
goal_pose1.pose.position.x = 1.0
goal_pose1.pose.position.y = 0.0
goal_pose1.pose.orientation.w = 1.0
goal_poses.append(goal_pose1)

# 目标点 2
goal_pose2 = PoseStamped()
goal_pose2.header.frame_id = 'map'
goal_pose2.header.stamp = navigator.get_clock().now().to_msg()
goal_pose2.pose.position.x = 0.0
goal_pose2.pose.position.y = 1.0
goal_pose2.pose.orientation.w = 1.0
goal_poses.append(goal_pose2)

# 循环导航
for goal_pose in goal_poses:
    navigator.goToPose(goal_pose)
    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        # 可以在这里处理反馈信息
        pass
    
    result = navigator.getResult()
    if result == TaskResult.SUCCEEDED:
        print(f'到达目标点')
    else:
        print(f'导航失败')

navigator.lifecycleShutdown()
```

保存为 `multi_point_nav.py`，运行：
```bash
python3 multi_point_nav.py
```

---

## Level 5: 智能应用

> **目标**：运行视觉和雷达相关的智能应用  
> **所需时间**：1 小时  
> **硬件要求**：深度相机 + 雷达 + 底盘 + 机械臂

### 5.1 巡线行驶

**功能**：识别地面黑线，沿线行驶。

```bash
# 编译应用包
colcon build --packages-select car1_app
source install/setup.bash

# 启动巡线
ros2 launch car1_app line_following.launch.py
```

**使用说明**：
- 在地面铺设黑色胶带作为引导线
- 机器人会自动识别并沿线行驶
- 可在 `config/app_params.yaml` 中调整 LAB 阈值和 PID 参数

**验证要点**：
- [ ] 能识别黑线
- [ ] 沿线行驶平稳
- [ ] 转弯响应及时

### 5.2 颜色目标追踪

**功能**：识别指定颜色物体，跟随目标移动。

```bash
# 启动颜色追踪
ros2 launch car1_app object_tracking.launch.py
```

**使用说明**：
- 在相机前放置红色物体（默认追踪红色）
- 机器人会自动跟随物体移动
- 保持一定距离（约 0.5m）

**验证要点**：
- [ ] 能识别目标颜色
- [ ] 跟随目标移动
- [ ] 保持合适距离

### 5.3 手势控制

**功能**：通过手势控制底盘运动。

```bash
# 启动手势控制
ros2 launch car1_app hand_gesture.launch.py
```

**手势说明**：
- **手掌张开**：停止
- **握拳**：前进
- **竖起食指**：后退
- **OK 手势**：左转
- **点赞**：右转

**验证要点**：
- [ ] 手势识别准确
- [ ] 底盘响应及时
- [ ] 控制流畅

### 5.4 雷达避障

**功能**：3 扇区雷达避障，自动规避障碍物。

```bash
# 启动雷达避障
ros2 launch car1_app lidar_controller.launch.py
```

**使用说明**：
- 机器人会自动前进
- 检测到障碍物时自动转向
- 可调整避障距离阈值

**验证要点**：
- [ ] 检测到障碍物
- [ ] 自动转向避障
- [ ] 避障后继续前进

### 5.5 视觉抓取（旧版,移动底盘）

**功能**：识别目标物体，机械臂自动抓取。

```bash
# 启动视觉抓取
ros2 launch car1_app track_and_grab.launch.py
```

**使用说明**：
- 在机器人前方放置红色物体
- 机器人会自动识别并抓取
- 抓取后放置到指定位置

**状态机流程**：
1. SEARCH - 搜索目标
2. APPROACH - 接近目标
3. ALIGN - 对准目标
4. GRAB - 抓取
5. LIFT - 提升
6. DONE - 完成

**验证要点**：
- [ ] 能识别目标物体
- [ ] IK 求解成功
- [ ] 抓取成功
- [ ] 放置准确

> ⚠️ **此节点已不推荐**：依赖底盘移动 + 硬编码 PWM,与 Level 3 已验证的 IK 接口不互通。
> 新项目请使用 5.6 节的 `visual_grasp`,基于 IK + look-then-move,不需要底盘移动。

---

### 5.6 视觉抓取（推荐，静态桌面 + look-then-move）

> **目标**：通过深度相机识别桌面物体，基于 IK 自动抓取（机器人底盘不动）  
> **所需时间**：30-60 分钟  
> **硬件要求**：HP60C 深度相机 + 机械臂 + 红色物体（30~50mm）  
> **前置条件**：完成 Level 1.7（交互式 IK 验证通过）  
> **当前状态（2026-06-18）**：机械臂/相机/TF/检测各环节已验证通过，**端到端抓取卡在观察姿态物理遮挡深度相机**（见 5.6.10）

#### 5.6.1 功能概述

`visual_grasp` 是 Level 4 的主节点,采用 **look-then-move（先看后动）** 策略:

```
观察姿态(俯视) → HSV 检测 → 深度+TF 算 base_link 坐标
   → 发布 target_pose → 调用 /arm_controller/pick → 完成
```

**为什么不做持续视觉伺服**：相机挂在机械臂末端 `arm_link4`（eye-in-hand）,下压抓取时相机会跟着进去,失去目标视野。look-then-move 在视野好的高位看准,再 IK 下去抓,工程上最稳。

**坐标变换无需手眼标定**: 相机通过 URDF(`camera_mount_joint` 挂 arm_link4)+ robot_state_publisher 提供 TF。物体坐标走 TF 链 `camera_depth_optical_frame → base_link`,实时反映机械臂姿态。

**pitch 约定(与 ik_analytical/web_server 一致)**: `0=朝上, 90°=水平, 180°=夹爪朝下`。抓取用 180°。

#### 5.6.2 启动文件功能介绍

视觉抓取系统需要 5 个 launch 文件协同工作，每个文件负责系统的一部分功能：

##### 1. bringup.launch.py — 底层驱动启动

**位置**：`bringup/launch/bringup.launch.py`

**功能**：
- 启动 STM32 板级驱动（`base_driver.launch.py`）：串口通信、IMU、电机、舵机、LED、蜂鸣器
- 启动底盘控制器（`chassis_controller.launch.py`）：
  - IMU 滤波（imu_filter_madgwick）
  - 里程计发布（odom_publisher）
  - EKF 融合（robot_localization）
  - 舵机控制器（servo_controller）
  - 初始位姿发布（init_pose）

**启动命令**：
```bash
ros2 launch car1_bringup bringup.launch.py
```

**关键话题/服务**：
- `/car1_base_driver/imu_raw` — 原始 IMU 数据
- `/imu` — 滤波后 IMU
- `/odom_raw` — 轮式里程计
- `/odometry/filtered` — EKF 融合里程计
- `/joint_states` — 舵机关节状态（20Hz 异步回读）
- `/car1_base_driver/bus_servo/set_position` — 舵机位置控制服务

**验证方法**：
```bash
# 检查 IMU 数据
ros2 topic hz /imu

# 检查关节状态回读
ros2 topic echo /joint_states --once

# 检查板级驱动初始化完成
ros2 topic echo /car1_base_driver/init_finish --once
```

---

##### 2. arm_controller.launch.py — 机械臂高层控制

**位置**：`arm/car1_arm_controller/launch/arm_controller.launch.py`

**功能**：
- 启动机械臂控制器节点（`arm_controller`）
- 提供高层 IK 接口和抓取服务
- 加载预设位姿配置（`preset_poses.yaml`）
- 加载机械臂参数（`arm_params.yaml`）

**可选参数**：
- `start_bringup:=true` — 同时启动 bringup（默认 false，假设已运行）

**启动命令**：
```bash
# 假设 bringup 已运行
ros2 launch car1_arm_controller arm_controller.launch.py

# 或一键启动（包含 bringup）
ros2 launch car1_arm_controller arm_controller.launch.py start_bringup:=true
```

**关键服务/话题**：
- `/arm_controller/target_pose` (PoseStamped) — IK 位姿控制
- `/arm_controller/joint_command` (JointState) — 直接关节角度控制
- `/arm_controller/pick` (Trigger) — 执行抓取序列
- `/arm_controller/place` (Trigger) — 执行放置序列
- `/arm_controller/set_gripper` (SetBool) — 夹爪开合
- `/arm_controller/go_home` (Trigger) — 回零位
- `/arm_controller/emergency_stop` (Trigger) — 紧急停止

**验证方法**：
```bash
# 检查服务是否就绪
ros2 service list | grep arm_controller

# 测试回零位
ros2 service call /arm_controller/go_home std_srvs/srv/Trigger

# 测试夹爪
ros2 service call /arm_controller/set_gripper std_srvs/srv/SetBool "{data: true}"
```

---

##### 3. depth_camera.launch.py — 深度相机驱动

**位置**：`peripherals/car1_peripherals/launch/depth_camera.launch.py`

**功能**：
- 启动 HP60C 深度相机节点（ascamera_node）
- 配置相机参数（分辨率、帧率、标定文件路径）
- **关键设计**：不使用 remap，保留原生话题名

**为什么不能 remap**：  
ascamera 驱动通过话题名子串 `"rgb0"` / `"depth0"` / `"ir0"` 判断流类型（见 `CameraPublisher.cpp:getSubTopicStreamType`）。如果 remap 将话题名改为 `/depth_cam/rgb/image_raw`，丢失 `"0"` 子串，驱动无法识别流类型，永不推流。

**启动命令**：
```bash
ros2 launch car1_peripherals depth_camera.launch.py
```

**发布话题（原生路径，不可 remap）**：
- `/ascamera_hp60c/camera_publisher/rgb0/image` — RGB 图像
- `/ascamera_hp60c/camera_publisher/depth0/image_raw` — 深度图（uint16, mm）
- `/ascamera_hp60c/camera_publisher/depth0/camera_info` — 相机内参
- `/ascamera_hp60c/camera_publisher/depth0/points` — 点云（可选）

**验证方法**：
```bash
# 检查相机话题（等≥10秒，驱动按需推流）
ros2 topic hz /ascamera_hp60c/camera_publisher/rgb0/image

# 检查相机内参
ros2 topic echo /ascamera_hp60c/camera_publisher/depth0/camera_info --once

# 查看 RGB 图像（需要 rqt_image_view）
ros2 run rqt_image_view rqt_image_view
```

**注意事项**：
- 相机驱动**按需推流**：无订阅者时会自动 `stop streaming`（日志正常），有订阅者 1-1.5 秒后自动 `start streaming`
- 检查帧率时需等待 ≥10 秒，避免过早退出 `ros2 topic hz`
- 第一帧通常是黑帧（自动曝光未生效），visual_grasp 会自动跳过

---

##### 4. rsp_only.launch.py — TF 树发布

**位置**：`app/car1_app/launch/rsp_only.launch.py`

**功能**：
- 启动 robot_state_publisher 节点
- 从 URDF 加载机器人模型
- 结合 `/joint_states` 发布完整 TF 树
- **关键作用**：提供 `base_link` → `camera_depth_optical_frame` 变换

**启动命令**：
```bash
ros2 launch car1_app rsp_only.launch.py
```

**发布 TF**：
- `base_link` → `arm_base_link` → ... → `arm_link4` → `camera_depth_optical_frame`
- TF 随 `/joint_states` 实时更新，反映机械臂当前姿态

**验证方法**：
```bash
# 检查 TF 树
ros2 run tf2_tools view_frames
# 生成 frames.pdf，检查 camera_depth_optical_frame 是否存在

# 实时查看特定变换
ros2 run tf2_ros tf2_echo base_link camera_depth_optical_frame
```

**为什么需要**：  
visual_grasp 需要将深度相机坐标系中的物体位置变换到 base_link 坐标系。由于相机安装在机械臂末端 `arm_link4`（eye-in-hand），TF 变换随机械臂姿态动态变化，robot_state_publisher 自动处理这种动态变换。

---

##### 5. visual_grasp.launch.py — 视觉抓取主节点

**位置**：`app/car1_app/launch/visual_grasp.launch.py`

**功能**：
- 启动 robot_state_publisher（与 rsp_only 功能相同，可复用或单独启动）
- 启动 visual_grasp 节点（视觉抓取主逻辑）
- 配置抓取参数（观察姿态、HSV 阈值、重试次数）

**启动命令**：
```bash
ros2 launch car1_app visual_grasp.launch.py

# 或单独运行节点（假设 rsp_only 已启动）
ros2 run car1_app visual_grasp
```

**可配置参数**：
```python
observe_pose: [0.20, 0.0, 0.22, 3.14159]  # 观察姿态 [x, y, z, pitch(rad)]
target_color_hsv_lower: [0, 80, 60]       # 红色 HSV 下界（低 H 端）
target_color_hsv_upper: [10, 255, 255]
target_color_hsv_lower2: [160, 80, 60]    # 红色 HSV 上界（高 H 端）
target_color_hsv_upper2: [180, 255, 255]
max_detection_attempts: 10                # 最多检测尝试次数
verify_after_pick: false                  # 抓取后是否验证
dry_run: false                            # 仅检测定位，不执行抓取（调试用）
```

**订阅话题**：
- `/ascamera_hp60c/camera_publisher/rgb0/image` — RGB 图像（HSV 检测）
- `/ascamera_hp60c/camera_publisher/depth0/image_raw` — 深度图（3D 定位）
- `/ascamera_hp60c/camera_publisher/depth0/camera_info` — 相机内参
- `/joint_states` — 关节状态（通过 robot_state_publisher → TF）

**发布话题**：
- `/arm_controller/target_pose` — 目标位姿（观察姿态、抓取位置）
- `/visual_grasp/debug_image` — 调试图像（RGB + 检测框）
- `/visual_grasp/mask` — HSV 掩码（白色=匹配像素）

**调用服务**：
- `/arm_controller/pick` — 执行抓取序列

**验证方法**：
```bash
# 查看调试图像（检测框、轮廓）
ros2 run rqt_image_view rqt_image_view
# 选择 /visual_grasp/debug_image

# 查看 HSV 掩码（白色区域=检测到的红色）
# 选择 /visual_grasp/mask

# 监控节点日志
ros2 run car1_app visual_grasp
# 观察状态机流程：INIT → MOVE_TO_OBSERVE → DETECT → PICK → DONE
```

---

#### 5.6.3 启动顺序与依赖关系

**推荐启动顺序**（5 个终端，逐个启动，中间留 2-3 秒）：

```
终端1: bringup.launch.py
         ↓ (等待 init_finish)
终端2: arm_controller.launch.py
         ↓ (等待 arm_controller 服务就绪)
终端3: depth_camera.launch.py
         ↓ (等待相机话题发布)
终端4: rsp_only.launch.py (或在终端5启动 visual_grasp.launch.py 时自动启动)
         ↓ (等待 TF 树发布)
终端5: visual_grasp (节点或 launch 文件)
```

**依赖关系**：
- `arm_controller` 依赖 `bringup` 的 `/car1_base_driver/bus_servo/set_position` 服务
- `robot_state_publisher` (rsp_only) 依赖 `bringup` 的 `/joint_states` 话题
- `visual_grasp` 依赖：
  - `depth_camera` 的相机话题
  - `arm_controller` 的 `/arm_controller/pick` 服务
  - `robot_state_publisher` 的 TF 树（`base_link` → `camera_depth_optical_frame`）

**启动脚本示例**：
```bash
#!/bin/bash
# 一键启动视觉抓取系统（示例）

# 终端1: bringup
gnome-terminal -- bash -c "source /home/iflytek/ros2_ws/install/setup.bash; \
  ros2 launch car1_bringup bringup.launch.py; exec bash"

sleep 5

# 终端2: arm_controller
gnome-terminal -- bash -c "source /home/iflytek/ros2_ws/install/setup.bash; \
  ros2 launch car1_arm_controller arm_controller.launch.py; exec bash"

sleep 3

# 终端3: depth_camera
gnome-terminal -- bash -c "source /home/iflytek/ros2_ws/install/setup.bash; \
  ros2 launch car1_peripherals depth_camera.launch.py; exec bash"

sleep 3

# 终端4+5: visual_grasp.launch.py（包含 rsp_only + visual_grasp）
gnome-terminal -- bash -c "source /home/iflytek/ros2_ws/install/setup.bash; \
  ros2 launch car1_app visual_grasp.launch.py; exec bash"
```

---

#### 5.6.4 前置修改说明

调试 Level 4 时修复了一连串底层 bug(详见 TODO.md)。**首次使用前必须重新编译并重启 bringup**:

| 文件 | 改动 |
|------|------|
| `car1_servo_controller/.../joint_position_controller.py` | 角度量程 240°→270°,与 transform.py 一致;读取方向去掉限位钳位 |
| `car1_servo_controller/.../controller_manager_node.py` | joint_states 改为主线程 timer 异步回读舵机实际位置(20Hz, round-robin) |
| `car1_base_driver/.../board_sdk.py` | 修正 `_bus_servo_read` 响应字节布局(原只有 ID5 能读) |
| `car1_servo_controller/config/servo_controller.yaml` | arm 关节限位放宽到 500-2500 硬件极限 |
| `car1_arm_controller/.../arm_controller.py` | IK 改用 `ik_analytical.py`(含 elbow 分支+PHI补偿);pitch 约定对齐 |
| `car1_peripherals/.../depth_camera.launch.py` | **去掉 remap 和自定义 node 名**(remap 会破坏相机推流) |
| `car1_app/.../visual_grasp.py` | 订阅相机原生话题;跳过黑帧;深度采样改整轮廓 |

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select car1_servo_controller car1_base_driver car1_arm_controller car1_peripherals car1_app
source install/setup.bash
```

#### 5.6.5 启动步骤（5 个终端，逐个启动）

每个终端都先 `cd ~/ros2_ws && source install/setup.bash`。

```bash
# 终端1: 底盘 + 舵机驱动(含 joint_states 回读)
ros2 launch car1_bringup bringup.launch.py

# 终端2: 机械臂控制器(提供 /arm_controller/pick)
ros2 launch car1_arm_controller arm_controller.launch.py

# 终端3: 深度相机(原生话题,绝不能 remap)
ros2 launch car1_peripherals depth_camera.launch.py

# 终端4: robot_state_publisher(发布 TF 树,visual_grasp 定位依赖它)
ros2 launch car1_app rsp_only.launch.py

# 终端5: 视觉抓取主节点
ros2 run car1_app visual_grasp
```

桌上放红块在机械臂前方 15-25cm。

> **重要**:必须按 1→2→3→4→5 顺序,中间留 2-3 秒。终端2 等终端1 的 init_finish;终端4 的 TF 依赖终端1 的 joint_states;终端5 等终端2/3/4 全部就绪。
>
> **相机话题是原生路径**(无 remap):
> ```
> /ascamera_hp60c/camera_publisher/rgb0/image         # RGB
> /ascamera_hp60c/camera_publisher/depth0/image_raw   # 深度
> /ascamera_hp60c/camera_publisher/depth0/camera_info # 内参
> /ascamera_hp60c/camera_publisher/depth0/points      # 点云
> ```

#### 5.6.6 状态机流程

```
INIT → MOVE_TO_OBSERVE → WAIT_STABLE(3s) → DETECT
   → COMPUTE_TARGET → PICK → DONE / FAILED
```

**预期日志**：
```
[INFO] Camera intrinsics: fx=594.5, fy=594.8, cx=350.3, cy=237.5
[INFO] State: INIT -> MOVE_TO_OBSERVE
[INFO] Published observation pose: x=0.2, y=0.0, z=0.22, pitch=180.0°
[INFO] State: MOVE_TO_OBSERVE -> WAIT_STABLE
[INFO] Arm stabilized, starting detection...
[INFO] State: WAIT_STABLE -> DETECT
[INFO] Object detected at base_link: [0.20, 0.01, 0.00]
[INFO] State: DETECT -> COMPUTE_TARGET
[INFO] State: COMPUTE_TARGET -> PICK
[INFO] Calling /arm_controller/pick...
[INFO] Pick completed successfully
```

#### 5.6.7 可调参数

在 `visual_grasp` 启动时通过 `--ros-args -p` 覆盖:

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `observe_pose` | `[0.20, 0.0, 0.22, 3.14159]` | 观察姿态 [x, y, z, pitch(rad)]。pitch=π=夹爪朝下 |
| `target_color_hsv_lower` | `[0, 100, 80]` | 红色 HSV 下界 |
| `target_color_hsv_upper` | `[10, 255, 255]` | 红色 HSV 上界 |
| `max_detection_attempts` | `5` | 检测重试次数 |
| `verify_after_pick` | `false` | 抓取后是否回观察姿态二次验证 |

```bash
# 例: 改观察姿态 + 追蓝色
ros2 run car1_app visual_grasp --ros-args \
  -p observe_pose:='[0.18, 0.0, 0.24, 3.14159]' \
  -p target_color_hsv_lower:='[100, 100, 80]' \
  -p target_color_hsv_upper:='[130, 255, 255]'
```

#### 5.6.8 分层验证（逐环节，出问题好定位）

**第 1 层：相机话题与内参**(注意原生话题路径)
```bash
ros2 topic list | grep ascamera
ros2 topic hz /ascamera_hp60c/camera_publisher/rgb0/image     # 等≥10秒,应~11Hz
ros2 topic echo /ascamera_hp60c/camera_publisher/depth0/camera_info --once   # k 数组有 fx/fy/cx/cy
```

> 相机驱动**按需推流**: 没订阅者时日志会打 `stop streaming`(正常),一旦有订阅(hz/visual_grasp)1~1.5 秒后自动 `start streaming`。所以 hz 要等够 10 秒,别立刻 Ctrl+C。

**第 2 层：图像可视化**
```bash
# venv 里缺 PyQt5 时,先把系统 PyQt5 软链接进 venv(勿 pip 编译,会 OOM):
#   ln -s /usr/lib/python3/dist-packages/PyQt5 ~/ros2_venv/lib/python3.10/site-packages/
ros2 run rqt_image_view rqt_image_view
# 选 /ascamera_hp60c/camera_publisher/rgb0/image,把红块放进视野
```

**第 3 层：TF 链路**
```bash
ros2 run tf2_ros tf2_echo base_link camera_depth_optical_frame
# 应持续打印 Translation/Rotation,且随机械臂姿态变化
```

**第 4 层：joint_states 实际回读**
```bash
ros2 topic echo /joint_states --once
# position 应反映实际舵机位置;与 interactive_ik_test.py --direct 读回 PWM 转角度对比应一致
```

**第 5 层：完整抓取**
```bash
ros2 run car1_app visual_grasp
# 观察日志: 抬到观察姿态 → 检测 → 下压抓取 → 提升
```

#### 5.6.9 故障排查

| 现象 | 检查命令 | 解决方向 |
|------|---------|---------|
| 相机话题无数据 | `ros2 topic hz /ascamera_hp60c/camera_publisher/rgb0/image`(等10秒) | 别用 remap 的话题;确认订阅触发推流 |
| RGB 全黑 | 抓多帧看亮度 | 第1帧是黑的(自动曝光),visual_grasp 已自动跳过 |
| 检测不到红色 | rqt 看 RGB | 调 HSV 阈值;确认红块在视野且光照足 |
| **深度全 0 / "No valid depth"** | 见 5.6.10 | **观察姿态物理遮挡，当前已知卡点** |
| TF 变换失败 | `ros2 run tf2_tools view_frames` | 终端4 的 rsp_only 没起来 |
| pick 服务超时 | `ros2 service list \| grep pick` | 终端2 arm_controller 没启动 |
| IK 无解 / limit violation | 看日志 | 物体超工作空间;换近点位置 |
| 夹爪没夹住 | — | 调 arm_controller 的 `gripper_depth` 参数 |

#### 5.6.10 ⚠️ 当前已知卡点：观察姿态物理遮挡深度相机

**端到端抓取尚未通过**，卡在深度定位。已确认是**物理遮挡问题，非配置或代码 bug**。

**问题描述**（2026-06-18 确认）：

在观察姿态 `[0.2, 0.0, 0.22, π]` 时，机械臂/夹爪物理遮挡了深度相机（HP60C）的红外投影器视野，导致桌面物体位置的深度数据无法获取。

**实验验证**：
- 单独启动相机驱动（无机械臂）：深度数据正常，覆盖率 ~54%
- 机械臂移动到观察姿态后：
  - 图像上半部分（0-240 行）：54.4% 有效深度 → 能看到机械臂和背景
  - **图像下半部分（240-480 行）：11.8% 有效深度 → 桌面被遮挡！**
  - 红色物块检测成功（RGB 图像中心 ~(368, 279)，面积 ~5500px）
  - 但红块所在像素区域深度值全为 0（空洞）

**根本原因**：  
相机安装在 `arm_link4`（eye-in-hand），观察姿态时机械臂下压，夹爪挡在深度传感器前方，遮挡了向前下方的视野。有效深度区域全部指向机器人后方（base_link 负 X 方向），无法覆盖前方桌面。

**诊断命令**：
```bash
# 查看深度图分布（运行时）
ros2 topic echo /ascamera_hp60c/camera_publisher/depth0/image_raw --once

# 可视化深度图（rqt）
ros2 run rqt_image_view rqt_image_view
# 选择 /ascamera_hp60c/camera_publisher/depth0/image_raw
# 观察有效深度区域（白色）是否覆盖物体位置
```

**待定解决方案**：

1. **调整观察姿态（推荐）**：
   - 增大 Z 高度（抬高机械臂）：`observe_pose: [0.20, 0.0, 0.28, π]`
   - 或向后退一点：`observe_pose: [0.15, 0.0, 0.25, π]`
   - 目标：让深度相机视野清空，能看到桌面

2. **改用已知平面投影（备选）**：
   - 物体与底座同高（z 已知）
   - 用 RGB 像素 + 相机内参 + TF 反算光线与 z=0 平面交点
   - **完全不依赖深度**，绕开遮挡问题
   - 需要修改 `visual_grasp.py` 中的 `_detect_and_localize` 方法

3. **换用 eye-to-hand 安装（长期方案）**：
   - 将相机固定在机器人基座或外部支架
   - 不随机械臂移动，视野稳定
   - 需要手眼标定

#### 5.6.11 验证要点

- [x] 相机话题正常（RGB ~11Hz、深度图、camera_info 都有）
- [x] TF 链 `base_link → camera_depth_optical_frame` 完整，随姿态更新
- [x] joint_states 反映实际舵机位置
- [x] 红色物体 HSV 检测成功
- [x] 机械臂 IK 控制 + pitch=180° 夹爪垂直向下
- [ ] **物体 3D 定位**（卡在观察姿态物理遮挡，见 5.6.10）
- [ ] 完整抓取流程跑通
- [ ] 不同位置物体均能抓取

#### 5.6.12 下一步

先解决 5.6.10 的深度遮挡问题（推荐方案：调整观察姿态高度或使用已知平面投影）。完整抓取通过后，可进入 Level 5（导航 + 视觉 + 抓取）。

---

#### 5.6.13 实时可视化调试（2026-07-07 新增）

visual_grasp 现在会把 **RGB / Depth / HSV Mask** 三栏并排 + 检测标注 + 坐标信息合成一张图，通过 ROS 话题 `/visual_grasp/visualization` 持续发布（~10Hz）。SSH 远程调试时通过 `rqt_image_view` 查看，比 OpenCV `imshow` 稳定得多（SSH -X 转发下 OpenCV 会黑屏，Qt/rqt 正常）。

**启动可视化**：
```bash
# 终端 A：启动 visual_grasp（默认 enable_viz=True）
ros2 launch car1_app visual_grasp.launch.py

# 终端 B：打开可视化窗口
ros2 run rqt_image_view rqt_image_view /visual_grasp/visualization
```

**画面布局**：

```
┌────────────────────────────────────────────────────────┐
│ State: WAIT_CONFIRMATION | Centroid: (u,v) | Depth: Xmm │  ← 顶部信息栏
├────────────┬────────────┬─────────────────────────────┤
│ RGB        │ Depth      │ HSV Mask                    │
│ + 检测轮廓 │ + 检测轮廓 │ + 匹配区域                  │  ← 三栏对齐
│ + BBox     │ + BBox     │ + 十字质心                  │
│ + 红十字   │ + 白十字   │ + 绿十字                    │
│ + TARGET   │ + 深度mm值 │                             │
└────────────┴────────────┴─────────────────────────────┘
│ Camera: (x, y, z) m                                    │
│ Base:   (x, y, z) m                                    │  ← 底部坐标栏
│ Joints: [j1°, j2°, j3°, j4°, j5°]  |  TF age: 0.05s   │
└────────────────────────────────────────────────────────┘
```

**每个信息的含义**：

| 元素 | 含义 | 判断用途 |
|------|------|---------|
| `State` | 状态机当前状态（INIT/MOVE_TO_OBSERVE/…/WAIT_CONFIRMATION/PICK） | 定位卡在哪一步 |
| `Centroid: (u, v) px` | 红块质心的**像素坐标** | 验证 HSV 检测是否命中 |
| `Depth: Xmm` | 质心处的**深度值**（毫米） | 用尺子对比是否合理 |
| **左栏 RGB** | 相机实时彩图 + 检测轮廓（绿色）+ Bounding Box（黄色）+ 红十字质心 | 目测检测框是否贴合红块 |
| **中栏 Depth** | JET 色彩深度图 + 白色十字 + 深度值 | 与 RGB 十字位置**对比**判断 D2C 对齐 |
| **右栏 HSV Mask** | HSV 阈值命中的白色区域 + 绿十字 | 判断 HSV 是否收得太宽（背景污染）或太窄（红块缺失） |
| `Camera: (x, y, z) m` | 红块在**相机光学系**的坐标（x 右, y 下, z 前） | 反投影是否正确（红块在图像中央时 x/y 应 ≈ 0） |
| `Base: (x, y, z) m` | 红块在**base_link** 的坐标（x 前, y 左, z 上） | **抓取用的核心坐标**，需要用尺子校验 |
| `Joints: [j1°..j5°]` | 当前 5 个机械臂关节角（度） | 判断机械臂是否到达命令姿态 |
| `TF age` | 用于坐标变换的 TF 数据的年龄（秒） | 越小越好，>0.5s 说明 joint_states 更新慢 |

**逐层验证顺序**（出问题时按这个顺序排查）：

1. **HSV** — 右栏 Mask 里红块是否白色连续区域？→ 不是就调 `target_color_hsv_lower/upper`
2. **质心** — 左栏 RGB 红十字是否在红块中心？→ 不在就检查轮廓是否被污染
3. **D2C 对齐** — RGB 红十字 vs Depth 白十字位置是否重合（±2px）？→ 偏差大就是相机 D2C 配准问题
4. **深度** — 顶部 `Depth: Xmm` 是否与尺子实测接近？→ 差 >20mm 说明相机有系统偏差
5. **相机坐标** — 底部 `Camera` 行是否符合视觉直觉？→ 红块在画面中间时 x/y 应接近 0
6. **Base 坐标** — 底部 `Base` 行 z 是否接近桌面高度？→ z 明显偏大说明 TF 错了（机械臂姿态错 or URDF 错）

---

#### 5.6.14 检测后暂停确认 + 服务触发继续

visual_grasp 默认参数 `wait_for_confirmation: True`，检测成功后进入 `WAIT_CONFIRMATION` 状态**持续实时刷新**可视化，等待用户手动确认再抓取。

> **注意**：因为 ROS launch 会重定向 stdin，键盘按 Enter 检测不到，所以用 **ROS 服务**触发。

**三个控制服务**：

```bash
# 确认坐标正确，开始抓取
ros2 service call /visual_grasp/confirm std_srvs/srv/Trigger

# 跳过这次物体（进入 DONE 状态）
ros2 service call /visual_grasp/skip std_srvs/srv/Trigger

# 中止抓取（进入 FAILED 状态）
ros2 service call /visual_grasp/abort std_srvs/srv/Trigger
```

**典型使用流程**：

```bash
# 终端 1：启动 visual_grasp
ros2 launch car1_app visual_grasp.launch.py

# 终端 2：打开可视化
ros2 run rqt_image_view rqt_image_view /visual_grasp/visualization

# 等待日志出现 "=== PAUSED FOR REVIEW ==="
# 观察可视化底部的 Base 坐标是否合理

# 终端 3：确认后触发抓取
ros2 service call /visual_grasp/confirm std_srvs/srv/Trigger
```

**关闭确认模式**（一步到位自动抓取）：

修改 `visual_grasp.launch.py`：
```python
'wait_for_confirmation': False   # 检测成功后直接抓取
```

---

#### 5.6.15 舵机按需读回架构（2026-07-07 修改）

**旧问题**：`servo_controller` 5Hz round-robin 主动读舵机 PWM，但读响应容易和请求错位（响应包 `state.position[0]` 属于哪个 servo_id 没做校验），导致 `/joint_states` 报错误角度 → TF 变换错乱 → Base 坐标荒谬（z 常出现 0.5m 半空中）。

**新架构**：
1. **默认用命令值缓存**：`servo_controller_callback` / `joint_controller_callback` 收到命令时立即把命令 PWM 写入 `last_actual_positions`，`/joint_states` 5Hz 从这个缓存发布。**平时 joint_states 反映"命令的舵机位置"**，无串口开销。
2. **按需刷新真实位置**：新服务 `/servo_controller/refresh_positions` 阻塞式读所有 6 个舵机的真实 PWM（含 ID 校验），返回 success/message。
3. **超时机制**：单关节 `read_timeout=1.5s` 可配置，任一关节超时该关节保留旧缓存，服务整体返回 `success=False` + 罗列失败关节，业务方决定是否继续。
4. **MultiThreadedExecutor + ReentrantCallbackGroup**：服务回调等 `get_state_client` future 时，另一个 executor 线程处理 get_state 响应，避免单线程死锁。

**visual_grasp 的调用时机**：`_detect_and_localize` 在做 `lookup_transform` **之前**调 `_refresh_joints_sync()`，确保 TF 反映**做检测那一刻**的真实机械臂姿态（而非命令姿态）。这样即使 IK 有偏差导致机械臂物理位置和命令位置不一致，视觉抓取坐标仍然基于真实姿态计算，是准的。

**手动调用刷新**：
```bash
ros2 service call /servo_controller/refresh_positions std_srvs/srv/Trigger

# 成功返回：
# success: True
# message: 'refreshed: arm_joint1=1499, arm_joint2=1100, ...'

# 部分失败：
# success: False
# message: 'failed: [arm_joint2(timeout)] refreshed: [arm_joint1=..., ...]'
```

**验证 joint_states 是否用真实值**（重要！）：
```bash
# 用手把机械臂稍微掰动一下（或让 arm_controller 命令它到某个位置）
ros2 topic echo /joint_states --once

# 对比直接读回底层：
ros2 service call /car1_base_driver/bus_servo/get_state \
  car1_base_driver_msgs/srv/GetBusServoState \
  "{cmd: [{id: 0, get_position: 1}]}"

# 两者应该 一致（如果 arm_controller 命令值已经写入缓存）
# 如果不一致，说明缓存没同步 → 需要手动 refresh_positions
```

**⚠️ 串口冲突陷阱**（新踩过的坑）：`test_servo_direct.py` 和 bringup 都会打开 `/dev/ttyUSB0`。Linux 允许多进程同时打开 tty，但只有一个能读到完整数据，另一个 `board_sdk._recv_task` 会抛 `SerialException`，daemon 线程死掉。**症状**：`refresh_positions` 6 个关节全 timeout，但 base_driver 进程还活着。**排查**：`lsof /dev/ttyUSB0` 看有几个进程占用，超过 1 个就是这个坑，必须完全停 bringup 再跑 test 脚本。已在 `board_sdk._recv_task` 加了 try/except 兜底（异常后 sleep 0.1s 重试而非杀线程），但仍应避免共用串口。

---

#### 5.6.16 URDF 相机原点标定（2026-07-07 处理经验）

**发现方式**：观察姿态下（相机朝下看桌面），红块放到相机镜头**正下方**（人眼判断的正下方），可视化显示 `Camera: (0.019, 0, 0.24) m` 而非 `(0, 0, 0.24)`。说明 URDF 里的**深度相机光心位置**与物理光心有 ~19mm 偏差。

**标定方法**（快速 offset 修正）：

1. 让机械臂到观察姿态，把红块**用眼睛对准相机镜头正下方**放置
2. 看 visual_grasp 报的 `Camera: (Δx, Δy, z)` 值
3. Δx/Δy 就是当前 URDF 里光心位置的偏差
4. 修改 `camera_depth_joint` 的 y 分量（因为该 joint 有 rpy 旋转，URDF 里的 y 对应物理左右方向）：

**修改位置**：`simulations/car1_description/urdf/car1.urdf` 里的 `camera_depth_joint`

```xml
<joint name="camera_depth_joint" type="fixed">
    <origin
      xyz="-0.0002257 <NEW_Y> 0.02494901"       <!-- 只改中间 y -->
      rpy="-1.57079706 -1.57079266 -1.56958489" />
    <parent link="camera_mount_link" />
    <child link="camera_depth_link" />
</joint>
```

`NEW_Y = 0.00199994 - Δx`（Δx 是 visual_grasp 显示的相机 x 坐标，符号需要试）。方向不确定时：
- 先试 `NEW_Y = 0.00199994 - 0.01944 = -0.01744006`（原值减 19.44mm）
- 如果 Camera x 反向变大，说明改反了，改成 `NEW_Y = 0.00199994 + 0.01944 = 0.02143994`

**编译 + 完整重启**（关键！）：

```bash
colcon build --packages-select car1_description --symlink-install
source install/setup.bash

# URDF 是 robot_state_publisher 启动时读一次，只重启 visual_grasp 不够，
# 必须重启 bringup 里的 robot_state_publisher。最简单：全部重启。
pkill -f 'ros2 launch'
sleep 2

# 按原顺序依次启动
ros2 launch car1_bringup bringup.launch.py               # 终端1
ros2 launch car1_arm_controller arm_controller.launch.py # 终端2
ros2 launch car1_peripherals depth_camera.launch.py      # 终端3
ros2 launch car1_app visual_grasp.launch.py              # 终端4
```

**验证**：
```bash
ros2 run tf2_ros tf2_echo camera_depth_link camera_depth_optical_frame
# Translation 应该反映新的偏移
```

然后再把红块放到相机正下方，检查 `Camera: (x, y, z)` 中 x 是否接近 0。

---

#### 5.6.17 抓取高度参数（gripper_depth / pre_grasp_height）

**问题背景**：`tcp_link` 在 URDF 里的定义位置（`arm_link5` 下方 76.2mm）并不是夹爪的**物理指尖**，指尖比 tcp_link 还往下延伸 **33mm**。如果不补偿，arm_controller 会把 TCP 直接下压到 `Base.z`（红块表面高度），实际夹爪指尖会撞穿桌面。

**修复**：在 `arm/car1_arm_controller/config/arm_params.yaml` 加参数：

```yaml
/**:
  ros__parameters:
    # ... 前面参数

    # 抓取参数
    # tcp_link 定义位置到夹爪最前端还差 33mm，抓取时 TCP 要停高 33mm，
    # 让指尖到达检测到的红块表面位置（否则指尖会撞地面/桌面）
    gripper_depth: -0.033      # TCP 高于目标 33mm（负值 = 抬高）
    pre_grasp_height: 0.03     # 预抓取高度（目标上方 3cm）
```

**arm_controller 的抓取序列**（`gripper_depth = -0.033` 时）：

```
输入 Base.z = 0.013m（红块表面）

1. TCP 移到 (x, y, z + pre_h) = (x, y, 0.043)   预抓取
   → 指尖在 0.043 - 0.033 = 0.010m ≈ 红块上方（安全）

2. 张开夹爪

3. TCP 下降到 (x, y, z - gripper_depth) = (x, y, 0.013 - (-0.033)) = (x, y, 0.046)   抓取
   → 指尖在 0.046 - 0.033 = 0.013m = 红块表面 ✓

4. 闭合夹爪
5. TCP 提起到 (x, y, 0.043)
```

**微调 gripper_depth**（第一次测试**先设保守值 -0.038**，多留 5mm 余量避免撞台）：

| 现象 | 说明 | 调整 |
|------|------|------|
| 指尖撞桌面 | 停得太低 | `gripper_depth` 减小（更负），如 -0.038 → -0.043 |
| 指尖悬在红块上方，夹不到 | 停得太高 | `gripper_depth` 增大（不那么负），如 -0.033 → -0.028 |
| 指尖到位但夹到红块顶部滑走 | 夹到边缘 | 让指尖再下 `半个红块高度`，如红块 30mm 高就 -0.033 + 0.015 = -0.018 |

**注意**：如果换了不同高度的物体（比如从 30mm 方块换成 50mm 方块），`gripper_depth` 需要重调，或者干脆在代码里让 `visual_grasp` 用**深度中位数扣除物体半高**的方式发布"物体中心 z"。

**长期方案（推荐但未做）**：直接改 URDF 让 `tcp_link` 移到夹爪指尖位置（把 `tcp_joint.origin.xyz.z` 从 0.0762 改成 0.0762 + 0.033 = 0.1092），同时相应改 IK 的 `toolFromJ4.z`（从 0.150642 → 0.183642），然后 `gripper_depth` 可以回到 0。这样 TCP 定义和物理夹尖一致，所有代码都自然。

---

#### 5.6.18 已知问题：IK 和物理姿态不一致

**现象**：命令观察姿态 `(0.20, 0.0, 0.22, pitch=π)`，IK 解出 `q = (0°, +15°, +47°, +118°, 0°)`，对应 PWM ≈ `(1499, 1672, 2037, 2838, 1500)`。舵机执行到这个 PWM 后，机械臂**物理上**并没有到 `(0.20, 0, 0.22)`，末端偏斜、朝斜上方，导致相机看不到桌面、TF 变换出的 Base 坐标飞到 60cm 高。

**根源**：`ik_analytical.py` + `config.py` 用的 DH 参数（`J1_origin`、`J2_offset`、`link1/link2/toolFromJ4`）与实际机械臂装配不完全匹配。因此 IK 计算的关节角**在 URDF 模型里**能到目标，但物理机械臂到不了。

**当前 workaround**：`visual_grasp._detect_and_localize` 在 TF lookup **之前**主动调 `refresh_positions` 服务，让 `/joint_states` 反映真实关节角，然后 robot_state_publisher 基于真实角度算 TF。这样物体 Base 坐标是**基于机械臂物理实际姿态**算出来的，即使姿态不是命令的姿态，坐标本身依然准确 —— 因为坐标只需要"相机在哪 + 相机看到什么"就能得到。

**长期修复**：需要精细标定 DH 参数（`config.py:RobotCalibration`），或用 AprilTag 手眼标定。

---



## 常见问题

### 编译问题

**Q: colcon build 报错找不到包**
```bash
# 检查依赖是否安装
rosdep install --from-paths src --ignore-src -r -y

# 或手动安装缺失的包
sudo apt install ros-${ROS_DISTRO}-<package-name>
```

**Q: Python 模块导入错误**
```bash
# 检查 Python 路径
echo $PYTHONPATH

# 重新 source
source install/setup.bash
```

### 硬件连接问题

**Q: 串口权限不足**
```bash
# 临时授权
sudo chmod 666 /dev/ttyUSB0

# 永久授权
sudo usermod -aG dialout $USER
# 重新登录生效
```

**Q: 找不到串口设备**
```bash
# 查看所有串口
ls /dev/tty*

# 查看 USB 设备
lsusb

# 查看内核日志
dmesg | grep tty
```

### 运行时问题

**Q: 节点启动失败**
```bash
# 查看详细日志
ros2 launch <package> <launch_file> --log-level debug

# 检查节点是否运行
ros2 node list

# 检查话题
ros2 topic list
```

**Q: TF 变换错误**
```bash
# 查看 TF 树
ros2 run tf2_tools view_frames

# 检查特定变换
ros2 run tf2_ros tf2_echo base_link laser_link
```

**Q: 雷达数据异常**
```bash
# 检查雷达话题
ros2 topic echo /scan

# 检查雷达参数
ros2 param list /m1ct_d2_node
```

**Q: 相机无图像**
```bash
# 检查相机设备
ls /dev/video*

# 测试相机
cheese  # 或其他相机测试工具

# 检查 ROS2 话题
ros2 topic hz /depth_cam/rgb/image_raw
```

### 导航问题

**Q: AMCL 定位不准**
- 重新设置初始位姿（2D Pose Estimate）
- 检查地图是否正确加载
- 调整 AMCL 参数（粒子数、更新频率）

**Q: 路径规划失败**
- 检查目标点是否在障碍物内
- 检查机器人半径参数是否正确
- 清除代价地图：`ros2 service call /global_costmap/clear_entirely_global_costmap std_srvs/srv/Empty`

**Q: 导航震荡**
- 降低最大速度
- 调整 TEB 参数（weight_kinematics_nh, min_obstacle_dist）
- 增大 inflation_radius

### 性能问题

**Q: CPU 占用过高**
- 降低传感器发布频率
- 减少 AMCL 粒子数
- 关闭不必要的可视化

**Q: 延迟过大**
- 检查网络连接（如使用远程机器）
- 降低图像分辨率
- 使用更快的算法

---

## 学习资源

### 官方文档

- [ROS2 官方文档](https://docs.ros.org/en/jazzy/)
- [Nav2 文档](https://navigation.ros.org/)
- [slam_toolbox 文档](https://github.com/SteveMacenski/slam_toolbox)
- [Gazebo 文档](https://gazebosim.org/docs)

### 推荐教程

- ROS2 基础教程
- Nav2 导航教程
- MoveIt2 运动规划教程
- OpenCV 视觉处理教程

### 社区支持

- ROS Discourse: https://discourse.ros.org/
- ROS Answers: https://answers.ros.org/
- GitHub Issues: 项目仓库 Issues 页面

---

## 总结

完成本教程后，你应该掌握：

- ✅ ROS2 基本操作和工具使用
- ✅ 机器人仿真和实物控制
- ✅ SLAM 建图和自主导航
- ✅ 视觉和雷达应用开发
- ✅ 常见问题排查和解决

**下一步建议**：
1. 深入学习 ROS2 核心概念（节点、话题、服务、参数）
2. 学习机器人运动学和控制理论
3. 尝试开发自己的应用功能
4. 参与开源社区，贡献代码

祝学习愉快！🚀

