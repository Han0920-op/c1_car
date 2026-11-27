"""EXP1 颜色识别节点。"""
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.parameter import Parameter

from car1_app.color_detection import COLORS, ColorDetector
from car1_app.image_experiment import ImageExperiment, run_experiment


class Exp01ColorDetection(ImageExperiment):
    def __init__(self):
        super().__init__('exp01_color_detection')
        startup_setting = ParameterDescriptor(read_only=True)
        min_area = self.declare_parameter('min_area', 250.0, startup_setting).value
        bounds = {
            color: tuple(self.declare_parameter(
                f'hsv.{color}.{edge}', Parameter.Type.INTEGER_ARRAY, startup_setting).value
                for edge in ('lower', 'upper'))
            for color in COLORS
        }
        self.detector = ColorDetector(bounds, min_area)


def main(args=None):
    run_experiment(Exp01ColorDetection, args)
