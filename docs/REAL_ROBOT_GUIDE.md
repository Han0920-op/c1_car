# 从 Gazebo 切换到 C1 和 HP60C

在 C1 上单独启动 HP60C 和一个视觉实验即可验收二维识别。下面的视觉步骤不启动底盘、舵机、抓取或导航。真机采集、相机外参和机械运动均待现场验收。

| 设置 | Gazebo Fortress | C1 真机 |
|---|---|---|
| 图像发布端 | 固定相机场景及 ros_gz_bridge | `ros2 launch ascamera hp60c.launch.py` |
| 实验启动参数 | `camera_source:=gazebo use_sim_time:=true` | `camera_source:=hp60c use_sim_time:=false` |
| 默认订阅话题 | `/camera/image` | `/ascamera_hp60c/camera_publisher/rgb0/image` |
| 时间与坐标系 | `/clock`、`camera_sim_optical_frame` | 系统时间，使用 RGB 消息实际的 `header.frame_id` |
| 本地图片 | 测试时传 `image_path` | 采集时使用默认空值，检查自定义 YAML 里也为空 |

## 一、准备相机

以下命令从仓库根目录执行。先在 Ubuntu 22.04 安装好 ROS 2 Humble 并配置 apt 源。驱动随仓库附带分架构的 SDK 动态库，构建时按本机编译器目标选择。虚拟机连接实体相机时，先将 USB 设备连接到客户机，在客户机运行 `lsusb` 核对设备。

```bash
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install build-essential python3-colcon-common-extensions ros-humble-pcl-conversions \
  libpcl-dev ros-humble-cv-bridge ros-humble-rqt-image-view python3-opencv \
  python3-numpy python3-yaml python3-pyzbar
colcon build --symlink-install --packages-select ascamera car1_app
source install/setup.bash
gcc -dumpmachine
ldd "$(ros2 pkg prefix ascamera)/lib/ascamera/ascamera_node" | grep 'not found'
```

最后一行没有输出表示未发现缺失的运行库。如果普通用户不能访问已枚举的 USB 设备，可按厂商脚本安装 udev 规则后重新插拔相机。

```bash
sudo bash src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/scripts/create_udev_rules.sh
```

## 二、只开相机，确认首帧

终端一运行课程使用的相机驱动。这个 launch 请求 640×480、25 FPS，实际频率以测量为准。只启动一个驱动实例。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ascamera hp60c.launch.py
```

终端二加载相同工作区后执行。驱动根据发布话题名中的 `rgb0` 等标记选择数据流。需要适配命名空间时，把实际话题传给实验的 `camera_topic`，保留驱动发布端的原名。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
rgb=/ascamera_hp60c/camera_publisher/rgb0/image
ros2 topic list -t
ros2 topic info -v "$rgb"
ros2 topic echo "$rgb" --once --field encoding --qos-reliability best_effort
ros2 topic echo "$rgb" --once --field header --qos-reliability best_effort
ros2 topic hz "$rgb"  # 打印帧率后按 Ctrl+C
```

预期类型为 `sensor_msgs/msg/Image`，驱动源码给 RGB 消息填写 `bgr8` 和 `step = width × 3`。若在另一台电脑运行 RQT，请确认两端在同一 ROS_DOMAIN_ID 且 DDS 可互相发现。

## 三、逐个验收视觉实验

终端二选择下面任意一条命令，测试结束按 Ctrl+C，再换下一个。结果话题名称与仿真相同。

```bash
ros2 launch car1_app exp01_color_detection.launch.py camera_source:=hp60c use_sim_time:=false
ros2 launch car1_app exp02_polygon_detection.launch.py camera_source:=hp60c use_sim_time:=false
ros2 launch car1_app exp03_qrcode_detection.launch.py camera_source:=hp60c use_sim_time:=false
```

另开已加载工作区的终端运行 `ros2 run rqt_image_view rqt_image_view`。依次展示彩色物体、多边形卡片和已知内容的二维码，切换原始 RGB 与相应节点的 `result`。检查识别名称、图形顶点数或二维码原文，并核对 `detections` 中的源帧。可用 `ros2 node info /exp01_color_detection` 核对其发布列表。光照变化时再调整实验 YAML 中的 HSV、分割阈值或检测比例，切换相机本身不要求修改算法。EXP3 的课程 MJPEG 入口和本地生成命令见 [EXP3 操作说明](EXP03_QRCODE_DETECTION.md)。

## 四、底盘、TF、里程计和导航的独立检查

以下为原有硬件栈的接口检查。只在底盘栈已经由操作员启动时运行下面的只读命令。仅做视觉实验时可以跳过本节。

```bash
ros2 topic info -v /controller/cmd_vel
ros2 topic info -v /car1_base_driver/set_motor
ros2 topic hz /odom_raw
ros2 topic hz /odometry/filtered
ros2 topic hz /scan
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_ros tf2_echo base_footprint laser_link
ros2 run tf2_ros tf2_echo map odom
ros2 lifecycle get /amcl
ros2 action list -t
```

频率和 TF 命令持续输出，逐条执行并用 Ctrl+C 返回。

- **底盘。** `car1_bringup/bringup.launch.py` 加载串口驱动、URDF、底盘和舵机控制器，`enable_init_pose` 默认关闭。底盘默认串口为 `/dev/ttyUSB0`，雷达默认 `/dev/ttyUSB1`，插拔后需按设备身份核对。原有控制节点可响应速度命令，上述视觉入口独立于它们。
- **里程计。** `odom_publisher_node.py` 接收 `/cmd_vel` 和 `/controller/cmd_vel`，向 `/car1_base_driver/set_motor` 发电机命令，并发布 `/odom_raw`。原始位姿按命令速度积分，平移积分使用纵向速度，横移只写入 twist。不能据此证明实际轮速、侧移距离或标定准确。EKF 配置融合 `/odom_raw` 与 `/imu`，输出 `/odometry/filtered` 和 `odom → base_footprint`。
- **TF。** URDF 负责机身到传感器安装座的关系，HP60C 课程启动入口启用厂商 TF。先从 RGB 消息读取实际帧名，再执行 `ros2 run tf2_ros tf2_echo base_footprint 实际帧名`。若树未接通，需按实际安装方向标定机身与相机的外参；二维结果可独立验收。
- **导航。** `car1_navigation/navigation.launch.py` 会包含真机 bringup、雷达、地图、AMCL 和 Nav2。默认地图由 `car1_slam/maps/slam_map.yaml` 及同目录 PGM 提供，可通过 `map_dir` 和无扩展名的 `map` 切换。AMCL 使用 `/scan` 及初始定位提供 `map → odom`。控制器输出经 `/cmd_vel_nav` 和速度平滑器到 `/controller/cmd_vel`。应分别核对生命周期、TF、扫描和定位后，再单独安排行驶验收。

软件侧测试结果见[仿真与集成记录](SIMULATION_GUIDE.md)。真机仍需记录 USB 枚举和权限、实际帧率与编码、三项实物识别、实测外参及底盘/Nav2 结果。
