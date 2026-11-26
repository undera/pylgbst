"""
Holds the BLE connection to a hub between script runs, so experiments need no power-up each time.

    python3 -m pylgbst.aio.relay [--name "LEGO Move Hub"] [--mac 00:16:53:...]

Scripts reach it with `pylgbst.aio.ble.connect()` or the sync `get_connection_auto()`, both prefer a running relay.
One script is served at a time; a new one takes over from the previous. For each script the relay:
- replays the attached-IO announcements the hub sent once, at connection time;
- on its exit, stops the motors it drove and switches off the value updates it enabled.
"""
import argparse
import asyncio
import logging
from struct import pack
from typing import Awaitable, Callable, Dict, Optional, Set

from pylgbst.messages import (
    MsgHubAttachedIO, MsgHubProperties, MsgPortInputFmtSetupSingle, MsgPortOutput, payload_offset,
)
from pylgbst.peripherals import Motor

from .ble import BleakConnection
from .connection import Connection, RELAY_HOST, RELAY_PORT, read_frame

log = logging.getLogger(__name__)

class ClientState:
    """What a script switched on at the hub, so that it can be switched off after the script is gone"""

    def __init__(self):
        self.updating_ports: Dict[int, int] = {}  # port -> mode with value updates enabled
        self.driven_ports: Set[int] = set()
        self.button_updates = False

    def track(self, frame: bytes) -> None:
        offset = payload_offset(frame)
        msg_type, payload = frame[offset - 1], frame[offset:]
        if msg_type == MsgPortInputFmtSetupSingle.TYPE:  # payload: port, mode, delta(4), update_enable
            port, mode, enabled = payload[0], payload[1], payload[6]
            if enabled:
                self.updating_ports[port] = mode
            else:
                self.updating_ports.pop(port, None)
        elif msg_type == MsgPortOutput.TYPE:  # payload: port, startup/completion flags, subcommand, params
            port, subcommand = payload[0], payload[2]
            if subcommand not in (MsgPortOutput.WRITE_DIRECT, MsgPortOutput.WRITE_DIRECT_MODE_DATA):  # LEDs, encoders
                self.driven_ports.add(port)
        elif msg_type == MsgHubProperties.TYPE:
            msg = MsgHubProperties.decode(frame)
            if msg.property == MsgHubProperties.BUTTON:
                if msg.operation == MsgHubProperties.UPD_ENABLE:
                    self.button_updates = True
                elif msg.operation == MsgHubProperties.UPD_DISABLE:
                    self.button_updates = False

    def undo_frames(self, virtual_ports: Set[int]):
        for port, mode in self.updating_ports.items():
            yield MsgPortInputFmtSetupSingle(port, mode, delta=1, update_enable=0).bytes()
        for port in self.driven_ports:
            if port in virtual_ports:
                yield MsgPortOutput(port, Motor.SUBCMD_START_POWER_GROUPED, pack('<bb', 0, 0)).bytes()
            else:
                yield MsgPortOutput(port, Motor.SUBCMD_START_POWER, pack('<b', 0)).bytes()
        if self.button_updates:
            yield MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_DISABLE).bytes()


class Relay:
    def __init__(self, connect_hub: Callable[[], Awaitable[Connection]]):
        self._connect_hub = connect_hub
        self._hub: Optional[Connection] = None
        self._hub_ready = asyncio.Event()
        self._attached: Dict[int, MsgHubAttachedIO] = {}
        self._announcements: Dict[int, bytes] = {}  # port -> attach frame as the hub sent it, for replay
        self._client: Optional[asyncio.StreamWriter] = None
        self._client_gone: Optional[asyncio.Event] = None
        self._admission = asyncio.Lock()

    async def serve(self, host: str = RELAY_HOST, port: int = RELAY_PORT) -> None:
        server = await asyncio.start_server(self._serve_client, host, port)
        log.info("Relay listening on %s:%s", host, port)
        async with server:
            await self.hold_hub()

    async def hold_hub(self) -> None:
        """Keep a hub connected, reconnecting whenever it drops"""
        while True:
            self._attached.clear()
            self._announcements.clear()
            hub = await self._connect_hub()
            await hub.start(self._from_hub)
            self._hub = hub
            self._hub_ready.set()
            await hub.disconnected.wait()
            self._hub_ready.clear()
            self._hub = None
            if self._client:
                log.warning("Dropping the client: hub state it knew is gone")
                self._client.close()

    def _virtual_ports(self) -> Set[int]:
        return {port for port, msg in self._attached.items() if msg.event == MsgHubAttachedIO.EVENT_ATTACHED_VIRTUAL}

    def _from_hub(self, frame: bytes) -> None:
        if frame[payload_offset(frame) - 1] == MsgHubAttachedIO.TYPE:
            msg = MsgHubAttachedIO.decode(frame)
            if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
                self._attached.pop(msg.port, None)
                self._announcements.pop(msg.port, None)
            else:
                self._attached[msg.port] = msg
                self._announcements[msg.port] = frame
        if self._client:
            self._client.write(frame)

    async def _serve_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info('peername')
        async with self._admission:
            if self._client:
                log.info("Client %s takes over, closing the previous one", peer)
                self._client.close()
                await self._client_gone.wait()

            if not self._hub_ready.is_set():
                log.info("Client %s waits for the hub", peer)
                await self._hub_ready.wait()

            log.info("Client %s connected, replaying %s attach announcements", peer, len(self._announcements))
            for frame in self._announcements.values():  # synchronously with registering: no frame is missed or doubled
                writer.write(frame)
            self._client = writer
            self._client_gone = asyncio.Event()
            hub = self._hub

        state = ClientState()
        try:
            while True:
                frame = await read_frame(reader)
                state.track(frame)
                await hub.write(frame)
        except asyncio.IncompleteReadError:
            log.info("Client %s disconnected", peer)
        except OSError as exc:  # ConnectionError included, which BLE write failures raise too
            log.warning("Client %s dropped: %s", peer, exc)
        finally:
            self._client = None
            await self._undo(state)
            writer.close()
            self._client_gone.set()

    async def _undo(self, state: ClientState) -> None:
        if not self._hub_ready.is_set():
            return
        for frame in state.undo_frames(self._virtual_ports()):
            log.info("Cleaning up after client: %s", frame.hex())
            try:
                await self._hub.write(frame)
            except OSError as exc:
                log.warning("Cleanup write failed: %s", exc)
                return


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mac', help="hub address")
    parser.add_argument('--name', help="hub advertised name; with neither given, any LEGO hub matches")
    parser.add_argument('--host', default=RELAY_HOST)
    parser.add_argument('--port', type=int, default=RELAY_PORT)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    relay = Relay(lambda: BleakConnection.connect(args.mac, args.name))
    try:
        asyncio.run(relay.serve(args.host, args.port))
    except KeyboardInterrupt:
        log.info("Relay stopped")


if __name__ == '__main__':
    main()
