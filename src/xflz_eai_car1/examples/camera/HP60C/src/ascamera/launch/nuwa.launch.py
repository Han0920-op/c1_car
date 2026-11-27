from os.path import join

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    ascamera_node = Node(
        namespace= "ascamera_nuwa",
        package='ascamera',
        executable='ascamera_node',
        respawn=True,
        output='both',
        parameters=[
            {"usb_bus_no": -1},
            {"usb_path": "null"},
            {"confiPath": join(get_package_share_directory('ascamera'), 'configurationfiles')},
            {"color_pcl": False},
            # {"depth_width": 640},
            # {"depth_height": 400},
            # {"fps": 30},
        ],
        remappings=[]
    )

    return LaunchDescription([ascamera_node])

