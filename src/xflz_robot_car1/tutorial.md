# xflz_robot_car1 使用教程

## 项目结构

```
xflz_robot_car1/
├── simulations/
│   ├── car1_description/      # URDF 模型 + RViz 可视化
│   ├── car1_moveit_config/    # MoveIt2 运动规划仿真
│   └── car1_gazebo/           # Gazebo 物理仿真
├── arm/                       # 机械臂运动学
├── bringup/                   # 启动配置
├── navigation/                # 导航（待开发）
└── slam/                      # SLAM（待开发）
```

---

## 1. URDF 模型可视化 (car1_description)

在 RViz 中查看机器人模型，通过滑块控制关节运动。

```bash
ros2 launch car1_description display.launch.py
```

启动后会打开：
- **Joint State Publisher GUI** — 拖动滑块控制 arm_joint1~5、r_joint 等关节
- **RViz2** — 显示机器人 3D 模型

---

## 2. MoveIt2 运动规划仿真 (car1_moveit_config)

使用 MoveIt2 进行机械臂运动规划和夹爪控制。

```bash
ros2 launch car1_moveit_config demo.launch.py
```

启动后 RViz 中会出现 **MotionPlanning** 面板，可以：

### 规划组说明

| 规划组 | 关节 | 说明 |
|--------|------|------|
| arm | arm_joint1 ~ arm_joint5 | 5自由度机械臂 |
| gripper | r_joint (主) + 5个mimic关节 | 夹爪开合 |

### 操作步骤

1. 在 **Planning** 标签页的 **Planning Group** 中选择 `arm` 或 `gripper`
2. 拖动末端执行器到目标位置（交互式标记）
3. 点击 **Plan & Execute** 执行运动规划
4. 也可在 **Goal State** 中选择预设位姿（如 `home`、`open`、`close`）

### 预设位姿

- **arm/home** — 机械臂回到零位
- **gripper/open** — 夹爪张开（r_joint = 0.5）
- **gripper/close** — 夹爪闭合（r_joint = 0）

---

## 3. Gazebo 物理仿真 (car1_gazebo)

在 Gazebo 物理引擎中仿真机器人运动，支持机械臂和夹爪的物理交互。

### 3.1 依赖安装

```bash
sudo apt update
sudo apt install -y \
    ros-${ROS_DISTRO}-ros-gz-sim \
    ros-${ROS_DISTRO}-ros-gz-bridge \
    ros-${ROS_DISTRO}-ros-gz-interfaces \
    ros-${ROS_DISTRO}-gz-ros2-control \
    ros-${ROS_DISTRO}-ros2-control \
    ros-${ROS_DISTRO}-ros2-controllers \
    ros-${ROS_DISTRO}-controller-manager \
    ros-${ROS_DISTRO}-joint-state-broadcaster \
    ros-${ROS_DISTRO}-joint-trajectory-controller \
    ros-${ROS_DISTRO}-joint-state-publisher \
    ros-${ROS_DISTRO}-joint-state-publisher-gui \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-tf2-tools
```

### 3.2 编译与启动

```bash
# 进入工作空间
cd ~/xflz_robot_car1_ros2_ws

# 编译
colcon build --packages-select car1_description car1_gazebo

# 加载环境变量
source install/setup.bash

# 启动 Gazebo 仿真
ros2 launch car1_gazebo gazebo_arm.launch.py
```

启动后会：
1. 打开 Gazebo 仿真环境
2. 生成 car1 机器人模型
3. 自动启动以下控制器：
   - `joint_state_broadcaster` — 发布关节状态
   - `arm_controller` — 机械臂轨迹控制器
   - `gripper_controller` — 夹爪控制器

### 3.3 测试

Gazebo 启动后，打开一个**新终端**，先加载环境：

```bash
source /opt/ros/jazzy/setup.bash
source ~/xflz_robot_car1_ros2_ws/install/setup.bash
```

#### 检查控制器状态

```bash
ros2 control list_controllers

# 应该看到：
# joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
# arm_controller[joint_trajectory_controller/JointTrajectoryController] active
# gripper_controller[joint_trajectory_controller/JointTrajectoryController] active
```

确认 3 个控制器都是 `active` 状态后，继续测试。

#### 测试机械臂运动

```bash
# 移动机械臂到指定位置
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

#### 测试夹爪开合

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

#### 查看关节状态

```bash
# 实时查看所有关节状态（Ctrl+C 退出）
ros2 topic echo /joint_states
```

#### 完整测试流程

依次执行以下命令验证机械臂各功能：

```bash
# 第 1 步：确认控制器正常
ros2 control list_controllers

# 第 2 步：机械臂移动到工作位置
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['arm_joint1', 'arm_joint2', 'arm_joint3', 'arm_joint4', 'arm_joint5'],
  points: [{
    positions: [0.5, 0.3, 0.3, 0.2, 0.0],
    time_from_start: {sec: 2}
  }]
}" --once

# 第 3 步：张开夹爪
ros2 topic pub /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['r_joint'],
  points: [{
    positions: [0.5],
    time_from_start: {sec: 1}
  }]
}" --once

# 第 4 步：闭合夹爪（模拟抓取）
ros2 topic pub /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['r_joint'],
  points: [{
    positions: [0.0],
    time_from_start: {sec: 1}
  }]
}" --once

# 第 5 步：机械臂回到零位
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['arm_joint1', 'arm_joint2', 'arm_joint3', 'arm_joint4', 'arm_joint5'],
  points: [{
    positions: [0.0, 0.0, 0.0, 0.0, 0.0],
    time_from_start: {sec: 2}
  }]
}" --once
```

在 Gazebo 界面中应该能看到机械臂跟随指令运动。

### 3.4 抓取演示 (Pick-and-Place)

在 Gazebo 中完成固定位置的物体抓取与放置，验证机械臂运动学逆解。

#### 启动方式

```bash
cd ~/xflz_robot_car1_ros2_ws
colcon build --packages-select car1_description car1_gazebo
source install/setup.bash

# 默认模式：几何 IK 自动抓取
ros2 launch car1_gazebo grasp_demo.launch.py

# 手动参考模式：使用预设关节角度抓取
ros2 launch car1_gazebo grasp_demo.launch.py mode:=manual

# 仅启动环境（用于手动控制调试）
ros2 launch car1_gazebo grasp_demo.launch.py mode:=none
```

#### 模式说明

| mode 参数 | 说明 |
|-----------|------|
| `ik` (默认) | 使用几何法逆运动学解算，自动计算关节角度完成抓取 |
| `manual` | 使用手动调试得到的参考关节角度，直接执行抓取序列 |
| `none` | 仅启动仿真环境（Gazebo + 机器人 + 方块 + 控制器），不执行抓取 |

#### 场景说明

- 红色方块（40mm）放置在机器人正前方 0.25m 处
- 抓取后放置到右前方 (0.20, 0.10) 位置
- 完整流程：张开夹爪 → pre-grasp → 下降抓取 → 闭合夹爪 → 提升 → 移动到放置点 → 释放 → 回到零位

#### 手动控制模式

当 `mode:=none` 时，可在另一个终端启动手动控制工具：

```bash
source ~/xflz_robot_car1_ros2_ws/install/setup.bash
ros2 run car1_gazebo manual_control.py
```

手动控制命令：

```
a j1 j2 j3 j4 j5   — 设置机械臂 5 个关节角度（弧度）
g value             — 设置夹爪开合（0=闭合, 0.8=张开）
r                   — 读取当前关节状态
h                   — 回到零位
q                   — 退出
```

示例操作：

```
>>> g 0.8                       # 张开夹爪
>>> a 0 -1.05 -1.05 -1.2 0     # 移动到抓取位置
>>> g 0                         # 闭合夹爪
>>> a 0 -0.85 -1.05 -1.2 0     # 提升
>>> h                           # 回到零位
```

### 3.5 常见问题

#### Q: Mesh 文件找不到（GUI 错误）

错误信息：`[GUI] [Err] Unable to find file with URI [model://car1_description/meshes/xxx.STL]`

解决方案：重新编译，launch 文件会自动处理路径转换。
```bash
cd ~/xflz_robot_car1_ros2_ws
rm -rf build/ install/ log/
colcon build --packages-select car1_description car1_gazebo
source install/setup.bash
```

#### Q: 控制器启动失败

```bash
# 检查硬件组件
ros2 control list_hardware_components

# 手动加载控制器
ros2 control load_controller arm_controller
ros2 control set_controller_state arm_controller active
```

#### Q: 夹爪不动

检查 mimic 关节是否正确配置：
```bash
ros2 topic echo /joint_states | grep -E "r_joint|l_joint"
```

#### Q: 机器人模型不显示

```bash
ros2 topic echo /robot_description --once
ros2 run tf2_tools view_frames
```

---

## 机器人模型说明

car1 是一个移动机械臂平台，包含：

- **底盘** — base_link，4个麦克纳姆轮（wheel_lf/rf/lb/rb）
- **机械臂** — 5自由度（arm_joint1~5）+ 固定底座（arm_base_link）
- **夹爪** — 双指夹爪，r_joint 主动控制，l_joint 等为 mimic 关节
- **激光雷达** — laser_link，固定在底盘前方

---

## 注意事项

- **ROS2 版本**：建议使用 Jazzy 或 Humble
- **Gazebo 版本**：Gazebo Harmonic (gz-sim)
- **首次启动慢**：Gazebo 首次启动需要下载模型，可能需要几分钟
- **修改文件后**：必须重新编译并 `source install/setup.bash`

### 故障排查

```bash
# 检查 ROS2 环境
printenv | grep ROS

# 检查包是否正确安装
ros2 pkg list | grep car1

# 查看控制器状态
ros2 control list_controllers

# 查看详细日志
ros2 launch car1_gazebo gazebo_arm.launch.py --log-level debug

# 重新编译
cd ~/xflz_robot_car1_ros2_ws
rm -rf build/ install/ log/
colcon build --packages-select car1_description car1_gazebo
source install/setup.bash
```
