"""
hiking_integration.py — Integration module for hiking scenario

Connects GroupMonitor with Claude Brain and Voice Commander.
Provides decision making for drone to follow group and respond to emergencies.
"""

import threading
import time
from typing import Optional, Dict, List
from group_monitor import GroupMonitor, GroupReport


class HikingAssistant:
    """
    Integrates group monitoring with AI brain for autonomous decision making.
    """
    
    def __init__(self, monitor: GroupMonitor, brain=None, voice_commander=None):
        """
        Initialize hiking assistant.
        
        Args:
            monitor: GroupMonitor instance
            brain: Claude AI brain (optional)
            voice_commander: Voice commander (optional)
        """
        self.monitor = monitor
        self.brain = brain
        self.voice_commander = voice_commander
        self.last_decision = None
        self.emergency_mode = False
        self.emergency_person = None
        
        # Set callbacks
        self.monitor.on_report_callback = self._on_report
        self.monitor.on_emergency_callback = self._on_emergency
    
    def _on_report(self, report_dict: Dict) -> None:
        """
        Called when center report is sent.
        
        Args:
            report_dict: Report dictionary
        """
        # Check if we need to alert via AI brain
        if report_dict.get('critical_alerts') and self.brain and self.brain._decision:
            missing = report_dict.get('missing_persons', 0)
            if missing > 0:
                self.emergency_mode = True
    
    def _on_emergency(self, person_name: str, emergency_type: str) -> None:
        """
        Called when emergency detected.
        
        Args:
            person_name: Name of person in emergency
            emergency_type: Type of emergency (missing, health, etc)
        """
        print(f"\n🚨 EMERGENCY ALERT: {person_name} - {emergency_type}")
        self.emergency_mode = True
        self.emergency_person = person_name
        
        # Voice alert
        if self.voice_commander:
            try:
                # Could integrate with text-to-speech here
                print(f"[VOICE] Emergency: {person_name} is {emergency_type}")
            except:
                pass
    
    def get_ai_recommendation(self, detections: List, position: List, 
                            altitude: float) -> Optional[Dict]:
        """
        Get AI recommendation based on group status and detections.
        
        Args:
            detections: YOLOv8 detections from camera
            position: Current drone position
            altitude: Current altitude
            
        Returns:
            Decision dictionary from Claude Brain
        """
        if not self.brain:
            return None
        
        # Get group status
        stats = self.monitor.get_statistics()
        group_center = self.monitor.get_group_centroid()
        
        # Build context about group
        group_context = (
            f"Hiking group status:\n"
            f"  Position: ({group_center[0]:.1f}, {group_center[1]:.1f})\n"
            f"  Persons present: {stats.get('missing_persons', 0)} missing out of {stats.get('total_persons', 0)}\n"
            f"  Avg temperature: {stats.get('temperature', {}).get('average', 0):.1f}°C\n"
            f"  Avg heart rate: {stats.get('heart_rate', {}).get('average', 0)} bpm\n"
            f"  Group spread: {stats.get('group_spread', 0):.1f}m"
        )
        
        # Update brain with context
        # Note: This would need custom context handling in claude_brain.py
        
        return self.last_decision
    
    def should_follow_group(self) -> bool:
        """
        Determine if drone should follow the group.
        
        Returns:
            True if drone should follow group
        """
        stats = self.monitor.get_statistics()
        return stats.get('missing_persons', 0) == 0
    
    def should_search_missing(self) -> bool:
        """
        Determine if drone should search for missing persons.
        
        Returns:
            True if missing persons detected
        """
        stats = self.monitor.get_statistics()
        return stats.get('missing_persons', 0) > 0
    
    def get_search_priority(self) -> Optional[str]:
        """
        Get ID of missing person to search for.
        
        Returns:
            Person ID or None
        """
        report = self.monitor.generate_report()
        if report.missing_ids:
            return report.missing_ids[0]  # Search for first missing person
        return None


def simulate_hiking_scenario(duration_seconds: int = 300):
    """
    Simulate a complete hiking scenario with group monitoring.
    
    Args:
        duration_seconds: Duration of simulation
    """
    # Create group monitor
    monitor = GroupMonitor(
        group_id="HIKING_EXPEDITION_001",
        report_interval=60,  # 1 minute reports
        missing_timeout=60   # 1 minute before marked missing
    )
    
    # Add group members
    monitor.add_person("H001", "Alice Johnson")
    monitor.add_person("H002", "Bob Smith")
    monitor.add_person("H003", "Charlie Brown")
    monitor.add_person("H004", "Diana Prince")
    monitor.add_person("H005", "Eve Wilson")
    
    # Start monitoring
    monitor.start_monitoring()
    
    print("\n" + "="*80)
    print("🏔️  HIKING GROUP MONITORING SCENARIO")
    print("="*80)
    print(f"Monitoring {len(monitor.persons)} hikers")
    print(f"Report interval: {monitor.report_interval} seconds")
    print(f"Missing timeout: {monitor.missing_timeout} seconds")
    print("="*80 + "\n")
    
    try:
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < duration_seconds:
            iteration += 1
            elapsed = time.time() - start_time
            
            # Simulate hiking progress
            progress = elapsed / duration_seconds
            base_x = progress * 500  # 500m forward
            base_y = 0
            altitude = 0
            
            # Simulate group movement (staying together)
            positions = [
                (base_x, base_y, altitude),
                (base_x + 5, base_y - 3, altitude),
                (base_x - 2, base_y + 4, altitude),
                (base_x + 3, base_y + 2, altitude),
                (base_x - 4, base_y - 1, altitude),
            ]
            
            person_ids = list(monitor.persons.keys())
            
            # Update positions and health
            for i, person_id in enumerate(person_ids):
                if i < len(positions):
                    x, y, z = positions[i]
                    monitor.update_person_location(person_id, x, y, z)
                    
                    # Simulate health variations
                    temp = 37.0 + (i * 0.3)  # Slight variations
                    hr = 75 + (i * 3)
                    gps = 95 - (iteration % 5)
                    
                    # Simulate one person missing after 2/3 of time
                    if i == 3 and elapsed > duration_seconds * 0.65:
                        # Skip position update for Diana (mark as missing)
                        monitor.persons[person_id].last_seen_time = time.time() - 70
                    else:
                        monitor.scan_person_health(person_id, temp, int(hr), gps)
            
            time.sleep(5)  # Update every 5 seconds
    
    finally:
        monitor.stop_monitoring()
        print("\n[Monitoring] Stopped")
        
        # Print final statistics
        stats = monitor.get_statistics()
        print("\nFinal Statistics:")
        print(f"  Total persons: {stats.get('total_persons', 0)}")
        print(f"  Missing: {stats.get('missing_persons', 0)}")
        print(f"  Avg Temperature: {stats.get('temperature', {}).get('average', 0):.1f}°C")
        print(f"  Avg Heart Rate: {stats.get('heart_rate', {}).get('average', 0)} bpm")
        print(f"  Total Reports Sent: {len(monitor.reports_sent)}")
        print(f"  Total Alerts: {len(monitor.alerts_log)}")


if __name__ == "__main__":
    # Run 5-minute demo
    simulate_hiking_scenario(duration_seconds=300)
