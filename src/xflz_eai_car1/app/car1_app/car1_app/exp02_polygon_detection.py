"""EXP2 多边形描绘的独立 ROS 节点。"""
from rcl_interfaces.msg import ParameterDescriptor

from car1_app.image_experiment import ImageExperiment, run_experiment
from car1_app.polygon_detection import PolygonDetector


class Exp02PolygonDetection(ImageExperiment):
    def __init__(self):
        super().__init__('exp02_polygon_detection')
        settings = ParameterDescriptor(read_only=True)
        self.detector = PolygonDetector(
            self.declare_parameter('foreground_mode', 'saturation', settings).value,
            self.declare_parameter('threshold', 80, settings).value,
            self.declare_parameter('min_area', 500.0, settings).value,
            self.declare_parameter('epsilon_ratio', 0.025, settings).value,
        )


def main(args=None):
    run_experiment(Exp02PolygonDetection, args)
