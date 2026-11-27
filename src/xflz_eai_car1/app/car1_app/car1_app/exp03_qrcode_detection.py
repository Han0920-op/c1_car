"""EXP3 二维码检测的独立 ROS 节点。"""
from rcl_interfaces.msg import ParameterDescriptor

from car1_app.image_experiment import ImageExperiment, run_experiment
from car1_app.qrcode_detection import QrCodeDetector


class Exp03QrCodeDetection(ImageExperiment):
    def __init__(self):
        super().__init__('exp03_qrcode_detection')
        scale = self.declare_parameter(
            'detect_scale', 0.5, ParameterDescriptor(read_only=True)).value
        self.detector = QrCodeDetector(scale)


def main(args=None):
    run_experiment(Exp03QrCodeDetection, args)
