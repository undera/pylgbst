import logging
from struct import pack

from pylgbst.peripherals import Peripheral, Motor, EncodedMotor, ColorDistanceSensor, LED, TiltSensor, Current, Voltage
from pylgbst.utilities import usbyte, ushort, str2hex

log = logging.getLogger('hub')


class Message(object):
    TYPE = None

    def __init__(self):
        self.payload = ""
        self.hub_id = 0x00  # not used according to official doc

    def __str__(self):
        """
        see https://lego.github.io/lego-ble-wireless-protocol-docs/#common-message-header
        """
        msglen = len(self.payload) + 3
        assert msglen < 127, "TODO: handle logner messages with 2-byte len"
        return pack("<B", msglen) + pack("<B", self.hub_id) + pack("<B", self.TYPE) + self.payload

    def __iter__(self):
        return iter(str(self))

    @classmethod
    def decode(cls, data):
        msglen = usbyte(data, 0)
        assert msglen < 127, "TODO: handle longer messages with 2-byte len"
        hub_id = usbyte(data, 1)
        assert hub_id == 0
        msg_type = usbyte(data, 2)
        assert cls.TYPE == msg_type, "Message type does not match: %x!=%x" % (cls.TYPE, msg_type)

        msg = cls()
        msg.payload = data[3:]
        return msg

    def __repr__(self):
        return self.__class__.__name__ + "(type=%x, payload=%s)" % (self.TYPE, str2hex(self.payload))


class MsgHubProperties(Message):
    TYPE = 0x01

    ADVERTISE_NAME = 0x01
    BUTTON = 0x02
    FW_VERSION = 0x03
    HW_VERSION = 0x04
    RSSI = 0x05
    VOLTAGE = 0x06
    BATTERY_TYPE = 0x07
    MANUFACTURER = 0x08
    RADIO_FW_VERSION = 0x09
    WIRELESS_PROTO_VERSION = 0x0A
    SYSTEM_TYPE_ID = 0x0B
    HW_NETW_ID = 0x0C
    PRIMARY_MAC = 0x0D
    SECONDARY_MAC = 0x0E
    HARDWARE_NETWORK_FAMILY = 0x0F

    SET = 0x01
    UPD_ENABLE = 0x02
    UPD_DISABLE = 0x03
    RESET = 0x04
    UPD_REQUEST = 0x05
    UPSTREAM_UPDATE = 0x06

    def __init__(self, prop=None, operation=None, parameters=""):
        super(MsgHubProperties, self).__init__()

        self.property = prop
        self.operation = operation
        self.parameters = parameters

    def payload(self):
        return pack("<B", self.property) + pack("<B", self.operation) + self.parameters

    @classmethod
    def decode(cls, data):
        msg = super(MsgHubProperties, cls).decode(data)
        assert isinstance(msg, MsgHubProperties)
        msg.property = usbyte(data, 3)
        msg.operation = usbyte(data, 4)
        msg.payload = data[5:]
        return msg


class MsgHubActions(Message):
    TYPE = 0x02

    SWITCH_OFF = 0x01
    DISCONNECT = 0x02
    VCC_PORT_CONTROL_ON = 0x03
    VCC_PORT_CONTROL_OFF = 0x04
    BUSY_INDICATION_ON = 0x05
    BUSY_INDICATION_OFF = 0x06
    SWITCH_OFF_IMMEDIATELY = 0x2F

    UPSTREAM_SHUTDOWN = 0x30
    UPSTREAM_DISCONNECT = 0x31
    UPSTREAM_BOOT_MODE = 0x32

    def __init__(self, action=None):
        super(MsgHubActions, self).__init__()
        if action is not None:
            self.payload = chr(action)

    @classmethod
    def decode(cls, data):
        msg = super(MsgHubActions, cls).decode(data)
        action = usbyte(msg.payload, 0)
        # TODO: make hub to disconnect if device says so
        if action == cls.UPSTREAM_SHUTDOWN:
            log.warning("Device will shut down")
        elif action == cls.UPSTREAM_DISCONNECT:
            log.warning("Device disconnects")
        elif action == cls.UPSTREAM_BOOT_MODE:
            log.warning("Device goes into boot mode")

        return msg


class MsgHubAlert(Message):
    TYPE = 0x03

    LOW_VOLTAGE = 0x01
    HIGH_CURRENT = 0x02
    LOW_SIGNAL = 0x03
    OVER_POWER = 0x04

    DESCR = {
        LOW_VOLTAGE: "low voltage",
        HIGH_CURRENT: "high current",
        LOW_SIGNAL: "low signal",
        OVER_POWER: "over power"
    }

    UPD_ENABLE = 0x01
    UPD_DISABLE = 0x02
    UPD_REQUEST = 0x03
    UPSTREAM_UPDATE = 0x04

    def __init__(self, atype=None, operation=None):
        super(MsgHubAlert, self).__init__()
        self.atype = atype
        self.status = None
        if atype is not None:
            self.payload = chr(atype) + chr(operation)

    @classmethod
    def decode(cls, data):
        msg = super(MsgHubAlert, cls).decode(data)
        assert isinstance(msg, MsgHubAlert)
        assert usbyte(msg.payload, 1) == cls.UPSTREAM_UPDATE
        # TODO: make this info visible to hub somehow?
        msg.atype = usbyte(msg.payload, 0)
        msg.status = usbyte(msg.payload, 2)

        if not msg.is_ok():
            log.warning("Alert: %s", msg.DESCR[msg.atype])
        else:
            log.info("Status is OK on: %s", msg.DESCR[msg.atype])
        return msg

    def is_ok(self):
        return not self.status


class MsgHubAttachedIO(Message):
    TYPE = 0x04

    EVENT_DETACHED = 0x00
    EVENT_ATTACHED = 0x01
    EVENT_ATTACHED_VIRTUAL = 0x02

    # DEVICE TYPES
    DEV_MOTOR = 0x0001
    DEV_SYSTEM_TRAIN_MOTOR = 0x0002
    DEV_BUTTON = 0x0005
    DEV_LED_LIGHT = 0x0008
    DEV_VOLTAGE = 0x0014
    DEV_CURRENT = 0x0015
    DEV_PIEZO_SOUND = 0x0016
    DEV_RGB_LIGHT = 0x0017
    DEV_TILT_EXTERNAL = 0x0022
    DEV_MOTION_SENSOR = 0x0023
    DEV_VISION_SENSOR = 0x0025
    DEV_MOTOR_EXTERNAL_TACHO = 0x0026
    DEV_MOTOR_INTERNAL_TACHO = 0x0027
    DEV_TILT_INTERNAL = 0x0028

    DEVICE_TYPES = {
    }

    def __init__(self):
        super(MsgHubAttachedIO, self).__init__()
        self.port = None
        self.event = None

    @classmethod
    def decode(cls, data):
        msg = super(MsgHubAttachedIO, cls).decode(data)
        assert isinstance(msg, MsgHubAttachedIO)
        msg.port = usbyte(msg.payload, 0)
        msg.event = usbyte(msg.payload, 1)
        msg.payload = msg.payload[2:]
        return msg

    def create_peripheral(self, hub):
        assert self.event in (self.EVENT_ATTACHED, self.EVENT_ATTACHED_VIRTUAL)
        port = self.port
        dev_type = ushort(self.payload, 0)

        if self.event == self.EVENT_ATTACHED:
            # TODO: what to do with this info? it's useless, I guess
            hw_revision = reversed([usbyte(self.payload, x) for x in range(2, 6)])
            sw_revision = reversed([usbyte(self.payload, x) for x in range(6, 10)])
        elif self.event == self.EVENT_ATTACHED_VIRTUAL:
            # TODO: what to do with this info? pass to device?
            joint_ports = (usbyte(self.payload, 2), usbyte(self.payload, 3))

        if dev_type == self.DEV_MOTOR:
            return Motor(hub, port)
        elif dev_type in (self.DEV_MOTOR_EXTERNAL_TACHO, self.DEV_MOTOR_INTERNAL_TACHO):
            return EncodedMotor(hub, port)
        elif dev_type == self.DEV_VISION_SENSOR:
            return ColorDistanceSensor(hub, port)
        elif dev_type == self.DEV_RGB_LIGHT:
            return LED(hub, port)
        elif dev_type in (self.DEV_TILT_EXTERNAL, self.DEV_TILT_INTERNAL):
            return TiltSensor(hub, port)
        elif dev_type == self.DEV_CURRENT:
            return Current(hub, port)
        elif dev_type == self.DEV_VOLTAGE:
            return Voltage(hub, port)
        # TODO: support more types of peripherals
        else:
            log.warning("Unhandled peripheral type 0x%x on port 0x%x", dev_type, port)
            return Peripheral(hub, port)


class MsgGenericError(Message):
    TYPE = 0x05
    pass


class MsgPortInfoRequest(Message):
    TYPE = 0x21
    pass


class MsgPortModeInfoRequest(Message):
    TYPE = 0x22
    pass


class MsgPortInputFmtSetupSingle(Message):
    TYPE = 0x41
    pass


class MsgPortInputFmtSetupCombined(Message):
    TYPE = 0x42
    pass


class MsgPortInfo(Message):
    TYPE = 0x43
    pass


class MsgPortModeInfo(Message):
    TYPE = 0x44
    pass


class MsgPortValueSingle(Message):
    TYPE = 0x45
    pass


class MsgPortValueCombined(Message):
    TYPE = 0x46
    pass


class MsgPortInputFmtSingle(Message):
    TYPE = 0x47
    pass


class MsgPortInputFmtCombined(Message):
    TYPE = 0x48
    pass


class MsgVirtualPortSetup(Message):
    TYPE = 0x61
    pass


class MsgPortOutput(Message):
    TYPE = 0x81
    pass


class MsgPortOutputFeedback(Message):
    TYPE = 0x82
    pass


UPSTREAM_MSGS = (
    MsgHubProperties, MsgHubActions, MsgHubAlert, MsgHubAttachedIO, MsgGenericError,
    MsgPortInfo, MsgPortModeInfo,
    MsgPortValueSingle, MsgPortValueCombined, MsgPortInputFmtSingle, MsgPortInputFmtCombined,
    MsgPortOutputFeedback
)
