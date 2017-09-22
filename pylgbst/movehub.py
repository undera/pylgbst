import logging
import time
from struct import pack

from pylgbst.comms import BLEConnection, str2hex, get_byte
from pylgbst.constants import *
from pylgbst.peripherals import Button, EncodedMotor, ColorDistanceSensor, LED, TiltSensor, Voltage, Peripheral, \
    Amperage

log = logging.getLogger('movehub')

ENABLE_NOTIFICATIONS_HANDLE = 0x000f
ENABLE_NOTIFICATIONS_VALUE = b'\x01\x00'


class MoveHub(object):
    """
    :type connection: pylgbst.comms.Connection
    :type devices: dict[int,Peripheral]
    :type led: LED
    :type tilt_sensor: TiltSensor
    :type button: Button
    :type amperage: Voltage
    :type color_distance_sensor: pylgbst.peripherals.ColorDistanceSensor
    :type motor_external: EncodedMotor
    :type port_C: Peripheral
    :type port_D: Peripheral
    :type motor_A: EncodedMotor
    :type motor_B: EncodedMotor
    :type motor_AB: EncodedMotor
    """

    def __init__(self, connection=None):
        if not connection:
            connection = BLEConnection()

        self.connection = connection
        self.devices = {}

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

        self.connection.set_notify_handler(self._notify)

        self._wait_for_devices()

    def _wait_for_devices(self):
        self.connection.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

        builtin_devices = ()
        for num in range(0, 60):
            builtin_devices = (self.led, self.motor_A, self.motor_B,
                               self.motor_AB, self.tilt_sensor, self.button, self.amperage, self.voltage)
            if None not in builtin_devices:
                return
            log.debug("Waiting for builtin devices to appear: %s", builtin_devices)
            time.sleep(1)
        log.warning("Got only these devices: %s", builtin_devices)
        raise RuntimeError("Failed to obtain all builtin devices")

    def _notify(self, handle, data):
        orig = data

        if handle != MOVE_HUB_HARDWARE_HANDLE:
            log.warning("Unsupported notification handle: 0x%s", handle)
            return

        data = data[3:]
        log.debug("Notification on %s: %s", handle, str2hex(orig))

        msg_type = get_byte(data, 2)

        if msg_type == MSG_PORT_INFO:
            self._handle_port_info(data)
        elif msg_type == MSG_PORT_STATUS:
            self._handle_port_status(data)
        elif msg_type == MSG_SENSOR_DATA:
            self._handle_sensor_data(data)
        elif msg_type == MSG_SENSOR_SUBSCRIBE_ACK:
            port = get_byte(data, 3)
            log.debug("Sensor subscribe ack on port %s", PORTS[port])
            self.devices[port].finished()
        elif msg_type == MSG_PORT_CMD_ERROR:
            log.warning("Command error: %s", str2hex(data[3:]))
        elif msg_type == MSG_DEVICE_SHUTDOWN:
            log.warning("Device reported shutdown: %s", str2hex(data))
            raise KeyboardInterrupt("Device shutdown")
        elif msg_type == MSG_DEVICE_INFO:
            self._handle_device_info(data)
        else:
            log.warning("Unhandled msg type 0x%x: %s", msg_type, str2hex(orig))

    def _handle_device_info(self, data):
        if get_byte(data, 3) == 2:
            self.button.handle_port_data(data)
        else:
            log.warning("Unhandled device info: %s", str2hex(data))

    def _handle_sensor_data(self, data):
        port = get_byte(data, 3)
        if port not in self.devices:
            log.warning("Notification on port with no device: %s", PORTS[port])
            return

        device = self.devices[port]
        device.queue_port_data(data)

    def _handle_port_status(self, data):
        port = get_byte(data, 3)
        status = get_byte(data, 4)

        if status == STATUS_STARTED:
            self.devices[port].started()
        elif status == STATUS_FINISHED:
            self.devices[port].finished()
        elif status == STATUS_CONFLICT:
            log.warning("Command conflict on port %s", PORTS[port])
        else:
            log.warning("Unhandled status value: 0x%x", status)

    def _handle_port_info(self, data):
        port = get_byte(data, 3)
        dev_type = get_byte(data, 5)

        if port in PORTS and dev_type in DEVICE_TYPES:
            log.debug("Device %s at port %s", DEVICE_TYPES[dev_type], PORTS[port])
        else:
            log.warning("Device 0x%x at port 0x%x", dev_type, port)

        if dev_type == DEV_MOTOR:
            self.devices[port] = EncodedMotor(self, port)
        elif dev_type == DEV_IMOTOR:
            self.motor_external = EncodedMotor(self, port)
            self.devices[port] = self.motor_external
        elif dev_type == DEV_DCS:
            self.color_distance_sensor = ColorDistanceSensor(self, port)
            self.devices[port] = self.color_distance_sensor
        elif dev_type == DEV_LED:
            self.devices[port] = LED(self, port)
        elif dev_type == DEV_TILT_SENSOR:
            self.devices[port] = TiltSensor(self, port)
        elif dev_type == DEV_AMPERAGE:
            self.devices[port] = Amperage(self, port)
        elif dev_type == DEV_VOLTAGE:
            self.devices[port] = Voltage(self, port)
        else:
            log.debug("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)
            self.devices[port] = Peripheral(self, port)

        if port == PORT_A:
            self.motor_A = self.devices[port]
        elif port == PORT_B:
            self.motor_B = self.devices[port]
        elif port == PORT_AB:
            self.motor_AB = self.devices[port]
        elif port == PORT_C:
            self.port_C = self.devices[port]
        elif port == PORT_D:
            self.port_D = self.devices[port]
        elif port == PORT_LED:
            self.led = self.devices[port]
        elif port == PORT_TILT_SENSOR:
            self.tilt_sensor = self.devices[port]
        elif port == PORT_AMPERAGE:
            self.amperage = self.devices[port]
        elif port == PORT_VOLTAGE:
            self.voltage = self.devices[port]
        else:
            log.debug("Unhandled port: %s", PORTS[port])

    def shutdown(self):
        cmd = pack("<B", PACKET_VER) + pack("<B", MSG_DEVICE_SHUTDOWN)
        self.connection.write(MOVE_HUB_HARDWARE_HANDLE, pack("<B", len(cmd) + 1) + cmd)
