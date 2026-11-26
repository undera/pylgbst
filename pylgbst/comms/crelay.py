import logging
import socket
import traceback
from threading import Thread

from pylgbst.aio.connection import RELAY_HOST, RELAY_PORT
from pylgbst.comms import Connection, MOVE_HUB_HARDWARE_HANDLE

log = logging.getLogger('comms-relay')


class RelayConnection(Connection):
    """Sync connection through `pylgbst.aio.relay`, which keeps the BLE link to the hub between script runs"""

    def __init__(self, host=RELAY_HOST, port=RELAY_PORT):
        super().__init__()
        self._sock = socket.create_connection((host, port), timeout=1.0)
        self._sock.settimeout(None)
        self._stream = self._sock.makefile('rb')
        self._handler = None
        self._reader = Thread(target=self._read, name="Relay reader", daemon=True)
        log.info("Connected to relay at %s:%s", host, port)

    def set_notify_handler(self, handler):
        self._handler = handler

    def enable_notifications(self):
        self._reader.start()  # frames the relay sent so far wait in the socket buffer

    def _read_frame(self):
        header = self._stream.read(1)
        if not header:
            return None
        length = header[0]
        if length & 0x80:
            header += self._stream.read(1)
            length = (length & 0x7F) | (header[1] << 7)
        frame = header + self._stream.read(length - len(header))
        return frame if len(frame) == length else None

    def _read(self):
        while True:
            try:
                frame = self._read_frame()
            except OSError as exc:
                log.warning("Relay connection lost: %s", exc)
                return
            if frame is None:
                log.warning("Relay closed the connection")
                return
            try:
                self._handler(MOVE_HUB_HARDWARE_HANDLE, frame)
            except BaseException:
                log.error("Failed to handle frame %s: %s", frame.hex(), traceback.format_exc())

    def write(self, handle, data):
        self._sock.sendall(bytes(data))

    def disconnect(self):
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError as exc:
            log.debug("Relay socket shutdown: %s", exc)
        self._sock.close()

    def is_alive(self):
        return self._reader.is_alive()
