#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Angular velocity calibration node.

Rotates the robot a known angle (default 360°) and compares odometry vs actual.
Use rqt_reconfigure to adjust odom_angular_scale_correction until they match.

Reads yaw directly from /odom_raw (wheel-only odometry from odom_publisher),
NOT from the odom->base_footprint TF (which is EKF-fused with IMU). This way the
measured angle reflects pure wheel odometry, matching the angular_correction_factor
that odom_publisher applies.
"""
import time
import rclpy
import signal
import threading
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from math import copysign, pi, atan2, asin, radians


def qua2rpy(quat):
    x, y, z, w = quat.x, quat.y, quat.z, quat.w
    roll = atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = asin(2 * (w * y - x * z))
    yaw = atan2(2 * (w * z + x * y), 1 - 2 * (z * z + y * y))
    if roll < 0:
        roll += 2 * pi
    if pitch < 0:
        pitch += 2 * pi
    if yaw < 0:
        yaw += 2 * pi
    return roll, pitch, yaw


def normalize_angle(angle):
    res = angle
    while res > pi:
        res -= 2.0 * pi
    while res < -pi:
        res += 2.0 * pi
    return res


class CalibrateAngular(Node):
    def __init__(self, name):
        rclpy.init()
        super().__init__(name)
        signal.signal(signal.SIGINT, self.shutdown)

        self.declare_parameter('test_angle', 360.0)
        self.declare_parameter('speed', 0.5)
        self.declare_parameter('tolerance', 1.5)
        self.declare_parameter('odom_angular_scale_correction', 1.0)
        self.declare_parameter('start_test', False)
        self.update_param()

        self.cmd_vel = self.create_publisher(Twist, "/controller/cmd_vel", 1)
        self.create_subscription(Odometry, '/odom_raw', self.odom_callback, 10)

        self.odom_yaw = None  # latest yaw from /odom_raw (radians)
        self.last_angle = 0
        self.reverse = 1
        self.calib_angle = 0

        self.clock = self.get_clock()
        threading.Thread(target=self.main, daemon=True).start()

        self.get_logger().info('\033[1;32m%s\033[0m' % 'Bring up rqt_reconfigure to control the test')

    def update_param(self):
        self.start_test = self.get_parameter('start_test').value
        self.test_angle = self.get_parameter('test_angle').value
        self.speed = self.get_parameter('speed').value
        self.tolerance = self.get_parameter('tolerance').value
        self.odom_angular_scale_correction = self.get_parameter('odom_angular_scale_correction').value

    def odom_callback(self, msg):
        self.odom_yaw = qua2rpy(msg.pose.pose.orientation)[2]

    def main(self):
        while True:
            self.update_param()
            move_cmd = Twist()
            if self.start_test:
                if self.odom_yaw is None:
                    self.get_logger().warn('Waiting for /odom_raw...')
                    time.sleep(0.1)
                    continue

                # Accumulate the MAGNITUDE of rotation, independent of odom's yaw
                # sign convention. We spin one constant direction (self.reverse)
                # until the accumulated |rotation| from odom reaches test_angle.
                # This avoids the positive-feedback divergence that happens when
                # odom yaw sign is opposite to the commanded direction.
                original_angle = self.odom_yaw                       # rad, wrapped [-pi,pi]
                target = radians(abs(self.test_angle))               # rad, positive
                step = abs(self.odom_angular_scale_correction *
                           normalize_angle(original_angle - self.last_angle))
                self.calib_angle += step                             # always grows
                self.last_angle = original_angle
                remaining = target - self.calib_angle                # shrinks to 0

                if remaining > radians(self.tolerance):
                    move_cmd.angular.z = copysign(self.speed, self.reverse)
                else:
                    self.calib_angle = 0.0
                    self.start_test = rclpy.parameter.Parameter(
                        'start_test', rclpy.Parameter.Type.BOOL, False)
                    self.set_parameters([self.start_test])
                    self.reverse = -self.reverse
                    self.last_angle = 0.0
                    self.get_logger().info('\033[1;32m%s\033[0m' % 'finish')
            else:
                # Keep last_angle synced while idle so the first delta after
                # start_test isn't a huge jump.
                if self.odom_yaw is not None:
                    self.last_angle = self.odom_yaw

            self.cmd_vel.publish(move_cmd)
            time.sleep(0.05)

    def shutdown(self, signum, frame):
        self.get_logger().info('\033[1;32m%s\033[0m' % 'Stopping the robot...')
        self.start_test = False
        self.cmd_vel.publish(Twist())
        rclpy.shutdown()


def main():
    node = CalibrateAngular('calibrate_angular')
    rclpy.spin(node)


if __name__ == "__main__":
    main()
