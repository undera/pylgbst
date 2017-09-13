import logging
import struct
import time

from pylegoboost.constants import *

log = logging.getLogger('movehub')


class MoveHub(object):
    """
    :type connection: pylegoboost.comms.Connection
    :type led: LED
    :type devices: dict[int,Peripheral]
    """

    def __init__(self, connection):
        self.connection = connection
        self.devices = {}

        # shorthand fields
        self.led = None
        self.motor_A = None
        self.motor_B = None
        self.motor_AB = None

        self.tilt_sensor = None
        self.color_distance_sensor = None
        # self.button

        # enables notifications reading
        self.connection.set_notify_handler(self._notify)
        self.connection.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

        # while not self.notified:
        # log.debug("Waiting to be notified")
        # time.sleep(1)

        self.port_C = None
        self.port_D = None

        # transport.write(MOVE_HUB_HARDWARE_HANDLE, b'\x0a\x00\x41\x01\x08\x01\x00\x00\x00\x01')

    def get_name(self):
        # note: reading this too fast makes it hang
        self.connection.read(DEVICE_NAME)

    def _notify(self, handle, data):
        """
        Using https://github.com/JorgePe/BOOSTreveng/blob/master/Notifications.md
        """
        orig = data
        log.debug("Notification on %s: %s", handle, orig.encode("hex"))
        data = data[3:]

        msg_type = ord(data[2])

        if msg_type == MSG_PORT_INFO:
            self._handle_port_info(data)
        else:
            log.warning("Unhandled msg type %s: %s", msg_type, orig.encode("hex"))

        pass

    def _handle_port_info(self, data):
        port = ord(data[3])
        dev_type = ord(data[5])

        if port in PORTS and dev_type in DEVICE_TYPES:
            log.debug("Device %s at port %s", DEVICE_TYPES[dev_type], PORTS[port])
        else:
            log.debug("Device 0x%x at port 0x%x", dev_type, port)

        if dev_type == TYPE_MOTOR:
            self.devices[port] = EncodedMotor(self, port)
        elif dev_type == TYPE_IMOTOR:
            self.devices[port] = EncodedMotor(self, port)
        elif dev_type == TYPE_DISTANCE_COLOR_SENSOR:
            self.devices[port] = ColorDistanceSensor(self, port)
            self.color_distance_sensor = self.devices[port]
        elif dev_type == TYPE_LED:
            self.devices[port] = LED(self, port)
        elif dev_type == TYPE_TILT_SENSOR:
            self.devices[port] = TiltSensor(self, port)
        else:
            log.warning("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)

        if port == PORT_A:
            self.motor_A = self.devices[port]
        elif port == PORT_B:
            self.motor_B = self.devices[port]
        elif port == PORT_AB:
            self.motor_AB = self.devices[port]
        elif port == PORT_C:
            self.port_C = self.devices[port]
        elif port == PORT_D:
            self.port_D = self.devices[port]
        elif port == PORT_LED:
            self.led = self.devices[port]
        elif port == PORT_TILT_SENSOR:
            self.tilt_sensor = self.devices[port]
        else:
            log.warning("Unhandled port: %s", PORTS[port])


class Peripheral(object):
    """
    :type parent: MoveHub
    """
    PACKET_VER = b'\x01'
    SET_PORT_VAL = b'\x81'

    def __init__(self, parent, port):
        super(Peripheral, self).__init__()
        self.parent = parent
        self.port = port

    def _set_port_val(self, value):
        cmd = self.PACKET_VER + self.SET_PORT_VAL + chr(self.port)
        cmd += value

        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, chr(len(cmd)) + cmd)


class LED(Peripheral):
    def set_color(self, color):
        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)

        cmd = '\x11\x51\x00' + chr(color)
        self._set_port_val(cmd)


class EncodedMotor(Peripheral):
    TRAILER = b'\x64\x7f\x03'  # NOTE: \x64 is 100, might mean something
    MOVEMENT_TYPE = b'\x11'
    TIMED_SINGLE = b'\x09'
    TIMED_GROUP = b'\x0A'
    ANGLED_SINGLE = b'\x0B'
    ANGLED_GROUP = b'\x0C'

    def __init__(self, parent, port):
        super(EncodedMotor, self).__init__(parent, port)
        if port not in [PORT_A, PORT_B, PORT_AB, PORT_C, PORT_D]:
            raise ValueError("Invalid port for motor: %s" % port)

    def _speed_abs(self, relative):
        if relative < -1 or relative > 1:
            raise ValueError("Invalid speed value: %s", relative)

        absolute = round(relative * 100)
        if absolute < 0:
            absolute += 255
        return int(absolute)

    def _wrap_and_write(self, command, speed_primary, speed_secondary):
        # set for port
        command = self.MOVEMENT_TYPE + command

        command += chr(self._speed_abs(speed_primary))
        if self.port == PORT_AB:
            command += chr(self._speed_abs(speed_secondary))

        command += self.TRAILER

        self._set_port_val(command)

    def timed(self, seconds, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        # movement type
        command = self.TIMED_GROUP if self.port == PORT_AB else self.TIMED_SINGLE
        # time
        msec = int(seconds * 1000)
        if msec > 255 * 255:
            raise ValueError("Too large value for seconds: %s", seconds)
        command += struct.pack('<H', msec)

        self._wrap_and_write(command, speed_primary, speed_secondary)

        if not async:
            time.sleep(seconds)

    def angled(self, angle, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        # movement type
        command = self.ANGLED_GROUP if self.port == PORT_AB else self.ANGLED_SINGLE
        # angle
        command += struct.pack('<I', angle)

        self._wrap_and_write(command, speed_primary, speed_secondary)
        # TODO: how to tell when motor has stopped?


class ColorDistanceSensor(Peripheral):
    pass


class TiltSensor(Peripheral):
    pass
