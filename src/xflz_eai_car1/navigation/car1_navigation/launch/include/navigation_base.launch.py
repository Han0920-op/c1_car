#!/usr/bin/env python3
"""Navigation base launch: controller, planner, behavior, bt_navigator, velocity_smoother."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    nav_pkg = get_package_share_directory('car1_navigation')
    nav2_params = os.path.join(nav_pkg, 'config', 'nav2_params.yaml')

    # 行为树与导航包一起安装，从包路径解析 XML。
    bt_dir = os.path.join(nav_pkg, 'config', 'behavior_trees')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='false')

    configured_params = RewrittenYaml(
        source_file=nav2_params,
        param_rewrites={
            'use_sim_time': use_sim_time,
            'default_nav_to_pose_bt_xml': os.path.join(
                bt_dir, 'navigate_to_pose_without_backup.xml'),
            'default_nav_through_poses_bt_xml': os.path.join(
                bt_dir, 'navigate_through_poses_without_backup.xml'),
        },
        convert_types=True
    )

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        parameters=[configured_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
        output='screen'
    )

    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        parameters=[configured_params],
        output='screen'
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        parameters=[configured_params],
        output='screen'
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        parameters=[configured_params],
        output='screen'
    )

    velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        parameters=[configured_params],
        remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'controller/cmd_vel')],
        output='screen'
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        parameters=[configured_params],
        output='screen'
    )

    return LaunchDescription([
        sim_time_arg,
        controller_server,
        planner_server,
        behavior_server,
        bt_navigator,
        velocity_smoother,
        lifecycle_manager,
    ])
