"""
scan_mode.py — Autonomous 360° scan for the drone.
Place in: webots_drone/scan_mode.py

Activated by saying "scan" or pressing B key.
Drone slowly rotates in place while detector.py looks for persons.
When a person is found it sets person_found=True so the main loop
can switch to follow mode automatically.
"""


class ScanMode:
    """Rotates the drone slowly to complete a 360° scan."""

    STEPS_PER_ROTATION = 350    # tune: more = slower spin
    TURN_FRACTION      = 0.30   # fraction of max yaw rate to use

    def __init__(self):
        self._step        = 0
        self.person_found = False
        self.rotations_done = 0
        print("[Scan] Scan mode ready.")

    def reset(self):
        self._step        = 0
        self.person_found = False

    def step(self, detections: list, limits) -> list:
        """
        Call every simulation loop step when scan mode is active.
        Returns [roll, pitch, yaw, altitude] action.
        Sets self.person_found = True if a person is detected.
        """
        if detections:
            self.person_found = True
            print(f"[Scan] Person found after {self._step} steps — switching to follow!", flush=True)
            return [0., 0., 0., 0.]   # hover; main loop switches mode

        self._step += 1
        if self._step % self.STEPS_PER_ROTATION == 0:
            self.rotations_done += 1
            print(f"[Scan] Completed rotation #{self.rotations_done}", flush=True)

        # Slow rightward yaw: limits[0][2] is the NEGATIVE limit (turn right)
        yaw = limits[0][2] * self.TURN_FRACTION
        return [0., 0., yaw, 0.]

    @property
    def status(self) -> str:
        pct = (self._step % self.STEPS_PER_ROTATION) / self.STEPS_PER_ROTATION * 100
        return f"[Scan] Scanning {pct:.0f}% — rotation #{self.rotations_done + 1}"