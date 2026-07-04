# xflz_eai_car1 项目功能清单与目录结构

---

## 项目目录结构

```
xflz_eai_car1/
├── TODO.md                              # 本文件：功能清单与验证指南
├── tutorial.md                          # 教程文档
├── driver/                              # 硬件驱动层（Phase 1）
│   ├── car1_base_driver/                # STM32 板级驱动（串口通信）
│   ├── car1_base_driver_msgs/           # 板级驱动消息/服务定义
│   ├── car1_servo_controller/           # 总线舵机控制器（关节状态 + 轨迹动作）
│   ├── car1_servo_controller_msgs/      # 舵机控制器消息定义
│   ├── controller/                      # 底盘控制（麦轮运动学 + 里程计 + EKF）
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
| 底盘 | 4 轮麦克纳姆（轮距 0.2117m，轴距 0.1946m，轮径 0.097m，固件已校准） |
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
              controller (chassis)
                    │
                    ▼
              car1_bringup
```

### 编译命令

```bash
cd ~/ros2_ws
colcon build --packages-select \
  car1_base_driver_msgs \
  car1_servo_controller_msgs \
  car1_sdk \
  car1_base_driver \
  car1_servo_controller \
  controller \
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
ros2 launch controller chassis_controller.launch.py
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
cd ~/ros2_ws
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
cd ~/ros2_ws
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

### ✅ 状态：航向问题已彻底解决（2026-06）

历史问题：建图航向漂移（曾达 162°），墙体双线/地图旋转。
**根因链（三个 bug 叠加，已全部修复）**：

| # | 问题 | 修复 | 状态 |
|---|------|------|------|
| 1 | IMU gyro scale 2× 过报告 | 固件 bmi088.c 加 30ms 复位延时 + 0x0F 回读校验 | ✅ |
| 2 | IMU 协方差全 0，EKF 丢弃数据 | base_driver 填非零协方差（角速度 0.0025） | ✅ |
| 3 | imu0_relative=true 导致 vyaw 被减初值 | ekf.yaml 改 false | ✅ |
| 4 | **缺 base_link→imu_link TF**（主因） | bringup 加 robot_state_publisher | ✅ |
| 5 | EKF 轮速 vyaw 与 IMU vyaw 冲突 | ekf.yaml 关 odom0 的 vyaw，航向只用 IMU | ✅ |

**校准成果**：
- IMU scale：1.01× 精度（转 360° 误差 ~1%）
- 线速度标定：linear_correction_factor=1.04，0% 残差
- 角速度：真实≈360°，系数≈1.0
- **航向闭环误差：0.25°/圈**（之前 162°）
- EKF 角速度：转动时 ≈0.5（之前恒 0）

### 编译命令

```bash
cd ~/ros2_ws
colcon build --packages-select car1_slam
```

### 启动命令

```bash
# 启动 SLAM（包含 bringup + 雷达 + slam_toolbox）
# 注意：bringup 现已含 robot_state_publisher（URDF TF），SLAM 不再单独启动
ros2 launch car1_slam slam.launch.py

# 保存地图（SLAM 运行时另开终端）
ros2 run nav2_map_server map_saver_cli \
  -f ~/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps/slam_map \
  --ros-args -p map_subscribe_transient_local:=true
```

### 验证要点

- [x] slam_toolbox 节点正常启动
- [x] EKF 融合 IMU 正常（转动时 /odometry/filtered 角速度≈指令值）
- [x] 航向闭环误差 <5°（实测 0.25°/圈）
- [x] 地图实时构建（RViz 中可见）
- [x] 地图保存成功（生成 .pgm 和 .yaml 文件）
- [ ] 墙体单线无重影（操作层面，需规整走位 + 走闭环）
- [ ] 地图覆盖完整（减少未知区域，多角度扫描）

### 建图操作建议（提升地图质量）

1. **起步前静止 10 秒**：让 EKF/IMU filter 充分收敛再动
2. **速度**：直线 0.2~0.3 m/s，转弯 ≤0.5 rad/s，拐角降速
3. **走闭环**：回到起点触发回环优化，地图更整齐
4. **覆盖全**：每区域多走、多角度，减少未知区域

---

## 自主导航（Phase 4）

### 功能说明

基于 Nav2 的自主导航系统。**与 lander_pi 参考栈对比讨论后的当前选型**：

- **AMCL**：DifferentialMotionModel（按差速车配置，麦轮横向不参与定位粒子建模）
- **全局规划**：ThetaStar（line-of-sight 优化，8-connectivity）
- **局部控制**：RotationShimController 外壳 → MPPI（DiffDrive 运动模型，vy=0）
  - shim 用于路径起点角度差 >0.5 rad 时先原地转齐，避免画弧线起步
  - MPPI vx_max=0.4 m/s、wz_max=3.0 rad/s
  - critic 去掉 PreferForward（麦轮可后退无代价）
- **Recovery**：与 lander_pi mecanum 对齐——`[spin, drive_on_heading, assisted_teleop, wait]`（无 backup）
- **BT**：
  - 单点 `navigate_to_pose_without_backup.xml`：双层 RecoveryNode（ComputePath/FollowPath 各带 ClearCostmap 内层重试）
  - 多点 `navigate_through_poses_without_backup.xml`：连续多点路径（用于"不停顿穿越"）
- **多点导航/巡逻/按点任务**：走应用层 Python 循环 `BasicNavigator.goToPose()`，**不**用 `follow_waypoints`，不加 `waypoint_follower` / `smoother_server`
- **cmd_vel 路由**：
  - Nav2 → `/cmd_vel_nav` → velocity_smoother → `/controller/cmd_vel`（无 clamp）→ odom_publisher
  - 外部 teleop/app → `/cmd_vel`（odom_publisher 内 ±0.2 m/s clamp）
  - 两通道**必须**通过 launch remap 分离，否则 Nav2 输出会被 clamp 截速 + 与 smoother 竞态
- **Costmap**：`inflation_radius=0.18` + `cost_scaling_factor=4.0`，针对最窄 0.5 m 通道 + 车宽 0.27 m 调参（通道居中 cost=0），**不要按"外接圆经验"抬高**
- **Lidar 范围（D8）**：AMCL 用 0.10–8.0 m；驱动 `m1ct_d2` 限 0.05–12 m（与厂家有效范围对齐）
- **地图加载（D12）**：`get_package_share_directory('car1_slam') + /maps/`，配 `--symlink-install` 后新建图无需 rebuild 即时生效

### 关键配置文件

| 文件 | 作用 |
|---|---|
| `car1_navigation/config/nav2_params.yaml` | 全栈 Nav2 参数 |
| `car1_navigation/config/behavior_trees/navigate_to_pose_without_backup.xml` | 单点导航 BT |
| `car1_navigation/config/behavior_trees/navigate_through_poses_without_backup.xml` | 多点穿越 BT |
| `car1_navigation/launch/include/navigation_base.launch.py` | cmd_vel remap 入口 |
| `car1_navigation/launch/navigation.launch.py` | 主 launch（含 map 路径解析） |
| `car1_peripherals/launch/lidar.launch.py` | COIN-D6 lidar 驱动范围 |
| `driver/controller/config/ekf.yaml` | EKF 输入通道（仅 odom_raw vx/vy + IMU vyaw） |
| `driver/controller/controller/odom_publisher_node.py` | cmd_vel 双通道路由（`cmd_vel` clamp / `controller/cmd_vel` 无 clamp）|

### 编译命令

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-select car1_navigation car1_slam car1_peripherals
```

### 启动命令

```bash
# 启动导航（默认地图 slam_map，对应 src/.../slam/car1_slam/maps/slam_map.yaml）
ros2 launch car1_navigation navigation.launch.py
# 或指定其他地图
ros2 launch car1_navigation navigation.launch.py map:=map_01

# 启动 RViz 导航可视化
ros2 launch car1_navigation rviz_navigation.launch.py
```

### 验证要点

- [ ] 地图加载成功（路径来自 `install/car1_slam/share/car1_slam/maps/` 软链到源码 maps）
- [ ] AMCL 定位正常（机器人位姿与地图对齐）
- [ ] RViz 单点 goal 能规划路径且到达
- [ ] **D3 RotationShim 预对齐**：路径起点方向差 >28° 时机器人先原地转再前进（不应画弧绕进）
- [ ] **D3 速度上限**：直线段最高速达 ~0.4 m/s（D11 修 cmd_vel 路由前会被 clamp 到 0.2）
- [ ] **D11 cmd_vel 隔离**：teleop 发 `/cmd_vel` 时车体受 ±0.2 m/s 限速；Nav2 自动控制时不受限
- [ ] **D8 AMCL 收敛**：在 8 m 房间内 5 s 内收敛粒子云
- [ ] 多点导航：Python 串行 `goToPose` 循环工作（不是 `followWaypoints`）

### ⚠️ 当前已知问题（2026-07-04）

#### 问题 1：navigation.launch.py 需要手动加载地图

**现象**：
- `navigation.launch.py` 启动后 AMCL 显示 "Waiting for map"
- 需要手动执行 `ros2 service call /map_server/load_map` 才能加载地图
- RViz 不会自动启动（即使修改了 launch 文件）

**根本原因**：
- `navigation.launch.py` 的地图路径传递机制有问题
- 从 `navigation.launch.py` → `localization.launch.py` → `map_server` 的参数传递链中断
- `OpaqueFunction` 用于延迟求值 `LaunchConfiguration`，但实际传递时仍有问题

**临时解决方案**：
1. 启动导航：`ros2 launch car1_navigation navigation.launch.py map:=slam_map`
2. 手动加载地图：
   ```bash
   ros2 service call /map_server/load_map nav2_msgs/srv/LoadMap "{map_url: '/home/iflytek/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps/slam_map.yaml'}"
   ```
3. 手动启动 RViz：
   ```bash
   ros2 run rviz2 rviz2 -d ~/ros2_ws/src/xflz_eai_car1/navigation/car1_navigation/rviz/navigation.rviz
   ```

**需要修复的文件**：
- `car1_navigation/launch/navigation.launch.py`（地图路径传递）
- `car1_navigation/launch/include/localization.launch.py`（map_server 参数接收）

**已修复的配置问题**（2026-07-04）：
- ✅ 插件命名格式：`nav2_behaviors::Spin` → `nav2_behaviors/Spin`
- ✅ 控制器切换：MPPI → DWB（更稳定，避免崩溃）
- ✅ BT 插件列表：移除 Humble 中不存在的插件
- ✅ 行为树 XML：移除 `is_recovery` 参数（Humble 不支持）
- ✅ BT 文件路径：`$(find-pkg-share ...)` → 绝对路径
- ✅ lifecycle_manager bond_timeout：4s → 10s

#### 问题 2：极小地图导致的潜在问题

**现象**：
- 当前测试地图 `slam_map.pgm` 只有 29×38 像素（1.45m × 1.9m）
- 这么小的地图可能导致 costmap、planner 等组件行为异常

**建议**：
- 重新建一个更大的地图（至少 4×4 米，建议 80×80 像素以上）
- 建图时覆盖更大范围，多角度扫描

### 已写入 auto-memory 的关键决策（防止以后绕回）

- `mecanum_lateral_disabled_in_nav.md` — Nav2 全栈按差速车配置；底盘 vy 通路完好，app/teleop 可直发 `/controller/cmd_vel.linear.y`
- `nav_multipoint_via_app_loop.md` — 多点统一走应用层 Python 循环
- `nav_costmap_tuned_for_narrow_corridor.md` — 0.18/4.0 是为 0.5 m 通道刻意调的
- `cmd_vel_routing_car1.md` — Nav2/teleop 双通道路由 + clamp 隔离规则

### 工程卫生收尾（F1-F6，已完成）

| # | 改动 | 文件 |
|---|---|---|
| F1 | 补 `navigation.rviz`（基于 lander_pi 拷改：`/scan_raw→/scan`、`lidar_frame→laser_link`） | `car1_navigation/rviz/navigation.rviz` |
| F2 | `xy_goal_tolerance 0.05→0.10`、`required_movement_radius 0.5→0.1`（解除接近 goal 时 progress 误判失败的冲突） | `nav2_params.yaml:128,133` |
| F3 | `amcl.transform_tolerance 1.0→0.3`（EKF TF 卡死时不会用 1s 旧 TF 推错粒子云） | `nav2_params.yaml:37` |
| F4 | 加 `test/test_copyright.py`、`test_flake8.py`、`test_pep257.py` + `package.xml` 加 `test_depend` | `car1_navigation/test/`、`package.xml`、`setup.py` |
| F5 | 删 `map_saver` 下无效的 `map_subscribe_transient_local: true`（该参数只对 static_layer 有效） | `nav2_params.yaml:354-359` |
| F6 | CLAUDE.md（根 + 子）补 `cmd_vel` 双通道注释，说明 Nav2 path 和 ±0.2 clamp 关系 | `CLAUDE.md:173-178`、`src/xflz_eai_car1/CLAUDE.md:103-107` |

### 未决事项

#### D9 — Lidar 滤波链（等实测）

**待验证**：lidar 装在车前端中线（laser_joint 偏移 x=0.146 m），向车尾扫描时可能扫到自身车体（外壳/支架/相机/手臂底座）。

**实测步骤**：
1. `ros2 launch car1_navigation navigation.launch.py`
2. RViz 加 `LocalCostmap` 显示
3. 机器人静止于空旷处，观察 footprint 周围一圈是否有持续标记的红色 cell

**判定 + 处置**：
- footprint 外圈干净 → 无需处理（保持现状）
- footprint 周围有持续残影 → 启用 `lidar.launch.py` 的 `ignore_array` 参数屏蔽对应车后扇区（不引入 `laser_filters` 节点以避免多一层 IPC 延迟）

#### D2 — 静止 yaw 漂移（等诊断）

**现象**：car1 静止运行一段时间后 yaw 漂移可见。

**初步定位**：EKF 仅靠 IMU 提供 vyaw（odom vyaw 实际是 cmd_vel 命令回声，已正确禁用），BMI088 静止零偏 ±0.04 rad/s 是物理事实。

**诊断步骤**：
1. `ros2 run tf2_ros tf2_echo odom base_footprint` — 静止 5 分钟看 yaw 变化率
2. `ros2 run tf2_ros tf2_echo map base_footprint` — 同上

**判定 + 处置**：
- 仅 `odom→base_footprint` 漂、`map→base_footprint` 稳 → AMCL 在兜底，**不用处理**，仅是 odom 帧外观
- 两者都漂 → AMCL 也失锁，回头查 AMCL 参数或粒子收敛
- 介意 odom 帧静止漂移 → 在 odom_publisher 或单独节点加在线零偏估计（静止 ≥2 s 平均 gyro_z 作 offset 扣减）

#### D3 — MPPI CPU 占用（等实测）

**待验证**：batch_size=2000 × time_steps=56 在 RK3576 上是否能稳到 controller_frequency=20 Hz。

**实测**：跑导航 + `htop` 看 `controller_server` CPU；`ros2 topic hz /local_costmap/costmap_updates`。

**回退**：若 controller_server 持续 >90% 单核 → 把 batch_size 砍到 1000，再不行 1500/40 组合。

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
cd ~/ros2_ws
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

## Gazebo 仿真抓取验证（参考路线，未实施）

> 仿真路线已被实机 Level 1-5 取代（见下方"实机机械臂抓取实施计划"）。这里仅保留 5 阶段总览供后续做仿真时参考。

| 阶段 | 内容 | 关键技术 |
|---|---|---|
| 1 | 固定位置抓取 | FK/IK + JointTrajectoryController |
| 2 | 视觉感知 + 坐标变换 | RGB-D HSV 检测 + TF（camera→base_link） |
| 3 | 运动规划 + 避障 | MoveIt2 + RRT* + PlanningScene |
| 4 | 视觉伺服闭环 | IBVS/PBVS + 抓取检测 |
| 5 | 多物体分类抓取 | 实例分割 + 状态机 |

代码位置：`simulations/car1_gazebo/`，启动文件 `grasp_demo.launch.py` / `grasp_demo_vision.launch.py`。详细分层验证步骤见 git 历史（`f48f26b^` 之前的 TODO.md）。

---

## 注意事项

1. **编译模式**：使用 `--symlink-install` 可实现源码修改即时生效
2. **硬件依赖**：部分功能（雷达、摄像头、机械臂）需要实际硬件
3. **安全限位**：机械臂关节角度建议设置为最大值的90%~95%
4. **坐标系**：确保 TF 树结构正确，避免定位失败

---

## 历史记录：SLAM/里程计优化（2026-06，已完成）

以下优化项已全部完成，详见 Phase 3 头部 "✅ 航向问题已彻底解决" 小节及内存文件：

- **P0-1 里程计标定** ✅ linear=0.961, angular=0.964（直线 0.5%、角度 1.1% 残差）
- **底盘速度单位错配修复** ✅ ROS 端直发 m/s + 固件轮径 0.08→0.097（残留 6% 由系数补）
- **IMU 航向链** ✅ 固件 scale + 协方差 + EKF imu0_relative + base_link→imu_link TF + EKF 关 odom0 vyaw（闭环 0.25°/圈）
- **slam_toolbox 配置** ✅ 启动延迟 10s + 单 robot_state_publisher 入口
- **校准文件归属约定** ✅ `calibrate_params.yaml` 留 `controller/config/`，`servo_offsets.yaml` 留 `calibration/config/`，未来 IMU `imu_calib.yaml` 跟 servo_offsets 同位

### 仍可选的未来增强（按需做）

| 项 | 时间 | 触发条件 |
|---|---|---|
| **编码器闭环 odom** | 半天（需 Windows 烧固件） | 长时间运动有明显累积漂移 / 麦轮打滑频繁 |
| **IMU Madgwick `do_bias_estimation=True`** | 5 分钟 | 静止 yaw 仍漂 |
| **EKF 静止协方差动态调整** | 10 分钟 | 静止时位姿不稳 |
| **IMU SM 矩阵校准** | 数小时（需转台） | 长时 SLAM 精度要求极高 |
| **地图保存 ROS 服务节点** | 20 分钟 | 想用 GUI/脚本触发存图（替代手动 CLI） |
| **`laser_filters` 集成** | 1-2 小时 | 建图后机身附近出现跟着转的固定假障碍 |

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

### Level 1：运动学基础 ✅ 已完成

**已完成组件**：
- **Transform 模块** (`arm/kinematics/kinematics/transform.py`): PWM↔角度转换；270° 舵机，center=1500，PWM_TO_RAD=0.002356，direction=+1，offset=0；`TCP_OFFSET_Z=0.0762m`
- **IK 求解器** (`ik_analytical.py`): 解析解（固定/自动/忽略俯仰），`solution_to_pwm()` 直出 PWM
- **Safe Arm Controller** (`arm/car1_arm_controller/.../arm_controller.py`): `move_to_pose` / `set_gripper` / `go_home` / `emergency_stop` / `pick` / `place`，含分步移动 + 限位检查 + 可中断等待
- **交互式测试** (`interactive_ik_test.py`): ROS2 模式 + `--direct` 直连串口模式，FK 误差 0.00mm，PWM 闭环验证通过

**验证状态**：Transform 准确、IK→PWM 闭环已通、分步移动安全、紧急停止有效、限位检查、IK 无解处理、完整抓取序列 — 全部 ✅。仅"同位置重复 5 次方差<1cm"待实机复测。

---

### Level 2：动作组控制 ✅ 已完成

YAML 预录制动作回放，已实现 `action_group_controller.py`（解析 + 单步/暂停/紧急停止）、`test_servo_direct.py` 手动调试工具，并产出预录制安全动作集（home / work_ready / pick_front / place_left / place_right）。回放话题 `/car1_base_driver/bus_servo/set_position`。

---

### Level 3：IK 分步抓取 ✅ 主要完成

**关键设计**：
- 末端控制目标 = **tcp_link**（arm_link5 下方 76.2mm，实测 76.25mm）
- 抓取策略：tcp_link → 物体顶部中心；指尖（tcp_link 下方 33mm）自然落在物体中部
- 无需预抓取偏移；33mm 夹爪长度自适应 30-50mm 物体高
- 坐标系：base_link 右手系，+X 前 / +Y 左 / +Z 上

**已实现**：transform 层、`ik_analytical` 求解、分步移动（底座先转后臂动）、emergency stop、限位检查、`interactive_ik_test` 闭环验证。FK 误差 0.00mm，PWM 回读与目标基本一致。

**Level 3 → Level 4 接口**：
```python
# Level 4 提供物体顶部中心坐标
detected_object = {'grasp_point': [x, y, z], 'confidence': 0.95}
# Level 3 直接移动 tcp_link 到该点
arm.move_to_pose(x, y, z, pitch=-π/2)
arm.set_gripper(close=True)
arm.move_to_pose(x, y, z+0.05)  # 提升 5cm
arm.go_home()
```

> **实测残留偏差（2026-06-12，暂不矫正）**：ID1(大臂) +22~24 PWM (≈+4°)、ID2(小臂) +13~14 PWM (≈+2.3°) 系统性偏移，ID0/3/4 准确。末端位置误差约 5~8mm，原因：装配/中位校准/负载稳态。若需补偿，在 `transform.py` 加 per-servo offset 或用 `#00xPSCK!` 硬件校中位。

**未验收项（需实机尺子复测）**：Transform 物理精度、IK 物理到达精度、可重复性。

---

### Level 4：视觉 + IK 抓取 ⏳ 卡在深度盲区

**目标**：深度相机识别物体 → IK 抓取。

**已通环节** ✅：
- 机械臂 IK 控制（pitch=180° 夹爪垂直向下，FK 误差 0.00mm）
- joint_states 实际回读（6 舵机 20Hz）
- 相机出图（RGB ~11Hz、Depth ~12Hz，内参 fx=594.5/fy=594.8/cx=350.3/cy=237.5）
- TF 链 `base_link → camera_depth_optical_frame` 完整且随姿态更新
- HSV 红色检测稳定（~5000 像素）

**当前卡点 — HP60C 近距盲区**（非代码问题）：
- 红块 HSV 检测成功，但该像素深度全 0（空洞）
- HP60C 近距质量极差：左上远处（0.6~1.1m）有深度，右下近处大片空洞；200-400mm 段有效像素仅 1%
- eye-in-hand 俯视抓取距离正好落在 0.2~0.5m 空洞区
- 标称最小 0.2m，实际 0.5m 内基本不可用

**待定方案（需拍板）**：
1. **已知平面射线投影（推荐）**：物体与底座同高 → RGB 像素 + 内参 + TF 反算射线与已知 z 平面交点，**完全不用深度**，绕开盲区
2. 换观察姿态把物体推到远距有效区（受工作空间限制）
3. 物体垫高（治标不治本）

**启动命令**：
```bash
ros2 launch car1_bringup bringup.launch.py            # 终端 1
ros2 launch car1_arm_controller arm_controller.launch.py  # 终端 2
ros2 launch car1_peripherals depth_camera.launch.py   # 终端 3（原生话题无 remap）
ros2 launch car1_app rsp_only.launch.py               # 终端 4（TF 树）
ros2 run car1_app visual_grasp                        # 终端 5
```

**Level 4 调试中已修复的底层 bug 链**（按发现顺序）：
- 统一 240°→270° 转换（`joint_position_controller.py` 改 `RADIANS_PER_ENCODER_TICK=0.002356`）
- joint_states 改实际回读（原发布指令值，污染 eye-in-hand TF）
- 跨线程 spin 崩溃 → 改主线程 timer + round-robin call_async + done_callback
- `board_sdk._bus_servo_read` 响应字节布局误解（`result[0]/[1]` 语义反，修正后 6 舵机全能读）
- 读取路径误钳位（pos_pulse_to_rad 读方向去钳位）
- arm_controller IK 缺解（自带简化 IK 单解 + 无 PHI 补偿，改复用 `ik_analytical.py`）
- pitch 约定统一（**0=朝上, 90=水平, 180=夹爪朝下，抓取用 180**）
- 软件限位过紧（J4 max=2200 钳掉 IK 解 PWM2295，所有 arm 关节放宽到 500-2500 硬件极限）
- 相机 launch remap 改坏推流（ascamera 靠 `rgb0/depth0` 子串判流，**不能 remap 改话题名**）
- RGB 第一帧黑帧（visual_grasp 加亮度检查跳过）
- 深度采样改整轮廓中值（避免中心 5×5 落在空洞）

**关键经验**：
1. 相机话题用驱动原生 `/ascamera_hp60c/camera_publisher/...`，不要 remap
2. ascamera 按需推流：无订阅自动 stop（日志正常），订阅后 1~1.5s 自动恢复
3. ros2_venv 缺 Qt：软链接系统 `/usr/lib/python3/dist-packages/PyQt5`（勿 pip 编译，会 OOM）
4. PoseStamped YAML 冒号后必须有空格：`{x: 0.25}` 不是 `{x:0.25}`
5. 相机已通过 URDF `camera_mount_joint` + robot_state_publisher 提供 TF，**无需额外手眼标定**

**验收目标**（解决深度后核对）：物体检测准确率 >90%、3D 定位误差 <1.5cm、抓取成功率 >70%。

---

### Level 5：导航 + 视觉 + 抓取（全自主任务）⏳ 待 Level 4 + Phase 4 完成

机器人自主导航 → 视觉识别 → 抓取 → 导航放置 → 循环。

**前置**：Level 4 通过 + Phase 4 Nav2 工作正常 + 已有地图。

**核心要点**：
- 任务状态机：`IDLE → NAV_TO_PICK → DETECT → PICK → NAV_TO_PLACE → PLACE → 循环`
- 导航时机械臂收回安全姿态避免碰撞
- 任务配置 YAML：`pick_point` / `place_point` / `target_color` / `max_attempts`
- 异常处理：导航失败重试、检测不到物体调整位置、抓取失败重试 N 次、物体掉落重检

**验收**：导航到抓取点 <5cm、自动状态切换、循环执行、异常处理有效、整体成功率 >60%。

---

### 虚实同步（辅助工具，贯穿所有 Level）⏳ 可选

RViz 中实时显示实物机械臂姿态。读取舵机 PWM → `pulse2angle` → 发 `/joint_states` → URDF 模型跟随。注意 Level 4 已实现了 joint_states 实际回读（20Hz），这块基本已可用，剩下的是按需做 RViz 端的 InteractiveMarker 反向控制。

---

## 历史记录：SLAM 漂移误诊（2026-06-24，已过时）

曾把"双线/29°漂移/点云失配"误诊为 IMU 陀螺仪固件 scale bug（缩小~29倍），结论"必须 Windows 烧固件"。
后续实测确认陀螺仪本身工作正常（静止零漂 ±0.04，旋转 -3.38 rad/s），29 倍是测试时车没真转造成的假象。
**真实根因**：EKF 配置错误 + 缺 `base_link→imu_link` TF + IMU 协方差全 0 被 EKF 丢弃，
已在 commit `f48f26b` 修复（详见 Phase 3 头部"航向问题已彻底解决"小节）。
**固件不要再改**。
