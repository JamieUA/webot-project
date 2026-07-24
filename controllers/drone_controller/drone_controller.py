#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autonomous Parking Guard Drone - self-contained Mavic 2 Pro controller.

This controller flies WITHOUT any external remote control. It implements the
full parking-surveillance role:

  * Autonomous take-off to patrol altitude.
  * Patrol path that sweeps over the three parking rows in a loop.
  * Parking monitoring / vehicle counting using ground-truth occupancy data
    streamed from the ParkingSupervisor on radio channel 9.
  * Security guard: on a theft / suspicious-movement alert it locks onto the
    moving vehicle and tracks it (keeping it under the camera).
  * Basic obstacle awareness using the onboard forward sonar sensors.
  * A live text HUD printed to the Webots console.

Flight stabilization uses the reference Mavic 2 Pro PD gains and motor mixing,
so no numpy / simple_pid / external packages are required.
"""

import math
import json
from controller import Robot


def clamp(value, low, high):
    return max(low, min(value, high))


def normalize_angle(a):
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


class ParkingGuardDrone(Robot):
    # Reference Mavic 2 Pro flight gains.
    K_VERTICAL_THRUST = 68.5
    K_VERTICAL_OFFSET = 0.6
    K_VERTICAL_P = 3.0
    K_ROLL_P = 50.0
    K_PITCH_P = 30.0

    # Mission parameters.
    PATROL_ALTITUDE = 8.0
    TRACK_ALTITUDE = 6.0
    WAYPOINT_RADIUS = 2.0     # m, "arrived" threshold
    CRUISE_PITCH = 2.0        # forward tilt magnitude (negative pitch == forward)
    YAW_GAIN = 1.5
    HUD_PERIOD = 3.0          # s

    def __init__(self):
        super().__init__()
        self.timestep = int(self.getBasicTimeStep())

        # --- Sensors ---
        self.imu = self.getDevice("inertial unit")
        self.imu.enable(self.timestep)
        self.gps = self.getDevice("gps")
        self.gps.enable(self.timestep)
        self.gyro = self.getDevice("gyro")
        self.gyro.enable(self.timestep)
        self.compass = self.getDevice("compass")
        self.compass.enable(self.timestep)
        self.camera = self.getDevice("camera")
        self.camera.enable(self.timestep)

        # --- Camera gimbal ---
        self.cam_roll = self.getDevice("camera roll")
        self.cam_pitch = self.getDevice("camera pitch")

        # --- LEDs ---
        self.led_fl = self.getDevice("front left led")
        self.led_fr = self.getDevice("front right led")

        # --- Motors ---
        motor_names = ["front left propeller", "front right propeller",
                       "rear left propeller", "rear right propeller"]
        self.motors = []
        for name in motor_names:
            m = self.getDevice(name)
            m.setPosition(float("inf"))
            m.setVelocity(1.0)
            self.motors.append(m)

        # --- Forward obstacle sonars ---
        self.dist_sensors = []
        for name in ["front left dist sonar", "front right dist sonar"]:
            s = self.getDevice(name)
            if s is not None:
                s.enable(self.timestep)
                self.dist_sensors.append(s)

        # --- Comms: supervisor status on channel 9 ---
        self.receiver = self.getDevice("SupervisorReceiver")
        if self.receiver is not None:
            self.receiver.enable(self.timestep)
        self.alert_emitter = self.getDevice("AlertEmitter")

        # --- Patrol path over the three parking rows (x, y) ---
        self.waypoints = [
            (11.0, 18.0), (-14.0, 18.0),      # sweep row A
            (-14.0, 0.5), (11.0, 0.5),        # sweep row B
            (11.0, -17.0), (-14.0, -17.0),    # sweep row C
            (30.0, 0.0),                      # return toward charging pad
        ]
        self.wp_index = 0

        # --- State ---
        self.flight_mode = "TAKEOFF"   # TAKEOFF -> PATROL -> TRACK
        self.target_altitude = self.PATROL_ALTITUDE
        self.stats = None
        self.theft_target = None
        self.last_hud = -1e9
        self.alert_announced = False

    # ------------------------------------------------------------------
    def read_supervisor(self):
        if self.receiver is None:
            return
        while self.receiver.getQueueLength() > 0:
            try:
                self.stats = json.loads(self.receiver.getData().decode("utf-8"))
                if self.stats.get("THEFT_ALERT") and self.stats.get("alerts"):
                    a = self.stats["alerts"][0]
                    self.theft_target = (a["position"][0], a["position"][1])
                    if not self.alert_announced:
                        self.alert_announced = True
                        print("\n" + "!" * 54)
                        print(f"  SECURITY ALERT: suspicious movement near {a['car']}"
                              f" (slot {a['slot']})")
                        print(f"  Locking on target at {a['position']} - tracking started")
                        print("!" * 54)
                        if self.alert_emitter is not None:
                            self.alert_emitter.send(json.dumps(
                                {"alert": "theft", "target": a}).encode("utf-8"))
                    self.flight_mode = "TRACK"
            except Exception as e:
                print(f"[Drone] status decode error: {e}")
            self.receiver.nextPacket()

    def obstacle_ahead(self):
        # Sonar value scales with distance (~100 per metre); < 200 means < ~2 m.
        for s in self.dist_sensors:
            if 0.0 < s.getValue() < 200.0:
                return True
        return False

    # ------------------------------------------------------------------
    def navigate(self, x, y, yaw):
        """Return (roll_dist, pitch_dist, yaw_dist) toward the active goal."""
        if self.flight_mode == "TRACK" and self.theft_target is not None:
            goal = self.theft_target
        else:
            goal = self.waypoints[self.wp_index]

        dx = goal[0] - x
        dy = goal[1] - y
        dist = math.hypot(dx, dy)

        # Advance to next patrol waypoint once reached.
        if self.flight_mode == "PATROL" and dist < self.WAYPOINT_RADIUS:
            self.wp_index = (self.wp_index + 1) % len(self.waypoints)

        desired_yaw = math.atan2(dy, dx)
        yaw_error = normalize_angle(desired_yaw - yaw)
        yaw_dist = clamp(self.YAW_GAIN * yaw_error, -1.3, 1.3)

        pitch_dist = 0.0
        if abs(yaw_error) < 0.5 and dist > self.WAYPOINT_RADIUS:
            speed_scale = clamp(dist / 10.0, 0.2, 1.0)
            pitch_dist = -self.CRUISE_PITCH * speed_scale   # negative == forward
            if self.obstacle_ahead():
                pitch_dist = 0.0                            # hold if blocked ahead
        return 0.0, pitch_dist, yaw_dist

    # ------------------------------------------------------------------
    def which_row(self, y):
        if y > 9.0:
            return "A"
        if y > -8.0:
            return "B"
        return "C"

    def print_hud(self, x, y, alt):
        if self.stats is None:
            print(f"[Drone] t={self.getTime():5.1f}s pos=({x:5.1f},{y:5.1f},{alt:4.1f}) "
                  f"mode={self.flight_mode}  (waiting for parking data...)")
            return
        s = self.stats
        print("\n============ PARKING STATUS (live) ============")
        print(f"  Time:          {s.get('time')} s")
        print(f"  Total Slots:   {s.get('total')}")
        print(f"  Occupied:      {s.get('occupied')}")
        print(f"  Available:     {s.get('available')}")
        print(f"  Vehicles:      {s.get('vehicles')}")
        rows = s.get("rows", {})
        if rows:
            summary = "  ".join(
                f"{r}:{rows[r]['occupied']}/{rows[r]['total']}" for r in sorted(rows))
            print(f"  Per-row:       {summary}")
        print(f"  Drone:         mode={self.flight_mode} over row {self.which_row(y)} "
              f"pos=({x:5.1f},{y:5.1f},{alt:4.1f})")
        if s.get("THEFT_ALERT"):
            print(f"  *** SECURITY ALERT: {len(s.get('alerts', []))} event(s) ***")
            for a in s.get("alerts", []):
                print(f"      - {a['car']} moved {a['distance']} m from slot {a['slot']}"
                      f" -> now at {a['position']}")
        print("===============================================")

    # ------------------------------------------------------------------
    def run(self):
        print("[Drone] Autonomous Parking Guard online. Taking off...")
        while self.step(self.timestep) != -1:
            t = self.getTime()
            self.read_supervisor()

            roll, pitch, yaw = self.imu.getRollPitchYaw()
            x, y, altitude = self.gps.getValues()
            roll_vel, pitch_vel, _ = self.gyro.getValues()

            # Gimbal stabilization.
            self.cam_roll.setPosition(-0.115 * roll_vel)
            self.cam_pitch.setPosition(-0.1 * pitch_vel)

            # Status LEDs.
            self.led_fl.set(int(t) % 2)
            self.led_fr.set((int(t) + 1) % 2)

            roll_dist = pitch_dist = yaw_dist = 0.0

            if self.flight_mode == "TAKEOFF":
                self.target_altitude = self.PATROL_ALTITUDE
                if altitude > self.PATROL_ALTITUDE - 0.5:
                    self.flight_mode = "PATROL"
                    print("[Drone] Patrol altitude reached - beginning patrol sweep.")
            elif self.flight_mode == "PATROL":
                self.target_altitude = self.PATROL_ALTITUDE
                roll_dist, pitch_dist, yaw_dist = self.navigate(x, y, yaw)
            elif self.flight_mode == "TRACK":
                self.target_altitude = self.TRACK_ALTITUDE
                roll_dist, pitch_dist, yaw_dist = self.navigate(x, y, yaw)
                # Resume patrol if the alert clears.
                if self.stats is not None and not self.stats.get("THEFT_ALERT"):
                    self.flight_mode = "PATROL"
                    self.alert_announced = False
                    print("[Drone] Area secured - resuming patrol.")

            # Attitude stabilization + Mavic 2 Pro motor mixing.
            roll_input = self.K_ROLL_P * clamp(roll, -1.0, 1.0) + roll_vel + roll_dist
            pitch_input = self.K_PITCH_P * clamp(pitch, -1.0, 1.0) + pitch_vel + pitch_dist
            yaw_input = yaw_dist
            clamped_diff_alt = clamp(
                self.target_altitude - altitude + self.K_VERTICAL_OFFSET, -1.0, 1.0)
            vertical_input = self.K_VERTICAL_P * clamped_diff_alt ** 3.0

            fl = self.K_VERTICAL_THRUST + vertical_input - roll_input + pitch_input - yaw_input
            fr = self.K_VERTICAL_THRUST + vertical_input + roll_input + pitch_input + yaw_input
            rl = self.K_VERTICAL_THRUST + vertical_input - roll_input - pitch_input + yaw_input
            rr = self.K_VERTICAL_THRUST + vertical_input + roll_input - pitch_input - yaw_input

            self.motors[0].setVelocity(fl)
            self.motors[1].setVelocity(-fr)
            self.motors[2].setVelocity(-rl)
            self.motors[3].setVelocity(rr)

            # Live HUD.
            if t - self.last_hud >= self.HUD_PERIOD:
                self.last_hud = t
                self.print_hud(x, y, altitude)


if __name__ == "__main__":
    ParkingGuardDrone().run()