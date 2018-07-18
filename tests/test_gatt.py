import unittest

from gatt import DeviceManager

from pylgbst.comms_gatt import CustomDevice
from tests import log, str2hex


class TestGatt(unittest.TestCase):
    def test_one(self):
        log.debug("")
        obj = CustomDevice("AA", DeviceManager("hci0"))

        def callback(handle, value):
            log.debug("%s: %s", type(value), str2hex(value))
            self.assertEquals("0f0004020126000000001000000010", str2hex(value))

        obj.set_notific_handler(callback)
        arr = "dbus.Array([dbus.Byte(15), dbus.Byte(0), dbus.Byte(4), dbus.Byte(2), dbus.Byte(1), dbus.Byte(38), " \
              "dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(16), dbus.Byte(0), dbus.Byte(0), " \
              "dbus.Byte(0), dbus.Byte(16)], signature=dbus.Signature('y'), variant_level=1)"
        obj.characteristic_value_updated(None, arr)
