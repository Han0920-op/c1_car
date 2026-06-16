#!/usr/bin/env python3
# encoding: utf-8
"""
Visual grasp node for static tabletop grasping.

Uses eye-in-hand camera (mounted on arm_link4) with look-then-move strategy:
1. Move arm to observation pose (elevated, looking down)
2. Detect object via HSV color segmentation
3. Compute 3D position in base_link via depth + TF
4. Execute pick via arm_controller
"""
import enum
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped, PointStamped
from std_srvs.srv import Trigger
from cv_bridge import CvBridge
import cv2
import numpy as np
import tf2_ros
from tf2_geometry_msgs import do_transform_point


class State(enum.Enum):
    """State machine for visual grasp."""
    INIT = 0
    MOVE_TO_OBSERVE = 1
    WAIT_STABLE = 2
    DETECT = 3
    COMPUTE_TARGET = 4
    PICK = 5
    DONE = 6
    FAILED = 7


class VisualGraspNode(Node):
    """ROS2 node for visual-guided static grasping."""

    def __init__(self):
        super().__init__('visual_grasp_node')

        # Declare parameters
        # observe_pose pitch convention (matches arm_controller/ik_analytical):
        #   0=up, pi/2=horizontal, pi=down. Observation should look down at table.
        self.declare_parameter('observe_pose', [0.20, 0.0, 0.22, 3.14159])
        self.declare_parameter('target_color_hsv_lower', [0, 100, 80])
        self.declare_parameter('target_color_hsv_upper', [10, 255, 255])
        self.declare_parameter('depth_sample_size', 5)
        self.declare_parameter('max_detection_attempts', 5)
        self.declare_parameter('verify_after_pick', False)

        # Get parameters
        observe_pose = self.get_parameter('observe_pose').value
        self.observe_x, self.observe_y, self.observe_z, self.observe_pitch = observe_pose
        hsv_lower = self.get_parameter('target_color_hsv_lower').value
        hsv_upper = self.get_parameter('target_color_hsv_upper').value
        self.hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        self.hsv_upper = np.array(hsv_upper, dtype=np.uint8)
        self.depth_sample_size = self.get_parameter('depth_sample_size').value
        self.max_attempts = self.get_parameter('max_detection_attempts').value
        self.verify_after_pick = self.get_parameter('verify_after_pick').value

        # CV Bridge
        self.bridge = CvBridge()

        # TF
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # State machine
        self.state = State.INIT
        self.state_start_time = self.get_clock().now()
        self.detection_attempts = 0

        # Camera data
        self.rgb_image = None
        self.depth_image = None
        self.camera_info = None
        self.fx = None
        self.fy = None
        self.cx = None
        self.cy = None

        # Detection result
        self.detected_point_base = None

        # Pick service future (async)
        self._pick_future = None

        # Subscribers
        # NOTE: subscribe to the ascamera driver's NATIVE topic names. The driver
        # gates streaming on the "rgb0"/"depth0" substring in the topic name, so
        # these must NOT be remapped. See depth_camera.launch.py for details.
        self.rgb_sub = self.create_subscription(
            Image, '/ascamera_hp60c/camera_publisher/rgb0/image', self.rgb_callback, 10
        )
        self.depth_sub = self.create_subscription(
            Image, '/ascamera_hp60c/camera_publisher/depth0/image_raw', self.depth_callback, 10
        )
        self.camera_info_sub = self.create_subscription(
            CameraInfo, '/ascamera_hp60c/camera_publisher/depth0/camera_info', self.camera_info_callback, 10
        )

        # Publisher for target pose
        self.target_pose_pub = self.create_publisher(
            PoseStamped, '/arm_controller/target_pose', 10
        )

        # Service client for pick
        self.pick_client = self.create_client(Trigger, '/arm_controller/pick')

        # Timer for state machine (10 Hz)
        self.timer = self.create_timer(0.1, self.state_machine_tick)

        self.get_logger().info('Visual grasp node started.')
        self.get_logger().info(f'Observation pose: [{self.observe_x}, {self.observe_y}, {self.observe_z}, {self.observe_pitch:.3f}]')
        self.get_logger().info(f'HSV range: {hsv_lower} - {hsv_upper}')

    def rgb_callback(self, msg):
        """Cache RGB image."""
        try:
            self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'RGB conversion failed: {e}')

    def depth_callback(self, msg):
        """Cache depth image."""
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        except Exception as e:
            self.get_logger().error(f'Depth conversion failed: {e}')

    def camera_info_callback(self, msg):
        """Extract camera intrinsics."""
        if self.camera_info is None:
            self.camera_info = msg
            self.fx = msg.k[0]
            self.fy = msg.k[4]
            self.cx = msg.k[2]
            self.cy = msg.k[5]
            self.get_logger().info(f'Camera intrinsics: fx={self.fx:.1f}, fy={self.fy:.1f}, cx={self.cx:.1f}, cy={self.cy:.1f}')

    def state_machine_tick(self):
        """Main state machine loop."""
        if self.state == State.INIT:
            self._handle_init()
        elif self.state == State.MOVE_TO_OBSERVE:
            self._handle_move_to_observe()
        elif self.state == State.WAIT_STABLE:
            self._handle_wait_stable()
        elif self.state == State.DETECT:
            self._handle_detect()
        elif self.state == State.COMPUTE_TARGET:
            self._handle_compute_target()
        elif self.state == State.PICK:
            self._handle_pick()
        elif self.state == State.DONE:
            self._handle_done()
        elif self.state == State.FAILED:
            self._handle_failed()

    def _change_state(self, new_state):
        """Transition to new state."""
        self.get_logger().info(f'State: {self.state.name} -> {new_state.name}')
        self.state = new_state
        self.state_start_time = self.get_clock().now()

    def _handle_init(self):
        """Initial state: wait for camera ready."""
        if self.camera_info is not None:
            self.get_logger().info('Camera ready, moving to observation pose...')
            self._change_state(State.MOVE_TO_OBSERVE)

    def _handle_move_to_observe(self):
        """Move arm to observation pose."""
        # Publish observation pose
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = 'base_link'
        pose_msg.pose.position.x = self.observe_x
        pose_msg.pose.position.y = self.observe_y
        pose_msg.pose.position.z = self.observe_z

        # Convert pitch to quaternion (rotation around Y axis)
        # pitch > 0 means looking down
        import math
        qw = math.cos(self.observe_pitch / 2)
        qx = 0.0
        qy = math.sin(self.observe_pitch / 2)
        qz = 0.0
        pose_msg.pose.orientation.w = qw
        pose_msg.pose.orientation.x = qx
        pose_msg.pose.orientation.y = qy
        pose_msg.pose.orientation.z = qz

        self.target_pose_pub.publish(pose_msg)
        self.get_logger().info(f'Published observation pose: x={self.observe_x}, y={self.observe_y}, z={self.observe_z}, pitch={math.degrees(self.observe_pitch):.1f}°')

        self._change_state(State.WAIT_STABLE)

    def _handle_wait_stable(self):
        """Wait for arm and TF to stabilize."""
        elapsed = (self.get_clock().now() - self.state_start_time).nanoseconds / 1e9
        if elapsed > 3.0:  # Wait 3 seconds
            self.get_logger().info('Arm stabilized, starting detection...')
            self.detection_attempts = 0
            self._change_state(State.DETECT)

    def _handle_detect(self):
        """Detect object via HSV and depth."""
        if self.rgb_image is None or self.depth_image is None:
            self.get_logger().warn('Waiting for camera images...')
            return

        result = self._detect_and_localize()
        if result is not None:
            self.detected_point_base = result
            self.get_logger().info(f'Object detected at base_link: [{result[0]:.3f}, {result[1]:.3f}, {result[2]:.3f}]')
            self._change_state(State.COMPUTE_TARGET)
        else:
            self.detection_attempts += 1
            if self.detection_attempts >= self.max_attempts:
                self.get_logger().error(f'Detection failed after {self.max_attempts} attempts')
                self._change_state(State.FAILED)
            else:
                self.get_logger().warn(f'Detection attempt {self.detection_attempts}/{self.max_attempts} failed, retrying...')

    def _detect_and_localize(self):
        """
        Detect object and compute 3D position in base_link.
        Returns (x, y, z) in base_link or None if detection fails.
        """
        # Skip black frames (camera's first frame after stream start is all-black,
        # and auto-exposure may need a frame to ramp up).
        if self.rgb_image.mean() < 5.0:
            self.get_logger().warn('RGB frame too dark (likely first frame), skipping')
            return None

        # HSV detection
        hsv = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Use largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < 100:  # Min area threshold
            return None

        # Get center pixel
        (u, v), radius = cv2.minEnclosingCircle(largest)
        u_int, v_int = int(u), int(v)

        # Sample depth across the WHOLE detected contour (not just a 5x5 at center).
        # The center pixel may fall in a depth hole; using the contour mask gives a
        # robust median over all valid depth pixels belonging to the object.
        h, w = self.depth_image.shape[:2]
        contour_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(contour_mask, [largest], -1, 255, thickness=cv2.FILLED)
        object_depths = self.depth_image[(contour_mask > 0) & (self.depth_image > 0)]

        if len(object_depths) == 0:
            self.get_logger().warn(
                f'No valid depth in object region (center pixel=({u_int},{v_int}), '
                f'area={area:.0f}). Object likely outside depth FOV (too low/close in image).')
            return None

        z_cam = float(np.median(object_depths))

        # Convert mm to meters if needed (depth published in mm as uint16)
        if z_cam > 100:
            z_cam = z_cam / 1000.0

        # Back-project to camera frame
        x_cam = (u - self.cx) * z_cam / self.fx
        y_cam = (v - self.cy) * z_cam / self.fy

        # Transform to base_link via TF
        try:
            pt_stamped = PointStamped()
            pt_stamped.header.frame_id = 'camera_depth_optical_frame'
            pt_stamped.header.stamp = self.get_clock().now().to_msg()
            pt_stamped.point.x = x_cam
            pt_stamped.point.y = y_cam
            pt_stamped.point.z = z_cam

            transform = self.tf_buffer.lookup_transform(
                'base_link', 'camera_depth_optical_frame',
                rclpy.time.Time(), timeout=Duration(seconds=1.0)
            )
            pt_base = do_transform_point(pt_stamped, transform)

            return (pt_base.point.x, pt_base.point.y, pt_base.point.z)

        except Exception as e:
            self.get_logger().error(f'TF transform failed: {e}')
            return None

    def _handle_compute_target(self):
        """Compute target pose and publish."""
        if self.detected_point_base is None:
            self._change_state(State.FAILED)
            return

        x, y, z = self.detected_point_base

        # Publish target pose (object top center, pitch=-90° pointing down)
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = 'base_link'
        pose_msg.pose.position.x = x
        pose_msg.pose.position.y = y
        pose_msg.pose.position.z = z

        # Quaternion for pitch=180° (gripper pointing straight down)
        # Convention matches arm_controller: 0=up, 90=horizontal, 180=down
        import math
        pitch = math.pi
        qw = math.cos(pitch / 2)
        qx = 0.0
        qy = math.sin(pitch / 2)
        qz = 0.0
        pose_msg.pose.orientation.w = qw
        pose_msg.pose.orientation.x = qx
        pose_msg.pose.orientation.y = qy
        pose_msg.pose.orientation.z = qz

        self.target_pose_pub.publish(pose_msg)
        self.get_logger().info(f'Published target pose for pick: [{x:.3f}, {y:.3f}, {z:.3f}]')

        self._change_state(State.PICK)

    def _handle_pick(self):
        """Call pick service (async, non-blocking - never spin inside a timer callback)."""
        # Already waiting on a previous call?
        if self._pick_future is not None:
            if self._pick_future.done():
                try:
                    response = self._pick_future.result()
                    if response and response.success:
                        self.get_logger().info('Pick completed successfully')
                        self._change_state(State.DONE)
                    else:
                        msg = response.message if response else 'no response'
                        self.get_logger().error(f'Pick failed: {msg}')
                        self._change_state(State.FAILED)
                except Exception as e:
                    self.get_logger().error(f'Pick service error: {e}')
                    self._change_state(State.FAILED)
                self._pick_future = None
            return

        # Not started yet: send the request once
        if not self.pick_client.service_is_ready():
            self.get_logger().warn('Waiting for /arm_controller/pick service...')
            return

        self.get_logger().info('Calling /arm_controller/pick...')
        self._pick_future = self.pick_client.call_async(Trigger.Request())

    def _handle_done(self):
        """Success state."""
        self.get_logger().info('Visual grasp completed successfully!')
        # Stop the node
        raise SystemExit(0)

    def _handle_failed(self):
        """Failure state."""
        self.get_logger().error('Visual grasp failed')
        # Stop the node
        raise SystemExit(1)


def main(args=None):
    rclpy.init(args=args)
    node = VisualGraspNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
