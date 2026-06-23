"""
group_monitor.py — Hiking Group Monitoring System for Drone

Monitors a group of hikers in a forest:
  - Tracks GPS positions of each hiker
  - Scans body temperature and heart rate
  - Detects missing persons (timeout-based)
  - Sends health reports to command center every 60 seconds
  - Maintains drone follow position relative to group centroid
  - Integrates with Claude AI Brain for autonomous decision making
  - Voice commands for hiker management
"""

import threading
import time
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PersonData:
    """Data structure for individual hiker"""
    id: str
    name: str
    position: Tuple[float, float, float]  # x, y, z (GPS)
    body_temperature: float  # Celsius
    heart_rate: int  # bpm
    gps_signal_strength: float  # 0-100%
    last_seen_time: float
    is_missing: bool = False
    alerts: List[str] = None
    health_history: List[Dict] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []
        if self.health_history is None:
            self.health_history = []


@dataclass
class GroupReport:
    """Report structure for command center"""
    timestamp: str
    group_id: str
    total_persons: int
    present_persons: int
    missing_persons: int
    missing_ids: List[str]
    average_temperature: float
    temperature_alerts: List[Dict]
    average_heart_rate: int
    heart_rate_alerts: List[Dict]
    group_position: Tuple[float, float]  # centroid
    group_spread: float  # radius in meters
    all_persons: List[Dict]
    critical_alerts: List[str]


class GroupMonitor:
    """
    Monitors a group of hikers on a forest hike using a drone.
    Tracks positions, health metrics, detects missing persons, and reports to center.
    """

    def __init__(self, group_id: str, report_interval: int = 60, 
                 missing_timeout: int = 60):
        """
        Initialize the group monitoring system.
        
        Args:
            group_id: Unique identifier for the hiking group
            report_interval: Seconds between center reports (default 60 = 1 minute)
            missing_timeout: Seconds before person marked missing
        """
        self.group_id = group_id
        self.report_interval = report_interval
        self.missing_timeout = missing_timeout
        
        # Group data management
        self.persons: Dict[str, PersonData] = {}
        self.lock = threading.Lock()
        
        # Alert thresholds
        self.temp_low_threshold = 35.0  # degrees C (hypothermia)
        self.temp_high_threshold = 38.5  # degrees C (fever)
        self.heart_rate_low = 50  # bpm
        self.heart_rate_high = 120  # bpm
        self.gps_signal_threshold = 30.0  # percent
        
        # History
        self.reports_sent = []
        self.alerts_log = []
        self.last_report_time = time.time()
        
        # Thread control
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Callbacks
        self.on_report_callback = None
        self.on_emergency_callback = None

    def add_person(self, person_id: str, name: str) -> None:
        """
        Add a person to monitor in the group.
        
        Args:
            person_id: Unique identifier for the person
            name: Person's name
        """
        with self.lock:
            self.persons[person_id] = PersonData(
                id=person_id,
                name=name,
                position=(0.0, 0.0, 0.0),
                body_temperature=37.0,
                heart_rate=70,
                gps_signal_strength=100.0,
                last_seen_time=time.time()
            )
        print(f"[GROUP] Added hiker: {name} (ID: {person_id})")

    def update_person_location(self, person_id: str, x: float, y: float, z: float = 0.0) -> None:
        """
        Update a person's GPS location.
        
        Args:
            person_id: Person's ID
            x, y, z: Coordinates in meters
        """
        with self.lock:
            if person_id in self.persons:
                self.persons[person_id].position = (x, y, z)
                self.persons[person_id].last_seen_time = time.time()
                self.persons[person_id].is_missing = False

    def scan_person_health(self, person_id: str, temperature: float, heart_rate: int,
                          gps_strength: float) -> List[str]:
        """
        Scan and update a person's health metrics.
        
        Args:
            person_id: Person's ID
            temperature: Body temperature in Celsius
            heart_rate: Heart rate in bpm
            gps_strength: GPS signal strength 0-100%
            
        Returns:
            List of alerts generated for this person
        """
        alerts = []
        
        with self.lock:
            if person_id not in self.persons:
                return alerts
            
            person = self.persons[person_id]
            person.body_temperature = temperature
            person.heart_rate = heart_rate
            person.gps_signal_strength = gps_strength
            
            # Store history
            person.health_history.append({
                'timestamp': datetime.now().isoformat(),
                'temperature': temperature,
                'heart_rate': heart_rate,
                'gps_signal': gps_strength
            })
            # Keep last 100 samples
            if len(person.health_history) > 100:
                person.health_history = person.health_history[-100:]
            
            # Check temperature
            if temperature < self.temp_low_threshold:
                alert = f"🌡️  HYPOTHERMIA: {person.name} - {temperature}°C"
                alerts.append(alert)
                self.alerts_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'person': person.name,
                    'type': 'temperature_low',
                    'value': temperature,
                    'level': AlertLevel.CRITICAL.value
                })
            elif temperature > self.temp_high_threshold:
                alert = f"🔥 FEVER: {person.name} - {temperature}°C"
                alerts.append(alert)
                self.alerts_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'person': person.name,
                    'type': 'temperature_high',
                    'value': temperature,
                    'level': AlertLevel.WARNING.value
                })
            
            # Check heart rate
            if heart_rate < self.heart_rate_low:
                alert = f"❤️  LOW HR: {person.name} - {heart_rate} bpm"
                alerts.append(alert)
                self.alerts_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'person': person.name,
                    'type': 'heart_rate_low',
                    'value': heart_rate,
                    'level': AlertLevel.WARNING.value
                })
            elif heart_rate > self.heart_rate_high:
                alert = f"❤️  HIGH HR: {person.name} - {heart_rate} bpm"
                alerts.append(alert)
                self.alerts_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'person': person.name,
                    'type': 'heart_rate_high',
                    'value': heart_rate,
                    'level': AlertLevel.WARNING.value
                })
            
            # Check GPS signal
            if gps_strength < self.gps_signal_threshold:
                alert = f"📡 WEAK GPS: {person.name} - Signal {gps_strength:.0f}%"
                alerts.append(alert)
            
            person.alerts = alerts
        
        return alerts

    def check_missing_persons(self) -> List[str]:
        """
        Check for missing persons based on last seen time.
        
        Returns:
            List of missing person IDs
        """
        current_time = time.time()
        missing_ids = []
        
        with self.lock:
            for person_id, person in self.persons.items():
                time_since_seen = current_time - person.last_seen_time
                
                if time_since_seen > self.missing_timeout and not person.is_missing:
                    person.is_missing = True
                    alert = f"🚨 MISSING: {person.name} - Not detected for {time_since_seen:.0f}s"
                    self.alerts_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'person': person.name,
                        'type': 'missing_person',
                        'duration': time_since_seen,
                        'level': AlertLevel.EMERGENCY.value
                    })
                    print(alert)
                    # Trigger emergency callback
                    if self.on_emergency_callback:
                        self.on_emergency_callback(person.name, 'missing')
                
                if person.is_missing:
                    missing_ids.append(person_id)
        
        return missing_ids

    def get_group_centroid(self) -> Tuple[float, float]:
        """
        Calculate the centroid of the group (average position).
        
        Returns:
            Tuple of (x, y) coordinates
        """
        with self.lock:
            if not self.persons:
                return (0.0, 0.0)
            
            positions = [p.position for p in self.persons.values() if not p.is_missing]
            if not positions:
                return (0.0, 0.0)
            
            x_avg = np.mean([p[0] for p in positions])
            y_avg = np.mean([p[1] for p in positions])
            
            return (x_avg, y_avg)

    def get_group_spread(self) -> float:
        """
        Calculate the spread/radius of the group.
        
        Returns:
            Maximum distance from centroid in meters
        """
        with self.lock:
            if len(self.persons) < 2:
                return 0.0
            
            centroid = self.get_group_centroid()
            max_distance = 0.0
            
            for person in self.persons.values():
                if not person.is_missing:
                    distance = np.sqrt(
                        (person.position[0] - centroid[0])**2 +
                        (person.position[1] - centroid[1])**2
                    )
                    max_distance = max(max_distance, distance)
            
            return max_distance

    def generate_report(self) -> GroupReport:
        """
        Generate a comprehensive report of the group status.
        
        Returns:
            GroupReport object
        """
        with self.lock:
            present_count = sum(1 for p in self.persons.values() if not p.is_missing)
            missing_ids = [p.id for p in self.persons.values() if p.is_missing]
            
            # Get health metrics from present persons only
            present_persons = [p for p in self.persons.values() if not p.is_missing]
            temperatures = [p.body_temperature for p in present_persons]
            heart_rates = [p.heart_rate for p in present_persons]
            
            # Find temperature anomalies
            temp_alerts = []
            for person in present_persons:
                if (person.body_temperature < self.temp_low_threshold or
                    person.body_temperature > self.temp_high_threshold):
                    temp_alerts.append({
                        'person': person.name,
                        'temperature': person.body_temperature,
                        'status': 'abnormal'
                    })
            
            # Find heart rate anomalies
            hr_alerts = []
            for person in present_persons:
                if (person.heart_rate < self.heart_rate_low or
                    person.heart_rate > self.heart_rate_high):
                    hr_alerts.append({
                        'person': person.name,
                        'heart_rate': person.heart_rate,
                        'status': 'abnormal'
                    })
            
            # Collect critical alerts
            critical_alerts = []
            for person in self.persons.values():
                critical_alerts.extend(person.alerts)
            critical_alerts.extend([f"MISSING: {pid}" for pid in missing_ids])
            
            # Prepare person data
            persons_data = []
            for person in self.persons.values():
                persons_data.append({
                    'id': person.id,
                    'name': person.name,
                    'position': person.position,
                    'temperature': person.body_temperature,
                    'heart_rate': person.heart_rate,
                    'gps_signal': person.gps_signal_strength,
                    'is_missing': person.is_missing
                })
            
            report = GroupReport(
                timestamp=datetime.now().isoformat(),
                group_id=self.group_id,
                total_persons=len(self.persons),
                present_persons=present_count,
                missing_persons=len(missing_ids),
                missing_ids=missing_ids,
                average_temperature=float(np.mean(temperatures)) if temperatures else 0.0,
                temperature_alerts=temp_alerts,
                average_heart_rate=int(np.mean(heart_rates)) if heart_rates else 0,
                heart_rate_alerts=hr_alerts,
                group_position=self.get_group_centroid(),
                group_spread=self.get_group_spread(),
                all_persons=persons_data,
                critical_alerts=critical_alerts
            )
        
        return report

    def send_report_to_center(self, report: GroupReport) -> bool:
        """
        Send report to command center (console output for now).
        
        Args:
            report: GroupReport object
            
        Returns:
            True if successful
        """
        try:
            report_dict = asdict(report)
            self.reports_sent.append(report_dict)
            
            print("\n" + "="*80)
            print(f"📡 CENTER REPORT | {report.timestamp}")
            print(f"Group: {report.group_id} | Total: {report.total_persons} | Present: {report.present_persons} | Missing: {report.missing_persons}")
            print(f"Avg Temp: {report.average_temperature:.1f}°C | Avg HR: {report.average_heart_rate} bpm")
            print(f"Group Center: ({report.group_position[0]:.1f}, {report.group_position[1]:.1f}) | Spread: {report.group_spread:.1f}m")
            
            if report.critical_alerts:
                print("\n⚠️  ALERTS:")
                for alert in report.critical_alerts:
                    print(f"   {alert}")
            
            if report.missing_ids:
                print(f"\n🚨 MISSING PERSONS: {', '.join(report.missing_ids)}")
            
            print("="*80 + "\n")
            
            # Trigger callback
            if self.on_report_callback:
                self.on_report_callback(report_dict)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send report: {e}")
            return False

    def should_report(self) -> bool:
        """
        Check if enough time has passed for next report.
        
        Returns:
            True if report interval has elapsed
        """
        now = time.time()
        if now - self.last_report_time >= self.report_interval:
            self.last_report_time = now
            return True
        return False

    def start_monitoring(self) -> None:
        """Start the background monitoring thread."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print(f"[GROUP] Monitoring started for group {self.group_id}")

    def stop_monitoring(self) -> None:
        """Stop the background monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print(f"[GROUP] Monitoring stopped for group {self.group_id}")

    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        while self.monitoring_active:
            try:
                # Check for missing persons
                self.check_missing_persons()
                
                # Send report every report_interval seconds
                if self.should_report():
                    report = self.generate_report()
                    self.send_report_to_center(report)
                
                time.sleep(1)  # Check every second
            
            except Exception as e:
                print(f"[ERROR] Monitoring loop: {e}")

    def get_statistics(self) -> Dict:
        """
        Get current group statistics.
        
        Returns:
            Dictionary with group statistics
        """
        with self.lock:
            if not self.persons:
                return {}
            
            present_persons = [p for p in self.persons.values() if not p.is_missing]
            temperatures = [p.body_temperature for p in present_persons]
            heart_rates = [p.heart_rate for p in present_persons]
            
            return {
                'total_persons': len(self.persons),
                'missing_persons': sum(1 for p in self.persons.values() if p.is_missing),
                'temperature': {
                    'average': float(np.mean(temperatures)) if temperatures else 0.0,
                    'min': float(np.min(temperatures)) if temperatures else 0.0,
                    'max': float(np.max(temperatures)) if temperatures else 0.0
                },
                'heart_rate': {
                    'average': int(np.mean(heart_rates)) if heart_rates else 0,
                    'min': int(np.min(heart_rates)) if heart_rates else 0,
                    'max': int(np.max(heart_rates)) if heart_rates else 0
                },
                'group_spread': self.get_group_spread(),
                'total_alerts': len(self.alerts_log)
            }


class DroneFollower:
    """
    Drone controller that follows the group and maintains formation.
    """

    def __init__(self, monitor: GroupMonitor, follow_distance: float = 30.0, 
                 altitude: float = 20.0):
        """
        Initialize drone follower.
        
        Args:
            monitor: GroupMonitor instance
            follow_distance: Horizontal distance to maintain from group (meters)
            altitude: Altitude to maintain (meters)
        """
        self.monitor = monitor
        self.follow_distance = follow_distance
        self.altitude = altitude
        self.drone_position = np.array([0.0, 0.0, altitude])

    def calculate_target_position(self) -> Tuple[float, float, float]:
        """
        Calculate drone target position based on group centroid.
        
        Returns:
            Target position (x, y, z)
        """
        group_center = self.monitor.get_group_centroid()
        
        # Position drone offset from group center to maintain formation
        offset_x = group_center[0] + self.follow_distance
        offset_y = group_center[1] + self.follow_distance * 0.5
        
        return (offset_x, offset_y, self.altitude)

    def get_next_action(self) -> Tuple[float, float, float, float]:
        """
        Get next drone action (roll, pitch, yaw, throttle).
        
        Returns:
            Tuple of (roll, pitch, yaw, throttle) in continuous space
        """
        target = self.calculate_target_position()
        current = self.drone_position
        
        # Calculate direction to target
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dz = target[2] - current[2]
        
        # Simple proportional control
        roll = np.clip(dx * 0.01, -0.5, 0.5)
        pitch = np.clip(dy * 0.01, -0.5, 0.5)
        throttle = np.clip(dz * 0.02, -0.5, 0.5)
        yaw = 0.0  # Maintain heading
        
        return (roll, pitch, yaw, throttle)
