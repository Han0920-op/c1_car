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
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    bringup_pkg = get_package_share_directory('car1_bringup')
    peripherals_pkg = get_package_share_directory('car1_peripherals')
    nav_pkg = get_package_share_directory('car1_navigation')

    # 默认读取已安装的地图，也支持从指定目录加载新保存的地图。
    maps_dir = LaunchConfiguration('map_dir').perform(context)
    map_name = LaunchConfiguration('map').perform(context)
    map_file = os.path.join(os.path.expanduser(maps_dir), map_name + '.yaml')
    rviz_config = os.path.join(nav_pkg, 'rviz', 'navigation.rviz')

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
        description='Map name without the YAML extension')

    map_dir_arg = DeclareLaunchArgument(
        'map_dir',
        default_value=PathJoinSubstitution([FindPackageShare('car1_slam'), 'maps']),
        description='Directory containing the map YAML and image')

    use_rviz_arg = DeclareLaunchArgument(
        'use_rviz', default_value='true',
        description='Whether to start RViz')

    return LaunchDescription([
        map_arg,
        map_dir_arg,
        use_rviz_arg,
        OpaqueFunction(function=launch_setup)
    ])
