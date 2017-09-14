import struct
import time

from pylgbst.constants import *


class Peripheral(object):
    """
    :type parent: MoveHub
    """
    PACKET_VER = b'\x01'

    def __init__(self, parent, port):
        super(Peripheral, self).__init__()
        self.parent = parent
        self.port = port
        self.working = False

    def _set_port_val(self, value):
        cmd = self.PACKET_VER + chr(MSG_SET_PORT_VAL) + chr(self.port)
        cmd += value

        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, chr(len(cmd)) + cmd)  # should we +1 cmd len here?

    def started(self):
        self.working = True

    def finished(self):
        self.working = False

    def __repr__(self):
        return "%s on port %s" % (self.__class__.__name__, PORTS[self.port])


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
