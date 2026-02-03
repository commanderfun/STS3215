# Servo Class Tutorial (Part 2)

A step-by-step guide to using the `Servo` class for simplified control of Feetech STS3215 servos.

## Table of Contents

- [Prerequisites](#prerequisites)
- [What is the Servo Class?](#what-is-the-servo-class)
- [Tutorial Steps](#tutorial-steps)
  - [Step 1: Connect to a Servo](#step-1-connect-to-a-servo)
  - [Step 2: Read Servo Status](#step-2-read-servo-status)
  - [Step 3: Move to a Position (Async)](#step-3-move-to-a-position-async)
  - [Step 4: Move to a Position (Sync)](#step-4-move-to-a-position-sync)
  - [Step 5: Run a Movement Sequence](#step-5-run-a-movement-sequence)
  - [Step 6: Read Load and Current](#step-6-read-load-and-current)
  - [Step 7: Check Error Status](#step-7-check-error-status)
  - [Step 8: Manual Movement Monitoring](#step-8-manual-movement-monitoring)
  - [Step 9: Wheel Mode (Continuous Rotation)](#step-9-wheel-mode-continuous-rotation)
  - [Step 10: Disconnect](#step-10-disconnect)
- [API Reference](#api-reference)

---

## Prerequisites

Before starting this tutorial:

1. Complete [Part 1 (README.md)](./README.md) to understand the hardware setup and low-level SDK
2. Have your servo, driver board, and power supply connected
3. Ensure `servo.py` is in your working directory
4. Set up your Python [environment](./README.md#environment-setup) and start a [Jupyter](./README.md#step-0-start-a-jupyter-notebook) Notebook as explained in Part 1.

---

## What is the Servo Class?

The `Servo` class is a high-level wrapper around the `scservo_sdk` that simplifies common operations:

| Low-Level SDK | Servo Class |
|---------------|-------------|
| Manual port detection | Auto-detects serial port |
| Manual torque enable/disable | Auto-enables torque when moving |
| Raw register reads | Named methods (`position()`, `voltage()`) |
| Fire-and-forget moves | Synchronous moves with `move_sync()` |
| Manual mode switching | Auto-switches modes as needed |

---

## Tutorial Steps

### Step 1: Connect to a Servo

The `Servo` class auto-detects the serial port and establishes a connection.

```python
from servo import Servo

# Connect with auto-detection
s = Servo()

# Verify connection
s.ping()
```

Expected output:

```
✓ Serial comm port: /dev/cu.usbmodemAAA000FFCCC (yours will differ)
✓ Successfully pinged servo ID 1
✓ Model number: 777
```

#### If Auto-Detection Fails

If your port isn't detected automatically, find it manually:

```python
from servo import Servo

# List available ports
for port, desc in Servo.list_ports():
    print(f"{port}: {desc}")
```

Then specify the port directly:

```python
s = Servo(port="/dev/cu.usbmodemAAA000FFCCC")
```

#### Multiple Servos

If you have multiple servos on the bus, specify the ID:

```python
s1 = Servo(servo_id=1)
s2 = Servo(servo_id=2)
```

---

### Step 2: Read Servo Status

Read the servo's current state with simple method calls.

```python
# Read position (returns raw value and degrees)
pos, deg = s.position()
print(f"Position: {pos} raw = {deg:.1f}°")

# Read speed, direction, and acceleration
print(f"Speed: {s.speed()} steps/sec")  # negative = CCW, positive = CW
print(f"Direction: {s.direction()}")     # "CW", "CCW", or None
print(f"Acceleration: {s.acceleration()}")  # 0-254, 0 = instant

# Read voltage
volts = s.voltage()
print(f"Voltage: {volts:.1f}V")

# Read temperature
temp = s.temperature()
print(f"Temperature: {temp}°C")

# Check if torque is enabled
print(f"Torque enabled: {s.torque_enabled()}")

# Check if servo is moving
print(f"Moving: {s.moving()}")
```

Expected output (values will vary):

```
Position: 2048 raw = 180.0°
Speed: 0 steps/sec
Direction: None
Acceleration: 0
Voltage: 12.3V
Temperature: 34°C
Torque enabled: False
Moving: False
```

#### Get Everything at Once

Use `status()` to get a comprehensive status dictionary in one call:

```python
info = s.status()

print(f"Position: {info['position'][1]:.1f}°")
print(f"Speed: {info['speed']} steps/sec")
print(f"Direction: {info['direction']}")
print(f"Acceleration: {info['acceleration']}")
print(f"Voltage: {info['voltage']:.1f}V")
print(f"Temperature: {info['temperature']}°C")
print(f"Load: {info['load'][0]:.1f}% {info['load'][1]}")
print(f"Current: {info['current']:.1f}mA")
print(f"Mode: {info['mode']}")
print(f"Healthy: {info['healthy']}")
```

---

### Step 3: Move to a Position (Async)

The `move_to()` method sends a move command and returns immediately (asynchronous).

```python
# Move to center position (2048 = 180°)
# Position range: 0-4095 (0°-360°)
s.move_to(2048)
print("Move command sent!")

# The servo is now moving, but Python continues immediately
```

You can also control speed and acceleration:

```python
# Parameter ranges:
#   position: 0-4095 (0°-360°, center = 2048)
#   speed:    0-3400 (0 = max speed, otherwise steps/second)
#   acc:      0-254  (0 = instant, higher = smoother ramp)

# Move slowly with smooth acceleration
s.move_to(1024, speed=500, acc=100)

import time
time.sleep(2)

# Move quickly (high speed, no acceleration ramp)
s.move_to(3072, speed=2000, acc=0)
```

#### Move Using Degrees

If you prefer working in degrees instead of raw positions:

```python
s.move_to_degrees(90)   # Move to 90°
s.move_to_degrees(180)  # Move to 180° (center)
s.move_to_degrees(270)  # Move to 270°
```

**Note**: `move_to()` automatically enables torque and sets position mode if needed.

---

### Step 4: Move to a Position (Sync)

The `move_sync()` method waits until the servo reaches the target position (synchronous).

```python
# Move and wait until complete
final_pos = s.move_sync(1024)
print(f"Arrived at position: {final_pos}")

# Move to another position
final_pos = s.move_sync(3072)
print(f"Arrived at position: {final_pos}")
```

This is useful when you need to ensure one movement completes before starting another.

#### Adjusting Tolerance and Timeout

```python
# Allow 20 steps of error, wait up to 5 seconds
final_pos = s.move_sync(2048, tolerance=20, timeout=5)
```

---

### Step 5: Run a Movement Sequence

The `move_sequence()` method moves through a list of positions in order, waiting for each to complete.

```python
# Define a sequence of positions
positions = [0, 1024, 2048, 3072, 4095, 2048]

# Run the sequence
print("Starting movement sequence...")
s.move_sequence(positions)
print("Sequence complete!")
```

This is useful for choreographed movements or testing range of motion.

#### With Custom Tolerance/Timeout

```python
s.move_sequence(positions, tolerance=15, timeout=8)
```

---

### Step 6: Read Load and Current

Monitor the servo's load (torque) and electrical current draw.

```python
# Read current load
load_percent, direction = s.current_load()
print(f"Load: {load_percent:.1f}% {direction}")

# Read current draw
current_ma = s.current_draw()
print(f"Current: {current_ma:.1f} mA")
```

**Tip**: Try gently pushing against the servo horn while reading these values - you'll see them increase as the servo resists.

#### Continuous Monitoring

```python
import time

print("Monitoring servo for 5 seconds...")
print("Try pushing the servo horn!\n")

for i in range(50):
    pos, deg = s.position()
    load, direction = s.current_load()
    current = s.current_draw()

    print(f"Pos: {deg:6.1f}° | Load: {load:5.1f}% {direction} | Current: {current:6.1f}mA")
    time.sleep(0.1)
```

---

### Step 7: Check Error Status

Use `is_healthy()` for a quick check, or `errors()` for details:

```python
# Quick health check
if s.is_healthy():
    print("✓ No errors - servo is healthy!")
else:
    print(f"⚠ Errors detected: {s.errors()}")
```

The `errors()` method returns a list of active error names:

```python
error_list = s.errors()
# Returns: [] if healthy
# Returns: ["Voltage", "Temperature"] if those errors are active
```

#### Possible Errors

| Error | Cause |
|-------|-------|
| Voltage | Input voltage too high or too low |
| Sensor | Position sensor malfunction |
| Temperature | Servo overheating |
| Current | Overcurrent detected |
| Overload | Mechanical overload/stall |

---

### Step 8: Manual Movement Monitoring

Disable torque so you can rotate the servo horn by hand while monitoring position, speed, and direction in real-time.

```python
import time

# Disable torque so servo can be moved by hand
s.disable_torque()
print("Torque disabled - rotate the servo horn by hand!\n")

# Monitor for 10 seconds
print("Monitoring for 10 seconds...\n")
for i in range(100):
    info = s.status()
    pos_deg = info['position'][1]
    speed = info['speed']
    direction = info['direction']

    dir_str = direction if direction else "stopped"
    print(f"Position: {pos_deg:6.1f}° | Speed: {speed:5d} | Direction: {dir_str}")
    time.sleep(0.1)

print("\nDone monitoring!")
```

Try rotating the horn slowly, then quickly - you should see the speed and direction values change as you move it.

---

### Step 9: Wheel Mode (Continuous Rotation)

Use `spin()` to rotate the servo continuously like a motor:

```python
# Spin clockwise
s.spin(500)
print("Spinning CW...")

import time
time.sleep(2)

# Spin counter-clockwise
s.spin(-500)
print("Spinning CCW...")

time.sleep(2)

# Stop
s.stop()
print("Stopped")
```

The `spin()` method automatically switches to wheel mode. To return to position mode, just use any move command:

```python
# After spinning, return to position mode
s.move_to(2048)  # Automatically switches back to position mode
```

#### Speed Control

```python
s.spin(200)       # Slow
s.spin(1000)      # Medium
s.spin(2000)      # Fast
s.spin(-500, acc=50)  # With acceleration ramp
```

---

### Step 10: Disconnect

Always disconnect when you're done to release the servo and free the serial port.

```python
s.disconnect()
print("✓ Disconnected")
```

This:
- Disables torque (servo goes limp)
- Closes the serial port

---

## API Reference

### Constructor

| Method | Description |
|--------|-------------|
| `Servo(servo_id=1, model="STS3215", port=None)` | Create a servo connection |
| `Servo.list_ports()` | List available serial ports (static method) |

### Status Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `ping()` | None | Verify communication, prints status |
| `position()` | `(raw, degrees)` | Current position |
| `speed()` | `int` | Current speed (negative = CCW, positive = CW) |
| `direction()` | `str` or `None` | Direction: "CW", "CCW", or None if stopped |
| `acceleration()` | `int` | Acceleration setting (0-254, 0 = instant). Returns last written value, not real-time feedback. |
| `voltage()` | `float` | Input voltage in volts |
| `temperature()` | `int` | Temperature in °C |
| `torque_enabled()` | `bool` | Whether torque is on |
| `moving()` | `bool` | Whether servo is in motion |
| `current_load()` | `(percent, direction)` | Load as % and "CW"/"CCW" |
| `current_draw()` | `float` | Current in milliamps |
| `servo_status()` | `int` | Error status bitmask (raw) |
| `errors()` | `list` | List of active error names |
| `is_healthy()` | `bool` | True if no errors |
| `status()` | `dict` | Complete status summary |
| `get_mode()` | `int` | Operating mode (0-3) |

### Movement Methods

| Method | Description |
|--------|-------------|
| `move_to(position, speed=0, acc=0)` | Move to raw position (async) |
| `move_to_degrees(degrees, speed=0, acc=0)` | Move to degrees (async) |
| `move_sync(target, tolerance=10, timeout=10)` | Move and wait (sync) |
| `move_sequence(positions, tolerance=10, timeout=10)` | Run position sequence |

### Wheel Mode Methods

| Method | Description |
|--------|-------------|
| `spin(speed, acc=0)` | Spin continuously (+ = CW, - = CCW) |
| `stop()` | Stop spinning |

### Control Methods

| Method | Description |
|--------|-------------|
| `enable_torque()` | Enable torque (servo holds position) |
| `disable_torque()` | Disable torque (servo can be moved by hand) |
| `set_mode(mode)` | Set operating mode |
| `disconnect()` | Disable torque and close port |

### Conversion Helpers

| Method | Description |
|--------|-------------|
| `position_to_degrees(position)` | Convert raw position to degrees |
| `degrees_to_position(degrees)` | Convert degrees to raw position |

### Position Reference

| Position | Degrees |
|----------|---------|
| 0 | 0° |
| 1024 | 90° |
| 2048 | 180° (center) |
| 3072 | 270° |
| 4095 | 360° |

---

## Complete Example

```python
from servo import Servo
import time

# Connect
s = Servo()
s.ping()

# Check health
if not s.is_healthy():
    print(f"Warning: {s.errors()}")

# Get full status
info = s.status()
print(f"\nStarting position: {info['position'][1]:.1f}°")
print(f"Voltage: {info['voltage']:.1f}V")
print(f"Temperature: {info['temperature']}°C")

# Run a movement sequence using degrees
print("\nRunning movement sequence...")
s.move_to_degrees(0)
time.sleep(1)
s.move_to_degrees(180)
time.sleep(1)
s.move_to_degrees(360)
time.sleep(1)

# Try wheel mode
print("\nTesting wheel mode...")
s.spin(500)
time.sleep(2)
s.stop()

# Return to position mode
s.move_to(2048)
time.sleep(1)

# Final status
pos, deg = s.position()
print(f"\nFinal position: {deg:.1f}°")
print(f"Healthy: {s.is_healthy()}")

# Disconnect
s.disconnect()
print("\n✓ Done!")
```

---

## Next Steps

- Create a multi-servo controller for robotic arms using `SyncWritePosEx`
- Add position interpolation for smoother movements
- Build a simple GUI for servo control
