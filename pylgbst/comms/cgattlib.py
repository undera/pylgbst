# noinspection PyMethodOverriding
import logging
import traceback
from threading import Thread

from gattlib import DiscoveryService, GATTRequester

from pylgbst.comms import Connection
from pylgbst.utilities import queue, str2hex

log = logging.getLogger('comms-gattlib')


class Requester(GATTRequester):
    """
    Wrapper to access `on_notification` capability of GATT
    Set "notification_sink" field to a callable that will handle incoming data
    """

    def __init__(self, p_object, *args, **kwargs):
        super().__init__(p_object, *args, **kwargs)
        self.notification_sink = None

        self._notify_queue = queue.Queue()  # this queue is to minimize time spent in gattlib C code
        self.notify_thread = Thread(target=self._dispatch_notifications)
        self.notify_thread.setDaemon(True)
        self.notify_thread.setName("Notify queue dispatcher")
        self.notify_thread.start()

    def on_notification(self, handle, data):
        # log.debug("requester notified, sink: %s", self.notification_sink)
        self._notify_queue.put((handle, data))

    def on_indication(self, handle, data):
        log.debug("Indication on handle %s: %s", handle, str2hex(data))

    def _dispatch_notifications(self):
        while True:
            handle, data = self._notify_queue.get()
            data = data[3:]  # for some reason, there are extra bytes
            if self.notification_sink:
                try:
                    self.notification_sink(handle, data)
                except BaseException:
                    log.warning("Data was: %s", str2hex(data))
                    log.warning("Failed to dispatch notification: %s", traceback.format_exc())
            else:
                log.warning("Dropped notification %s: %s", handle, str2hex(data))


class GattLibConnection(Connection):
    """
    Main transport class, uses real Bluetooth LE connection.
    Loops with timeout of 1 seconds to find device named "Lego MOVE Hub"

    :type requester: Requester
    """

    def __init__(self, bt_iface_name='hci0'):
        super().__init__()
        self.requester = None
        self._iface = bt_iface_name

    def connect(self, hub_mac=None, hub_name=None):
        service = DiscoveryService(self._iface)

        while not self.requester:
            log.info("Discovering devices using %s...", self._iface)
            devices = service.discover(1)
            log.debug("Devices: %s", devices)

            for address, name in devices.items():
                if self._is_device_matched(address, name, hub_mac, hub_name):
                    self.requester = Requester(address, True, self._iface)
                    break

            if self.requester:
                break

        return self

    def set_notify_handler(self, handler):
        if self.requester:
            log.debug("Setting notification handler: %s", handler)
            self.requester.notification_sink = handler
        else:
            raise RuntimeError("No requester available")

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        return self.requester.write_by_handle(handle, data)

    def is_alive(self):
        return self.requester.notify_thread.isAlive()
