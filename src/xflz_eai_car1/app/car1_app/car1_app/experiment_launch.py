"""三个实验共用的 Humble 启动参数和相机配置选择。"""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def experiment_launch(executable):
    config = Path(get_package_share_directory('car1_app')) / 'config'

    def start(context):
        source = LaunchConfiguration('camera_source').perform(context)
        parameters = [str(config / f'{executable}.yaml'), {'camera_source': source}]
        custom_config = LaunchConfiguration('config_file').perform(context)
        if custom_config:
            parameters.append(custom_config)
        # 仅显式传入的参数覆盖 YAML，避免空启动参数覆盖用户的相机或静态图片配置。
        overrides = {}
        for name, kind in [('camera_topic', str), ('image_path', str), ('use_sim_time', bool)]:
            value = LaunchConfiguration(name).perform(context)
            if value:
                overrides[name] = ParameterValue(LaunchConfiguration(name), value_type=kind)
        if overrides:
            parameters.append(overrides)
        return [Node(package='car1_app', executable=executable, name=executable, namespace='', output='screen',
                     parameters=parameters)]

    return LaunchDescription([
        DeclareLaunchArgument('camera_source', default_value='gazebo', choices=['gazebo', 'hp60c']),
        DeclareLaunchArgument('config_file', default_value='', description='Optional experiment YAML overrides'),
        DeclareLaunchArgument('camera_topic', default_value='', description='Override RGB Image topic'),
        DeclareLaunchArgument('image_path', default_value='', description='Optional local test image'),
        DeclareLaunchArgument('use_sim_time', default_value='', choices=['', 'true', 'false']),
        OpaqueFunction(function=start),
    ])
