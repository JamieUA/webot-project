"""
parking_main.py — Autonomous Parking Guard Drone main controller.

Run AFTER pressing Play in Webots:
    python parking_main.py

Auto-takeoff → patrol → detect → theft alert → track → resume patrol.

KEYBOARD (click Webots 3D window first):
  W/S          — altitude up/down
  Arrow keys   — fly manually
  A/D          — yaw
  F            — follow detected person
  X            — toggle patrol mode
  P            — save photo
  G            — print parking report now
  Q            — quit

VOICE: "scan", "follow", "stop", "up", "down",
       "forward", "back", "left", "right", "manual", "report"
"""

import os, sys, traceback, json, datetime, warnings
import numpy as np
import cv2

warnings.filterwarnings("ignore", category=DeprecationWarning)

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "webots_drone"))
sys.path.insert(0, _ROOT)

os.environ.setdefault("WEBOTS_HOME", "C:/Program Files/Webots")
sys.path.append(os.environ["WEBOTS_HOME"] + "/lib/controller/python")

from webots_drone.webots_simulation import WebotsSimulation, print_control_keys
from webots_drone.follower          import PersonFollower
from webots_drone.hud_overlay       import HUD
from webots_drone.voice_commander   import VoiceCommander
from webots_drone.utils             import constrained_action, receiver_get_json, emitter_send_json

from parking_detector import ParkingDetector
from path_planner     import PatrolPlanner

TAKEOFF_HEIGHT  = 15.0   # metres
TOTAL_SLOTS     = 25
AUTO_TAKEOFF    = True   # drone lifts off automatically on start


def kb2action_parking(kb, limits):
    """Extended keyboard handler — adds G key for report."""
    key = kb.getKey()
    run_flag = True
    take_shot = tog_follow = tog_patrol = print_report = False
    roll = pitch = yaw = alt = 0.

    while key > 0:
        if   key == kb.UP:      pitch = limits[1][1]
        elif key == kb.DOWN:    pitch = limits[0][1]
        elif key == kb.LEFT:    roll  = limits[0][0]
        elif key == kb.RIGHT:   roll  = limits[1][0]
        elif key == ord('W'):   alt   = limits[1][3]
        elif key == ord('S'):   alt   = limits[0][3]
        elif key == ord('A'):   yaw   = limits[1][2]
        elif key == ord('D'):   yaw   = limits[0][2]
        elif key == ord('F'):   tog_follow  = True
        elif key == ord('X'):   tog_patrol  = True
        elif key == ord('P'):   take_shot   = True
        elif key == ord('G'):   print_report = True
        elif key == ord('Q'):   run_flag    = False; print("Quit.")
        key = kb.getKey()

    return [roll,pitch,yaw,alt], run_flag, take_shot, tog_follow, tog_patrol, print_report


def run():
    detector = ParkingDetector(confidence=0.35)
    follower = PersonFollower(frame_w=400, frame_h=240)
    planner  = PatrolPlanner()
    hud      = HUD()
    voice    = VoiceCommander()
    voice.start()

    controller  = WebotsSimulation()
    kb          = controller.get_kb_capturer()
    flight_area = controller.get_flight_area(altitude_limits=[2., 50.])

    # Supervisor receiver — channel 9 messages
    sup_receiver = controller.getDevice("SupervisorReceiver")
    if sup_receiver:
        sup_receiver.enable(controller.timestep)

    print_control_keys()
    print("\n[Parking Guard] Auto-takeoff starting...\n")

    controller.play()
    controller.sync()

    # ── Auto takeoff ─────────────────────────────────────────────────────────
    if AUTO_TAKEOFF:
        print(f"[Parking Guard] Taking off to {TAKEOFF_HEIGHT}m...")
        controller.take_off(TAKEOFF_HEIGHT)
        print("[Parking Guard] Airborne. Starting patrol.\n")

    run_flag     = True
    follow_mode  = False
    patrol_mode  = True    # start in patrol immediately
    theft_alert  = False
    step         = 0

    last_report    = {}
    last_sup_stats = {}

    VOICE_HOLD   = 150
    _v_action    = [0.,0.,0.,0.]
    _v_remaining = 0

    while run_flag:
        state    = controller.get_data()
        pos      = state.get("position",  [0.,0.,TAKEOFF_HEIGHT])
        north    = state.get("north_rad", 0.)
        altitude = float(pos[2])

        # ── Supervisor messages ───────────────────────────────────────────────
        if sup_receiver:
            while sup_receiver.getQueueLength() > 0:
                try:
                    raw  = sup_receiver.getData()
                    data = json.loads(raw.decode("utf-8"))
                    last_sup_stats = data
                    if data.get("THEFT_ALERT"):
                        theft_alert = True
                        planner.receive_alert(data)
                        follow_mode = False
                        patrol_mode = False
                        print("[ALERT] Theft detected! Switching to TRACK mode.")
                except Exception as e:
                    print(f"[Supervisor msg] {e}")
                sup_receiver.nextPacket()

        # ── Vision detection ──────────────────────────────────────────────────
        img = state.get("image")
        if img is not None and hasattr(img,"shape") and img.shape[0] > 0:
            try:
                annotated, report = detector.detect(img)
                last_report = report
            except Exception as e:
                print(f"[Detector] {e}")
                annotated = np.zeros((240,400,3), dtype=np.uint8)
                report    = {}
        else:
            annotated = np.zeros((240,400,3), dtype=np.uint8)
            report    = {}

        persons   = report.get("persons", [])
        car_count = report.get("car_count", 0)

        # Auto-switch to follow on person detection
        if persons and not follow_mode and not theft_alert:
            follow_mode  = True
            patrol_mode  = False
            print(f"[Auto] Person detected → FOLLOW mode")

        # ── Keyboard ──────────────────────────────────────────────────────────
        try:
            action, run_flag, take_shot, tog_follow, tog_patrol, do_report = \
                kb2action_parking(kb, controller.limits)
        except Exception:
            action = [0.,0.,0.,0.]
            run_flag=True; take_shot=False; tog_follow=tog_patrol=do_report=False

        kb_pressed = any(v != 0. for v in action)

        if tog_follow:
            follow_mode = not follow_mode
            if follow_mode: patrol_mode = False; theft_alert = False
            print(f"[F] Follow {'ON' if follow_mode else 'OFF'}")

        if tog_patrol:
            patrol_mode = not patrol_mode
            if patrol_mode: follow_mode = False; theft_alert = False; planner.resume_patrol()
            print(f"[X] Patrol {'ON' if patrol_mode else 'OFF'}")

        if do_report and last_sup_stats:
            _print_full_report(last_sup_stats, altitude)

        # Periodic auto-report every ~500 steps
        if step % 500 == 0 and last_sup_stats:
            _print_full_report(last_sup_stats, altitude)

        # ── Voice ─────────────────────────────────────────────────────────────
        try:
            va = voice.get_action(controller.limits)
        except Exception:
            va = None

        if   va == "QUIT":    run_flag = False
        elif va == "FOLLOW":  follow_mode=True;  patrol_mode=False; _v_remaining=0
        elif va == "SCAN":    patrol_mode=True;  follow_mode=False; planner.resume_patrol(); _v_remaining=0
        elif va == "MANUAL":  follow_mode=False; patrol_mode=False; theft_alert=False; _v_remaining=0
        elif va is not None:
            follow_mode=False; patrol_mode=False
            _v_action=va; _v_remaining=VOICE_HOLD

        # ── Action priority ───────────────────────────────────────────────────
        if kb_pressed:
            final = action; _v_remaining = 0

        elif theft_alert or planner.mode == "TRACK":
            # Track the moving theft car via planner
            final = planner.step(pos, controller.limits)
            # If we've been tracking for >30s, resume patrol
            if step % 375 == 0 and theft_alert:
                print("[Track] Resuming patrol.")
                theft_alert = False
                patrol_mode = True
                planner.resume_patrol()

        elif follow_mode and persons:
            try:    final = follower.compute_action(persons[0], controller.limits)
            except: final = [0.,0.,0.,0.]

        elif follow_mode and not persons:
            # Search yaw
            final = [0., 0., controller.limits[0][2] * 0.15, 0.]

        elif patrol_mode:
            final = planner.step(pos, controller.limits)

        elif _v_remaining > 0:
            final = _v_action; _v_remaining -= 1

        else:
            final = [0.,0.,0.,0.]

        # ── Constrain & send ──────────────────────────────────────────────────
        try:
            final = constrained_action(final, pos, north, flight_area, is_vel=False)
        except: pass

        controller.send_action(final)

        # ── Photo ─────────────────────────────────────────────────────────────
        if take_shot:
            os.makedirs("photos", exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"photos/parking_{ts}.png"
            cv2.imwrite(fname, annotated)
            print(f"[Camera] Saved {fname}")

        # ── Display ───────────────────────────────────────────────────────────
        mode_label = ("track" if theft_alert else
                      "follow" if follow_mode else
                      "patrol" if patrol_mode else "manual")

        parking_report_for_hud = {
            "total":    last_sup_stats.get("total",    TOTAL_SLOTS),
            "occupied": last_sup_stats.get("occupied", car_count),
            "available":last_sup_stats.get("available",TOTAL_SLOTS - car_count),
            "alerts":   last_sup_stats.get("alerts",   []),
        }

        try:
            frame = hud.draw(
                annotated,
                mode          = mode_label,
                detections    = persons,
                altitude      = altitude,
                brain_message = "",
                follow_mode   = follow_mode,
                scan_active   = patrol_mode,
                brain_active  = False,
                parking_report= parking_report_for_hud,
                waypoint_label= planner.current_waypoint_label,
                theft_alert   = theft_alert,
            )
            cv2.imshow("Parking Guard Drone", frame)
            cv2.waitKey(1)
        except Exception as e:
            print(f"[HUD] {e}")

        step += 1

    voice.stop()
    cv2.destroyAllWindows()


def _print_full_report(stats, altitude):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print("\n" + "="*52)
    print(f"  PARKING STATUS REPORT  [{ts}]")
    print("="*52)
    print(f"  Total Slots      : {stats.get('total', 25)}")
    print(f"  Occupied         : {stats.get('occupied', 0)}")
    print(f"  Available        : {stats.get('available', 25)}")
    print(f"  Drone Position   : {stats.get('drone_pos', [0,0,0])}")
    print(f"  Drone Altitude   : {altitude:.1f}m")
    alerts = stats.get("alerts", [])
    if alerts:
        print("  !! THEFT ALERT !!")
        for a in alerts:
            print(f"     Vehicle : {a.get('car', '?')}")
            print(f"     Slot    : {a.get('slot', '?')}")
            print(f"     Moved   : {a.get('distance', 0)}m from slot")
            print(f"     Location: {a.get('position', [0,0])}")
    else:
        print("  Security         : CLEAR")
    print("="*52 + "\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        print(e)
