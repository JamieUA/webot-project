"""
webots_drone/hud_overlay.py — Parking guard HUD overlay.

Adds parking-specific panels: slot count, theft alert, patrol waypoint.
Fully backwards-compatible with the existing HUD() call in webots_simulation.py.
"""

import cv2
import numpy as np


class HUD:

    C_GREEN  = (0, 220, 80)
    C_RED    = (0, 60, 220)
    C_YELLOW = (0, 200, 220)
    C_WHITE  = (240, 240, 240)
    C_DARK   = (20, 20, 20)
    C_ORANGE = (0, 140, 255)
    C_CYAN   = (220, 200, 0)

    MODE_COLOURS = {
        "manual":  (200, 200, 200),
        "follow":  (0, 220, 80),
        "scan":    (0, 200, 220),
        "patrol":  (0, 200, 220),
        "track":   (0, 60, 220),
        "ai":      (210, 120, 0),
    }

    def __init__(self):
        self._font = cv2.FONT_HERSHEY_SIMPLEX

    def draw(self, frame, mode="manual", detections=None,
             altitude=0.0, brain_message="", follow_mode=False,
             scan_active=False, brain_active=False,
             # parking-specific extras (all optional)
             parking_report=None, waypoint_label="", theft_alert=False):

        if detections is None:
            detections = []

        out = frame.copy()
        h, w = out.shape[:2]

        self._top_bar(out, w, mode, detections, altitude, follow_mode, scan_active, brain_active)
        self._parking_panel(out, w, h, parking_report, waypoint_label, theft_alert)

        if brain_message:
            self._ai_strip(out, w, h, brain_message)

        self._bottom_legend(out, w, h)
        self._mode_badge(out, w, mode, follow_mode, scan_active, brain_active, theft_alert)

        return out

    # ── sections ─────────────────────────────────────────────────────────────

    def _top_bar(self, frame, w, mode, detections, altitude,
                 follow_mode, scan_active, brain_active):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0,0),(w,28), self.C_DARK, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        n       = len(detections)
        det_txt = f"PERSON DETECTED: {n}" if n > 0 else "NO PERSON"
        det_col = (0,0,220) if n > 0 else (130,130,130)
        self._text(frame, det_txt, (8,18), 0.50, det_col)
        self._text(frame, f"ALT: {altitude:.1f}m", (200,18), 0.50, self.C_WHITE)
        if brain_active:
            self._text(frame, "AI ON", (310,18), 0.50, self.C_ORANGE)

    def _parking_panel(self, frame, w, h, report, waypoint_label, theft_alert):
        """Right-side panel: parking stats."""
        if report is None:
            return
        px = w - 150
        overlay = frame.copy()
        cv2.rectangle(overlay, (px-4, 32),(w, 110), self.C_DARK, -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        total     = report.get("total",      25)
        occupied  = report.get("occupied",    0)
        available = report.get("available",  25)
        alerts    = report.get("alerts",      [])

        self._text(frame, "PARKING STATUS",        (px, 46), 0.38, self.C_CYAN)
        self._text(frame, f"Total  : {total}",     (px, 62), 0.38, self.C_WHITE)
        self._text(frame, f"Parked : {occupied}",  (px, 76), 0.38, self.C_YELLOW)
        self._text(frame, f"Free   : {available}", (px, 90), 0.38, self.C_GREEN)
        if alerts:
            self._text(frame, "!! THEFT !!",       (px,106), 0.40, (0,0,220))

        if waypoint_label:
            self._text(frame, f"WP: {waypoint_label}", (px,122), 0.36, (160,160,160))

    def _ai_strip(self, frame, w, h, message):
        overlay = frame.copy()
        y0,y1 = h-48, h-28
        cv2.rectangle(overlay,(0,y0),(w,y1),(30,60,30),-1)
        cv2.addWeighted(overlay,0.65,frame,0.35,0,frame)
        self._text(frame, f"AI: {message}", (8,h-33), 0.46, self.C_GREEN)

    def _bottom_legend(self, frame, w, h):
        overlay = frame.copy()
        cv2.rectangle(overlay,(0,h-26),(w,h), self.C_DARK,-1)
        cv2.addWeighted(overlay,0.55,frame,0.45,0,frame)
        legend = "W/S:alt  ARROWS:fly  A/D:yaw  F:follow  X:patrol  P:photo  Q:quit"
        self._text(frame, legend, (6,h-8), 0.36, (170,170,170))

    def _mode_badge(self, frame, w, mode, follow_mode, scan_active,
                    brain_active, theft_alert):
        if theft_alert:
            label, col = "!! THEFT TRACK !!", (0,0,220)
        elif brain_active:
            label, col = "AI MODE", self.C_ORANGE
        elif follow_mode:
            label, col = "FOLLOW", self.C_GREEN
        elif scan_active:
            label, col = "PATROL", self.C_YELLOW
        else:
            label, col = "MANUAL", (160,160,160)

        (tw,th),_ = cv2.getTextSize(label, self._font, 0.52, 1)
        x0 = w - tw - 12
        overlay = frame.copy()
        cv2.rectangle(overlay,(x0-4,4),(w-4,26), self.C_DARK,-1)
        cv2.addWeighted(overlay,0.6,frame,0.4,0,frame)
        self._text(frame, label, (x0,20), 0.52, col)

    def _text(self, frame, text, pos, scale=0.5, color=(255,255,255), thickness=1):
        cv2.putText(frame, text, pos, self._font, scale, color, thickness, cv2.LINE_AA)
