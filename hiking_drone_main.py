#!/usr/bin/env python3
"""
hiking_drone_main.py — Complete Hiking Drone Assistant

Full integration of:
  ✓ Group monitoring (tracks hikers, health, missing persons)
  ✓ AI brain (Claude autonomous decisions)
  ✓ Voice commands (natural language control)
  ✓ Drone following (tracks group centroid)
  ✓ Emergency alerts (1-minute reports to center)

Usage:
    python hiking_drone_main.py
"""

import os
import sys
import time
import threading
from typing import Optional

# Add webots_drone to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webots_drone'))

try:
    from webots_drone.group_monitor import GroupMonitor, DroneFollower
    from webots_drone.hiking_integration import HikingAssistant
    from webots_drone.voice_commander import VoiceCommander
    VOICE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import voice commander: {e}")
    VOICE_AVAILABLE = False

try:
    from webots_drone.claude_brain import ClaudeBrain
    BRAIN_AVAILABLE = True
except ImportError:
    print("[WARNING] Claude brain not available")
    BRAIN_AVAILABLE = False


class HikingDroneController:
    """
    Main controller for hiking drone assistant.
    """
    
    def __init__(self, group_id: str = "EXPEDITION_001", 
                 api_key: Optional[str] = None):
        """
        Initialize hiking drone controller.
        
        Args:
            group_id: Group identifier
            api_key: Anthropic API key for Claude Brain
        """
        self.group_id = group_id
        self.running = False
        
        # Initialize components
        print("\n" + "="*80)
        print("🚁 HIKING DRONE ASSISTANT - INITIALIZATION")
        print("="*80)
        
        # Group monitoring
        print("\n[1/4] Initializing group monitor...")
        self.monitor = GroupMonitor(
            group_id=group_id,
            report_interval=60,  # 1 minute
            missing_timeout=60   # 1 minute before marking missing
        )
        print("     ✓ Group monitor ready")
        
        # Voice commander
        print("\n[2/4] Initializing voice commander...")
        self.voice_commander = None
        if VOICE_AVAILABLE:
            try:
                self.voice_commander = VoiceCommander(model="tiny")
                self.voice_commander.start()
                print("     ✓ Voice commander ready")
            except Exception as e:
                print(f"     ✗ Voice commander failed: {e}")
        else:
            print("     ⊘ Voice commander not available")
        
        # AI Brain
        print("\n[3/4] Initializing AI brain...")
        self.brain = None
        if BRAIN_AVAILABLE and api_key:
            try:
                self.brain = ClaudeBrain(api_key=api_key, cooldown_seconds=5.0)
                print("     ✓ AI brain ready")
            except Exception as e:
                print(f"     ✗ AI brain failed: {e}")
        else:
            print("     ⊘ AI brain not configured")
        
        # Hiking assistant
        print("\n[4/4] Initializing hiking assistant...")
        self.assistant = HikingAssistant(
            monitor=self.monitor,
            brain=self.brain,
            voice_commander=self.voice_commander
        )
        print("     ✓ Hiking assistant ready")
        
        # Drone follower
        self.drone_follower = DroneFollower(
            monitor=self.monitor,
            follow_distance=30.0,
            altitude=20.0
        )
        
        print("\n" + "="*80)
        print("✓ ALL SYSTEMS INITIALIZED")
        print("="*80 + "\n")
    
    def add_hiker(self, person_id: str, name: str) -> None:
        """
        Add a hiker to the group.
        
        Args:
            person_id: Unique ID
            name: Hiker's name
        """
        self.monitor.add_person(person_id, name)
    
    def start(self) -> None:
        """
        Start the hiking drone assistant.
        """
        self.running = True
        self.monitor.start_monitoring()
        print("\n🟢 HIKING DRONE ASSISTANT STARTED")
        print("Ready to monitor group and respond to voice commands")
        if self.brain:
            print("AI brain is in standby (say 'ai on' to activate)")
    
    def stop(self) -> None:
        """
        Stop the hiking drone assistant.
        """
        self.running = False
        self.monitor.stop_monitoring()
        if self.voice_commander:
            self.voice_commander.stop()
        print("\n🔴 HIKING DRONE ASSISTANT STOPPED")
    
    def update_hiker_location(self, person_id: str, x: float, y: float, 
                            z: float = 0.0) -> None:
        """
        Update hiker location (would come from real GPS in production).
        
        Args:
            person_id: Hiker ID
            x, y, z: Coordinates
        """
        self.monitor.update_person_location(person_id, x, y, z)
    
    def scan_hiker_health(self, person_id: str, temperature: float, 
                         heart_rate: int, gps_signal: float) -> None:
        """
        Scan hiker health metrics.
        
        Args:
            person_id: Hiker ID
            temperature: Body temperature (°C)
            heart_rate: Heart rate (bpm)
            gps_signal: GPS signal strength (0-100%)
        """
        alerts = self.monitor.scan_person_health(
            person_id, temperature, heart_rate, gps_signal
        )
        if alerts:
            for alert in alerts:
                print(f"[ALERT] {alert}")
    
    def get_group_status(self) -> dict:
        """
        Get current group status.
        
        Returns:
            Status dictionary
        """
        stats = self.monitor.get_statistics()
        report = self.monitor.generate_report()
        return {
            'statistics': stats,
            'group_center': report.group_position,
            'group_spread': report.group_spread,
            'missing_persons': report.missing_ids,
            'critical_alerts': report.critical_alerts
        }
    
    def get_drone_action(self) -> tuple:
        """
        Get next drone action for following group.
        
        Returns:
            Tuple of (roll, pitch, yaw, throttle)
        """
        return self.drone_follower.get_next_action()


def demo_hiking_scenario():
    """
    Run a demo hiking scenario.
    """
    # Create controller (without API key - AI brain will be disabled)
    controller = HikingDroneController(
        group_id="HIKING_DEMO_001",
        api_key=None  # Set your key here for AI brain
    )
    
    # Add hikers
    print("\nAdding hikers to group...")
    hikers = [
        ("H001", "Alice Johnson"),
        ("H002", "Bob Smith"),
        ("H003", "Charlie Brown"),
        ("H004", "Diana Prince"),
        ("H005", "Eve Wilson"),
    ]
    
    for hiker_id, name in hikers:
        controller.add_hiker(hiker_id, name)
    
    # Start monitoring
    controller.start()
    
    print("\n" + "="*80)
    print("📊 DEMO: Simulating 5-minute hiking expedition")
    print("="*80)
    
    try:
        start_time = time.time()
        duration = 300  # 5 minutes
        
        while time.time() - start_time < duration and controller.running:
            elapsed = time.time() - start_time
            progress = elapsed / duration
            
            # Simulate hiking progress
            base_x = progress * 500  # 500m forward
            base_y = 0
            
            # Update each hiker's position and health
            for i, (hiker_id, name) in enumerate(hikers):
                # Position with slight offset
                x = base_x + (i * 2)
                y = (i - 2) * 3
                z = 0
                
                controller.update_hiker_location(hiker_id, x, y, z)
                
                # Health metrics
                temp = 37.0 + (i * 0.2)
                hr = 75 + (i * 2)
                gps = 95 - (int(elapsed) % 10)
                
                # Simulate one person lagging behind (Diana)
                if i == 3 and elapsed > duration * 0.65:
                    # Don't update position - will be marked missing
                    pass
                else:
                    controller.scan_hiker_health(hiker_id, temp, int(hr), gps)
            
            # Get drone action
            action = controller.get_drone_action()
            
            # Print status every minute (when report is sent)
            if controller.monitor.should_report():
                status = controller.get_group_status()
                print(f"\n[T+{elapsed:.0f}s] Group status:")
                print(f"  - Position: {status['group_center']}")
                print(f"  - Spread: {status['group_spread']:.1f}m")
                if status['missing_persons']:
                    print(f"  - ⚠️  MISSING: {status['missing_persons']}")
            
            time.sleep(5)  # Update every 5 seconds
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        controller.stop()
        print("\n" + "="*80)
        print("Demo completed")
        print("="*80)


if __name__ == "__main__":
    print("\n🚁 HIKING DRONE ASSISTANT")
    print("Forest Hike Monitoring System\n")
    
    # Run demo
    demo_hiking_scenario()
