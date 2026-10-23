"""
Part 3 (TUTORIAL_TELEOPERATION.md) self-test: two servos on two driver boards.

Run:  python tests/test_part3_teleop.py [--leader PORT --follower PORT] [--non-interactive]

Without --leader/--follower the two detected boards are used (leader = first found).
The automated part drives the leader under its own power and checks that the
follower mirrors it. Interactive steps let you move the leader by hand and try
the bidirectional loop from Step 7.
Leaves both servos with torque disabled and both ports closed.
"""

import time

from common import Checker, MODEL_NUMBER_STS3215, CENTER, make_parser, find_servo_ports, fail_exit, ask, ask_yes_no, wait_until
from servo import Servo

args = make_parser("Part 3 teleoperation test", ports=2).parse_args()
c = Checker()

if not (args.leader and args.follower):
    found = find_servo_ports()
    if len(found) != 2:
        fail_exit(f"Need exactly two boards (found {found}); or pass --leader and --follower.")
    args.leader, args.follower = found

leader = follower = None


def settle(servo, target, tol=10, timeout=8):
    return wait_until(lambda: not servo.moving() and abs(servo.position()[0] - target) <= tol, timeout)


def mirror(seconds, speed_match=False, until_leader_stops=False):
    """
    Run the tutorial's mirror loop; return (iterations, errors_per_iteration).

    With until_leader_stops=True the loop keeps going until the leader has been
    still for 0.5 s (so the follower can catch up), capped at `seconds`.
    """
    n = 0
    errs = []
    t0 = time.perf_counter()
    stopped_at = None
    while time.perf_counter() - t0 < seconds:
        if until_leader_stops:
            if leader.moving():
                stopped_at = None
            elif stopped_at is None:
                stopped_at = time.perf_counter()
            elif time.perf_counter() - stopped_at > 0.5:
                break
        if speed_match:
            info = leader.status()
            lp = info["position"][0]
            follower.move_to(lp, speed=abs(info["speed"]))
        else:
            lp = leader.position()[0]
            follower.move_to(lp)
        errs.append(abs(follower.position()[0] - lp))
        n += 1
    return n, errs


try:
    # ---- Steps 1-3: ports, connect, ping ------------------------------------
    c.section("Steps 1-3: Ports, connect, ping")
    c.check("two boards detected", len(find_servo_ports()) == 2, str(find_servo_ports()))
    leader = Servo(port=args.leader, servo_id=args.id)
    follower = Servo(port=args.follower, servo_id=args.id)
    c.check("independent port handlers", leader._port_handler is not follower._port_handler)
    c.check("leader ping", leader.ping() == MODEL_NUMBER_STS3215)
    c.check("follower ping", follower.ping() == MODEL_NUMBER_STS3215)
    c.note("voltages", f"leader {leader.voltage():.1f}V, follower {follower.voltage():.1f}V")

    # ---- Step 4: synchronize ------------------------------------------------
    c.section("Step 4: Synchronize starting positions")
    leader.move_to(CENTER)
    follower.move_sync(CENTER)
    settle(leader, CENTER)
    lp, fp = leader.position()[0], follower.position()[0]
    c.check("both at center ±10", abs(lp - CENTER) <= 10 and abs(fp - CENTER) <= 10, f"leader {lp}, follower {fp}")

    # ---- Step 5: basic mirroring, leader driven by software -----------------
    c.section("Step 5: Position mirroring (leader moves under its own power)")
    leader.move_to(1024, speed=800)
    t0 = time.perf_counter()
    n, errs = mirror(8.0, until_leader_stops=True)
    hz = n / (time.perf_counter() - t0)
    c.check("mirror loop rate > 50 Hz", hz > 50, f"{hz:.0f} Hz")
    c.check("follower caught up to leader", errs[-1] <= 15, f"final error {errs[-1]} steps, max lag during move {max(errs)}")
    leader.move_to(3072, speed=800)
    n, errs = mirror(8.0, until_leader_stops=True)
    c.check("follower tracks a second move", errs[-1] <= 15, f"final error {errs[-1]} steps, max lag {max(errs)}")

    # ---- Step 6: speed matching -----------------------------------------
    c.section("Step 6: Speed matching")
    leader.move_to(1024, speed=600)
    t0 = time.perf_counter()
    n, errs = mirror(8.0, speed_match=True, until_leader_stops=True)
    hz = n / (time.perf_counter() - t0)
    c.check("speed-matched loop rate > 50 Hz", hz > 50, f"{hz:.0f} Hz")
    c.check("follower caught up (speed matched)", errs[-1] <= 15, f"final error {errs[-1]}, max lag {max(errs)}")

    # ---- Step 7 calibration: idle holding load -------------------------
    c.section("Step 7: Idle load calibration (V9)")
    leader.move_sync(CENTER)
    follower.move_sync(CENTER)
    leader.enable_torque()
    follower.enable_torque()
    time.sleep(0.5)
    idle = {"leader": [], "follower": []}
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3.0:
        idle["leader"].append(leader.current_load()[0])
        idle["follower"].append(follower.current_load()[0])
        time.sleep(0.02)
    for name, vals in idle.items():
        c.check(f"{name} idle load below LOAD_THRESHOLD 3.0%", max(vals) < 3.0, f"max {max(vals):.1f}%, mean {sum(vals) / len(vals):.2f}%")
    # Also check idle load away from center, where the doc says it can be higher
    leader.move_sync(512)
    time.sleep(0.5)
    vals = [leader.current_load()[0] for _ in range(50) if not time.sleep(0.02)]
    c.note("leader idle load at position 512", f"max {max(vals):.1f}%")
    leader.move_sync(CENTER)

    # ---- Interactive: hand-move the leader -----------------------------
    c.section("Interactive: move the leader by hand")
    if not args.non_interactive:
        print("    Wiggling the LEADER so you can tell which one it is...")
        for target in (CENTER - 300, CENTER + 300, CENTER - 300, CENTER + 300, CENTER):
            leader.move_sync(target, speed=1500)
        print(f"    The servo that just wiggled is the leader ({args.leader}).")
    if ask("Leader torque will be OFF for 8 s. Move the leader horn by hand and watch the follower copy it", args):
        leader.disable_torque()
        print("    mirroring for 8 s...")
        n, errs = mirror(8.0, speed_match=True)
        c.check("hand-move mirror loop rate > 50 Hz", n / 8.0 > 50, f"{n / 8.0:.0f} Hz")
        c.note("tracking error while hand-moved", f"max {max(errs)} steps, final {errs[-1]}")
        c.check("human confirms follower mirrored", ask_yes_no("Did the follower copy your movement?", args))

    # ---- Interactive: bidirectional (tutorial Step 7 state machine) ------
    c.section("Interactive: bidirectional teleoperation")
    if ask("Both servos will lock. Push against EITHER servo; it releases and the other mirrors. 20 s run", args):
        LOAD_THRESHOLD, IDLE_SPEED, SETTLE_TIME = 3.0, 20, 0.15
        leader.move_sync(CENTER)
        follower.move_sync(CENTER)
        leader.enable_torque()
        follower.enable_torque()
        active, last_moved = None, time.time()
        transitions = []
        t0 = time.time()
        n = 0
        while time.time() - t0 < 20:
            li, fi = leader.status(), follower.status()
            l_load, f_load = li["load"][0], fi["load"][0]
            l_speed, f_speed = abs(li["speed"]), abs(fi["speed"])
            n += 1
            if active is None:
                if l_load > LOAD_THRESHOLD:
                    leader.disable_torque(); active = "leader"; last_moved = time.time(); transitions.append("leader released")
                elif f_load > LOAD_THRESHOLD:
                    follower.disable_torque(); active = "follower"; last_moved = time.time(); transitions.append("follower released")
            elif active == "leader":
                follower.move_to(li["position"][0])
                if l_speed > IDLE_SPEED:
                    last_moved = time.time()
                elif time.time() - last_moved > SETTLE_TIME:
                    leader.enable_torque(); active = None; transitions.append("re-locked")
            else:
                leader.move_to(fi["position"][0])
                if f_speed > IDLE_SPEED:
                    last_moved = time.time()
                elif time.time() - last_moved > SETTLE_TIME:
                    follower.enable_torque(); active = None; transitions.append("re-locked")
        c.note("bidirectional loop rate", f"{n / 20:.0f} Hz")
        c.note("state transitions", "; ".join(transitions) or "none")
        c.check("at least one release and one re-lock happened", "re-locked" in transitions and len(transitions) >= 2)
        c.check("human confirms bidirectional behavior",
                ask_yes_no("Did it feel right (release on push, other servo mirrors, both re-lock)?", args))

    # ---- Step 8: shutdown -----------------------------------------------
    c.section("Step 8: Clean shutdown")
    leader.disable_torque()
    follower.disable_torque()
    leader.close_bus()
    follower.close_bus()
    c.check("both ports closed", not leader._port_handler.is_open and not follower._port_handler.is_open)

finally:
    for s in (leader, follower):
        try:
            if s is not None and s.SERIAL_PORT in Servo._connections:
                s.disable_torque()
                s.close_bus()
        except Exception as e:  # pragma: no cover
            print(f"cleanup warning: {e}")

c.exit()
