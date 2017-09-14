from pylgbst.comms import *
from pylgbst.constants import *
from pylgbst.peripherals import *

log = logging.getLogger('movehub')


class MoveHub(object):
    """
    :type connection: pylegoboost.comms.Connection
    :type devices: dict[int,Peripheral]
    :type led: LED
    :type tilt_sensor: TiltSensor
    :type button: Button
    :type color_distance_sensor: ColorDistanceSensor
    :type external_motor: EncodedMotor
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
        self.motor_A = None
        self.motor_B = None
        self.motor_AB = None
        self.tilt_sensor = None
        self.color_distance_sensor = None
        self.external_motor = None
        self.port_C = None
        self.port_D = None

        self.connection.set_notify_handler(self._notify)

        self._wait_for_devices()

    def _wait_for_devices(self):
        self.connection.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

        builtin_devices = ()
        for num in range(0, 60):
            builtin_devices = (self.led, self.motor_A, self.motor_B, self.motor_AB, self.tilt_sensor, self.button)
            if None not in builtin_devices:
                return
            log.debug("Waiting for builtin devices to appear: %s", builtin_devices)
            time.sleep(1)
        log.warning("Got only these devices: %s", builtin_devices)
        raise RuntimeError("Failed to obtain all builtin devices")

    def get_name(self):
        # note: reading this too fast makes it hang
        return self.connection.read(DEVICE_NAME)

    def _notify(self, handle, data):
        """
        Using https://github.com/JorgePe/BOOSTreveng/blob/master/Notifications.md
        """
        orig = data

        if handle == MOVE_HUB_HARDWARE_HANDLE:
            data = data[3:]
            log.debug("Notification on %s: %s", handle, str2hex(orig))

            msg_type = get_byte(data, 2)

            if msg_type == MSG_PORT_INFO:
                self._handle_port_info(data)
            elif msg_type == MSG_PORT_STATUS:
                self._handle_port_status(data)
            elif msg_type == MSG_SENSOR_DATA:
                self._handle_sensor_data(data)
            else:
                log.warning("Unhandled msg type 0x%x: %s", msg_type, str2hex(orig))
        else:
            log.warning("Unsupported notification handle: 0x%s", handle)

    def _handle_sensor_data(self, data):
        port = get_byte(data, 3)
        sensor = self.devices[port]
        if isinstance(sensor, TiltSensor):
            sensor.notify_subscribers()

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

        if dev_type == TYPE_MOTOR:
            self.devices[port] = EncodedMotor(self, port)
        elif dev_type == TYPE_IMOTOR:
            self.devices[port] = EncodedMotor(self, port)
            self.external_motor = self.devices[port]
        elif dev_type == TYPE_DISTANCE_COLOR_SENSOR:
            self.devices[port] = ColorDistanceSensor(self, port)
            self.color_distance_sensor = self.devices[port]
        elif dev_type == TYPE_LED:
            self.devices[port] = LED(self, port)
        elif dev_type == TYPE_TILT_SENSOR:
            self.devices[port] = TiltSensor(self, port)
        else:
            log.warning("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)
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
        else:
            log.warning("Unhandled port: %s", PORTS[port])
