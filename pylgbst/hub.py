import logging
import time

from pylgbst import get_connection_auto
from pylgbst.messages import DownstreamMsg, UPSTREAM_MSGS, MsgHubAttachedIO, MsgPortOutputFeedback, MsgPortValueSingle, \
    MsgPortValueCombined, MsgGenericError, MsgHubProperties, MsgHubAlert
from pylgbst.peripherals import Button, EncodedMotor, ColorDistanceSensor, LED, TiltSensor, Voltage, Peripheral, \
    Current, Motor
from pylgbst.utilities import str2hex, usbyte, ushort

log = logging.getLogger('hub')


class Hub(object):
    """
    :type connection: pylgbst.comms.Connection
    :type peripherals: dict[int,Peripheral]
    :type _sent_msg: pylgbst.messages.DownstreamMsg
    """
    HUB_HARDWARE_HANDLE = 0x0E

    def __init__(self, connection=None):
        self.peripherals = {}
        self._sent_msg = DownstreamMsg()

        if not connection:
            connection = get_connection_auto()
        self.connection = connection
        self.connection.set_notify_handler(self._notify)
        self.connection.enable_notifications()

    def __del__(self):
        if self.connection and self.connection.is_alive():
            self.connection.disconnect()

    def send(self, msg):
        """
        :type msg: pylgbst.messages.DownstreamMsg
        """
        self._wait_for_reply(None)

        log.debug("Send message: %r", msg)
        self.connection.write(self.HUB_HARDWARE_HANDLE, msg)
        self._sent_msg = msg

        self._wait_for_reply(msg)

        resp = self._sent_msg
        self._sent_msg = DownstreamMsg()
        return resp

    def _wait_for_reply(self, msg):
        start = time.time()
        while isinstance(self._sent_msg, DownstreamMsg) and self._sent_msg.needs_reply:
            spent = time.time() - start
            if spent > 10.0:
                log.debug("Waiting %.2f for pair message to answer %r", spent, msg)
                time.sleep(1.0)
            elif spent > 1.0:
                log.debug("Waiting %.2f for pair message to answer %r", spent, msg)
                time.sleep(0.1)
            elif spent > 0.1:
                log.debug("Waiting %.2f for pair message to answer %r", spent, msg)
                time.sleep(0.01)

    def _notify(self, handle, data):
        orig = data

        if handle != self.HUB_HARDWARE_HANDLE:
            log.warning("Unsupported notification handle: 0x%s", handle)
            return

        log.debug("Notification on %s: %s", handle, str2hex(orig))

        msg = self._get_upstream_msg(data)
        if self._sent_msg.is_reply(msg):
            log.debug("Found matching upstream msg: %r", msg)
            self._sent_msg = msg  # FIXME: weird piggyback of UpstreamMsg via field of DownstreamMsg
        elif type(self._sent_msg) != DownstreamMsg:
            log.debug("Upstream msg is not reply we need: %r", msg)

        self._handle_message(msg)

    def _get_upstream_msg(self, data):
        msg_type = usbyte(data, 2)
        msg = None
        for msg_kind in UPSTREAM_MSGS:
            if msg_type == msg_kind.TYPE:
                msg = msg_kind.decode(data)
                log.debug("Decoded message: %r", msg)
                break
        assert msg
        return msg

    def _handle_message(self, msg):
        if type(msg) == MsgHubAttachedIO:
            self._handle_device_change(msg)
        elif type(msg) == MsgPortOutputFeedback:
            self.peripherals[msg.port].notify_feedback(msg)
        elif type(msg) in (MsgPortValueSingle, MsgPortValueCombined):
            self._handle_sensor_data(msg)
        elif type(msg) == MsgGenericError:
            log.warning("Command error: %s", msg.message())
        else:
            log.warning("Unhandled message: %r", msg)

        pass
        """
        elif msg_type == MSG_SENSOR_SUBSCRIBE_ACK:
            port = usbyte(data, 3)
            log.debug("Sensor subscribe ack on port %s", PORTS[port])
            self.devices[port].finished()
        elif msg_type == MSG_DEVICE_INFO:
            self._handle_device_info(data)
        else:
            log.warning("Unhandled msg type 0x%x: %s", msg_type, str2hex(orig))
        """

    def _handle_device_change(self, msg):
        if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
            log.debug("Detaching peripheral: %s", self.peripherals[msg.port])
            self.peripherals.pop(msg.port)
            return

        assert msg.event in (msg.EVENT_ATTACHED, msg.EVENT_ATTACHED_VIRTUAL)
        port = msg.port
        dev_type = ushort(msg.payload, 0)

        if dev_type == msg.DEV_MOTOR:
            self.peripherals[port] = Motor(self, port)
        elif dev_type in (msg.DEV_MOTOR_EXTERNAL_TACHO, msg.DEV_MOTOR_INTERNAL_TACHO):
            self.peripherals[port] = EncodedMotor(self, port)
        elif dev_type == msg.DEV_VISION_SENSOR:
            self.peripherals[port] = ColorDistanceSensor(self, port)
        elif dev_type == msg.DEV_RGB_LIGHT:
            self.peripherals[port] = LED(self, port)
        elif dev_type in (msg.DEV_TILT_EXTERNAL, msg.DEV_TILT_INTERNAL):
            self.peripherals[port] = TiltSensor(self, port)
        elif dev_type == msg.DEV_CURRENT:
            self.peripherals[port] = Current(self, port)
        elif dev_type == msg.DEV_VOLTAGE:
            self.peripherals[port] = Voltage(self, port)
        # TODO: support more types of peripherals
        else:
            log.warning("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)
            self.peripherals[port] = Peripheral(self, port)

        log.info("Attached peripheral: %s", self.peripherals[msg.port])

        if msg.event == msg.EVENT_ATTACHED:
            # TODO: what to do with this info? it's useless, I guess
            hw_revision = reversed([usbyte(msg.payload, x) for x in range(2, 6)])
            sw_revision = reversed([usbyte(msg.payload, x) for x in range(6, 10)])
        elif msg.event == msg.EVENT_ATTACHED_VIRTUAL:
            # TODO: what to do with this info? pass to device?
            self.peripherals[port].virtual_ports = (usbyte(msg.payload, 2), usbyte(msg.payload, 3))

    def _handle_sensor_data(self, msg):
        assert isinstance(msg, (MsgPortValueSingle, MsgPortValueCombined))
        if msg.port not in self.peripherals:
            log.warning("Notification on port with no device: %s", msg.port)
            return

        device = self.peripherals[msg.port]
        device.queue_port_data(msg)

    def disconnect(self):
        self.send(MsgHubAction(MsgHubAction.DISCONNECT))

    def switch_off(self):
        self.send(MsgHubAction(MsgHubAction.SWITCH_OFF))


class MoveHub(Hub):
    """
    :type led: LED
    :type tilt_sensor: TiltSensor
    :type button: Button
    :type amperage: Current
    :type voltage: Voltage
    :type color_distance_sensor: pylgbst.peripherals.ColorDistanceSensor
    :type port_C: Peripheral
    :type port_D: Peripheral
    :type motor_A: EncodedMotor
    :type motor_B: EncodedMotor
    :type motor_AB: EncodedMotor
    :type motor_external: EncodedMotor
    """

    # PORTS
    PORT_C = 0x01
    PORT_D = 0x02
    PORT_LED = 0x32
    PORT_A = 0x37
    PORT_B = 0x38
    PORT_AB = 0x39
    PORT_TILT_SENSOR = 0x3A
    PORT_AMPERAGE = 0x3B
    PORT_VOLTAGE = 0x3C

    PORTS = {
        PORT_A: "A",
        PORT_B: "B",
        PORT_AB: "AB",
        PORT_C: "C",
        PORT_D: "D",
        PORT_LED: "LED",
        PORT_TILT_SENSOR: "TILT_SENSOR",
        PORT_AMPERAGE: "AMPERAGE",
        PORT_VOLTAGE: "VOLTAGE",
    }

    # noinspection PyTypeChecker
    def __init__(self, connection=None):
        super(MoveHub, self).__init__(connection)
        self.info = {}

        # shorthand fields
        self.button = Button(self)
        self.led = None
        self.amperage = None
        self.voltage = None
        self.motor_A = None
        self.motor_B = None
        self.motor_AB = None
        self.color_distance_sensor = None
        self.tilt_sensor = None
        self.motor_external = None
        self.port_C = None
        self.port_D = None

    def wait_for_devices(self):
        required_devices = ()
        for num in range(0, 60):
            required_devices = (self.motor_A, self.motor_B, self.motor_AB,
                                self.led, self.tilt_sensor,
                                self.amperage, self.voltage)
            if all(required_devices):
                log.debug("All devices are present: %s", required_devices)
                return
            log.debug("Waiting for builtin devices to appear: %s", required_devices)
            time.sleep(0.1)
        log.warning("Got only these devices: %s", required_devices)

    # noinspection PyTypeChecker
    def _handle_message(self, msg):
        super(MoveHub, self)._handle_message(msg)
        if type(msg) == MsgHubAttachedIO:
            port = msg.port
            if port == self.PORT_A:
                self.motor_A = self.peripherals[port]
            elif port == self.PORT_B:
                self.motor_B = self.peripherals[port]
            elif port == self.PORT_AB:
                self.motor_AB = self.peripherals[port]
            elif port == self.PORT_C:
                self.port_C = self.peripherals[port]
            elif port == self.PORT_D:
                self.port_D = self.peripherals[port]
            elif port == self.PORT_LED:
                self.led = self.peripherals[port]
            elif port == self.PORT_TILT_SENSOR:
                self.tilt_sensor = self.peripherals[port]
            elif port == self.PORT_AMPERAGE:
                self.amperage = self.peripherals[port]
            elif port == self.PORT_VOLTAGE:
                self.voltage = self.peripherals[port]

            if type(self.peripherals[port]) == ColorDistanceSensor:
                self.color_distance_sensor = self.peripherals[port]
            elif type(self.peripherals[port]) == EncodedMotor and port not in (self.PORT_A, self.PORT_B, self.PORT_AB):
                self.motor_external = self.peripherals[port]

    def report_status(self):
        # TODO: add firmware version
        name = self.send(MsgHubProperties(MsgHubProperties.ADVERTISE_NAME, MsgHubProperties.UPD_REQUEST))
        mac = self.send(MsgHubProperties(MsgHubProperties.HW_NETW_ID, MsgHubProperties.UPD_REQUEST))
        log.info("%s on %s", name, mac)

        voltage = self.send(MsgHubProperties(MsgHubProperties.VOLTAGE, MsgHubProperties.UPD_REQUEST))
        log.info("Voltage: %s", voltage)

        voltage = self.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        assert isinstance(voltage, MsgHubAlert)
        if not voltage.is_ok():
            log.warning("Low voltage, check power source (maybe replace battery)")
