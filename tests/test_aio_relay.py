import asyncio
import unittest
from unittest import mock

from pylgbst.aio.connection import Connection, RelayConnection
from pylgbst.aio.relay import Relay
from pylgbst.exceptions import HubError
from pylgbst.messages import frame_length, length_size, payload_offset

ATTACH_A = bytes.fromhex('0f0004000127000000001000000010')
ATTACH_AB = bytes.fromhex('090004100227000001')
DETACH_A = bytes.fromhex('0500040000')
FEEDBACK_A = bytes.fromhex('0500820001')

SUBSCRIBE_A = bytes.fromhex('0a004100020100000001')  # port A, mode 2, delta 1, updates on
TIMED_A = bytes.fromhex('0c0081001109900114647f03')
TIMED_AB = bytes.fromhex('0d008110110af401ecec647f03')
LED_COLOR = bytes.fromhex('0800813211510003')
BUTTON_ON = bytes.fromhex('0500010202')

HUB_PROPERTY_REPLIES = {  # recorded on a Move Hub
    bytes.fromhex('0500010105'): bytes.fromhex('12000101064c45474f204d6f766520487562'),  # name
    bytes.fromhex('0500010d05'): bytes.fromhex('0b00010d06001653a0d1d4'),  # mac
}


class FakeHub(Connection):
    def __init__(self, announce):
        super().__init__()
        self.announce = announce
        self.written = []
        self.on_frame = None

    async def start(self, on_frame):
        self.on_frame = on_frame
        for frame in self.announce:
            on_frame(frame)

    async def write(self, frame):
        self.written.append(frame)
        reply = HUB_PROPERTY_REPLIES.get(frame)
        if reply:
            self.on_frame(reply)

    async def disconnect(self):
        self.disconnected.set()


class RelayTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hubs = []
        self.failing_connects = 0
        self.relay = Relay(self._connect_hub)
        self.server = await asyncio.start_server(self.relay._serve_client, '127.0.0.1', 0)
        self.port = self.server.sockets[0].getsockname()[1]
        self.holder = asyncio.create_task(self.relay.hold_hub())

    async def asyncTearDown(self):
        self.holder.cancel()
        self.server.close()
        await self.server.wait_closed()

    async def _connect_hub(self):
        if self.failing_connects:
            self.failing_connects -= 1
            raise ConnectionError("br-connection-canceled")
        hub = FakeHub([ATTACH_A, ATTACH_AB])
        self.hubs.append(hub)
        return hub

    async def _client(self):
        received = []
        conn = await RelayConnection.connect('127.0.0.1', self.port)
        await conn.start(received.append)
        return conn, received

    @staticmethod
    async def _until(condition):
        for _ in range(200):
            if condition():
                return
            await asyncio.sleep(0.005)
        raise AssertionError("condition not met")

    async def test_replays_attachments_and_forwards_both_ways(self):
        conn, received = await self._client()
        await self._until(lambda: len(received) == 2)
        self.assertEqual([ATTACH_A, ATTACH_AB], received)

        await conn.write(TIMED_A)
        await self._until(lambda: self.hubs[0].written)
        self.assertEqual([TIMED_A], self.hubs[0].written)

        self.hubs[0].on_frame(FEEDBACK_A)
        await self._until(lambda: len(received) == 3)
        self.assertEqual(FEEDBACK_A, received[2])
        await conn.disconnect()

    async def test_detach_is_not_replayed(self):
        await self._until(lambda: self.hubs)
        self.hubs[0].on_frame(DETACH_A)
        conn, received = await self._client()
        await self._until(lambda: received)
        await asyncio.sleep(0.02)
        self.assertEqual([ATTACH_AB], received)
        await conn.disconnect()

    async def test_undoes_client_state_on_exit(self):
        conn, received = await self._client()
        for frame in (SUBSCRIBE_A, TIMED_A, TIMED_AB, LED_COLOR, BUTTON_ON):
            await conn.write(frame)
        await self._until(lambda: len(self.hubs[0].written) == 5)
        await conn.disconnect()

        await self._until(lambda: len(self.hubs[0].written) == 9)
        self.assertEqual({
            bytes.fromhex('0a004100020100000000'),  # updates off for port A
            bytes.fromhex('07008100110100'),  # A: power 0
            bytes.fromhex('0800811011020000'),  # AB: grouped power 0
            bytes.fromhex('0500010203'),  # button updates off
        }, set(self.hubs[0].written[5:]))

    async def test_new_client_takes_over(self):
        first, _ = await self._client()
        await first.write(TIMED_A)
        await self._until(lambda: self.hubs[0].written)

        second, received = await self._client()
        await self._until(lambda: first.disconnected.is_set())
        await self._until(lambda: len(received) == 2)
        self.assertIn(bytes.fromhex('07008100110100'), self.hubs[0].written)  # first's motor stopped
        await second.disconnect()

    async def test_hub_loss_drops_client_and_reconnects(self):
        conn, _ = await self._client()
        await self._until(lambda: self.hubs)
        self.hubs[0].disconnected.set()
        await self._until(lambda: conn.disconnected.is_set())
        await self._until(lambda: len(self.hubs) == 2)

    async def test_answers_disconnect_and_keeps_hub(self):
        conn, received = await self._client()
        await self._until(lambda: len(received) == 2)
        await conn.write(bytes.fromhex('04000202'))
        await self._until(lambda: len(received) == 3)
        self.assertEqual(bytes.fromhex('04000231'), received[2])
        self.assertEqual([], self.hubs[0].written)
        await conn.disconnect()

    async def test_retries_failed_hub_connect(self):
        self.holder.cancel()
        self.failing_connects = 2
        with mock.patch('pylgbst.aio.relay.RECONNECT_PAUSE', 0):
            self.holder = asyncio.create_task(self.relay.hold_hub())
            await self._until(lambda: self.hubs)

    async def test_checks_the_held_hub(self):
        conn = await RelayConnection.connect('127.0.0.1', self.port, hub_mac='00:16:53:A0:D1:D4')
        received = []
        await conn.start(received.append)
        await self._until(lambda: len(received) == 3)  # frames read during the check are not lost
        self.assertEqual([ATTACH_A, ATTACH_AB], received[:2])
        await conn.disconnect()

        conn = await RelayConnection.connect('127.0.0.1', self.port, hub_name='LEGO Move Hub')
        await conn.disconnect()

    async def test_refuses_another_hub(self):
        with self.assertRaisesRegex(HubError, "00:16:53:a0:d1:d4"):
            await RelayConnection.connect('127.0.0.1', self.port, hub_mac='AA:BB:CC:DD:EE:FF')
        with self.assertRaisesRegex(HubError, "LEGO Move Hub"):
            await RelayConnection.connect('127.0.0.1', self.port, hub_name='Smart Hub')


class FramingTest(unittest.TestCase):
    def test_short_frame(self):
        frame = bytes.fromhex('0500820001')
        self.assertEqual(1, length_size(frame[0]))
        self.assertEqual(5, frame_length(frame))
        self.assertEqual(3, payload_offset(frame))

    def test_extended_frame(self):
        frame = bytes([0x82, 0x01]) + bytes(128)  # 0x02 | 0x01 << 7 = 130
        self.assertEqual(2, length_size(frame[0]))
        self.assertEqual(130, frame_length(frame))
        self.assertEqual(4, payload_offset(frame))
