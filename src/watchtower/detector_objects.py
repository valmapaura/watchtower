"""Object detection behind the same ``MotionDetector`` interface.

``ObjectDetector`` uses a YOLO model (via ``ultralytics``) to detect specific
object classes (person, car, animal, ...) instead of just "something moved".
It implements the same interface as ``FrameDiffDetector``, so the recorder
does not change — you swap the detector in config.

Design notes:
  * The model is loaded lazily on first use so importing the module never
    requires ultralytics to be installed.
  * ``motion_score`` returns (has_motion, score) where score is the peak
    confidence (0-100) of any detected object of interest.
  * ``detected_classes`` records which classes were seen, so the recorder can
    tag the clip's ``category``.
"""

from __future__ import annotations

from .detector import MotionDetector

# COCO class ids we care about. YOLO's default model (yolov8n) uses COCO.
# Map a friendly category name to the set of COCO class ids that count as it.
CATEGORY_CLASS_IDS: dict[str, set[int]] = {
    "person": {0},
    "vehicle": {2, 3, 5, 7},          # car, motorcycle, bus, truck
    "animal": {14, 15, 16, 17, 18, 19, 20, 21, 22, 23},  # bird..zebra
    "bicycle": {1},
}


class ObjectDetector(MotionDetector):
    """Detects objects of interest using a YOLO model.

    ``categories`` selects which object groups count as motion (e.g.
    ``["person", "vehicle"]``). ``confidence`` is the minimum detection
    confidence (0-1) to accept.
    """

    def __init__(
        self,
        categories: list[str] | None = None,
        confidence: float = 0.5,
        model_name: str = "yolov8n",
    ):
        self.categories = categories or ["person"]
        self.confidence = float(confidence)
        self.model_name = model_name
        self._model = None
        self.detected_classes: set[str] = set()

    def _load_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as e:  # pragma: no cover - env-dependent
                raise RuntimeError(
                    "ObjectDetector requires 'ultralytics'. Install it with "
                    "`pip install ultralytics`."
                ) from e
            self._model = YOLO(self.model_name)
        return self._model

    def _class_ids(self) -> set[int]:
        ids: set[int] = set()
        for cat in self.categories:
            ids |= CATEGORY_CLASS_IDS.get(cat, set())
        return ids

    def _analyze(self, frame) -> tuple[bool, float]:
        """Run inference; return (has_interest, peak_confidence)."""
        model = self._load_model()
        results = model(frame, verbose=False)
        if not results:
            return (False, 0.0)
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return (False, 0.0)

        wanted = self._class_ids()
        peak = 0.0
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id in wanted and conf >= self.confidence:
                peak = max(peak, conf)
                for cat, ids in CATEGORY_CLASS_IDS.items():
                    if cls_id in ids:
                        self.detected_classes.add(cat)
        return (peak > 0.0, round(peak * 100.0, 1))

    def detect(self, frame) -> bool:
        return self.motion_score(frame)[0]

    def motion_score(self, frame) -> tuple[bool, float]:
        return self._analyze(frame)

    def reset(self) -> None:
        self.detected_classes.clear()