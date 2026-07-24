"""
controllers/supervisor_controller/supervisor_controller.py

Ground-truth parking monitor that feeds the autonomous guard drone.

The ParkingSupervisor Robot node in parking_world.wbt provides:
  children [ Emitter { name "emitter" channel 9 } ]

This controller:
  - Maps all 24 parking slots (3 rows x 8 bays) using the CURRENT car layout.
  - Monitors every car's position each timestep.
  - Simulates a theft at t = THEFT_TRIGGER by driving THEFT_CAR toward the exit.
  - Detects any car that leaves its baseline slot (theft / suspicious movement).
  - Broadcasts a JSON status packet on channel 9 (occupancy, per-row counts,
    per-slot map, alerts, drone position) that the drone consumes to build its
    HUD and to trigger target tracking.
"""

from controller import Supervisor
import json
import math

# --- Parking layout (matches the fixed car positions in parking_world.wbt) ---
# Bay-center Y for each row and the 8 bay-center X values.
ROWS = [("A", 18.0), ("B", 0.5), ("C", -17.0)]
X_POS = [-13.25, -9.75, -6.25, -2.75, 0.75, 4.25, 7.75, 11.25]

SLOT_DEFS = []
for _row_label, _y in ROWS:
    for _i, _x in enumerate(X_POS):
        SLOT_DEFS.append({"id": f"{_row_label}{_i + 1}", "row": _row_label, "x": _x, "y": _y})

TOTAL_SLOTS = len(SLOT_DEFS)          # 24
OCC_RADIUS = 2.5                      # m, a car within this counts as occupying a slot
THEFT_TRIGGER = 30.0                  # s, when the staged theft begins
MOVE_SPEED = 1.5                      # m/s, theft car speed
MOVE_THRESHOLD = 2.0                  # m, movement from baseline that raises an alert
REPORT_EVERY = 3.0                    # s, periodic status broadcast


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def find_slot(pos):
    best, bd = "??", 1e9
    for s in SLOT_DEFS:
        d = dist2d((pos[0], pos[1]), (s["x"], s["y"]))
        if d < bd:
            bd, best = d, s["id"]
    return best


def main():
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())
    emitter = robot.getDevice("emitter")

    car_defs = [
        "CAR_A1", "CAR_A2", "CAR_A3", "CAR_A4", "CAR_A5", "CAR_A7", "CAR_A8",
        "CAR_B1", "CAR_B2", "CAR_B4", "CAR_B5", "CAR_B6", "CAR_B8",
        "CAR_C1", "CAR_C2", "CAR_C3", "CAR_C4", "CAR_C5", "CAR_C6", "CAR_C7", "CAR_C8",
        "THEFT_CAR",
    ]
    nodes = {d: robot.getFromDef(d) for d in car_defs}
    nodes = {k: v for k, v in nodes.items() if v is not None}

    # Record baseline positions to detect later movement.
    baselines = {}
    for name, node in nodes.items():
        p = node.getField("translation").getSFVec3f()
        baselines[name] = (p[0], p[1])

    theft_node = robot.getFromDef("THEFT_CAR")
    drone_node = robot.getFromDef("Drone")
    theft_active = False
    theft_done = False

    def car_positions():
        return [
            (n.getField("translation").getSFVec3f()[0],
             n.getField("translation").getSFVec3f()[1])
            for n in nodes.values()
        ]

    def slot_occupied(slot, positions):
        return any(dist2d(p, (slot["x"], slot["y"])) < OCC_RADIUS for p in positions)

    # Startup slot map.
    positions = car_positions()
    print("[Supervisor] Ready. Parking slot map:")
    for s in SLOT_DEFS:
        occ = slot_occupied(s, positions)
        print(f"  {s['id']:3s} ({s['x']:6.2f}, {s['y']:5.1f}) -> {'OCCUPIED' if occ else 'EMPTY'}")

    report_timer = 0.0

    while robot.step(timestep) != -1:
        t = robot.getTime()
        dt = timestep / 1000.0

        # Trigger the staged theft once.
        if t >= THEFT_TRIGGER and not theft_done and theft_node and not theft_active:
            theft_active = True
            print(f"\n[Supervisor] !! THEFT at t={t:.1f}s - THEFT_CAR is leaving its slot!")

        # Drive the theft car toward the exit gate.
        if theft_active and theft_node:
            p = theft_node.getField("translation").getSFVec3f()
            tx, ty = 50.0, -40.0
            dx, dy = tx - p[0], ty - p[1]
            d = math.hypot(dx, dy)
            if d > 0.5:
                step = MOVE_SPEED * dt
                theft_node.getField("translation").setSFVec3f(
                    [p[0] + dx / d * step, p[1] + dy / d * step, p[2]])
                theft_node.getField("rotation").setSFRotation(
                    [0, 0, 1, math.atan2(dy, dx) - math.pi / 2])
            else:
                theft_active = False
                theft_done = True
                print("[Supervisor] THEFT_CAR reached the exit.")

        # Detect any car that left its baseline (suspicious movement).
        alerts = []
        for name, node in nodes.items():
            p = node.getField("translation").getSFVec3f()
            cur = (p[0], p[1])
            moved = dist2d(cur, baselines[name])
            if moved > MOVE_THRESHOLD:
                alerts.append({
                    "car": name,
                    "slot": find_slot(baselines[name]),
                    "distance": round(moved, 1),
                    "position": [round(cur[0], 1), round(cur[1], 1)],
                })

        # Occupancy: aggregate, per-row, and per-slot.
        positions = car_positions()
        row_counts = {r: {"occupied": 0, "total": 0} for r, _ in ROWS}
        slot_map = {}
        occupied = 0
        for s in SLOT_DEFS:
            occ = slot_occupied(s, positions)
            slot_map[s["id"]] = occ
            row_counts[s["row"]]["total"] += 1
            if occ:
                occupied += 1
                row_counts[s["row"]]["occupied"] += 1
        available = TOTAL_SLOTS - occupied

        drone_pos = [0, 0, 0]
        if drone_node:
            dp = drone_node.getField("translation").getSFVec3f()
            drone_pos = [round(dp[0], 1), round(dp[1], 1), round(dp[2], 1)]

        stats = {
            "time": round(t, 1),
            "total": TOTAL_SLOTS,
            "occupied": occupied,
            "available": available,
            "vehicles": len(nodes),
            "rows": row_counts,
            "slots": slot_map,
            "alerts": alerts,
            "drone_pos": drone_pos,
            "THEFT_ALERT": len(alerts) > 0,
        }

        # Broadcast: immediately when a new alert appears, otherwise periodically.
        report_timer += dt
        if alerts or report_timer >= REPORT_EVERY:
            report_timer = 0.0
            _send(emitter, stats)


def _send(emitter, stats):
    if emitter is None:
        return
    try:
        emitter.send(json.dumps(stats).encode("utf-8"))
    except Exception as e:
        print(f"[Supervisor] Emitter error: {e}")


main()
