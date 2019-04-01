# PACKET TYPES
MSG_DEVICE_INFO = 0x01
# 0501010305 gives 090001030600000010
MSG_DEVICE_SHUTDOWN = 0x02  # sent when hub shuts down by button hold
MSG_PING_RESPONSE = 0x03
MSG_PORT_INFO = 0x04
MSG_PORT_CMD_ERROR = 0x05

MSG_SET_PORT_VAL = 0x81
MSG_PORT_STATUS = 0x82
MSG_SENSOR_SUBSCRIBE = 0x41
MSG_SENSOR_SOMETHING1 = 0x42  # it is seen close to sensor subscribe commands. Subscription options? Initial value?
MSG_SENSOR_DATA = 0x45
MSG_SENSOR_SUBSCRIBE_ACK = 0x47


# NOTIFICATIONS
STATUS_STARTED = 0x01
STATUS_CONFLICT = 0x05
STATUS_FINISHED = 0x0a
STATUS_INPROGRESS = 0x0c  # FIXME: not sure about description
STATUS_INTERRUPTED = 0x0e  # FIXME:  not sure about description

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
