# Tutorial Self-Tests

Scripts that exercise each part of the tutorial on real hardware and report PASS/FAIL per step.
Use them to confirm your own setup works, or to re-verify after changing `servo.py`.

Run them from the repo root with the tutorial environment active:

| Script | Hardware | What it covers |
|--------|----------|----------------|
| `python tests/test_unit.py` | none | SDK import, register addresses, error bits, degree conversions, port filtering |
| `python tests/test_part1_lowlevel.py` | 1 servo, 1 board | Part 1 (README) Steps 2–11 using the raw SDK |
| `python tests/test_part2_servo_class.py` | 1 servo, 1 board | Part 2, every public `Servo` method |
| `python tests/test_part3_teleop.py --leader PORT --follower PORT` | 2 servos, 2 boards | Part 3 teleoperation |
| `python tests/test_part4_daisy_chain.py` | 2 servos (IDs 1 and 2), 1 board | Part 4 daisy chain |

Common options:

- `--port /dev/cu.usbmodemXXXX` picks the board when more than one is connected (auto-detected otherwise).
- `--id N` targets a servo ID other than 1.
- `--non-interactive` skips steps that ask you to move or push the servo by hand.

Safety: the servo horn moves on its own during these tests. Keep fingers, cables, and loose objects clear.
Each script leaves the servo with torque disabled and the port closed, even on failure.
