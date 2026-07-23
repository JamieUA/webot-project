"""
webots_drone/parking_detector.py  (also used as parking_detector.py in project root)

Detects cars and intruders/persons using YOLOv8.
Reports per-slot occupancy, total count, and theft alerts.
"""

import cv2
import numpy as np
from ultralytics import YOLO

TOTAL_SLOTS = 25

class ParkingDetector:

    CAR_CLASSES  = {2: "car", 5: "bus", 7: "truck"}
    PERSON_CLASS = 0

    def __init__(self, confidence=0.35, run_every_n_frames=5):
        print("Loading YOLOv8 model... ", end="", flush=True)
        self.model      = YOLO("yolov8n.pt")
        self.confidence = confidence
        self.run_every_n_frames = run_every_n_frames
        self._frame_count  = 0
        self._last_cars    = []
        self._last_persons = []
        print("OK")

    def detect(self, frame_bgra):
        """
        Returns:
            annotated  — BGR frame with all boxes drawn
            report     — dict: car_count, available_slots, persons, alert
        """
        frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
        self._frame_count += 1

        if self._frame_count % self.run_every_n_frames == 0:
            results = self.model(
                frame_bgr,
                classes=list(self.CAR_CLASSES.keys()) + [self.PERSON_CLASS],
                conf=self.confidence,
                verbose=False,
                imgsz=320
            )[0]

            self._last_cars    = []
            self._last_persons = []
            for box in results.boxes:
                cls    = int(box.cls[0])
                conf   = float(box.conf[0])
                coords = tuple(map(int, box.xyxy[0].tolist()))
                obj    = {"bbox": coords, "confidence": conf,
                          "label": self.CAR_CLASSES.get(cls, "person")}
                if cls in self.CAR_CLASSES:
                    self._last_cars.append(obj)
                else:
                    self._last_persons.append(obj)

        # Draw
        annotated = frame_bgr.copy()
        for det in self._last_cars:
            x1,y1,x2,y2 = det["bbox"]
            cv2.rectangle(annotated, (x1,y1),(x2,y2), (0,200,255), 2)
            cv2.putText(annotated, f"{det['label']} {det['confidence']:.0%}",
                        (x1+2,y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,200,255), 1)

        for det in self._last_persons:
            x1,y1,x2,y2 = det["bbox"]
            cv2.rectangle(annotated, (x1,y1),(x2,y2), (0,0,255), 2)
            cv2.putText(annotated, f"!! PERSON {det['confidence']:.0%}",
                        (x1+2,y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)

        # Stats HUD
        cars_seen = len(self._last_cars)
        available = max(0, TOTAL_SLOTS - cars_seen)
        alert     = len(self._last_persons) > 0

        cv2.putText(annotated, f"Cars: {cars_seen}  Free: {available}/{TOTAL_SLOTS}",
                    (8,18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,220,255), 2)
        if alert:
            cv2.putText(annotated, "!! INTRUDER / THEFT ALERT !!",
                        (8,44), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,255), 2)

        return annotated, {
            "cars":            self._last_cars,
            "persons":         self._last_persons,
            "car_count":       cars_seen,
            "available_slots": available,
            "alert":           alert,
        }


# Backwards-compat alias used by webots_simulation.py
class PersonDetector(ParkingDetector):
    def detect(self, frame_bgra):
        annotated, report = super().detect(frame_bgra)
        return annotated, report["persons"]
