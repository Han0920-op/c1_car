#!/usr/bin/env python3
"""启动基于手动参考角度的仿真抓取演示。"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # 共用基础入口的控制器启动顺序，只选择手动参考抓取节点。
    return LaunchDescription([IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('car1_gazebo'), 'launch', 'grasp_demo.launch.py',
        ])),
        launch_arguments={'mode': 'manual'}.items(),
    )])
