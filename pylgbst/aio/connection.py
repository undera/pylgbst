"""
Transport abstraction for raw LWP3 frames, and the relay client. No BLE dependency here.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from pylgbst.exceptions import HubError
from pylgbst.messages import MsgHubProperties, decode_upstream, frame_length, length_size

log = logging.getLogger(__name__)

RELAY_HOST = '127.0.0.1'
RELAY_PORT = 9090

FrameHandler = Callable[[bytes], None]


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    """
    Read one LWP3 frame from a byte stream

    :raises asyncio.IncompleteReadError: on end of stream
    """
    length_field = await reader.readexactly(1)
    length_field += await reader.readexactly(length_size(length_field[0]) - 1)
    return length_field + await reader.readexactly(frame_length(length_field) - len(length_field))


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
        self._early: List[bytes] = []  # read before start(), delivered by it

    @classmethod
    async def connect(cls, host: str = RELAY_HOST, port: int = RELAY_PORT, hub_mac: Optional[str] = None,
                      hub_name: Optional[str] = None) -> 'RelayConnection':
        """
        :param hub_mac: fail unless the relay holds the hub with this address; takes precedence over `hub_name`
        :param hub_name: fail unless the relay holds a hub advertising this name
        :raises HubError: the relay holds another hub
        """
        reader, writer = await asyncio.open_connection(host, port)
        log.info("Connected to relay at %s:%s", host, port)
        conn = cls(reader, writer)
        try:
            await conn._check_hub(hub_mac, hub_name)
        except BaseException:
            await conn.disconnect()
            raise
        return conn

    async def _check_hub(self, hub_mac: Optional[str], hub_name: Optional[str]) -> None:
        if hub_mac:
            held = (await self._hub_property(MsgHubProperties.PRIMARY_MAC)).hex(':')
            if held.lower() != hub_mac.lower():
                raise HubError("Relay holds hub %s, not the requested %s" % (held, hub_mac))
        elif hub_name:
            held = (await self._hub_property(MsgHubProperties.ADVERTISE_NAME)).decode()
            if held != hub_name:
                raise HubError("Relay holds hub %r, not the requested %r" % (held, hub_name))

    async def _hub_property(self, prop: int) -> bytes:
        request = MsgHubProperties(prop, MsgHubProperties.UPD_REQUEST)
        await self.write(request.bytes())
        while True:
            try:
                frame = await read_frame(self._reader)
            except asyncio.IncompleteReadError as exc:
                raise ConnectionError("Relay closed the connection") from exc
            self._early.append(frame)
            try:
                msgs = decode_upstream(frame)
            except Exception:  # the hub will get the frame on start(); here it only is not the reply
                log.exception("Undecodable frame while waiting for hub property: %s", frame.hex())
                continue
            for msg in msgs:
                if request.is_reply(msg):
                    return msg.parameters

    async def start(self, on_frame: FrameHandler) -> None:
        for frame in self._early:
            on_frame(frame)
        self._early.clear()
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
