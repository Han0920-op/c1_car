import os
from ament_index_python.packages import get_package_share_directory

from launch_ros.actions import Node
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    base_driver_pkg = get_package_share_directory('car1_base_driver')
    chassis_pkg = get_package_share_directory('controller')
    description_pkg = get_package_share_directory('car1_description')

    # URDF (single source of static TF: base_footprint -> base_link -> imu_link / laser_link / arm joints).
    # EKF needs base_link -> imu_link to transform IMU angular velocity into base frame,
    # so robot_state_publisher MUST run as part of bringup (not only in slam.launch).
    urdf_file = os.path.join(description_pkg, 'urdf', 'car1.urdf')
    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    bringup_description = LaunchDescription([
        # 1. Board-level driver (serial communication with STM32)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(base_driver_pkg, 'launch/base_driver.launch.py')),
        ),
        # 2. Robot state publisher — URDF static TF (base_link -> imu_link etc.).
        #    Started before/with the chassis controller so EKF can look up the
        #    base_link -> imu_link transform. robot_localization retries TF lookups,
        #    so a small startup-order gap is tolerated.
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_desc}],
            output='screen',
        ),
        # 3. Joint state publisher — fills wheel joints (arm joints come from servo_controller).
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            parameters=[
                {'robot_description': robot_desc},
                {'source_list': ['joint_states']},
                {'rate': 20},
            ],
            output='screen',
        ),
        # 4. Chassis controller (IMU filter + odom + EKF + servo controller + init pose)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(chassis_pkg, 'launch/chassis_controller.launch.py')),
        ),
    ])

    return bringup_description
