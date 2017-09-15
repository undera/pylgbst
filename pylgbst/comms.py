"""
This package holds communication aspects
"""
import binascii
import json
import logging
import socket
import sys
import time
import traceback
from six.moves import queue
from abc import abstractmethod
from binascii import unhexlify
from gattlib import DiscoveryService, GATTRequester
from threading import Thread

from pylgbst.constants import LEGO_MOVE_HUB, MSG_DEVICE_SHUTDOWN

log = logging.getLogger('comms')


def str2hex(data):  # TODO: eliminate it
    return binascii.hexlify(data).decode("utf8")


if sys.version_info[0] == 2:
    def get_byte(seq, index):
        return ord(seq[index])
else:
    def get_byte(seq, index):
        return seq[index]


# noinspection PyMethodOverriding
class Requester(GATTRequester):
    """
    Wrapper to access `on_notification` capability of GATT
    Set "notification_sink" field to a callable that will handle incoming data
    """

    def __init__(self, p_object, *args, **kwargs):
        super(Requester, self).__init__(p_object, *args, **kwargs)
        self.notification_sink = None

        # noinspection PyUnresolvedReferences
        self._notify_queue = queue.Queue()
        self._notifier_thread = Thread(target=self._dispatch_notifications)
        self._notifier_thread.setDaemon(True)
        self._notifier_thread.setName("Notify queue dispatcher")
        self._notifier_thread.start()

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
                    log.warning("Failed to dispatch notification: %s", str2hex(data))
                    log.warning("Failed to dispatch notification: %s", traceback.format_exc())
            else:
                log.warning("Dropped notification %s: %s", handle, str2hex(data))


class Connection(object):
    @abstractmethod
    def read(self, handle):
        pass

    @abstractmethod
    def write(self, handle, data):
        pass

    @abstractmethod
    def set_notify_handler(self, handler):
        pass


class BLEConnection(Connection):
    """
    Main transport class, uses real Bluetooth LE connection.
    Loops with timeout of 1 seconds to find device named "Lego MOVE Hub"

    :type _requester: Requester
    """

    def __init__(self):
        super(BLEConnection, self).__init__()
        self._requester = None

    def connect(self, bt_iface_name='hci0'):
        service = DiscoveryService(bt_iface_name)

        while not self._requester:
            log.info("Discovering devices using %s...", bt_iface_name)
            devices = service.discover(1)
            log.debug("Devices: %s", devices)

            for address, name in devices.items():
                if name == LEGO_MOVE_HUB:
                    logging.info("Found %s at %s", name, address)
                    self._requester = Requester(address, True, bt_iface_name)
                    break

        return self

    def set_notify_handler(self, handler):
        if self._requester:
            log.debug("Setting notification handler: %s", handler)
            self._requester.notification_sink = handler
        else:
            raise RuntimeError("No requester available")

    def read(self, handle):
        # FIXME: repeating reads hangs it...
        log.debug("Reading from: %s", handle)
        data = self._requester.read_by_handle(handle)
        log.debug("Result: %s", data)
        if isinstance(data, list):
            data = data[0]
        return data

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        return self._requester.write_by_handle(handle, data)


class DebugServer(object):
    """
    Starts TCP server to be used with DebugServerConnection to speed-up development process
    It holds BLE connection to Move Hub, so no need to re-start it every time
    Usage: DebugServer(BLEConnection().connect()).start()

    :type ble: BLEConnection
    """

    def __init__(self, ble_trans):
        self._running = False
        self.sock = socket.socket()
        self.ble = ble_trans

    def start(self, port=9090):
        self.sock.bind(('', port))
        self.sock.listen(1)

        self._running = True
        while self._running:
            log.info("Accepting connections at %s", port)
            conn, addr = self.sock.accept()
            if not self._running:
                raise KeyboardInterrupt("Shutdown")
            self.ble._requester.notification_sink = lambda x, y: self._notify(conn, x, y)
            try:
                self._handle_conn(conn)
            except KeyboardInterrupt:
                raise
            except BaseException:
                log.error("Problem handling incoming connection: %s", traceback.format_exc())
            finally:
                self.ble._requester.notification_sink = self._notify_dummy
                conn.close()

    def __del__(self):
        self.sock.close()

    def _notify_dummy(self, handle, data):
        log.debug("Dropped notification from handle %s: %s", handle, binascii.hexlify(data.strip()))
        self._check_shutdown(data)

    def _notify(self, conn, handle, data):
        payload = {"type": "notification", "handle": handle, "data": str2hex(data)}
        log.debug("Send notification: %s", payload)
        try:
            conn.send(json.dumps(payload) + "\n")
        except KeyboardInterrupt:
            raise
        except BaseException:
            log.error("Problem sending notification: %s", traceback.format_exc())

        self._check_shutdown(data)

    def _check_shutdown(self, data):
        if get_byte(data, 5) == MSG_DEVICE_SHUTDOWN:
            log.warning("Device shutdown")
            self._running = False

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
                    log.info("Cmd line: %s", line)
                    try:
                        self._handle_cmd(json.loads(line))
                    except KeyboardInterrupt:
                        raise
                    except BaseException:
                        log.error("Failed to handle cmd: %s", traceback.format_exc())

    def _handle_cmd(self, cmd):
        if cmd['type'] == 'write':
            self.ble.write(cmd['handle'], unhexlify(cmd['data']))
        elif cmd['type'] == 'read':
            data = self.ble.read(cmd['handle'])
            payload = {"type": "response", "data": str2hex(data)}
            log.debug("Send response: %s", payload)
            self.sock.send(json.dumps(payload) + "\n")
        else:
            raise ValueError("Unhandled cmd: %s", cmd)


class DebugServerConnection(Connection):
    """
    Connection type to be used with DebugServer, replaces BLEConnection
    """

    def __init__(self, port=9090):
        super(DebugServerConnection, self).__init__()
        self.notify_handler = None
        self.buf = ""
        self.sock = socket.socket()
        self.sock.connect(('localhost', port))
        self.incoming = []

        self.reader = Thread(target=self._recv)
        self.reader.setName("Debug connection reader")
        self.reader.setDaemon(True)
        self.reader.start()

    def __del__(self):
        self.sock.close()

    def write(self, handle, data):
        payload = {
            "type": "write",
            "handle": handle,
            "data": str2hex(data)
        }
        self._send(payload)

    def read(self, handle):
        payload = {
            "type": "read",
            "handle": handle
        }
        self._send(payload)

        while True:
            for item in self.incoming:
                if item['type'] == 'response':
                    self.incoming.remove(item)
                    return unhexlify(item['data'])
            time.sleep(0.1)

    def _send(self, payload):
        log.debug("Sending to debug server: %s", payload)
        self.sock.send(json.dumps(payload) + "\n")

    def _recv(self):
        while True:
            data = self.sock.recv(1024)
            log.debug("Recv from debug server: %s", data.strip())
            if not data:
                raise KeyboardInterrupt("Server has closed connection")

            self.buf += data

            while "\n" in self.buf:
                line = self.buf[:self.buf.index("\n")]
                self.buf = self.buf[self.buf.index("\n") + 1:]
                if line:
                    item = json.loads(line)
                    if item['type'] == 'notification' and self.notify_handler:
                        try:
                            self.notify_handler(item['handle'], unhexlify(item['data']))
                        except BaseException:
                            log.error("Failed to notify handler: %s", traceback.format_exc())
                    elif item['type'] == 'response':
                        self.incoming.append(item)
                    else:
                        log.warning("Dropped inbound: %s", item)

    def set_notify_handler(self, handler):
        self.notify_handler = handler


def start_debug_server(iface="hci0", port=9090):
    ble = BLEConnection()
    ble.connect(iface)
    server = DebugServer(ble)
    server.start(port)
