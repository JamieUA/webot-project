"""
follower.py — Smooth person-following for the Webots drone.

Fixes:
  - Uses YAW to turn toward person (not roll) — eliminates left/right swinging
  - Exponential smoothing on all outputs — no sudden jerks
  - Larger dead zone so tiny detection jitter doesn't move the drone
  - Pitch (approach) is slow and only activates when clearly too far/close
  - Roll completely disabled — yaw handles all left/right tracking
"""


class PersonFollower:

    def __init__(self, frame_w=400, frame_h=240,
                 target_box_ratio=0.15,   # person fills 15% of frame = ideal distance
                 dead_zone=0.12):         # 12% dead band — ignore small errors
        self.frame_w  = frame_w
        self.frame_h  = frame_h
        self.frame_cx = frame_w / 2.0
        self.frame_cy = frame_h / 2.0
        self.target_box_ratio = target_box_ratio
        self.dead_zone = dead_zone

        # Gains — fraction of controller limit to apply
        self.YAW_GAIN    = 0.30   # turn toward person left/right
        self.PITCH_GAIN  = 0.15   # approach/retreat — very gentle
        self.ALT_GAIN    = 0.15   # up/down centering — very gentle
        self.APPROACH_ON = True

        # Smoothing — higher = smoother but slower response (0.0–1.0)
        # output = alpha * previous + (1-alpha) * new
        self.SMOOTH = 0.72

        # Internal smoothed state
        self._yaw  = 0.0
        self._pitch = 0.0
        self._alt   = 0.0

    def compute_action(self, detection, limits):
        x1, y1, x2, y2 = detection["bbox"]

        box_cx = (x1 + x2) / 2.0
        box_cy = (y1 + y2) / 2.0
        box_w  = x2 - x1

        # Normalised errors in [-1 .. +1]
        error_x    = (box_cx - self.frame_cx) / self.frame_cx   # + = person right of centre
        error_y    = (box_cy - self.frame_cy) / self.frame_cy   # + = person below centre
        size_error = self.target_box_ratio - (box_w / self.frame_w)  # + = too far away

        # ---- YAW — turn to face person left/right ----
        # No roll at all. Yaw rotates the whole drone to face the target.
        raw_yaw = 0.0
        if abs(error_x) > self.dead_zone:
            # error_x > 0 means person is RIGHT → yaw right → positive yaw
            raw_yaw = limits[1][2] * error_x * self.YAW_GAIN
            raw_yaw = float(max(limits[0][2], min(limits[1][2], raw_yaw)))

        # ---- PITCH — approach when too far, back off when too close ----
        raw_pitch = 0.0
        if self.APPROACH_ON and abs(size_error) > self.dead_zone * 0.6:
            raw_pitch = limits[1][1] * size_error * self.PITCH_GAIN
            raw_pitch = float(max(limits[0][1], min(limits[1][1], raw_pitch)))

        # ---- ALTITUDE — keep person vertically centred ----
        raw_alt = 0.0
        if abs(error_y) > self.dead_zone:
            # person below centre (error_y > 0) → descend
            raw_alt = limits[0][3] * error_y * self.ALT_GAIN
            raw_alt = float(max(limits[0][3], min(limits[1][3], raw_alt)))

        # ---- Exponential smoothing — kills oscillation ----
        self._yaw   = self.SMOOTH * self._yaw   + (1 - self.SMOOTH) * raw_yaw
        self._pitch = self.SMOOTH * self._pitch + (1 - self.SMOOTH) * raw_pitch
        self._alt   = self.SMOOTH * self._alt   + (1 - self.SMOOTH) * raw_alt

        # roll = 0.0 always — yaw handles left/right
        return [0.0, self._pitch, self._yaw, self._alt]

    def reset(self):
        """Call when switching into follow mode to clear smoothing state."""
        self._yaw   = 0.0
        self._pitch = 0.0
        self._alt   = 0.0

    def status(self, detection):
        x1, y1, x2, y2 = detection["bbox"]
        box_cx = (x1 + x2) / 2.0
        box_w  = x2 - x1
        ex = (box_cx - self.frame_cx) / self.frame_cx
        se = self.target_box_ratio - (box_w / self.frame_w)

        h = "centered"
        if   ex >  self.dead_zone: h = "person RIGHT → yawing"
        elif ex < -self.dead_zone: h = "person LEFT  → yawing"

        d = "good distance"
        if   se >  self.dead_zone * 0.6: d = "too far → moving closer"
        elif se < -self.dead_zone * 0.6: d = "too close → backing off"

        return f"[Follow] {h} | {d} | conf={detection['confidence']:.0%}"
