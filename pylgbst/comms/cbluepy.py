import logging
import re
from threading import Thread, Event

from bluepy import btle

from pylgbst.comms import Connection
from pylgbst.utilities import str2hex, queue

log = logging.getLogger('comms-bluepy')

COMPLETE_LOCAL_NAME_ADTYPE = 9
PROPAGATE_DISPATCHER_EXCEPTION = False


def _get_iface_number(controller):
    """bluepy uses iface numbers instead of full names."""
    if not controller:
        return None
    m = re.search(r'hci(\d+)$', controller)
    if not m:
        raise ValueError('Cannot find iface number in {}.'.format(controller))
    return int(m.group(1))


class BluepyDelegate(btle.DefaultDelegate):
    def __init__(self, handler):
        btle.DefaultDelegate.__init__(self)

        self._handler = handler

    def handleNotification(self, cHandle, data):
        log.debug('Incoming notification')
        self._handler(cHandle, data)


# We need a separate thread to wait for notifications,
# but calling peripheral's methods from different threads creates issues,
# so we will wrap all the calls into a thread
class BluepyThreadedPeripheral:
    def __init__(self, addr, addrType, controller):
        self._call_queue = queue.Queue()
        self._addr = addr
        self._addrType = addrType
        self._iface_number = _get_iface_number(controller)

        self._disconnect_event = Event()

        self._dispatcher_thread = Thread(target=self._dispatch_calls)
        self._dispatcher_thread.setDaemon(True)
        self._dispatcher_thread.setName("Bluepy call dispatcher")
        self._dispatcher_thread.start()

    def _dispatch_calls(self):
        self._peripheral = btle.Peripheral(self._addr, self._addrType, self._iface_number)
        try:
            while not self._disconnect_event.is_set():
                try:
                    try:
                        method = self._call_queue.get(False)
                        method()
                    except queue.Empty:
                        pass
                    self._peripheral.waitForNotifications(1.)
                except Exception as ex:
                    log.exception('Exception in call dispatcher thread', exc_info=ex)
                    if PROPAGATE_DISPATCHER_EXCEPTION:
                        log.error("Terminating dispatcher thread.")
                        raise
        finally:
            self._peripheral.disconnect()

    def write(self, handle, data):
        self._call_queue.put(lambda: self._peripheral.writeCharacteristic(handle, data))

    def set_notify_handler(self, handler):
        delegate = BluepyDelegate(handler)
        self._call_queue.put(lambda: self._peripheral.withDelegate(delegate))

    def disconnect(self):
        self._disconnect_event.set()


class BluepyConnection(Connection):
    def __init__(self, controller='hci0'):
        Connection.__init__(self)
        self._peripheral = None  # :type BluepyThreadedPeripheral
        self._controller = controller

    def connect(self, hub_mac=None, hub_name=None):
        log.debug("Trying to connect client to MoveHub with MAC: %s", hub_mac)
        scanner = btle.Scanner()

        while not self._peripheral:
            log.info("Discovering devices...")
            scanner.scan(1)
            devices = scanner.getDevices()

            for dev in devices:
                address = dev.addr
                address_type = dev.addrType
                name = dev.getValueText(COMPLETE_LOCAL_NAME_ADTYPE)

                if self._is_device_matched(address, name, hub_mac, hub_name):
                    self._peripheral = BluepyThreadedPeripheral(address, address_type, self._controller)
                    break

        return self

    def disconnect(self):
        self._peripheral.disconnect()

    def write(self, handle, data):
        log.debug("Writing to handle %s: %s", handle, str2hex(data))
        self._peripheral.write(handle, data)

    def set_notify_handler(self, handler):
        self._peripheral.set_notify_handler(handler)

    def is_alive(self):
        return True
