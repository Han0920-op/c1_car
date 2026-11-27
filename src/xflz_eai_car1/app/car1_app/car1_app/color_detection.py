"""EXP1 的 OpenCV 算法，可独立于 ROS 测试。"""
import math

import cv2
import numpy as np


COLORS = {
    'red': (0, 0, 255),
    'green': (0, 255, 0),
    'blue': (255, 0, 0),
    'yellow': (0, 255, 255),
}


def denoise_mask(mask, kernel):
    """先开运算去除亮噪点，再闭运算填补颜色区域的小孔。"""
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)


def hue_mask(hsv, lower, upper):
    if lower[0] <= upper[0]:
        return cv2.inRange(hsv, lower, upper)

    # OpenCV 的 H 是环形坐标。较大的下界表示跨过 179 → 0。
    high = cv2.inRange(hsv, lower, (179, upper[1], upper[2]))
    low = cv2.inRange(hsv, (0, lower[1], lower[2]), upper)
    return cv2.bitwise_or(high, low)


class ColorDetector:
    def __init__(self, bounds, min_area):
        if not math.isfinite(min_area) or min_area <= 0:
            raise ValueError('min_area must be a positive, finite area in px²')
        self.min_area = min_area
        self.bounds = {}
        for color, (lower, upper) in bounds.items():
            for value in (lower, upper):
                if len(value) != 3 or any(not 0 <= v <= limit
                                          for v, limit in zip(value, (179, 255, 255))):
                    raise ValueError(f'{color}: HSV bounds must be [H:0-179, S:0-255, V:0-255]')
            if lower[1] > upper[1] or lower[2] > upper[2]:
                raise ValueError(f'{color}: S and V lower bounds must not exceed upper bounds')
            self.bounds[color] = (tuple(lower), tuple(upper))
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detect(self, bgr):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        annotated = bgr.copy()
        combined_mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
        detections = []

        for color, (lower, upper) in self.bounds.items():
            mask = denoise_mask(hue_mask(hsv, lower, upper), self.kernel)
            combined_mask |= mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.min_area:
                    continue
                # 图像矩给出轮廓质心，坐标原点位于图像左上角。
                moments = cv2.moments(contour)
                u = round(moments['m10'] / moments['m00'])
                v = round(moments['m01'] / moments['m00'])
                x, y, width, height = cv2.boundingRect(contour)
                # 外接圆描述目标的覆盖范围，质心仍由图像矩给出。
                (cx, cy), radius = cv2.minEnclosingCircle(contour)
                cv2.circle(annotated, (round(cx), round(cy)), round(radius), COLORS[color], 1)
                detections.append({
                    'color': color, 'u': u, 'v': v, 'area_px2': area,
                    'bbox': [x, y, width, height],
                    'circle': {'u': cx, 'v': cy, 'radius_px': radius},
                })
                cv2.rectangle(annotated, (x, y), (x + width - 1, y + height - 1),
                              COLORS[color], 2)
                cv2.circle(annotated, (u, v), 4, (255, 255, 255), -1)
                label = f'{color} ({u}, {v})'
                origin = (x, y - 5 if y >= 20 else min(y + 17, bgr.shape[0] - 1))
                cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 0, 0), 3, cv2.LINE_AA)
                cv2.putText(annotated, label, origin, cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (255, 255, 255), 1, cv2.LINE_AA)

        return annotated, combined_mask, detections
