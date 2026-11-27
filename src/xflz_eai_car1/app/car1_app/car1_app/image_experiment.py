"""视觉实验共用的 ROS 图像输入、静态样例与结果发布。"""
import json
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory

import cv2
from cv_bridge import CvBridge, CvBridgeError
import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class ImageExperiment(Node):
    def __init__(self, name):
        super().__init__(name)
        startup_setting = ParameterDescriptor(read_only=True)
        config = Path(get_package_share_directory('car1_app')) / 'config/camera_topics.yaml'
        topics = yaml.safe_load(config.read_text(encoding='utf-8'))
        source = self.declare_parameter('camera_source', 'gazebo', startup_setting).value
        if source not in topics:
            raise ValueError(f'Unknown camera_source: {source}')
        camera_topic = self.declare_parameter('camera_topic', topics[source], startup_setting).value
        image_path = self.declare_parameter('image_path', '', startup_setting).value
        self.bridge = CvBridge()
        self.result_pub = self.create_publisher(Image, '~/result', 10)
        self.mask_pub = self.create_publisher(Image, '~/mask', 10)
        self.detections_pub = self.create_publisher(String, '~/detections', 10)
        if image_path:
            bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError(f'Cannot read test image: {image_path}')
            # 以低频重复同一输入，便于晚启动的 RQT 立即看到结果。
            self.test_image = self.bridge.cv2_to_imgmsg(bgr, encoding='bgr8')
            self.timer = self.create_timer(0.5, self.publish_test_result)
            self.get_logger().info(f'Test image: {image_path}')
        else:
            self.subscription = self.create_subscription(
                Image, camera_topic, self.process_image, qos_profile_sensor_data)
            self.get_logger().info(f'Camera input: {self.subscription.topic_name} (sensor QoS → bgr8)')

    def publish_test_result(self):
        self.test_image.header.stamp = self.get_clock().now().to_msg()
        self.process_image(self.test_image)

    def process_image(self, msg):
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            annotated, mask, detections = self.detector.detect(bgr)
            result_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            mask_msg = self.bridge.cv2_to_imgmsg(mask, encoding='mono8')
        except (CvBridgeError, cv2.error) as exc:
            self.get_logger().error(f'Image processing failed ({msg.encoding}, {msg.width}x{msg.height}): {exc}', throttle_duration_sec=2.0)
            return

        # 保留源时间戳和 frame_id，便于按帧比对原图、标注和掩膜。
        result_msg.header = msg.header
        mask_msg.header = msg.header
        self.result_pub.publish(result_msg)
        self.mask_pub.publish(mask_msg)
        self.detections_pub.publish(String(data=json.dumps({
            'stamp': {'sec': msg.header.stamp.sec, 'nanosec': msg.header.stamp.nanosec},
            'frame_id': msg.header.frame_id,
            'detections': detections,
        })))
        return annotated, detections


def run_experiment(node_type, args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = node_type()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        # Humble 在关闭 ROS 上下文时可能同时从订阅队列取消息。
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
