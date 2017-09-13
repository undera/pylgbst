import logging
import struct
import time

from pylegoboost.constants import *

log = logging.getLogger('movehub')


class MoveHub(object):
    """
    :type connection: pylegoboost.comms.Connection
    :type led: LED
    """

    def __init__(self, connection):
        self.notified = False

        self.connection = connection

        self.led = LED(self)
        self.motor_A = EncodedMotor(self, PORT_A)
        self.motor_B = EncodedMotor(self, PORT_B)
        self.motor_AB = EncodedMotor(self, PORT_AB)

        # self.button
        # self.tilt_sensor

        # enables notifications reading
        self.connection.set_notify_handler(self._notify)
        self.connection.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

        # while not self.notified:
        # log.debug("Waiting to be notified")
        # time.sleep(1)

        # self.port_C = None
        # self.port_D = None

        # transport.write(MOVE_HUB_HARDWARE_HANDLE, b'\x0a\x00\x41\x01\x08\x01\x00\x00\x00\x01')

    def _notify(self, handle, data):
        # TODO
        log.debug("Notification on %s: %s", handle, data.encode("hex"))

    def get_name(self):
        # note: reading this too fast makes it hang
        self.connection.read(DEVICE_NAME)


class Peripheral(object):
    """
    :type parent: MoveHub
    """

    def __init__(self, parent):
        super(Peripheral, self).__init__()
        self.parent = parent


class LED(Peripheral):
    def set_color(self, color):
        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)

        cmd = CMD_SET_COLOR + chr(color)
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, cmd)


class EncodedMotor(Peripheral):
    TRAILER = b'\x64\x7f\x03'  # NOTE: \x64 is 100, might mean something
    PACKET_VER = b'\x01'
    SET_PORT_VAL = b'\x81'
    MOVEMENT_TYPE = b'\x11'
    TIMED_SINGLE = b'\x09'
    TIMED_GROUP = b'\x0A'
    ANGLED_SINGLE = b'\x0B'
    ANGLED_GROUP = b'\x0C'

    def __init__(self, parent, port):
        super(EncodedMotor, self).__init__(parent)
        if port not in PORTS:
            raise ValueError("Invalid port for motor: %s" % port)
        self.port = port

    def _speed_abs(self, relative):
        if relative < -1 or relative > 1:
            raise ValueError("Invalid speed value: %s", relative)

        absolute = round(relative * 100)
        if absolute < 0:
            absolute += 255
        return int(absolute)

    def _wrap_and_write(self, command, speed_primary, speed_secondary):
        # set for port
        command = self.SET_PORT_VAL + chr(self.port) + self.MOVEMENT_TYPE + command

        command += chr(self._speed_abs(speed_primary))
        if self.port == PORT_AB:
            command += chr(self._speed_abs(speed_secondary))

        command += self.TRAILER

        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, chr(len(command) + 1) + self.PACKET_VER + command)

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
