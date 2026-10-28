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
- **Verified SDK version**: `ftservo-python-sdk` 2.0.1 (Oct 2026). The only change from 2.0.0 is `PortHandler.clearPort()` using `reset_input_buffer()`.
- **Default Baud Rate**: 1,000,000 bps (1 Mbps)
- **Default Servo ID**: 1
- **Position Range**: 0-4095 (represents 0-360 degrees)
- **Serial Port Pattern**: `/dev/cu.usbmodem*` on macOS

## Common Register Addresses

Full tables are in `REGISTER_REFERENCE.md`; these are the ones the tutorials use most.

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

- `README.md` - Part 1: hardware setup and low-level SDK usage
- `TUTORIAL_SERVO_CLASS.md` - Part 2: the high-level `Servo` class
- `TUTORIAL_TELEOPERATION.md` - Part 3: mirroring one servo to another (two boards)
- `TUTORIAL_DAISY_CHAIN.md` - Part 4: two servos on one board (IDs 1 and 2)
- `servo.py` - High-level Servo class wrapper; instances on the same port share one connection
- `REGISTER_REFERENCE.md` - Full register tables; defaults verified against two real units (firmware 3.10)
- `STS3215_Reference.pdf` - Printable copy of the register reference
- `Servo-Stand.stl`, `Servo-Paddle.stl`, `Servo-Stand-Dual.stl` - 3D printable single and dual test stands
- `photos/` - Hardware setup reference images
- `tests/` - Hardware self-test scripts, one per tutorial part, plus a no-hardware unit test (`python tests/test_unit.py`). All four parts were verified on hardware in October 2026 with these scripts.
