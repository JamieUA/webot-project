# 🧠 AI Brain Mode - Complete Guide

## What is AI Mode?

**AI Mode** turns your drone into an **autonomous intelligent assistant** that makes decisions automatically using Claude AI. Instead of you manually controlling the drone, Claude's brain analyzes the situation and decides what the drone should do next.

---

## 🎯 What AI Mode DOES

### 1. **Continuous Situation Analysis** (Every 5 Seconds)
AI sends the current drone state to Claude and receives decisions:

```
AI asks Claude:
├─ Where is the drone? (GPS position)
├─ How high is it? (altitude)
├─ Are people detected in camera? (person tracking)
├─ What's the current mode? (follow/scan/ai)
└─ Did the operator say anything? (voice commands)

Claude responds with:
├─ Action: move_forward | hover | follow_person | scan | etc
├─ Reason: Why it chose this action
├─ Urgency: low | medium | high
└─ Status Message: Display text for HUD
```

### 2. **Smart Decision Making**
Claude uses these rules:

| Situation | AI Decision |
|-----------|-----------|
| Person detected in camera | Follow them automatically |
| Scanning, no person found | Keep searching (rotate/move) |
| Too low (< 3m) | Ascend (safety first) |
| Too high (> 60m) | Descend to safe altitude |
| User gave voice command | Honor the command |
| No emergency | Hover safely |

### 3. **Updates Flow** 📊

```
Hiking Group → GPS Positions + Health Data
                      ↓
            GROUP MONITOR (every 60 seconds)
                      ↓
        ┌─ CENTER REPORT (Health, Missing, Alerts)
        │
        └─ DRONE STATUS UPDATES
                      ↓
            AI BRAIN ANALYSIS (every 5 seconds)
                      ↓
    Claude AI Decision (Action + Reasoning)
                      ↓
        Drone executes action automatically
                      ↓
        HUD displays "Analyzing... Following target"
```

---

## 🚀 How to Use AI Mode

### **Step 1: Set Your API Key**

Edit `webots_drone/webots_simulation.py` (line ~278):

```python
# ------ LINE 278 ------
ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxxxxxxxxxx"  # ← Paste your key here
USE_CLAUDE_BRAIN  = True
# -------- END --------
```

**Get your API key:**
1. Go to https://console.anthropic.com
2. Create account or login
3. Go to API Keys → Create Key
4. Copy the key (starts with `sk-ant-`)
5. Paste in the file above

### **Step 2: Start the Simulation**

```bash
# In your terminal, make sure WEBOTS_HOME is set
export WEBOTS_HOME=/path/to/webots

# Run the simulation
python webots_drone/webots_simulation.py
```

### **Step 3: Activate AI Brain**

**Option A: Voice Command**
```
Say clearly into your microphone:
"AI on"  or  "activate AI"  or  "enable AI"
```

**Option B: Keyboard**
```
Press: B (with Webots window focused)
```

**Output:**
```
[Brain] Ready — say 'ai on' or press B to activate.
[Key B] AI Brain ON
[Brain] Claude AI decision layer initialised.
```

---

## 📊 What You'll See

### **Console Output During AI Mode:**

```
[Brain] #1 → hover | Waiting for target | (low urgency)
[Brain] #2 → follow_person | Person in frame | (high urgency)
[Brain] #3 → move_forward | Searching for target | (medium urgency)
```

### **HUD Display (Top of Video):**

```
┌─────────────────────────────────────────────┐
│ MODE: ai  BRAIN: ON  MSG: Following target  │
│ ALT: 25.3m  PEOPLE: 2 detected (center)     │
│ DETECTIONS: confidence 0.95                 │
└─────────────────────────────────────────────┘
```

### **Brain Message Examples:**

```
"Analyzing..."                    → Thinking, no decision yet
"Following target"                → Person detected, moving toward
"Searching for person"            → Scan mode, looking around
"Safety ascent"                   → Too low, going up
"Maintaining altitude"            → All good, hovering
"Person lost - rotating"          → Lost track, searching
```

---

## 🔄 Complete Data Flow

### **Real-Time Updates (Every Second)**

```
DRONE SIMULATION (Webots)
    ↓
Position: (x, y, z)
Camera: Image frame
Altitude: 25.3m
    ↓
DETECTION (YOLOv8)
    ├─ Person at x=150, bbox=100px wide
    └─ Confidence: 0.95
    ↓
AI BRAIN (Every 5 sec)
    ├─ Input: Position + Detection + Mode + Voice
    │
    ├─ Claude API Call:
    │   "Drone at (50, 30), 25m high, person in center..."
    │
    └─ Response: {action: "follow_person", urgency: "high"}
    ↓
DRONE ACTION
    ├─ Roll: +0.2 (lean right toward person)
    ├─ Pitch: -0.1 (lean forward to follow)
    └─ Yaw: 0 (maintain heading)
    ↓
HUD UPDATE
    └─ "Following target"
    ↓
REPEAT
```

### **Group Monitoring (Every 60 Seconds = 1 MINUTE)**

```
HIKING GROUP
    ├─ Alice: Temp 37.2°C, HR 72 bpm, GPS (100, 50)
    ├─ Bob:   Temp 36.8°C, HR 68 bpm, GPS (105, 48)
    ├─ Charlie: Temp 37.5°C, HR 75 bpm, GPS (102, 52)
    ├─ Diana: Temp 38.2°C, HR 85 bpm, GPS (98, 55)  ← HIGH TEMP
    └─ Eve:   NOT DETECTED ← MISSING!
    ↓
GROUP MONITOR (Analyzes)
    ├─ Missing: 1 person (Eve) - not seen for 60+ seconds
    ├─ Health: Diana has fever (38.2°C)
    └─ Emergency: YES
    ↓
REPORT TO CENTER (Printed/Logged)
    ┌─────────────────────────────────────────────┐
    │ 📡 CENTER REPORT | 2024-06-23T15:30:45      │
    │ Group: HIKING_GROUP_001                     │
    │ Total: 5 | Present: 4 | Missing: 1          │
    │ Avg Temp: 37.5°C | Avg HR: 75 bpm          │
    │                                             │
    │ ⚠️  ALERTS:                                   │
    │   🔥 FEVER: Diana - 38.2°C                  │
    │   🚨 MISSING: Eve - Not detected 60s        │
    │                                             │
    │ GROUP POSITION: (101.5, 51.2) | Spread: 8m │
    └─────────────────────────────────────────────┘
    ↓
AI BRAIN INTEGRATION
    └─ Recommends: "Enter search mode for missing person"
    ↓
DRONE ACTION TRIGGERED
    └─ Automatically switches to SCAN mode
```

---

## 💬 Voice Commands Reference

### **AI Brain Controls**
```
"AI on"            → Enable autonomous brain
"AI off"           → Disable autonomous brain
"Brain on/off"     → Toggle brain
```

### **Movement (Works in Manual OR AI Mode)**
```
"Forward"          → Move forward
"Back"             → Move backward
"Go left"          → Strafe left
"Go right"         → Strafe right
"Up"               → Ascend
"Down"             → Descend
"Turn left"        → Rotate left
"Turn right"       → Rotate right
"Stop"             → Hover in place
```

### **Mode Commands**
```
"Follow"           → Follow detected person
"Manual"           → Disable AI & follow, back to manual
"Scan"             → Autonomous search pattern
```

### **Exit**
```
"Quit"  or  "Exit" or  "Land"  → Stop simulation
```

---

## 🎮 Keyboard Shortcuts (Alternative)

```
Arrow UP/DOWN      → Pitch (forward/backward)
Arrow LEFT/RIGHT   → Roll (strafe)
W / S              → Altitude (up/down)
A / D              → Yaw (turn)
F                  → Toggle FOLLOW mode
B                  → Toggle AI BRAIN ← This activates AI!
X                  → Toggle SCAN mode
P                  → Take photo
Q                  → Quit
```

---

## 📋 Action Priority (What AI Actually Does)

When AI is ON, it has this decision hierarchy:

```
1. KEYBOARD INPUT (if you press a key)
   └─ Overrides everything, AI pauses

2. FOLLOW MODE + Person Detected
   └─ AI keeps person centered in frame

3. FOLLOW MODE + No Person
   └─ AI searches gently (rotate)

4. SCAN MODE (AI searching)
   └─ Rotation sweep pattern

5. VOICE CARRY-OVER (timed movement from voice command)
   └─ Hold movement for ~1 second

6. AI BRAIN DECISION (every 5 sec from Claude)
   └─ Autonomous action based on situation

7. DEFAULT: HOVER
   └─ Stay in place, hold altitude
```

---

## 🎯 Real Example: Complete Scenario

### **You Say: "AI on"**
```
✓ AI brain activates
  [Brain] Claude AI decision layer initialised.
```

### **Drone sees a person**
```
[Brain] #1 → follow_person | Person detected | (high urgency)
HUD: "Following target"
Action: Roll +0.2, Pitch -0.1 (follow person)
```

### **Person exits camera**
```
[Brain] #2 → turn_right | Lost target, searching | (medium urgency)
HUD: "Searching for person"
Action: Yaw +0.3 (rotate right)
```

### **Person re-enters camera**
```
[Brain] #3 → follow_person | Target reacquired | (high urgency)
HUD: "Following target"
Action: Back to following
```

### **You say: "scan" (operator override)**
```
Voice heard: "scan"
[Voice] SCAN ON
AI Brain PAUSES (you're in control now)
HUD: "scan"
```

### **You say: "AI on"**
```
AI resumes full autonomy
```

---

## ⚙️ Configuration Options

Edit `webots_drone/webots_simulation.py`:

```python
# Line 278-280
ANTHROPIC_API_KEY = "sk-ant-..."   # Your API key
USE_CLAUDE_BRAIN  = True            # Enable/disable AI

# In ClaudeBrain init (line 295)
brain = ClaudeBrain(api_key=ANTHROPIC_API_KEY, cooldown_seconds=5.0)
                                    # ↑ Change this for faster/slower decisions
                                    #   5.0 = query Claude every 5 seconds
                                    #   3.0 = faster decisions
                                    #   10.0 = slower, saves API calls
```

---

## 🚨 Troubleshooting

### **Problem: "No API key set — AI brain disabled"**
- **Solution:** Set `ANTHROPIC_API_KEY` in `webots_simulation.py` (line 278)

### **Problem: "API error" in console**
- **Cause:** Bad API key or no internet connection
- **Solution:** Verify key at https://console.anthropic.com/api/keys

### **Problem: Brain not responding**
- **Cause:** Currently busy processing previous query
- **Check:** Wait for `[Brain] #X →` message (X increments each decision)
- **Fix:** Increase `cooldown_seconds` if too many API errors

### **Problem: AI decides wrong thing**
- **Note:** Claude is intelligent but not perfect in simulation
- **Fix:** Use voice commands to override: "manual" to disable AI, then "AI on" to re-enable

---

## 📊 Group Monitor + AI Brain Together

### **How They Work Together:**

```
GROUP MONITORING (Your hiking group)
    ├─ Tracks 5 hikers
    ├─ Scans health every update
    ├─ Reports every 60 seconds
    └─ Detects missing persons
            ↓
        REPORTS HEALTH ALERTS
            ↓
        AI BRAIN INTEGRATION
            ├─ Receives alert: "Diana has fever (38.2°C)"
            ├─ Receives alert: "Eve is MISSING"
            └─ Receives alert: "Group spread is 12m"
            ↓
        CLAUDE AI ANALYZES
            ├─ Current situation: Group in trouble
            ├─ Camera: Person detected 50m away
            ├─ Decision: "Should search for missing person"
            └─ Action: move_forward + ascend
            ↓
        DRONE EXECUTES
            └─ Automatically moves to search coordinates
            ↓
        NEXT REPORT (60 sec)
            ├─ Missing person still missing?
            ├─ Diana's fever getting worse?
            └─ AI re-adjusts strategy
```

---

## 🔗 Integration with Your Hiking Scenario

Your new files work like this:

```
hiking_drone_main.py (Main executable)
    ├─ Creates GroupMonitor (tracks hikers)
    ├─ Creates VoiceCommander (listens for commands)
    ├─ Creates ClaudeBrain (AI decision making)
    └─ Creates HikingAssistant (binds everything together)
            ↓
        GROUP MONITOR
            ├─ Scans health every cycle
            └─ Reports to center every 60 seconds
            ��
        HEALTH ALERTS
            ├─ Too hot/cold? Alert
            ├─ Too high/low HR? Alert
            └─ Missing person? Emergency
            ↓
        AI BRAIN SEES ALERTS
            ├─ Analyzes situation
            ├─ Gets camera detections
            └─ Makes autonomous decision
            ↓
        DRONE FOLLOWS GROUP
            └─ Automatically maintains position over group centroid
```

---

## 📝 Summary

| Aspect | Details |
|--------|---------|
| **What it does** | Makes autonomous drone decisions using AI |
| **How often** | Every 5 seconds (configurable) |
| **Input data** | Position, altitude, detections, voice, mode |
| **Output** | Action + Reasoning + Urgency level |
| **Activation** | Say "AI on" or Press B |
| **Updates** | Real-time console, HUD display, group reports |
| **API** | Anthropic Claude (requires free API key) |
| **Integration** | Works with group monitor, voice, follow mode |
| **Override** | Any keyboard input or voice command overrides AI |

---

## 🎓 Next Steps

1. **Get API Key:** https://console.anthropic.com
2. **Set in Code:** Edit `webots_simulation.py` line 278
3. **Run Demo:** `python hiking_drone_main.py`
4. **Say "AI on":** Let it fly autonomously
5. **Monitor Hikers:** Watch 1-minute health reports
6. **Watch HUD:** See what AI decides in real-time

---

**Happy autonomous hiking! 🚁🏕️**
