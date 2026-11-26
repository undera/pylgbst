import logging
import socket
import traceback
from threading import Thread

from pylgbst.aio.connection import RELAY_HOST, RELAY_PORT
from pylgbst.comms import Connection, MOVE_HUB_HARDWARE_HANDLE
from pylgbst.messages import frame_length, length_size

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
        """:return: next frame, or None when the stream has ended"""
        length_field = self._stream.read(1)
        if not length_field:
            return None
        length_field += self._stream.read(length_size(length_field[0]) - 1)
        if len(length_field) < length_size(length_field[0]):
            return None
        length = frame_length(length_field)
        frame = length_field + self._stream.read(length - len(length_field))
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
