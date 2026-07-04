#!/usr/bin/env python3
"""Main navigation launch: bringup + lidar + localization + navigation."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    bringup_pkg = get_package_share_directory('car1_bringup')
    peripherals_pkg = get_package_share_directory('car1_peripherals')
    nav_pkg = get_package_search_directory('car1_navigation') if False else get_package_share_directory('car1_navigation')

    # 直接使用源码目录下的地图路径（不依赖 install 目录）
    maps_dir = os.path.expanduser('~/ros2_ws/src/xflz_eai_car1/slam/car1_slam/maps')

    # 在运行时求值 LaunchConfiguration
    map_name = LaunchConfiguration('map').perform(context)
    map_file = os.path.join(maps_dir, map_name + '.yaml')

    # 使用源码目录的 RViz 配置
    rviz_config = os.path.expanduser('~/ros2_ws/src/xflz_eai_car1/navigation/car1_navigation/rviz/navigation.rviz')

    # 1. Bringup
    bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_pkg, 'launch', 'bringup.launch.py'))
    )

    # 2. Lidar
    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(peripherals_pkg, 'launch', 'lidar.launch.py'))
    )

    # 3. Localization
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav_pkg, 'launch', 'include', 'localization.launch.py')),
        launch_arguments={'map': map_file}.items()
    )

    # 4. Navigation
    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav_pkg, 'launch', 'include', 'navigation_base.launch.py'))
    )

    # 5. RViz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(LaunchConfiguration('use_rviz')),
        output='screen'
    )

    return [
        bringup_launch,
        lidar_launch,
        localization_launch,
        navigation_launch,
        rviz_node,
    ]


def generate_launch_description():
    map_arg = DeclareLaunchArgument(
        'map', default_value='slam_map',
        description='Map name (without extension) under car1_slam/maps/')

    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz')

    return LaunchDescription([
        map_arg,
        use_rviz_arg,
        OpaqueFunction(function=launch_setup)
    ])
