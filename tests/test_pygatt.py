import unittest

import pygatt
import serial
from pygatt import BLEAddressType
from pygatt.backends.bgapi.bgapi import MAX_CONNECTION_ATTEMPTS
from pygatt.backends.bgapi.device import BGAPIBLEDevice
from pygatt.backends.bgapi.util import USBSerialDeviceInfo

from pylgbst.comms.cpygatt import GattoolConnection
from tests import log


class SerialMock(serial.Serial):
    def write(self, data):
        self.is_open = True
        log.debug("Write data to serial: %s", data)
        return len(data)

    def flush(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def read(self, size=1):
        return bytes()


class BGAPIBLEDeviceMock(BGAPIBLEDevice):
    def subscribe(self, uuid, callback=None, indication=False):
        log.debug("Mock subscribing")

    def char_write_handle(self, char_handle, value, wait_for_response=False):
        log.debug("Mock write: %s", value)


class BlueGigaBackendMock(pygatt.BGAPIBackend):
    def _open_serial_port(self, max_connection_attempts=MAX_CONNECTION_ATTEMPTS):
        log.debug("Mock open serial port")
        self._ser = SerialMock()

    def expect(self, expected, *args, **kargs):
        log.debug("Mock expect")
        data = {
            "packet_type": 0x04,
            "sender": "abcdef".encode('ascii'),
            "data": [1, 2, 3],
            "rssi": 1
        }
        self._ble_evt_gap_scan_response(data)

    def connect(self, address, timeout=5, address_type=BLEAddressType.public, interval_min=60, interval_max=76,
                supervision_timeout=100, latency=0):
        log.debug("Mock connect")
        device = BGAPIBLEDeviceMock("address", 0, self)
        return device

    def _detect_device_port(self):
        return USBSerialDeviceInfo().port_name


class BlueGigaTests(unittest.TestCase):
    def test_1(self):
        obj = GattoolConnection()
        obj.backend = BlueGigaBackendMock
        obj.connect(u'66:65:64:63:62:61')
        obj.write(0, "test".encode('ascii'))
        obj.set_notify_handler(lambda x: None)
