"""
follower.py — Visual person-following logic for the Webots drone.

v3 — Crash-safe edition:
  - Much lower gains (drone moves gently, no flip/crash)
  - Pitch capped at 30% of max (was 100%)
  - Roll capped at 40% of max
  - Altitude capped at 25% of max
  - Dead zone widened so small detections don't trigger movement
  - Size-based approach is optional (off by default) — the main
    crash cause was aggressive pitch when person filled the frame
"""


class PersonFollower:

    def __init__(self, frame_w=400, frame_h=240,
                 target_box_ratio=0.10,   # person fills 10% of frame = good dist
                 dead_zone=0.15):         # 15% dead band = no jitter
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.target_box_ratio = target_box_ratio
        self.dead_zone = dead_zone
        self.frame_cx = frame_w / 2.0
        self.frame_cy = frame_h / 2.0

        # Gain caps — fraction of controller limit to use (0.0–1.0)
        # LOW values = gentle, safe. Increase slowly if you want faster tracking.
        self.ROLL_GAIN     = 0.35   # left/right centering
        self.PITCH_GAIN    = 0.25   # approach/retreat  ← was 1.0, crash cause!
        self.ALT_GAIN      = 0.20   # up/down centering
        self.APPROACH_ON   = True   # set False to disable pitch-to-approach

    def compute_action(self, detection, limits):
        """
        Return [roll, pitch, yaw, altitude] to keep person centered.
        All values are gently clamped — will not flip the drone.
        """
        x1, y1, x2, y2 = detection["bbox"]

        box_cx = (x1 + x2) / 2.0
        box_cy = (y1 + y2) / 2.0
        box_w  = x2 - x1

        # Errors in [-1 .. +1]
        error_x    = (box_cx - self.frame_cx) / self.frame_cx    # + = person right
        error_y    = (box_cy - self.frame_cy) / self.frame_cy    # + = person below
        size_error = self.target_box_ratio - (box_w / self.frame_w)  # + = too far

        roll = pitch = yaw = altitude = 0.0

        # ---- ROLL — center person left/right ----
        if abs(error_x) > self.dead_zone:
            roll = limits[1][0] * error_x * self.ROLL_GAIN
            roll = float(max(limits[0][0], min(limits[1][0], roll)))

        # ---- PITCH — approach / retreat to maintain distance ----
        if self.APPROACH_ON and abs(size_error) > self.dead_zone * 0.5:
            pitch = limits[1][1] * size_error * self.PITCH_GAIN
            pitch = float(max(limits[0][1], min(limits[1][1], pitch)))

        # ---- ALTITUDE — center person vertically ----
        if abs(error_y) > self.dead_zone:
            # person below center (error_y > 0) → descend (negative alt)
            altitude = limits[0][3] * error_y * self.ALT_GAIN
            altitude = float(max(limits[0][3], min(limits[1][3], altitude)))

        return [roll, pitch, yaw, altitude]

    def status(self, detection):
        x1, y1, x2, y2 = detection["bbox"]
        box_cx = (x1 + x2) / 2.0
        box_w  = x2 - x1
        ex = (box_cx - self.frame_cx) / self.frame_cx
        se = self.target_box_ratio - (box_w / self.frame_w)

        h = "centered"
        if   ex >  self.dead_zone: h = "person RIGHT"
        elif ex < -self.dead_zone: h = "person LEFT"

        d = "good distance"
        if   se >  self.dead_zone * 0.5: d = "too far → closer"
        elif se < -self.dead_zone * 0.5: d = "too close → back"

        return f"[Follow] {h} | {d} | conf={detection['confidence']:.0%}"