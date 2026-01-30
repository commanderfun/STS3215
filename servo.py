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
    s.disconnect()

    # If auto-detection fails, specify port manually:
    Servo.list_ports()  # Show available ports
    s = Servo(port="/dev/cu.usbmodem1101")
"""

from scservo_sdk import sms_sts, PortHandler
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
    ADDR_PRESENT_POSITION = 56
    ADDR_PRESENT_VOLTAGE = 62
    ADDR_PRESENT_TEMPERATURE = 63
    ADDR_MOVING = 66
    ADDR_TORQUE_ENABLE = 40
    ADDR_GOAL_POSITION = 42
    ADDR_PRESENT_LOAD = 60
    ADDR_PRESENT_CURRENT = 69
    ADDR_SERVO_STATUS = 65
    DDR_MAX_TEMP_LIMIT = 13
    ADDR_MAX_VOLTAGE_LIMIT = 14
    ADDR_MIN_VOLTAGE_LIMIT = 15
    ADDR_MIN_ANGLE_LIMIT = 9
    ADDR_MAX_ANGLE_LIMIT = 11
    ADDR_MODE = 33

    POSITION_MIN = 0
    POSITION_MAX = 4095

    _port_handler = None
    _servo = None

    def __init__(self, servo_id=1, model="STS3215", port=None):
        """
        Initialize connection to a servo.

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
        if self.SERIAL_PORT:
            # Initialize the comm port and servo handlers
            self._port_handler = PortHandler(self.SERIAL_PORT)
            if self._port_handler.openPort():
                self._servo = sms_sts(self._port_handler)
            else:
                raise IOError(f"Failed to open serial comm port: {self.SERIAL_PORT}")
        else:
            raise IOError(
                "Couldn't auto-detect serial port. "
                "Use Servo.list_ports() to find available ports, "
                "then create with Servo(port='/dev/cu.usbmodemXXXX')."
            )


    def find_port(self):
        """
        Auto-detect the serial port for the servo driver board.

        Searches for USB serial devices matching the Waveshare driver board
        pattern (usbmodem devices with "serial" in description).

        Returns:
            str or None: Device path (e.g., "/dev/cu.usbmodem1101") or None if not found.
        """
        ports = serial.tools.list_ports.comports()
        port = None
        for p in ports:
            if "serial" in p.description.lower() and "usbmodem" in p.device.lower():
                port = p.device

        return port

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

        Raises:
            IOError: If communication fails or servo doesn't respond.
        """
        if self._port_handler.openPort():
            # Ping the servo to check communication
            model_number, comm_result, error = self._servo.ping(self.servo_id)
            if comm_result == 0:  # COMM_SUCCESS
                print(f"✓ Serial comm port: {self.SERIAL_PORT}")
                print(f"✓ Successfully pinged servo ID {self.servo_id}")
                print(f"✓ Model number: {model_number}")
                # return True
            else:
                raise IOError(f"✗ Failed to ping servo_id: {self.servo_id}")
        else:
            raise IOError(f"✗ Failed to open serial comm port.")

    def position_to_degrees(self, position):
        """
        Convert a raw position value to degrees.

        Args:
            position: Raw position value (0-4095).

        Returns:
            float: Angle in degrees (0-360).
        """
        return position * 360 / (self.POSITION_MAX + 1)

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
        if comm_result != 0:
            raise IOError(f"✗ Communication failed for servo_id: {self.servo_id}, comm_result: {comm_result}")

        if error != 0:
            raise IOError(f"Servo {self.servo_id} returned error: {error}")

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
        if comm_result != 0:
            raise IOError(f"✗ Communication failed for servo_id: {self.servo_id}, comm_result: {comm_result}")

        if error != 0:
            raise IOError(f"Servo {self.servo_id} returned error: {error}")

        return read_value

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

    def enable_torque(self):
        """Enable torque so the servo holds its position."""
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_TORQUE_ENABLE, 1)

    def move_to(self, position, speed=0, acc=0):
        """
        Move servo to a target position (asynchronous).

        Returns immediately after sending the command. Use move_sync() if you
        need to wait for the movement to complete.

        Automatically enables torque and sets position mode if needed.

        Args:
            position: Target position (0-4095, where 2048 is center).
            speed: Movement speed (0 = max speed, or steps/second).
            acc: Acceleration (0 = max acceleration).
        """
        if self.get_mode() != 0:
            # Set mode back to 0 (Position servo mode)
            self.set_mode(0)

        if not self.torque_enabled():
            # Restore angle limits (0-4095 = full 360° range)
            self._servo.write2ByteTxRx(self.servo_id, self.ADDR_MIN_ANGLE_LIMIT, 0)
            self._servo.write2ByteTxRx(self.servo_id, self.ADDR_MAX_ANGLE_LIMIT, 4095)
            self.enable_torque()

        self._servo.WritePosEx(self.servo_id, position, speed, acc)

    def move_sync(self, target, tolerance=10, timeout=10):
        """
        Move servo to a target position and wait until it arrives (synchronous).

        Blocks until the servo reaches the target position within the specified
        tolerance and stops moving.

        Args:
            target: Target position (0-4095).
            tolerance: Acceptable position error in steps (default: 10).
            timeout: Maximum seconds to wait (default: 10).

        Returns:
            int: Final position after movement completes.

        Raises:
            TimeoutError: If servo doesn't start moving or reach target in time.
        """
        start = time.perf_counter()
        position = self.read2Byte(self.ADDR_PRESENT_POSITION)
        self.move_to(target)
        # Wait for movement to start
        while True:
            if time.perf_counter() - start > timeout:
                raise TimeoutError("Servo never started moving.")

            moving = self.read1Byte(self.ADDR_MOVING)
            if moving or abs(position - target) <= tolerance:
                break

        # Wait for movement to complete
        while True:
            if time.perf_counter() - start > timeout:
                raise TimeoutError("Servo didn't reach target position before timeout.")

            position = self.read2Byte(self.ADDR_PRESENT_POSITION)
            moving = self.read1Byte(self.ADDR_MOVING)

            if not moving and abs(position - target) <= tolerance:
                break

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


    def current_load(self):
        """
        Read the current load/torque on the servo.

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

        Args:
            mode: Mode value (0 = position servo, 1 = wheel/velocity,
                  2 = PWM, 3 = step servo).
        """
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_MODE, mode)

    def disconnect(self):
        """
        Disable torque and close the serial connection.

        Call this when done to release the servo (make it limp) and
        free the serial port.
        """
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_TORQUE_ENABLE, 0)
        self._port_handler.closePort()
