# 三个视觉实验的仿真操作指南

在 Ubuntu 22.04、ROS 2 Humble 和 Ignition Fortress 中，每次启动一个固定相机场景和一个实验节点。每个新终端从仓库根目录开始。实验只发布图像、掩膜和识别结果。

## 安装与构建

以下命令假定已经配置 Humble 软件源。使用系统 Python 3 和 apt 版 OpenCV、NumPy、cv_bridge，保持三者的二进制接口一致。

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions ros-humble-ros-gz ros-humble-xacro \
  ros-humble-joint-state-publisher ros-humble-robot-state-publisher ros-humble-cv-bridge \
  ros-humble-rqt-image-view python3-opencv python3-numpy python3-yaml python3-pyzbar
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_description car1_gazebo car1_app
source install/setup.bash
```

## 选择实验

| 实验 | 终端一的 `target` | 终端二的 `experiment` | 静态样例 |
|---|---|---|---|
| EXP1 HSV | exp01_color_targets | exp01_color_detection | exp01_colors.png |
| EXP2 多边形 | exp02_polygon_targets | exp02_polygon_detection | exp02_polygons.png |
| EXP3 二维码 | exp03_qrcode_target | exp03_qrcode_detection | exp03_qrcode.png |

终端一启动场景。示例选择 EXP1，测试其他实验时替换表中同一行的两个值。切换世界前先用 Ctrl+C 关闭上一套 launch。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
target=exp01_color_targets
ros2 launch car1_gazebo grasp_demo_vision.launch.py \
  camera_only:=true fortress:=true camera_target:="$target"
```

终端二启动识别。此命令不启动相机驱动、底盘或导航。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
experiment=exp01_color_detection
ros2 launch car1_app "$experiment.launch.py" camera_source:=gazebo use_sim_time:=true
```

终端三查看结果。RQT 下拉框选 `/camera/image` 看原图，选实验节点下的 `result` 看标注。EXP2 结果横向包含三幅图，检测坐标仍以单幅输入图像为准。

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
experiment=exp01_color_detection
ros2 topic info -v /camera/image
ros2 topic hz /camera/image        # 打印帧率后按 Ctrl+C
ros2 topic echo "/$experiment/detections" std_msgs/msg/String --once
ros2 run tf2_ros tf2_echo base_footprint camera_sim_optical_frame  # 按 Ctrl+C 返回
ros2 run rqt_image_view rqt_image_view
```

## 不启动 Gazebo 的自检

先关闭同名实验节点。在已加载工作区的终端运行以下示例；其他实验用表中的节点名和样例文件名替换。静态模式每秒发布两帧，使用系统时间即可。

```bash
share=$(ros2 pkg prefix --share car1_app)
ros2 launch car1_app exp02_polygon_detection.launch.py \
  image_path:="$share/images/exp02_polygons.png" use_sim_time:=false
```

## 共用输入与参数

- 三个独立 launch 均使用 `car1_app/experiment_launch.py`。默认实验参数来自 `config/exp*.yaml`，相机预设来自 `config/camera_topics.yaml`。使用 `config_file` 可覆盖相应节点的参数，显式 `camera_topic`、`image_path`、`use_sim_time` 启动参数优先。非空 `image_path` 选择文件输入。自定义 YAML 的顶层键使用实验节点名。
- `camera_source:=gazebo` 选 `/camera/image`，`camera_source:=hp60c` 选 HP60C 原生彩色话题。自定义桥接名直接加 `camera_topic:=/my_camera/color/image_raw`。查看最终值可运行 `ros2 param get /exp01_color_detection camera_topic`。相机输入在节点启动时确定。
- `image_experiment.py` 订阅原始 `sensor_msgs/msg/Image`，采用传感器 QoS（best effort、volatile、队列深度 5），可匹配 best effort 和 reliable 发布者。cv_bridge 按消息的 encoding 转为 `bgr8`。深度、点云和压缩话题不能代替彩色原图。结果图为 `bgr8`，掩膜为 `mono8`，两个图像话题及 JSON 检测结果均采用 reliable、深度 10，并保留源帧和时间戳。
- 有话题却没有画面时，先用 `ros2 topic info -v` 确认发布端、订阅端、类型和 QoS，再看 `ros2 topic echo /camera/image --field encoding --once --qos-reliability best_effort`。节点有输出但没有目标时切回原图，核对场景目标、遮挡与光照。启用仿真时间后可检查 `ros2 topic hz /clock`。

固定相机场景发布机器人 TF 和图像，不提供移动底盘的轮式里程计、激光扫描或 Nav2 行驶验收。真机的导航链路和只读检查见[真机指南](REAL_ROBOT_GUIDE.md)。各实验的算法及操作见 [EXP1](EXP01_COLOR_DETECTION.md)、[EXP2](EXP02_POLYGON_DETECTION.md)、[EXP3](EXP03_QRCODE_DETECTION.md)。[课程入口](https://course-generate-agent.pages.dev/courses/core/exp001-robot-vision/)

## 本阶段验证记录

| 检查 | 实测结果 |
|---|---|
| Fortress 图像桥接与 TF | 三个场景收到带仿真时间戳的检测消息，源帧为 `camera_sim_optical_frame`。查询 `base_footprint → camera_sim_optical_frame` 得到平移约 (0.015, 0.036, 0.538) m。 |
| 三个场景的目标 | EXP1 将被车体遮挡的色球移到左前方后同时检出红、绿、蓝、黄。EXP2 调整摆位并为 OBJ 补齐材质、法线和 UV 后，同一帧检出 3、4、5、6 个顶点的四种图形。EXP3 解出 `C1-EXP3`。 |
| 共用输入与启动参数 | 每个实验分别以 Gazebo 话题（测试发布器，rgb8、best effort）、HP60C 话题（测试发布器，bgr8、reliable）、YAML 话题覆盖、命令行话题覆盖、YAML 本地图片启动。15 组均收到预期目标数和图像编码，订阅模式保留原始消息头。逐个检查实验节点发布端，均无电机、舵机或速度命令话题。 |
| 依赖 | Humble 中 18 项算法回归通过，x86‑64 版 ascamera 构建成功，厂商源码有编译警告。加载 ROS 环境后检查安装的可执行文件，ldd 未发现缺失动态库。 |
| 现场待验收 | 没有连接 HP60C、底盘或雷达。真机 USB 采集、帧率、TF 标定、轮式里程计精度及 Nav2 到点行驶均待现场测量。 |
