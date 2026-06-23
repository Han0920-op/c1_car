#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Linear velocity calibration node.

Drives the robot forward a known distance and compares odometry vs actual
measurement (用尺子量实际距离). 系数 = test_distance / 实际距离。

读 /odom_raw（纯轮式里程计），累加行进【里程】，单向前进，到目标就停。
不再用欧氏距离 + 正负 error 闭环纠偏（那会因 sqrt 永远为正导致前后震荡）。
"""
import time
import rclpy
import signal
import threading
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist


class CalibrateLinear(Node):
    def __init__(self, name):
        rclpy.init()
        super().__init__(name)
        signal.signal(signal.SIGINT, self.shutdown)

        self.declare_parameter('test_distance', 1.0)
        self.declare_parameter('speed', 0.2)
        self.declare_parameter('tolerance', 0.03)
        self.declare_parameter('odom_linear_scale_correction', 1.0)
        self.declare_parameter('start_test', False)
        self.update_param()

        self.cmd_vel = self.create_publisher(Twist, "/controller/cmd_vel", 1)
        self.create_subscription(Odometry, '/odom_raw', self.odom_callback, 10)

        self.pos = None          # 最新 (x, y) from /odom_raw
        self.last_pos = None     # 上一帧 (x, y)
        self.traveled = 0.0      # 累加行进里程

        self.clock = self.get_clock()
        threading.Thread(target=self.main, daemon=True).start()

        self.get_logger().info('\033[1;32m%s\033[0m' % 'Set start_test:=true to run')

    def update_param(self):
        self.start_test = self.get_parameter('start_test').value
        self.test_distance = self.get_parameter('test_distance').value
        self.speed = self.get_parameter('speed').value
        self.tolerance = self.get_parameter('tolerance').value
        self.odom_linear_scale_correction = self.get_parameter('odom_linear_scale_correction').value

    def odom_callback(self, msg):
        self.pos = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def main(self):
        running = False
        while True:
            self.update_param()
            move_cmd = Twist()

            if self.start_test:
                if self.pos is None:
                    self.get_logger().warn('Waiting for /odom_raw...')
                    time.sleep(0.1)
                    continue

                if not running:
                    # 开始一次新测试：清零累加
                    running = True
                    self.traveled = 0.0
                    self.last_pos = self.pos

                # 累加这一帧的行进里程（幅度，与方向无关）
                dx = self.pos[0] - self.last_pos[0]
                dy = self.pos[1] - self.last_pos[1]
                self.traveled += (dx * dx + dy * dy) ** 0.5
                self.last_pos = self.pos

                calib = self.traveled * self.odom_linear_scale_correction
                remaining = self.test_distance - calib

                if remaining > self.tolerance:
                    move_cmd.linear.x = self.speed   # 单向前进
                else:
                    running = False
                    self.start_test = rclpy.parameter.Parameter(
                        'start_test', rclpy.Parameter.Type.BOOL, False)
                    self.set_parameters([self.start_test])
                    self.get_logger().info(
                        '\033[1;32mfinish: odom 行进 %.3f m\033[0m' % self.traveled)
            else:
                running = False
                if self.pos is not None:
                    self.last_pos = self.pos

            self.cmd_vel.publish(move_cmd)
            time.sleep(0.05)

    def shutdown(self, signum, frame):
        self.get_logger().info('\033[1;32m%s\033[0m' % 'Stopping the robot...')
        self.start_test = False
        self.cmd_vel.publish(Twist())
        rclpy.shutdown()


def main():
    node = CalibrateLinear('calibrate_linear')
    rclpy.spin(node)


if __name__ == "__main__":
    main()
