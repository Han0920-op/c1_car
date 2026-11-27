"""EXP2 的图像分割和多边形几何处理。"""
import math

import cv2
import numpy as np

from car1_app.color_detection import denoise_mask


SHAPES = {3: 'triangle', 4: 'quadrilateral', 5: 'pentagon', 6: 'hexagon'}


class PolygonDetector:
    def __init__(self, foreground_mode, threshold, min_area, epsilon_ratio):
        if foreground_mode not in ('saturation', 'bright', 'dark'):
            raise ValueError('foreground_mode must be saturation, bright or dark')
        if not 0 <= threshold <= 255:
            raise ValueError('threshold must be in [0, 255]')
        if not math.isfinite(min_area) or min_area <= 0:
            raise ValueError('min_area must be positive and finite')
        if not 0 < epsilon_ratio < 0.1:
            raise ValueError('epsilon_ratio must be between 0 and 0.1 (exclusive)')
        self.mode = foreground_mode
        self.threshold = threshold
        self.min_area = min_area
        self.epsilon_ratio = epsilon_ratio
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detect(self, bgr):
        if self.mode == 'saturation':
            channel = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
        else:
            channel = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        polarity = cv2.THRESH_BINARY_INV if self.mode == 'dark' else cv2.THRESH_BINARY
        _, mask = cv2.threshold(channel, self.threshold, 255, polarity)
        mask = denoise_mask(mask, self.kernel)

        # 保留边界采样点，用于描绘原始轮廓及说明逼近的作用。
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        original, polygon_view, hull_view = (bgr.copy() for _ in range(3))
        detections = []
        rows, cols = mask.shape
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            if area < self.min_area or x == 0 or y == 0 or x + w == cols or y + h == rows:
                continue
            perimeter = cv2.arcLength(contour, True)
            polygon = cv2.approxPolyDP(contour, perimeter * self.epsilon_ratio, True)
            hull = cv2.convexHull(contour)
            # 分类依据逼近轮廓。凸包会填平凹陷，不能用它替代原目标边界。
            count = len(polygon)
            category = SHAPES.get(count, 'other') if cv2.isContourConvex(polygon) else 'other'
            moments = cv2.moments(contour)
            u = round(moments['m10'] / moments['m00'])
            v = round(moments['m01'] / moments['m00'])
            vertices = polygon.reshape(-1, 2).tolist()
            detections.append({
                'category': category, 'vertex_count': count, 'vertices': vertices,
                'area_px2': area, 'perimeter_px': perimeter, 'u': u, 'v': v,
                'hull_area_px2': cv2.contourArea(hull),
            })

            cv2.drawContours(original, [contour], -1, (255, 255, 0), 2)
            cv2.drawContours(polygon_view, [polygon], -1, (0, 255, 0), 2)
            cv2.drawContours(hull_view, [hull], -1, (255, 0, 255), 2)
            for vx, vy in vertices:
                cv2.circle(polygon_view, (vx, vy), 4, (0, 255, 255), -1)
            cv2.circle(polygon_view, (u, v), 3, (255, 255, 255), -1)
            self.label(polygon_view, f'{category} ({count})', (x, max(y - 5, 18)))

        for panel, title in zip((original, polygon_view, hull_view),
                                ('Original contour', 'Approximation', 'Convex hull')):
            self.label(panel, title, (8, 20))
        return np.hstack((original, polygon_view, hull_view)), mask, detections

    @staticmethod
    def label(image, text, origin):
        cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(image, text, origin, cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 1, cv2.LINE_AA)
