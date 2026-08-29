"""Unit tests for the object detector (categorisation)."""
from __future__ import annotations

import pytest

from watchtower.detector_objects import CATEGORY_CLASS_IDS, ObjectDetector


def test_category_class_ids_mapping():
    # COCO class 0 is person, 2 is car.
    assert 0 in CATEGORY_CLASS_IDS["person"]
    assert 2 in CATEGORY_CLASS_IDS["vehicle"]


def test_object_detector_requires_ultralytics():
    """Without ultralytics installed, inference raises a clear error."""
    det = ObjectDetector(categories=["person"])
    with pytest.raises(RuntimeError, match="ultralytics"):
        det.motion_score(None)


def test_object_detector_default_categories():
    det = ObjectDetector()
    assert det.categories == ["person"]
    assert det.confidence == 0.5


def test_object_detector_reset_clears_classes():
    det = ObjectDetector()
    det.detected_classes.add("person")
    det.reset()
    assert det.detected_classes == set()