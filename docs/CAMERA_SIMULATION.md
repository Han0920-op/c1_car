# C1 仿真相机与红球检查

## 根因和修复

当前仓库原有的 `grasp_demo_vision.launch.py` 生成的是红色**方块**，世界 `camera_demo.sdf` 只提供地面、灯光和系统插件。原始仓库没有红球 SDF，识别节点输出的 RViz 球形标记也属于 ROS 可视化。若现场的 Gazebo 场景确实有红球，它可能由手工或其他场景放入，现场位姿无法从本仓库确认。

对零位 URDF 和启动位姿做了矩阵计算。原相机的 Gazebo +X 光轴在世界坐标下约为 `(0.155, 0.029, 0.987)`，几乎向上。原默认地面方块相对于相机的前向距离约为 **−0.570 m**，在相机背后。当前向距离为负时，改裁剪距离、HSV 或 ROS 订阅设置无法让目标进入原始画面。

- 仿真传感器仍挂在随机械臂移动的 `camera_depth_link`。仿真专用旋转按零位相机位置和地面目标方向计算，光轴朝车前下方约 66°。真机 URDF 安装位姿保留。视野保持水平 `1.288 rad`（约 74°）、垂直约 59°，分辨率 `640×480`，裁剪范围 `0.2–4.0 m`，传感器配置为 `20 Hz`。
- 相同的安装旋转用于仿真传感器和 ROS TF。`camera_sim_link` 遵循 Gazebo 的 +X 前向，`camera_sim_optical_frame` 遵循 ROS 的 +Z 前向、+X 向右、+Y 向下。RGB、深度、内参使用这个光学帧，现有识别节点也采用同一参考帧。固定模式使用零位关节状态，抓取模式由控制器的 `/joint_states` 提供动态 TF。
- `camera_only:=true` 生成固定零位小车和独立的红色球体。红球世界坐标为 `(0.28, 0, 0.035) m`，半径 `0.035 m`，模型带不透明的红色 ambient/diffuse visual。这个模式不启动控制器和识别节点。原抓取模式仍使用动态红方块。
- 在零位和原启动高度 `0.1 m` 下，离线计算得到红球约在光轴前 **0.660 m**、图像中心附近 `(320, 240)`。方块前向距离约 **0.674 m**。两者均落在视锥和裁剪范围内，红球中心视线在近裁剪面以后未穿过 URDF 可视 STL。真实图像仍需验证。
- 世界保留 Ogre2 Sensors，使用 Fortress 的系统插件名称，Harmonic 源码也接受这些旧名称。启动提供 `fortress:=true`，使用 Fortress 的 `ignition.msgs.*` 类型；原 Harmonic 路径默认使用 `gz.msgs.*`。桥接方向为 Gazebo 到 ROS。

## Ubuntu 22.04 / ROS 2 Humble / Ignition Fortress

在已配置 Ubuntu 与 ROS 2 软件源、已安装 Humble 的终端运行。进入 C1 仓库根目录执行；确认当前使用的源码包含本报告及红球模型。

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions \
  ros-humble-ros-gz ros-humble-xacro ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher ros-humble-rqt-image-view mesa-utils

source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_description car1_gazebo
source install/setup.bash

ros2 launch car1_gazebo grasp_demo_vision.launch.py \
  camera_only:=true fortress:=true
```

预期 Gazebo 打开 `camera_demo` 世界、持续运行仿真，并生成 `car1` 和 `red_ball`。这个相机检查不需要安装或启动抓取控制器。已有 Ubuntu 24.04 / Jazzy / Harmonic 环境可加载该发行版的环境并以 `fortress:=false` 运行等价的相机检查。

### 在 RQT 看原始画面

1. 保持仿真终端运行。另开终端，进入相同仓库根目录，执行：

   ```bash
   source /opt/ros/humble/setup.bash
   source install/setup.bash
   ros2 run rqt_image_view rqt_image_view
   ```

2. 在图像话题下拉框选择 `/camera/image`。列表为空时等模型生成后点击刷新，确认 Gazebo 未暂停。若通过通用 `rqt` 启动，则从 **Plugins → Visualization → Image View** 打开插件。
3. 预期看到连续的彩色地面画面，红球靠近画面中心。可切到 `/camera/depth_image` 检查深度；深度图不会显示红色材质。`/camera/camera_info` 是内参消息。

### 按链路检查话题

在加载同一 ROS 环境的终端运行。Fortress 使用 `ign topic`，Harmonic 改用 `gz topic`。

```bash
ign topic -l | grep -E '(^/camera/|/clock$)'
ign topic -i -t /camera/image
timeout 8s ign topic -e -t /camera/image | grep -m1 'width:'

ros2 topic list -t | grep -E '(^/camera/|^/clock)'
ros2 topic info -v /camera/image
ros2 topic echo /camera/image --once --field header --qos-reliability best_effort
ros2 topic echo /camera/image --once --field encoding --qos-reliability best_effort
ros2 topic hz /camera/image
ros2 run tf2_ros tf2_echo base_link camera_sim_optical_frame
```

| 话题 | Gazebo Fortress 消息 | ROS 2 消息或预期 |
|---|---|---|
| `/camera/image` | `ignition.msgs.Image` | `sensor_msgs/msg/Image`，`rgb8`，有持续时间戳，名义仿真频率 20 Hz |
| `/camera/depth_image` | `ignition.msgs.Image` | `sensor_msgs/msg/Image`，`32FC1` |
| `/camera/camera_info` | `ignition.msgs.CameraInfo` | `sensor_msgs/msg/CameraInfo`，640×480 的尺寸及有效焦距 |
| `/camera/points` | `ignition.msgs.PointCloudPacked` | `sensor_msgs/msg/PointCloud2` |
| `/clock` | `ignition.msgs.Clock` | `rosgraph_msgs/msg/Clock`，持续推进 |

图像头部的预期 `frame_id` 是 `camera_sim_optical_frame`。用 `ros2 topic info -v` 对比桥接发布端与 RQT 订阅端的实际 QoS。Best Effort 订阅兼容 Reliable 和 Best Effort 发布端，Reliable 订阅要求 Reliable 发布端。若 `echo` 收到图像而 RQT 没画面，先核对两个终端的 `ROS_DOMAIN_ID`、话题类型和 QoS。实际墙钟帧率会随实时因子和渲染性能下降。

## 用观察结果区分问题

| 观察结果 | 优先检查 |
|---|---|
| Gazebo Transport 无图像话题，或话题存在却无帧 | 模型生成、是否暂停、`camera_demo` 的 Sensors/SceneBroadcaster 插件是否加载，以及 Ogre2 日志。先让 Gazebo 端有帧。 |
| Gazebo 有帧，ROS 的 `echo` 没有帧 | 核对 `fortress` 参数、桥接终端的创建或转换错误、话题类型和 ROS 域。 |
| ROS 有帧，RQT 不显示 | 选择原始 `/camera/image`，检查订阅 QoS 与图像编码。 |
| RQT 有稳定彩色画面但没球 | 确认场景生成的是 `red_ball`，复查目标位姿与当前机械臂姿态。使用 Gazebo 主视口确认红球 visual 存在，再以相机视角排除视锥外、遮挡或裁剪。 |
| Gazebo 主视口能看见红球，传感器画面全黑或报渲染错误 | 检查传感器端 Ogre2、OpenGL 和虚拟 GPU。主视口可渲染仍可能伴随传感器渲染失败。 |
| 原始彩色图能看到球，识别或定位无输出 | 相机检查模式只出原始数据。需要排查现有识别时，在原抓取模式核对检测订阅、有效深度、内参和 `base_link → camera_sim_optical_frame` 变换。TF 或 HSV 出错不会改变 RQT 原始图。 |

## VMware 渲染排查

在虚拟机桌面终端运行 `glxinfo -B`，检查 renderer 和 OpenGL Core Profile。结合 Gazebo 日志中的 Ogre2/OpenGL 初始化错误判断。若 VMware 3D 加速的渲染失败，从终端用 Mesa 软件渲染做一次对照：

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch car1_gazebo grasp_demo_vision.launch.py \
  camera_only:=true fortress:=true server_only:=true
```

`server_only` 关闭 Gazebo GUI，仍要由 Ogre2 绘制传感器画面；从带显示会话的终端执行，另开 RQT 观察。若软件渲染能出图，记录 VMware 的 3D 设置、客户机 Mesa 版本及日志。软件渲染帧率可能较低。VMware 实机对照尚未执行。

## 验证范围

已运行零位变换、球与立方体视锥检查、红球中心射线和 STL 相交检查，Python/XML 解析和 `git diff --check` 通过。Ubuntu 22.04 / Humble 容器内构建了 `car1_description` 和 `car1_gazebo`，展开并核对两种 xacro 模式，确认红球 SDF 已安装、固定模式无控制插件，并检查了 launch 参数。容器没有可运行的 Ignition 与 ROS 图像桥接环境，实际出帧、RQT 和 VMware 渲染尚未验证。本阶段没有启动真机或开发新的识别算法。
