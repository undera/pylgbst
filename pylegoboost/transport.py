import json
import logging
import socket
import traceback
from abc import abstractmethod
from gattlib import DiscoveryService, GATTRequester

from pylegoboost.constants import DEVICE_NAME, LEGO_MOVE_HUB

log = logging.getLogger('transport')


# noinspection PyMethodOverriding
class Requester(GATTRequester):
    def __init__(self, p_object, *args, **kwargs):
        super(Requester, self).__init__(p_object, *args, **kwargs)
        self.notification_sink = None

    def on_notification(self, handle, data):
        if self.notification_sink:
            self.notification_sink(handle, data)

    def on_indication(self, handle, data):
        log.debug("Indication on handle %s: %s", handle, data.encode("hex"))


class Connection(object):
    @abstractmethod
    def read(self, handle):
        pass

    # TODO: it always writes same handle, hardcode it?
    @abstractmethod
    def write(self, handle, data):
        pass

    @abstractmethod
    def notify(self, handle, data):
        pass


class ConnectionMock(Connection):
    """
    For unit testing purposes
    """

    def notify(self, handle, data):
        pass

    def write(self, handle, data):
        pass

    def read(self, handle):
        pass


class BLEConnection(Connection):
    """
    :type requester: Requester
    """

    def __init__(self):
        super(Connection, self).__init__()
        self.requester = None

    def connect(self, bt_iface_name='hci0'):
        service = DiscoveryService(bt_iface_name)

        while not self.requester:
            log.info("Discovering devices using %s...", bt_iface_name)
            devices = service.discover(5)
            log.debug("Devices: %s", devices)

            for address, name in devices.items():
                if name == LEGO_MOVE_HUB:
                    logging.info("Found %s at %s", name, address)
                    self._get_requester(address, bt_iface_name)
                    break

        log.info("Device declares itself as: %s", self.read(DEVICE_NAME))
        return self

    def _get_requester(self, address, bt_iface_name):
        self.requester = Requester(address, True, bt_iface_name)
        self.requester.notification_sink = self.notify

    def read(self, handle):
        log.debug("Reading from: %s", handle)
        data = self.requester.read_by_handle(handle)
        log.debug("Result: %s", data)
        if isinstance(data, list):
            data = data[0]
        return data

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, data.encode("hex"))
        return self.requester.write_by_handle(handle, data)

    def notify(self, handle, data):
        log.debug("Notification on %s: %s", handle, data.encode("hex"))


class DebugServer(object):
    def __init__(self, ble_trans):
        self.sock = socket.socket()
        self.ble = ble_trans

    def start(self, port=9090):
        self.sock.bind(('', port))
        self.sock.listen(1)

        while True:
            conn, addr = self.sock.accept()
            try:
                self._handle_conn(conn)
            finally:
                conn.close()

    def __del__(self):
        self.sock.close()

    def _handle_conn(self, conn):
        """
        :type conn: socket._socketobject
        """
        buf = ""
        while True:
            data = conn.recv(1024)
            log.debug("Recv: %s", data)
            if not data:
                break

            buf += data

            if "\n" in buf:
                line = buf[:buf.index("\n")]
                buf = buf[buf.index("\n") + 1:]

                if line:
                    log.debug("Cmd line: %s", line)
                    try:
                        self._handle_cmd(json.loads(line))
                    except BaseException:
                        log.error("Failed to handle cmd: %s", traceback.format_exc())

                        # conn.send(data.upper())

    def _handle_cmd(self, line):
        pass


class DebugServerConnection(Connection):
    def __init__(self):
        self.sock = socket.socket()
        self.sock.connect(('localhost', 9090))

        # sock.send('hello, world!')

        # data = sock.recv(1024)

    def __del__(self):
        self.sock.close()
