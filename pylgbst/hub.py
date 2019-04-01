import time

from pylgbst import get_connection_auto
from pylgbst.messages import *
from pylgbst.peripherals import Button, EncodedMotor, ColorDistanceSensor, LED, TiltSensor, Voltage, Peripheral, \
    Current
from pylgbst.utilities import str2hex, usbyte

log = logging.getLogger('hub')


class Hub(object):
    """
    :type connection: pylgbst.comms.Connection
    :type peripherals: dict[int,Peripheral]
    """
    HUB_HARDWARE_HANDLE = 0x0E

    def __init__(self, connection=None):
        if not connection:
            connection = get_connection_auto()
        self.connection = connection
        self.connection.set_notify_handler(self._notify)
        self.connection.enable_notifications()
        self.peripherals = {}

    def __del__(self):
        if self.connection and self.connection.is_alive():
            self.connection.disconnect()

    def send(self, msg):
        """
        :type msg: pylgbst.messages.Message
        """
        self.connection.write(self.HUB_HARDWARE_HANDLE, msg)

    def _notify(self, handle, data):
        orig = data

        if handle != self.HUB_HARDWARE_HANDLE:
            log.warning("Unsupported notification handle: 0x%s", handle)
            return

        log.debug("Notification on %s: %s", handle, str2hex(orig))

        msg = self._get_upstream_msg(data)

        if isinstance(msg, MsgHubAttachedIO):
            if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
                self.peripherals[msg.port].finished()
                self.peripherals.pop(msg.port)
            else:
                self.peripherals[msg.port] = msg.create_peripheral(self)
        else:
            log.warning("Unhandled message: %s", msg)

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

    def disconnect(self):
        self.send(MsgHubActions(MsgHubActions.DISCONNECT))

    def switch_off(self):
        self.send(MsgHubActions(MsgHubActions.SWITCH_OFF))


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

        self._wait_for_devices()
        self._report_status()

    def _wait_for_devices(self):
        builtin_devices = ()
        for num in range(0, 60):
            builtin_devices = (self.led, self.motor_A, self.motor_B,
                               self.motor_AB, self.tilt_sensor, self.button, self.amperage, self.voltage)
            if None not in builtin_devices:
                log.debug("All devices are present")
                return
            log.debug("Waiting for builtin devices to appear: %s", builtin_devices)
            time.sleep(0.05)
        log.warning("Got only these devices: %s", builtin_devices)
        raise RuntimeError("Failed to obtain all builtin devices")

    def _notify(self, handle, data):
        orig = data

        if handle != MOVE_HUB_HARDWARE_HANDLE:
            log.warning("Unsupported notification handle: 0x%s", handle)
            return

        log.debug("Notification on %s: %s", handle, str2hex(orig))

        msg_type = usbyte(data, 2)

        if msg_type == MSG_PORT_INFO:
            self._handle_port_info(data)
        elif msg_type == MSG_PORT_STATUS:
            self._handle_port_status(data)
        elif msg_type == MSG_SENSOR_DATA:
            self._handle_sensor_data(data)
        elif msg_type == MSG_SENSOR_SUBSCRIBE_ACK:
            port = usbyte(data, 3)
            log.debug("Sensor subscribe ack on port %s", PORTS[port])
            self.devices[port].finished()
        elif msg_type == MSG_PORT_CMD_ERROR:
            log.warning("Command error: %s", str2hex(data[3:]))
            port = usbyte(data, 3)
            self.devices[port].finished()
        elif msg_type == MSG_DEVICE_SHUTDOWN:
            log.warning("Device reported shutdown: %s", str2hex(data))
            raise KeyboardInterrupt("Device shutdown")
        elif msg_type == MSG_DEVICE_INFO:
            self._handle_device_info(data)
        else:
            log.warning("Unhandled msg type 0x%x: %s", msg_type, str2hex(orig))

    def _handle_device_info(self, data):
        kind = usbyte(data, 3)
        if kind == 2:
            self.button.handle_port_data(data)

        if usbyte(data, 4) == 0x06:
            self.info[kind] = data[5:]
        else:
            log.warning("Unhandled device info: %s", str2hex(data))

    def _handle_sensor_data(self, data):
        port = usbyte(data, 3)
        if port not in self.devices:
            log.warning("Notification on port with no device: %s", PORTS[port])
            return

        device = self.devices[port]
        device.queue_port_data(data)

    def _handle_port_status(self, data):
        port = usbyte(data, 3)
        status = usbyte(data, 4)

        if status == STATUS_STARTED:
            self.devices[port].started()
        elif status == STATUS_FINISHED:
            self.devices[port].finished()
        elif status == STATUS_CONFLICT:
            log.warning("Command conflict on port %s", PORTS[port])
            self.devices[port].finished()
        elif status == STATUS_INPROGRESS:
            log.warning("Another command is in progress on port %s", PORTS[port])
            self.devices[port].finished()
        elif status == STATUS_INTERRUPTED:
            log.warning("Command interrupted on port %s", PORTS[port])
            self.devices[port].finished()
        else:
            log.warning("Unhandled status value: 0x%x on port %s", status, PORTS[port])

    def _update_field(self, port):
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
        else:
            log.warning("Unhandled port: 0x%x", port)

    def _report_status(self):
        # TODO: add firmware version
        log.info("%s by %s", self.info_get(INFO_DEVICE_NAME), self.info_get(INFO_MANUFACTURER))

        self.__voltage = 0

        def on_voltage(value):
            self.__voltage = value

        self.voltage.subscribe(on_voltage, granularity=0)
        while not self.__voltage:
            time.sleep(0.05)
        self.voltage.unsubscribe(on_voltage)
        log.info("Voltage: %d%%", self.__voltage * 100)

    def info_get(self, info_type):
        self.info[info_type] = None
        self.send(MSG_DEVICE_INFO, pack("<B", info_type) + pack("<B", INFO_ACTION_GET))
        while self.info[info_type] is None:  # FIXME: will hang forever on error
            time.sleep(0.05)

        return self.info[info_type]
