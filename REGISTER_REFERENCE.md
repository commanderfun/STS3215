# STS3215 Register Address Reference

Printable PDF version: [STS3215_Reference.pdf](./STS3215_Reference.pdf)

## EEPROM Registers (Non-Volatile)

These values are saved even after power off. Torque must be disabled to write.

| Addr | Name | Size | R/W | Default | Description |
|------|------|------|-----|---------|-------------|
| 0 | Firmware Major | 1 | R | - | Major firmware version number |
| 1 | Firmware Minor | 1 | R | - | Minor firmware version number |
| 3 | Servo Major | 1 | R | - | Servo series major version |
| 4 | Servo Minor | 1 | R | - | Servo series minor version |
| 5 | ID | 1 | R/W | 1 | Servo ID (0-253), must be unique on bus |
| 6 | Baud Rate | 1 | R/W | 0 | 0=1Mbps, 1=500K, 2=250K, 3=128K, 4=115200, 5=76800, 6=57600, 7=38400 |
| 7 | Return Delay | 1 | R/W | 0 | Response delay time in microseconds |
| 8 | Response Level | 1 | R/W | 1 | 0=No response, 1=Respond to read, 2=Respond to all |
| 9 | Min Angle Limit | 2 | R/W | 0 | Minimum position limit (0-4095); set both to 0 for motor mode |
| 11 | Max Angle Limit | 2 | R/W | 4095 | Maximum position limit (0-4095); set both to 0 for motor mode |
| 13 | Max Temp Limit | 1 | R/W | 70 | Maximum temperature limit in °C |
| 14 | Max Voltage Limit | 1 | R/W | 140 | Maximum voltage limit (value × 0.1V) |
| 15 | Min Voltage Limit | 1 | R/W | 50 | Minimum voltage limit (value × 0.1V) |
| 16 | Max Torque Limit | 2 | R/W | 1000 | Maximum torque output (0-1000 = 0-100%) |
| 18 | Phase | 1 | R/W | 0 | Motor phase/direction setting |
| 19 | Unload Condition | 1 | R/W | 0 | Conditions that trigger torque release |
| 20 | LED Alarm | 1 | R/W | 0 | LED blink conditions for alarms (bitmask) |
| 21 | P Coefficient | 1 | R/W | 32 | PID proportional gain |
| 22 | D Coefficient | 1 | R/W | 32 | PID derivative gain |
| 23 | I Coefficient | 1 | R/W | 0 | PID integral gain |
| 24 | Min Startup Force | 2 | R/W | 0 | Minimum torque to start moving (0-1000) |
| 26 | CW Dead Zone | 1 | R/W | 1 | Clockwise dead zone width |
| 27 | CCW Dead Zone | 1 | R/W | 1 | Counter-clockwise dead zone width |
| 28 | Protection Current | 2 | R/W | 0 | Overcurrent protection threshold (×6.5mA) |
| 30 | Angular Resolution | 1 | R/W | 1 | Position resolution multiplier |
| 31 | Position Offset | 2 | R/W | 0 | Position offset calibration value |
| 33 | Mode | 1 | R/W | 0 | 0=Position, 1=Constant speed, 2=PWM, 3=Step servo |
| 34 | Protection Torque | 1 | R/W | 20 | Torque during overload protection (%) |
| 35 | Protection Time | 1 | R/W | 200 | Time before overload protection triggers |
| 36 | Overload Torque | 1 | R/W | 80 | Torque threshold for overload detection (%) |

## RAM Registers (Volatile)

These values reset on power cycle. Used for real-time control and status.

| Addr | Name | Size | R/W | Description |
|------|------|------|-----|-------------|
| 40 | Torque Enable | 1 | R/W | 0=Torque off (servo is limp), 1=Torque on (servo holds position) |
| 41 | Acceleration | 1 | R/W | Goal acceleration setting (0=instant, 1-254=smoother ramp). Note: This is a setting register, not real-time feedback. |
| 42 | Goal Position | 2 | R/W | Target position (0-4095); in motor mode this is speed/direction |
| 44 | Goal Time | 2 | R/W | Time to reach goal position in milliseconds |
| 46 | Goal Speed | 2 | R/W | Speed limit for movement (0=max speed, 1-4095=limited) |
| 48 | Torque Limit | 2 | R/W | Current torque limit (0-1000 = 0-100%) |
| 55 | Lock | 1 | R/W | 0=EEPROM unlocked, 1=EEPROM locked (write protected) |
| 56 | Present Position | 2 | R | Current actual position (0-4095) |
| 58 | Present Speed | 2 | R | Current movement speed |
| 60 | Present Load | 2 | R | Current load/torque (bits 0-9=magnitude, bit 10=direction) |
| 62 | Present Voltage | 1 | R | Current voltage (value × 0.1V) |
| 63 | Present Temperature | 1 | R | Current temperature in °C |
| 64 | Async Write Flag | 1 | R | Status of asynchronous write operation |
| 65 | Servo Status | 1 | R | Error status bitmask (voltage, temp, overload, etc.) |
| 66 | Moving | 1 | R | 1=Servo is currently moving, 0=Stationary |
| 69 | Present Current | 2 | R | Current draw (value × 6.5mA) |

## Quick Reference — Common Operations

| Operation | Register(s) | Example Value | Notes |
|-----------|-------------|---------------|-------|
| Enable torque | 40 | 1 | Must enable before servo responds to goal positions |
| Disable torque | 40 | 0 | Servo goes limp; can move by hand, still read position |
| Move to position | 42 | 0-4095 | 2048 = center position |
| Set speed limit | 46 | 0-4095 | 0 = maximum speed |
| Read position | 56 | - | Returns current position 0-4095 |
| Read load | 60 | - | Returns load magnitude and direction |
| Set acceleration | 41 | 0-254 | 0 = instant, higher = smoother ramp (setting only, no real-time feedback) |
| Motor mode | 9 & 11 | both 0 | Set min and max angle limits to 0 |
| Servo mode | 9 & 11 | 0 & 4095 | Restore angle limits for position control |

## Notes

- **Size**: Number of bytes (1 or 2). Use `read1ByteTxRx`/`write1ByteTxRx` for 1-byte, `read2ByteTxRx`/`write2ByteTxRx` for 2-byte registers.
- **Position range**: 0-4095 represents 0-360°. Each unit is approximately 0.088°.
- **Default baud rate**: 1,000,000 bps (1 Mbps).
- **Default servo ID**: 1.
- **Voltage values**: Multiply by 0.1 to get volts (e.g., 74 = 7.4V).
- **Current values**: Multiply by 6.5 to get milliamps.
- **Torque/Load values**: 1000 = 100% of maximum.
- **EEPROM writes**: Disable torque first, then write, then re-enable torque.
