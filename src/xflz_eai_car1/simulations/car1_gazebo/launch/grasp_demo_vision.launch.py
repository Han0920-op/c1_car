import os
import subprocess
from shlex import quote
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, RegisterEventHandler,
    IncludeLaunchDescription, OpaqueFunction
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup_simulation(context, *args, **kwargs):
    """启动 Gazebo 仿真 + 机器人 + 控制器 + 物体 + 深度相机 + 视觉抓取"""
    car1_gazebo_path = get_package_share_directory('car1_gazebo')
    car1_description_path = get_package_share_directory('car1_description')

    use_sim_time = LaunchConfiguration('use_sim_time').perform(context)
    camera_only = LaunchConfiguration('camera_only').perform(context)
    fortress = LaunchConfiguration('fortress').perform(context).lower() == 'true'
    server_only = LaunchConfiguration('server_only').perform(context).lower() == 'true'
    optical_frame = 'camera_sim_optical_frame'
    gz_msgs = 'ignition.msgs' if fortress else 'gz.msgs'

    # 处理 URDF
    xacro_file = os.path.join(car1_gazebo_path, 'urdf', 'car1.gazebo.xacro')
    urdf_content = subprocess.check_output(['xacro', xacro_file, f'camera_only:={camera_only}']).decode('utf-8')

    meshes_path = os.path.join(car1_description_path, 'meshes')
    urdf_content = urdf_content.replace(
        'package://car1_description/meshes/',
        f'file://{meshes_path}/'
    )

    # 启动 Gazebo（使用包含 Sensors 插件的自定义 world）
    world_file = os.path.join(car1_gazebo_path, 'worlds', 'camera_demo.sdf')
    gz_args = f'-r {"-s " if server_only else ""}{quote(world_file)}'
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'),
                         'launch', 'gz_sim.launch.py')
        ]),
        launch_arguments={'gz_args': gz_args}.items()
    )

    # Gazebo-ROS 时钟桥接
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[f'/clock@rosgraph_msgs/msg/Clock[{gz_msgs}.Clock'],
        output='screen'
    )

    # 深度相机话题桥接 (Gazebo Transport → ROS2)
    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            f'/camera/image@sensor_msgs/msg/Image[{gz_msgs}.Image',
            f'/camera/depth_image@sensor_msgs/msg/Image[{gz_msgs}.Image',
            f'/camera/points@sensor_msgs/msg/PointCloud2[{gz_msgs}.PointCloudPacked',
            f'/camera/camera_info@sensor_msgs/msg/CameraInfo[{gz_msgs}.CameraInfo',
        ],
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time == 'true',
            'override_frame_id': optical_frame,
        }]
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': urdf_content,
            'use_sim_time': use_sim_time == 'true'
        }]
    )

    # 生成机器人
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-world', 'camera_demo', '-name', 'car1',
            '-allow_renaming', 'true',
            '-x', '0', '-y', '0', '-z', '0.1'
        ],
        parameters=[{'use_sim_time': True}]
    )

    if camera_only.lower() == 'true':
        # 固定模型用默认零位关节状态发布 TF，抓取模式使用控制器反馈。
        joint_state_publisher = Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time == 'true'}],
        )

        # 保留红球检查，课程实验复用同一固定相机。
        target_model = LaunchConfiguration('camera_target').perform(context)
        spawn_target = Node(
            package='ros_gz_sim',
            executable='create',
            output='screen',
            arguments=[
                '-world', 'camera_demo',
                '-file', os.path.join(car1_gazebo_path, 'models', target_model, 'model.sdf'),
                '-name', target_model, '-x', '0.28', '-y', '0', '-z', '0.035',
            ],
        )
        return [gazebo, clock_bridge, camera_bridge, robot_state_publisher,
                joint_state_publisher, spawn_robot, spawn_target]

    # 保留原有演示使用的动态红方块。
    cube_sdf_path = os.path.join(car1_gazebo_path, 'models', 'cube', 'model.sdf')
    cube_x = LaunchConfiguration('cube_x').perform(context)
    cube_y = LaunchConfiguration('cube_y').perform(context)
    spawn_cube = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-file', cube_sdf_path,
            '-world', 'camera_demo', '-name', 'red_cube',
            '-x', cube_x, '-y', cube_y, '-z', '0.02'
        ],
        parameters=[{'use_sim_time': True}]
    )

    # 控制器
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['gripper_controller', '--controller-manager', '/controller_manager'],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # 物体检测节点
    object_detector = Node(
        package='car1_gazebo',
        executable='object_detector.py',
        name='object_detector',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time == 'true', 'optical_frame': optical_frame}]
    )

    # 视觉抓取节点
    grasp_demo_vision = Node(
        package='car1_gazebo',
        executable='grasp_demo_vision.py',
        name='grasp_demo_vision',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time == 'true'}]
    )

    return [
        gazebo,
        clock_bridge,
        robot_state_publisher,
        spawn_robot,
        camera_bridge,
        spawn_cube,

        # 等待机器人生成后启动控制器
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_robot,
                on_exit=[joint_state_broadcaster_spawner]
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_state_broadcaster_spawner,
                on_exit=[arm_controller_spawner]
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=arm_controller_spawner,
                on_exit=[gripper_controller_spawner]
            )
        ),
        # 等待控制器就绪后启动视觉节点
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=gripper_controller_spawner,
                on_exit=[object_detector, grasp_demo_vision]
            )
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('camera_only', default_value='false', choices=['true', 'false'],
                              description='Use a fixed robot and red sphere for camera checks'),
        DeclareLaunchArgument('camera_target', default_value='red_ball',
                              choices=['red_ball', 'exp01_color_targets', 'exp02_polygon_targets',
                                       'exp03_qrcode_target'],
                              description='Target model used only in camera-only mode'),
        DeclareLaunchArgument('fortress', default_value='false', choices=['true', 'false'],
                              description='Use Ignition Fortress bridge message names'),
        DeclareLaunchArgument('server_only', default_value='false', choices=['true', 'false'],
                              description='Run Gazebo without its GUI; sensor rendering stays enabled'),
        DeclareLaunchArgument(
            'cube_x', default_value='0.28',
            description='立方体 X 坐标 (base_link 坐标系)'
        ),
        DeclareLaunchArgument(
            'cube_y', default_value='0.0',
            description='立方体 Y 坐标 (base_link 坐标系)'
        ),
        OpaqueFunction(function=setup_simulation)
    ])
