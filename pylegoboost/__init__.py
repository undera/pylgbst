from pylegoboost.constants import *


class MoveHub(object):
    """
    :type connection: pylegoboost.comms.Connection
    :type led: LED
    """

    def __init__(self, connection):
        self.connection = connection

        self.led = LED(self)
        # self.motor_a
        # self.motor_b
        # self.motor_ab

        # self.port_c
        # self.port_d

        # self.button
        # self.tilt_sensor

        # transport.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)
        # transport.write(MOVE_HUB_HARDWARE_HANDLE, b'\x0a\x00\x41\x01\x08\x01\x00\x00\x00\x01')


class Peripheral(object):
    """
    :type parent: MoveHub
    """

    def __init__(self, parent):
        super(Peripheral, self).__init__()
        self.parent = parent


class LED(Peripheral):
    def set_color(self, color):
        if color not in COLORS_MAP:
            raise ValueError("Color %s is not in list of available colors" % color)

        cmd = CMD_SET_COLOR + chr(color)
        self.parent.connection.write(MOVE_HUB_HARDWARE_HANDLE, cmd)


class InteractiveMotor(object):
    pass


class ColorDistanceSensor(object):
    pass
