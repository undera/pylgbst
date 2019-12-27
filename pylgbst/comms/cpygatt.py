import logging

import pygatt

from pylgbst.comms import Connection, LEGO_MOVE_HUB, MOVE_HUB_HW_UUID_CHAR
from pylgbst.utilities import str2hex

log = logging.getLogger('comms-pygatt')


class GattoolConnection(Connection):
    """
    Used for connecting to

    :type _conn_hnd: pygatt.backends.bgapi.device.BGAPIBLEDevice
    """

    def __init__(self, controller='hci0'):
        Connection.__init__(self)
        self.backend = lambda: pygatt.GATTToolBackend(hci_device=controller)
        self._conn_hnd = None

    def connect(self, hub_mac=None):
        log.debug("Trying to connect client to MoveHub with MAC: %s", hub_mac)
        adapter = self.backend()
        adapter.start()

        while not self._conn_hnd:
            log.info("Discovering devices...")
            devices = adapter.scan(1)
            log.debug("Devices: %s", devices)

            for dev in devices:
                address = dev['address']
                name = dev['name']
                if self._is_device_matched(address, name, hub_mac):
                    self._conn_hnd = adapter.connect(address)
                    break

            if self._conn_hnd:
                break

        return self

    def disconnect(self):
        self._conn_hnd.disconnect()

    def write(self, handle, data):
        log.debug("Writing to handle %s: %s", handle, str2hex(data))
        return self._conn_hnd.char_write_handle(handle, bytearray(data))

    def set_notify_handler(self, handler):
        self._conn_hnd.subscribe(MOVE_HUB_HW_UUID_CHAR, handler)

    def is_alive(self):
        return True


class BlueGigaConnection(GattoolConnection):
    def __init__(self):
        super(BlueGigaConnection, self).__init__()
        self.backend = lambda: pygatt.BGAPIBackend()
