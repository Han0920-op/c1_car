#!/usr/bin/env python3
"""统计 HP60C 深度图各区域的有效深度覆盖率。

默认实时刷新(像 top, Ctrl+C 退出); 加 --once 只采集一次打印快照。

用法:
  source install/setup.bash
  python3 depth_coverage.py                      # 实时刷新
  python3 depth_coverage.py --once               # 一次性快照
  python3 depth_coverage.py --rows 8 --cols 12   # 更细网格
  python3 depth_coverage.py --window 10 --hz 2   # 最近10帧滑窗, 每秒刷2次
"""
import argparse
import sys
from collections import deque

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


class DepthCoverage(Node):
    def __init__(self, topic, rows, cols, live, window, hz, frames):
        super().__init__('depth_coverage')
        self.rows, self.cols = rows, cols
        self.live = live
        self.want = frames           # --once 模式下采集帧数
        self.frames = deque(maxlen=window)   # 滑动窗口, 每元素是单帧 valid(bool) 图
        self.depths = deque(maxlen=window)   # 对应单帧深度(mm, 仅有效处)
        self.n_total = 0
        self.w = self.h = 0
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.RELIABLE
        self.sub = self.create_subscription(Image, topic, self.cb, qos)
        if live:
            self.timer = self.create_timer(1.0 / hz, self.tick)
            self.get_logger().info(f'订阅 {topic} ,实时刷新中 (Ctrl+C 退出)...')
        else:
            self.get_logger().info(f'订阅 {topic} ,采集 {frames} 帧...')

    def cb(self, msg):
        if msg.encoding != '16UC1':
            self.get_logger().error(f'非 16UC1 编码: {msg.encoding}')
            return
        d = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
        self.w, self.h = msg.width, msg.height
        valid = d > 0
        self.frames.append(valid)
        self.depths.append(d.astype(np.int64))
        self.n_total += 1
        if not self.live and self.n_total >= self.want:
            self.report(snapshot=True)
            rclpy.shutdown()

    def tick(self):
        if self.frames:
            self.report(snapshot=False)

    def report(self, snapshot):
        n = len(self.frames)
        cov = np.mean(self.frames, axis=0)        # 每像素有效率 0..1
        overall = cov.mean() * 100
        stacked = np.stack(self.depths)
        valid_mask = stacked > 0
        valid_total = valid_mask.sum()
        mean_depth = (stacked[valid_mask].sum() / valid_total / 1000.0) if valid_total else 0
        lines = []
        if self.live:
            lines.append('\033[2J\033[H')   # 清屏 + 光标归位
        title = '深度覆盖率快照' if snapshot else '深度覆盖率(实时, Ctrl+C 退出)'
        lines.append(f'=== {title}  窗口{n}帧  {self.w}x{self.h} ===')
        lines.append(f'整体有效率: {overall:5.1f}%   有效区平均深度: {mean_depth:.2f} m')
        lines.append('')
        lines.append(f'网格有效率 ({self.rows}行 x {self.cols}列), 左上=画面左上:')
        ys = np.linspace(0, self.h, self.rows + 1, dtype=int)
        xs = np.linspace(0, self.w, self.cols + 1, dtype=int)
        lines.append('       ' + ''.join(f' C{c:<5d}' for c in range(self.cols)))
        for r in range(self.rows):
            cells = []
            for c in range(self.cols):
                block = cov[ys[r]:ys[r+1], xs[c]:xs[c+1]]
                pct = block.mean() * 100
                cells.append(f'{pct:4.0f}%{self.bar(pct)}')
            lines.append(f'  R{r:<2d} ' + ' '.join(cells))
        lines.append('')
        lines.append('标记: ##=>80%好  ++=40-80%中  ..=10-40%差  --=<10%几乎空洞')
        sys.stdout.write('\n'.join(lines) + '\n')
        sys.stdout.flush()

    @staticmethod
    def bar(pct):
        if pct >= 80:
            return '##'
        if pct >= 40:
            return '++'
        if pct >= 10:
            return '..'
        return '--'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='/ascamera_hp60c/camera_publisher/depth0/image_raw')
    ap.add_argument('--rows', type=int, default=6)
    ap.add_argument('--cols', type=int, default=8)
    ap.add_argument('--once', action='store_true', help='只采集一次打印快照后退出')
    ap.add_argument('--window', type=int, default=10, help='实时模式滑动窗口帧数')
    ap.add_argument('--hz', type=float, default=2.0, help='实时模式刷新频率')
    ap.add_argument('--frames', type=int, default=30, help='--once 模式采集帧数')
    args = ap.parse_args()
    rclpy.init()
    node = DepthCoverage(args.topic, args.rows, args.cols,
                         live=not args.once, window=args.window,
                         hz=args.hz, frames=args.frames)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
