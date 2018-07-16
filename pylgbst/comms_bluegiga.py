import logging

import pygatt

from pylgbst.comms import Connection, DebugServer, LEGO_MOVE_HUB
from pylgbst.constants import MOVE_HUB_HW_UUID_CHAR
from pylgbst.utilities import str2hex

log = logging.getLogger('comms-pygatt')


class BlueGigaConnection(Connection):
    def __init__(self):
        Connection.__init__(self)
        self.backend = pygatt.BGAPIBackend
        self._conn_hnd = None

    def connect(self, hub_mac=None):
        log.debug("Trying to connect client to MoveHub with MAC: %s", hub_mac)
        service = self.backend()
        service.start()

        while not self._conn_hnd:
            log.info("Discovering devices...")
            devices = service.scan(1)
            log.debug("Devices: %s", devices)

            for dev in devices:
                address = dev['address']
                name = dev['name']
                if name == LEGO_MOVE_HUB or hub_mac == address:
                    logging.info("Found %s at %s", name, address)
                    self._conn_hnd = service.connect(address)
                    break

            if self._conn_hnd:
                break

        return self

    def write(self, handle, data):
        log.debug("Writing to handle %s: %s", handle, str2hex(data))
        return self._conn_hnd.char_write_handle(handle, data)

    def set_notify_handler(self, handler):
        self._conn_hnd.subscribe(MOVE_HUB_HW_UUID_CHAR, handler)
