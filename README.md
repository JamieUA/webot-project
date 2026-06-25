# 🚁 Webots Drone Project - Hiking Group Monitoring System

**A complete autonomous drone assistant for monitoring hiking groups in forests with AI brain, voice control, and real-time health tracking.**

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Project Overview](#project-overview)
3. [System Architecture](#system-architecture)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage Guide](#usage-guide)
7. [Hiking Scenario Explained](#hiking-scenario-explained)
8. [AI Brain Mode](#ai-brain-mode)
9. [Voice Commands](#voice-commands)
10. [Group Monitoring](#group-monitoring)
11. [Troubleshooting](#troubleshooting)
12. [File Structure](#file-structure)
13. [References](#references)

---

## 🚀 Quick Start

### **For the Impatient (5 Minutes)**

```bash
# 1. Set environment
export WEBOTS_HOME=/path/to/webots
export ANTHROPIC_API_KEY="sk-ant-xxxxx"  # Optional, for AI brain

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run hiking demo
python hiking_drone_main.py

# 4. Or run full simulation
cd webots_drone
python webots_simulation.py

# 5. Voice control (optional)
# Say: "ai on"  →  AI brain activates
# Say: "follow" →  Follow detected person
```

**What you'll see:**
```
🧠 HIKING DRONE ASSISTANT - INITIALIZATION
[1/4] Initializing group monitor... ✓
[2/4] Initializing voice commander... ✓
[3/4] Initializing AI brain... ✓
[4/4] Initializing hiking assistant... ✓

✓ ALL SYSTEMS INITIALIZED

🟢 HIKING DRONE ASSISTANT STARTED

════════════════════════════════════════════════════
📡 CENTER REPORT | 2024-06-23T15:30:00
Group: HIKING_DEMO_001
Total: 5 | Present: 5 | Missing: 0
Avg Temp: 37.2°C | Avg HR: 73 bpm
Group Center: (100.5, 2.1) | Spread: 8.3m
════════════════════════════════════════════════════
```

---

## 🎯 Project Overview

### **What This Project Does**

You have a **forest hiking group** with multiple people. This system provides:

1. **🏥 Health Monitoring** - Tracks body temperature, heart rate, GPS signal for each hiker
2. **🚁 Drone Assistant** - Autonomous drone that follows the group and monitors them
3. **🧠 AI Brain** - Claude AI makes decisions autonomously (say "AI on")
4. **🎤 Voice Control** - Natural language commands: "Follow", "Scan", "AI on"
5. **🚨 Emergency Detection** - Alerts when someone goes missing or has health issues
6. **📊 Reports** - Every 60 seconds, sends complete group status to command center

### **Key Features**

| Feature | Details |
|---------|---------|
| **Group Tracking** | Monitor up to any number of hikers in real-time |
| **Health Scanning** | Temperature, heart rate, GPS signal strength per person |
| **Missing Person Detection** | Automatic alert if hiker not detected for 60+ seconds |
| **Reports to Center** | Every 1 minute with full health statistics and alerts |
| **Autonomous AI** | Claude AI decides drone actions (follow, search, scan) |
| **Voice Control** | Whisper-based speech recognition + natural language |
| **Real-time HUD** | Live video feed with status, detections, AI decisions |
| **Emergency Mode** | Automatic search pattern when someone goes missing |

---

## 🏗️ System Architecture

### **Component Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                   HIKING DRONE SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HIKING GROUP (Forest)                                      │
│  ├─ Alice: 37.2°C, 72 bpm, GPS (100, 50)                  │
│  ├─ Bob:   36.8°C, 68 bpm, GPS (105, 48)                  │
│  ├─ Charlie: 37.5°C, 75 bpm, GPS (102, 52)                │
│  ├─ Diana: 38.2°C, 85 bpm, GPS (98, 55)                   │
│  └─ Eve:   NOT DETECTED ← MISSING                          │
│         ↓                                                   │
│  GROUP MONITOR (tracks health every update)                │
│  ├─ Health scanning                                        │
│  ├─ Missing person detection                               │
│  └─ Emergency alerts                                       │
│         ↓                                                   │
│  REPORTS TO CENTER (every 60 seconds)                      │
│  └─ \"Alice: 37.2°C | Bob: 36.8°C | Eve: MISSING\"        │
│         ↓                                                   │
│  HIKING ASSISTANT (integration layer)                      │
│  └─ Connects Monitor + Brain + Voice                       │
│         ↓                                                   │
│  ┌──────────────────┬──────────────────┬──────────────┐    │
│  │                  │                  │              │    │
│  ↓                  ↓                  ↓              ↓    │
│  DRONE CONTROL   VOICE COMMAND    AI BRAIN       HUD      │
│  ├─ Position     ├─ \"Forward\"    ├─ Analyzes   ├─ Live  │
│  ├─ Altitude     ├─ \"AI on\"      ├─ Decides    │  Video │
│  ├─ Movement     ├─ \"Follow\"     └─ Acts       └─ Detections
│  └─ Follow group └─ \"Scan\"                            │
│         ↓                 ↓           ↓              ↓    │
│         └─────────────────┴───────────┴──────────────┘    │
│                    ↓                                       │
│         WEBOTS SIMULATION (3D environment)                │
│         └─ DJI Mavic 2 Pro drone physics                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Data Flow During Operation**

```
Every ~33ms (Simulation Loop):
  └─ Read drone position, altitude, sensors
  └─ YOLOv8 detects people in camera
  └─ Check if keyboard/voice input
  └─ Send action to drone

Every 1 second (Monitoring):
  └─ Update hiker positions (simulated GPS)
  └─ Check if missing persons threshold crossed

Every 5 seconds (AI Brain):
  └─ Build situation context from drone state
  └─ Send to Claude API
  └─ Receive decision (action + reasoning)
  └─ Execute action

Every 60 seconds (Center Report):
  └─ Compile health statistics
  └─ Generate alerts if any
  └─ Print formatted report
  └─ Trigger emergency mode if needed
```

---

## 📦 Installation

### **Prerequisites**

- **Python 3.8+**
- **Webots 2023b** (for simulation)
- **Microphone** (for voice commands, optional)
- **Internet** (for Claude AI, optional)

### **Step 1: Install Webots**

```bash
# Linux/macOS
wget https://github.com/cyberbotics/webots/releases/download/R2023b/webots-R2023b-x86-64.tar.bz2
tar xjf webots-R2023b-x86-64.tar.bz2
export WEBOTS_HOME=/path/to/webots

# Or download from https://cyberbotics.com/download
```

### **Step 2: Clone Repository**

```bash
git clone https://github.com/JamieUA/webot-project.git
cd webot-project
```

### **Step 3: Install Python Dependencies**

```bash
# Core dependencies
pip install -r requirements.txt

# Specific packages:
pip install numpy
pip install gym
pip install ultralytics          # YOLOv8 for person detection
pip install openai-whisper       # Speech recognition
pip install sounddevice          # Microphone input
pip install anthropic            # Claude AI (optional)
pip install simple-pid           # PID control
pip install opencv-python        # Video processing
```

### **Step 4: Verify Installation**

```bash
# Check Webots
echo $WEBOTS_HOME  # Should show path to webots

# Test imports
python -c "from webots_drone import group_monitor; print('✓ Group monitor imported')"
python -c "from webots_drone import claude_brain; print('✓ Claude brain imported')"
python -c "from webots_drone import voice_commander; print('✓ Voice commander imported')"

# Run tests
python -c "from webots_drone.group_monitor import GroupMonitor; m = GroupMonitor('test'); print('✓ All systems ready')"
```

---

## ⚙️ Configuration

### **Step 1: Set Webots Environment**

```bash
# Linux/macOS
export WEBOTS_HOME=/opt/webots

# Windows (PowerShell)
$env:WEBOTS_HOME="C:\Program Files\Webots"

# Verify
echo $WEBOTS_HOME
```

### **Step 2: Configure Claude AI (Optional but Recommended)**

1. **Get API Key:**
   - Go to https://console.anthropic.com
   - Sign up or login
   - Navigate to API Keys
   - Create new key (copy it)

2. **Set Environment Variable:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxx"
   ```

3. **Or hardcode in code:**
   Edit `webots_drone/webots_simulation.py` line 278:
   ```python
   ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxx"  # ← Paste here
   USE_CLAUDE_BRAIN  = True
   ```

### **Step 3: Configure Voice Recognition (Optional)**

Voice works automatically with Whisper (no API needed). To test:

```bash
# Test microphone input
python -c "
import sounddevice as sd
import numpy as np
print('Recording 3 seconds...')
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1)
sd.wait()
print('✓ Microphone working')
"
```

### **Step 4: Configure Group Parameters**

Edit `hiking_drone_main.py` or `webots_drone/group_monitor.py`:

```python
# Report interval (seconds)
monitor = GroupMonitor(
    group_id="HIKING_GROUP_001",
    report_interval=60,        # ← Change this (1 minute default)
    missing_timeout=60         # ← How long before marking missing
)

# Health alert thresholds
monitor.temp_low_threshold = 35.0   # Hypothermia alert
monitor.temp_high_threshold = 38.5  # Fever alert
monitor.heart_rate_low = 50         # Low HR alert
monitor.heart_rate_high = 120       # High HR alert
monitor.gps_signal_threshold = 30.0 # Weak GPS alert
```

---

## 🎮 Usage Guide

### **Method 1: Hiking Demo (Easiest)**

```bash
python hiking_drone_main.py
```

**What happens:**
- Starts monitoring 5 simulated hikers
- Walks them through a 5-minute forest hike
- Shows health updates and alerts
- Demonstrates missing person detection

**Output:**
```
🚁 HIKING DRONE ASSISTANT
Forest Hike Monitoring System

[1/4] Initializing group monitor... ✓ Group monitor ready
[2/4] Initializing voice commander... ⊘ Voice commander not available
[3/4] Initializing AI brain... ⊘ AI brain not configured
[4/4] Initializing hiking assistant... ✓ Hiking assistant ready

════════════════════════════════════════════════════
🟢 Monitoring started for group HIKING_DEMO_001
════════════════════════════════════════════════════

Added hiker: Alice Johnson (ID: H001)
Added hiker: Bob Smith (ID: H002)
Added hiker: Charlie Brown (ID: H003)
Added hiker: Diana Prince (ID: H004)
Added hiker: Eve Wilson (ID: H005)

🟢 HIKING DRONE ASSISTANT STARTED
Ready to monitor group and respond to voice commands
```

### **Method 2: Full Webots Simulation (Interactive)**

```bash
cd webots_drone
python webots_simulation.py
```

**Initial Setup:**
1. Webots window opens with drone in 3D forest scene
2. Console shows available controls
3. Click Webots 3D window to focus it
4. Press W to take off

**Live Controls:**

```
KEYBOARD (Click Webots window first):
  Arrow UP/DOWN      → Fly forward/backward
  Arrow LEFT/RIGHT   → Strafe left/right
  W / S              → Altitude up/down
  A / D              → Turn left/right
  F                  → Toggle FOLLOW mode
  B                  → Toggle AI BRAIN
  X                  → Toggle SCAN mode
  P                  → Take screenshot
  Q                  → Quit

VOICE (Say clearly into microphone):
  "Forward"          → Fly forward
  "Back"             → Fly backward
  "Left"             → Strafe left
  "Right"            → Strafe right
  "Up"               → Ascend
  "Down"             → Descend
  "Stop"             → Hover
  "Turn left"        → Rotate left
  "Turn right"       → Rotate right
  "Follow"           → Follow detected person
  "Scan"             → Start search pattern
  "Manual"           → Manual control mode
  "AI on"            → Enable autonomous AI
  "AI off"           → Disable autonomous AI
  "Quit"             → Stop and exit
```

**Console Output:**
```
Simulation running! Click the 3D window then press W to take off.

[Voice] Listening... speak clearly into your mic
[Detector] YOLOv8 model loaded
[Brain] Claude AI decision layer initialised.

--- Iteration 1 ---
  >>> Hovering (no input yet)

--- Iteration 2 ---
  >>> Person detected (in frame)

[Brain] #1 → follow_person | Person in frame | (high urgency)
[Follow] Moving to center person in frame
```

### **Method 3: Manual Integration**

```python
from webots_drone.group_monitor import GroupMonitor, DroneFollower
from webots_drone.hiking_integration import HikingAssistant
from webots_drone.voice_commander import VoiceCommander
from webots_drone.claude_brain import ClaudeBrain

# Create monitor
monitor = GroupMonitor("MY_GROUP", report_interval=60)

# Add hikers
monitor.add_person("P1", "Alice")
monitor.add_person("P2", "Bob")

# Start monitoring
monitor.start_monitoring()

# Simulate hike
for i in range(100):
    # Update positions (would come from real GPS)
    monitor.update_person_location("P1", i * 2, 0, 0)
    monitor.update_person_location("P2", i * 2 + 1, 1, 0)
    
    # Scan health
    monitor.scan_person_health("P1", 37.2, 72, 95)
    monitor.scan_person_health("P2", 36.8, 68, 98)
    
    time.sleep(1)

monitor.stop_monitoring()
```

---

## 🥾 Hiking Scenario Explained

### **What is the Hiking Scenario?**

A realistic forest hiking expedition where:

1. **5 hikers** start a trek into the forest
2. **Drone monitors** them from above
3. **Every 60 seconds**, health report sent to command center
4. **One hiker (Diana)** starts falling behind (fever 38.2°C)
5. **Another hiker (Eve)** gets lost in the forest
6. **Drone must respond** to emergencies

### **Timeline**

```
T+0:00    Hike begins
          └─ All 5 hikers at starting position

T+0:30    Warm up phase
          └─ Normal temperatures (36.8-37.5°C)
          └─ Normal heart rates (68-75 bpm)

T+1:00    FIRST REPORT
          ├─ All present
          ├─ Avg Temp: 37.2°C ✓
          ├─ Avg HR: 71 bpm ✓
          └─ Group spread: 8.3m

T+2:00    Diana showing symptoms
          ├─ Temperature rising (37.8°C)
          ├─ Heart rate elevated (78 bpm)
          └─ Still moving with group

T+2:30    Eve starts lagging
          └─ Falls 50m behind group

T+3:00    SECOND REPORT
          ├─ Diana: 38.2°C ⚠️  (FEVER ALERT)
          ├─ Eve: NOT DETECTED 🚨 (MISSING)
          └─ AI brain triggers search mode

T+3:10    Drone enters EMERGENCY MODE
          ├─ Automatically switches to SCAN
          ├─ Starts moving toward last known Eve position
          └─ AI analyzes camera for Eve

T+4:00    THIRD REPORT
          ├─ Diana: Still high temp, needs rest
          ├─ Eve: Still missing (65+ seconds)
          └─ Group spread: 12.1m (increased)

T+5:00    Hike ends / Demo complete
          └─ All statistics printed
```

### **Group Member Simulation**

In the demo, hiker positions are simulated as:

```python
# Everyone walks forward together
base_x = elapsed_time * 100  # 100m per minute

# Slight spread
positions = [
    (base_x + 0,  0),   # Alice - center
    (base_x + 2,  -1),  # Bob - slightly right
    (base_x + 1,  2),   # Charlie - slightly back-right
    (base_x - 1,  1),   # Diana - slightly forward-left
    (base_x - 2,  -2),  # Eve - will become missing
]

# After 65% of time, Eve stops updating (marked missing)
if time > 0.65 * total_time and person == "Eve":
    # Don't update position → marked missing
    person.last_seen_time = current_time - 70
```

### **Health Simulation**

```python
# Each person has slightly different health
temperature = 37.0 + (person_index * 0.2)
heart_rate = 75 + (person_index * 2)
gps_signal = 95 - (time % 10)  # Varies with time

# Diana shows symptoms after 2 minutes
if person == "Diana" and time > 120:
    temperature += 1.0  # Fever developing
    heart_rate += 5     # Stress response
```

---

## 🧠 AI Brain Mode

### **What is AI Mode?**

When you say **"AI on"**, the drone becomes autonomous:

- **Every 5 seconds**, Claude AI analyzes the current situation
- **Claude decides** what the drone should do next
- **Drone executes** the decision automatically
- **You can still override** with voice commands or keyboard

### **How to Enable AI Brain**

**Option 1: Voice**
```
Say: "AI on"
```

**Option 2: Keyboard**
```
Press: B (in Webots window)
```

**Option 3: Code**
```python
brain_active = True
```

### **What AI Considers**

Each decision, Claude analyzes:

```
DRONE STATE:
  ├─ Position (X, Y meters)
  ├─ Altitude (meters)
  ├─ Camera view (what can it see?)
  ├─ Current mode (follow/scan/ai)
  └─ Operator voice commands

CLAUDE DECIDES:
  ├─ Action (hover, move_forward, follow, scan, etc)
  ├─ Reason (why this action?)
  ├─ Urgency (low/medium/high)
  └─ Status message (what to display)
```

### **AI Decision Rules**

```
IF person detected in camera AND not following
  → follow_person (high urgency)

ELSE IF no person AND in scan mode
  → keep searching (turn_right or move_forward)

ELSE IF altitude < 3m
  → ascend (safety first)

ELSE IF altitude > 60m
  → descend (too high)

ELSE IF operator said something
  → honor their command

ELSE
  → hover (safe default)
```

### **Console Output**

When AI is running, you'll see:

```
[Brain] #1 → hover | Waiting for target | (low urgency)
[Brain] #2 → follow_person | Person detected | (high urgency)
[Brain] #3 → move_forward | Searching for target | (medium urgency)
```

Each line = new decision (every 5 seconds)

### **HUD Display**

On the video feed, you'll see:

```
┌─────────────────────────────────────────┐
│ MODE: ai  BRAIN: ON  MSG: Following... │
│ ALT: 25.3m  PEOPLE: 2 detected         │
└─────────────────────────────────────────┘
```

---

## 🎤 Voice Commands

### **Setup Voice Control**

Voice works automatically with Whisper (free, no API needed).

**First time:**
```bash
# Whisper will download model (~1.4 GB for "tiny")
python -c "import whisper; whisper.load_model('tiny')"
```

### **All Voice Commands**

```
AI BRAIN:
  "AI on"           → Enable autonomous AI
  "AI off"          → Disable autonomous AI
  "Brain on"        → Same as "AI on"
  "Activate AI"     → Same as "AI on"

MOVEMENT:
  "Forward"         → Move forward
  "Back"            → Move backward
  "Left"            → Strafe left
  "Right"           → Strafe right
  "Up"              → Ascend
  "Down"            → Descend
  "Stop"            → Hover in place
  "Turn left"       → Rotate counterclockwise
  "Turn right"      → Rotate clockwise

MODES:
  "Follow"          → Follow detected person
  "Manual"          → Disable AI, manual mode
  "Scan"            → Start search pattern

EXIT:
  "Quit"            → Stop simulation
  "Exit"            → Stop simulation
  "Land"            → Stop simulation
```

### **How Voice Works**

```
1. You speak into microphone
2. Whisper transcribes to text (runs locally)
3. Keywords matched to commands
4. Command executed

Example:
  You say: "Move forward and scan the area"
  ↓
  Whisper: "move forward and scan the area"
  ↓
  Matching: finds "forward" and "scan"
  ↓
  Commands: [move forward] → [scan mode]
  ↓
  Drone executes both commands
```

---

## 📊 Group Monitoring

### **What Gets Monitored**

For each hiker:

| Metric | Range | Alert If |
|--------|-------|----------|
| **Temperature** | 35-40°C | < 35°C or > 38.5°C |
| **Heart Rate** | 50-120 bpm | < 50 or > 120 |
| **GPS Signal** | 0-100% | < 30% |
| **Position** | GPS coords | Updated every cycle |
| **Last Seen** | Timestamp | Missing if > 60s |

### **Report Format (Every 60 Seconds)**

```
════════════════════════════════════════════════════════════════
📡 CENTER REPORT | 2024-06-23T15:30:45
Group: HIKING_GROUP_001 | Total: 5 | Present: 4 | Missing: 1
Avg Temp: 37.3°C | Avg HR: 75 bpm
Group Center: (100.5, 2.1) | Spread: 8.3m

⚠️  ALERTS:
   🔥 FEVER: Diana - 38.2°C
   🚨 MISSING: Eve - Not detected 60s

DETAILED PERSON DATA:
   ✓ Alice: 37.2°C, 72 bpm, GPS (100, 50), Present
   ✓ Bob: 36.8°C, 68 bpm, GPS (105, 48), Present
   ✓ Charlie: 37.5°C, 75 bpm, GPS (102, 52), Present
   ⚠️ Diana: 38.2°C, 85 bpm, GPS (98, 55), Present - FEVER
   ✗ Eve: Not detected, GPS (---, ---), MISSING

════════════════════════════════════════════════════════════════
```

### **Alert Levels**

```
🟢 NORMAL     - All within range
🟡 WARNING    - Temperature/HR slightly off, or weak GPS
🔴 CRITICAL   - Temperature/HR dangerous levels
🚨 EMERGENCY  - Missing person detected
```

### **How Missing Person Detection Works**

```
IF hiker.last_seen_time > 60 seconds ago:
  → Mark as missing
  → Print alert
  → Trigger emergency callback
  → AI brain notified

DEFAULT: 60 seconds
Can be changed: monitor.missing_timeout = 120
```

---

## 🔧 Troubleshooting

### **Problem: "No API key set — AI brain disabled"**

**Cause:** Claude AI not configured

**Solution:**
```bash
# Option 1: Set environment variable
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Option 2: Edit webots_simulation.py line 278
ANTHROPIC_API_KEY = "sk-ant-xxxxx"

# Option 3: Get free key at https://console.anthropic.com
```

### **Problem: "Failed to import claude_brain"**

**Cause:** anthropic library not installed

**Solution:**
```bash
pip install anthropic
```

### **Problem: "Whisper model not found"**

**Cause:** Voice recognition model needs download

**Solution:**
```bash
python -c "import whisper; whisper.load_model('tiny')"
# Will download ~1.4 GB
```

### **Problem: "No microphone detected"**

**Cause:** Sounddevice can't find microphone

**Solution:**
```bash
# List devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Use specific device
# Edit voice_commander.py to use device index
```

### **Problem: "Webots window not responding"**

**Cause:** Webots needs focus

**Solution:**
1. Click on Webots 3D window
2. Press spacebar to unpause simulation
3. Try keyboard command again

### **Problem: "Drone doesn't follow person"**

**Cause:** FOLLOW mode not enabled

**Solution:**
```bash
# Press F to toggle follow mode
# Or say "follow"
# Or press B to enable AI (AI will auto-follow if person detected)
```

### **Problem: "Reports not printing"**

**Cause:** Monitor not started or report interval not reached

**Solution:**
```bash
# Make sure to call
monitor.start_monitoring()

# Check report interval
monitor.report_interval = 30  # Print every 30 seconds instead of 60

# Wait at least 60 seconds (or configured interval)
```

### **Problem: "API rate limit exceeded"**

**Cause:** Too many Claude requests

**Solution:**
```bash
# Increase cooldown between AI queries
brain = ClaudeBrain(api_key=api_key, cooldown_seconds=10.0)
# Default 5.0, change to 10.0 or higher
```

### **Problem: "WEBOTS_HOME not found"**

**Cause:** Environment variable not set

**Solution:**
```bash
# Set it
export WEBOTS_HOME=/opt/webots

# Verify
echo $WEBOTS_HOME  # Should show path

# Make it permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export WEBOTS_HOME=/opt/webots' >> ~/.bashrc
source ~/.bashrc
```

---

## 📁 File Structure

```
webot-project/
├── README.md                          ← You are here
├── requirements.txt                   ← Python dependencies
├── setup.py                           ← Install script
├── AI_BRAIN_GUIDE.md                 ← Detailed AI docs
├── hiking_drone_main.py               ← Hiking demo (easiest start)
│
├── webots_drone/
│   ├── __init__.py
│   ├── webots_simulation.py           ← Main Webots integration
│   ├── claude_brain.py                ← AI decision making
│   ├── voice_commander.py             ← Speech recognition
│   ├── group_monitor.py               ← Hiking group tracking
│   ├── hiking_integration.py          ← Integration layer
│   ├── detector.py                    ← YOLOv8 person detection
│   ├── follower.py                    ← Follow-person logic
│   ├── scan_mode.py                   ← Search patterns
│   ├── hud_overlay.py                 ← Video HUD display
│   ├── reward.py                      ← Reward calculations
│   ├── target.py                      ← Target tracking
│   ├── data.py                        ← Data structures
│   ├── utils.py                       ← Utility functions
│   ├── cf_simulation.py               ← Crazyflie sim (legacy)
│   ├── envs/                          ← Gym environments
│   │   └── (environment definitions)
│   ├── controllers/                   ← Webots controllers
│   │   ├── drone_controller/
│   │   ├── fire_movement/
│   │   ├── crazyflie_controller/
│   │   └── pedestrian_controller/
│   │
│   └── worlds/                        ← Webots simulation scenes
│       ├── forest_tower.wbt
│       ├── forest_tower_200x200_simple.wbt
│       └── crazyflie_2.5x2.5_simple.wbt
│
├── protos/                            ← Webots PROTO files
│   ├── RadioController.proto
│   └── FireSmoke.proto
│
├── yolov8n.pt                         ← Pre-trained YOLOv8 model
│
└── photos/                            ← Screenshot storage
    └── (drone camera captures)
```

---

## 🎓 Example Usage Scenarios

### **Scenario 1: Just Monitor a Group (No AI, No Voice)**

```python
from webots_drone.group_monitor import GroupMonitor
import time

# Create monitor
monitor = GroupMonitor("HIKING_001", report_interval=60)

# Add hikers
for i in range(5):
    monitor.add_person(f"P{i}", f"Hiker {i}")

# Start
monitor.start_monitoring()

# Simulate hike for 10 minutes
for minute in range(10):
    # Update positions (would come from GPS in real system)
    for i in range(5):
        x = minute * 100 + (i * 5)
        y = (i - 2) * 3
        monitor.update_person_location(f"P{i}", x, y)
        
        # Scan health
        temp = 37.0 + (i * 0.1)
        hr = 75 + (i * 2)
        monitor.scan_person_health(f"P{i}", temp, int(hr), 95.0)
    
    time.sleep(60)

monitor.stop_monitoring()
```

### **Scenario 2: Full Autonomous with AI + Voice**

```bash
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
export WEBOTS_HOME=/opt/webots

cd webots_drone
python webots_simulation.py

# Then:
# 1. Click Webots window
# 2. Say "AI on"
# 3. Say "Follow"
# 4. Watch drone autonomously track group
```

### **Scenario 3: Detect Emergency and Alert**

```python
from webots_drone.group_monitor import GroupMonitor

monitor = GroupMonitor("EMERGENCY_TEST")

def on_emergency(person_name, emergency_type):
    print(f"🚨 EMERGENCY: {person_name} is {emergency_type}")
    # Could integrate with SMS, email, etc.

monitor.on_emergency_callback = on_emergency
monitor.add_person("E1", "Eve")
monitor.start_monitoring()

# Simulate missing person
import time
time.sleep(65)  # Wait for missing timeout
monitor.check_missing_persons()  # Triggers callback
```

---

## 📚 References

### **External Documentation**

- **Webots:** https://cyberbotics.com/doc/guide/
- **Claude API:** https://docs.anthropic.com/
- **YOLOv8:** https://docs.ultralytics.com/
- **Whisper:** https://github.com/openai/whisper
- **OpenAI Gym:** https://www.gymlibrary.dev/

### **Research Papers**

- Butler, C. (1998). "Firefighter Safety Zones: A Theoretical Model Based on Radiative Heating"
- OpenAI. (2018). "OpenAI Gym" - https://arxiv.org/abs/1606.01540

### **Original Project**

This project extends [gym-webots-drone](https://github.com/angel-ayala/gym-webots-drone) by Angel Ayala with:
- Real-time group monitoring
- Health tracking
- AI decision making
- Voice control
- Emergency detection

---

## 📝 License

GNU General Public License v3.0 - See LICENSE file

---

## 🤝 Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** See AI_BRAIN_GUIDE.md
- **Questions:** Check this README first

---

## 🚀 Next Steps

1. **Install everything** → Follow Installation section
2. **Run the demo** → `python hiking_drone_main.py`
3. **Try manual control** → `python webots_drone/webots_simulation.py`
4. **Enable AI** → Say "AI on" or press B
5. **Monitor health** → Watch 1-minute center reports

**Happy autonomous hiking! 🚁🏕️**
