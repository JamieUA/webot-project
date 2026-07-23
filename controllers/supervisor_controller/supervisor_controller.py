"""
controllers/supervisor_controller/supervisor_controller.py

NOTE: The ParkingSupervisor Robot node in the .wbt must have:
  children [
    Emitter { channel 9 name "emitter" }
  ]

This controller:
  - Maps all 25 parking slots
  - Monitors car positions every timestep
  - Simulates theft at t=60s by moving THEFT_CAR
  - Sends JSON status every 5s to drone on channel 9
  - Prints the slot map on startup
"""

from controller import Supervisor
import json, math

ROWS      = [("A", 28), ("B", 0), ("C", -28)]
X_POS     = [-15, -10.5, -6, -1.5, 3, 7.5, 12, 16.5]

SLOT_DEFS = []
for row_label, y in ROWS:
    for i, x in enumerate(X_POS):
        SLOT_DEFS.append({"id": f"{row_label}{i+1}", "x": x, "y": y})

TOTAL_SLOTS   = 25
THEFT_TRIGGER = 60.0
MOVE_SPEED    = 1.5   # m/s

def dist2d(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def find_slot(pos):
    best, bd = "??", 999
    for s in SLOT_DEFS:
        d = dist2d((pos[0],pos[1]), (s["x"],s["y"]))
        if d < bd: bd=d; best=s["id"]
    return best

def main():
    robot    = Supervisor()
    timestep = int(robot.getBasicTimeStep())
    emitter  = robot.getDevice("emitter")

    car_defs = [
        "CAR_A1","CAR_A2","CAR_A3","CAR_A4","CAR_A5","CAR_A7","CAR_A8",
        "CAR_B1","CAR_B2","CAR_B4","CAR_B5","CAR_B6","CAR_B8",
        "CAR_C1","CAR_C2","CAR_C3","CAR_C4","CAR_C5","CAR_C6","CAR_C7","CAR_C8",
        "THEFT_CAR",
    ]

    nodes = {d: robot.getFromDef(d) for d in car_defs}
    nodes = {k:v for k,v in nodes.items() if v is not None}

    # Record baseline positions
    baselines = {}
    for name, node in nodes.items():
        p = node.getField("translation").getSFVec3f()
        baselines[name] = (p[0], p[1])

    theft_node   = robot.getFromDef("THEFT_CAR")
    theft_active = False
    theft_done   = False
    alert_sent   = False

    print("[Supervisor] Ready. Slot map:")
    for s in SLOT_DEFS:
        occ = any(
            dist2d((nodes[n].getField("translation").getSFVec3f()[0],
                    nodes[n].getField("translation").getSFVec3f()[1]),
                   (s["x"], s["y"])) < 2.5
            for n in nodes
        )
        print(f"  {s['id']:3s} ({s['x']:5.1f}, {s['y']:5.1f}) → {'OCCUPIED' if occ else 'EMPTY'}")

    report_timer = 0.0
    REPORT_EVERY = 5.0

    while robot.step(timestep) != -1:
        t  = robot.getTime()
        dt = timestep / 1000.0

        # Trigger theft
        if t >= THEFT_TRIGGER and not theft_done and theft_node:
            theft_active = True
            print(f"\n[Supervisor] !! THEFT at t={t:.1f}s — THEFT_CAR is moving!")

        # Move theft car toward exit
        if theft_active and theft_node:
            p  = theft_node.getField("translation").getSFVec3f()
            tx, ty = 50, -40
            dx, dy = tx-p[0], ty-p[1]
            d  = math.sqrt(dx*dx+dy*dy)
            if d > 0.5:
                s  = MOVE_SPEED * dt
                theft_node.getField("translation").setSFVec3f([p[0]+dx/d*s, p[1]+dy/d*s, p[2]])
                theft_node.getField("rotation").setSFRotation([0,0,1, math.atan2(dy,dx)-math.pi/2])
            else:
                theft_active = False; theft_done = True
                print("[Supervisor] THEFT_CAR exited the lot.")

        # Detect unexpected movement
        alerts = []
        for name, node in nodes.items():
            p   = node.getField("translation").getSFVec3f()
            cur = (p[0], p[1])
            if dist2d(cur, baselines[name]) > 2.0:
                alerts.append({
                    "car":      name,
                    "slot":     find_slot(baselines[name]),
                    "distance": round(dist2d(cur, baselines[name]), 1),
                    "position": [round(cur[0],1), round(cur[1],1)],
                })

        # Count occupancy
        occupied  = sum(
            1 for s in SLOT_DEFS
            if any(dist2d((nodes[n].getField("translation").getSFVec3f()[0],
                           nodes[n].getField("translation").getSFVec3f()[1]),
                          (s["x"],s["y"])) < 2.5 for n in nodes)
        )
        available = TOTAL_SLOTS - occupied

        drone_pos = [0,0,0]
        drone = robot.getFromDef("Drone")
        if drone:
            p = drone.getField("translation").getSFVec3f()
            drone_pos = [round(p[0],1), round(p[1],1), round(p[2],1)]

        stats = {
            "time": round(t,1),
            "total": TOTAL_SLOTS,
            "occupied": occupied,
            "available": available,
            "alerts": alerts,
            "drone_pos": drone_pos,
            "THEFT_ALERT": len(alerts) > 0,
        }

        # Send alert immediately
        if alerts and not alert_sent:
            alert_sent = True
            _send(emitter, stats)
            _print(stats)

        # Periodic report
        report_timer += dt
        if report_timer >= REPORT_EVERY:
            report_timer = 0.0
            _send(emitter, stats)
            _print(stats)

def _send(emitter, stats):
    if emitter is None: return
    try: emitter.send(json.dumps(stats).encode("utf-8"))
    except Exception as e: print(f"[Supervisor] Emitter: {e}")

def _print(stats):
    print(f"\n[Supervisor] t={stats['time']}s | "
          f"Occupied:{stats['occupied']} Free:{stats['available']} "
          f"Alert:{'YES' if stats['THEFT_ALERT'] else 'no'} "
          f"DronePos:{stats['drone_pos']}")

main()
