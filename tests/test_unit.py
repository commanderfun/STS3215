"""
No-hardware checks for servo.py and the installed SDK.

Run:  python tests/test_unit.py
"""

import sys
from unittest import mock

from common import Checker  # noqa: E402  (adds repo root to sys.path)

import scservo_sdk
from scservo_sdk import sms_sts, PortHandler
import importlib
# The package re-exports the protocol_packet_handler *class* under the module's name,
# so fetch the real module to reach its ERRBIT_* constants.
pph = importlib.import_module("scservo_sdk.protocol_packet_handler")
from servo import Servo

c = Checker()

# --- README Step 0: Verify Installation -------------------------------------
c.section("SDK import (README Part 1, Step 0)")
for name in ("WheelMode", "WriteSpec", "WritePosEx", "ReadSpeed", "ReadPosSpeed"):
    c.check(f"sms_sts.{name} exists", hasattr(sms_sts, name))
try:
    from importlib.metadata import version
    c.note("ftservo-python-sdk version", version("ftservo-python-sdk"))
except Exception as e:  # pragma: no cover
    c.note("ftservo-python-sdk version", f"unknown ({e})")
c.check("PortHandler default baud is 1 Mbps", PortHandler("/dev/null").baudrate == 1_000_000)

# --- Register addresses in servo.py match the SDK's constants ----------------
c.section("servo.py register addresses vs SDK constants")
pairs = {
    "ADDR_ID": "SMS_STS_ID",
    "ADDR_MIN_ANGLE_LIMIT": "SMS_STS_MIN_ANGLE_LIMIT_L",
    "ADDR_MAX_ANGLE_LIMIT": "SMS_STS_MAX_ANGLE_LIMIT_L",
    "ADDR_MODE": "SMS_STS_MODE",
    "ADDR_TORQUE_ENABLE": "SMS_STS_TORQUE_ENABLE",
    "ADDR_ACCELERATION": "SMS_STS_ACC",
    "ADDR_GOAL_POSITION": "SMS_STS_GOAL_POSITION_L",
    "ADDR_LOCK": "SMS_STS_LOCK",
    "ADDR_PRESENT_POSITION": "SMS_STS_PRESENT_POSITION_L",
    "ADDR_PRESENT_LOAD": "SMS_STS_PRESENT_LOAD_L",
    "ADDR_PRESENT_VOLTAGE": "SMS_STS_PRESENT_VOLTAGE",
    "ADDR_PRESENT_TEMPERATURE": "SMS_STS_PRESENT_TEMPERATURE",
    "ADDR_MOVING": "SMS_STS_MOVING",
    "ADDR_PRESENT_CURRENT": "SMS_STS_PRESENT_CURRENT_L",
}
for ours, theirs in pairs.items():
    c.check(f"{ours} == {theirs}", getattr(Servo, ours) == getattr(scservo_sdk, theirs),
            f"{getattr(Servo, ours)} vs {getattr(scservo_sdk, theirs)}")

# --- Error flag bits match the SDK's ERRBIT_* values -------------------------
c.section("Servo.ERROR_FLAGS vs SDK ERRBIT_*")
errbits = {"Voltage": pph.ERRBIT_VOLTAGE, "Sensor": pph.ERRBIT_ANGLE,
           "Temperature": pph.ERRBIT_OVERHEAT, "Current": pph.ERRBIT_OVERELE,
           "Overload": pph.ERRBIT_OVERLOAD}
for bit, name in Servo.ERROR_FLAGS.items():
    c.check(f"bit {bit} = {name}", (1 << bit) == errbits[name], f"1<<{bit}={1 << bit}, SDK={errbits[name]}")

# --- Degree conversions ------------------------------------------------------
c.section("Degree conversions")
s = Servo.__new__(Servo)  # no hardware: skip __init__
c.check("0 -> 0°", s.position_to_degrees(0) == 0)
c.check("2048 -> 180°", s.position_to_degrees(2048) == 180)
c.check("4095 -> ~359.9°", abs(s.position_to_degrees(4095) - 359.912) < 0.01)
c.check("90° -> 1024", s.degrees_to_position(90) == 1024)
c.check("180° -> 2048", s.degrees_to_position(180) == 2048)
for p in (0, 1, 1023, 2048, 3072, 4095):
    c.check(f"round trip {p}", s.degrees_to_position(s.position_to_degrees(p)) == p)

# --- find_port() filtering --------------------------------------------------
c.section("find_port() filtering")


class FakePort:
    def __init__(self, device, description):
        self.device, self.description = device, description


def with_ports(ports):
    with mock.patch("serial.tools.list_ports.comports", return_value=ports):
        with mock.patch("builtins.print"):
            return s.find_port()


c.check("no ports -> None", with_ports([]) is None)
c.check("ignores Bluetooth port",
        with_ports([FakePort("/dev/cu.Bluetooth-Incoming-Port", "n/a")]) is None)
c.check("finds one Waveshare board",
        with_ports([FakePort("/dev/cu.usbmodem1101", "USB Single Serial")]) == "/dev/cu.usbmodem1101")
c.check("two boards -> None (ambiguous)",
        with_ports([FakePort("/dev/cu.usbmodem1101", "USB Single Serial"),
                    FakePort("/dev/cu.usbmodem1201", "USB Single Serial")]) is None)

# --- SDK packet encoding (sanity, no port) ----------------------------------
c.section("SDK encoding helpers")
h = pph.protocol_packet_handler(PortHandler("/dev/null"), 0)
c.check("scs_toscs(-500) sets bit 15", h.scs_toscs(-500, 15) == (500 | (1 << 15)))
c.check("scs_tohost round trip -500", h.scs_tohost(h.scs_toscs(-500, 15), 15) == -500)
c.check("lobyte/hibyte of 2048", (h.scs_lobyte(2048), h.scs_hibyte(2048)) == (0x00, 0x08))

c.exit()
