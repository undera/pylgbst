"""
This package holds communication aspects
"""
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
    """
    Wrapper to access `on_notification` capability of GATT
    Set "notification_sink" field to a callable that will handle incoming data
    """

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
        # TODO
        pass

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, data.encode("hex"))

    def read(self, handle):
        log.debug("Reading from: %s", handle)
        return None  # TODO


class BLEConnection(Connection):
    """
    Main transport class, uses real Bluetooth LE connection.
    Loops with timeout of 5 seconds to find device named "Lego MOVE Hub"

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
        # TODO
        log.debug("Notification on %s: %s", handle, data.encode("hex"))


class DebugServer(object):
    """
    Starts TCP server to be used with DebugServerConnection to speed-up development process
    It holds BLE connection to Move Hub, so no need to re-start it every time
    Usage: DebugServer(BLEConnection().connect()).start()

    :type ble: BLEConnection
    """

    def __init__(self, ble_trans):
        self.sock = socket.socket()
        self.ble = ble_trans

    def start(self, port=9090):
        self.sock.bind(('', port))
        self.sock.listen(1)

        while True:
            log.info("Accepting connections at %s", port)
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
            log.debug("Recv: %s", data.strip())
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

    def _handle_cmd(self, cmd):
        if cmd['type'] == 'write':
            self.ble.write(cmd['handle'], cmd['data'].decode('hex'))
        elif cmd['type'] == 'read':
            self.sock.send(self.ble.read(cmd['handle']).encode('hex') + "\n")
        else:
            raise ValueError("Unhandled cmd: %s", cmd)


class DebugServerConnection(Connection):
    """
    Connection type to be used with DebugServer, replaces BLEConnection
    """

    def __init__(self):
        self.buf = ""
        self.sock = socket.socket()
        self.sock.connect(('localhost', 9090))

    def __del__(self):
        self.sock.close()

    def notify(self, handle, data):
        # TODO
        pass

    def write(self, handle, data):
        payload = {
            "type": "write",
            "handle": handle,
            "data": data.encode("hex")
        }
        self._send(payload)

    def read(self, handle):
        payload = {
            "type": "read",
            "handle": handle
        }
        self._send(payload)
        return self._recv()

    def _send(self, payload):
        log.debug("Sending to debug server: %s", payload)
        self.sock.send(json.dumps(payload) + "\n")

    def _recv(self):
        while True:
            data = self.sock.recv(1024)
            log.debug("Recv from debug server: %s", data.strip())
            if not data:
                break

            self.buf += data

            if "\n" in self.buf:
                line = self.buf[:self.buf.index("\n")]
                self.buf = self.buf[self.buf.index("\n") + 1:]
                if line:
                    return line.decode("hex")
                break
        raise RuntimeError("No data read")
