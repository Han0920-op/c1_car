"""把同一帧 ROS 检测结果送往 RQT 和课程 MJPEG 网页。"""
from contextlib import suppress
import time

from aiohttp.web_runner import GracefulExit
import cv2
import rclpy
from rclpy.executors import ExternalShutdownException

from car1_app.exp03_qrcode_detection import Exp03QrCodeDetection


def scan(args, cfg, server_type, stream_type, report):
    source = cfg['source']['ros']
    topic = args.topic or source['rgb_topic']
    timeout = float(source['timeout'])
    if timeout <= 0 or not 1 <= args.port <= 65535:
        raise ValueError('首帧超时必须为正数，端口范围为 1–65535')
    stream = stream_type('qrcode.mjpg')
    server = server_type(args.host, args.port)
    server.add_stream(stream)

    class LiveScan(Exp03QrCodeDetection):
        def __init__(self):
            super().__init__()
            self.frames = 0
            self.started = time.monotonic()
            self.stop_requested = False

        def process_image(self, msg):
            processed = super().process_image(msg)
            if processed is None:
                return
            image, detections = processed
            stream.set_frame(image)
            report(detections)
            self.frames += 1
            if self.frames % 30 == 0:
                now = time.monotonic()
                print(f'30帧平均帧率: {30 / (now - self.started):.1f}', flush=True)
                self.started = now
            if args.display:
                cv2.imshow(cfg['display']['window_name'], image)
                self.stop_requested = cv2.waitKey(1) & 0xff in (27, ord('q'))

    rclpy.init(args=['--ros-args', '-p', f'camera_topic:={topic}',
                     '-p', f"detect_scale:={float(cfg['detect']['scale'])}"])
    node = None
    try:
        node = LiveScan()
        server.start()
        deadline = time.monotonic() + timeout
        while rclpy.ok() and not node.stop_requested:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.frames == 0 and time.monotonic() >= deadline:
                raise ValueError(f'cannot open ros topic: {topic} ({timeout:g} s)')
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if args.display:
            cv2.destroyAllWindows()
        if server.is_running():
            with suppress(GracefulExit):
                server.stop()
