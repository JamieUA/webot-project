"""
controllers/path_planner/path_planner.py  (also used as webots_drone/path_planner.py)

Autonomous waypoint patrol for the parking lot drone.
Covers all 3 rows (A, B, C) in a lawnmower pattern.
Receives supervisor alerts via channel 9 and switches to TRACK mode.

Patrol route:
  Start (charging pad) → Row A pass → Row B pass → Row C pass → repeat
  Each row: fly along X axis at the row's Y, pause at each slot to inspect.
"""

import math
import json

# ── Patrol waypoints ─────────────────────────────────────────────────────────
# (x, y, altitude, label)
PATROL_WAYPOINTS = [
    # Take off from charging pad
    ( 30,    0,  18, "TAKEOFF"),
    # Row A sweep — left to right
    (-18,   28,  15, "ROW_A_START"),
    ( -6,   28,  15, "ROW_A_MID"),
    ( 19,   28,  15, "ROW_A_END"),
    # Cross to Row B
    ( 19,    0,  15, "ROW_B_START"),
    # Row B sweep — right to left
    (  6,    0,  15, "ROW_B_MID"),
    (-18,    0,  15, "ROW_B_END"),
    # Cross to Row C
    (-18,  -28,  15, "ROW_C_START"),
    # Row C sweep — left to right
    (  6,  -28,  15, "ROW_C_MID"),
    ( 19,  -28,  15, "ROW_C_END"),
    # Return to centre hover
    (  0,    0,  18, "CENTRE"),
]

WAYPOINT_THRESHOLD = 3.0    # metres — close enough to count as "reached"
HOVER_STEPS        = 60     # steps to hover at each waypoint (~0.5s inspection)


class PatrolPlanner:
    """
    Implements the waypoint patrol loop for the parking drone.
    Call .step() every simulation loop iteration.
    """

    def __init__(self):
        self._wp_idx      = 0
        self._hover_count = 0
        self._mode        = "PATROL"   # PATROL | TRACK | RETURN
        self._track_target= None       # [x, y] of theft car
        self._alert_data  = None
        print("[Patrol] Waypoint patrol ready. Points:", len(PATROL_WAYPOINTS))

    # ── Public API ───────────────────────────────────────────────────────────

    def receive_alert(self, alert_data: dict):
        """Called when supervisor sends a theft alert."""
        if alert_data.get("THEFT_ALERT") and alert_data.get("alerts"):
            car_pos = alert_data["alerts"][0]["position"]
            self._track_target = car_pos
            self._alert_data   = alert_data
            self._mode         = "TRACK"
            print(f"[Patrol] THEFT ALERT → switching to TRACK mode. Target: {car_pos}")

    def step(self, current_pos: list, limits) -> list:
        """
        Args:
            current_pos: [x, y, z] drone position
            limits: controller.limits from WebotsSimulation

        Returns:
            [roll, pitch, yaw, altitude] action
        """
        if self._mode == "TRACK":
            return self._track_step(current_pos, limits)
        return self._patrol_step(current_pos, limits)

    def resume_patrol(self):
        """Call after theft vehicle is lost to resume patrol."""
        self._mode        = "PATROL"
        self._track_target = None
        print("[Patrol] Resuming patrol route.")

    @property
    def mode(self):
        return self._mode

    @property
    def current_waypoint_label(self):
        if self._wp_idx < len(PATROL_WAYPOINTS):
            return PATROL_WAYPOINTS[self._wp_idx][3]
        return "DONE"

    # ── Internal ─────────────────────────────────────────────────────────────

    def _patrol_step(self, pos, limits):
        wp = PATROL_WAYPOINTS[self._wp_idx]
        tx, ty, tz, label = wp

        dx = tx - pos[0]
        dy = ty - pos[1]
        dz = tz - pos[2]
        dist_xy = math.sqrt(dx*dx + dy*dy)

        if dist_xy < WAYPOINT_THRESHOLD and abs(dz) < 2.0:
            # At waypoint — hover briefly then advance
            self._hover_count += 1
            if self._hover_count >= HOVER_STEPS:
                self._hover_count = 0
                self._wp_idx      = (self._wp_idx + 1) % len(PATROL_WAYPOINTS)
                print(f"[Patrol] → next waypoint: {PATROL_WAYPOINTS[self._wp_idx][3]}")
            return [0., 0., 0., 0.]   # hover

        return self._navigate_to(pos, tx, ty, tz, limits)

    def _track_step(self, pos, limits):
        """Fly toward the theft car's last known position."""
        if self._track_target is None:
            return [0., 0., 0., 0.]
        tx, ty = self._track_target
        tz     = 10.0   # lower altitude for tracking
        return self._navigate_to(pos, tx, ty, tz, limits)

    def _navigate_to(self, pos, tx, ty, tz, limits):
        """Simple proportional navigation toward target."""
        dx   = tx - pos[0]
        dy   = ty - pos[1]
        dz   = tz - pos[2]
        dist = math.sqrt(dx*dx + dy*dy)

        MAX_PITCH = limits[1][1] * 0.5   # 50% max pitch — gentle
        MAX_ROLL  = limits[1][0] * 0.4
        MAX_ALT   = limits[1][3] * 0.3

        pitch    = MAX_PITCH if dy > 1.0 else (-MAX_PITCH if dy < -1.0 else dy * MAX_PITCH / 2)
        roll     = MAX_ROLL  if dx > 1.0 else (-MAX_ROLL  if dx < -1.0 else dx * MAX_ROLL  / 2)
        altitude = MAX_ALT   if dz > 1.0 else (-MAX_ALT   if dz < -1.0 else dz * MAX_ALT   / 2)

        return [roll, pitch, 0., altitude]
