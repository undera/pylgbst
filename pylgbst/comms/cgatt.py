import logging
import re
import threading
from time import sleep

import gatt

from pylgbst.comms import Connection, MOVE_HUB_HW_UUID_SERV, MOVE_HUB_HW_UUID_CHAR, \
    MOVE_HUB_HARDWARE_HANDLE
from pylgbst.utilities import str2hex

log = logging.getLogger('comms-gatt')


class CustomDevice(gatt.Device):
    def __init__(self, mac_address, manager):
        gatt.Device.__init__(self, mac_address=mac_address, manager=manager)
        self._notify_callback = lambda hnd, val: None
        self._handle = None

    def connect(self):
        gatt.Device.connect(self)
        log.info("Waiting for device connection...")
        while self._handle is None:
            log.debug("Sleeping...")
            sleep(1)

        if isinstance(self._handle, BaseException):
            exc = self._handle
            self._handle = None
            raise exc

    def write(self, data):
        log.debug("Writing to handle: %s", str2hex(data))
        return self._handle.write_value(data)

    def enable_notifications(self):
        log.debug('Enable Notifications...')
        self._handle.enable_notifications()

    def set_notific_handler(self, func_hnd):
        self._notify_callback = func_hnd

    def services_resolved(self):
        log.debug('Getting MoveHub services and characteristics...')
        gatt.Device.services_resolved(self)
        log.debug("[%s] Resolved services", self.mac_address)
        for service in self.services:
            log.debug("[%s]  Service [%s]", self.mac_address, service.uuid)
            for characteristic in service.characteristics:
                log.debug("[%s]    Characteristic [%s]", self.mac_address, characteristic.uuid)
                if service.uuid == MOVE_HUB_HW_UUID_SERV and characteristic.uuid == MOVE_HUB_HW_UUID_CHAR:
                    log.debug('MoveHub characteristic found')
                    self._handle = characteristic

        if self._handle is None:
            self.manager.stop()
            self._handle = RuntimeError("Failed to obtain MoveHub handle")

    def characteristic_value_updated(self, characteristic, value):
        value = self._fix_weird_bug(value)
        log.debug('Notification in GattDevice: %s', str2hex(value))
        self._notify_callback(MOVE_HUB_HARDWARE_HANDLE, value)

    def _fix_weird_bug(self, value):
        if isinstance(value, str) and "dbus.Array" in value:  # weird bug from gatt on my Ubuntu 16.04!
            log.debug("Fixing broken notify string: %s", value)
            return ''.join([chr(int(x.group(1))) for x in re.finditer(r"dbus.Byte\((\d+)\)", value)])

        return value


class GattConnection(Connection):
    """
    :type _device: CustomDevice
    """

    def __init__(self, bt_iface_name='hci0'):
        super().__init__()
        self._device = None
        self._iface = bt_iface_name
        try:
            self._manager = gatt.DeviceManager(adapter_name=self._iface)
        except TypeError:
            raise NotImplementedError("Gatt is not implemented for this platform")

        self._manager_thread = threading.Thread(target=self._manager.run)
        self._manager_thread.setDaemon(True)
        log.debug('Starting DeviceManager...')

    def connect(self, hub_mac=None, hub_name=None):
        self._manager_thread.start()
        self._manager.start_discovery()

        while not self._device:
            log.info("Discovering devices...")
            devices = self._manager.devices()
            log.debug("Devices: %s", devices)

            for dev in devices:
                address = dev.mac_address
                name = dev.alias()
                if self._is_device_matched(address, name, hub_mac, hub_name):
                    self._device = CustomDevice(address, self._manager)
                    break

            if not self._device:
                sleep(1)

        self._device.connect()
        return self

    def disconnect(self):
        self._manager.stop()
        self._device.disconnect()

    def write(self, handle, data):
        self._device.write(data)

    def set_notify_handler(self, handler):
        self._device.set_notific_handler(handler)

    def enable_notifications(self):
        self._device.enable_notifications()

    def is_alive(self):
        return self._manager_thread.isAlive()
