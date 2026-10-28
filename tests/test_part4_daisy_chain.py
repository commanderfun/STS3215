"""
Part 4 (TUTORIAL_DAISY_CHAIN.md) self-test: two servos chained on ONE driver board.

Run:  python tests/test_part4_daisy_chain.py [--port PORT] [--id 1] [--id2 2] [--non-interactive]

Prerequisite: the two servos already have different IDs (tutorial Step 1, done
with ONE servo on the bus at a time). This script never calls set_id(); it only
checks that both IDs answer. Leaves both servos limp and the port closed.
"""

import time

from common import Checker, MODEL_NUMBER_STS3215, CENTER, make_parser, resolve_port, ask, ask_yes_no, wait_until
from servo import Servo

parser = make_parser("Part 4 daisy chain test")
parser.add_argument("--id2", type=int, default=2, help="ID of the second servo (default 2)")
args = parser.parse_args()
port = resolve_port(args)
c = Checker()

s1 = s2 = None


transient_errors = []  # one-off comm errors seen while polling (reported in the summary)


def settle(servo, target, tol=10, timeout=8):
    """Wait until servo stops within tol of target. A single corrupt reply is logged and retried."""
    def arrived():
        try:
            return not servo.moving() and abs(servo.position()[0] - target) <= tol
        except IOError as e:
            transient_errors.append(str(e))
            return False
    return wait_until(arrived, timeout)


def both_at(p1, p2, tol=10):
    ok1, ok2 = settle(s1, p1, tol), settle(s2, p2, tol)
    a, b = s1.position()[0], s2.position()[0]
    return ok1 and ok2, f"s1 {a} (want {p1}), s2 {b} (want {p2})"


try:
    # ---- Step 1: IDs already assigned ----------------------------------------
    c.section("Step 1: Unique IDs (assigned beforehand, one servo on the bus)")
    c.check("IDs differ", args.id != args.id2, f"{args.id} and {args.id2}")

    # ---- Step 2: connect, shared handler --------------------------------------
    c.section("Step 2: Connect to both servos")
    s1 = Servo(port=port, servo_id=args.id)
    s2 = Servo(port=port, servo_id=args.id2)
    c.check("same serial port", s1.SERIAL_PORT == s2.SERIAL_PORT, s1.SERIAL_PORT)
    c.check("same port handler", s1._port_handler is s2._port_handler)
    c.check("one open connection", len(Servo._connections) == 1, f"{len(Servo._connections)} in Servo._connections")

    # ---- Step 3: ping + get_id ----------------------------------------------
    c.section("Step 3: Verify both servos")
    c.check("s1 ping", s1.ping() == MODEL_NUMBER_STS3215)
    c.check("s2 ping", s2.ping() == MODEL_NUMBER_STS3215)
    c.check("s1 get_id from EEPROM", s1.get_id() == args.id, f"read {s1.get_id()}")
    c.check("s2 get_id from EEPROM", s2.get_id() == args.id2, f"read {s2.get_id()}")

    # ---- Step 4: status ------------------------------------------------------
    c.section("Step 4: Read status from both")
    for name, s in (("s1", s1), ("s2", s2)):
        pos, deg = s.position()
        v, t = s.voltage(), s.temperature()
        c.check(f"{name} status reads sane", 0 <= pos <= 4095 and 6.0 < v < 15.0 and 0 < t < 80,
                f"{pos} ({deg:.1f}°), {v:.1f}V, {t}°C, torque {s.torque_enabled()}, healthy {s.is_healthy()}")
    # Bus contention: interleave many reads and make sure none time out
    t0 = time.perf_counter()
    n = 0
    try:
        while time.perf_counter() - t0 < 2.0:
            s1.position(); s2.position(); s1.moving(); s2.moving()
            n += 4
        c.check("2 s of interleaved reads with no comm errors", True, f"{n} reads, {n / 2:.0f} reads/s")
    except IOError as e:
        c.check("2 s of interleaved reads with no comm errors", False, str(e))
    if ask("Both servos are limp. Rotate EACH horn by hand to a new spot", args):
        a0, b0 = s1.position()[0], s2.position()[0]
        c.note("positions after hand move", f"s1 {a0}, s2 {b0}")
        c.check("human confirms positions read independently",
                ask_yes_no("Did the two position values reflect where you left each horn?", args))

    # ---- Step 5: independent control ------------------------------------------
    c.section("Step 5: Independent control")
    s1.move_to(1024)
    s2.move_to(3072)
    ok, d = both_at(1024, 3072)
    c.check("s1 → 90°, s2 → 270°", ok, d)
    s1.move_to(CENTER)
    s2.move_to(CENTER)
    ok, d = both_at(CENTER, CENTER)
    c.check("both back to center", ok, d)
    c.check("move_to turned torque on for both", s1.torque_enabled() and s2.torque_enabled())

    # ---- Step 6: coordinated ------------------------------------------------
    c.section("Step 6: Coordinated movements")
    s1.move_to(0); s2.move_to(0)
    ok, d = both_at(0, 0)
    c.check("sync: both to 0", ok, d)
    t0 = time.perf_counter()
    all_ok = True
    for pos in (512, 2048, 3584, 2048):
        s1.move_to(pos); s2.move_to(pos)
        ok, d = both_at(pos, pos)
        all_ok &= ok
        if not ok:
            c.note("sync sweep miss", d)
    c.check("synchronized sweep 512/2048/3584/2048", all_ok, f"{time.perf_counter() - t0:.1f} s")

    s1.move_to(0); s2.move_to(0)
    both_at(0, 0)
    t0 = time.perf_counter()
    all_ok = True
    for p1, p2 in ((1024, 3072), (3072, 1024), (CENTER, CENTER)):
        s1.move_to(p1); s2.move_to(p2)
        ok, d = both_at(p1, p2)
        all_ok &= ok
        if not ok:
            c.note("mirror sweep miss", d)
    c.check("mirrored sweep (opposite directions)", all_ok, f"{time.perf_counter() - t0:.1f} s")

    t0 = time.perf_counter()
    f1 = s1.move_sync(512)
    s2_still = s2.position()[0]
    f2 = s2.move_sync(3584)
    f3 = s1.move_sync(CENTER)
    f4 = s2.move_sync(CENTER)
    c.check("sequential move_sync chain", all(abs(a - b) <= 10 for a, b in ((f1, 512), (f2, 3584), (f3, CENTER), (f4, CENTER))),
            f"{f1}, {f2}, {f3}, {f4} in {time.perf_counter() - t0:.1f} s")
    c.check("s2 stayed put while s1 moved", abs(s2_still - CENTER) <= 10, f"s2 at {s2_still}")

    # ---- Step 7: monitoring --------------------------------------------------
    c.section("Step 7: Monitoring both servos")
    s1.move_to(512, speed=500)
    s2.move_to(3584, speed=500)
    seen_moving = {"s1": False, "s2": False}
    samples = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3:
        p1, d1 = s1.position()
        p2, d2 = s2.position()
        m1, m2 = s1.moving(), s2.moving()
        seen_moving["s1"] |= bool(m1)
        seen_moving["s2"] |= bool(m2)
        samples += 1
        time.sleep(0.1)
    c.check("both servos reported moving during the poll", seen_moving["s1"] and seen_moving["s2"], str(seen_moving))
    ok, d = both_at(512, 3584)
    c.check("both reached targets at speed 500", ok, d)
    c.note("poll samples in 3 s", f"{samples} (0.1 s sleep each)")

    # ---- Complete Example ----------------------------------------------------
    c.section("Complete Example (abbreviated)")
    s1.move_to(CENTER); s2.move_to(CENTER); both_at(CENTER, CENTER)
    s1.move_to(1024); s2.move_to(3072); ok_a, _ = both_at(1024, 3072)
    s1.move_to(3072); s2.move_to(1024); ok_b, _ = both_at(3072, 1024)
    s1.move_to(CENTER); s2.move_to(CENTER); ok_c, _ = both_at(CENTER, CENTER)
    c.check("complete example sequence", ok_a and ok_b and ok_c)

    # ---- Step 8: clean shutdown ----------------------------------------------
    c.section("Step 8: Clean shutdown")
    s1.disable_torque()
    s2.disable_torque()
    c.check("torque off on both", not s1.torque_enabled() and not s2.torque_enabled())
    s1.close_bus()
    c.check("port closed", not s1._port_handler.is_open)
    c.check("connection table empty", len(Servo._connections) == 0)
    s2.close_bus()  # must be a harmless no-op
    c.check("second close_bus() is a no-op", len(Servo._connections) == 0)
    r1 = Servo(port=port, servo_id=args.id)
    r2 = Servo(port=port, servo_id=args.id2)
    c.check("reconnect after close works", r1.ping() == MODEL_NUMBER_STS3215 and r2.ping() == MODEL_NUMBER_STS3215)
    r1.close_bus()
    s1 = s2 = None

    c.section("Bus health")
    c.check("no more than one transient comm error during the whole run", len(transient_errors) <= 1,
            f"{len(transient_errors)} seen" + (": " + transient_errors[0] if transient_errors else ""))

finally:
    for s in (s1, s2):
        try:
            if s is not None and s.SERIAL_PORT in Servo._connections:
                s.disable_torque()
        except Exception as e:  # pragma: no cover
            print(f"cleanup warning: {e}")
    if port in Servo._connections:
        Servo._connections[port]["handler"].closePort()
        del Servo._connections[port]

c.exit()
