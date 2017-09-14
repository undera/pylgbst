import logging
import struct
import time

from pylgbst import get_byte
from pylgbst.constants import *

log = logging.getLogger('peripherals')


class Peripheral(object):
    """
    :type parent: MoveHub
    """

    def __init__(self, parent, port):
        """
        :type parent: pylgbst.MoveHub
        :type port: int
        """
        super(Peripheral, self).__init__()
        self.parent = parent
        self.port = port
        self.working = False
        self._subscribers = []

    def __repr__(self):
        return "%s on port %s" % (self.__class__.__name__, PORTS[self.port] if self.port in PORTS else 'N/A')

    def _write_to_hub(self, msg_type, params):
        cmd = PACKET_VER + chr(msg_type) + chr(self.port)
        cmd += params
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, chr(len(cmd) + 1) + cmd)  # should we +1 cmd len here?

    def _set_port_val(self, value):
        # FIXME: became obsolete
        self._write_to_hub(MSG_SET_PORT_VAL, value)

    def _subscribe_on_port(self, params):
        # FIXME: became obsolete
        self._write_to_hub(MSG_SENSOR_SUBSCRIBE, params)

    def started(self):
        self.working = True

    def finished(self):
        self.working = False

    def _notify_subscribers(self, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)


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
        if msec >= pow(2, 16):
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
    def _switch_mode(self, simple):
        self._subscribe_on_port(chr(simple) + b'\x01\x00\x00\x00\x01')

    def subscribe(self, callback, mode=TILT_SENSOR_MODE_BASIC):
        if mode not in (TILT_SENSOR_MODE_BASIC, TILT_SENSOR_MODE_SOME1, TILT_SENSOR_MODE_FULL):
            raise ValueError("Wrong tilt sensor mode: 0x%x", mode)
        self._switch_mode(mode)
        self._subscribers.append(callback)  # TODO: maybe join it into `_subscribe_on_port`

        # 1b0e00 0a00 47 3a020100000001
        # 1b0e00 0a00 47 3a020100000001

        # 1b0e000a00  47 3a030100000001 - sent finish?

    def unsubscribe(self, callback):
        self._subscribers.remove(callback)
        if not self._subscribers:
            self._switch_mode(3)

    def handle_notification(self, data):
        if len(data) == 5:
            state = get_byte(data, 4)
            self._notify_subscribers(state)
        elif len(data) == 6:
            # TODO: how to interpret these 2 bytes?
            self._notify_subscribers(get_byte(data, 4), get_byte(data, 5))
        else:
            log.warning("Unexpected length for tilt sensor data: %s", len(data))


class Button(Peripheral):
    def __init__(self, parent):
        super(Button, self).__init__(parent, None)


LISTEN_COLOR_SENSOR_ON_C = b'   \x0a\x00 \x41\x01 \x08\x01\x00\x00\x00\x01'
LISTEN_COLOR_SENSOR_ON_D = b'   \x0a\x00 \x41\x02 \x08\x01\x00\x00\x00\x01'

LISTEN_DIST_SENSOR_ON_C = b'    \x0a\x00 \x41\x01 \x08\x01\x00\x00\x00\x01'
LISTEN_DIST_SENSOR_ON_D = b'    \x0a\x00 \x41\x02 \x08\x01\x00\x00\x00\x01'

LISTEN_ENCODER_ON_A = b'        \x0a\x00 \x41\x37 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_B = b'        \x0a\x00 \x41\x38 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_C = b'        \x0a\x00 \x41\x01 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_D = b'        \x0a\x00 \x41\x02 \x02\x01\x00\x00\x00\x01'
