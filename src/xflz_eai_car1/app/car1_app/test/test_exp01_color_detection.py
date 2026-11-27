from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from car1_app.color_detection import ColorDetector, hue_mask


PACKAGE = Path(__file__).resolve().parents[1]


def test_sample_detects_four_colors_and_both_red_hues():
    params = yaml.safe_load((PACKAGE / 'config/exp01_color_detection.yaml').read_text())[
        'exp01_color_detection']['ros__parameters']
    bounds = {name: (hsv['lower'], hsv['upper']) for name, hsv in params['hsv'].items()}
    image = cv2.imread(str(PACKAGE / 'images/exp01_colors.png'))
    annotated, mask, detections = ColorDetector(bounds, params['min_area']).detect(image)

    assert {(d['color'], d['u'], d['v']) for d in detections} == {
        ('red', 120, 100), ('green', 320, 100), ('blue', 520, 100),
        ('yellow', 220, 260), ('red', 420, 260),
    }
    for detection in detections:
        x, y, width, height = detection['bbox']
        assert x <= detection['u'] < x + width
        assert y <= detection['v'] < y + height
        assert 81 <= width <= 85 and 81 <= height <= 85
    assert mask[100, 120] == 255  # 闭运算补孔
    assert mask[20, 20] == 0  # 开运算去掉孤立像素
    assert mask[255, 600] == 255  # 小斑块在掩膜可见，但未通过面积过滤
    assert annotated.shape == image.shape
    assert np.all(annotated[100, 120] == 255)  # 白色中心标记


def test_red_wrap_respects_hue_saturation_and_value():
    hsv = np.uint8([[[0, 255, 255], [179, 255, 255], [60, 255, 255],
                     [175, 60, 255], [5, 255, 50]]])
    assert hue_mask(hsv, (170, 100, 70), (10, 255, 255)).tolist() == [[255, 255, 0, 0, 0]]


@pytest.mark.parametrize('bounds, area', [
    ({'red': ([180, 0, 0], [10, 255, 255])}, 250),
    ({'red': ([170, 150, 0], [10, 100, 255])}, 250),
    ({'red': ([170, 100, 0], [10, 255, 255])}, 0),
])
def test_invalid_configuration(bounds, area):
    with pytest.raises(ValueError):
        ColorDetector(bounds, area)
