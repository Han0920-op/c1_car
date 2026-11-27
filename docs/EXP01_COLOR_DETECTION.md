# EXP1 颜色识别实验

本实验用 OpenCV 标注红、绿、蓝、黄目标，并输出颜色名称和中心像素坐标。它只处理图像，不启动底盘、机械臂或抓取节点。[对应课程网页](https://course-generate-agent.pages.dev/courses/core/exp001-robot-vision/exp-01-color-hsv/index.html)

## 原理

1. ROS 2 节点订阅相机的 `sensor_msgs/msg/Image`，用 `cv_bridge` 统一转换成 OpenCV 的 `bgr8` 图像。
2. 用 `cv2.cvtColor` 将 BGR 转为 HSV。H 表示色相，S 表示饱和度，V 表示明度。在 OpenCV 的 8 位 HSV 中，H 的范围是 0–179，S 和 V 的范围是 0–255。
3. 每种颜色配置下界和上界。默认红色 H 下界 170、上界 10，表示跨越 179 到 0 的边界，实际匹配 170–179 和 0–10。两个区间共用同一组 S、V 上下界。
4. `cv2.inRange` 把满足阈值的像素标成白色，其余标成黑色。跨界红色的两个掩膜通过按位 OR 合并。
5. 每个颜色掩膜先做开运算消除孤立噪点，再做闭运算填补小孔。沿用项目原有 HSV 示例的 5×5 椭圆核。
6. `findContours` 提取每种颜色的外轮廓。过滤小于最小面积的轮廓。同色多个目标可以分别输出。
7. 用 `boundingRect` 绘制边框。中心用轮廓图像矩计算，公式为 `u = m10/m00`、`v = m01/m00`，结果取整。
8. 输出颜色、中心和边框。图像左上角为原点，u 向右、v 向下，单位为像素。物体在车体坐标系中的位置需要另做深度投影，本实验输出的是二维图像坐标。

## 代码结构

| 文件 | 职责 |
|---|---|
| `car1_app/color_detection.py` | HSV 阈值、掩膜、形态学、轮廓及绘图，可脱离 ROS 验证。 |
| `car1_app/exp01_color_detection.py` | ROS 图像输入、静态图片模式和结果发布。 |
| `launch/exp01_color_detection.launch.py` | 独立实验入口，传入话题、配置文件和可选图片。 |
| `config/exp01_color_detection.yaml` | 四种颜色的 HSV 阈值及最小轮廓面积。 |
| `images/exp01_colors.png` | 五个明显目标，其中红色在 H 低端和高端各有一个，另含用于观察降噪的小孔、孤立像素和小色斑。 |
| `car1_gazebo/models/exp01_color_targets/model.sdf` | 在已有固定相机场景中放置四色球。默认红球检查仍可用。 |

## 准备工作区

以下命令在 Ubuntu 22.04、ROS 2 Humble 和 C1 仓库根目录使用。静态图片和相机输入使用同一个实验入口。

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-opencv python3-numpy \
  ros-humble-cv-bridge ros-humble-rqt-image-view
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_app
source install/setup.bash
```

### 方式一：静态测试图片

```bash
ros2 launch car1_app exp01_color_detection.launch.py \
  image_path:="$(ros2 pkg prefix --share car1_app)/images/exp01_colors.png"
```

静态模式以 2 Hz 重复处理安装后的图片，便于稍后打开 RQT。预期有五条检测结果，红色中心分别约为 `(120, 100)` 和 `(420, 260)`，绿色 `(320, 100)`，蓝色 `(520, 100)`，黄色 `(220, 260)`。掩膜上的小色斑可保留，轮廓面积过滤会阻止它生成检测结果。

### 方式二：Ignition Fortress 四色球

安装与构建步骤详见 [仿真相机说明](CAMERA_SIMULATION.md)。按其中步骤安装仿真依赖并构建 `car1_description`、`car1_gazebo`。加载工作区后运行：

```bash
ros2 launch car1_gazebo grasp_demo_vision.launch.py \
  camera_only:=true fortress:=true camera_target:=exp01_color_targets
```

另外打开终端，进仓库并加载同一 ROS 环境和工作区：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch car1_app exp01_color_detection.launch.py camera_topic:=/camera/image
```

预期在 Gazebo 原始 RGB 画面中看到四个固定球，实验结果中出现四种颜色的边框与中心。渲染光照和材质会改变 HSV，如果原图可见但某色掩膜为空，应根据现场图像调阈值。此方式不启动运动控制或抓取。已有其他 ROS 相机发布节点时，同样可把 `camera_topic` 改为相机的 RGB 图像话题。例如 HP60C 的某些启动配置使用 `/ascamera_hp60c/camera_publisher/rgb0/image`，以 `ros2 topic list -t` 为准。

## 用 RQT 和命令查看结果

另开加载了相同工作区的终端：

```bash
ros2 run rqt_image_view rqt_image_view
```

在下拉框选择 `/exp01_color_detection/result` 看彩色边框和白色中心，选择 `/exp01_color_detection/mask` 看合并后的黑白掩膜。摄像头模式也可切到原始 `/camera/image` 做对照。

```bash
ros2 topic list -t | grep -E 'camera/image|exp01_color_detection'
ros2 topic info -v /camera/image
ros2 topic echo /exp01_color_detection/detections std_msgs/msg/String --once
```

`result` 是 `bgr8` 图像，`mask` 是 `mono8` 图像。两者保留输入帧的时间戳和 `frame_id`。检测话题是 `std_msgs/msg/String`，`data` 为 JSON，包含 `stamp`、`frame_id` 和 `detections` 列表。每项包含 `color`、`u`、`v`、`area_px2` 和 `bbox`，边框顺序为 `[左, 上, 宽, 高]`。另有最小外接圆 `circle`，包含圆心 `u`、`v` 和像素半径 `radius_px`。质心与圆心对不规则物体可能不同。没有目标时发布空列表。

## 参数调节和排错

可复制并修改安装后的配置，再重启实验。HSV 数组使用整数，`min_area` 使用浮点数，单位是平方像素。参数在启动时加载，先观察掩膜，再逐项调整。

```bash
cp "$(ros2 pkg prefix --share car1_app)/config/exp01_color_detection.yaml" ./exp01-local.yaml
ros2 launch car1_app exp01_color_detection.launch.py \
  camera_topic:=/camera/image config_file:="$(pwd)/exp01-local.yaml"
```

| 现象 | 检查方法 |
|---|---|
| RQT 没有结果图像 | 确认选中结果图话题，检查实验节点日志。相机模式先核对输入话题是否为 RGB、是否持续出帧、两个终端是否在同一 `ROS_DOMAIN_ID`。节点按传感器 QoS 订阅。 |
| 原图正常但没有某种颜色 | 先看该目标位置的白色掩膜。检查输入是否为深度图、光照是否太暗，以及阈值是否把低饱和度或低明度排除了。 |
| 红色只检出一部分 | 确认红色 H 下界比上界大，例如 170 到 10，且 S 和 V 上下界仍按从小到大排列。 |
| 掩膜有小目标却没有框 | 轮廓面积可能小于 `min_area`，或目标被 5×5 开运算去除。先依据目标在画面中的大小调整面积。 |
| 同一个目标被不同颜色标注 | 检查不同颜色的 HSV 范围是否重叠，缩小阈值交集。 |
| 仿真场景看不到球，或相机不出图 | 按 [仿真相机说明](CAMERA_SIMULATION.md) 分别检查 Gazebo Sensors、桥接、RQT 和渲染。 |

## 验证记录

静态测试用例位于 `test/test_exp01_color_detection.py`，覆盖两端红色、四色坐标、边框、形态学和面积过滤，以及无效配置拒绝。

- **离线通过**。运行 5 项 pytest 用例，全部通过。Python、YAML、SDF 解析与 `git diff --check` 通过。
- **Humble 容器通过**。`car1_app`、`car1_description` 和 `car1_gazebo` 构建成功，确认四色模型安装。通过自定义 ROS 图像话题发送样例帧，实际收到标注图、掩膜和五项检测，并核对图像编码、时间戳与 `frame_id`。另从安装路径启动静态模式，实际收到五项检测。
- **Fortress 实测**。系统集成时将四球布置到车体左前方。640×480 相机帧同时检出红、绿、蓝、黄，中心约为 (209,253)、(95,267)、(206,151)、(104,162)。实体相机待验收。[集成步骤](SIMULATION_GUIDE.md)
