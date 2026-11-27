"""EXP3 共用的二维码检测、原图标注和解码兼容处理。"""
import cv2
import numpy as np

try:
    from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode
except ImportError:
    zbar_decode = None

MAX_DETECT_PASSES = 8


class QrCodeDetector:
    def __init__(self, detect_scale):
        if not 0.1 <= detect_scale <= 2.0:
            raise ValueError('detect_scale must be between 0.1 and 2.0')
        self.detect_scale = detect_scale
        self.detector = cv2.QRCodeDetector()

    def detect(self, bgr):
        height, width = bgr.shape[:2]
        scaled_width = int(width * self.detect_scale)
        scaled_height = int(height * self.detect_scale)
        result = bgr.copy()
        mask = np.zeros((height, width), np.uint8)
        detections = []
        if min(scaled_width, scaled_height) < 21:
            return result, mask, detections

        # 单独的工作图可以涂白，原图和标注图始终保持原始尺寸。
        work = cv2.resize(bgr, (scaled_width, scaled_height))
        ratio = np.float32([width / scaled_width, height / scaled_height])
        for _ in range(MAX_DETECT_PASSES):
            try:
                content, points, _ = self.detector.detectAndDecode(work)
            except UnicodeDecodeError:
                # 非 UTF-8 载荷也可能有可用的角点。
                _, points = self.detector.detect(work)
                content = ''
            if points is None:
                break
            points = points.reshape(4, 2)
            corners = (points + 0.5) * ratio - 0.5
            if not np.isfinite(corners).all() or abs(cv2.contourArea(corners)) < 1.0:
                break
            if not content:
                content = self.decode_fallback(bgr, corners)
            detections.append({
                'corners': corners.tolist(), 'decoded': bool(content), 'content': content or None,
            })
            border = np.rint(corners).astype(np.int32)
            color = (0, 255, 0) if content else (0, 180, 255)
            x, y, w, h = cv2.boundingRect(border)
            cv2.rectangle(result, (x, y), (x + w - 1, y + h - 1), color, 2)
            cv2.polylines(mask, [border], True, 255, 2)
            for point in border:
                cv2.circle(result, tuple(point), 3, color, -1)
            label = content or 'Undecoded QR'
            if len(label) > 40:
                label = label[:37] + '...'
            cv2.putText(result, label, (max(0, x), max(16, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)
            # 掩去工作图上刚处理的码，再扫描剩余区域，最多八次。
            x, y, w, h = cv2.boundingRect(points)
            work[max(0, y-2):y+h+2, max(0, x-2):x+w+2] = 255
        return result, mask, detections

    @staticmethod
    def decode_fallback(bgr, corners):
        if zbar_decode is None:
            return ''
        # 某些 Humble 系统包没有 QUIRC，保留原图透视校正和 ZBar 兼容路径。
        side = 252
        square = np.float32([[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]])
        transform = cv2.getPerspectiveTransform(corners, square)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        straight = cv2.warpPerspective(gray, transform, (side, side))
        padded = cv2.copyMakeBorder(straight, 48, 48, 48, 48, cv2.BORDER_CONSTANT, value=255)
        decoded = zbar_decode(padded, symbols=[ZBarSymbol.QRCODE])
        if decoded:
            return decoded[0].data.decode('utf-8', errors='replace')
        return ''
