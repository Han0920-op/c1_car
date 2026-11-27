"""课程入口：生成、图片读回、ROS 实时扫描。"""
import argparse
from pathlib import Path
import sys

import cv2
import numpy as np
import qrcode
import yaml

# 离线实验也复用工作区的算法，不依赖 ROS 安装或当前工作目录。
LESSON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LESSON.parents[1] / 'app' / 'car1_app'))
from car1_app.qrcode_detection import QrCodeDetector


def generate_qr(data, cfg):
    levels = {'L': qrcode.constants.ERROR_CORRECT_L, 'M': qrcode.constants.ERROR_CORRECT_M,
              'Q': qrcode.constants.ERROR_CORRECT_Q, 'H': qrcode.constants.ERROR_CORRECT_H}
    qr = qrcode.QRCode(version=cfg['version'], error_correction=levels[cfg['error_correction']],
                       box_size=cfg['box_size'], border=cfg['border'])
    qr.add_data(data)
    qr.make(fit=True)
    rgb = qr.make_image(fill_color=tuple(cfg['fill_color']),
                        back_color=tuple(cfg['back_color'])).convert('RGB')
    return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def report(detections):
    for qr in detections:
        if qr['decoded']:
            print(f"[QR] {qr['content']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--generate', metavar='TEXT')
    mode.add_argument('--detect', action='store_true')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--image', type=Path)
    source.add_argument('--ros', action='store_true')
    parser.add_argument('--save', type=Path)
    parser.add_argument('--config', type=Path, default=LESSON / 'config/qrcode_config.yaml')
    parser.add_argument('--topic', help='覆盖配置的 ROS 彩色图像话题')
    parser.add_argument('--host', default='localhost', help='MJPEG 监听主机')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--display', action='store_true')
    args = parser.parse_args()
    if args.detect != bool(args.image or args.ros):
        parser.error('--detect 需要 --image 或 --ros，--generate 直接接文字')
    if args.ros and args.save:
        parser.error('--save 用于生成或单张图片读回')
    try:
        from mjpeg_streamer import MjpegServer, Stream
    except ImportError as exc:
        parser.exit(2, f'请按实验文档安装 mjpeg_streamer 及依赖：{exc}\n')
    try:
        cfg = yaml.safe_load(args.config.read_text(encoding='utf-8'))
        if args.ros:
            from live_scan import scan
            return scan(args, cfg, MjpegServer, Stream, report)
        if args.generate is not None:
            image = generate_qr(args.generate, cfg['generate'])
            dest = args.save or Path('my_qr.png')
        else:
            image = cv2.imread(str(args.image))
            if image is None:
                raise ValueError(f'cannot read image: {args.image}')
            image, _, detections = QrCodeDetector(cfg['detect']['scale']).detect(image)
            report(detections)
            dest = args.save
        if dest:
            if not cv2.imwrite(str(dest), image):
                raise OSError(f'无法写入 {dest}')
            print(f'QR 已保存: {dest.resolve()}' if args.generate is not None else f'saved -> {dest}')
        if args.display:
            cv2.imshow(cfg['display']['window_name'], image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    except (ValueError, TypeError, KeyError, OSError, ImportError, cv2.error, yaml.YAMLError,
            qrcode.exceptions.DataOverflowError) as exc:
        parser.exit(2, f'EXP3: {exc}\n')


if __name__ == '__main__':
    sys.exit(main())
