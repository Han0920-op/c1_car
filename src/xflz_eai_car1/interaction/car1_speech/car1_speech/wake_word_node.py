"""
Wake Word Detection Node

Listens to audio stream and publishes when wake word is detected.
Supports offline wake word engines (e.g., Porcupine, Snowboy).
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


class WakeWordNode(Node):
    def __init__(self):
        super().__init__('wake_word_node')

        # Parameters
        self.declare_parameter('wake_word', 'hello robot')
        self.declare_parameter('sensitivity', 0.5)
        self.declare_parameter('audio_device_index', -1)  # -1 = default

        self.wake_word = self.get_parameter('wake_word').value
        self.sensitivity = self.get_parameter('sensitivity').value
        self.audio_device_index = self.get_parameter('audio_device_index').value

        # Publishers
        self.detected_pub = self.create_publisher(
            Bool, '/interaction/wake_word/detected', 10)
        self.wake_word_pub = self.create_publisher(
            String, '/interaction/wake_word/text', 10)

        self.get_logger().info(f'Wake word node started, listening for: "{self.wake_word}"')
        self.get_logger().warn('TODO: Implement actual wake word detection engine')

        # TODO: Initialize wake word detection engine
        # - Porcupine (https://picovoice.ai/platform/porcupine/)
        # - Snowboy (https://github.com/Kitt-AI/snowboy)
        # - Custom model

        # TODO: Start audio capture thread
        # self._start_audio_capture()

    def _start_audio_capture(self):
        """Start capturing audio and detecting wake word."""
        # TODO: Implement audio capture loop
        # 1. Open audio stream (pyaudio/sounddevice)
        # 2. Process audio chunks
        # 3. Run wake word detection
        # 4. Publish when detected
        pass

    def _on_wake_word_detected(self):
        """Called when wake word is detected."""
        self.get_logger().info(f'Wake word detected: "{self.wake_word}"')

        # Publish detection event
        msg = Bool()
        msg.data = True
        self.detected_pub.publish(msg)

        # Publish wake word text
        text_msg = String()
        text_msg.data = self.wake_word
        self.wake_word_pub.publish(text_msg)


def main(args=None):
    rclpy.init(args=args)
    node = WakeWordNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
