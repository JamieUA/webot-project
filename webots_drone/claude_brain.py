"""
claude_brain.py — AI Decision Layer for the Drone
Place in: webots_drone/claude_brain.py

Sends the current drone situation to Claude API every few seconds
and gets back a structured decision. Runs in a background thread
so it never freezes the simulation loop.

Usage:
    from claude_brain import ClaudeBrain
    brain = ClaudeBrain(api_key="sk-ant-...")
    brain.start()

    # inside the loop:
    decision = brain.update(detections, position, altitude, mode)
    if decision:
        print(decision['status_message'])
"""

import anthropic
import json
import threading
import time


class ClaudeBrain:

    # Map Claude's action strings to voice_commander command strings
    ACTION_MAP = {
        "hover":         None,           # do nothing, hold position
        "move_forward":  "forward",
        "move_backward": "backward",
        "move_left":     "left",
        "move_right":    "right",
        "ascend":        "up",
        "descend":       "down",
        "turn_left":     "turn_left",
        "turn_right":    "turn_right",
        "scan":          "scan",
        "follow_person": "FOLLOW",       # special string picked up by main loop
        "land":          "QUIT",
    }

    def __init__(self, api_key: str, cooldown_seconds: float = 5.0):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cooldown = cooldown_seconds

        self._decision = None          # latest parsed decision
        self._lock = threading.Lock()
        self._busy = False
        self._last_query = 0.0
        self._count = 0

        print("[Brain] Claude AI decision layer initialised.")

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    def update(self, detections: list, position: list,
               altitude: float, mode: str, voice_heard: str = None):
        """
        Call this every simulation loop iteration.
        Fires a background query when cooldown has elapsed.
        Returns the latest decision dict (or None before first reply).

        Decision dict keys:
            action          str  — see ACTION_MAP above
            drone_command   str | None — ready-to-use command string for main loop
            reason          str  — why Claude chose this action
            urgency         str  — "low" / "medium" / "high"
            status_message  str  — short HUD string (≤ 6 words)
        """
        now = time.time()
        if not self._busy and (now - self._last_query) >= self.cooldown:
            self._last_query = now
            self._busy = True
            ctx = self._build_context(detections, position, altitude, mode, voice_heard)
            t = threading.Thread(target=self._query, args=(ctx,), daemon=True)
            t.start()

        with self._lock:
            return self._decision

    def get_latest(self):
        with self._lock:
            return self._decision

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _build_context(self, detections, position, altitude, mode, voice_heard):
        n = len(detections)
        if n > 0:
            d = detections[0]
            x1, y1, x2, y2 = d["bbox"]
            cx = (x1 + x2) / 2
            bw = x2 - x1
            side = "left" if cx < 160 else ("right" if cx > 240 else "center")
            dist = "close" if bw > 120 else ("medium" if bw > 60 else "far")
            cam = f"{n} person(s) detected — {side} of frame, {dist} range, conf={d['confidence']:.0%}"
        else:
            cam = "No persons detected in camera."

        voice = f'Last voice command heard: "{voice_heard}".' if voice_heard else "No recent voice command."

        return (
            f"Drone state:\n"
            f"  GPS position: x={position[0]:.1f} m, y={position[1]:.1f} m\n"
            f"  Altitude: {altitude:.1f} m\n"
            f"  Current mode: {mode}\n"
            f"Camera: {cam}\n"
            f"Operator: {voice}"
        )

    def _query(self, context: str):
        self._count += 1
        n = self._count

        system = (
            "You are the autonomous AI brain of a search-and-rescue drone in a Webots simulation.\n"
            "Analyse the drone's situation and decide the single best next action.\n\n"
            "Respond ONLY with a valid JSON object — no markdown, no explanation:\n"
            "{\n"
            '  "action": "<one of: hover | move_forward | move_backward | move_left | move_right | '
            'ascend | descend | turn_left | turn_right | scan | follow_person | land>",\n'
            '  "reason": "<one short sentence>",\n'
            '  "urgency": "<low | medium | high>",\n'
            '  "status_message": "<max 5 words for HUD display>"\n'
            "}\n\n"
            "Rules:\n"
            "- If a person is detected and mode is not 'follow': suggest follow_person\n"
            "- If no person and mode is 'scan': suggest turn_right or move_forward to keep searching\n"
            "- If altitude < 3 m: suggest ascend (safety first)\n"
            "- If altitude > 60 m: suggest descend\n"
            "- If operator gave a voice command, honour their intent\n"
            "- hover is always a safe fallback"
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                system=system,
                messages=[{"role": "user", "content": context}],
            )
            raw = response.content[0].text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            decision = json.loads(raw)

            # attach ready-to-use command string
            action = decision.get("action", "hover")
            decision["drone_command"] = self.ACTION_MAP.get(action, None)
            decision["query_id"] = n

            with self._lock:
                self._decision = decision

            print(
                f"[Brain] #{n} → {action} | {decision.get('status_message', '')} "
                f"({decision.get('urgency', '?')} urgency)"
            )

        except json.JSONDecodeError as e:
            print(f"[Brain] #{n} JSON error: {e}")
        except anthropic.APIError as e:
            print(f"[Brain] #{n} API error: {e}")
        except Exception as e:
            print(f"[Brain] #{n} Unexpected error: {e}")
        finally:
            self._busy = False
