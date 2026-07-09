"""Launch all speech nodes (wake word, ASR, TTS)."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare arguments
    config_dir = PathJoinSubstitution([
        FindPackageShare('car1_speech'), 'config'
    ])

    wake_word_config = PathJoinSubstitution([config_dir, 'wake_word.yaml'])
    asr_config = PathJoinSubstitution([config_dir, 'asr.yaml'])
    tts_config = PathJoinSubstitution([config_dir, 'tts.yaml'])

    # Nodes
    wake_word_node = Node(
        package='car1_speech',
        executable='wake_word_node',
        name='wake_word_node',
        output='screen',
        parameters=[wake_word_config],
    )

    asr_node = Node(
        package='car1_speech',
        executable='asr_node',
        name='asr_node',
        output='screen',
        parameters=[asr_config],
    )

    tts_node = Node(
        package='car1_speech',
        executable='tts_node',
        name='tts_node',
        output='screen',
        parameters=[tts_config],
    )

    return LaunchDescription([
        wake_word_node,
        asr_node,
        tts_node,
    ])
