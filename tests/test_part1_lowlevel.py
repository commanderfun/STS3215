"""
Part 1 (README.md) self-test: Steps 2-11 using the raw scservo_sdk.

Run:  python tests/test_part1_lowlevel.py [--port PORT] [--id N] [--non-interactive]

Moves the servo through several positions and spins it in wheel mode.
Leaves the servo in position mode with torque disabled and the port closed.
"""

import time

from common import (Checker, MODEL_NUMBER_STS3215, CENTER, make_parser, resolve_port,
                    ask, ask_text, wait_until)
from scservo_sdk import sms_sts, PortHandler, COMM_SUCCESS

args = make_parser("Part 1 low-level SDK test", ports=1).parse_args()
PORT = resolve_port(args)
ID = args.id

# Register addresses exactly as the README uses them
ADDR_MIN_ANGLE_LIMIT = 9
ADDR_MAX_ANGLE_LIMIT = 11
ADDR_MAX_TEMP_LIMIT = 13
ADDR_MAX_VOLTAGE_LIMIT = 14
ADDR_MIN_VOLTAGE_LIMIT = 15
ADDR_MODE = 33
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_LOCK = 55
ADDR_PRESENT_POSITION = 56
ADDR_PRESENT_SPEED = 58
ADDR_PRESENT_LOAD = 60
ADDR_PRESENT_VOLTAGE = 62
ADDR_PRESENT_TEMPERATURE = 63
ADDR_SERVO_STATUS = 65
ADDR_MOVING = 66
ADDR_PRESENT_CURRENT = 69

c = Checker()
ph = PortHandler(PORT)
servo = sms_sts(ph)


def r1(addr):
    v, res, err = servo.read1ByteTxRx(ID, addr)
    assert res == COMM_SUCCESS, f"read1 addr {addr}: comm={res}"
    return v


def r2(addr):
    v, res, err = servo.read2ByteTxRx(ID, addr)
    assert res == COMM_SUCCESS, f"read2 addr {addr}: comm={res}"
    return v


def pos():
    return r2(ADDR_PRESENT_POSITION)


def speed_signed():
    s, res, err = servo.ReadSpeed(ID)
    assert res == COMM_SUCCESS
    return s


def settle(target, tol=10, timeout=8):
    """Wait for the servo to stop within tol of target. Returns (ok, final_pos, seconds)."""
    t0 = time.perf_counter()
    ok = wait_until(lambda: r1(ADDR_MOVING) == 0 and abs(pos() - target) <= tol, timeout)
    return ok, pos(), time.perf_counter() - t0


try:
    # ---- Step 2: connect and ping ------------------------------------------
    c.section("Step 2: Connect and ping")
    c.check("openPort()", ph.openPort())
    c.check("setBaudRate(1000000)", ph.setBaudRate(1000000))
    model, res, err = servo.ping(ID)
    c.check("ping comm_result == 0", res == COMM_SUCCESS, f"comm={res}")
    c.check(f"model number == {MODEL_NUMBER_STS3215}", model == MODEL_NUMBER_STS3215, f"got {model}")

    # ---- Step 3: read status -------------------------------------------------
    c.section("Step 3: Read status and position")
    p = pos()
    c.check("position in 0..4095", 0 <= p <= 4095, f"{p} = {p * 360 / 4096:.1f}°")
    v = r1(ADDR_PRESENT_VOLTAGE) * 0.1
    c.check("voltage plausible (6-14V)", 6 <= v <= 14, f"{v:.1f}V")
    t = r1(ADDR_PRESENT_TEMPERATURE)
    c.check("temperature plausible (10-60°C)", 10 <= t <= 60, f"{t}°C")
    c.note("torque enabled at start", str(bool(r1(ADDR_TORQUE_ENABLE))))
    c.check("moving == 0 at rest", r1(ADDR_MOVING) == 0)
    c.note("EEPROM lock register (55)", str(r1(ADDR_LOCK)))
    c.check("mode == 0 (position) at start", r1(ADDR_MODE) == 0)

    # ---- Step 4: enable torque and move ------------------------------------
    c.section("Step 4: Enable torque and move to 2048")
    res, err = servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 1)
    c.check("torque enable write ok", res == COMM_SUCCESS and err == 0)
    c.check("torque reads back 1", r1(ADDR_TORQUE_ENABLE) == 1)
    res, err = servo.WritePosEx(ID, CENTER, 1000, 50)
    c.check("WritePosEx comm ok", res == COMM_SUCCESS and err == 0)
    ok, p, dt = settle(CENTER)
    c.check("arrived at 2048 ±10", ok, f"pos={p} in {dt:.2f}s")

    # ---- Step 5: speed and acceleration ------------------------------------
    c.section("Step 5: Speed and acceleration")
    servo.WritePosEx(ID, 1024, 500, 100)
    time.sleep(0.15)
    sp = speed_signed()
    c.note("present speed while moving 2048→1024 (decreasing position)", str(sp))
    ok_slow, p, t_slow = settle(1024)
    c.check("slow move (speed 500, acc 100) arrived at 1024", ok_slow, f"pos={p} in {t_slow:.2f}s")
    servo.WritePosEx(ID, 3072, 2000, 0)
    time.sleep(0.15)
    sp2 = speed_signed()
    c.note("present speed while moving 1024→3072 (increasing position)", str(sp2))
    ok_fast, p, t_fast = settle(3072)
    c.check("fast move (speed 2000, acc 0) arrived at 3072", ok_fast, f"pos={p} in {t_fast:.2f}s")
    c.check("fast move took less time than slow move (same distance)", t_fast < t_slow,
            f"{t_fast:.2f}s vs {t_slow:.2f}s")
    c.check("speed sign: decreasing position reads negative, increasing reads positive",
            sp < 0 < sp2, f"{sp}, {sp2}")

    # ---- Step 6: load and current while moving -----------------------------
    c.section("Step 6: Load / current monitoring")
    servo.WritePosEx(ID, 1024, 500, 50)
    samples = []
    for _ in range(20):
        load_raw = r2(ADDR_PRESENT_LOAD)
        cur_raw = r2(ADDR_PRESENT_CURRENT)
        samples.append((load_raw & 0x3FF, bool(load_raw & 0x400), cur_raw * 6.5))
        time.sleep(0.1)
    settle(1024)
    max_load = max(s[0] for s in samples)
    max_cur = max(s[2] for s in samples)
    c.check("load magnitude > 0 at some point during move", max_load > 0, f"max {max_load / 10:.1f}%")
    c.check("current > 0 at some point during move", max_cur > 0, f"max {max_cur:.0f}mA")
    c.note("load direction bit while moving 3072→1024", f"bit10 set in {sum(s[1] for s in samples)}/20 samples")
    if ask("Gently push the paddle CLOCKWISE (as seen from the paddle side) and hold for 3 s", args):
        pushed = [r2(ADDR_PRESENT_LOAD) for _ in range(15) if not time.sleep(0.2)]
        mags = [x & 0x3FF for x in pushed]
        dirs = [bool(x & 0x400) for x in pushed]
        c.check("load rose while pushing", max(mags) > max_load, f"max {max(mags) / 10:.1f}% vs idle {max_load / 10:.1f}%")
        c.note("load bit10 while pushed clockwise", f"set in {sum(dirs)}/{len(dirs)} samples")

    # ---- Step 7: error status ---------------------------------------------
    c.section("Step 7: Error status")
    st = r1(ADDR_SERVO_STATUS)
    c.check("status register == 0 (healthy)", st == 0, f"{st:#04x}")
    mn, mx, mt = r1(ADDR_MIN_VOLTAGE_LIMIT), r1(ADDR_MAX_VOLTAGE_LIMIT), r1(ADDR_MAX_TEMP_LIMIT)
    c.note("voltage limits", f"{mn * 0.1:.1f}V - {mx * 0.1:.1f}V (README expects 4.0-14.0)")
    c.note("temperature limit", f"{mt}°C (README expects 70)")

    # ---- Step 8: disable torque and close ----------------------------------
    c.section("Step 8: Disable torque and close port")
    res, err = servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 0)
    c.check("torque disable write ok", res == COMM_SUCCESS)
    c.check("torque reads back 0", r1(ADDR_TORQUE_ENABLE) == 0)
    ph.closePort()
    c.check("port closed", not ph.is_open)

    # ---- Step 9: wheel mode -------------------------------------------------
    c.section("Step 9: Wheel mode (reconnect as README does)")
    ph = PortHandler(PORT)
    servo = sms_sts(ph)
    c.check("reopen + baud", ph.openPort() and ph.setBaudRate(1000000))
    lim_before = (r2(ADDR_MIN_ANGLE_LIMIT), r2(ADDR_MAX_ANGLE_LIMIT))
    lock_before = r1(ADDR_LOCK)
    res, err = servo.WheelMode(ID)
    c.check("WheelMode() comm ok", res == COMM_SUCCESS and err == 0)
    c.check("mode reads back 1 (V2: write accepted with lock=%d)" % lock_before, r1(ADDR_MODE) == 1)
    lim_after = (r2(ADDR_MIN_ANGLE_LIMIT), r2(ADDR_MAX_ANGLE_LIMIT))
    c.note("V1 angle limits before/after WheelMode", f"{lim_before} -> {lim_after}")
    c.note("V3 torque register after WheelMode (torque was disabled in Step 8)", str(r1(ADDR_TORQUE_ENABLE)))
    p0 = pos()
    res, err = servo.WriteSpec(ID, 500, 50)
    c.check("WriteSpec(500, 50) comm ok", res == COMM_SUCCESS)
    time.sleep(1.0)
    p1 = pos()
    sp = speed_signed()
    c.check("V3: servo spins after WriteSpec without explicit torque enable", p1 != p0, f"pos {p0} -> {p1}, speed {sp}")
    c.note("V3 torque register after WriteSpec", str(r1(ADDR_TORQUE_ENABLE)))
    c.check("positive WriteSpec → positive present speed", sp > 0, str(sp))
    seen = ask_text("Watch the paddle now. Is it turning cw or ccw (viewed from the paddle side)? [cw/ccw]", args)
    if seen:
        c.note("V4 human-observed direction at WriteSpec(+500)", seen)
    servo.WriteSpec(ID, -500, 50)
    time.sleep(1.0)
    sp = speed_signed()
    c.check("negative WriteSpec → negative present speed", sp < 0, str(sp))
    servo.WriteSpec(ID, 0, 50)
    c.check("WriteSpec(0) stops the motor", wait_until(lambda: abs(speed_signed()) < 5, 3), f"speed {speed_signed()}")

    # ---- Step 10: back to servo mode ---------------------------------------
    c.section("Step 10: Back to servo mode")
    servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 0)
    res, err = servo.write1ByteTxRx(ID, ADDR_MODE, 0)
    c.check("mode write comm ok", res == COMM_SUCCESS and err == 0)
    c.check("mode reads back 0", r1(ADDR_MODE) == 0)
    c.check("angle limits still 0..4095 (never touched by wheel mode)",
            (r2(ADDR_MIN_ANGLE_LIMIT), r2(ADDR_MAX_ANGLE_LIMIT)) == (0, 4095))
    servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 1)
    servo.WritePosEx(ID, CENTER, 1000, 50)
    ok, p, dt = settle(CENTER)
    c.check("position control works again: arrived at 2048", ok, f"pos={p} in {dt:.2f}s")

    # ---- V2 extra: does a mode write with torque ENABLED take effect? -------
    c.section("V2 probe: mode write while torque is enabled and EEPROM locked")
    c.note("lock register now", str(r1(ADDR_LOCK)))
    res, err = servo.write1ByteTxRx(ID, ADDR_MODE, 1)
    m = r1(ADDR_MODE)
    c.note("mode after writing 1 with torque on", f"comm={res} err={err} mode={m}")
    servo.write1ByteTxRx(ID, ADDR_MODE, 0)
    c.check("mode restored to 0", r1(ADDR_MODE) == 0)

    # ---- Step 11: clean shutdown -------------------------------------------
    c.section("Step 11: Clean shutdown")
    res, err = servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 0)
    c.check("torque disabled", res == COMM_SUCCESS and r1(ADDR_TORQUE_ENABLE) == 0)
    ph.closePort()
    c.check("port closed", not ph.is_open)

finally:
    # Always leave the servo safe: position mode, torque off, port closed.
    try:
        if not ph.is_open:
            ph.openPort()
        servo.write1ByteTxRx(ID, ADDR_MODE, 0)
        servo.write1ByteTxRx(ID, ADDR_TORQUE_ENABLE, 0)
        ph.closePort()
    except Exception as e:  # pragma: no cover
        print(f"cleanup warning: {e}")

c.exit()
