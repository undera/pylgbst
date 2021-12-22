"""
This package holds communication aspects
"""
import binascii
import json
import logging
import socket
import traceback
from abc import abstractmethod
from binascii import unhexlify
from threading import Thread

from pylgbst.messages import MsgHubAction
from pylgbst.utilities import str2hex

log = logging.getLogger('comms')

MOVE_HUB_HW_UUID_SERV = '00001623-1212-efde-1623-785feabcd123'
MOVE_HUB_HW_UUID_CHAR = '00001624-1212-efde-1623-785feabcd123'
ENABLE_NOTIFICATIONS_HANDLE = 0x000f
ENABLE_NOTIFICATIONS_VALUE = b'\x01\x00'

MOVE_HUB_HARDWARE_HANDLE = 0x0E


class Connection:
    def connect(self, hub_mac=None):
        pass

    @abstractmethod
    def is_alive(self):
        pass

    def disconnect(self):
        pass

    @abstractmethod
    def write(self, handle, data):
        pass

    @abstractmethod
    def set_notify_handler(self, handler):
        pass

    def enable_notifications(self):
        self.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

    def _is_device_matched(self, address, dev_name, hub_mac, find_name):
        assert hub_mac or find_name, 'You have to provide either hub_mac or hub_name in connection options'
        log.debug("Checking device: %s, MAC: %s", dev_name, address)
        matched = False
        if address != "00:00:00:00:00:00":
            if hub_mac:
                if hub_mac.lower() == address.lower():
                    matched = True
            elif dev_name == find_name:
                matched = True

            if matched:
                log.info("Found %s at %s", dev_name, address)

        return matched


class DebugServer:
    """
    WARNING: deprecated class
    Starts TCP server to be used with DebugServerConnection to speed-up development process
    It holds BLE connection to Move Hub, so no need to re-start it every time
    Usage: DebugServer(BLEConnection().connect()).start()

    :type connection: BLEConnection
    """

    def __init__(self, connection):
        self._running = False
        self.sock = socket.socket()
        self.connection = connection

    def start(self, port=9090):
        self.sock.bind(('', port))
        self.sock.listen(1)

        self._running = True
        while self._running:
            log.info("Accepting MoveHub debug connections at %s", port)
            conn, addr = self.sock.accept()
            if not self._running:
                raise KeyboardInterrupt("Shutdown")
            self.connection.set_notify_handler(lambda x, y: self._notify(conn, x, y))
            try:
                self._handle_conn(conn)
            except KeyboardInterrupt:
                raise
            except BaseException:
                log.error("Problem handling incoming connection: %s", traceback.format_exc())
            finally:
                self.connection.set_notify_handler(self._notify_dummy)
                conn.close()

    def __del__(self):
        self.sock.close()

    def _notify_dummy(self, handle, data):
        log.debug("Dropped notification from handle %s: %s", handle, binascii.hexlify(data))
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
        if data[5] == MsgHubAction.TYPE:
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
                    log.debug("Cmd line: %s", line)
                    try:
                        self._handle_cmd(json.loads(line))
                    except KeyboardInterrupt:
                        raise
                    except BaseException:
                        log.error("Failed to handle cmd: %s", traceback.format_exc())

    def _handle_cmd(self, cmd):
        if cmd['type'] == 'write':
            self.connection.write(cmd['handle'], unhexlify(cmd['data']))
        else:
            raise ValueError("Unhandled cmd: %s", cmd)


class DebugServerConnection(Connection):
    """
    WARNING: deprecated class
    Connection type to be used with DebugServer, replaces BLEConnection
    """

    def __init__(self, port=9090):
        super().__init__()
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

    def is_alive(self):
        return self.reader.isAlive()
