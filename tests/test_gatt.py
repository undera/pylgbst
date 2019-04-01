import dbus
import sys
import unittest

from gatt import DeviceManager

from pylgbst.comms.cgatt import CustomDevice, GattConnection
from tests import log, str2hex


class MockBus(object):
    def __init__(self, *args, **kwargs):
        # super(MockBus, self).__init__(*args, **kwargs)
        pass

    def get_object(self, bus_name, object_path, introspect=True, follow_name_owner_changes=False, **kwargs):
        return None


dbus.SystemBus = lambda: MockBus()


class DeviceManagerMock(DeviceManager, object):
    def update_devices(self):
        pass


class TestGatt(unittest.TestCase):
    def test_one(self):
        log.debug("")
        manager = DeviceManagerMock("hci0")
        obj = CustomDevice("AA", manager)

        def callback(handle, value):
            log.debug("%s: %s", type(value), str2hex(value))
            if sys.version_info[0] == 2:
                self.assertEquals("0f0004020126000000001000000010", str2hex(value))

        obj.set_notific_handler(callback)
        arr = "dbus.Array([dbus.Byte(15), dbus.Byte(0), dbus.Byte(4), dbus.Byte(2), dbus.Byte(1), dbus.Byte(38), " \
              "dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(0), dbus.Byte(16), dbus.Byte(0), dbus.Byte(0), " \
              "dbus.Byte(0), dbus.Byte(16)], signature=dbus.Signature('y'), variant_level=1)"
        obj.characteristic_value_updated(None, arr if sys.version_info[0] == 2 else bytes(arr, 'ascii'))

    def test_conn(self):
        try:
            obj = GattConnection()
            obj.connect()
        except AttributeError:
            pass
