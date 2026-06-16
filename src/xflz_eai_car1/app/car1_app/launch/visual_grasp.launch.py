#!/usr/bin/env python3
"""Launch file for visual grasp (static tabletop grasping).

NOTE: This launch starts robot_state_publisher + visual_grasp node.
It does NOT start the depth camera (run it separately:
  ros2 launch car1_peripherals depth_camera.launch.py)
and assumes bringup + arm_controller are already running.
"""
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get URDF for robot_state_publisher
    urdf_file = os.path.join(
        get_package_share_directory('car1_description'),
        'urdf', 'car1.urdf'
    )

    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # robot_state_publisher (publishes TF tree from URDF + joint_states)
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}]
    )

    # Visual grasp node
    visual_grasp_node = Node(
        package='car1_app',
        executable='visual_grasp',
        output='screen',
        parameters=[{
            'observe_pose': [0.20, 0.0, 0.22, 3.14159],  # x, y, z, pitch(rad). pitch=pi=gripper down
            'target_color_hsv_lower': [0, 100, 80],     # Red lower bound
            'target_color_hsv_upper': [10, 255, 255],   # Red upper bound
            'depth_sample_size': 5,
            'max_detection_attempts': 5,
            'verify_after_pick': False
        }]
    )

    return LaunchDescription([
        robot_state_pub,
        visual_grasp_node
    ])
