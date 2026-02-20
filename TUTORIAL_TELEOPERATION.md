# Teleoperation Tutorial (Part 3)

Mirror the manual movement of one servo (leader) to another servo (follower) in real-time.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Hardware Setup](#hardware-setup)
- [Tutorial Steps](#tutorial-steps)
  - [Step 1: Identify Your Serial Ports](#step-1-identify-your-serial-ports)
  - [Step 2: Connect to Both Servos](#step-2-connect-to-both-servos)
  - [Step 3: Verify Both Servos](#step-3-verify-both-servos)
  - [Step 4: Synchronize Starting Positions](#step-4-synchronize-starting-positions)
  - [Step 5: Basic Position Mirroring](#step-5-basic-position-mirroring)
  - [Step 6: Teleoperation with Speed Matching](#step-6-teleoperation-with-speed-matching)
  - [Step 7: Bidirectional Teleoperation](#step-7-bidirectional-teleoperation)
  - [Step 8: Clean Shutdown](#step-8-clean-shutdown)
- [Complete Example](#complete-example)

---

## Prerequisites

Before starting this tutorial:

1. Complete [Part 1 (README.md)](./README.md) and [Part 2 (TUTORIAL_SERVO_CLASS.md)](./TUTORIAL_SERVO_CLASS.md)
2. Have **two** Waveshare Serial Bus Servo Driver Boards
3. Have **two** STS3215 servos (one connected to each board)
4. Both boards powered and connected via USB to your computer
5. Ensure `servo.py` is in your working directory

---

## Hardware Setup

For teleoperation, you need two independent servo setups:

| Component | Leader Setup | Follower Setup |
|-----------|--------------|----------------|
| Servo | STS3215 #1 | STS3215 #2 |
| Driver Board | Waveshare Board #1 | Waveshare Board #2 |
| USB Connection | USB Port #1 | USB Port #2 |
| Power | 12V or 7.4V supply | 12V or 7.4V supply |

Each servo connects to its own Waveshare board, and each board has its own USB connection to your computer. This gives you two independent serial ports.

**Why two boards?** Each Waveshare board has one serial port. To read from the leader and write to the follower simultaneously without bus conflicts, they need separate communication channels.

---

## Tutorial Steps

### Step 1: Identify Your Serial Ports

With both Waveshare boards connected, list the available serial ports to identify them.

```python
import serial.tools.list_ports

# List all available serial ports
ports = serial.tools.list_ports.comports()

print("Available serial ports:")
for port in ports:
    print(f"  {port.device}")
    print(f"    Description: {port.description}")
    print()
```

Expected output (your port names will differ):

```
Available serial ports:
  /dev/cu.usbmodem5AE60577551
    Description: USB Single Serial

  /dev/cu.usbmodem5AE60543861
    Description: USB Single Serial
```

You should see two `usbmodem` ports. Note both port names for the next step.

**Tip**: If you're unsure which port is which, unplug one board and run the code again to see which port disappears.

---

### Step 2: Connect to Both Servos

Create two Servo instances, one for each board.

```python
from servo import Servo

# Replace with your actual port names from Step 1
leader_port = '/dev/cu.usbmodem5AE60577551'
follower_port = '/dev/cu.usbmodem5AE60543861'

# Connect to both servos
leader = Servo(port=leader_port)
follower = Servo(port=follower_port)

print("Connected to both servos")
```

---

### Step 3: Verify Both Servos

Ping each servo to confirm communication.

```python
print("=== Leader Servo ===")
leader.ping()

print("\n=== Follower Servo ===")
follower.ping()
```

Expected output:

```
=== Leader Servo ===
✓ Serial comm port: /dev/cu.usbmodem5AE60577551
✓ Successfully pinged servo ID 1
✓ Model number: 777

=== Follower Servo ===
✓ Serial comm port: /dev/cu.usbmodem5AE60543861
✓ Successfully pinged servo ID 1
✓ Model number: 777
```

---

### Step 4: Synchronize Starting Positions

Move both servos to the same starting position.

```python
# Move both to center position
start_position = 2048  # 180 degrees

leader.move_to(start_position)
follower.move_sync(start_position)  # Wait for follower to arrive

# Verify positions match
leader_pos, leader_deg = leader.position()
follower_pos, follower_deg = follower.position()

print(f"Leader position:   {leader_pos} ({leader_deg:.1f}°)")
print(f"Follower position: {follower_pos} ({follower_deg:.1f}°)")
```

Expected output:

```
Leader position:   2048 (180.0°)
Follower position: 2048 (180.0°)
```

---

### Step 5: Basic Position Mirroring

Disable the leader's torque so you can move it by hand, then read its position and send it to the follower.

```python
import time

# Disable leader torque so it can be moved by hand
leader.disable_torque()

print("Move the leader servo by hand!")
print("The follower will mirror the position.")

# Mirror for 10 seconds
duration = 10
start = time.time()

while time.time() - start < duration:
    # Read leader position
    pos, deg = leader.position()

    # Send to follower
    follower.move_to(pos)

print("Done mirroring!")
```

Try moving the leader servo horn by hand. The follower should track the position in near real-time.

---

### Step 6: Teleoperation with Speed Matching

For smoother follower movement, also read the leader's speed and pass it to the follower.

```python
import time

# Disable leader torque
leader.disable_torque()

print("Teleoperation with speed matching")
print("Move the leader servo by hand!")

duration = 20
start = time.time()

while time.time() - start < duration:
    # Read leader status
    info = leader.status()
    pos = info['position'][0]      # Raw position
    speed = abs(info['speed'])     # Speed magnitude

    # Move follower with matching speed
    follower.move_to(pos, speed=speed)

print("Teleoperation complete!")
```

The follower now matches both the position and speed of the leader, resulting in smoother tracking.

---

### Step 7: Bidirectional Teleoperation

For bidirectional control, either servo can be the leader. This example uses a three-state approach:

1. **Locked** — both servos hold position with torque on, acting as force sensors
2. **Active** — the pushed servo is released to move freely; the other mirrors it
3. **Re-lock** — once movement stops, both servos hold the new position

Detecting a push *while torque is on* is reliable because the motor actively resists the force, producing a clear load signal. This is more robust than sensing on a limp servo.

**Calibration tip**: before running the loop, check both servos' idle holding load to find a safe threshold. Torque must be **enabled** for this reading to be meaningful — a limp servo will read near zero regardless of position:

```python
leader.enable_torque()
follower.enable_torque()

leader_load,   _ = leader.current_load()
follower_load, _ = follower.current_load()
print(f"Idle load — leader: {leader_load:.1f}%  follower: {follower_load:.1f}%")
```

Then push firmly against the leader while this loop runs to see your peak push values:

```python
import time

print("Push against the leader servo and watch the load...")
for _ in range(50):
    load, direction = leader.current_load()
    print(f"  load: {load:.1f}%  direction: {direction}")
    time.sleep(0.1)
```

Set `LOAD_THRESHOLD` just above your observed idle floor — typically 3–6% works well.

```python
import time

# These three values are the main tuning knobs — small changes can make a big
# difference, so experiment until the feel is right for your setup.

# Load (%) against a holding servo that signals an intentional push.
# Run the calibration check above first. Idle typically reads 0-3% depending
# on joint angle; set this just above your observed floor.
LOAD_THRESHOLD = 3.0

# Speed (steps/sec) below which the active servo is considered stopped.
IDLE_SPEED = 20

# Seconds of no movement before both servos re-lock.
# Lower = snappier re-lock; higher = more forgiving during slow movements.
SETTLE_TIME = 0.15

# Start with both servos holding position
leader.enable_torque()
follower.enable_torque()

print("Bidirectional teleoperation")
print("Push against either servo — it will release and the other will mirror!")

active     = None          # 'leader', 'follower', or None (locked)
last_moved = time.time()

duration = 30
start = time.time()

while time.time() - start < duration:
    leader_info   = leader.status()
    follower_info = follower.status()

    leader_load,   _ = leader_info['load']
    follower_load, _ = follower_info['load']
    leader_speed     = abs(leader_info['speed'])
    follower_speed   = abs(follower_info['speed'])

    if active is None:
        # LOCKED: both holding — watch for a push against either servo
        if leader_load > LOAD_THRESHOLD:
            leader.disable_torque()    # release so human can move it freely
            active = 'leader'
            last_moved = time.time()

        elif follower_load > LOAD_THRESHOLD:
            follower.disable_torque()
            active = 'follower'
            last_moved = time.time()

    elif active == 'leader':
        # Human is moving the leader (limp) — follower mirrors
        follower.move_to(leader_info['position'][0])
        if leader_speed > IDLE_SPEED:
            last_moved = time.time()
        elif time.time() - last_moved > SETTLE_TIME:
            # Movement stopped — re-lock both at current positions
            leader.enable_torque()
            active = None

    elif active == 'follower':
        # Human is moving the follower (limp) — leader mirrors
        leader.move_to(follower_info['position'][0])
        if follower_speed > IDLE_SPEED:
            last_moved = time.time()
        elif time.time() - last_moved > SETTLE_TIME:
            # Movement stopped — re-lock both at current positions
            follower.enable_torque()
            active = None

# Shutdown
leader.disable_torque()
follower.disable_torque()
print("Bidirectional teleoperation complete!")
```

---

### Step 8: Clean Shutdown

Always disable torque and close both buses when done.

```python
leader.disable_torque()
follower.disable_torque()
leader.close_bus()
follower.close_bus()

print("Both servos shut down")
```

---

## Complete Example

Here's a complete teleoperation script you can run:

```python
from servo import Servo
import time

# === Configuration ===
leader_port = '/dev/cu.usbmodem5AE60577551'   # Replace with your port
follower_port = '/dev/cu.usbmodem5AE60543861' # Replace with your port
duration = 20  # seconds

# === Setup ===
print("Connecting to servos...")
leader = Servo(port=leader_port)
follower = Servo(port=follower_port)

# Verify connections
leader.ping()
follower.ping()

# Synchronize starting positions
print("\nMoving to starting position...")
start_pos = 2048
leader.move_to(start_pos)
follower.move_sync(start_pos)

# Disable leader torque for manual movement
leader.disable_torque()

# === Teleoperation Loop ===
print(f"\nTeleoperation active for {duration} seconds.")
print("Move the leader servo by hand - the follower will mirror!")

start = time.time()

while time.time() - start < duration:
    # Read leader position and speed
    info = leader.status()
    pos = info['position'][0]
    speed = abs(info['speed'])

    # Command follower
    follower.move_to(pos, speed=speed)

# === Cleanup ===
print("Teleoperation ended.")
leader.disable_torque()
follower.disable_torque()
leader.close_bus()
follower.close_bus()
print("Both servos shut down.")
```

---

## Next Steps

Continue to **[Part 4: Daisy Chain Tutorial](./TUTORIAL_DAISY_CHAIN.md)** to learn how to control multiple servos from a single driver board using one serial connection.
