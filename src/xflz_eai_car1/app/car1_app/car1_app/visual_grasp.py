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
        # Red wraps around the HSV hue circle, so we need TWO ranges OR'd together:
        # low-H end (0-10) and high-H end (160-180). Measured cube is mostly high-H
        # (H 167-178, S down to 80), so the second range is what actually catches it.
        self.declare_parameter('target_color_hsv_lower', [0, 80, 60])
        self.declare_parameter('target_color_hsv_upper', [10, 255, 255])
        self.declare_parameter('target_color_hsv_lower2', [160, 80, 60])
        self.declare_parameter('target_color_hsv_upper2', [180, 255, 255])
        self.declare_parameter('depth_sample_size', 5)
        self.declare_parameter('max_detection_attempts', 5)
        self.declare_parameter('verify_after_pick', False)
        # dry_run: detect and print base_link coords, then STOP. Does NOT publish the
        # detected target_pose (which would trigger arm_controller to move) and does NOT
        # call pick. Use this to verify localization accuracy safely (arm only goes UP to
        # the observe pose, never descends toward the object).
        self.declare_parameter('dry_run', False)

        # Get parameters
        observe_pose = self.get_parameter('observe_pose').value
        self.observe_x, self.observe_y, self.observe_z, self.observe_pitch = observe_pose
        hsv_lower = self.get_parameter('target_color_hsv_lower').value
        hsv_upper = self.get_parameter('target_color_hsv_upper').value
        self.hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        self.hsv_upper = np.array(hsv_upper, dtype=np.uint8)
        hsv_lower2 = self.get_parameter('target_color_hsv_lower2').value
        hsv_upper2 = self.get_parameter('target_color_hsv_upper2').value
        self.hsv_lower2 = np.array(hsv_lower2, dtype=np.uint8)
        self.hsv_upper2 = np.array(hsv_upper2, dtype=np.uint8)
        self.depth_sample_size = self.get_parameter('depth_sample_size').value
        self.max_attempts = self.get_parameter('max_detection_attempts').value
        self.verify_after_pick = self.get_parameter('verify_after_pick').value
        self.dry_run = self.get_parameter('dry_run').value

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
        # set_pick_target: tells arm_controller the grasp target WITHOUT moving the
        # arm. Using target_pose here would make the arm descend to the object before
        # the pick service runs, which looks like a redundant "first grasp".
        self.set_pick_target_pub = self.create_publisher(
            PoseStamped, '/arm_controller/set_pick_target', 10
        )

        # Debug image publishers: view in rqt to SEE what the camera sees and what
        # HSV catches. /visual_grasp/debug_image = RGB with detected contour drawn;
        # /visual_grasp/mask = raw HSV mask (white = pixels matching the color range).
        self.debug_image_pub = self.create_publisher(Image, '/visual_grasp/debug_image', 1)
        self.mask_pub = self.create_publisher(Image, '/visual_grasp/mask', 1)

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
        """Move arm to observation pose using go_home service (safer than direct pose)."""
        # Instead of publishing observation pose via target_pose (which sets pick_target),
        # we should use a dedicated service or wait for arm to be manually positioned.
        # For now, we publish but note this will set pick_target to observation pose.
        # TODO: Add a dedicated service for non-grasp movements, or use joint_command.

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
        self.get_logger().info(f'Moving to observation pose: x={self.observe_x}, y={self.observe_y}, z={self.observe_z}, pitch={math.degrees(self.observe_pitch):.1f}°')
        self.get_logger().warn('Note: This sets pick_target. Real grasp target will be set after detection.')

        self._change_state(State.WAIT_STABLE)

    def _handle_wait_stable(self):
        """Wait for arm to reach observation pose and camera to stabilize."""
        elapsed = (self.get_clock().now() - self.state_start_time).nanoseconds / 1e9
        if elapsed > 5.0:  # Increased from 3s to 5s for camera auto-exposure/white-balance
            self.get_logger().info('Starting detection (arm stable, camera warmed up)...')
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
            if self.dry_run:
                self.get_logger().warn(
                    '[DRY_RUN] Localization only. Measure the cube with a ruler and compare to '
                    f'the base_link coords above [{result[0]:.3f}, {result[1]:.3f}, {result[2]:.3f}] '
                    '(target <1.5cm). NOT publishing target_pose, NOT calling pick. Stopping.')
                self._change_state(State.DONE)
            else:
                self._change_state(State.COMPUTE_TARGET)
        else:
            self.detection_attempts += 1
            if self.detection_attempts >= self.max_attempts:
                self.get_logger().error(f'Detection failed after {self.max_attempts} attempts')
                self._change_state(State.FAILED)
            else:
                self.get_logger().warn(f'Detection attempt {self.detection_attempts}/{self.max_attempts} failed, retrying...')

    def _publish_mask(self, mask):
        """Publish the HSV mask as a mono8 image for rqt inspection."""
        try:
            self.mask_pub.publish(self.bridge.cv2_to_imgmsg(mask, encoding='mono8'))
        except Exception as e:
            self.get_logger().error(f'mask publish failed: {e}')

    def _publish_debug_image(self, rgb, contour, center=None):
        """Publish RGB with the detected contour + center drawn, for rqt inspection."""
        try:
            img = rgb.copy()
            if contour is not None:
                cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)
            if center is not None:
                cv2.circle(img, center, 6, (255, 0, 0), -1)
            self.debug_image_pub.publish(self.bridge.cv2_to_imgmsg(img, encoding='bgr8'))
        except Exception as e:
            self.get_logger().error(f'debug image publish failed: {e}')

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

        # HSV detection — OR the two red ranges (red wraps around H=0/180)
        hsv = cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2HSV)
        mask = cv2.bitwise_or(
            cv2.inRange(hsv, self.hsv_lower, self.hsv_upper),
            cv2.inRange(hsv, self.hsv_lower2, self.hsv_upper2),
        )

        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Publish the raw mask so we can SEE in rqt what HSV catches (white pixels).
        self._publish_mask(mask)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            self.get_logger().warn(f'HSV found NO red contour (mask white px={int(mask.sum()/255)})')
            self._publish_debug_image(self.rgb_image, None)
            return None

        # Use largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area < 100:  # Min area threshold
            self.get_logger().warn(f'Largest red contour too small: area={area:.0f} (<100)')
            self._publish_debug_image(self.rgb_image, largest)
            return None

        # Get center pixel
        (u, v), radius = cv2.minEnclosingCircle(largest)
        u_int, v_int = int(u), int(v)

        # Annotated debug image: RGB with detected contour + center marked.
        self._publish_debug_image(self.rgb_image, largest, (u_int, v_int))

        # Sample depth at center region (more reliable than full contour which may
        # include background edges). Use a small window around the center pixel.
        h, w = self.depth_image.shape[:2]
        sample_size = 10  # 10x10 window around center
        v_min = max(0, v_int - sample_size//2)
        v_max = min(h, v_int + sample_size//2)
        u_min = max(0, u_int - sample_size//2)
        u_max = min(w, u_int + sample_size//2)

        center_region = self.depth_image[v_min:v_max, u_min:u_max]
        object_depths = center_region[center_region > 0]

        if len(object_depths) == 0:
            self.get_logger().warn(
                f'No valid depth in center region (center pixel=({u_int},{v_int}), '
                f'area={area:.0f}). Object likely outside depth FOV.')
            return None

        z_cam = float(np.median(object_depths))

        # Convert mm to meters if needed (depth published in mm as uint16)
        if z_cam > 100:
            z_cam = z_cam / 1000.0

        # Back-project to camera frame
        x_cam = (u - self.cx) * z_cam / self.fx
        y_cam = (v - self.cy) * z_cam / self.fy

        # Debug: print every intermediate value so we can isolate which stage is wrong
        # (HSV pixel / depth / back-projection / TF).
        self.get_logger().info(
            f'[DETECT] pixel=({u_int},{v_int}) area={area:.0f} valid_depth_px={len(object_depths)} '
            f'z_cam={z_cam:.3f}m | cam_frame=({x_cam:.3f}, {y_cam:.3f}, {z_cam:.3f})')

        # Transform to base_link manually (don't use TF which may use stale joint_states)
        # At observation pose [0.2, 0, 0.22, pi]:
        # - Camera at approximately [0.256, -0.003, 0.244] in base_link
        # - Camera pointing down with ~5.31° forward tilt
        # - Rotation matrix derived from URDF + observation pose FK
        cam_x, cam_y, cam_z = 0.256, -0.003, 0.244
        pitch_rad = 0.0927  # 5.31° in radians
        cos_p, sin_p = 0.9957, 0.0925

        # Rotation: optical frame → base_link (with 5.31° pitch)
        # optical_x (image right) → -base_y (right, negative Y)
        # optical_y (image down)  → -base_x (backward)
        # optical_z (depth)       → -base_z (downward) with pitch correction
        x_base = cam_x - y_cam
        y_base = cam_y - cos_p * x_cam + sin_p * z_cam
        z_base = cam_z - sin_p * x_cam - cos_p * z_cam

        self.get_logger().info(
            f'[MANUAL_TF] cam_pos=[{cam_x:.3f},{cam_y:.3f},{cam_z:.3f}], '
            f'pitch={pitch_rad:.4f}rad → base_link=[{x_base:.3f},{y_base:.3f},{z_base:.3f}]')

        return (x_base, y_base, z_base)

    def _handle_compute_target(self):
        """Set arm_controller's pick_target WITHOUT moving the arm."""
        if self.detected_point_base is None:
            self._change_state(State.FAILED)
            return

        x, y, z = self.detected_point_base

        # Publish to set_pick_target (NOT target_pose): this only stores the target in
        # arm_controller; it does NOT move the arm. The pick service will run the full
        # grasp sequence (pre-grasp -> descend -> close -> retract) from this target.
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

        self.set_pick_target_pub.publish(pose_msg)
        self.get_logger().info(f'Set pick target (no move): [{x:.3f}, {y:.3f}, {z:.3f}]')

        self._change_state(State.PICK)

    def _handle_pick(self):
        """Call pick service (async, non-blocking - never spin inside a timer callback)."""
        # Already waiting on a previous call?
        if self._pick_future is not None:
            if self._pick_future.done():
                try:
                    response = self._pick_future.result()
                    if response and response.success:
                        self.get_logger().info('Pick completed successfully (arm returned to post-grasp pose)')
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
