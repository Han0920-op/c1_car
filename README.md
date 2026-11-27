# C1 智能小车 ROS 2 工作区

本项目用于学习相机感知、机械臂、底盘、建图和导航。学习环境为 Ubuntu 22.04、ROS 2 Humble 和 Gazebo Ignition Fortress。三个基础视觉实验均可单独运行，默认只输出识别结果。

| 我想做什么 | 从哪里开始 |
|---|---|
| 第一次运行、了解 23 个功能包和三个实验的代码 | [初学者学习指南](docs/LEARNING_GUIDE.md) |
| 在 Gazebo 看相机原图、掩膜和检测结果 | [仿真指南](docs/SIMULATION_GUIDE.md) |
| 把同一实验切换到 HP60C | [真机指南](docs/REAL_ROBOT_GUIDE.md) |
| 核对已通过、尚未验收的功能及修改文件 | [最终验收报告](docs/TEST_REPORT.md) |
| 按课程逐步学习 | [颜色识别](docs/EXP01_COLOR_DETECTION.md)、[多边形描绘](docs/EXP02_POLYGON_DETECTION.md)、[二维码生成与识别](docs/EXP03_QRCODE_DETECTION.md) |

安装依赖后，在仓库根目录用一张图片做首次自检。成功后可在另一已加载工作区的终端运行 `ros2 run rqt_image_view rqt_image_view`，选择 `/exp01_color_detection/result`。

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select car1_app
source install/setup.bash
ros2 launch car1_app exp01_color_detection.launch.py \
  image_path:="$(ros2 pkg prefix --share car1_app)/images/exp01_colors.png"
```

[课程主页](https://course-generate-agent.pages.dev/courses/core/exp001-robot-vision/) · [项目开发规范](AGENTS.md) · [源码审计](docs/PROJECT_AUDIT.md)
