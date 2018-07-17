import time
import unittest

from gatt import DeviceManager

from pylgbst import MoveHub
from pylgbst.comms_gatt import CustomDevice, GattConnection
from tests import log, str2hex


class TestGatt(unittest.TestCase):
    def test_one(self):
        log.debug("")
        obj = CustomDevice("AA", DeviceManager("hci0"))

        def callback(handle, value):
            log.debug("%s: %s", type(value), str2hex(value))
            self.assertEquals("0f0004020126000000001000000010", str2hex(value))

        obj.set_notific_handler(callback)
        arr = "dbus.Array([dbus.Byte(15), dbus.Byte(0), dbus.Byte(4), dbus.Byte(2), dbus.Byte(1), dbus.Byte(38), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(16), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(16)], signature=dbus.Signature('y'), variant_level=1)"
        obj.characteristic_value_updated(None, arr)

    def test_two(self):
        obj = GattConnection()
        obj.connect()

        def callback(handle, value):
            log.debug("%s: %s", type(value), value)

        obj.set_notify_handler(callback)
        try:
            obj.enable_notifications()
            time.sleep(600)
        finally:
            obj.disconnect()

    def test_three(self):
        connect = GattConnection().connect()
        hub = MoveHub(connect)
        try:
            #time.sleep(5)
            hub.motor_AB.angled(90)
            time.sleep(1)
        finally:
            connect.disconnect()
