import logging
import math
import time
import traceback
from struct import pack, unpack
from threading import Thread

from pylgbst.constants import PORTS, MSG_SENSOR_SUBSCRIBE, COLOR_NONE, COLOR_BLACK, COLORS, MSG_SET_PORT_VAL, PORT_AB, \
    MSG_DEVICE_INFO, INFO_BUTTON_STATE, INFO_ACTION_SUBSCRIBE, INFO_ACTION_UNSUBSCRIBE
from pylgbst.utilities import queue, str2hex, usbyte, ushort

log = logging.getLogger('peripherals')


class Peripheral(object):
    """
    :type parent: MoveHub
    :type _incoming_port_data: queue.Queue
    """

    def __init__(self, parent, port):
        """
        :type parent: pylgbst.movehub.MoveHub
        :type port: int
        """
        super(Peripheral, self).__init__()
        self.parent = parent
        self.port = port
        self._working = False
        self._subscribers = set()
        self._port_subscription_mode = None
        # TODO: maybe max queue len of 2?
        self._incoming_port_data = queue.Queue(1)  # limit 1 means we drop data if we can't handle it fast enough
        thr = Thread(target=self._queue_reader)
        thr.setDaemon(True)
        thr.setName("Port data queue: %s" % self)
        thr.start()

    def __repr__(self):
        return "%s on port %s" % (self.__class__.__name__, PORTS[self.port] if self.port in PORTS else self.port)

    def _write_to_hub(self, msg_type, params):
        cmd = pack("<B", self.port) + params
        self.parent.send(msg_type, cmd)

    def _port_subscribe(self, mode, granularity, enable):
        params = pack("<B", mode)
        params += pack("<H", granularity)
        params += b'\x00\x00'  # maybe also bytes of granularity
        params += pack("<?", bool(enable))
        self._write_to_hub(MSG_SENSOR_SUBSCRIBE, params)

    def started(self):
        log.debug("Peripheral Started: %s", self)
        self._working = True

    def finished(self):
        log.debug("Peripheral Finished: %s", self)
        self._working = False

    def in_progress(self):
        return bool(self._working)

    def subscribe(self, callback, mode, granularity=1, async=False):
        self._port_subscription_mode = mode
        self.started()
        self._port_subscribe(self._port_subscription_mode, granularity, True)

        self._wait_sync(async)  # having async=True leads to stuck notifications

        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None, async=False):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if self._port_subscription_mode is None:
            log.warning("Attempt to unsubscribe while never subscribed: %s", self)
        elif not self._subscribers:
            self.started()
            self._port_subscribe(self._port_subscription_mode, 0, False)
            self._wait_sync(async)
            self._port_subscription_mode = None

    def _notify_subscribers(self, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)

    def queue_port_data(self, data):
        try:
            self._incoming_port_data.put_nowait(data)
        except queue.Full:
            log.debug("Dropped port data: %s", data)

    def handle_port_data(self, data):
        log.warning("Unhandled device notification for %s: %s", self, str2hex(data[4:]))
        self._notify_subscribers(data[4:])

    def _queue_reader(self):
        while True:
            data = self._incoming_port_data.get()
            try:
                self.handle_port_data(data)
            except BaseException:
                log.warning("%s", traceback.format_exc())
                log.warning("Failed to handle port data by %s: %s", self, str2hex(data))

    def _wait_sync(self, async):
        if not async:
            log.debug("Waiting for sync command work to finish...")
            while self.in_progress():
                time.sleep(0.001)
            log.debug("Command has finished.")


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

    def subscribe(self, callback, mode=None, granularity=None, async=False):
        self._subscribers.add(callback)

    def unsubscribe(self, callback=None, async=False):
        if callback in self._subscribers:
            self._subscribers.remove(callback)


class EncodedMotor(Peripheral):
    TRAILER = b'\x64\x7f\x03'  # NOTE: \x64 is 100, might mean something; also trailer might be a sequence terminator
    # TODO: investigate sequence behavior, seen with zero values passed to angled mode
    # trailer is not required for all movement types
    MOVEMENT_TYPE = 0x11

    CONSTANT_SINGLE = 0x01
    CONSTANT_GROUP = 0x02
    SOME_SINGLE = 0x07
    SOME_GROUP = 0x08
    TIMED_SINGLE = 0x09
    TIMED_GROUP = 0x0A
    ANGLED_SINGLE = 0x0B
    ANGLED_GROUP = 0x0C

    # MOTORS
    SENSOR_SOMETHING1 = 0x00  # TODO: understand it
    SENSOR_SPEED = 0x01
    SENSOR_ANGLE = 0x02

    def _speed_abs(self, relative):
        if relative < -1:
            log.warning("Speed cannot be less than -1")
            relative = -1

        if relative > 1:
            log.warning("Speed cannot be more than 1")
            relative = 1

        absolute = math.ceil(relative * 100)  # scale of 100 is proven by experiments
        return int(absolute)

    def _wrap_and_write(self, mtype, params, speed_primary, speed_secondary):
        if self.port == PORT_AB:
            mtype += 1  # de-facto rule

        abs_primary = self._speed_abs(speed_primary)
        abs_secondary = self._speed_abs(speed_secondary)

        if mtype == self.ANGLED_GROUP and (not abs_secondary or not abs_primary):
            raise ValueError("Cannot have zero speed in double angled mode")  # otherwise it gets nuts

        params = pack("<B", self.MOVEMENT_TYPE) + pack("<B", mtype) + params

        params += pack("<b", abs_primary)
        if self.port == PORT_AB:
            params += pack("<b", abs_secondary)

        params += self.TRAILER

        self._write_to_hub(MSG_SET_PORT_VAL, params)

    def timed(self, seconds, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        params = pack('<H', int(seconds * 1000))

        self.started()
        self._wrap_and_write(self.TIMED_SINGLE, params, speed_primary, speed_secondary)
        self._wait_sync(async)

    def angled(self, angle, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        angle = int(round(angle))
        if angle < 0:
            angle = -angle
            speed_primary = -speed_primary
            speed_secondary = -speed_secondary

        params = pack('<I', angle)

        self.started()
        self._wrap_and_write(self.ANGLED_SINGLE, params, speed_primary, speed_secondary)
        self._wait_sync(async)

    def constant(self, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        self.started()
        self._wrap_and_write(self.CONSTANT_SINGLE, b"", speed_primary, speed_secondary)
        self._wait_sync(async)

    def __some(self, speed_primary=1, speed_secondary=None, async=False):
        if speed_secondary is None:
            speed_secondary = speed_primary

        self.started()
        self._wrap_and_write(self.SOME_SINGLE, b"", speed_primary, speed_secondary)
        self._wait_sync(async)

    def stop(self, async=False):
        self.constant(0, async=async)

    def handle_port_data(self, data):
        if self._port_subscription_mode == self.SENSOR_ANGLE:
            rotation = unpack("<l", data[4:8])[0]
            self._notify_subscribers(rotation)
        elif self._port_subscription_mode == self.SENSOR_SOMETHING1:
            # TODO: understand what it means
            rotation = usbyte(data, 4)
            self._notify_subscribers(rotation)
        elif self._port_subscription_mode == self.SENSOR_SPEED:
            rotation = unpack("<b", data[4])[0]
            self._notify_subscribers(rotation)
        else:
            log.debug("Got motor sensor data while in unexpected mode: %s", self._port_subscription_mode)

    def subscribe(self, callback, mode=SENSOR_ANGLE, granularity=1, async=False):
        super(EncodedMotor, self).subscribe(callback, mode, granularity)


class TiltSensor(Peripheral):
    MODE_2AXIS_FULL = 0x00
    MODE_2AXIS_SIMPLE = 0x01
    MODE_3AXIS_SIMPLE = 0x02
    MODE_BUMP_COUNT = 0x03
    MODE_3AXIS_FULL = 0x04

    TRI_BACK = 0x00
    TRI_UP = 0x01
    TRI_DOWN = 0x02
    TRI_LEFT = 0x03
    TRI_RIGHT = 0x04
    TRI_FRONT = 0x05

    DUO_HORIZ = 0x00
    DUO_DOWN = 0x03
    DUO_LEFT = 0x05
    DUO_RIGHT = 0x07
    DUO_UP = 0x09

    DUO_STATES = {
        DUO_HORIZ: "HORIZONTAL",
        DUO_DOWN: "DOWN",
        DUO_LEFT: "LEFT",
        DUO_RIGHT: "RIGHT",
        DUO_UP: "UP",
    }

    TRI_STATES = {
        TRI_BACK: "BACK",
        TRI_UP: "UP",
        TRI_DOWN: "DOWN",
        TRI_LEFT: "LEFT",
        TRI_RIGHT: "RIGHT",
        TRI_FRONT: "FRONT",
    }

    def subscribe(self, callback, mode=MODE_3AXIS_SIMPLE, granularity=1, async=False):
        super(TiltSensor, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, data):
        if self._port_subscription_mode == self.MODE_3AXIS_SIMPLE:
            state = usbyte(data, 4)
            self._notify_subscribers(state)
        elif self._port_subscription_mode == self.MODE_2AXIS_SIMPLE:
            state = usbyte(data, 4)
            self._notify_subscribers(state)
        elif self._port_subscription_mode == self.MODE_BUMP_COUNT:
            bump_count = ushort(data, 4)
            self._notify_subscribers(bump_count)
        elif self._port_subscription_mode == self.MODE_2AXIS_FULL:
            roll = self._byte2deg(usbyte(data, 4))
            pitch = self._byte2deg(usbyte(data, 5))
            self._notify_subscribers(roll, pitch)
        elif self._port_subscription_mode == self.MODE_3AXIS_FULL:
            roll = self._byte2deg(usbyte(data, 4))
            pitch = self._byte2deg(usbyte(data, 5))
            yaw = self._byte2deg(usbyte(data, 6))  # did I get the order right?
            self._notify_subscribers(roll, pitch, yaw)
        else:
            log.debug("Got tilt sensor data while in unexpected mode: %s", self._port_subscription_mode)

    def _byte2deg(self, val):
        if val > 90:
            return val - 256
        else:
            return val


class ColorDistanceSensor(Peripheral):
    COLOR_ONLY = 0x00
    DISTANCE_INCHES = 0x01
    COUNT_2INCH = 0x02
    DISTANCE_HOW_CLOSE = 0x03
    DISTANCE_SUBINCH_HOW_CLOSE = 0x04
    OFF1 = 0x05
    STREAM_3_VALUES = 0x06
    OFF2 = 0x07
    COLOR_DISTANCE_FLOAT = 0x08
    LUMINOSITY = 0x09
    SOME_20BYTES = 0x0a  # TODO: understand it

    def __init__(self, parent, port):
        super(ColorDistanceSensor, self).__init__(parent, port)

    def subscribe(self, callback, mode=COLOR_DISTANCE_FLOAT, granularity=1, async=False):
        super(ColorDistanceSensor, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, data):
        if self._port_subscription_mode == self.COLOR_DISTANCE_FLOAT:
            color = usbyte(data, 4)
            distance = usbyte(data, 5)
            partial = usbyte(data, 7)
            if partial:
                distance += 1.0 / partial
            self._notify_subscribers(color, float(distance))
        elif self._port_subscription_mode == self.COLOR_ONLY:
            color = usbyte(data, 4)
            self._notify_subscribers(color)
        elif self._port_subscription_mode == self.DISTANCE_INCHES:
            distance = usbyte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.DISTANCE_HOW_CLOSE:
            distance = usbyte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.DISTANCE_SUBINCH_HOW_CLOSE:
            distance = usbyte(data, 4)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.OFF1 or self._port_subscription_mode == self.OFF2:
            log.info("Turned off led on %s", self)
        elif self._port_subscription_mode == self.COUNT_2INCH:
            count = unpack("<L", data[4:8])[0]  # is it all 4 bytes or just 2?
            self._notify_subscribers(count)
        elif self._port_subscription_mode == self.STREAM_3_VALUES:
            # TODO: understand better meaning of these 3 values
            val1 = ushort(data, 4)
            val2 = ushort(data, 6)
            val3 = ushort(data, 8)
            self._notify_subscribers(val1, val2, val3)
        elif self._port_subscription_mode == self.LUMINOSITY:
            luminosity = ushort(data, 4) / 1023.0
            self._notify_subscribers(luminosity)
        else:  # TODO: support whatever we forgot
            log.debug("Unhandled data in mode %s: %s", self._port_subscription_mode, str2hex(data))


class Voltage(Peripheral):
    MODE1 = 0x00  # give less frequent notifications
    MODE2 = 0x01  # give more frequent notifications, maybe different value (cpu vs board?)

    def __init__(self, parent, port):
        super(Voltage, self).__init__(parent, port)
        self.last_value = None

    def subscribe(self, callback, mode=MODE1, granularity=1, async=False):
        super(Voltage, self).subscribe(callback, mode, granularity)

    # we know only voltage subscription from it. is it really battery or just onboard voltage?
    # device has turned off on 1b0e00060045 3c 0803 / 1b0e000600453c 0703
    # moderate 9v ~= 3840
    # good 7.5v ~= 3892
    # liion 5v ~= 2100
    def handle_port_data(self, data):
        val = ushort(data, 4)
        self.last_value = val / 4096.0
        if self.last_value < 0.2:
            log.warning("Battery low! %s%%", int(100 * self.last_value))
        self._notify_subscribers(self.last_value)


class Amperage(Peripheral):
    MODE1 = 0x00  # give less frequent notifications
    MODE2 = 0x01  # give more frequent notifications, maybe different value (cpu vs board?)

    def __init__(self, parent, port):
        super(Amperage, self).__init__(parent, port)
        self.last_value = None

    def subscribe(self, callback, mode=MODE1, granularity=1, async=False):
        super(Amperage, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, data):
        val = ushort(data, 4)
        self.last_value = val / 4096.0
        self._notify_subscribers(self.last_value)


class Button(Peripheral):
    """
    It's not really a peripheral, we use MSG_DEVICE_INFO commands to interact with it
    """

    def __init__(self, parent):
        super(Button, self).__init__(parent, 0)  # fake port 0

    def subscribe(self, callback, mode=None, granularity=1, async=False):
        self.started()
        self.parent.send(MSG_DEVICE_INFO, pack('<B', INFO_BUTTON_STATE) + pack('<B', INFO_ACTION_SUBSCRIBE))
        self._wait_sync(async)

        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None, async=False):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._subscribers:
            self.parent.send(MSG_DEVICE_INFO, pack('<B', INFO_BUTTON_STATE) + pack('<B', INFO_ACTION_UNSUBSCRIBE))
            # FIXME: will this require sync wait?

    def handle_port_data(self, data):
        param = usbyte(data, 5)
        if self.in_progress():
            self.finished()
        self._notify_subscribers(bool(param))
