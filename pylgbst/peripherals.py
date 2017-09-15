import logging
import struct
import time

from pylgbst import get_byte, int2byte, str2hex
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
        self._subscribers = set()

    def __repr__(self):
        return "%s on port %s" % (self.__class__.__name__, PORTS[self.port] if self.port in PORTS else 'N/A')

    def _write_to_hub(self, msg_type, params):
        cmd = int2byte(PACKET_VER) + int2byte(msg_type) + int2byte(self.port)
        cmd += params
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE,
                                     int2byte(len(cmd) + 1) + cmd)  # should we +1 cmd len here?

    def started(self):
        self.working = True

    def finished(self):
        self.working = False

    def _notify_subscribers(self, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)

    def handle_sensor_data(self, data):
        log.warning("Unhandled device notification for %s: %s", self, str2hex(data))


class LED(Peripheral):
    def set_color(self, color):
        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)

        cmd = b'\x01\x51\x00' + int2byte(color)
        self._write_to_hub(MSG_SET_PORT_VAL, cmd)

    def finished(self):
        super(LED, self).finished()
        log.debug("LED has changed color")


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

        command += int2byte(self._speed_abs(speed_primary))
        if self.port == PORT_AB:
            command += int2byte(self._speed_abs(speed_secondary))

        command += self.TRAILER

        self._write_to_hub(MSG_SET_PORT_VAL, command)

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


class TiltSensor(Peripheral):
    TRAILER = b'\x00\x00\x00'

    def __init__(self, parent, port):
        super(TiltSensor, self).__init__(parent, port)
        self.mode = None

    def subscribe(self, callback, mode=TILT_SENSOR_MODE_BASIC, granularity=1):
        self.mode = mode

        params = int2byte(self.mode)
        params += int2byte(granularity)
        params += self.TRAILER
        params += int2byte(1)  # enable
        self._write_to_hub(MSG_SENSOR_SUBSCRIBE, params)
        self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._subscribers:
            self._write_to_hub(MSG_SENSOR_SUBSCRIBE, int2byte(self.mode) + b'\x00\x00\x00' + int2byte(0))
            self.mode = None

    def handle_sensor_data(self, data):
        if self.mode == TILT_SENSOR_MODE_BASIC:
            state = get_byte(data, 4)
            self._notify_subscribers(state)
        elif self.mode == TILT_SENSOR_MODE_2AXIS_SIMPLE:
            # TODO: figure out right interpreting of this
            state = get_byte(data, 4)
            self._notify_subscribers(state)
        elif self.mode == TILT_SENSOR_MODE_BUMP:
            bump_count = get_byte(data, 4)
            self._notify_subscribers(bump_count)
        elif self.mode == TILT_SENSOR_MODE_2AXIS_FULL:
            roll = self._byte2deg(get_byte(data, 4))
            pitch = self._byte2deg(get_byte(data, 5))
            self._notify_subscribers(roll, pitch)
        elif self.mode == TILT_SENSOR_MODE_FULL:
            roll = self._byte2deg(get_byte(data, 4))
            pitch = self._byte2deg(get_byte(data, 5))
            yaw = self._byte2deg(get_byte(data, 6))  # did I get the order right?
            self._notify_subscribers(roll, pitch, yaw)
        else:
            log.debug("Got tilt sensor data while in unexpected mode: %s", self.mode)

    def _byte2deg(self, val):
        if val > 90:
            return val - 256
        else:
            return val


class ColorDistanceSensor(Peripheral):
    def __init__(self, parent, port):
        super(ColorDistanceSensor, self).__init__(parent, port)
        self.mode = None

    def subscribe(self, callback, mode=CDS_MODE_COLOR_DISTANCE_INCHES_SUBINCHES, granularity=1):
        self.mode = mode
        params = int2byte(mode)
        params += int2byte(granularity)
        params += b'\x00\x00\x00'
        params += int2byte(1)  # enable
        self._write_to_hub(MSG_SENSOR_SUBSCRIBE, params)
        self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._subscribers:
            self._write_to_hub(MSG_SENSOR_SUBSCRIBE, int2byte(self.mode) + b'\x01\x00\x00\x00' + int2byte(0))
            self.mode = None

    def handle_sensor_data(self, data):
        if self.mode == CDS_MODE_COLOR_DISTANCE_INCHES_SUBINCHES:
            color = get_byte(data, 4)
            distance = get_byte(data, 5)
            partial = get_byte(data, 7)
            if partial:
                distance += 1.0 / partial
            self._notify_subscribers(color if color != 0xFF else None, float(distance))
        elif self.mode == CDS_MODE_COLOR_ONLY:
            color = get_byte(data, 4)
            self._notify_subscribers(color if color != 0xFF else None)
        elif self.mode == CDS_MODE_DISTANCE_INCHES:
            distance = get_byte(data, 4)
            self._notify_subscribers(float(distance))
        elif self.mode == CDS_MODE_DISTANCE_HOW_CLOSE:
            distance = get_byte(data, 4)
            self._notify_subscribers(float(distance))
        elif self.mode == CDS_MODE_DISTANCE_SUBINCH_HOW_CLOSE:
            distance = get_byte(data, 4)
            self._notify_subscribers(float(distance))
        elif self.mode == CDS_MODE_OFF1 or self.mode == CDS_MODE_OFF2:
            log.info("Turned off led on %s", self)
        elif self.mode == CDS_MODE_COUNT_2INCH:
            count = struct.unpack("<L", data[4:8])[0]  # is it all 4 bytes or just 2?
            self._notify_subscribers(count)
        elif self.mode == CDS_MODE_STREAM_3_VALUES:
            # TODO: understand better meaning of these 3 values
            val1 = struct.unpack("<H", data[4:6])[0]
            val2 = struct.unpack("<H", data[6:8])[0]
            val3 = struct.unpack("<H", data[8:10])[0]
            self._notify_subscribers(val1, val2, val3)
        elif self.mode == CDS_MODE_LUMINOSITY:
            luminosity = struct.unpack("<H", data[4:6])[0]
            self._notify_subscribers(luminosity)
        else:  # TODO: support whatever we forgot
            log.warning("Unhandled data in mode %s: %s", self.mode, str2hex(data))


# 0a00 41 01 01 enable


class Button(Peripheral):
    def __init__(self, parent):
        super(Button, self).__init__(parent, 0)


LISTEN_ENCODER_ON_A = b'        \x0a\x00 \x41\x37 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_B = b'        \x0a\x00 \x41\x38 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_C = b'        \x0a\x00 \x41\x01 \x02\x01\x00\x00\x00\x01'
LISTEN_ENCODER_ON_D = b'        \x0a\x00 \x41\x02 \x02\x01\x00\x00\x00\x01'
