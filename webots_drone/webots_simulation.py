#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
webots_simulation.py — Main drone simulation controller (HIKING SCENARIO).
Integrates: keyboard, voice, YOLOv8 detection, follow mode,
            autonomous scan mode, Claude AI brain, HUD overlay.

KEYBOARD CONTROLS (click the Webots 3D window first!):
  Arrow UP    — fly forward
  Arrow DOWN  — fly backward
  Arrow LEFT  — strafe left
  Arrow RIGHT — strafe right
  W / S       — altitude up / down
  A / D       — rotate left / right (yaw)
  F           — toggle FOLLOW mode
  B           — toggle AI BRAIN on/off
  X           — toggle SCAN mode
  P           — take photo
  Q           — quit

VOICE: forward | back | go left | go right | up | down
       turn left | turn right | stop | scan | follow
       manual | ai on | ai off | quit
"""

import numpy as np
import traceback
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from webots_drone.utils import check_flight_area
from webots_drone.utils import compute_distance
from webots_drone.utils import min_max_norm
from webots_drone.utils import decode_image
from webots_drone.utils import emitter_send_json
from webots_drone.utils import receiver_get_json
from webots_drone.utils import constrained_action

sys.path.append(os.environ['WEBOTS_HOME'] + "/lib/controller/python")
from controller import Supervisor


class WebotsSimulation(Supervisor):
    def __init__(self):
        super(WebotsSimulation, self).__init__()
        self.timestep    = int(self.getBasicTimeStep())
        self.image_shape = (240, 400, 4)
        self.vehicle_dim = [0.15, 0.3]
        self._data       = dict()
        self.limits      = self.get_control_ranges()
        self.init_nodes()
        self.init_comms()

    @property
    def is_running(self):
        return self.SIMULATION_MODE_PAUSE != self.simulationGetMode()

    def pause(self):     self.simulationSetMode(self.SIMULATION_MODE_PAUSE)
    def play(self):      self.simulationSetMode(self.SIMULATION_MODE_REAL_TIME)
    def play_fast(self): self.simulationSetMode(self.SIMULATION_MODE_FAST)

    def seed(self, seed=None):
        self.np_random = np.random.RandomState(seed)
        return seed

    @staticmethod
    def get_control_ranges():
        control_ranges = np.array([np.pi / 12., np.pi / 12., np.pi, 5.])
        return np.array([control_ranges * -1, control_ranges])

    def get_flight_area(self, altitude_limits=[11, 75]):
        try:
            area_node  = self.getFromDef('FlightArea')
            area_size  = area_node.getField('size').getSFVec2f()
            area_size  = [fs / 2 for fs in area_size]
            flight_area = [[fs * -1 for fs in area_size], area_size]
            flight_area[0].append(altitude_limits[0])
            flight_area[1].append(altitude_limits[1])
            return np.asarray(flight_area)
        except Exception:
            print("[WebotsSimulation] FlightArea DEF not found — using 200x200 m default.")
            return np.array([[-100., -100., altitude_limits[0]],
                             [ 100.,  100., altitude_limits[1]]])

    def init_comms(self):
        self.action = self.getDevice('ActionEmitter')
        self.state  = self.getDevice('StateReceiver')
        self.state.enable(self.timestep)
        return self

    def init_areas(self):
        try:
            forest_shape = self.getFromDef('ForestArea').getField('shape')
            self.forest_area = []
            for i in range(forest_shape.getCount()):
                self.forest_area.append(forest_shape.getMFVec2f(i))
            self.forest_area = np.asarray(self.forest_area)
        except Exception:
            self.forest_area = None

    def init_drone_node(self):
        drone_node = self.getFromDef('Drone')
        self.drone_node = dict(
            node    = drone_node,
            get_pos = lambda: np.array(drone_node.getField('translation').getSFVec3f()),
            set_pos = drone_node.getField('translation').setSFVec3f
        )

    def init_nodes(self):
        self.init_areas()
        self.init_drone_node()

    def reset(self):
        if self.is_running:
            self.state.disable()
            self.drone_node['node'].restartController()
            self.simulationReset()
            self.simulationResetPhysics()
            self.one_step()
            self.pause()
            self.state.enable(self.timestep)
            self._data = dict()

    def one_step(self):
        self.step(self.timestep)

    def get_drone_pos(self):
        return self.drone_node['get_pos']()

    def read_data(self):
        uav_state, emitter_info = receiver_get_json(self.state)
        if len(uav_state.keys()) == 0:
            return self._data
        dist_sensors = []
        for idx, sensor in uav_state['dist_sensors'].items():
            if sensor[2] == sensor[1] == sensor[0] == 0.:
                continue
            s_val = min_max_norm(sensor[0], a=0, b=1,
                                 minx=sensor[1], maxx=sensor[2])
            dist_sensors.append(s_val)
        if type(uav_state['image']) == str and uav_state['image'] == "NoImage":
            img = np.zeros(self.image_shape)
        else:
            img = decode_image(uav_state['image'])
        self._data = dict(
            timestamp        = uav_state['timestamp'],
            orientation      = uav_state['orientation'],
            angular_velocity = uav_state['angular_velocity'],
            position         = uav_state['position'],
            speed            = uav_state['speed'],
            north_rad        = uav_state['north'],
            dist_sensors     = dist_sensors,
            motors_vel       = uav_state['motors_vel'],
            image            = img,
            emitter          = emitter_info,
            rc_position      = self.getSelf().getPosition()
        )

    def get_data(self):
        return self._data.copy()

    def send_action(self, action):
        command = {'disturbances': np.clip(action, *self.limits).tolist(),
                   'timestamp': self.getTime()}
        emitter_send_json(self.action, command)
        self.one_step()
        self.read_data()

    def take_off(self, height):
        lift_action = [0., 0., 0., self.limits[1][3]]
        height_diff = lambda x: x - self.get_data()['position'][2]
        min_lift = self.get_data()['position'][2] + 1.
        while height_diff(min_lift) > 0.:
            self.send_action(lift_action)
        while height_diff(height) > 0.:
            self.send_action(lift_action)

    def sync(self):
        while len(self._data.keys()) == 0:
            self.one_step()
            self.read_data()

    def get_kb_capturer(self):
        kb = self.getKeyboard()
        kb.enable(self.timestep)
        return kb

    def __del__(self):
        try:
            self.reset()
        except Exception as e:
            print('ERROR: unable to reset the environment!')
            traceback.print_tb(e.__traceback__)
            print(e)


# ======================================================================
# Keyboard handler
# ======================================================================

def print_control_keys():
    print("\n" + "=" * 56)
    print("  DRONE CONTROL — click the Webots 3D window first!")
    print("=" * 56)
    print("  Arrow UP/DOWN    — fly forward / backward")
    print("  Arrow LEFT/RIGHT — strafe left / right")
    print("  W / S            — altitude up / down")
    print("  A / D            — rotate (yaw) left / right")
    print("  F                — toggle FOLLOW mode")
    print("  B                — toggle AI BRAIN on/off")
    print("  X                — toggle SCAN mode")
    print("  P                — take photo")
    print("  Q                — quit")
    print("-" * 56)
    print("  VOICE: forward/back/left/right/up/down/stop")
    print("         scan | follow | manual | ai on | ai off")
    print("=" * 56 + "\n")


def kb2action(kb, limits):
    """Read keyboard. Returns (action, run_flag, take_shot,
                               toggle_follow, toggle_brain, toggle_scan)."""
    key = kb.getKey()

    run_flag      = True
    take_shot     = False
    toggle_follow = False
    toggle_brain  = False
    toggle_scan   = False

    roll_angle  = 0.
    pitch_angle = 0.
    yaw_angle   = 0.
    altitude    = 0.

    while key > 0:
        if   key == kb.UP:      pitch_angle = limits[1][1]   # forward
        elif key == kb.DOWN:    pitch_angle = limits[0][1]   # backward
        elif key == kb.LEFT:    roll_angle  = limits[0][0]   # strafe left
        elif key == kb.RIGHT:   roll_angle  = limits[1][0]   # strafe right
        elif key == ord('W'):   altitude    = limits[1][3]   # up
        elif key == ord('S'):   altitude    = limits[0][3]   # down
        elif key == ord('A'):   yaw_angle   = limits[1][2]   # yaw left
        elif key == ord('D'):   yaw_angle   = limits[0][2]   # yaw right
        elif key == ord('F'):   toggle_follow = True
        elif key == ord('B'):   toggle_brain  = True
        elif key == ord('X'):   toggle_scan   = True
        elif key == ord('P'):   take_shot     = True
        elif key == ord('Q'):
            print('Terminated')
            run_flag = False
        key = kb.getKey()

    action = [roll_angle, pitch_angle, yaw_angle, altitude]
    return action, run_flag, take_shot, toggle_follow, toggle_brain, toggle_scan


# ======================================================================
# Main run loop
# ======================================================================

def run(controller, show=True, **kwargs):
    import cv2
    import datetime

    from webots_drone.follower import PersonFollower
    from webots_drone.voice_commander import VoiceCommander
    from webots_drone.detector import PersonDetector
    from webots_drone.scan_mode import ScanMode
    from webots_drone.hud_overlay import HUD
    from webots_drone.claude_brain import ClaudeBrain
    from webots_drone.target import VirtualTarget

    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
    USE_CLAUDE_BRAIN  = True
    # ------------------------------------------------------------------

    print("\n" + "=" * 60)
    print("🚁 HIKING DRONE SIMULATION - Webots Integration")
    print("=" * 60)
    print("Mode: Interactive Drone Control with Hiking Scenario")
    print("=" * 60 + "\n")

    follower = PersonFollower(frame_w=400, frame_h=240)
    scanner  = ScanMode()
    hud      = HUD()
    detector = PersonDetector(confidence=0.35)

    voice = VoiceCommander()
    voice.start()
    print("[Voice] Voice commander started - listening for commands")

    # AI brain: loaded but OFF by default — say "ai on" or press B
    brain        = None
    brain_active = False
    if USE_CLAUDE_BRAIN and ANTHROPIC_API_KEY and "YOUR-KEY" not in ANTHROPIC_API_KEY:
        try:
            brain = ClaudeBrain(api_key=ANTHROPIC_API_KEY)
            print("[Brain] ✓ Claude AI brain ready — say 'ai on' or press B to activate")
        except Exception as e:
            print(f"[Brain] ✗ Failed to initialize: {e}")
    else:
        print("[Brain] ⊘ No API key set — AI brain disabled")
        print("       Set ANTHROPIC_API_KEY environment variable to enable")

    print_control_keys()
    kb = controller.get_kb_capturer()

    # --- sim parameters ---
    goal_threshold  = kwargs.get('goal_threshold', 5.)
    target_pos      = kwargs.get('target_pos', [-50, 50])
    target_dim      = kwargs.get('target_dim', [7., 3.5])
    altitude_limits = kwargs.get('height_limits', [2., 75.])
    is_3d           = kwargs.get('is_3d', False)
    is_vel_control  = kwargs.get('is_vel_control', False)

    controller.seed()
    flight_area = controller.get_flight_area(altitude_limits)

    vtarget = VirtualTarget(dimension=target_dim, webots_node=None, is_3d=is_3d)
    vtarget.set_position(target_pos)

    controller.play()
    controller.sync()

    # --- flags ---
    run_flag    = True
    take_shot   = False
    follow_mode = False
    scan_active = False
    step        = 0

    # Voice carry-over: hold voice movement commands for N steps (~1 second)
    VOICE_HOLD_STEPS       = 150
    _last_voice_action     = [0., 0., 0., 0.]
    _voice_steps_remaining = 0
    _last_detection_count  = -1
    _last_voice_heard      = None
    _brain_message         = ""

    state = controller.get_data()

    print('\n✓ Simulation running! Click the 3D window then press W to take off.\n')

    # ==================================================================
    # MAIN LOOP
    # ==================================================================
    while run_flag:

        pos       = state.get('position',  [0., 0., 5.]) if state else [0., 0., 5.]
        north_rad = state.get('north_rad', 0.)           if state else 0.
        altitude  = float(pos[2])

        # ---- Detection -----------------------------------------------
        img = state.get('image') if state else None
        if img is not None and hasattr(img, 'shape') and img.shape[0] > 0:
            try:
                annotated, detections = detector.detect(img)
            except Exception as e:
                print(f"[Detector] {e}")
                annotated  = np.zeros((240, 400, 3), dtype=np.uint8)
                detections = []
        else:
            annotated  = np.zeros((240, 400, 3), dtype=np.uint8)
            detections = []

        count = len(detections)
        if count != _last_detection_count:
            if count > 0:
                print(f"  >>> PERSON DETECTED ({count})", flush=True)
            else:
                print(f"  >>> Person lost from view", flush=True)
            _last_detection_count = count

        # Auto scan → follow
        if count > 0 and scan_active:
            follow_mode = True
            scan_active = False
            scanner.reset()
            print("[Auto] Person detected → switching to FOLLOW", flush=True)

        # ---- AI Brain ------------------------------------------------
        if brain and brain_active:
            mode_str = ("follow" if follow_mode else
                        "scan"   if scan_active  else "ai")
            try:
                brain_decision = brain.update(
                    detections, list(pos), altitude, mode_str, _last_voice_heard)
            except Exception as e:
                print(f"[Brain] {e}")
                brain_decision = None

            if brain_decision:
                _brain_message = brain_decision.get("status_message", "")
                cmd = brain_decision.get("drone_command")
                if cmd == "FOLLOW" and detections:
                    follow_mode = True; scan_active = False
                    print("[Brain] → Follow mode", flush=True)
                elif cmd == "scan":
                    scan_active = True; follow_mode = False; scanner.reset()
                    print("[Brain] → Scan mode", flush=True)
                elif cmd and cmd not in ("QUIT", "FOLLOW"):
                    try:
                        mapped = voice._command_to_action(cmd, controller.limits)
                        if isinstance(mapped, list):
                            _last_voice_action     = mapped
                            _voice_steps_remaining = 35
                    except Exception:
                        pass
        else:
            _brain_message = ""

        # ---- Keyboard ------------------------------------------------
        try:
            kb_result = kb2action(kb, controller.limits)
            action, run_flag, take_shot, tog_follow, tog_brain, tog_scan = kb_result
        except Exception as e:
            print(f"[KB] {e}")
            action = [0., 0., 0., 0.]
            run_flag = True; take_shot = False
            tog_follow = tog_brain = tog_scan = False

        kb_pressed = any(v != 0. for v in action)

        if tog_follow:
            follow_mode = not follow_mode
            if follow_mode: scan_active = False
            print(f"[Key F] Follow {'ON' if follow_mode else 'OFF'}", flush=True)

        if tog_brain:
            if brain:
                brain_active = not brain_active
                print(f"[Key B] AI Brain {'ON' if brain_active else 'OFF'}", flush=True)
            else:
                print("[Key B] No API key — AI brain unavailable", flush=True)

        if tog_scan:
            scan_active = not scan_active
            if scan_active:
                follow_mode = False
                scanner.reset()
                print("[Key X] SCAN ON", flush=True)
            else:
                print("[Key X] Scan stopped", flush=True)

        # ---- Voice ---------------------------------------------------
        try:
            voice_action = voice.get_action(controller.limits)
        except Exception:
            voice_action = None

        if voice_action == "QUIT":
            run_flag = False

        elif voice_action == "FOLLOW":
            follow_mode = True; scan_active = False
            _voice_steps_remaining = 0
            print("[Voice] Follow ON", flush=True)

        elif voice_action == "MANUAL":
            follow_mode = False; scan_active = False; brain_active = False
            _voice_steps_remaining = 0
            print("[Voice] Manual mode", flush=True)

        elif voice_action == "SCAN":
            scan_active = True; follow_mode = False; scanner.reset()
            _voice_steps_remaining = 0
            print("[Voice] Scan ON", flush=True)

        elif voice_action == "AI_ON":
            if brain:
                brain_active = True
                print("[Voice] AI brain ON", flush=True)
            else:
                print("[Voice] No API key", flush=True)

        elif voice_action == "AI_OFF":
            brain_active = False
            print("[Voice] AI brain OFF", flush=True)

        elif voice_action is not None:
            # Movement voice command — hold for VOICE_HOLD_STEPS
            follow_mode = False; scan_active = False
            _last_voice_action     = voice_action
            _voice_steps_remaining = VOICE_HOLD_STEPS
            _last_voice_heard      = None
            print(f"[Voice] Moving for ~{VOICE_HOLD_STEPS} steps", flush=True)

        # ==============================================================
        # FINAL ACTION PRIORITY:
        #   1. Keyboard held    — always wins, cancels voice carry-over
        #   2. Follow + person  — visual tracking
        #   3. Follow, no person — gentle search yaw
        #   4. Scan mode        — rotation scan
        #   5. Voice carry-over — timed movement
        #   6. Hover            — do nothing
        # ==============================================================
        if kb_pressed:
            # Keyboard wins over everything; cancel pending voice steps
            action = action
            _voice_steps_remaining = 0

        elif follow_mode and detections:
            try:
                action = follower.compute_action(detections[0], controller.limits)
                if step % 30 == 0:
                    print(follower.status(detections[0]), flush=True)
            except Exception as e:
                print(f"[Follow] {e}")
                action = [0., 0., 0., 0.]

        elif follow_mode and not detections:
            action = [0., 0., controller.limits[0][2] * 0.15, 0.]
            if step % 40 == 0:
                print("[Follow] Searching — no person in view", flush=True)

        elif scan_active:
            try:
                action = scanner.step(detections, controller.limits)
                if scanner.person_found:
                    follow_mode = True; scan_active = False; scanner.reset()
                    print("[Scan] → Follow mode", flush=True)
                elif step % 60 == 0:
                    print(scanner.status, flush=True)
            except Exception as e:
                print(f"[Scan] {e}")
                action = [0., 0., 0., 0.]

        elif _voice_steps_remaining > 0:
            action = _last_voice_action
            _voice_steps_remaining -= 1
            if _voice_steps_remaining == 0:
                print("[Voice] Command done — hovering", flush=True)

        else:
            action = [0., 0., 0., 0.]   # hover

        # ---- Constrain & send ----------------------------------------
        try:
            action = constrained_action(
                action, pos, north_rad, flight_area, is_vel=is_vel_control)
        except Exception as e:
            print(f"[Constrain] {e}")
            action = [0., 0., 0., 0.]

        try:
            controller.send_action(action)
            state = controller.get_data()
        except Exception as e:
            print(f"[Send] {e}")

        # ---- Photo ---------------------------------------------------
        if take_shot:
            os.makedirs('photos', exist_ok=True)
            ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            cv2.imwrite(f'photos/picture_{ts}.png', annotated)
            print(f"[Camera] Saved photos/picture_{ts}.png")

        # ---- Display -------------------------------------------------
        if show:
            mode_label = ("ai"     if brain_active else
                          "follow" if follow_mode  else
                          "scan"   if scan_active  else "manual")
            try:
                frame = hud.draw(
                    annotated,
                    mode         = mode_label,
                    detections   = detections,
                    altitude     = altitude,
                    brain_message= _brain_message,
                    follow_mode  = follow_mode,
                    scan_active  = scan_active,
                    brain_active = brain_active,
                )
                cv2.imshow("Drone's live view", frame)
                cv2.waitKey(1)
            except Exception as e:
                print(f"[HUD] {e}")

        step += 1

    # ---- cleanup -----------------------------------------------------
    voice.stop()
    if show:
        cv2.destroyAllWindows()
    print("\n🔴 Simulation ended")


# ======================================================================
# Entry point
# ======================================================================

if __name__ == '__main__':
    sim_args = {
        'goal_threshold': 5.,
        'target_pos':     [-50, 50],
        'target_dim':     [7., 3.5],
        'height_limits':  [2., 75.],
        'is_3d':          False,
        'is_vel_control': False,
    }

    try:
        controller = WebotsSimulation()
        run(controller, show=True, **sim_args)
    except Exception as e:
        traceback.print_tb(e.__traceback__)
        print(e)
        try:
            controller.reset()
        except Exception:
            pass
