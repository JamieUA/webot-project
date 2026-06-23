"""
pedestrian_controller.py — Makes the pedestrian walk back and forth in Webots.

IMPORTANT — TWO THINGS REQUIRED IN WEBOTS:
============================================
1. The Pedestrian node needs supervisor = TRUE
   - Click the Pedestrian node in scene tree
   - Find the 'supervisor' field → set it to TRUE

2. The controller field must be set to 'pedestrian_controller'
   - Find the 'controller' field → type: pedestrian_controller

3. This file must be placed at:
   controllers/pedestrian_controller/pedestrian_controller.py

4. Save world (Ctrl+S) and restart simulation.

WHY supervisor=TRUE is needed:
  We use getSelf() + getField('translation') to teleport the
  pedestrian each step. Without supervisor rights, getSelf()
  returns None and the controller crashes silently.

ALTERNATIVE (if you cannot set supervisor=TRUE):
  Use a Motor node instead — but the Pedestrian PROTO doesn't
  have motors, so supervisor-teleport is the correct approach.
"""

from controller import Supervisor
import math

def main():
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())

    # Get own node
    self_node = robot.getSelf()
    if self_node is None:
        print("[Pedestrian] ERROR: getSelf() returned None!")
        print("[Pedestrian] Make sure 'supervisor' field = TRUE in the Pedestrian node.")
        # Still run the loop so Webots doesn't complain
        while robot.step(timestep) != -1:
            pass
        return

    translation_field = self_node.getField('translation')
    rotation_field    = self_node.getField('rotation')

    if translation_field is None or rotation_field is None:
        print("[Pedestrian] ERROR: Could not get translation/rotation fields.")
        while robot.step(timestep) != -1:
            pass
        return

    # Walk parameters — tune these
    WALK_DISTANCE = 8.0    # metres each direction before turning around
    WALK_SPEED    = 0.9    # metres per second

    direction = 1.0        # +1 = +X axis, -1 = -X axis
    walked    = 0.0

    start_pos = translation_field.getSFVec3f()
    print(f"[Pedestrian] Controller active. Starting pos: {[round(v,2) for v in start_pos]}")
    print(f"[Pedestrian] Walking {WALK_DISTANCE}m each way at {WALK_SPEED} m/s")

    while robot.step(timestep) != -1:
        dt   = timestep / 1000.0
        pos  = translation_field.getSFVec3f()

        move  = WALK_SPEED * dt * direction
        new_x = pos[0] + move
        walked += abs(move)

        # Teleport pedestrian to new position (keep Y height and Z unchanged)
        translation_field.setSFVec3f([new_x, pos[1], pos[2]])

        # Turn around when walked far enough
        if walked >= WALK_DISTANCE:
            direction *= -1
            walked = 0.0
            rot = rotation_field.getSFRotation()
            rotation_field.setSFRotation([0, 1, 0, rot[3] + math.pi])
            print(f"[Pedestrian] Turning at x={new_x:.1f} — now going {'→' if direction > 0 else '←'}", flush=True)

main()