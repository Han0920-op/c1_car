# 从第一帧相机图像开始学习 C1

先用 README 的图片命令认识输出，再在仿真中接收连续画面，最后换 HP60C。彩色框或二维码中心的单位是像素；要让机械臂去抓，还要测深度并把点变换到机械臂坐标系。

## 工作区地图

`src/xflz_eai_car1` 是源码树，colcon 构建后把运行入口放入 `install`。终端执行 `source install/setup.bash` 后，ROS 才能找到当前版本。下面每行对应一个可发现的包。

| 包 | 在小车中做什么 |
|---|---|
| ascamera | 调厂商 SDK，将 HP60C 的彩色图、深度和内参发布到 ROS。 |
| m1ct_d2 | COIN-D6 雷达驱动，提供激光扫描。 |
| car1_base_driver_msgs | 定义底层板卡使用的消息和服务，例如电机状态。 |
| car1_base_driver | 连接控制板串口，收发传感器数据和执行器命令。 |
| car1_sdk | 供其他节点调用的 Python 工具与硬件接口。 |
| car1_servo_controller_msgs | 定义舵机控制使用的消息和服务。 |
| car1_servo_controller | 将上层舵机和关节请求转到底层控制接口。 |
| controller | 将底盘速度转换成麦克纳姆轮命令，发布原始里程计，组织 IMU 和 EKF。 |
| car1_bringup | 组合真机驱动、关节状态、机器人 TF 和底盘控制。 |
| car1_peripherals | 单独启动相机或雷达等外设。 |
| car1_description | URDF 定义各连杆、关节和安装关系，网格给出外观。 |
| car1_gazebo | 提供世界、仿真传感器、固定实验目标及 ROS 桥接。 |
| car1_app | 三个视觉实验和原有循迹、抓取等应用。请选择名称以 exp 开头的识别入口。 |
| camera_web_viewer | 将 RGB-D 和点云提供给浏览器查看。 |
| car1_kinematics | 机械臂正逆运动学，在关节角与末端位姿间换算。 |
| car1_arm_controller | 提供机械臂动作和执行控制。 |
| car1_moveit_config | 配置 MoveIt 的机械臂模型、规划和控制。 |
| calibration | 提供小车标定工具。 |
| eye_hand_calibration | 采集手眼标定数据，估计相机与机械臂之间的变换。 |
| car1_slam | 组合底盘、雷达与 slam_toolbox 建图，并保存地图。 |
| car1_navigation | 加载已有地图，由 AMCL 定位、Nav2 规划并跟随路径。 |
| car1_speech | 唤醒、语音识别和合成接口，部分节点仍使用模拟结果。 |
| car1_llm | 语言交互与任务接口，需要相应模型或服务。 |

## 图像如何到达 OpenCV

发布者将编码、宽高、每行字节数、像素数据、时间戳及坐标系打包成 `sensor_msgs/msg/Image`。Gazebo 的画面先经过 ros_gz_bridge，HP60C 直接由 ascamera 发布。三个节点继承 `car1_app/image_experiment.py` 中的 ImageExperiment。它用传感器 QoS 订阅彩色话题，cv_bridge 按编码转换成 BGR 数组，再调用对应检测器。检测器返回标注图、掩膜和检测列表。ROS 节点把它们分别发布到自己的 `result`、`mask`、`detections`，并保留来源帧信息。

| 实验 | 跟读的源码（app/car1_app/car1_app 内） | 看什么 |
|---|---|---|
| EXP1 | `color_detection.py` | cvtColor 将 BGR 转为 HSV，inRange 选像素，红色合并色相两端的掩膜。开闭运算去噪后找轮廓，按面积筛选并标框、标中心。 |
| EXP2 | `polygon_detection.py` | findContours 得到边界，arcLength 算周长，approxPolyDP 用周长的一定比例作容差简化边界。convexHull 包住凹口，contourArea 算面积。比较结果图的三栏和顶点数。 |
| EXP3 | `qrcode_detection.py` | 在缩放图上 detectAndDecode，将四角映回原图，涂白已读区域后继续找码。Humble 缺 QUIRC 时利用角点校正原图交给 ZBar。课程生成命令在 vision/04_qrcode。 |

## 每个实验怎么开

先按[仿真指南](SIMULATION_GUIDE.md)安装依赖并构建。三个实验各用 **3 个终端**，每个都在仓库根目录执行 `source /opt/ros/humble/setup.bash` 和 `source install/setup.bash`。每次选一行，在对应终端运行命令。

| 实验 | 终端一（世界） | 终端二（检测） |
|---|---|---|
| EXP1 | `ros2 launch car1_gazebo grasp_demo_vision.launch.py camera_only:=true fortress:=true camera_target:=exp01_color_targets` | `ros2 launch car1_app exp01_color_detection.launch.py use_sim_time:=true` |
| EXP2 | 同上，将 camera_target 改为 `exp02_polygon_targets` | `ros2 launch car1_app exp02_polygon_detection.launch.py use_sim_time:=true` |
| EXP3 | 同上，将 camera_target 改为 `exp03_qrcode_target` | `ros2 launch car1_app exp03_qrcode_detection.launch.py use_sim_time:=true` |

终端三运行 `ros2 run rqt_image_view rqt_image_view`，先选 `/camera/image`，再选对应节点的结果图。只用样例图时省去世界终端，在检测命令中传 `image_path` 并设 `use_sim_time:=false`。二维码的生成和图片读回也可以在一个终端完成。[EXP3 课程操作](EXP03_QRCODE_DETECTION.md)

上车时，终端一改为 `ros2 launch ascamera hp60c.launch.py`，终端二将时间参数改为 `use_sim_time:=false` 并添加 `camera_source:=hp60c`。终端三的结果话题保持一致。设备枚举、udev 和运行库检查见[真机操作](REAL_ROBOT_GUIDE.md)。

## 根据现象排查

- 找不到包：运行 `colcon list` 确认源码存在，再检查当前终端的 `ros2 pkg prefix car1_app`。
- 原图为空：检查图像源和 `ros2 topic info -v /camera/image`。真机替换为 HP60C 原生 RGB 话题。检查发布者数量、消息类型、QoS 以及两端 ROS_DOMAIN_ID。
- 有原图却无框：先用样例图分清输入和算法问题，再查颜色阈值、图形分割模式、二维码静区与目标像素大小。
- 图像有框但三维位置不对：检查时间戳、内参、深度单位和 TF。二维识别通过并不能验证手眼外参。
- 地图或导航无响应：分别检查 `/scan`、`/odometry/filtered`、`map → odom → base_footprint → laser_link` 及 Nav2 生命周期。先做静止检查。

## 之后怎样扩展

先用录制图像实现独立 YOLO 检测节点，沿用相机输入，输出类别、置信度、边框和源帧。用同一批图片核对缩放、补边与坐标还原。迁移 NPU 时，按板卡支持的格式转换模型，比较 CPU 和 NPU 在同一输入上的精度与延迟。再把连续检测框关联为目标 ID，测试遮挡、短暂丢失和重现。最后在仿真中由独立任务节点调用 Nav2 的 NavigateToPose，逐个到达巡逻点，处理超时、取消与定位丢失。以上是后续开发路线，当前识别节点不发布运动命令。
