"""
Shared helpers for the STS3215 tutorial self-test scripts.

Every test script in this folder uses these helpers for argument parsing,
serial port discovery, interactive prompts, and PASS/FAIL bookkeeping.
Run any script with --help to see its options.
"""

import argparse
import os
import sys
import time

# Make `servo.py` (repo root) importable when running from anywhere.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import serial.tools.list_ports  # noqa: E402

MODEL_NUMBER_STS3215 = 777
CENTER = 2048


def find_servo_ports():
    """Return device paths that look like a Waveshare servo driver board."""
    return [
        p.device
        for p in serial.tools.list_ports.comports()
        if "usbmodem" in p.device.lower() and "serial" in (p.description or "").lower()
    ]


def make_parser(description, ports=1):
    """
    Build an argparse parser with the standard options.

    Args:
        description: Script description shown in --help.
        ports: 1 for single-board tests (--port), 2 for two-board tests
               (--leader and --follower).
    """
    parser = argparse.ArgumentParser(description=description)
    if ports == 1:
        parser.add_argument("--port", help="Serial port (auto-detected if exactly one board is found)")
    else:
        parser.add_argument("--leader", help="Serial port of the leader board")
        parser.add_argument("--follower", help="Serial port of the follower board")
    parser.add_argument("--id", type=int, default=1, help="Servo ID (default 1)")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip steps that need a human to move or push the servo",
    )
    return parser


def resolve_port(args):
    """Return args.port, or the single auto-detected board, or exit with a message."""
    if args.port:
        return args.port
    found = find_servo_ports()
    if len(found) == 1:
        return found[0]
    if not found:
        fail_exit("No servo driver board found. Is it plugged in and powered? Use --port to specify.")
    fail_exit(f"Several boards found: {found}. Use --port to pick one.")


def fail_exit(msg):
    print(f"\n✗ {msg}")
    sys.exit(2)


def ask(prompt, args):
    """
    Pause for a human action. Returns False if the step was skipped.

    Honors --non-interactive by skipping immediately.
    """
    if getattr(args, "non_interactive", False):
        print(f"  (skipped, non-interactive) {prompt}")
        return False
    answer = input(f"\n>>> {prompt}\n    Press Enter when done, or type s to skip: ").strip().lower()
    return answer != "s"


def ask_text(prompt, args, default=""):
    """Ask the human a short question; returns default under --non-interactive."""
    if getattr(args, "non_interactive", False):
        print(f"  (skipped, non-interactive) {prompt}")
        return default
    return input(f"\n>>> {prompt}: ").strip().lower() or default


class Checker:
    """Collects PASS/FAIL results and prints a summary."""

    def __init__(self):
        self.results = []  # (name, passed, detail)

    def check(self, name, condition, detail=""):
        status = "PASS" if condition else "FAIL"
        self.results.append((name, bool(condition), detail))
        line = f"  [{status}] {name}"
        if detail:
            line += f"  ({detail})"
        print(line)
        return bool(condition)

    def note(self, name, detail):
        """Record an observation that is neither pass nor fail."""
        self.results.append((name, None, detail))
        print(f"  [NOTE] {name}  ({detail})")

    def section(self, title):
        print(f"\n=== {title} ===")

    def summary(self):
        passed = sum(1 for _, ok, _ in self.results if ok is True)
        failed = [(n, d) for n, ok, d in self.results if ok is False]
        print("\n" + "=" * 60)
        print(f"{passed} passed, {len(failed)} failed")
        for name, detail in failed:
            print(f"  FAIL: {name}  {detail}")
        print("=" * 60)
        return len(failed) == 0

    def exit(self):
        sys.exit(0 if self.summary() else 1)


def wait_until(predicate, timeout=5.0, interval=0.05):
    """Poll predicate() until it returns truthy or timeout seconds pass."""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if predicate():
            return True
        time.sleep(interval)
    return False
