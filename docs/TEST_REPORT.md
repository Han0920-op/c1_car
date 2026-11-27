# C1 工作区最终验收报告

**验收结论：三个基础视觉算法、ROS 图像通信和 Fortress 相机场景通过。全仓自动化测试仍有失败，实车运动尚未验收。** 环境为 x86-64 Ubuntu 22.04 容器、ROS 2 Humble、Ignition Fortress，通过虚拟显示器进行软件渲染。构建使用单独工作区，未连接 USB、串口或执行器。

## 实测结果

| 项目 | 方法与结果 |
|---|---|
| 源码与导入 | 对 src 下 190 个 Python 文件解析语法，并在已加载工作区的系统 Python 中逐个加载 39 个已安装 Python console_scripts 入口。修复 ASR 无效导入、装齐依赖后 39 个均能加载。引擎初始化和模型推理需另测。 |
| 依赖与构建 | colcon 发现并构建 23 个包。校正清单、安装系统依赖后，rosdep check 返回 All system dependencies have been satisfied。首次干净构建的厂商相机及雷达 C++ 源码有警告，编译成功。 |
| Launch | 对安装目录下 54 个 Python launch 执行 --show-args。手动参考抓取入口首次解析失败，改用原有 manual 模式后，最终一轮 54 个均返回成功。参数检查不等同于驱动、设备和控制器全部启动。 |
| ROS 视觉链路 | 18 项算法回归通过。每个实验分别用 Gazebo 预设话题、HP60C 预设话题、YAML 自定义话题、命令行覆盖和本地图片启动，共 15 组。测试发布器模拟 rgb8/best effort 与 bgr8/reliable，实际检查结果数、图像编码、消息头和运动发布端。 |
| Gazebo 与 TF | 三个实际渲染场景通过桥接输出检测数据。零位时 base_footprint 到 camera_sim_optical_frame 的平移约为 (0.015, 0.036, 0.538) m。 |
| EXP1 | 同帧读到红、绿、蓝、黄四球，红球质心 (209,253)，最小外接圆半径约 23.59 像素。 |
| EXP2 | 同帧检出三角形、四边形、五边形、六边形各一个，顶点数为 3、4、5、6。 |
| EXP3 | 半分辨率检测从实际相机帧解出 C1-EXP3，并返回原图四角。生成、中文读回、MJPEG 与 RQT 的实测记录见 EXP3 文档。 |
| 底盘 | 隔离 ROS 域中运行 odom_publisher，收到 /odom_raw，子帧为 base_footprint。未启动板卡驱动，未测轮速、横移距离或急停。原始位姿依靠命令速度积分。 |
| SLAM | 使用项目 slam.yaml、测试用静态 TF 和合成 361 束扫描，slam_toolbox 发布 80×80 的栅格地图。移动建图、回环与地图精度待实测。 |
| Nav2 | 用仓库地图、定位及导航子 launch 和测试 TF，7 个节点进入 active。调用 ComputePathToPose 成功，返回 7 个路径点。没有发送导航行驶目标，AMCL 实际定位误差、避障和路径跟随待验收。 |

## 本次修复

- 10 个包的 package.xml 将不可解析的构建依赖 ament_python 换为 python3-setuptools，保留 ament_python 构建类型；底盘的 pyserial 改用 rosdep 键 python3-serial。网页查看器声明 Flask 和 Flask-SocketIO 运行依赖。
- car1_speech 移除未使用且 Humble 不提供的 sensor_msgs.msg.Audio 导入。ASR 节点依然是模拟实现。删除 bringup/launch 中遮蔽 ROS launch 包的空 Python 包标记。
- 修复 grasp_manual_ref 启动入口错误地向 IncludeLaunchDescription 注册进程退出事件的问题，复用基础 launch 对控制器的等待顺序和手动抓取模式。已校正导航 setup.py 和行为树路径设置的超长行。
- EXP1 在原有质心与边框基础上绘制最小外接圆并输出半径。更新实验文档、根 README，增加学习指南及本报告。

## 尚未通过或有条件通过的部分

最终一次 `colcon test-result --all` 汇总为 **2148 tests, 3 errors, 2094 failures, 32 skipped**。该工具同时统计 CTest 和底层 lint XML，不能把这个数字解释为独立机器人功能的数量。18 项视觉回归另外用 pytest 显式执行。

- 厂商 ascamera 与 m1ct_d2 有大量既有版权、C++ 样式及格式检查失败，导航包版权检查也未通过。未批量重写厂商源码或添加未经确认的版权声明。
- car1_speech 和 car1_llm 的 pytest 自动收集到了依赖额外模型或服务的交互工具，分别发生 sherpa_onnx 缺失、工具导入时退出。ROS 清单能解析和命令入口能加载，无法替代语音识别与云服务验收。
- 原机械臂 FK/IK 往返脚本输出 1 项通过、3 项失败。失败误差为 18.40、22.95、21.73 mm，容差 1.5 mm；脚本返回成功退出码。需核对运动学模型和标定后重新验收。
- EXP1、EXP2 的 ROS/RQT 主链路可运行，仓库未完整复现这两课的原版交互滑块与网页操作，当前可通过 YAML 调参。EXP3 已有独立课程网页流入口。
- HP60C 真机帧率和 USB 权限、雷达串口、机械臂动作、底盘动态精度及导航到点未验证。仿真通过也不能证明 VMware 上的显卡驱动与当前容器表现一致。

## Ubuntu 22.04 复测

配置 Humble 软件源后，在仓库根目录执行。首次使用 rosdep 的机器先运行一次 sudo rosdep init。

```bash
source /opt/ros/humble/setup.bash
rosdep update --rosdistro humble
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
rosdep check --from-paths src --ignore-src
colcon build --parallel-workers 3
source install/setup.bash
python3 -m compileall -q src
python3 -m pytest -q src/xflz_eai_car1/app/car1_app/test
colcon test --parallel-workers 3
colcon test-result --verbose
python3 src/xflz_eai_car1/arm/kinematics/kinematics/test_fk_ik.py
```

仿真复测按[三个终端的命令表](LEARNING_GUIDE.md)逐项切换目标。接入 HP60C 后按[真机指南](REAL_ROBOT_GUIDE.md)测首帧、TF 和识别结果。实车建图和导航应分别运行，先确认底盘和雷达串口、地图与物理场地、初始位姿及急停。它们会启动硬件控制栈。以下命令每次只运行一个入口，另开终端检查话题；导航测试先不发送目标。

```bash
ros2 launch car1_slam slam.launch.py
# 另一个已加载环境的终端
ros2 topic hz /scan
ros2 topic echo /map --once --field info
ros2 run tf2_ros tf2_echo map base_footprint

# 结束建图栈后，使用已保存且与现场匹配的地图启动导航
ros2 launch car1_navigation navigation.launch.py map_dir:="$PWD/maps" map:=my_map
# 上例对应 maps/my_map.yaml 和该 YAML 引用的图像
ros2 lifecycle get /bt_navigator
ros2 action list -t
```

## 累计修改文件

下面列出验收时相对当前 Git HEAD 的工作区差异，包含之前各阶段的开发及文档，不能仅凭 Git 状态推断文件作者。各阶段的修改原因另见[源码审计](PROJECT_AUDIT.md)、[相机排查](CAMERA_SIMULATION.md)和[集成记录](SIMULATION_GUIDE.md)。


```text
 M README.md
 M src/xflz_eai_car1/app/car1_app/car1_app/test_hsv_detection.py
 M src/xflz_eai_car1/app/car1_app/package.xml
 M src/xflz_eai_car1/app/car1_app/setup.py
 M src/xflz_eai_car1/arm/kinematics/CMakeLists.txt
 M src/xflz_eai_car1/arm/kinematics/kinematics/fk_demo.py
 M src/xflz_eai_car1/arm/kinematics/package.xml
 D src/xflz_eai_car1/bringup/launch/__init__.py
 M src/xflz_eai_car1/bringup/launch/bringup.launch.py
 M src/xflz_eai_car1/calibration/package.xml
 M src/xflz_eai_car1/driver/car1_base_driver/package.xml
 M src/xflz_eai_car1/driver/car1_sdk/package.xml
 M src/xflz_eai_car1/driver/car1_servo_controller/package.xml
 M src/xflz_eai_car1/driver/controller/launch/chassis_controller.launch.py
 M src/xflz_eai_car1/driver/controller/package.xml
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/CMakeLists.txt
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/ascamera.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/changA.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/hp60c.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/hp60cn.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/kondyor.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/kunlun_a.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/kunlun_c.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/launch/nuwa.launch.py
 M src/xflz_eai_car1/examples/camera/HP60C/src/ascamera/package.xml
 M src/xflz_eai_car1/eye_hand_calibration/eye_hand_calibration/data_collector.py
 M src/xflz_eai_car1/eye_hand_calibration/package.xml
 M src/xflz_eai_car1/interaction/car1_speech/car1_speech/asr_node.py
 M src/xflz_eai_car1/navigation/car1_navigation/config/nav2_params.yaml
 M src/xflz_eai_car1/navigation/car1_navigation/launch/include/navigation_base.launch.py
 M src/xflz_eai_car1/navigation/car1_navigation/launch/navigation.launch.py
 M src/xflz_eai_car1/navigation/car1_navigation/package.xml
 M src/xflz_eai_car1/navigation/car1_navigation/setup.py
 M src/xflz_eai_car1/peripherals/car1_peripherals/launch/depth_camera.launch.py
 M src/xflz_eai_car1/peripherals/car1_peripherals/package.xml
 M src/xflz_eai_car1/simulations/car1_gazebo/launch/grasp_demo_vision.launch.py
 M src/xflz_eai_car1/simulations/car1_gazebo/launch/grasp_manual_ref.launch.py
 M src/xflz_eai_car1/simulations/car1_gazebo/package.xml
 M src/xflz_eai_car1/simulations/car1_gazebo/scripts/object_detector.py
 M src/xflz_eai_car1/simulations/car1_gazebo/urdf/car1.gazebo.xacro
 M src/xflz_eai_car1/simulations/car1_gazebo/worlds/camera_demo.sdf
 M src/xflz_eai_car1/slam/car1_slam/package.xml
 M src/xflz_eai_car1/test/camera_web_viewer/launch/camera_viewer.launch.py
 M src/xflz_eai_car1/test/camera_web_viewer/package.xml
?? .gitattributes
?? AGENTS.md
?? docs/CAMERA_SIMULATION.md
?? docs/EXP01_COLOR_DETECTION.md
?? docs/EXP02_POLYGON_DETECTION.md
?? docs/EXP03_QRCODE_DETECTION.md
?? docs/LEARNING_GUIDE.md
?? docs/PROJECT_AUDIT.md
?? docs/REAL_ROBOT_GUIDE.md
?? docs/SIMULATION_GUIDE.md
?? docs/TEST_REPORT.md
?? docs/images/exp03-gazebo-result.png
?? src/xflz_eai_car1/app/car1_app/car1_app/color_detection.py
?? src/xflz_eai_car1/app/car1_app/car1_app/exp01_color_detection.py
?? src/xflz_eai_car1/app/car1_app/car1_app/exp02_polygon_detection.py
?? src/xflz_eai_car1/app/car1_app/car1_app/exp03_qrcode_detection.py
?? src/xflz_eai_car1/app/car1_app/car1_app/experiment_launch.py
?? src/xflz_eai_car1/app/car1_app/car1_app/image_experiment.py
?? src/xflz_eai_car1/app/car1_app/car1_app/polygon_detection.py
?? src/xflz_eai_car1/app/car1_app/car1_app/qrcode_detection.py
?? src/xflz_eai_car1/app/car1_app/config/camera_topics.yaml
?? src/xflz_eai_car1/app/car1_app/config/exp01_color_detection.yaml
?? src/xflz_eai_car1/app/car1_app/config/exp02_polygon_detection.yaml
?? src/xflz_eai_car1/app/car1_app/config/exp03_qrcode_detection.yaml
?? src/xflz_eai_car1/app/car1_app/images/exp01_colors.png
?? src/xflz_eai_car1/app/car1_app/images/exp02_polygons.png
?? src/xflz_eai_car1/app/car1_app/images/exp03_qrcode.png
?? src/xflz_eai_car1/app/car1_app/launch/exp01_color_detection.launch.py
?? src/xflz_eai_car1/app/car1_app/launch/exp02_polygon_detection.launch.py
?? src/xflz_eai_car1/app/car1_app/launch/exp03_qrcode_detection.launch.py
?? src/xflz_eai_car1/app/car1_app/test/test_exp01_color_detection.py
?? src/xflz_eai_car1/app/car1_app/test/test_exp02_polygon_detection.py
?? src/xflz_eai_car1/app/car1_app/test/test_exp03_qrcode_detection.py
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp01_color_targets/model.sdf
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/meshes/hexagon.obj
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/meshes/pentagon.obj
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/meshes/polygons.mtl
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/meshes/quadrilateral.obj
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/meshes/triangle.obj
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp02_polygon_targets/model.sdf
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp03_qrcode_target/meshes/modules.mtl
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp03_qrcode_target/meshes/modules.obj
?? src/xflz_eai_car1/simulations/car1_gazebo/models/exp03_qrcode_target/model.sdf
?? src/xflz_eai_car1/simulations/car1_gazebo/models/red_ball/model.sdf
?? src/xflz_eai_car1/vision/04_qrcode/config/qrcode_config.yaml
?? src/xflz_eai_car1/vision/04_qrcode/src/app.py
?? src/xflz_eai_car1/vision/04_qrcode/src/live_scan.py
```
