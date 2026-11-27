# EXP2 多边形描绘实验

在相机图像中分离目标，再用三种线条描述同一个物体的边界。实验可识别三角形、四边形、五边形和六边形，输出顶点、面积和中心像素坐标。[对应课程网页](https://course-generate-agent.pages.dev/courses/core/exp001-robot-vision/exp-02-contour-polygon/index.html)

## 轮廓、逼近多边形与凸包

| 几何表示 | 如何得到 | 在结果图中的含义 |
|---|---|---|
| 原始轮廓 | `findContours(mask, RETR_EXTERNAL, CHAIN_APPROX_NONE)` 沿白色目标的外边界取点。 | 左栏青色线。它保留二值掩膜的像素阶梯、轻微噪声和凹陷。 |
| 逼近多边形 | `arcLength(contour, True)` 计算闭合轮廓周长。将周长乘 `epsilon_ratio` 得到像素容差，再用 `approxPolyDP`（Douglas–Peucker）减少边界点。 | 中栏绿色线，黄色圆点是保留顶点，白点表示轮廓质心。可用此图数边和观察误差。 |
| 凸包 | `convexHull(contour)` 找到包含原轮廓的最小凸边界。可想象一根橡皮筋收紧后包住物体。 | 右栏紫色线。它会跨过凹口，原轮廓内部的凹陷不会出现在凸包上。 |

用 `drawContours` 绘制三栏边界。用 `contourArea` 分别计算原始轮廓和凸包面积。中心用原始轮廓的图像矩计算，公式为 `u = m10/m00`、`v = m01/m00`。报告坐标相对于输入图像左上角，u 向右、v 向下，单位为像素。结果图是三栏拼接，JSON 中的坐标仍位于原输入图坐标系。

类别按**凸的逼近轮廓**顶点数判定，3、4、5、6 分别对应四种常见图形。`quadrilateral` 包括所有符合条件的四边形。凹形或其他顶点数输出 `other`，仍可观察边界和顶点。圆形在一般容差下会呈现多于六个顶点，容差过高时可能被误判。两目标相接时会形成一个连通区域，应先在画面中分开。

### 如何得到掩膜

默认使用 HSV 的 S 通道，提取饱和度高于 80 的区域，适用于灰色背景上的彩色样例或仿真薄板。拍摄白纸上的黑色图形时，可用 `dark` 模式按灰度反阈值分割；暗背景的亮色图形可用 `bright`。沿用 EXP1 的 5×5 椭圆核做开运算和闭运算。实验过滤面积太小和边界被画面裁断的轮廓。

## 项目文件

- `car1_app/image_experiment.py` 由 EXP1 与 EXP2 共用，负责图像话题订阅、静态图输入、`cv_bridge` 转换、时间戳和发布。
- `car1_app/polygon_detection.py` 实现掩膜、轮廓、逼近、凸包、分类和三栏绘图。 `car1_app/exp02_polygon_detection.py` 声明实验参数并加载算法。
- `launch/exp02_polygon_detection.launch.py` 提供独立入口，默认读取 `config/exp02_polygon_detection.yaml`。
- `images/exp02_polygons.png` 包含四种目标、一个凹 L 形和一个圆。仿真模型 `exp02_polygon_targets` 是四块固定的彩色多边形薄板。两种模式都只做视觉观察。

## 操作一：用测试图片检查算法

在 Ubuntu 22.04、ROS 2 Humble 的 C1 仓库根目录执行：

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-opencv python3-numpy \
  ros-humble-cv-bridge ros-humble-rqt-image-view
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_app
source install/setup.bash

ros2 launch car1_app exp02_polygon_detection.launch.py \
  image_path:="$(ros2 pkg prefix --share car1_app)/images/exp02_polygons.png"
```

样例以 2 Hz 重复处理。预期发布六个目标，其中三角形 3 顶点、四边形 4 顶点、五边形 5 顶点和六边形 6 顶点，另有两个 `other`。推荐观察 L 形的拐角。中栏逼近轮廓沿着拐角，右栏凸包跨过缺口，凸包面积随之增大。

## 操作二：在 Gazebo 仿真中识别四块薄板

按 [仿真相机说明](CAMERA_SIMULATION.md) 安装 Ignition Fortress 和 ROS 桥接依赖，在同一工作区构建：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_description car1_gazebo car1_app
source install/setup.bash

ros2 launch car1_gazebo grasp_demo_vision.launch.py \
  camera_only:=true fortress:=true camera_target:=exp02_polygon_targets
```

在另一终端进入仓库根目录并加载相同环境：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch car1_app exp02_polygon_detection.launch.py camera_topic:=/camera/image
```

预期在车体左前方看到两排薄板，包括红色三角形、绿色四边形、蓝色五边形和黄色六边形。仿真使用固定相机和模型，无需启动底盘、机械臂控制或抓取。实际输入话题可通过 `camera_topic:=...` 修改。

### RQT 和数值结果

加载工作区后执行 `ros2 run rqt_image_view rqt_image_view`。选择：

- `/exp02_polygon_detection/result` 查看原始轮廓、逼近多边形和凸包三栏图。
- `/exp02_polygon_detection/mask` 查看分割是否完整。
- `/camera/image` 对照仿真原图，静态模式无需该话题。

```bash
ros2 topic info -v /camera/image
ros2 topic echo /exp02_polygon_detection/detections std_msgs/msg/String --once
```

检测消息的 `data` 是 JSON，每帧含 `stamp`、`frame_id` 和 `detections`。每个目标含 `category`、`vertex_count`、`vertices`（逼近后的各顶点 `[u,v]`）、`area_px2`、`hull_area_px2`、`perimeter_px` 和 `u,v`（质心）。没有合格目标时，检测列表为空。

## 调参和常见问题

```bash
cp "$(ros2 pkg prefix --share car1_app)/config/exp02_polygon_detection.yaml" ./exp02-local.yaml
ros2 launch car1_app exp02_polygon_detection.launch.py \
  camera_topic:=/camera/image config_file:="$(pwd)/exp02-local.yaml"
```

修改配置后重启实验。默认最小面积为 `500.0 px²`，`epsilon_ratio` 为 `0.025`。

| 现象 | 检查 |
|---|---|
| 没有结果图像 | 检查相机原图和 ROS 话题类型。若相机尚未出帧，先用测试图片区分算法与输入问题。 |
| 掩膜全黑或背景大面积变白 | 检查 `foreground_mode` 与目标和背景是否匹配，再调整 0–255 的 `threshold`。 |
| 顶点数量偏多 | 先检查边缘是否破碎，再适当提高 `epsilon_ratio`。 |
| 角消失或边数过少 | 降低 `epsilon_ratio`，检查目标是否过小、模糊或被遮挡。 |
| 掩膜中有白块却不输出目标 | 检查轮廓面积是否低于 `min_area`，以及物体是否被图像边缘裁断。 |
| 仿真模型已生成但画面看不到薄板 | 检查 Gazebo 的 mesh URI 或资源路径报错，确认加载了最新工作区和已安装的 `exp02_polygon_targets` 网格；再检查原图和桥接。 |

## 验证记录

EXP2 的三项离线测试和 EXP1 的五项回归测试全部通过。按零位相机位姿对四块薄板的 OBJ 顶点做离线投影，确认它们在视野及裁剪范围内，合成投影图由默认参数检出 3、4、5、6 顶点各一项。该检查使用模型几何与材质颜色，未运行 Gazebo 渲染。

Ubuntu 22.04 / Humble 容器中构建了 `car1_app`、`car1_description` 和 `car1_gazebo`，检查了已安装模型和场景参数。EXP2 通过 ROS 相机话题与静态图片各发布六个目标，EXP1 继续通过相机话题发布五个样例目标。验证接收了标注图、掩膜和检测消息，并核对了 ROS 相机模式的时间戳和帧名。修复并复测了 Humble 在接收图像时退出可能出现的关闭异常。

系统集成时为 OBJ 补齐材质、法线和纹理坐标，调整彩板位置。Humble／Fortress 的实际相机帧检出三、四、五、六边形各一项。实体相机待验收。[集成步骤](SIMULATION_GUIDE.md)
