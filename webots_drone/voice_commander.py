"""
voice_commander.py — Voice control for the Webots drone.
Uses Whisper (local, free) + keyword matching (no API needed).

Place in webots_drone/ folder alongside webots_simulation.py.

Install dependencies (run once):
    pip install openai-whisper sounddevice numpy
"""

import threading
import queue
import numpy as np
import traceback
import re


class VoiceCommander:

    KEYWORDS = [
        # --- special modes (check BEFORE simple movement words) ---
        ("quit",      ["quit", "exit", "stop and land"]),
        ("AI_ON",     ["ai on", "activate ai", "ai mode on", "brain on", "enable ai"]),
        ("AI_OFF",    ["ai off", "deactivate ai", "ai mode off", "brain off", "disable ai"]),
        ("follow",    ["follow", "track", "chase", "pursue", "follow the person"]),
        ("manual",    ["manual", "free", "stop following", "stop tracking"]),
        ("scan",      ["scan", "search area", "survey", "start scan"]),

        # --- movement ---
        ("forward",   ["forward", "go forward", "advance", "ahead", "move forward"]),
        ("backward",  ["backward", "back", "go back", "reverse", "retreat", "move back"]),
        ("left",      ["go left", "move left", "strafe left", "slide left"]),
        ("right",     ["go right", "move right", "strafe right", "slide right"]),
        ("up",        ["go up", "move up", "higher", "ascend", "climb", "up"]),
        ("down",      ["go down", "move down", "lower", "descend", "down"]),
        ("turn_left", ["turn left", "rotate left", "spin left"]),
        ("turn_right",["turn right", "rotate right", "spin right"]),
        ("stop",      ["stop", "halt", "freeze", "hold", "hover"]),
        ("land",      ["land", "landing"]),
    ]

    def __init__(self, model="tiny", record_seconds=2, silence_threshold=0.05):
        self.record_seconds = record_seconds
        self.silence_threshold = silence_threshold
        self._action_queue = queue.Queue()
        self._running = False
        self._thread = None

        print(f"Loading Whisper ({model}) model... ", end="", flush=True)
        import whisper
        self._whisper = whisper.load_model(model)
        print("OK")
        print("Voice commander ready.")
        print("Say: forward / back / go left / go right / up / down")
        print("     turn left / turn right / scan / follow / manual")
        print("     ai on / ai off / stop / quit")

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[Voice] Listening... speak clearly into your mic")

    def stop(self):
        self._running = False

    def get_action(self, limits):
        """
        Returns:
            list [roll, pitch, yaw, alt]  — movement action
            "FOLLOW" / "MANUAL" / "SCAN" / "AI_ON" / "AI_OFF" / "QUIT"  — mode strings
            None  — nothing heard yet
        """
        try:
            command = self._action_queue.get_nowait()
            return self._command_to_action(command, limits)
        except queue.Empty:
            return None

    # ------------------------------------------------------------------ #

    def _clean(self, text):
        """Strip punctuation, lowercase — fixes 'Up!', 'Down.', 'Right?' etc."""
        return re.sub(r"[^\w\s]", "", text).lower().strip()

    def _match_command(self, text):
        text = self._clean(text)
        for command, keywords in self.KEYWORDS:
            for kw in keywords:
                if kw in text:
                    return command
        return None

    def _listen_loop(self):
        import sounddevice as sd
        sample_rate = 16000

        while self._running:
            try:
                audio = sd.rec(
                    int(self.record_seconds * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32"
                )
                sd.wait()
                audio = audio.flatten()

                if np.abs(audio).max() < self.silence_threshold:
                    continue

                result = self._whisper.transcribe(
                    audio,
                    fp16=False,
                    language="en",
                    temperature=0.0
                )
                text = result["text"].strip()
                if not text:
                    continue

                cleaned = self._clean(text)
                print(f"[Voice] Heard: '{text}' → cleaned: '{cleaned}'", flush=True)

                command = self._match_command(text)
                if command:
                    print(f"[Voice] Command: {command}", flush=True)
                    self._action_queue.put(command)
                else:
                    print(f"[Voice] No match — try: forward / back / up / down / scan / follow / ai on", flush=True)

            except Exception as e:
                print(f"[Voice] Error: {e}", flush=True)

    def _command_to_action(self, command, limits):
        """Convert command string to action vector or special string."""
        roll, pitch, yaw, alt = 0., 0., 0., 0.

        if command == "forward":
            pitch = limits[1][1]
        elif command == "backward":
            pitch = limits[0][1]
        elif command == "left":
            roll = limits[0][0]
        elif command == "right":
            roll = limits[1][0]
        elif command == "up":
            alt = limits[1][3]
        elif command == "down":
            alt = limits[0][3]
        elif command == "turn_left":
            yaw = limits[1][2]
        elif command == "turn_right":
            yaw = limits[0][2]
        elif command == "stop":
            return [0., 0., 0., 0.]

        # special mode strings — picked up by main loop
        elif command == "follow":
            return "FOLLOW"
        elif command == "manual":
            return "MANUAL"
        elif command == "scan":
            return "SCAN"
        elif command == "AI_ON":
            return "AI_ON"
        elif command == "AI_OFF":
            return "AI_OFF"
        elif command in ("quit", "land"):
            return "QUIT"

        return [roll, pitch, yaw, alt]
