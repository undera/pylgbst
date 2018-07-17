import logging
import threading
from time import sleep

from gatt import gatt_linux as gatt, DeviceManager  # FIXME: temporary

from pylgbst.comms import Connection, LEGO_MOVE_HUB
from pylgbst.constants import MOVE_HUB_HW_UUID_SERV, MOVE_HUB_HW_UUID_CHAR, MOVE_HUB_HARDWARE_HANDLE
from pylgbst.utilities import str2hex

log = logging.getLogger('comms-bluez')


class BlueZInterface(gatt.Device, object):  # Pendant zu Klasse BlueGigaInterface
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
        log.debug('Notification in GattDevice: %s', str2hex(value))
        self._notify_callback(MOVE_HUB_HARDWARE_HANDLE, value)


class BlueZConnection(Connection):
    """
    :type _device: BlueZInterface
    """

    def __init__(self):
        super(BlueZConnection, self).__init__()
        self._device = None

    def connect(self, bt_iface_name='hci0', hub_mac=None):
        dev_manager = DeviceManager(adapter_name=bt_iface_name)
        dman_thread = threading.Thread(target=dev_manager.run)
        dman_thread.setDaemon(True)
        log.debug('Starting DeviceManager...')
        dman_thread.start()
        dev_manager.start_discovery()

        while not self._device:
            log.info("Discovering devices...")
            devices = dev_manager.devices()
            log.debug("Devices: %s", devices)

            for dev in devices:
                address = dev.mac_address
                name = dev.alias()
                if name == LEGO_MOVE_HUB or hub_mac == address:
                    logging.info("Found %s at %s", name, address)
                    self._device = BlueZInterface(address, dev_manager)
                    break

            if not self._device:
                sleep(1)

        self._device.connect()
        return self

    def disconnect(self):
        self._device.disconnect()

    def write(self, handle, data):
        self._device.write(data)

    def set_notify_handler(self, handler):
        self._device.set_notific_handler(handler)

    def enable_notifications(self):
        self._device.enable_notifications()
