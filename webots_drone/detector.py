"""
detector.py — YOLOv8 person detection for the drone camera feed.
Place in the same folder as webots_simulation.py (webots_drone/).

Install dependency (run once):
    pip install ultralytics
"""

import cv2
import numpy as np
from ultralytics import YOLO


class PersonDetector:
    """Detects people in drone camera frames using YOLOv8."""

    def __init__(self, confidence=0.4, run_every_n_frames=5):
        """
        confidence        : minimum detection score (0.0-1.0)
        run_every_n_frames: only run YOLO every N frames, reuse last result
                            in between. 5 = smooth display, responsive drone.
                            Increase to 10 if still slow.
        """
        print("Loading YOLOv8 model... ", end="", flush=True)
        self.model = YOLO("yolov8n.pt")  # nano = fastest model
        self.confidence = confidence
        self.person_class_id = 0  # COCO class 0 = person
        self.run_every_n_frames = run_every_n_frames

        # cache — reuse last detection between YOLO runs
        self._frame_count = 0
        self._last_detections = []
        print("OK")

    def detect(self, frame_bgra):
        """
        Run detection on a BGRA frame from the Webots drone camera.
        Only calls YOLO every N frames — returns cached result otherwise.

        Returns:
            annotated_frame  — BGR image with bounding boxes drawn
            detections       — list of dicts: {bbox, confidence, label}
        """
        frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
        self._frame_count += 1

        # Only run YOLO every N frames
        if self._frame_count % self.run_every_n_frames == 0:
            results = self.model(
                frame_bgr,
                classes=[self.person_class_id],
                conf=self.confidence,
                verbose=False,
                imgsz=320   # smaller input = much faster, still accurate enough
            )[0]

            self._last_detections = []
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                self._last_detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "label": "person"
                })

        # Always draw cached detections on the fresh frame (smooth display)
        annotated = frame_bgr.copy()
        for det in self._last_detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label_text = f"person {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 255, 0), -1)
            cv2.putText(annotated, label_text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Status bar
        count = len(self._last_detections)
        status = f"Persons detected: {count}"
        color = (0, 255, 0) if count > 0 else (100, 100, 100)
        cv2.putText(annotated, status, (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        return annotated, self._last_detections