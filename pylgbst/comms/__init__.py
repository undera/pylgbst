"""
Connections for the blocking API. The async core does the work; these bridge to it.
"""
import asyncio
import atexit
import logging
from abc import abstractmethod

from pylgbst.aio import connection as aio_connection
from pylgbst.aio.loop_thread import LoopThread

log = logging.getLogger('comms')

ENABLE_NOTIFICATIONS_HANDLE = 0x000f
ENABLE_NOTIFICATIONS_VALUE = b'\x01\x00'

MOVE_HUB_HARDWARE_HANDLE = 0x0E


class Connection:
    """
    A blocking transport. Implement it to plug a custom transport (or a test double)
    into the blocking API; it gets adapted to the async core with `BlockingConnectionAdapter`.
    """

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


class AsyncBackedConnection(Connection):
    """
    An async core connection, held for the blocking API: what `get_connection_*()` return.
    The hub talks to `aio` directly; this object only answers `is_alive()` and `disconnect()`.
    """

    def __init__(self, loop_thread: LoopThread, aio: aio_connection.Connection):
        self.loop_thread = loop_thread
        self.aio = aio
        atexit.register(self._disconnect_at_exit)

    def is_alive(self):
        return not self.aio.disconnected.is_set()

    def disconnect(self):
        self.loop_thread.run(self.aio.disconnect())

    def write(self, handle, data):
        raise NotImplementedError("The hub writes to the async connection directly")

    def set_notify_handler(self, handler):
        raise NotImplementedError("The hub reads from the async connection directly")

    def _disconnect_at_exit(self):
        if self.is_alive():
            try:
                self.disconnect()
            except Exception:
                log.exception("Failed to disconnect at exit")


class BlockingConnectionAdapter(aio_connection.Connection):
    """Runs a blocking `Connection` under the async core"""

    def __init__(self, connection: Connection):
        super().__init__()
        self._connection = connection

    async def start(self, on_frame):
        loop = asyncio.get_running_loop()
        self._connection.set_notify_handler(lambda _handle, data: loop.call_soon_threadsafe(on_frame, bytes(data)))
        self._connection.enable_notifications()

    async def write(self, frame):
        self._connection.write(MOVE_HUB_HARDWARE_HANDLE, frame)

    async def disconnect(self):
        self._connection.disconnect()
        self.disconnected.set()


def to_async(connection: Connection) -> aio_connection.Connection:
    if isinstance(connection, AsyncBackedConnection):
        return connection.aio
    return BlockingConnectionAdapter(connection)
