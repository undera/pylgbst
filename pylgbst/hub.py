import time

from pylgbst import get_connection_auto
from pylgbst.messages import *
from pylgbst.peripherals import *
from pylgbst.utilities import str2hex, usbyte, ushort
from pylgbst.utilities import queue

log = logging.getLogger('hub')


class Hub(object):
    """
    :type connection: pylgbst.comms.Connection
    :type peripherals: dict[int,Peripheral]
    """
    HUB_HARDWARE_HANDLE = 0x0E

    def __init__(self, connection=None):
        self._msg_handlers = []
        self.peripherals = {}
        self._sync_request = None
        self._sync_replies = queue.Queue(1)

        self.add_message_handler(MsgHubAttachedIO, self._handle_device_change)
        self.add_message_handler(MsgPortValueSingle, self._handle_sensor_data)
        self.add_message_handler(MsgPortValueCombined, self._handle_sensor_data)
        self.add_message_handler(MsgGenericError, self._handle_error)
        self.add_message_handler(MsgHubAction, self._handle_action)

        if not connection:
            connection = get_connection_auto()
        self.connection = connection
        self.connection.set_notify_handler(self._notify)
        self.connection.enable_notifications()

    def __del__(self):
        if self.connection and self.connection.is_alive():
            self.connection.disconnect()

    def add_message_handler(self, classname, callback):
        self._msg_handlers.append((classname, callback))

    def send(self, msg):
        """
        :type msg: pylgbst.messages.DownstreamMsg
        """
        log.debug("Send message: %r", msg)
        self.connection.write(self.HUB_HARDWARE_HANDLE, msg.bytes())
        if msg.needs_reply:
            assert not self._sync_request, "Pending request %r while trying to put %r" % (self._sync_request, msg)
            self._sync_request = msg
            log.debug("Waiting for sync reply to %r...", msg)
            return self._sync_replies.get()
        else:
            return None

    def _notify(self, handle, data):
        log.debug("Notification on %s: %s", handle, str2hex(data))

        msg = self._get_upstream_msg(data)

        if self._sync_request:
            if self._sync_request.is_reply(msg):
                log.debug("Found matching upstream msg: %r", msg)
                self._sync_replies.put(msg)
                self._sync_request = None

        found = False
        for msg_class, handler in self._msg_handlers:
            if isinstance(msg, msg_class):
                found = True
                handler(msg)

        if not found:
            log.debug("Did not find handler for message: %r", msg)

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

    def _handle_error(self, msg):
        log.warning("Command error: %s", msg.message())
        self._sync_request = DownstreamMsg()

    def _handle_action(self, msg):
        """
        :type msg: MsgHubAction
        """
        if msg.action == MsgHubAction.UPSTREAM_DISCONNECT:
            log.warning("Hub disconnects")
            self.connection.disconnect()
        elif msg.action == MsgHubAction.UPSTREAM_SHUTDOWN:
            log.warning("Hub switches off")
            self.connection.disconnect()

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
            self.peripherals[port] = LEDRGB(self, port)
        elif dev_type in (msg.DEV_TILT_EXTERNAL, msg.DEV_TILT_INTERNAL):
            self.peripherals[port] = TiltSensor(self, port)
        elif dev_type == msg.DEV_CURRENT:
            self.peripherals[port] = Current(self, port)
        elif dev_type == msg.DEV_VOLTAGE:
            self.peripherals[port] = Voltage(self, port)
        else:
            # TODO: support more types of peripherals from
            # https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#io-type-id
            log.warning("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)
            self.peripherals[port] = Peripheral(self, port)

        log.info("Attached peripheral: %s", self.peripherals[msg.port])

        if msg.event == msg.EVENT_ATTACHED:
            hw_revision = reversed([usbyte(msg.payload, x) for x in range(2, 6)])
            sw_revision = reversed([usbyte(msg.payload, x) for x in range(6, 10)])
            # what to do with this info? it's useless, I guess
            del hw_revision, sw_revision
        elif msg.event == msg.EVENT_ATTACHED_VIRTUAL:
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
    Class implementing Lego Boost's MoveHub specifics

    :type led: LEDRGB
    :type tilt_sensor: TiltSensor
    :type button: Button
    :type current: Current
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
    PORT_CURRENT = 0x3B
    PORT_VOLTAGE = 0x3C

    PORTS = {
        PORT_A: "A",
        PORT_B: "B",
        PORT_AB: "AB",
        PORT_C: "C",
        PORT_D: "D",
        PORT_LED: "LED",
        PORT_TILT_SENSOR: "TILT_SENSOR",
        PORT_CURRENT: "AMPERAGE",
        PORT_VOLTAGE: "VOLTAGE",
    }

    # noinspection PyTypeChecker
    def __init__(self, connection=None):
        super(MoveHub, self).__init__(connection)
        self.info = {}

        # shorthand fields
        self.button = Button(self)
        self.led = None
        self.current = None
        self.voltage = None
        self.motor_A = None
        self.motor_B = None
        self.motor_AB = None
        self.color_distance_sensor = None
        self.tilt_sensor = None
        self.motor_external = None
        self.port_C = None
        self.port_D = None

        self._wait_for_devices()
        self._report_status()

    def _wait_for_devices(self, get_dev_set=None):
        if not get_dev_set:
            get_dev_set = lambda: (self.motor_A, self.motor_B, self.motor_AB, self.led, self.tilt_sensor,
                                   self.current, self.voltage)
        for num in range(0, 60):
            devices = get_dev_set()
            if all(devices):
                log.debug("All devices are present: %s", devices)
                return
            log.debug("Waiting for builtin devices to appear: %s", devices)
            time.sleep(0.1)
        log.warning("Got only these devices: %s", get_dev_set())

    def _report_status(self):
        # maybe add firmware version
        name = self.send(MsgHubProperties(MsgHubProperties.ADVERTISE_NAME, MsgHubProperties.UPD_REQUEST))
        mac = self.send(MsgHubProperties(MsgHubProperties.PRIMARY_MAC, MsgHubProperties.UPD_REQUEST))
        log.info("%s on %s", name.payload, str2hex(mac.payload))

        voltage = self.send(MsgHubProperties(MsgHubProperties.VOLTAGE_PERC, MsgHubProperties.UPD_REQUEST))
        assert isinstance(voltage, MsgHubProperties)
        log.info("Voltage: %s%%", usbyte(voltage.parameters, 0))

        voltage = self.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        assert isinstance(voltage, MsgHubAlert)
        if not voltage.is_ok():
            log.warning("Low voltage, check power source (maybe replace battery)")

    # noinspection PyTypeChecker
    def _handle_device_change(self, msg):
        super(MoveHub, self)._handle_device_change(msg)
        if isinstance(msg, MsgHubAttachedIO) and msg.event != MsgHubAttachedIO.EVENT_DETACHED:
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
            elif port == self.PORT_CURRENT:
                self.current = self.peripherals[port]
            elif port == self.PORT_VOLTAGE:
                self.voltage = self.peripherals[port]

            if type(self.peripherals[port]) == ColorDistanceSensor:
                self.color_distance_sensor = self.peripherals[port]
            elif type(self.peripherals[port]) == EncodedMotor and port not in (self.PORT_A, self.PORT_B, self.PORT_AB):
                self.motor_external = self.peripherals[port]
