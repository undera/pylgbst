import logging
import math
import traceback
from struct import pack, unpack
from threading import Thread

from pylgbst.messages import MsgHubProperties, MsgPortOutput, MsgPortInputFmtSetupSingle, MsgPortInfoRequest
from pylgbst.utilities import queue, str2hex, usbyte, ushort

log = logging.getLogger('peripherals')

# COLORS
COLOR_BLACK = 0x00
COLOR_PINK = 0x01
COLOR_PURPLE = 0x02
COLOR_BLUE = 0x03
COLOR_LIGHTBLUE = 0x04
COLOR_CYAN = 0x05
COLOR_GREEN = 0x06
COLOR_YELLOW = 0x07
COLOR_ORANGE = 0x09
COLOR_RED = 0x09
COLOR_WHITE = 0x0a
COLOR_NONE = 0xFF
COLORS = {
    COLOR_BLACK: "BLACK",
    COLOR_PINK: "PINK",
    COLOR_PURPLE: "PURPLE",
    COLOR_BLUE: "BLUE",
    COLOR_LIGHTBLUE: "LIGHTBLUE",
    COLOR_CYAN: "CYAN",
    COLOR_GREEN: "GREEN",
    COLOR_YELLOW: "YELLOW",
    COLOR_ORANGE: "ORANGE",
    COLOR_RED: "RED",
    COLOR_WHITE: "WHITE",
    COLOR_NONE: "NONE"
}


class Peripheral(object):
    """
    :type parent: pylgbst.hub.Hub
    :type _incoming_port_data: queue.Queue
    """

    def __init__(self, parent, port):
        """
        :type parent: pylgbst.hub.Hub
        :type port: int
        """
        super(Peripheral, self).__init__()
        self.do_buffer = False
        self.virtual_ports = ()
        self.hub = parent
        self.port = port
        self.use_command_buffering = False
        self._subscribers = set()
        self._port_subscription_mode = None
        # TODO: maybe max queue len of 2?
        self._incoming_port_data = queue.Queue(1)  # limit 1 means we drop data if we can't handle it fast enough
        thr = Thread(target=self._queue_reader)
        thr.setDaemon(True)
        thr.setName("Port data queue: %s" % self)
        thr.start()

    def __repr__(self):
        msg = "%s on port 0x%x" % (self.__class__.__name__, self.port)
        if self.virtual_ports:
            msg += " (ports 0x%x and 0x%x combined)" % (self.virtual_ports[0], self.virtual_ports[1])
        return msg

    def _port_subscribe(self, mode, granularity, enable):
        msg = MsgPortInputFmtSetupSingle(self.port, mode, granularity, enable)  # TODO: combined mode?
        self.hub.send(msg)

    def _send_to_port(self, msg):
        assert type(msg) == MsgPortOutput
        msg.do_buffer = self.do_buffer
        self.hub.send(msg)

    def __get_sensor_data(self):  # TODO: implement single sensor request
        msg = MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_PORT_VALUE)
        return self.hub.send(msg)

    def subscribe(self, callback, mode, granularity=1):
        if self._port_subscription_mode and mode != self._port_subscription_mode:
            raise ValueError("Port is in active mode %s, unsubscribe first" % self._port_subscription_mode)
        self._port_subscription_mode = mode
        self._port_subscribe(self._port_subscription_mode, granularity, True)
        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if self._port_subscription_mode is None:
            log.warning("Attempt to unsubscribe while never subscribed: %s", self)
        elif not self._subscribers:
            self._port_subscribe(self._port_subscription_mode, 0, False)
            self._port_subscription_mode = None

    def _notify_subscribers(self, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber(*args, **kwargs)
        return args

    def queue_port_data(self, msg):
        try:
            self._incoming_port_data.put_nowait(msg)
        except queue.Full:
            log.debug("Dropped port data: %r", msg)

    def handle_port_data(self, msg):
        """
        :type msg: pylgbst.messages.MsgPortValueSingle
        """
        log.warning("Unhandled device notification for %s: %r", self, str2hex(msg))
        self._notify_subscribers(msg)

    def _queue_reader(self):
        while True:
            data = self._incoming_port_data.get()
            try:
                self.handle_port_data(data)
            except BaseException:
                log.warning("%s", traceback.format_exc())
                log.warning("Failed to handle port data by %s: %s", self, str2hex(data))

    def notify_feedback(self, msg):
        """
        :type msg: pylgbst.messages.MsgPortOutputFeedback
        """
        return  # FIXME
        if msg.status == STATUS_STARTED:
            self.peripherals[port].started()
        elif status == STATUS_FINISHED:
            self.peripherals[port].finished()
        elif status == STATUS_CONFLICT:
            log.warning("Command conflict on port %s", PORTS[port])
            self.peripherals[port].finished()
        elif status == STATUS_INPROGRESS:
            log.warning("Another command is in progress on port %s", PORTS[port])
            self.peripherals[port].finished()
        elif status == STATUS_INTERRUPTED:
            log.warning("Command interrupted on port %s", PORTS[port])
            self.peripherals[port].finished()
        else:
            log.warning("Unhandled status value: 0x%x on port %s", status, PORTS[port])


class LED(Peripheral):
    MODE_INDEX = 0x00
    MODE_RGB = 0x01

    def __init__(self, parent, port):
        super(LED, self).__init__(parent, port)

    def set_color_index(self, color):
        if color == COLOR_NONE:
            color = COLOR_BLACK

        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)

        payload = pack("<B", self.MODE_INDEX) + pack("<B", color)
        msg = MsgPortOutput(self.port, MsgPortOutput.WRITE_DIRECT_MODE_DATA, payload)
        self._send_to_port(msg)

    def set_color_rgb(self, red, green, blue):
        payload = pack("<B", self.MODE_RGB) + pack("<B", red) + pack("<B", green) + pack("<B", blue)
        msg = MsgPortOutput(self.port, MsgPortOutput.WRITE_DIRECT_MODE_DATA, payload)
        self._send_to_port(msg)


class Motor(Peripheral):
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
        if self.virtual_ports:
            mtype += 1  # de-facto rule

        abs_primary = self._speed_abs(speed_primary)
        abs_secondary = self._speed_abs(speed_secondary)

        if mtype == self.ANGLED_GROUP and (not abs_secondary or not abs_primary):
            raise ValueError("Cannot have zero speed in double angled mode")  # otherwise it gets nuts

        params = pack("<B", self.MOVEMENT_TYPE) + pack("<B", mtype) + params

        params += pack("<b", abs_primary)
        if self.virtual_ports:
            params += pack("<b", abs_secondary)

        params += self.TRAILER

        self._send_to_port(params)

    def timed(self, seconds, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        params = pack('<H', int(seconds * 1000))

        self._wrap_and_write(self.TIMED_SINGLE, params, speed_primary, speed_secondary)

    def angled(self, angle, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        angle = int(round(angle))
        if angle < 0:
            angle = -angle
            speed_primary = -speed_primary
            speed_secondary = -speed_secondary

        params = pack('<I', angle)

        self._wrap_and_write(self.ANGLED_SINGLE, params, speed_primary, speed_secondary)

    def constant(self, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        self._wrap_and_write(self.CONSTANT_SINGLE, b"", speed_primary, speed_secondary)

    def __some(self, speed_primary=1, speed_secondary=None):
        if speed_secondary is None:
            speed_secondary = speed_primary

        self._wrap_and_write(self.SOME_SINGLE, b"", speed_primary, speed_secondary)

    def stop(self):
        self.constant(0)


class EncodedMotor(Motor):
    # MOTORS
    SENSOR_SOMETHING1 = 0x00  # TODO: understand it
    SENSOR_SPEED = 0x01
    SENSOR_ANGLE = 0x02

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

    def subscribe(self, callback, mode=SENSOR_ANGLE, granularity=1):
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

    def subscribe(self, callback, mode=MODE_3AXIS_SIMPLE, granularity=1):
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

    def subscribe(self, callback, mode=COLOR_DISTANCE_FLOAT, granularity=1):
        super(ColorDistanceSensor, self).subscribe(callback, mode, granularity)

    def handle_port_data(self, msg):
        data = msg.payload
        if self._port_subscription_mode == self.COLOR_DISTANCE_FLOAT:
            color = usbyte(data, 0)
            distance = usbyte(data, 1)
            partial = usbyte(data, 3)
            if partial:
                distance += 1.0 / partial
            self._notify_subscribers(color, float(distance))
        elif self._port_subscription_mode == self.COLOR_ONLY:
            color = usbyte(data, 0)
            self._notify_subscribers(color)
        elif self._port_subscription_mode == self.DISTANCE_INCHES:
            distance = usbyte(data, 0)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.DISTANCE_HOW_CLOSE:
            distance = usbyte(data, 0)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.DISTANCE_SUBINCH_HOW_CLOSE:
            distance = usbyte(data, 0)
            self._notify_subscribers(distance)
        elif self._port_subscription_mode == self.OFF1 or self._port_subscription_mode == self.OFF2:
            log.info("Turned off led on %s", self)
        elif self._port_subscription_mode == self.COUNT_2INCH:
            count = unpack("<L", data[0:4])[0]  # is it all 4 bytes or just 2?
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

    def subscribe(self, callback, mode=MODE1, granularity=1):
        super(Voltage, self).subscribe(callback, mode, granularity)

    # we know only voltage subscription from it. is it really battery or just onboard voltage?
    # device has turned off on 1b0e00060045 3c 0803 / 1b0e000600453c 0703
    # moderate 9v ~= 3840
    # good 7.5v ~= 3892
    # liion 5v ~= 2100
    def handle_port_data(self, msg):
        data = msg.payload
        val = ushort(data, 0)
        self.last_value = val / 4096.0
        self._notify_subscribers(self.last_value)


class Current(Peripheral):
    MODE1 = 0x00  # give less frequent notifications
    MODE2 = 0x01  # give more frequent notifications, maybe different value (cpu vs board?)

    def __init__(self, parent, port):
        super(Current, self).__init__(parent, port)
        self.last_value = None

    def subscribe(self, callback, mode=MODE1, granularity=1):
        super(Current, self).subscribe(callback, mode, granularity)

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
        self.hub.add_message_handler(MsgHubProperties, self._props_msg)

    def subscribe(self, callback, mode=None, granularity=1):
        self.hub.send(MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_ENABLE))

        if callback:
            self._subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

        if not self._subscribers:
            self.hub.send(MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_DISABLE))

    def _props_msg(self, msg):
        """
        :type msg: MsgHubProperties
        """
        if msg.property == MsgHubProperties.BUTTON and msg.operation == MsgHubProperties.UPSTREAM_UPDATE:
            self._notify_subscribers(bool(usbyte(msg.parameters, 0)))
