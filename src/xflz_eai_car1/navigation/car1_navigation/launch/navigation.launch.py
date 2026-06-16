#!/usr/bin/env python3
"""Main navigation launch: bringup + lidar + localization + navigation."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    bringup_pkg = get_package_share_directory('car1_bringup')
    peripherals_pkg = get_package_share_directory('car1_peripherals')
    nav_pkg = get_package_share_directory('car1_navigation')
    slam_pkg = get_package_share_directory('car1_slam')

    map_name = LaunchConfiguration('map', default='map_01')
    map_arg = DeclareLaunchArgument(
        'map', default_value='map_01',
        description='Map name (without extension) in car1_slam/maps/')

    map_file = [slam_pkg, '/maps/', map_name, '.yaml']

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

    return LaunchDescription([
        map_arg,
        bringup_launch,
        lidar_launch,
        localization_launch,
        navigation_launch,
    ])
