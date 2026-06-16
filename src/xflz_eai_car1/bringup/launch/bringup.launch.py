import os
from ament_index_python.packages import get_package_share_directory

from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    base_driver_pkg = get_package_share_directory('car1_base_driver')
    chassis_pkg = get_package_share_directory('controller')

    bringup_description = LaunchDescription([
        # 1. Board-level driver (serial communication with STM32)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(base_driver_pkg, 'launch/base_driver.launch.py')),
        ),
        # 2. Chassis controller (IMU filter + odom + EKF + servo controller + init pose)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(chassis_pkg, 'launch/chassis_controller.launch.py')),
        ),
    ])

    return bringup_description
