# noinspection PyMethodOverriding
import logging
import traceback
from gattlib import DiscoveryService, GATTRequester
from threading import Thread

from pylgbst.comms import Connection, LEGO_MOVE_HUB, DebugServer
from pylgbst.utilities import queue, str2hex

log = logging.getLogger('comms-gattlib')


class Requester(GATTRequester):
    """
    Wrapper to access `on_notification` capability of GATT
    Set "notification_sink" field to a callable that will handle incoming data
    """

    def __init__(self, p_object, *args, **kwargs):
        super(Requester, self).__init__(p_object, *args, **kwargs)
        self.notification_sink = None

        self._notify_queue = queue.Queue()  # this queue is to minimize time spent in gattlib C code
        thr = Thread(target=self._dispatch_notifications)
        thr.setDaemon(True)
        thr.setName("Notify queue dispatcher")
        thr.start()

    def on_notification(self, handle, data):
        # log.debug("requester notified, sink: %s", self.notification_sink)
        self._notify_queue.put((handle, data))

    def on_indication(self, handle, data):
        log.debug("Indication on handle %s: %s", handle, str2hex(data))

    def _dispatch_notifications(self):
        while True:
            handle, data = self._notify_queue.get()
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

    def __init__(self):
        super(GattLibConnection, self).__init__()
        self.requester = None

    def connect(self, bt_iface_name='hci0', hub_mac=None):
        service = DiscoveryService(bt_iface_name)

        while not self.requester:
            log.info("Discovering devices using %s...", bt_iface_name)
            devices = service.discover(1)
            log.debug("Devices: %s", devices)

            for address, name in devices.items():
                if name == LEGO_MOVE_HUB or hub_mac == address:
                    logging.info("Found %s at %s", name, address)
                    self.requester = Requester(address, True, bt_iface_name)
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


def start_debug_server(iface="hci0", port=9090):
    ble = GattLibConnection()
    ble.connect(iface)
    server = DebugServer(ble)
    server.start(port)
