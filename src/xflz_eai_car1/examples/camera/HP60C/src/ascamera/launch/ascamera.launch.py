from os.path import join

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
import launch_ros.actions

def generate_launch_description():
    return LaunchDescription([
        launch_ros.actions.Node(
            namespace= "ascamera",
            package='ascamera',
            executable='ascamera_node',
            respawn=True,
            output='both',
            parameters=[
                {"confiPath": join(get_package_share_directory('ascamera'), 'configurationfiles')}
            ]
        ),
    ])
