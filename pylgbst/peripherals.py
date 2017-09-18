import logging
import time
from struct import pack, unpack
from threading import Thread

from six.moves import queue

from pylgbst import get_byte, str2hex
from pylgbst.constants import *

log = logging.getLogger('peripherals')


class Peripheral(object):
    """
    :type parent: MoveHub
    :type _incoming_port_data: queue.Queue
    """

    def __init__(self, parent, port):
        """
        :type parent: pylgbst.MoveHub
        :type port: int
        """
        super(Peripheral, self).__init__()
        self.parent = parent
        self.port = port
        self._working = False
        self._subscribers = set()
        self._port_subscription_mode = None
        self._incoming_port_data = queue.Queue()
        thr = Thread(target=self._queue_reader)
        thr.setDaemon(True)
        thr.setName("Port data queue: %s" % self)
        thr.start()

    def __repr__(self):
        return "%s on port %s" % (self.__class__.__name__, PORTS[self.port] if self.port in PORTS else self.port)

    def _write_to_hub(self, msg_type, params):
        cmd = pack("<B", PACKET_VER) + pack("<B", msg_type) + pack("<B", self.port)
        cmd += params
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, pack("<B", len(cmd) + 1) + cmd)

    def _port_subscribe(self, mode, granularity, enable):
        params = pack("<B", mode)
        params += pack("<H", granularity)
        params += b'\x00\x00'  # maybe also bytes of granularity
        params += pack("<?", bool(enable))
        self._write_to_hub(MSG_SENSOR_SUBSCRIBE, params)

    def started(self):
        log.debug("Started: %s", self)
        self._working = True

    def finished(self):
        log.debug("Finished: %s", self)
        self._working = False

    def in_progress(self):
        return bool(self._working)

    def subscribe(self, callback, mode, granularity=1):
        self._port_subscription_mode = mode
        self._port_subscribe(self._port_subscription_mode, granularity, True)
        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._port_subscription_mode:
            log.warning("Attempt to unsubscribe while never subscribed: %s", self)
        elif not self._subscribers:
            self._port_subscribe(self._port_subscription_mode, 0, False)
            self._port_subscription_mode = None

    def _notify_subscribers(self, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)

    def queue_port_data(self, data):
        self._incoming_port_data.put(data)

    def handle_port_data(self, data):
        log.warning("Unhandled device notification for %s: %s", self, str2hex(data[4:]))
        self._notify_subscribers(data[4:])

    def _queue_reader(self):
        while True:
            data = self._incoming_port_data.get()
            try:
                self.handle_port_data(data)
            except BaseException:
                log.warning("Failed to handle port data by %s: %s", self, str2hex(data))


class LED(Peripheral):
    SOMETHING = b'\x51\x00'

    def __init__(self, parent, port):
        super(LED, self).__init__(parent, port)
        self._last_color_set = COLOR_NONE

    def set_color(self, color, do_notify=True):
        if color == COLOR_NONE:
            color = COLOR_BLACK

        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)

        self._last_color_set = color
        cmd = pack("<B", do_notify) + self.SOMETHING + pack("<B", color)
        self.started()
        self._write_to_hub(MSG_SET_PORT_VAL, cmd)

    def finished(self):
        super(LED, self).finished()
        log.debug("LED has changed color to %s", COLORS[self._last_color_set])
        self._notify_subscribers(self._last_color_set)

    def subscribe(self, callback, mode=None, granularity=None):
        self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)


class EncodedMotor(Peripheral):
    TRAILER = b'\x64\x7f\x03'  # NOTE: \x64 is 100, might mean something
    MOVEMENT_TYPE = b'\x11'

    CONSTANT_SINGLE = b'\x01'
    CONSTANT_GROUP = b'\x02'
    TIMED_SINGLE = b'\x09'
    TIMED_GROUP = b'\x0A'
    ANGLED_SINGLE = b'\x0B'
    ANGLED_GROUP = b'\x0C'

    def _speed_abs(self, relative):
        if relative < -1:
            log.warning("Speed cannot be less than -1")
            relative = -1

        if relative > 1:
            log.warning("Speed cannot be more than 1")
            relative = 1

        absolute = round(relative * 100)
        if absolute < 0:
            absolute += 255
        return int(absolute)

    def _wrap_and_write(self, command, speed_primary, speed_secondary):
        # set for port
        command = self.MOVEMENT_TYPE + command

        command += pack("<B", self._speed_abs(speed_primary))
        if self.port == PORT_AB:
            command += pack("<B", self._speed_abs(speed_secondary))

        command += self.TRAILER

        self._write_to_hub(MSG_SET_PORT_VAL, command)

    def timed(self, seconds, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        # movement type
        command = self.TIMED_GROUP if self.port == PORT_AB else self.TIMED_SINGLE
        # time
        command += pack('<H', int(seconds * 1000))

        self.started()
        self._wrap_and_write(command, speed_primary, speed_secondary)
        self.__wait_sync(async)

    def angled(self, angle, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        if angle < 0:
            angle = -angle
            speed_primary = -speed_primary
            speed_secondary = -speed_secondary

        # movement type
        command = self.ANGLED_GROUP if self.port == PORT_AB else self.ANGLED_SINGLE
        # angle
        command += pack('<I', angle)

        self.started()
        self._wrap_and_write(command, speed_primary, speed_secondary)
        self.__wait_sync(async)

    def constant(self, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        # movement type
        command = self.CONSTANT_GROUP if self.port == PORT_AB else self.CONSTANT_SINGLE

        self.started()
        self._wrap_and_write(command, speed_primary, speed_secondary)
        self.__wait_sync(async)

    def stop(self):
        self.constant(0)

    def test(self, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        self.started()

        # self._wrap_and_write(command, 0.2, 0.2)

        # set for port
        command = self.MOVEMENT_TYPE + b"\x02"

        command += pack('<B', self._speed_abs(speed_primary))  # time or angle - first param
        command += pack('<B', self._speed_abs(speed_secondary))  # time or angle - first param

        speed_primary = 0.5
        speed_secondary = -0.5
        # command += pack("<B", self._speed_abs(speed_primary))
        # if self.port == PORT_AB:
        #    command += pack("<B", self._speed_abs(speed_secondary))

        # command += self.TRAILER

        self._write_to_hub(MSG_SET_PORT_VAL, command)

    def __wait_sync(self, async):
        if not async:
            log.debug("Waiting for sync command work to finish...")
            while self.in_progress():
                time.sleep(0.5)
            log.debug("Command has finished.")

    def handle_port_data(self, data):
        if self._port_subscription_mode == MOTOR_MODE_ANGLE:
            rotation = unpack("<l", data[4:8])[0]
            self._notify_subscribers(rotation)
        elif self._port_subscription_mode == MOTOR_MODE_SOMETHING1:
            # TODO: understand what it means
            rotation = unpack("<B", data[4])[0]
            self._notify_subscribers(rotation)
        elif self._port_subscription_mode == MOTOR_MODE_SPEED:
            rotation = unpack("<b", data[4])[0]
            self._notify_subscribers(rotation)
        else:
            log.debug("Got motor sensor data while in unexpected mode: %s", self._port_subscription_mode)

    def subscribe(self, callback, mode=MOTOR_MODE_ANGLE, granularity=1):
        super(EncodedMotor, self).subscribe(callback, mode, granularity)


class TiltSensor(Peripheral):
    def subscribe(self, callback, mode=TILT_MODE_BASIC, granularity=1):
        super(TiltSensor, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, data):
        if self._port_subscription_mode == TILT_MODE_BASIC:
            state = get_byte(data, 4)
            self._notify_subscribers(state)
        elif self._port_subscription_mode == TILT_MODE_2AXIS_SIMPLE:
            # TODO: figure out right interpreting of this
            state = get_byte(data, 4)
            self._notify_subscribers(state)
        elif self._port_subscription_mode == TILT_MODE_BUMP:
            bump_count = get_byte(data, 4)
            self._notify_subscribers(bump_count)
        elif self._port_subscription_mode == TILT_MODE_2AXIS_FULL:
            roll = self._byte2deg(get_byte(data, 4))
            pitch = self._byte2deg(get_byte(data, 5))
            self._notify_subscribers(roll, pitch)
        elif self._port_subscription_mode == TILT_MODE_FULL:
            roll = self._byte2deg(get_byte(data, 4))
            pitch = self._byte2deg(get_byte(data, 5))
            yaw = self._byte2deg(get_byte(data, 6))  # did I get the order right?
            self._notify_subscribers(roll, pitch, yaw)
        else:
            log.debug("Got tilt sensor data while in unexpected mode: %s", self._port_subscription_mode)

    def _byte2deg(self, val):
        if val > 90:
            return val - 256
        else:
            return val


class ColorDistanceSensor(Peripheral):
    def __init__(self, parent, port):
        super(ColorDistanceSensor, self).__init__(parent, port)

    def subscribe(self, callback, mode=CDS_MODE_COLOR_DISTANCE_FLOAT, granularity=1):
        super(ColorDistanceSensor, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, data):
        if self._port_subscription_mode == CDS_MODE_COLOR_DISTANCE_FLOAT:
            color = get_byte(data, 4)
            distance = get_byte(data, 5)
            partial = get_byte(data, 7)
            if partial:
                distance += 1.0 / partial
            self._notify_subscribers(color, float(distance))
        elif self._port_subscription_mode == CDS_MODE_COLOR_ONLY:
            color = get_byte(data, 4)
            self._notify_subscribers(color)
        elif self._port_subscription_mode == CDS_MODE_DISTANCE_INCHES:
            distance = get_byte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == CDS_MODE_DISTANCE_HOW_CLOSE:
            distance = get_byte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == CDS_MODE_DISTANCE_SUBINCH_HOW_CLOSE:
            distance = get_byte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == CDS_MODE_OFF1 or self._port_subscription_mode == CDS_MODE_OFF2:
            log.info("Turned off led on %s", self)
        elif self._port_subscription_mode == CDS_MODE_COUNT_2INCH:
            count = unpack("<L", data[4:8])[0]  # is it all 4 bytes or just 2?
            self._notify_subscribers(count)
        elif self._port_subscription_mode == CDS_MODE_STREAM_3_VALUES:
            # TODO: understand better meaning of these 3 values
            val1 = unpack("<H", data[4:6])[0]
            val2 = unpack("<H", data[6:8])[0]
            val3 = unpack("<H", data[8:10])[0]
            self._notify_subscribers(val1, val2, val3)
        elif self._port_subscription_mode == CDS_MODE_LUMINOSITY:
            luminosity = unpack("<H", data[4:6])[0] / 1023.0
            self._notify_subscribers(luminosity)
        else:  # TODO: support whatever we forgot
            log.debug("Unhandled data in mode %s: %s", self._port_subscription_mode, str2hex(data))


class Battery(Peripheral):
    def __init__(self, parent, port):
        super(Battery, self).__init__(parent, port)
        self.last_value = None

    def subscribe(self, callback, mode=0, granularity=1):
        super(Battery, self).subscribe(callback, mode, granularity)

    # we know only voltage subscription from it. is it really battery or just onboard voltage?
    # device has turned off on 1b0e000600453ba800 - 168d
    # moderate 9v ~= 3840
    # good 7.5v ~= 3892
    # liion 5v ~= 2100
    def handle_port_data(self, data):
        self.last_value = unpack("<h", data[4:6])[0]
        self._notify_subscribers(self.last_value)


class Button(Peripheral):
    """
    It's not really a peripheral, we use MSG_DEVICE_INFO commands to interact with it
    """

    def __init__(self, parent):
        super(Button, self).__init__(parent, 0)

    def subscribe(self, callback, mode=None, granularity=1):
        cmd = pack("<B", PACKET_VER) + pack("<B", MSG_DEVICE_INFO) + b'\x02\x02'
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, pack("<B", len(cmd) + 1) + cmd)
        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._subscribers:
            cmd = pack("<B", PACKET_VER) + pack("<B", MSG_DEVICE_INFO) + b'\x02\x03'
            self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, pack("<B", len(cmd) + 1) + cmd)

    def handle_port_data(self, data):
        self._notify_subscribers(bool(unpack("<B", data[5:6])[0]))
