# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a tutorial repository for controlling **Feetech STS3215 servos** (12V 30kg torque model) using Python on macOS. The tutorial uses the Waveshare Serial Bus Servo Driver Board for communication.

## Environment Setup

```bash
# Create and activate conda environment
conda create -n servo-tutorial python=3.11 -y
conda activate servo-tutorial

# Install dependencies
conda install -c conda-forge pyserial -y
pip install ftservo-python-sdk
```

**Important**: Do NOT install `feetech-servo-sdk` or `scservo-sdk` - they cause conflicts or don't exist.

## Key Technical Details

- **SDK Import**: `from scservo_sdk import sms_sts, PortHandler`
- **Default Baud Rate**: 1,000,000 bps (1 Mbps)
- **Default Servo ID**: 1
- **Position Range**: 0-4095 (represents 0-360 degrees)
- **Serial Port Pattern**: `/dev/cu.usbmodem*` on macOS

## Common Register Addresses

| Register | Address | Size | Description |
|----------|---------|------|-------------|
| Torque Enable | 40 | 1 byte | 0=off (limp), 1=on (holding) |
| Goal Position | 42 | 2 bytes | Target position 0-4095 |
| Present Position | 56 | 2 bytes | Current position (read-only) |
| Present Load | 60 | 2 bytes | Current load/torque |
| Present Voltage | 62 | 1 byte | Voltage (value x 0.1V) |
| Present Temperature | 63 | 1 byte | Temperature in Celsius |
| Servo Status | 65 | 1 byte | Error bitmask |

## SDK Source Code

The `ftservo-python-sdk` package (which imports as `scservo_sdk`) source code is on GitHub:
- **Repository**: https://github.com/ftservo/FTServo_Python
- **Key file**: `scservo_sdk/sms_sts.py` contains the servo control methods like `ReadSpeed()`, `WritePosEx()`, `WheelMode()`, etc.
- **Return pattern**: Most read methods return a tuple `(value, comm_result, error)` where `comm_result=0` means success

## Repository Contents

- `README.md` - Full step-by-step tutorial with Python code examples
- `TUTORIAL_SERVO_CLASS.md` - Part 2 tutorial using the high-level Servo class
- `servo.py` - High-level Servo class wrapper
- `STS3215_Reference.pdf` - Official servo documentation
- `Servo-Stand.stl`, `Servo-Paddle.stl` - 3D printable test stand
- `photos/` - Hardware setup reference images
