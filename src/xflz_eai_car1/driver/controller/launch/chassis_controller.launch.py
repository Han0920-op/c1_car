#!/usr/bin/env python3
"""Main chassis controller launch: IMU filter + odom + EKF + servo controller."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    chassis_pkg = get_package_share_directory('controller')
    servo_pkg = get_package_share_directory('car1_servo_controller')

    calibrate_config = os.path.join(chassis_pkg, 'config', 'calibrate_params.yaml')
    ekf_config = os.path.join(chassis_pkg, 'config', 'ekf.yaml')
    init_pose_config = os.path.join(chassis_pkg, 'config', 'init_pose.yaml')

    # IMU Complementary filter (参考 lander_pi，支持零偏估计)
    imu_filter_node = Node(
        package='imu_complementary_filter',
        executable='complementary_filter_node',
        name='imu_filter',
        parameters=[{
            'use_mag': False,
            'publish_tf': False,
            'do_bias_estimation': True,    # 启用零偏在线估计
            'do_adaptive_gain': True,      # 启用自适应增益
            'bias_alpha': 0.1,             # 加快零偏收敛速度（0.01→0.1）
        }],
        remappings=[
            ('imu/data_raw', 'car1_base_driver/imu_raw'),
            ('imu/data', 'imu'),
        ],
        output='screen'
    )

    # Odometry publisher
    odom_publisher_node = Node(
        package='controller',
        executable='odom_publisher',
        name='odom_publisher',
        parameters=[calibrate_config],
        output='screen'
    )

    # EKF node (robot_localization)
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[ekf_config],
        output='screen'
    )

    # Servo controller
    servo_controller_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(servo_pkg, 'launch', 'servo_controller.launch.py')
        )
    )

    # Init pose
    init_pose_node = Node(
        package='controller',
        executable='init_pose',
        name='init_pose',
        parameters=[init_pose_config],
        output='screen'
    )

    return LaunchDescription([
        imu_filter_node,
        odom_publisher_node,
        ekf_node,
        servo_controller_launch,
        init_pose_node,
    ])
