from struct import pack, unpack

from pylgbst.utilities import usbyte


class Message(object):
    TYPE = None

    def __init__(self):
        self.hub_id = 0x00  # not used according to official doc

    def __str__(self):
        """
        see https://lego.github.io/lego-ble-wireless-protocol-docs/#common-message-header
        """
        payload = self.payload()
        msglen = len(payload) + 3
        assert msglen < 127, "TODO: handle logner messages with 2-byte len"
        return pack("<B", msglen) + pack("<B", self.hub_id) + pack("<B", self.TYPE) + payload

    def payload(self):
        return ''

    def __iter__(self):
        return iter(str(self))

    @classmethod
    def decode(cls, data):
        msglen = usbyte(data, 0)
        assert msglen < 127, "TODO: handle logner messages with 2-byte len"
        hub_id = usbyte(data, 1)
        assert hub_id == 0
        msg_type = usbyte(data, 2)
        assert cls.TYPE == msg_type, "Message type does not match: %x!=%x" % (cls.TYPE, msg_type)
        return cls()

    def __repr__(self):
        return self.__class__.__name__ + "(type=%x)" % self.TYPE


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

    def __init__(self, prop, operation, parameters=""):
        super(MsgHubProperties, self).__init__()

        self.property = prop
        self.operation = operation
        self.parameters = parameters

    def payload(self):
        return pack("<B", self.property) + pack("<B", self.operation) + self.parameters

    @classmethod
    def decode(cls, data):
        # super(MsgHubProperties, cls).decode(data)
        prop = usbyte(data, 3)
        operation = usbyte(data, 4)
        msg = cls(prop, operation, data[5:])
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
    pass


class MsgHubAlerts(Message):
    TYPE = 0x03

    LOW_VOLTAGE = 0x01
    HIGH_CURRENT = 0x02
    LOW_SIGNAL = 0x03
    OVER_POWER = 0x04

    UPD_ENABLE = 0x01
    UPD_DISABLE = 0x02
    UPD_REQUEST = 0x03
    UPSTREAM_UPDATE = 0x04
    pass


class MsgHubAttachedIO(Message):
    TYPE = 0x04
    pass


class MsgGenericError(Message):
    TYPE = 0x05
    pass


class MsgPortInfoRequest(Message):
    TYPE = 0x21
    pass


class MsgPortModeInfoRequest(Message):
    TYPE = 0x22
    pass


class MsgPortInputFmtSingle(Message):
    TYPE = 0x41
    pass


class MsgPortInputFmtCombined(Message):
    TYPE = 0x42
    pass
