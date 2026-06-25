"""
pedestrian_controller.py — Hiking scenario pedestrian controller.

Each hiker is identified by their Webots node name (set in the .wbt file):
  name "hiker_alice"  ->  alice profile
  name "hiker_bob"    ->  bob profile
  etc.

controllerArgs must be non-empty to activate the controller inside the
Pedestrian PROTO — the actual value is not used here.
"""

from controller import Supervisor
import math

HIKER_PROFILES = {
    "alice":   {"speed": 1.0,  "offset_y":  0.0, "stops_at": 1.0},
    "bob":     {"speed": 0.9,  "offset_y":  2.0, "stops_at": 1.0},
    "charlie": {"speed": 0.95, "offset_y": -2.0, "stops_at": 1.0},
    "diana":   {"speed": 0.7,  "offset_y": -3.0, "stops_at": 1.0},  # slower, fatigued
    "eve":     {"speed": 0.85, "offset_y":  3.0, "stops_at": 0.6},  # gets lost at 60%
}

def main():
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())

    # Identify this hiker from their node name e.g. "hiker_alice" -> "alice"
    raw_name = robot.getName()   # e.g. "hiker_alice"
    name = raw_name.replace("hiker_", "").strip().lower()
    profile = HIKER_PROFILES.get(name, {"speed": 0.8, "offset_y": 0.0, "stops_at": 1.0})

    speed    = profile["speed"]
    stops_at = profile["stops_at"]

    self_node = robot.getSelf()
    if self_node is None:
        print(f"[Hiker:{name}] ERROR: getSelf() returned None")
        while robot.step(timestep) != -1:
            pass
        return

    trans_field = self_node.getField("translation")
    rot_field   = self_node.getField("rotation")

    if trans_field is None:
        print(f"[Hiker:{name}] ERROR: no translation field")
        while robot.step(timestep) != -1:
            pass
        return

    start_pos = trans_field.getSFVec3f()
    print(f"[Hiker:{name}] Ready at {[round(v,2) for v in start_pos]}, speed={speed} m/s")

    SIM_DURATION = 300.0  # 5 minutes
    sim_start    = robot.getTime()
    walk_phase   = 0.0
    stopped      = False

    while robot.step(timestep) != -1:
        now      = robot.getTime()
        elapsed  = now - sim_start
        progress = min(elapsed / SIM_DURATION, 1.0)

        if progress >= stops_at:
            if not stopped:
                print(f"[Hiker:{name}] Stopped — separated from group")
                stopped = True
            continue

        dt  = timestep / 1000.0
        pos = trans_field.getSFVec3f()

        # Walk forward along X axis
        new_x = pos[0] + speed * dt
        trans_field.setSFVec3f([new_x, pos[1], pos[2]])

        # Simple lean animation
        walk_phase += speed * dt * 2.5
        lean = math.sin(walk_phase) * 0.04
        rot_field.setSFRotation([0, 0, 1, lean])

    print(f"[Hiker:{name}] Simulation ended.")

main()