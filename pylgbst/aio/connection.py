"""
Transport abstraction for raw LWP3 frames, and the relay client. No BLE dependency here.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Optional

log = logging.getLogger(__name__)

RELAY_HOST = '127.0.0.1'
RELAY_PORT = 9090

FrameHandler = Callable[[bytes], None]


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    """
    Read one LWP3 frame from a byte stream. Frames carry their own total length:
    one byte, or two bytes when the high bit of the first one is set.

    :raises asyncio.IncompleteReadError: on end of stream
    """
    header = await reader.readexactly(1)
    length = header[0]
    if length & 0x80:
        header += await reader.readexactly(1)
        length = (length & 0x7F) | (header[1] << 7)
    return header + await reader.readexactly(length - len(header))


class Connection(ABC):
    """
    Transport to a single hub. Frames are delivered to the handler given to `start()`,
    on the event loop thread, in the order the hub sent them.
    """

    def __init__(self):
        self.disconnected = asyncio.Event()

    @abstractmethod
    async def start(self, on_frame: FrameHandler) -> None:
        """Begin delivering incoming frames. Frames that arrive earlier are not lost."""

    @abstractmethod
    async def write(self, frame: bytes) -> None:
        """:raises ConnectionError: when the frame cannot be delivered"""

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        await self.disconnect()


class RelayConnection(Connection):
    """Connection through `pylgbst.aio.relay`, which keeps the BLE link to the hub between script runs"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        super().__init__()
        self._reader = reader
        self._writer = writer
        self._reading: Optional[asyncio.Task] = None

    @classmethod
    async def connect(cls, host: str = RELAY_HOST, port: int = RELAY_PORT) -> 'RelayConnection':
        reader, writer = await asyncio.open_connection(host, port)
        log.info("Connected to relay at %s:%s", host, port)
        return cls(reader, writer)

    async def start(self, on_frame: FrameHandler) -> None:
        self._reading = asyncio.create_task(self._read(on_frame), name='relay reader')

    async def _read(self, on_frame: FrameHandler) -> None:
        try:
            while True:
                on_frame(await read_frame(self._reader))
        except asyncio.IncompleteReadError:
            log.warning("Relay closed the connection")
        except ConnectionError as exc:
            log.warning("Relay connection lost: %s", exc)
        finally:
            self.disconnected.set()

    async def write(self, frame: bytes) -> None:
        self._writer.write(frame)
        await self._writer.drain()

    async def disconnect(self) -> None:
        if self._reading:
            self._reading.cancel()
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except ConnectionError as exc:
            log.debug("Relay socket closed with: %s", exc)
        self.disconnected.set()
