"""
hud_overlay.py — On-screen HUD for the drone camera view.
Place in: webots_drone/hud_overlay.py

Draws mode, detection count, altitude, AI decision, and controls
directly onto the cv2 camera frame — no separate window needed.

Usage:
    from hud_overlay import HUD
    hud = HUD()

    # in the loop, before cv2.imshow:
    frame = hud.draw(annotated, mode=mode, detections=detections,
                     altitude=altitude, brain_message="Follow person",
                     follow_mode=follow_mode, scan_mode=scan_mode_active)
    cv2.imshow("Drone's live view", frame)
"""

import cv2
import numpy as np


class HUD:

    # Colours (BGR)
    C_GREEN  = (0, 220, 80)
    C_RED    = (0, 60, 220)
    C_YELLOW = (0, 200, 220)
    C_WHITE  = (240, 240, 240)
    C_DARK   = (20, 20, 20)
    C_BLUE   = (210, 120, 0)
    C_ORANGE = (0, 140, 255)

    MODE_COLOURS = {
        "manual": (200, 200, 200),
        "follow": (0, 220, 80),
        "scan":   (0, 200, 220),
        "ai":     (210, 120, 0),
    }

    def __init__(self):
        self._font = cv2.FONT_HERSHEY_SIMPLEX

    # ------------------------------------------------------------------ #

    def draw(self, frame, mode="manual", detections=None,
             altitude=0.0, brain_message="", follow_mode=False,
             scan_active=False, brain_active=False):
        """
        Draw HUD onto frame (in-place copy returned).
        Call this every loop with the annotated frame from detector.py.
        """
        if detections is None:
            detections = []

        out = frame.copy()
        h, w = out.shape[:2]

        # ---- top bar ----
        self._top_bar(out, w, mode, detections, altitude,
                      follow_mode, scan_active, brain_active)

        # ---- AI message strip ----
        if brain_message:
            self._ai_strip(out, w, h, brain_message)

        # ---- bottom legend ----
        self._bottom_legend(out, w, h)

        # ---- mode badge (top-right) ----
        self._mode_badge(out, w, mode, follow_mode, scan_active, brain_active)

        return out

    # ------------------------------------------------------------------ #
    # Sub-sections                                                         #
    # ------------------------------------------------------------------ #

    def _top_bar(self, frame, w, mode, detections, altitude,
                 follow_mode, scan_active, brain_active):
        # semi-transparent dark bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 28), self.C_DARK, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        n = len(detections)
        det_txt = f"PERSON: {n}" if n == 0 else f"PERSON DETECTED: {n}"
        det_col = self.C_GREEN if n > 0 else (130, 130, 130)
        self._text(frame, det_txt, (8, 18), scale=0.50, color=det_col, thickness=1)

        alt_txt = f"ALT: {altitude:.1f}m"
        self._text(frame, alt_txt, (180, 18), scale=0.50, color=self.C_WHITE, thickness=1)

        if brain_active:
            self._text(frame, "AI ON", (280, 18), scale=0.50, color=self.C_ORANGE, thickness=1)

    def _ai_strip(self, frame, w, h, message):
        overlay = frame.copy()
        y0, y1 = h - 48, h - 28
        cv2.rectangle(overlay, (0, y0), (w, y1), (30, 60, 30), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        self._text(frame, f"AI: {message}", (8, h - 33),
                   scale=0.46, color=self.C_GREEN, thickness=1)

    def _bottom_legend(self, frame, w, h):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 26), (w, h), self.C_DARK, -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        legend = "ARROWS:fly  W/S:alt  A/D:yaw  F:follow  B:AI  X:scan  SAY:follow|scan|stop"
        self._text(frame, legend, (6, h - 8),
                   scale=0.36, color=(170, 170, 170), thickness=1)

    def _mode_badge(self, frame, w, mode, follow_mode, scan_active, brain_active):
        if brain_active:
            label, col = "AI MODE", self.C_ORANGE
        elif follow_mode:
            label, col = "FOLLOW", self.C_GREEN
        elif scan_active:
            label, col = "SCANNING", self.C_YELLOW
        else:
            label, col = "MANUAL", (160, 160, 160)

        (tw, th), _ = cv2.getTextSize(label, self._font, 0.52, 1)
        x0 = w - tw - 12
        overlay = frame.copy()
        cv2.rectangle(overlay, (x0 - 4, 4), (w - 4, 26), self.C_DARK, -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        self._text(frame, label, (x0, 20), scale=0.52, color=col, thickness=1)

    # ------------------------------------------------------------------ #

    def _text(self, frame, text, pos, scale=0.5, color=(255, 255, 255), thickness=1):
        cv2.putText(frame, text, pos, self._font, scale, color, thickness, cv2.LINE_AA)