#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Angular velocity calibration node.

Rotates the robot a known angle (default 360°) and compares odometry vs actual.
Use rqt_reconfigure to adjust odom_angular_scale_correction until they match.
"""
import time
import rclpy
import signal
import threading
from rclpy.node import Node
from tf2_ros.buffer import Buffer
from geometry_msgs.msg import Twist, Point
from math import copysign, pi, atan2, asin, degrees
from tf2_ros.transform_listener import TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


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

        self.odom_frame = 'odom'
        self.base_frame = 'base_footprint'
        self.cmd_vel = self.create_publisher(Twist, "/controller/cmd_vel", 1)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.position = Point()
        self.x_start = self.position.x
        self.y_start = self.position.y

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

    def main(self):
        while True:
            self.update_param()
            move_cmd = Twist()
            if self.start_test:
                original_angle = degrees(self.get_odom_angle())
                self.test_angle = copysign(self.test_angle, self.reverse)

                delta_angle = self.odom_angular_scale_correction * normalize_angle(
                    original_angle - self.last_angle)
                self.calib_angle += delta_angle
                error = self.test_angle - self.calib_angle
                self.last_angle = original_angle

                if abs(error) > self.tolerance and self.start_test:
                    move_cmd.angular.z = copysign(self.speed, error)
                else:
                    self.calib_angle = 0.0
                    self.start_test = rclpy.parameter.Parameter(
                        'start_test', rclpy.Parameter.Type.BOOL, False)
                    self.set_parameters([self.start_test])
                    self.reverse = -self.reverse
                    self.last_angle = 0
                    self.get_logger().info('\033[1;32m%s\033[0m' % 'finish')

            self.cmd_vel.publish(move_cmd)
            time.sleep(0.05)

    def get_odom_angle(self):
        try:
            trans = self.tf_buffer.lookup_transform(
                self.odom_frame, self.base_frame,
                rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=1))
            return qua2rpy(trans.transform.rotation)[2]
        except (LookupException, ConnectivityException, ExtrapolationException):
            self.get_logger().info('\033[1;32m%s\033[0m' % 'TF Exception')
            return 0.0

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
