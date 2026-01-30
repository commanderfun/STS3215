"""Simple servo control for robotics"""

from scservo_sdk import sms_sts, PortHandler
import serial.tools.list_ports
import time

class Servo:
    """Servo Class"""

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

    def __init__(self, servo_id=1, model="STS3215"):
        self.model = model
        self.servo_id = servo_id
        self.SERIAL_PORT = self.find_port()
        if self.SERIAL_PORT:
            # Initialize the comm port and servo handlers
            self._port_handler = PortHandler(self.SERIAL_PORT)
            if self._port_handler.openPort():
                self._servo = sms_sts(self._port_handler)
            else:
                raise IOError(f"Failed to open serial comm port: {self.SERIAL_PORT}")
        else:
            raise IOError("Couldn't find serial port for communication with motor driver board.")


    def find_port(self):
        ports = serial.tools.list_ports.comports()
        port = None
        for p in ports:
            if "serial" in p.description.lower() and "usbmodem" in p.device.lower():
                port = p.device

        return port

    def ping(self):
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
        return position * 360 / (self.POSITION_MAX + 1)  # Convert to degrees

    def read1Byte(self, address):
        read_value, comm_result, error = self._servo.read1ByteTxRx(self.servo_id, address)
        if comm_result != 0:
            raise IOError(f"✗ Communication failed for servo_id: {self.servo_id}, comm_result: {comm_result}")
    
        if error != 0:
            raise IOError(f"Servo {self.servo_id} returned error: {error}")

        return read_value

    def read2Byte(self, address):
        read_value, comm_result, error = self._servo.read2ByteTxRx(self.servo_id, address)
        if comm_result != 0:
            raise IOError(f"✗ Communication failed for servo_id: {self.servo_id}, comm_result: {comm_result}")
    
        if error != 0:
            raise IOError(f"Servo {self.servo_id} returned error: {error}")

        return read_value

    def position(self):
        pos = self.read2Byte(self.ADDR_PRESENT_POSITION)
        degrees = self.position_to_degrees(pos)
        return pos, degrees

    def torque_enabled(self):
        enabled = self.read1Byte(self.ADDR_TORQUE_ENABLE)
        return bool(enabled)

    def moving(self):
        m = self.read1Byte(self.ADDR_MOVING)
        return bool(m)

    def voltage(self):
        v_raw = self.read1Byte(self.ADDR_PRESENT_VOLTAGE)
        volts = v_raw * 0.1  # Convert to volts
        return volts

    def temperature(self):
        temp = self.read1Byte(self.ADDR_PRESENT_TEMPERATURE) 
        return temp # Celcius

    def enable_torque(self):
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_TORQUE_ENABLE, 1)

    def move_to(self, position, speed=0, acc=0):
        """Move servo to desired position. Asyncronous move to position."""                                                            
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
      """Wait until servo reaches target position and stops moving. (Syncronous move)"""                                                            
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
          for target in positions:                                                                                                           
            self.move_sync(target, tolerance, timeout)


    def current_load(self):
        load_raw = self.read2Byte(self.ADDR_PRESENT_LOAD)
        load_magnitude = load_raw & 0x3FF  # Lower 10 bits
        load_direction = "CW" if load_raw & 0x400 else "CCW"  # Bit 10
        load_percent = load_magnitude / 1000 * 100
        return load_percent, load_direction

    def current_draw(self):
        current_raw = self.read2Byte(self.ADDR_PRESENT_CURRENT)
        current_ma = current_raw * 6.5  # Convert to milliamps
        return current_ma

    def servo_status(self):
        status_raw = self.read1Byte(self.ADDR_SERVO_STATUS)
        return status_raw

    def get_mode(self):
        mode = self.read1Byte(self.ADDR_MODE)
        return mode

    def set_mode(self, mode):
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_MODE, mode)

    def disconnect(self):
        self._servo.write1ByteTxRx(self.servo_id, self.ADDR_TORQUE_ENABLE, 0)
        self._port_handler.closePort()
