from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from car1_app.polygon_detection import PolygonDetector


PACKAGE = Path(__file__).resolve().parents[1]


def test_sample_distinguishes_approximation_and_hull():
    settings = yaml.safe_load((PACKAGE / 'config/exp02_polygon_detection.yaml').read_text())[
        'exp02_polygon_detection']['ros__parameters']
    image = cv2.imread(str(PACKAGE / 'images/exp02_polygons.png'))
    detector = PolygonDetector(settings['foreground_mode'], settings['threshold'],
                               settings['min_area'], settings['epsilon_ratio'])
    result, mask, detections = detector.detect(image)

    assert {(item['category'], item['vertex_count']) for item in detections
            if item['category'] != 'other'} == {
        ('triangle', 3), ('quadrilateral', 4), ('pentagon', 5), ('hexagon', 6)
    }
    assert len(detections) == 6
    by_category = {item['category']: item for item in detections}
    assert (by_category['pentagon']['u'], by_category['pentagon']['v']) == (550, 110)
    concave = next(item for item in detections if item['u'] == 319)
    assert concave['vertex_count'] == 6 and concave['category'] == 'other'
    assert concave['hull_area_px2'] > concave['area_px2'] * 1.2
    circle = next(item for item in detections if item['v'] == 330 and item['u'] == 550)
    assert circle['category'] == 'other'
    assert result.shape == (image.shape[0], image.shape[1] * 3, 3)
    assert mask[215, 30] == 0


@pytest.mark.parametrize('mode, background, foreground', [
    ('bright', 0, 255),
    ('dark', 255, 0),
])
def test_grayscale_polarities_and_area_filter(mode, background, foreground):
    image = np.full((140, 180, 3), background, dtype=np.uint8)
    cv2.rectangle(image, (40, 30), (100, 90), (foreground,) * 3, -1)
    cv2.rectangle(image, (130, 30), (141, 41), (foreground,) * 3, -1)
    detections = PolygonDetector(mode, 100, 500, 0.025).detect(image)[2]
    assert len(detections) == 1
    assert detections[0]['category'] == 'quadrilateral'
    assert (detections[0]['u'], detections[0]['v']) == (70, 60)
