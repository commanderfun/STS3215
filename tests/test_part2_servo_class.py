"""
Part 2 (TUTORIAL_SERVO_CLASS.md) self-test: every public method of the Servo class.

Run:  python tests/test_part2_servo_class.py [--port PORT] [--id N] [--non-interactive]

Moves the servo through several positions and spins it in wheel mode.
Leaves the servo in position mode with torque disabled and the bus closed.
"""

import time

from common import Checker, MODEL_NUMBER_STS3215, CENTER, make_parser, ask, wait_until
from servo import Servo

args = make_parser("Part 2 Servo class test", ports=1).parse_args()
c = Checker()


def expect_raises(exc, fn, label):
    try:
        fn()
    except exc as e:
        c.check(label, True, f"{exc.__name__}: {e}")
    except Exception as e:  # noqa: BLE001
        c.check(label, False, f"wrong exception {type(e).__name__}: {e}")
    else:
        c.check(label, False, "no exception")


def bench(fn, n=20):
    t = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t) / n * 1000


s = None
try:
    # ---- Step 1: connect --------------------------------------------------
    c.section("Step 1: Connect and ping")
    s = Servo(port=args.port, servo_id=args.id) if args.port else Servo(servo_id=args.id)
    c.check("Servo() connected", s.SERIAL_PORT is not None, s.SERIAL_PORT)
    model = s.ping()
    c.check(f"ping() returns {MODEL_NUMBER_STS3215}", model == MODEL_NUMBER_STS3215, str(model))
    ser_obj = s._port_handler.ser
    s.ping()
    c.check("V5: ping() does not reopen the port", ser_obj is s._port_handler.ser)
    c.check("V5: ping() is fast", bench(s.ping, 5) < 5, "see ms above")
    s2 = Servo(port=s.SERIAL_PORT, servo_id=args.id)
    c.check("second instance on same port shares the handler", s2._port_handler is s._port_handler)
    expect_raises(IOError, lambda: Servo(port="/dev/cu.usbmodemDOESNOTEXIST"), "bad port raises IOError")
    c.check("port baud rate is 1 Mbps", s._port_handler.getBaudRate() == 1_000_000)

    # ---- Step 2: status ---------------------------------------------------
    c.section("Step 2: Status reads")
    pos, deg = s.position()
    c.check("position() in range", 0 <= pos <= 4095 and 0 <= deg < 360, f"{pos} = {deg:.1f}°")
    c.check("speed() is int", isinstance(s.speed(), int), str(s.speed()))
    c.check("direction() in (None, CW, CCW)", s.direction() in (None, "CW", "CCW"), str(s.direction()))
    c.check("voltage() plausible", 6 <= s.voltage() <= 14, f"{s.voltage():.1f}V")
    c.check("temperature() plausible", 10 <= s.temperature() <= 60, f"{s.temperature()}°C")
    c.check("torque_enabled() is bool", isinstance(s.torque_enabled(), bool))
    c.check("moving() is bool", isinstance(s.moving(), bool))
    c.check("acceleration() 0-254", 0 <= s.acceleration() <= 254, str(s.acceleration()))
    info = s.status()
    keys = {"position", "speed", "direction", "voltage", "temperature", "load", "current",
            "moving", "torque_enabled", "mode", "errors", "healthy"}
    c.check("status() has all documented keys", keys <= set(info), str(sorted(set(info) ^ keys)))
    c.note("status() call time", f"{bench(s.status):.2f} ms")
    c.note("position() call time", f"{bench(s.position):.2f} ms")

    # ---- Step 3: move_to (async) ----------------------------------------
    c.section("Step 3: move_to / move_to_degrees")
    s.move_to(CENTER)
    c.check("move_to(2048) arrives", wait_until(lambda: abs(s.position()[0] - CENTER) <= 10 and not s.moving(), 5),
            str(s.position()[0]))
    c.check("move_to enabled torque", s.torque_enabled())
    c.note("move_to() call time", f"{bench(lambda: s.move_to(CENTER)):.2f} ms")
    t0 = time.perf_counter()
    s.move_to(1024, speed=500, acc=100)
    wait_until(lambda: abs(s.position()[0] - 1024) <= 10 and not s.moving(), 8)
    t_slow = time.perf_counter() - t0
    t0 = time.perf_counter()
    s.move_to(3072, speed=2000, acc=0)
    wait_until(lambda: abs(s.position()[0] - 3072) <= 10 and not s.moving(), 8)
    t_fast = time.perf_counter() - t0
    c.check("speed/acc arguments respected", t_fast < t_slow, f"fast {t_fast:.2f}s < slow {t_slow:.2f}s")
    s.move_to_degrees(90)
    c.check("move_to_degrees(90) -> ~1024", wait_until(lambda: abs(s.position()[0] - 1024) <= 10 and not s.moving(), 5),
            str(s.position()[0]))
    s.move_to_degrees(360)
    c.check("F5: move_to_degrees(360) -> 4095 area, no wrap to 0",
            wait_until(lambda: s.position()[0] >= 4080 and not s.moving(), 5), str(s.position()[0]))
    expect_raises(ValueError, lambda: s.move_to(4096), "move_to(4096) raises ValueError")
    expect_raises(ValueError, lambda: s.move_to(-1), "move_to(-1) raises ValueError")
    expect_raises(ValueError, lambda: s.move_to(2048, speed=9999), "bad speed raises ValueError")
    expect_raises(ValueError, lambda: s.move_to(2048, acc=300), "bad acc raises ValueError")
    expect_raises(ValueError, lambda: s.move_to_degrees(361), "move_to_degrees(361) raises ValueError")

    # ---- Step 4: move_sync ------------------------------------------------
    c.section("Step 4: move_sync")
    t0 = time.perf_counter()
    final = s.move_sync(1024)
    c.check("move_sync(1024) returns within tolerance", abs(final - 1024) <= 10, f"{final} in {time.perf_counter() - t0:.2f}s")
    final = s.move_sync(3072)
    c.check("move_sync(3072) returns within tolerance", abs(final - 3072) <= 10, str(final))
    t0 = time.perf_counter()
    final = s.move_sync(3072)
    dt = time.perf_counter() - t0
    c.check("V7: move_sync to current position returns immediately", dt < 0.2, f"{dt:.3f}s")
    t0 = time.perf_counter()
    final = s.move_sync(3072 + 5)  # inside the default tolerance
    dt = time.perf_counter() - t0
    c.check("V7: tiny move inside tolerance does not hang", dt < 1.0, f"{dt:.3f}s, pos {final}")
    final = s.move_sync(CENTER, tolerance=20, timeout=5)
    c.check("move_sync with tolerance/timeout kwargs", abs(final - CENTER) <= 20, str(final))
    expect_raises(TimeoutError, lambda: s.move_sync(0, timeout=0.25, speed=300), "move_sync raises TimeoutError when too slow")
    wait_until(lambda: not s.moving(), 10)

    # ---- Step 5: move_sequence -------------------------------------------
    c.section("Step 5: move_sequence")
    t0 = time.perf_counter()
    s.move_sequence([0, 1024, 2048, 3072, 4095, 2048])
    c.check("move_sequence completes at last position", abs(s.position()[0] - CENTER) <= 10,
            f"{time.perf_counter() - t0:.1f}s total")

    # ---- Step 6: load and current ----------------------------------------
    c.section("Step 6: current_load / current_draw")
    s.move_to(1024, speed=500)
    loads, currents = [], []
    for _ in range(15):
        loads.append(s.current_load()[0])
        currents.append(s.current_draw())
        time.sleep(0.1)
    wait_until(lambda: not s.moving(), 5)
    c.check("load > 0 during move", max(loads) > 0, f"max {max(loads):.1f}%")
    c.check("current > 0 during move", max(currents) > 0, f"max {max(currents):.0f}mA")
    c.check("current_load() direction label is CW/CCW", s.current_load()[1] in ("CW", "CCW"))
    if ask("Push the horn gently and hold while 2 s of readings are taken", args):
        pushed = [s.current_load()[0] for _ in range(10) if not time.sleep(0.2)]
        c.check("load rose while pushed", max(pushed) > 1.0, f"max {max(pushed):.1f}%")

    # ---- Step 7: errors ----------------------------------------------------
    c.section("Step 7: Error status")
    c.check("is_healthy()", s.is_healthy(), f"status={s.servo_status()}")
    c.check("errors() == []", s.errors() == [], str(s.errors()))

    # ---- Step 8: manual monitoring (interactive only) --------------------
    c.section("Step 8: Manual movement monitoring")
    s.disable_torque()
    c.check("disable_torque() -> torque_enabled() False", not s.torque_enabled())
    if ask("Torque is off. Rotate the horn by hand for 3 seconds", args):
        speeds = [s.speed() for _ in range(30) if not time.sleep(0.1)]
        c.check("speed() changed while hand-moved", max(abs(x) for x in speeds) > 0, str(speeds[:10]))

    # ---- Step 9: wheel mode -------------------------------------------------
    c.section("Step 9: spin / stop")
    start_pos = s.position()[0]
    turns = 0.0
    last = start_pos
    s.spin(speed=2000)
    c.check("spin() switched to wheel mode", s.get_mode() == Servo.MODE_WHEEL)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 4.0:
        p = s.position()[0]
        d = p - last
        if d < -2048:
            d += 4096
        elif d > 2048:
            d -= 4096
        turns += d / 4096
        last = p
        time.sleep(0.01)
    sp = s.speed()
    s.stop()
    c.check("speed() positive while spinning CW", sp > 0, str(sp))
    c.check("V8: spin(2000) for 4 s is about 2 turns", 1.6 <= turns <= 2.4, f"{turns:.2f} turns")
    s.spin(speed=-500, acc=50)
    time.sleep(0.5)
    c.check("spin(-500) -> negative speed", s.speed() < 0, str(s.speed()))
    s.stop()
    c.check("stop() -> speed 0", wait_until(lambda: abs(s.speed()) < 5, 3), str(s.speed()))
    expect_raises(ValueError, lambda: s.spin(5000), "spin(5000) raises ValueError")
    s.move_to(CENTER)
    c.check("move_to() after spin returns to position mode", s.get_mode() == Servo.MODE_POSITION)
    c.check("and arrives at center", wait_until(lambda: abs(s.position()[0] - CENTER) <= 10 and not s.moving(), 5),
            str(s.position()[0]))
    expect_raises(ValueError, lambda: s.set_mode(7), "set_mode(7) raises ValueError")

    # ---- ID helpers (read only here; set_id is covered in Part 4) ----------
    c.section("get_id")
    c.check("get_id() matches servo_id", s.get_id() == s.servo_id, str(s.get_id()))

    # ---- Step 10: close_bus -------------------------------------------------
    c.section("Step 10: close_bus")
    s.disable_torque()
    s.close_bus()
    c.check("port closed", not s._port_handler.is_open)
    c.check("connection cache cleared", s.SERIAL_PORT not in Servo._connections)
    expect_raises(IOError, s.ping, "ping() after close_bus raises IOError")
    s = Servo(port=s.SERIAL_PORT, servo_id=args.id)
    c.check("can reconnect after close_bus", s.ping() == MODEL_NUMBER_STS3215)

finally:
    if s is not None:
        try:
            if s.SERIAL_PORT in Servo._connections:
                s.set_mode(Servo.MODE_POSITION)
                s.disable_torque()
                s.close_bus()
        except Exception as e:  # pragma: no cover
            print(f"cleanup warning: {e}")

c.exit()
