"""
Holds the BLE connection to a hub between script runs, so experiments need no power-up each time.

    python3 -m pylgbst.aio.relay [--name "LEGO Move Hub"] [--mac 00:16:53:...]

Scripts reach it with `pylgbst.aio.ble.connect()` or the sync `get_connection_auto()`, both prefer a running relay.
One script is served at a time; a new one takes over from the previous. For each script the relay:
- replays the attached-IO announcements the hub sent once, at connection time;
- answers its request to disconnect the hub itself, keeping the hub connected;
- on its exit, stops the motors it drove and switches off the value updates it enabled.
The hub's LED shows it: blue while a script is served, red once it is gone.
"""
import argparse
import asyncio
import logging
import signal
from struct import pack
from typing import Awaitable, Callable, Dict, Optional, Set

from pylgbst.messages import (
    DevTypes, MsgHubAction, MsgHubAttachedIO, MsgHubProperties, MsgPortInputFmtSetupCombined,
    MsgPortInputFmtSetupSingle, MsgPortOutput, MsgPortOutputFeedback, decode_upstream, payload_offset,
)
from pylgbst.utilities import ushort

from .ble import BleakConnection
from .connection import Connection, RELAY_HOST, RELAY_PORT, read_frame
from .peripherals import COLOR_BLUE, COLOR_RED, LEDRGBConstants, MotorConstants

log = logging.getLogger(__name__)

RECONNECT_PAUSE = 1.0
LED_FEEDBACK_TIMEOUT = 1.0
LED_SERVING = pack('<BB', LEDRGBConstants.MODE_INDEX, COLOR_BLUE)  # the color of a hub with a connection
LED_IDLE = pack('<BB', LEDRGBConstants.MODE_INDEX, COLOR_RED)  # same mode as LED_SERVING: no mode switch
_DISCONNECT_REPLY = MsgHubAction(MsgHubAction.UPSTREAM_DISCONNECT).bytes()  # what the hub would answer


def _is_disconnect_request(frame: bytes) -> bool:
    offset = payload_offset(frame)
    return frame[offset - 1] == MsgHubAction.TYPE and frame[offset] == MsgHubAction.DISCONNECT

class ClientState:
    """What a script switched on at the hub, so that it can be switched off after the script is gone"""

    def __init__(self):
        self.updating_ports: Dict[int, int] = {}  # port -> mode with value updates enabled
        self.combined_ports: Set[int] = set()
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
        elif msg_type == MsgPortInputFmtSetupCombined.TYPE:  # payload: port, subcommand, ...
            port, subcommand = payload[0], payload[1]
            if subcommand == MsgPortInputFmtSetupCombined.SUB_UNLOCK_MULTI_UPDATE:
                self.combined_ports.add(port)
            elif subcommand == MsgPortInputFmtSetupCombined.SUB_RESET:
                self.combined_ports.discard(port)
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
        for port in self.combined_ports:
            yield MsgPortInputFmtSetupCombined(port, MsgPortInputFmtSetupCombined.SUB_RESET).bytes()
        for port, mode in self.updating_ports.items():
            yield MsgPortInputFmtSetupSingle(port, mode, delta=1, update_enable=0).bytes()
        for port in self.driven_ports:
            if port in virtual_ports:
                yield MsgPortOutput(port, MotorConstants.SUBCMD_START_POWER_GROUPED, pack('<bb', 0, 0)).bytes()
            else:
                yield MsgPortOutput(port, MotorConstants.SUBCMD_START_POWER, pack('<b', 0)).bytes()
        if self.button_updates:
            yield MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_DISABLE).bytes()


class Relay:
    def __init__(self, connect_hub: Callable[[], Awaitable[Connection]]):
        self._connect_hub = connect_hub
        self._hub: Optional[Connection] = None
        self._hub_ready = asyncio.Event()
        self._attached: Dict[int, MsgHubAttachedIO] = {}
        self._announcements: Dict[int, bytes] = {}  # port -> attach frame as the hub sent it, for replay
        self._led_port: Optional[int] = None
        self._led_done: Optional[asyncio.Event] = None  # the hub's feedback on the relay's LED command
        self._client: Optional[asyncio.StreamWriter] = None
        self._client_gone: Optional[asyncio.Event] = None
        self._admission = asyncio.Lock()

    async def serve(self, host: str = RELAY_HOST, port: int = RELAY_PORT) -> None:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, asyncio.current_task().cancel)  # as Ctrl+C
        server = await asyncio.start_server(self._serve_client, host, port)
        log.info("Relay listening on %s:%s", host, port)
        async with server:
            try:
                await self.hold_hub()
            finally:  # an abandoned link keeps the hub from advertising until BlueZ times it out
                if self._hub:
                    log.info("Disconnecting the hub")
                    await self._hub.disconnect()

    async def hold_hub(self) -> None:
        """Keep a hub connected, reconnecting whenever it drops"""
        while True:
            self._attached.clear()
            self._announcements.clear()
            self._led_port = None
            try:
                hub = await self._connect_hub()
                await hub.start(self._from_hub)
            except Exception:  # BlueZ fails connects now and then; keep trying, as a hub holder must
                log.exception("Failed to connect the hub, retrying")
                await asyncio.sleep(RECONNECT_PAUSE)
                continue
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
        msg_type = frame[payload_offset(frame) - 1]
        if msg_type == MsgHubAttachedIO.TYPE:
            msg = MsgHubAttachedIO.decode(frame)
            if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
                self._attached.pop(msg.port, None)
                self._announcements.pop(msg.port, None)
                if msg.port == self._led_port:
                    self._led_port = None
            else:
                self._attached[msg.port] = msg
                self._announcements[msg.port] = frame
                if ushort(msg.payload, 0) == DevTypes.RGB_LIGHT.value:
                    self._led_port = msg.port
        elif msg_type == MsgPortOutputFeedback.TYPE and self._led_done and not self._led_done.is_set():
            if [msg.port for msg in decode_upstream(frame)] == [self._led_port]:  # the relay's own, not a client's
                self._led_done.set()
                return
        if self._client:
            self._client.write(frame)

    async def _show(self, led_data: bytes) -> None:
        """Set the hub's LED, waiting for the hub's feedback so that no client gets it"""
        if self._led_port is None:
            return
        self._led_done = asyncio.Event()
        try:
            await self._hub.write(MsgPortOutput(self._led_port, MsgPortOutput.WRITE_DIRECT_MODE_DATA, led_data).bytes())
            await asyncio.wait_for(self._led_done.wait(), LED_FEEDBACK_TIMEOUT)
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("Failed to set the LED: %r", exc)
        finally:
            self._led_done = None

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

            await self._show(LED_SERVING)
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
                if _is_disconnect_request(frame):
                    log.info("Client %s asked to disconnect the hub: answering for it, the hub stays", peer)
                    writer.write(_DISCONNECT_REPLY)
                    continue
                state.track(frame)
                await hub.write(frame)
        except asyncio.IncompleteReadError:
            log.info("Client %s disconnected", peer)
        except OSError as exc:  # ConnectionError included, which BLE write failures raise too
            log.warning("Client %s dropped: %s", peer, exc)
        finally:
            self._client = None
            await self._undo(state)
            if self._hub_ready.is_set():
                await self._show(LED_IDLE)
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
