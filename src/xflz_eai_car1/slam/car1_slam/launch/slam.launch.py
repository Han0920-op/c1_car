#!/usr/bin/env python3
"""SLAM launch: bringup + lidar + robot_state_publisher + slam_toolbox.

Single entry point. Layered include of bringup (driver + chassis controller),
then lidar, then a single robot_state_publisher for URDF static TF, and finally
slam_toolbox delayed until odom/TF/scan have stabilized.

Note: joint_state_publisher is intentionally NOT launched here. The real arm
joint states are published by car1_servo_controller (controller_manager_node);
adding a default-zero joint_state_publisher would fight it on /joint_states and
make the arm jitter in RViz.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_pkg = get_package_share_directory('car1_bringup')
    peripherals_pkg = get_package_share_directory('car1_peripherals')
    slam_pkg = get_package_share_directory('car1_slam')
    description_pkg = get_package_share_directory('car1_description')

    slam_config = os.path.join(slam_pkg, 'config', 'slam.yaml')
    urdf_file = os.path.join(description_pkg, 'urdf', 'car1.urdf')
    rviz_config = os.path.join(slam_pkg, 'rviz', 'slam.rviz')

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    use_rviz = LaunchConfiguration('use_rviz', default='true')
    use_rviz_arg = DeclareLaunchArgument('use_rviz', default_value='true')

    # 1. Bringup (driver layer: base_driver + chassis controller + servo controller).
    #    servo_controller publishes the real /joint_states for the arm.
    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, 'launch', 'bringup.launch.py'))
    )

    # 2. Lidar (publishes /scan in frame laser_link)
    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(peripherals_pkg, 'launch', 'lidar.launch.py'))
    )

    # 3. Robot state publisher (the single source of URDF static TF).
    #    bringup does NOT start one, so slam must provide it.
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'robot_description': robot_desc}],
        output='screen'
    )

    # 4. Joint state publisher (fills in missing wheel joints).
    #    servo_controller publishes arm_joint1-5 + r_joint (real servo positions).
    #    But the 4 wheel_*_joint (continuous) are never published by anyone.
    #    This node subscribes to /joint_states (gets arm joints from servo_controller),
    #    republishes them unchanged, and adds default zero positions for wheels.
    #    Result: robot_state_publisher receives complete joint_states for all URDF joints.
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[
            {'robot_description': robot_desc},
            {'source_list': ['joint_states']},  # Subscribe to servo_controller's output
            {'rate': 20},
        ],
        output='screen'
    )

    # 4. slam_toolbox, delayed 10s to let odom / TF / scan stabilize.
    slam_node = TimerAction(
        period=10.0,
        actions=[
            Node(
                package='slam_toolbox',
                executable='sync_slam_toolbox_node',
                name='slam_toolbox',
                parameters=[slam_config],
                output='screen'
            )
        ]
    )

    # 5. RViz2 (optional, toggle with use_rviz:=false)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(use_rviz),
        output='screen'
    )

    return LaunchDescription([
        use_rviz_arg,
        bringup_launch,
        lidar_launch,
        robot_state_publisher_node,
        joint_state_publisher_node,
        slam_node,
        rviz_node,
    ])
