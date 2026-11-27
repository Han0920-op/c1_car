from pathlib import Path

import cv2
import numpy as np
import pytest

from car1_app.qrcode_detection import QrCodeDetector


PACKAGE = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample():
    return cv2.imread(str(PACKAGE / 'images/exp03_qrcode.png'))


@pytest.mark.parametrize('scale', [0.5, 0.73, 1.0, 1.5])
def test_decode_and_remap_to_odd_sized_input(sample, scale):
    result, mask, detections = QrCodeDetector(scale).detect(sample)
    assert len(detections) == 1
    qr = detections[0]
    assert qr['decoded'] and qr['content'] == 'C1-EXP3'
    expected = np.array([[217, 133], [426, 133], [426, 342], [217, 342]])
    np.testing.assert_allclose(qr['corners'], expected, atol=4)
    assert result.shape == sample.shape
    assert mask.shape == sample.shape[:2] and np.count_nonzero(mask) > 0


def test_no_qr_returns_unchanged_image_and_empty_detections(sample):
    sample.fill(145)
    result, mask, detections = QrCodeDetector(0.73).detect(sample)
    assert detections == []
    assert not np.any(mask)
    np.testing.assert_array_equal(result, sample)


def test_located_but_undecodable_still_reports_corners(sample):
    detector = QrCodeDetector(1.0)
    # 保留三个定位图案，破坏中间的数据格。
    sample[180:310, 260:380] = 255
    _, mask, detections = detector.detect(sample)
    assert len(detections) == 1
    assert len(detections[0]['corners']) == 4
    assert detections[0]['decoded'] is False and detections[0]['content'] is None
    assert np.any(mask)


@pytest.mark.parametrize('scale', [0.0, 2.1, float('nan')])
def test_invalid_scale(scale):
    with pytest.raises(ValueError):
        QrCodeDetector(scale)


def test_two_codes_masked_individually_without_changing_input(sample):
    patch = sample[93:383, 177:467]
    canvas = np.full((600, 820, 3), 230, np.uint8)
    canvas[20:310, 20:310] = patch
    canvas[330:533, 520:723] = cv2.resize(patch, (203, 203), interpolation=cv2.INTER_NEAREST)
    original = canvas.copy()
    _, _, found = QrCodeDetector(0.5).detect(canvas)
    assert [qr['content'] for qr in found] == ['C1-EXP3', 'C1-EXP3']
    centers = sorted(np.mean(qr['corners'], axis=0).tolist() for qr in found)
    np.testing.assert_allclose(centers, [[165, 165], [621, 431]], atol=5)
    np.testing.assert_array_equal(canvas, original)
