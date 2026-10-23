"""
Servo control module for Feetech STS3215 serial bus servos.

Provides a high-level interface for controlling STS3215 servos via the
Waveshare Serial Bus Servo Driver Board. Wraps the low-level scservo_sdk
to simplify common operations like position control, status reading, and
mode switching.

Example:
    from servo import Servo

    s = Servo(servo_id=1)
    s.ping()
    s.move_to(2048)  # Move to center position
    pos, deg = s.position()
    s.disable_torque()
    s.close_bus()

    # If auto-detection fails, specify port manually:
    Servo.list_ports()  # Show available ports
    s = Servo(port="/dev/cu.usbmodem1101")
"""

from scservo_sdk import sms_sts, PortHandler
import serial
import serial.tools.list_ports
import time


class Servo:
    """
    High-level controller for a single Feetech STS3215 servo.

    Automatically detects the serial port and establishes communication
    with the servo on initialization.

    Attributes:
        servo_id (int): The ID of the servo on the bus.
        model (str): Servo model name.
        SERIAL_PORT (str): Detected serial port path.
        POSITION_MIN (int): Minimum position value (0).
        POSITION_MAX (int): Maximum position value (4095).
    """

    # Class attributes (shared by all instances)
    BAUD_RATE = 1000000
    SERIAL_PORT = None

    # STS3215 Register addresses
    ADDR_ID = 5
    ADDR_MIN_ANGLE_LIMIT = 9
    ADDR_MAX_ANGLE_LIMIT = 11
    ADDR_MAX_TEMP_LIMIT = 13
    ADDR_MAX_VOLTAGE_LIMIT = 14
    ADDR_MIN_VOLTAGE_LIMIT = 15
    ADDR_MODE = 33
    ADDR_TORQUE_ENABLE = 40
    ADDR_ACCELERATION = 41
    ADDR_GOAL_POSITION = 42
    ADDR_LOCK = 55
    ADDR_PRESENT_POSITION = 56
    ADDR_PRESENT_LOAD = 60
    ADDR_PRESENT_VOLTAGE = 62
    ADDR_PRESENT_TEMPERATURE = 63
    ADDR_SERVO_STATUS = 65
    ADDR_MOVING = 66
    ADDR_PRESENT_CURRENT = 69

    POSITION_MIN = 0
    POSITION_MAX = 4095
    SPEED_MAX = 3400        # steps/second; 0 means "no limit"
    ACCELERATION_MAX = 254  # 0 means instant

    # Operating modes (register 33)
    MODE_POSITION = 0
    MODE_WHEEL = 1
    MODE_PWM = 2
    MODE_STEP = 3

    # Error flag bit definitions for servo_status register
    ERROR_FLAGS = {
        0: "Voltage",
        1: "Sensor",
        2: "Temperature",
        3: "Current",
        5: "Overload",
    }

    _connections = {}  # {port_path: {'handler': PortHandler, 'servo': sms_sts}}

    def __init__(self, servo_id=1, model="STS3215", port=None):
        """
        Initialize connection to a servo.

        Multiple Servo instances on the same serial bus (same port) share a
        single connection automatically. Instances on different ports each get
        their own independent connection.

        Args:
            servo_id: ID of the servo on the bus (default: 1).
            model: Servo model name for reference (default: "STS3215").
            port: Serial port path (e.g., "/dev/cu.usbmodem1101"). If None,
                  auto-detection is attempted.

        Raises:
            IOError: If serial port cannot be found or opened.
        """
        self.model = model
        self.servo_id = servo_id
        self.SERIAL_PORT = port if port else self.find_port()
        if not self.SERIAL_PORT:
            candidates = self._candidate_ports()
            if len(candidates) > 1:
                raise IOError(
                    f"Found more than one servo driver board: {candidates}. "
                    "Specify which one to use with Servo(port='...')."
                )
            raise IOError(
                "Couldn't auto-detect serial port. "
                "Use Servo.list_ports() to find available ports, "
                "then create with Servo(port='/dev/cu.usbmodemXXXX')."
            )
        if self.SERIAL_PORT not in Servo._connections:
            handler = PortHandler(self.SERIAL_PORT)
            try:
                opened = handler.openPort() and handler.setBaudRate(self.BAUD_RATE)
            except serial.SerialException as e:
                raise IOError(f"Failed to open serial port {self.SERIAL_PORT}: {e}") from None
            if not opened:
                raise IOError(f"Failed to open serial comm port: {self.SERIAL_PORT}")
            Servo._connections[self.SERIAL_PORT] = {
                "handler": handler,
                "servo": sms_sts(handler),
            }
        self._port_handler = Servo._connections[self.SERIAL_PORT]["handler"]
        self._servo = Servo._connections[self.SERIAL_PORT]["servo"]

    @staticmethod
    def _candidate_ports():
        """Return device paths that look like a Waveshare servo driver board."""
        return [
            p.device
            for p in serial.tools.list_ports.comports()
            if "serial" in (p.description or "").lower() and "usbmodem" in p.device.lower()
        ]

    def find_port(self):
        """
        Auto-detect the serial port for the servo driver board.

        Searches for USB serial devices matching the Waveshare driver board
        pattern (usbmodem devices with "serial" in description).

        Returns:
            str or None: Device path (e.g., "/dev/cu.usbmodem1101"), or None if
                         no board or more than one board is found.
        """
        candidates = self._candidate_ports()
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def list_ports():
        """
        List all available serial ports.

        Useful for finding the correct port when auto-detection fails.

        Returns:
            list: List of tuples (device_path, description) for each port.

        Example:
            for port, desc in Servo.list_ports():
                print(f"{port}: {desc}")
        """
        ports = serial.tools.list_ports.comports()
        return [(p.device, p.description) for p in ports]

    def ping(self):
        """
        Verify communication with the servo.

        Sends a ping command and prints connection status and model number.

        Returns:
            int: The servo's model number (777 for the STS3215).

        Raises:
            IOError: If the port is not open or the servo doesn't respond.
        """
        if not self._port_handler.is_open:
            raise IOError(f"✗ Serial port {self.SERIAL_PORT} is not open. Create a new Servo instance.")
        model_number, comm_result, error = self._servo.ping(self.servo_id)
        if comm_result != 0:  # COMM_SUCCESS
            raise IOError(f"✗ Failed to ping servo_id: {self.servo_id}, comm_result: {comm_result}")
        print(f"✓ Serial comm port: {self.SERIAL_PORT}")
        print(f"✓ Successfully pinged servo ID {self.servo_id}")
        print(f"✓ Model number: {model_number}")
        return model_number

    def position_to_degrees(self, position):
        """
        Convert a raw position value to degrees.

        Args:
            position: Raw position value (0-4095).

        Returns:
            float: Angle in degrees (0-360).
        """
        return position * 360 / (self.POSITION_MAX + 1)

    def degrees_to_position(self, degrees):
        """
        Convert degrees to a raw position value.

        The result is clamped to the valid range, so 360° maps to 4095
        (the last step) rather than wrapping around to 0.

        Args:
            degrees: Angle in degrees (0-360).

        Returns:
            int: Raw position value (0-4095).
        """
        position = int(round(degrees * (self.POSITION_MAX + 1) / 360))
        return max(self.POSITION_MIN, min(self.POSITION_MAX, position))

    # --- Low-level register access -------------------------------------------

    def _check(self, comm_result, error, what):
        """Raise IOError if a read or write failed."""
        if comm_result != 0:
            raise IOError(f"✗ Communication failed ({what}) for servo_id: {self.servo_id}, comm_result: {comm_result}")
        if error != 0:
            raise IOError(f"Servo {self.servo_id} returned error {error} ({what})")

    def read1Byte(self, address):
        """
        Read a 1-byte value from a servo register.

        Args:
            address: Register address to read from.

        Returns:
            int: Value read from the register (0-255).

        Raises:
            IOError: If communication fails or servo returns an error.
        """
        read_value, comm_result, error = self._servo.read1ByteTxRx(self.servo_id, address)
        self._check(comm_result, error, f"read1 addr {address}")
        return read_value

    def read2Byte(self, address):
        """
        Read a 2-byte value from a servo register.

        Args:
            address: Register address to read from.

        Returns:
            int: Value read from the register (0-65535).

        Raises:
            IOError: If communication fails or servo returns an error.
        """
        read_value, comm_result, error = self._servo.read2ByteTxRx(self.servo_id, address)
        self._check(comm_result, error, f"read2 addr {address}")
        return read_value

    def write1Byte(self, address, value):
        """
        Write a 1-byte value to a servo register.

        Raises:
            IOError: If communication fails or servo returns an error.
        """
        comm_result, error = self._servo.write1ByteTxRx(self.servo_id, address, value)
        self._check(comm_result, error, f"write1 addr {address}")

    def write2Byte(self, address, value):
        """
        Write a 2-byte value to a servo register.

        Raises:
            IOError: If communication fails or servo returns an error.
        """
        comm_result, error = self._servo.write2ByteTxRx(self.servo_id, address, value)
        self._check(comm_result, error, f"write2 addr {address}")

    # --- Status --------------------------------------------------------------

    def position(self):
        """
        Read the current servo position.

        Returns:
            tuple: (raw_position, degrees) where raw_position is 0-4095
                   and degrees is 0-360.
        """
        pos = self.read2Byte(self.ADDR_PRESENT_POSITION)
        degrees = self.position_to_degrees(pos)
        return pos, degrees

    def torque_enabled(self):
        """
        Check if torque is enabled (servo is holding position).

        Returns:
            bool: True if torque is enabled, False if servo is limp.
        """
        enabled = self.read1Byte(self.ADDR_TORQUE_ENABLE)
        return bool(enabled)

    def moving(self):
        """
        Check if the servo is currently moving.

        Returns:
            bool: True if servo is in motion, False if stationary.
        """
        m = self.read1Byte(self.ADDR_MOVING)
        return bool(m)

    def speed(self):
        """
        Read the current movement speed.

        The speed value is signed to indicate direction:
        - Positive = clockwise (CW), position increasing
        - Negative = counter-clockwise (CCW), position decreasing
        - Zero = stationary

        "Clockwise" is as seen looking at the servo horn.

        Returns:
            int: Current speed in steps/second (negative = CCW, positive = CW).
        """
        speed, comm_result, error = self._servo.ReadSpeed(self.servo_id)
        self._check(comm_result, error, "ReadSpeed")
        return speed

    def direction(self):
        """
        Get the current direction of movement based on speed.

        Returns:
            str or None: "CW" (clockwise), "CCW" (counter-clockwise), or None if stopped.
        """
        speed = self.speed()
        if speed > 0:
            return "CW"
        elif speed < 0:
            return "CCW"
        else:
            return None

    def acceleration(self):
        """
        Read the current acceleration setting.

        Note: This returns the goal/setting value, not real-time feedback.
        Unlike position and speed which have separate "present" registers,
        acceleration only has a setting register. The value returned is
        whatever was last written to the servo.

        Returns:
            int: Acceleration setting (0-254, where 0 = instant).
        """
        return self.read1Byte(self.ADDR_ACCELERATION)

    def voltage(self):
        """
        Read the current input voltage.

        Returns:
            float: Voltage in volts.
        """
        v_raw = self.read1Byte(self.ADDR_PRESENT_VOLTAGE)
        volts = v_raw * 0.1
        return volts

    def temperature(self):
        """
        Read the servo's internal temperature.

        Returns:
            int: Temperature in degrees Celsius.
        """
        temp = self.read1Byte(self.ADDR_PRESENT_TEMPERATURE)
        return temp

    def current_load(self):
        """
        Read the current load/torque on the servo.

        The direction is the direction the *motor* is applying torque. When
        you push the horn by hand while torque is on, the motor pushes back,
        so the reading is opposite to your push: push clockwise and it reads
        "CCW". While the servo moves on its own, the direction matches the
        direction of travel.

        Returns:
            tuple: (load_percent, direction) where load_percent is 0-100
                   and direction is "CW" or "CCW".
        """
        load_raw = self.read2Byte(self.ADDR_PRESENT_LOAD)
        load_magnitude = load_raw & 0x3FF  # Lower 10 bits
        load_direction = "CW" if load_raw & 0x400 else "CCW"  # Bit 10
        load_percent = load_magnitude / 1000 * 100
        return load_percent, load_direction

    def current_draw(self):
        """
        Read the current electrical draw.

        Returns:
            float: Current in milliamps (mA).
        """
        current_raw = self.read2Byte(self.ADDR_PRESENT_CURRENT)
        current_ma = current_raw * 6.5
        return current_ma

    def servo_status(self):
        """
        Read the servo error status register.

        Returns:
            int: Status bitmask (0 = no errors). See STS3215 documentation
                 for bit definitions.
        """
        status_raw = self.read1Byte(self.ADDR_SERVO_STATUS)
        return status_raw

    def errors(self):
        """
        Get a list of active error names.

        Returns:
            list: List of error name strings (e.g., ["Voltage", "Temperature"]).
                  Empty list if no errors.

        Example:
            if s.errors():
                print(f"Errors: {s.errors()}")
        """
        status = self.servo_status()
        active_errors = []
        for bit, name in self.ERROR_FLAGS.items():
            if status & (1 << bit):
                active_errors.append(name)
        return active_errors

    def is_healthy(self):
        """
        Check if the servo has no errors.

        Returns:
            bool: True if no errors, False if any error is active.
        """
        return self.servo_status() == 0

    def status(self):
        """
        Get a comprehensive status summary.

        Takes about a dozen serial round trips (roughly 3-4 ms at 1 Mbps).

        Returns:
            dict: Dictionary containing all status information:
                - position: (raw, degrees)
                - speed: steps/second (negative = CCW, positive = CW)
                - direction: "CW", "CCW", or None if stopped
                - voltage: volts
                - temperature: celsius
                - load: (percent, direction)
                - current: milliamps
                - moving: bool
                - torque_enabled: bool
                - mode: int
                - errors: list of error names
                - healthy: bool

        Example:
            s = servo.status()
            print(f"Position: {s['position'][1]:.1f}°")
            print(f"Healthy: {s['healthy']}")
        """
        pos = self.read2Byte(self.ADDR_PRESENT_POSITION)
        spd = self.speed()
        status = self.servo_status()
        return {
            "position": (pos, self.position_to_degrees(pos)),
            "speed": spd,
            "direction": "CW" if spd > 0 else ("CCW" if spd < 0 else None),
            "voltage": self.voltage(),
            "temperature": self.temperature(),
            "load": self.current_load(),
            "current": self.current_draw(),
            "moving": self.moving(),
            "torque_enabled": self.torque_enabled(),
            "mode": self.get_mode(),
            "errors": [name for bit, name in self.ERROR_FLAGS.items() if status & (1 << bit)],
            "healthy": status == 0,
        }

    # --- Control -------------------------------------------------------------

    def enable_torque(self):
        """Enable torque so the servo holds its position."""
        self.write1Byte(self.ADDR_TORQUE_ENABLE, 1)

    def disable_torque(self):
        """Disable torque so the servo can be moved by hand."""
        self.write1Byte(self.ADDR_TORQUE_ENABLE, 0)

    def move_to(self, position, speed=0, acc=0):
        """
        Move servo to a target position (asynchronous).

        Returns immediately after sending the command. Use move_sync() if you
        need to wait for the movement to complete.

        Automatically enables torque and switches back to position mode if the
        servo is in wheel mode.

        Args:
            position: Target position (0-4095, where 2048 is center).
            speed: Movement speed (0 = max speed, or 1-3400 steps/second).
            acc: Acceleration (0 = instant, 1-254 = smoother ramp).

        Raises:
            ValueError: If an argument is out of range.
        """
        if not self.POSITION_MIN <= position <= self.POSITION_MAX:
            raise ValueError(f"position must be {self.POSITION_MIN}-{self.POSITION_MAX}, got {position}")
        if not 0 <= speed <= self.SPEED_MAX:
            raise ValueError(f"speed must be 0-{self.SPEED_MAX}, got {speed}")
        if not 0 <= acc <= self.ACCELERATION_MAX:
            raise ValueError(f"acc must be 0-{self.ACCELERATION_MAX}, got {acc}")

        if self.get_mode() != self.MODE_POSITION:
            self.set_mode(self.MODE_POSITION)

        if not self.torque_enabled():
            self.enable_torque()

        comm_result, error = self._servo.WritePosEx(self.servo_id, int(position), int(speed), int(acc))
        self._check(comm_result, error, "WritePosEx")

    def move_to_degrees(self, degrees, speed=0, acc=0):
        """
        Move servo to a target position specified in degrees (asynchronous).

        Convenience wrapper around move_to() that accepts degrees instead of
        raw position values. 360° is treated as the last step (4095).

        Args:
            degrees: Target angle (0-360, where 180 is center).
            speed: Movement speed (0 = max speed, or 1-3400 steps/second).
            acc: Acceleration (0 = instant, 1-254 = smoother ramp).
        """
        if not 0 <= degrees <= 360:
            raise ValueError(f"degrees must be 0-360, got {degrees}")
        position = self.degrees_to_position(degrees)
        self.move_to(position, speed, acc)

    def move_sync(self, target, tolerance=10, timeout=10, speed=0, acc=0):
        """
        Move servo to a target position and wait until it arrives (synchronous).

        Blocks until the servo reaches the target position within the specified
        tolerance and stops moving.

        Args:
            target: Target position (0-4095).
            tolerance: Acceptable position error in steps (default: 10).
            timeout: Maximum seconds to wait (default: 10).
            speed: Movement speed (0 = max speed, or 1-3400 steps/second).
            acc: Acceleration (0 = instant, 1-254 = smoother ramp).

        Returns:
            int: Final position after movement completes.

        Raises:
            TimeoutError: If servo doesn't start moving or reach target in time.
        """
        start = time.perf_counter()
        self.move_to(target, speed, acc)
        # Wait for movement to start (or confirm we're already there)
        while True:
            if time.perf_counter() - start > timeout:
                raise TimeoutError("Servo never started moving.")

            position = self.read2Byte(self.ADDR_PRESENT_POSITION)
            moving = self.read1Byte(self.ADDR_MOVING)
            if moving or abs(position - target) <= tolerance:
                break
            time.sleep(0.005)

        # Wait for movement to complete
        while True:
            if time.perf_counter() - start > timeout:
                raise TimeoutError("Servo didn't reach target position before timeout.")

            position = self.read2Byte(self.ADDR_PRESENT_POSITION)
            moving = self.read1Byte(self.ADDR_MOVING)

            if not moving and abs(position - target) <= tolerance:
                break
            time.sleep(0.005)

        return position

    def move_sequence(self, positions, tolerance=10, timeout=10):
        """
        Move through a sequence of positions in order.

        Each position is reached before moving to the next (synchronous).

        Args:
            positions: List of target positions (0-4095 each).
            tolerance: Acceptable position error in steps (default: 10).
            timeout: Maximum seconds to wait per move (default: 10).

        Raises:
            TimeoutError: If any movement times out.
        """
        for target in positions:
            self.move_sync(target, tolerance, timeout)

    def get_mode(self):
        """
        Get the current operating mode.

        Returns:
            int: Mode value (0 = position servo, 1 = wheel/velocity,
                 2 = PWM, 3 = step servo).
        """
        mode = self.read1Byte(self.ADDR_MODE)
        return mode

    def set_mode(self, mode):
        """
        Set the operating mode.

        The mode register lives in EEPROM, but the servo ships with EEPROM
        writes locked (register 55 = 1). While locked, the change takes effect
        immediately but is not saved: the servo returns to position mode after
        a power cycle. That is usually what you want while experimenting.

        Args:
            mode: Mode value (0 = position servo, 1 = wheel/velocity,
                  2 = PWM, 3 = step servo).

        Raises:
            ValueError: If mode is not 0-3.
        """
        if mode not in (self.MODE_POSITION, self.MODE_WHEEL, self.MODE_PWM, self.MODE_STEP):
            raise ValueError(f"mode must be 0-3, got {mode}")
        self.write1Byte(self.ADDR_MODE, mode)

    def spin(self, speed, acc=0):
        """
        Spin the servo continuously in wheel mode.

        Automatically switches to wheel mode if not already in it. Torque is
        turned on by the servo itself when a speed is written.
        Use stop() or spin(0) to stop, or move_to() to return to position mode.

        Args:
            speed: Spin speed in steps/second. Positive = CW, negative = CCW,
                   0 = stop. Range is -3400 to 3400; 4096 steps is one turn.
            acc: Acceleration (0 = instant, 1-254 = smoother ramp).

        Example:
            s.spin(500)      # Spin clockwise
            s.spin(-500)     # Spin counter-clockwise
            s.stop()         # Stop spinning
            s.move_to(2048)  # Return to position mode
        """
        if not -self.SPEED_MAX <= speed <= self.SPEED_MAX:
            raise ValueError(f"speed must be -{self.SPEED_MAX}..{self.SPEED_MAX}, got {speed}")
        if not 0 <= acc <= self.ACCELERATION_MAX:
            raise ValueError(f"acc must be 0-{self.ACCELERATION_MAX}, got {acc}")
        if self.get_mode() != self.MODE_WHEEL:
            self.set_mode(self.MODE_WHEEL)
        comm_result, error = self._servo.WriteSpec(self.servo_id, int(speed), int(acc))
        self._check(comm_result, error, "WriteSpec")

    def stop(self):
        """
        Stop the servo if spinning in wheel mode.

        Equivalent to spin(0). The servo remains in wheel mode.
        Use move_to() to return to position mode.
        """
        comm_result, error = self._servo.WriteSpec(self.servo_id, 0, 0)
        self._check(comm_result, error, "WriteSpec")

    def get_id(self):
        """
        Get the current servo ID by reading from the servo's EEPROM register.

        Returns:
            int: The servo ID (0-253).
        """
        return self.read1Byte(self.ADDR_ID)

    def set_id(self, new_id):
        """
        Change the servo's ID.

        The new ID is written to EEPROM and persists after power off.
        After calling this method, the Servo instance's servo_id is updated
        to communicate with the servo at its new address.

        Args:
            new_id: New servo ID (0-253). Must be unique on the bus.

        Raises:
            ValueError: If new_id is out of range.
            IOError: If communication fails.

        Example:
            s = Servo(servo_id=1)
            s.set_id(2)  # Change ID from 1 to 2
            # s.servo_id is now 2, and servo responds to ID 2
        """
        if not 0 <= new_id <= 253:
            raise ValueError(f"Servo ID must be 0-253, got {new_id}")

        # Disable torque before writing to EEPROM
        was_enabled = self.torque_enabled()
        if was_enabled:
            self.disable_torque()

        # Unlock EEPROM so the new ID is saved, not just applied in RAM
        self.write1Byte(self.ADDR_LOCK, 0)

        try:
            self.write1Byte(self.ADDR_ID, new_id)
        except IOError:
            self.write1Byte(self.ADDR_LOCK, 1)
            raise

        # Lock EEPROM and update instance to use new ID
        self.servo_id = new_id
        self.write1Byte(self.ADDR_LOCK, 1)

        # Restore torque state if it was enabled
        if was_enabled:
            self.enable_torque()

    def close_bus(self):
        """
        Close the serial bus connection for this servo's port.

        Closes the shared serial connection and frees the port so other
        programs can use it. Since the connection is shared, this affects
        all Servo instances on the same port.

        Disable torque on each servo individually before calling this if
        you want the servos to go limp:

            s1.disable_torque()
            s2.disable_torque()
            s1.close_bus()  # s2.close_bus() would also work
        """
        if self.SERIAL_PORT in Servo._connections:
            Servo._connections[self.SERIAL_PORT]["handler"].closePort()
            del Servo._connections[self.SERIAL_PORT]
