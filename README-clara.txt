=== Intelligent Autonomous Drone Assistant ===
FYP Project — Clara Tayoun & Jamie Knayer

REQUIREMENTS:
- Webots simulator (https://cyberbotics.com)
- Python 3.13

SETUP (run once):
1. Install dependencies:
      pip install -r requirements.txt

2. Set Webots environment variable:
      setx WEBOTS_HOME "C:\Program Files\Webots"
   Then close and reopen your terminal.

HOW TO RUN:
1. Open Webots
2. Open world: worlds\forest_tower.wbt
3. Wait for world to fully load
4. Open terminal and run:
      cd gym-webots-drone-main
      python webots_drone\webots_simulation.py
5. First run downloads Whisper model (~72MB) — just wait

CONTROLS:
  Keyboard:
    Arrow keys  — move forward/backward/left/right
    W / S       — altitude up / down
    A / D       — rotate left / right
    Q           — quit

  Voice commands (speak clearly into mic):
    "forward"       — move forward
    "back"          — move backward
    "go left"       — strafe left
    "go right"      — strafe right
    "up"            — increase altitude
    "down"          — decrease altitude
    "turn left"     — rotate left
    "turn right"    — rotate right
    "scan"          — hover and scan
    "stop"          — stop moving
    "follow"        — auto-follow detected person
    "manual"        — return to manual control
    "land"          — exit simulation

NOTE: The Webots 3D window must be selected for keyboard controls to work.
