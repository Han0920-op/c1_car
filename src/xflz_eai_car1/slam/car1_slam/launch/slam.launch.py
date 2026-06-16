#!/usr/bin/env python3
"""SLAM launch: bringup + lidar + robot_state_publisher + slam_toolbox."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
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
    if not os.path.exists(rviz_config):
        rviz_config = '/home/iflytek/ros2_ws/src/xflz_robot_car1/slam/car1_slam/rviz/slam.rviz'

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    # 1. Bringup (driver layer)
    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, 'launch', 'bringup.launch.py'))
    )

    # 2. Lidar
    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(peripherals_pkg, 'launch', 'lidar.launch.py'))
    )

    # 3. Robot state publisher (publishes TF from URDF)
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'robot_description': robot_desc}],
        output='screen'
    )

    # 4. Joint state publisher (publishes default joint states for visualization)
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{'robot_description': robot_desc}],
        output='screen'
    )

    # 5. slam_toolbox (delayed to let sensors stabilize)
    slam_node = TimerAction(
        period=3.0,
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

    # 6. RViz2 (optional, with saved config)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        output='screen'
    )

    return LaunchDescription([
        bringup_launch,
        lidar_launch,
        robot_state_publisher_node,
        joint_state_publisher_node,
        slam_node,
        rviz_node,
    ])
