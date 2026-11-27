# C1 智能小车项目审计

审计日期为 2026-11-26。原本检出的本地 `work` 分支对应远端 `main` 的 `14dc329`，其中只有 README。源码及问题记录位于同一远端的 `master`，该分支与 `main` 没有共同祖先。本次在干净工作区从 `master` 的 `412ba84` 创建本地 `project-audit` 分支，源码修复和本报告均落在该分支。远端分支与原本的 `work` 分支保留。

## 目录与数据流

审计覆盖根目录两份 README、两级 `CLAUDE.md`、`issues/` 三份历史分析，以及 `src/` 中 24 份包清单、52 个 Python 启动文件和相关源码、构建脚本及资源。以下子目录均相对于 `src/xflz_eai_car1/`。

| 子目录 | 包或工具 | 现有功能与接口 |
|---|---|---|
| `bringup/` | `car1_bringup` | 启动 STM32 驱动、机器人模型状态发布及底盘控制。主入口会尝试连接实体串口。 |
| `driver/` | `car1_base_driver`、`car1_base_driver_msgs`、`car1_servo_controller`、`car1_servo_controller_msgs`、`car1_sdk`、`controller` | STM32 串口和消息接口。底盘控制把速度指令转换为麦克纳姆轮命令，发布轮式里程计。互补滤波器处理 IMU，EKF 输出融合里程计。总线舵机层接收关节和轨迹命令，发布关节状态。 |
| `examples/`、`peripherals/` | `ascamera`、`m1ct_d2`、`car1_peripherals` | HP60C USB RGB-D 驱动发布 RGB、深度及相机内参。COIN-D6 串口驱动提供激光扫描。外设启动文件组装驱动并指定话题及设备配置。 |
| `app/` | `car1_app` | 循迹、颜色追踪、手势、激光交互、视觉抓取及导航搬运。已有单独的 HSV 调试节点。识别、追踪与抓取入口用途不同，追踪和抓取入口可能发运动指令。 |
| `slam/` | `car1_slam` | 使用 `slam_toolbox`、激光扫描和底盘 TF 建图，含 RViz、遥控、保存地图工具及 `slam_map.yaml`/PGM。默认建图入口包含真机 bringup。 |
| `navigation/` | `car1_navigation` | Nav2 的地图服务、AMCL、ThetaStar、MPPI、行为树和速度平滑。速度经 `cmd_vel_nav` 转发至 `controller/cmd_vel`，保留原有重映射和无倒车恢复的行为树。 |
| `arm/` | `car1_arm_controller`、`car1_kinematics` | 机械臂 FK、解析 IK、目标位姿和舵机动作。舵机配置将 ID 0–4 分配给机械臂，ID 5 分配给夹爪。 |
| `calibration/`、`eye_hand_calibration/` | `calibration`、`eye_hand_calibration` | 底盘直线、角度及舵机标定。手眼标定包含 AprilTag 检测、数据采集、求解、URDF 更新及验证入口。采集路径可发舵机指令。 |
| `simulations/` | `car1_description`、`car1_gazebo`、`car1_moveit_config` | URDF、网格、RViz、Gazebo 场景、RGB-D 桥接、机械臂控制与抓取演示，以及 MoveIt 规划配置。 |
| `interaction/` | `car1_speech`、`car1_llm`，另有 `car1_interaction` 工具目录 | 唤醒、语音识别、合成、LLM 和联调入口。依赖板端模型、运行库和音频设备。 |
| `test/`、根目录 `fw/` | `camera_web_viewer`、独立 URDF 浏览器、STM32 固件工具 | Web 相机查看和 URDF 浏览。固件镜像与刷写工具属于硬件流程。 |

## 已修复的基础问题

| 实际问题 | 修改 |
|---|---|
| 相机的 `confiPath` 依赖原开发机的源码路径或启动目录，且 CMake 没有安装配置目录。 | 在 `ascamera` 中安装 `configurationfiles/`，8 个厂商启动文件、外设启动和 Web 相机启动共 10 处从已安装包的 share 目录解析配置。保留相机参数及话题设置。 |
| `ascamera/package.xml` 仍声明 ROS 1 的 Catkin、`roscpp` 和 `rospy`，与实际 CMake 不符；底盘实际启动互补滤波器，却声明 Madgwick。 | 对齐 ROS 2 相机、PCL、TF 和启动依赖，补齐相机调用方依赖，声明底盘所用的 `imu_complementary_filter` 及舵机控制包。 |
| 导航固定使用特定工作区下面的地图、RViz 和行为树。 | 地图默认使用已安装的 `slam_map`，新增 `map_dir` 用于读取用户保存的地图，保留 `map` 无扩展名参数；RViz 和自定义行为树从导航包 share 目录定位。补充 `nav2_common` 和 `rviz2` 依赖。 |
| `kinematics.launch.py` 引用 `fk_demo`，但 CMake 未安装该可执行程序。手眼数据采集通过开发机绝对路径加载 IK。 | 安装已有 FK 演示程序并为源脚本设置执行位，保留启动文件所用的名称；采集节点复用已安装的 `kinematics` Python 包，补充相应依赖，并将手眼包的构建工具声明与其现有 ament_python 打包方式对齐。 |
| 底盘 bringup 无条件运行会发送舵机姿态的 `init_pose`。 | 底盘及顶层 bringup 默认关闭这一步。保留显式 `enable_init_pose:=true` 的原功能。此开关只管启动姿态，硬件接口仍会订阅外部运动命令。 |
| Git 未约束 Shell 脚本换行。 | 增加 `.gitattributes`，为 `*.sh` 固定 LF，避免 Windows 检出后回到 Linux 或 WSL 时 shebang 带 CR。 |

## 已发现、仍需处理的问题

- **目标仿真平台**。两级 `CLAUDE.md` 的参考仿真环境是 Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic，而用户目标是 Ubuntu 22.04、ROS 2 Humble、Ignition。当前世界使用 `gz::sim` 系统插件，桥接参数采用 `gz.msgs.*`，控制插件使用 `gz_ros2_control`，机器人 xacro 中仍有 `ignition::gazebo` 的关节状态插件，清单还声明 Gazebo Classic 依赖。需在目标版本核对桥接消息名、控制插件、SDF 和差速/全向底盘接口。已跟踪的演示重点是机械臂与抓取，尚无已验证的仿真底盘、激光、SLAM 和 Nav2 联调入口。现有真机 SLAM/Nav2 顶层启动会带起实体驱动。
- **抓取与 TF**。三份历史 issue 描述了手眼坐标、TF 多发布者、关节反馈及抓取时序。当前 `visual_grasp.py` 已使用 TF 查询和独立 `set_pick_target` 路径，历史上对应的硬编码变换与直接用 `target_pose` 设置抓取目标的结论不能原样沿用。仍需在带时间戳的图像、相机内参及机械臂运动下验证 TF 和深度单位。另一个入口 `track_and_grab.py` 仍使用与接收端不一致的舵机话题，给 `ServosPosition` 写入未定义的 `servo_id` 字段并直接赋值数字列表，夹爪命令还使用 ID 1。需先在仿真或隔离台架验证消息、ID、动作顺序及反馈，再启用该路径。
- **模型与导航**。`car1_description/urdf/package.xml` 与上层清单完全相同，源码清单统计出现两次 `car1_description`；Humble 容器的标准 `colcon list` 只发现上层包，本次没有出现包名冲突。根文档示例的 `map_01` 需要用户自己生成，仓库仅提交 `slam_map`。Nav2 的 MPPI、Rotation Shim、TF 和里程计话题还需针对 Humble 验证。
- **外部资产和依赖**。根文档所述 `src/lander_pi/` 被 Git 忽略，当前检出没有该参考源码。语音和 LLM 模型未提交，部分脚本仍需原板端模型目录及运行时；Web 相机查看器导入 Flask、Flask-SocketIO，项目顶层 requirements 未列出这两项。HP60C 已提交三种 Linux 架构的供应商动态库，需在目标机实测 ABI 和 USB 权限。文档提到的 Windows 不作为这些 Linux 驱动库的原生运行目标。
- **硬件侧默认与联调边界**。本阶段未启动真机。已有应用、遥控、导航、标定和刷写入口仍可能控制实体设备。启动姿态默认关闭并不构成全栈电机禁能。课程仿真验证应使用仿真入口，硬件迁移前另行确认运动使能、急停和速度限制。

## Linux 与 Windows 文件检查

- Git 基线有 529 个跟踪文件，34 个记录为 `100755`，两个记录为 `120000`，没有 Git 子模块。目录遍历发现两个 `llm_server/lib/librkllmrt.so` 均指向板端的 `/usr/lib/librkllmrt.so`，在本机为悬空链接。保留链接，运行时由板端供应商库满足。禁用 Git 符号链接的 Windows 检出可能生成只有目标路径的普通文件。
- 共有 10 个跟踪文件在 Git 中使用 CRLF，包括固件 HEX、CSV、部分供应商雷达源码、关节 YAML 和 IMU 测试脚本。未批量改写历史资源。14 个 Shell 脚本均通过 `bash -n`；厂商相机的三个 Shell 脚本基线是 `100644`，其中 CMake 使用 `bash` 调用 `gettarget.sh`。在 Linux 或 WSL 上可对普通脚本使用 `bash 脚本名`，或按实际需要恢复执行位。
- 未发现只有大小写不同的跟踪路径。Windows 或 WSL 迁移后可用 `git status --short`、`git ls-files --stage` 和 `git ls-files --eol` 对照同一提交，分别核查工作区差异、执行位与链接、换行。串口、udev 和 Linux 动态库仍要在 Ubuntu 上验证。未在真实 Windows 文件系统复现检出过程，无法判断原迁移时是否遗漏未跟踪文件。

## 课程实验对应情况

| 实验 | 当前证据 | 结论 |
|---|---|---|
| EXP1 颜色识别 | `car1_app.test_hsv_detection` 有现成的 `test_hsv_detection` 入口，执行红色 HSV 阈值、形态学处理及轮廓标注，只输出调试图和掩膜。仿真 `object_detector.py` 也有 HSV 检测。 | 已有可复用实现。缺少标明 EXP1 的课程原始材料，尚未按课程标准验收。 |
| EXP2 多边形描绘 | 现有 HSV 调试会画检测轮廓，AprilTag 调试会描画已知标记边界。未找到明确的 EXP2 入口或通用多边形描绘实现。 | 未发现课程对应实现。 |
| EXP3 二维码检测 | 有 AprilTag 位姿估计。检索未找到二维码检测或解码入口、`QRCodeDetector`、`detectAndDecode` 或 `pyzbar`。 | 未发现课程对应实现。 |

本阶段没有新增视觉实验。EXP2 和 EXP3 的输入、输出和验收标准应在取得课程资料后确定。

## 验证与后续顺序

- **已通过**：Git 对象完整性和 `git diff --check`；177 个 Python 文件的 AST 解析、39 个 XML 类文件和 35 个 YAML 文件的解析、14 个 Shell 脚本的语法检查。静态核对了 10 个相机启动文件的配置定位、地图图像、RViz 与行为树资源、FK 安装声明及 Shell LF 属性。用源码 Python 路径验证了更新后的 IK 导入。
- **已运行且发现失败**：现有 `test_fk_ik.py` 离线脚本完成并返回 0，但实际报告往返测试 1 项通过、3 项失败，失败误差分别为 18.40、22.95、21.73 mm，容差是 1.5 mm。近最大伸展距离用例还报告了与其预期不一致的可行解。本次未改求解逻辑。
- **Humble 容器已通过**：使用 Ubuntu 22.04 的 `ros:humble-ros-base-jammy`。依次验证 `colcon list` 发现 23 个包、`colcon build --symlink-install --packages-up-to car1_kinematics controller car1_bringup` 构建 8 个包，以及 `ros2 launch car1_kinematics kinematics.launch.py` 从安装目录运行 FK 演示并正常退出。安装后也成功导入更新后的 IK 模块。另一次 `colcon build --symlink-install --packages-up-to eye_hand_calibration` 构建 4 个包，`ros2 pkg executables eye_hand_calibration` 列出 7 个已安装入口，未启动采集和标定节点。
- **未运行**：ROS 软件仓库 `packages.ros.org` 的 HTTP 和 HTTPS 请求都收到代理 403，容器未能刷新该仓库的索引。未完成全量依赖安装及构建，未运行 Ignition、相机驱动、Nav2/SLAM 启动与硬件测试。

1. 在 Ubuntu 22.04 和 ROS 2 Humble 环境用 `rosdep` 核对尚未安装的仿真和导航依赖，构建仿真相关包后检查安装资源与 RViz 模型。现有模型与 FK 的构建与入口已在容器验证。
2. 确认 Ignition 版本和 ROS 桥接/控制器的可安装组合，依次验证仿真世界、机器人生成、`/clock`、RGB-D/相机内参、机械臂控制器，以及仿真底盘、扫描、里程计和 TF。完成仿真数据链后再联调建图和导航。
3. 取得 EXP1–EXP3 课程原始资料后，先用图像或仿真相机验收已有 EXP1 代码，再确认其余实验的交付范围。
4. 真机迁移前先在断开运动使能的状态核对设备访问、话题和 TF，再在隔离台架验证关节反馈、IK、夹爪 ID 和动作时序。将现有运动入口的显式使能与急停纳入真机验收。
