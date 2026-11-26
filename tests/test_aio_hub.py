"""Frames below were recorded on a Move Hub (see probe logs in the async rework)"""
import asyncio
import unittest

from pylgbst.aio.connection import Connection
from pylgbst.aio.hub import Hub
from pylgbst.exceptions import CommandDiscarded, CommandFailed, HubDisconnected, ReplyTimeout
from pylgbst.messages import MsgHubProperties, MsgPortInfoRequest, MsgPortOutput, MsgPortInfo

PORT_A, PORT_B, PORT_AB = 0x00, 0x01, 0x10


def timed(port):
    return MsgPortOutput(port, 0x09, bytes.fromhex('900114647f03'))


class FakeConnection(Connection):
    def __init__(self):
        super().__init__()
        self.written = []
        self.on_frame = None
        self.fail_writes = False

    async def start(self, on_frame):
        self.on_frame = on_frame

    async def write(self, frame):
        if self.fail_writes:
            raise ConnectionError("gone")
        self.written.append(frame)

    async def disconnect(self):
        self.disconnected.set()

    def hub_says(self, *hex_frames):
        for frame in hex_frames:
            self.on_frame(bytes.fromhex(frame))


class HubTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.conn = FakeConnection()
        self.hub = Hub(self.conn, request_timeout=0.2)
        await self.hub.start()

    async def asyncTearDown(self):
        await self.hub.close()

    async def _started(self, coro):
        """Run a hub call in the background until it has written its command"""
        sent = len(self.conn.written)
        task = asyncio.create_task(coro)
        while len(self.conn.written) == sent and not task.done():
            await asyncio.sleep(0)
        return task

    async def test_request_reply(self):
        task = await self._started(self.hub.request(MsgHubProperties(MsgHubProperties.VOLTAGE_PERC,
                                                                     MsgHubProperties.UPD_REQUEST)))
        self.conn.hub_says('060001060664')
        reply = await task
        self.assertEqual(b'\x64', reply.parameters)

    async def test_concurrent_requests_resolve_by_content(self):
        info_a = await self._started(self.hub.request(MsgPortInfoRequest(PORT_A, MsgPortInfoRequest.INFO_MODE_INFO)))
        info_b = await self._started(self.hub.request(MsgPortInfoRequest(PORT_B, MsgPortInfoRequest.INFO_MODE_INFO)))
        self.conn.hub_says('0b004301010f0306000700', '0b004300010f0306000700')  # B answered first
        self.assertEqual(PORT_A, (await info_a).port)
        self.assertEqual(PORT_B, (await info_b).port)
        self.assertIsInstance(await info_a, MsgPortInfo)

    async def test_output_waits_for_completion(self):
        task = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820001')
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.conn.hub_says('050082000a')
        await task

    async def test_output_without_waiting_returns_on_start(self):
        task = await self._started(self.hub.output(timed(PORT_A), wait_complete=False))
        self.conn.hub_says('0500820001')
        await task

    async def test_interrupted_output_raises(self):
        first = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820001')
        second = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820005', '050082000a')  # in progress + discarded, then completed
        with self.assertRaises(CommandDiscarded):
            await first
        await second

    async def test_overlapping_port_interrupt(self):
        ab = await self._started(self.hub.output(timed(PORT_AB)))
        self.conn.hub_says('0500821001')
        a = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('070082100c0001', '050082000a')  # multi-port: AB discarded, A in progress
        with self.assertRaises(CommandDiscarded):
            await ab
        await a

    async def test_rejected_output(self):
        task = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820004')
        with self.assertRaises(CommandDiscarded):
            await task

    async def test_stalled_output(self):
        task = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820001', '050082000c')  # in progress, then discarded with nothing taking over
        with self.assertRaisesRegex(CommandDiscarded, 'gave up'):
            await task

    async def test_completes_without_progress_report(self):
        task = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('050082000a')  # seen for an unknown subcommand
        await task

    async def test_errors_go_to_oldest_command_of_their_type(self):
        bad1 = await self._started(self.hub.output(MsgPortOutput(0x2F, 0x09, b'')))
        good_a = await self._started(self.hub.output(timed(PORT_A), wait_complete=False))
        bad2 = await self._started(self.hub.output(MsgPortOutput(0x2E, 0x09, b'')))
        good_b = await self._started(self.hub.output(timed(PORT_B), wait_complete=False))
        self.conn.hub_says('0500058106', '0500820001', '0500058106', '0500820101')  # recorded order
        with self.assertRaises(CommandFailed):
            await bad1
        with self.assertRaises(CommandFailed):
            await bad2
        await good_a
        await good_b

    async def test_timeout(self):
        with self.assertRaises(ReplyTimeout):
            await self.hub.request(MsgPortInfoRequest(PORT_A, MsgPortInfoRequest.INFO_MODE_INFO))
        self.conn.hub_says('0b004300010f0306000700')  # late reply is ignored, nothing breaks

    async def test_disconnect_fails_pending_and_later_calls(self):
        running = await self._started(self.hub.output(timed(PORT_A)))
        self.conn.hub_says('0500820001')
        self.conn.disconnected.set()
        with self.assertRaises(HubDisconnected):
            await running
        with self.assertRaises(HubDisconnected):
            await self.hub.output(timed(PORT_B))

    async def test_write_failure(self):
        self.conn.fail_writes = True
        with self.assertRaises(HubDisconnected):
            await self.hub.output(timed(PORT_A))

    async def test_hub_switch_off(self):
        task = await self._started(self.hub.switch_off())
        self.conn.hub_says('04000230')
        await task
        with self.assertRaises(HubDisconnected):
            await self.hub.output(timed(PORT_A))

    async def test_bad_frame_does_not_break_dispatch(self):
        self.conn.hub_says('0500ee0000')  # unknown type
        task = await self._started(self.hub.output(timed(PORT_A), wait_complete=False))
        self.conn.hub_says('0500820001')
        await task


MOVE_HUB_ATTACH = [
    '0f0004000127000000001000000010', '0f0004010127000000001000000010', '0f0004020125000000001000000010',
    '0f0004030126000000001000000010', '090004100227000001', '0f0004320117000000000106000020',
    '0f00043a0128000000001000000102', '0f00043b0115000200000000000100', '0f00043c0114000200000000000100',
]


class AnnouncingConnection(FakeConnection):
    """Announces Move Hub devices on start and answers the status requests MoveHub makes"""

    def __init__(self, announce=MOVE_HUB_ATTACH):
        super().__init__()
        self.announce = announce
        self.replies = {}  # written frame hex -> reply frames hex

    async def start(self, on_frame):
        await super().start(on_frame)
        asyncio.get_running_loop().call_soon(self.hub_says, *self.announce)

    async def write(self, frame):
        await super().write(frame)
        replies = self.replies.get(frame.hex(), ())
        if replies:
            asyncio.get_running_loop().call_soon(self.hub_says, *replies)


def move_hub_connection(announce=MOVE_HUB_ATTACH):
    conn = AnnouncingConnection(announce)
    conn.replies = {
        '0500010105': ['12000101064c45474f204d6f766520487562'],
        '0500010d05': ['0b00010d06001653a0d1d4'],
        '0500010605': ['060001060664'],
        '0500030103': ['060003010400'],
    }
    return conn


class MoveHubTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_finds_devices(self):
        from pylgbst.aio.hub import MoveHub
        from pylgbst.aio.peripherals import EncodedMotor, VisionSensor
        async with MoveHub(move_hub_connection(), request_timeout=0.2) as hub:
            self.assertIsInstance(hub.motor_A, EncodedMotor)
            self.assertEqual((0x00, 0x01), hub.motor_AB.virtual_ports)
            self.assertIsInstance(hub.vision_sensor, VisionSensor)
            self.assertIsInstance(hub.motor_external, EncodedMotor)

    async def test_missing_builtin_devices_raise(self):
        from pylgbst.aio.hub import MoveHub
        from pylgbst.exceptions import HubError
        hub = MoveHub(move_hub_connection(MOVE_HUB_ATTACH[:3]), devices_timeout=0.1)
        with self.assertRaisesRegex(HubError, "0x10"):
            await hub.start()
        await hub.close()

    async def test_values_iteration_toggles_updates(self):
        from pylgbst.aio.hub import MoveHub
        conn = move_hub_connection()
        conn.replies['0a004100020100000001'] = ['0a004700020100000001']  # angle mode, updates on
        conn.replies['0a004100020100000000'] = ['0a004700020100000000']  # updates off
        async with MoveHub(conn, request_timeout=0.2) as hub:
            angles = []

            async def read_two():
                async for (angle,) in hub.motor_A.values():
                    angles.append(angle)
                    if len(angles) == 2:
                        break

            reader = asyncio.create_task(read_two())
            while not hub.motor_A.port_mode.upd_enabled:
                await asyncio.sleep(0)
            conn.hub_says('0800450010000000')
            await asyncio.sleep(0)
            conn.hub_says('0800450020000000')
            await reader
            self.assertEqual([16, 32], angles)
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertFalse(hub.motor_A.port_mode.upd_enabled)

    async def test_callbacks_sync_and_async(self):
        from pylgbst.aio.hub import MoveHub
        conn = move_hub_connection()
        conn.replies['0a00413a020100000001'] = ['0a00473a020100000001']
        async with MoveHub(conn, request_timeout=0.2) as hub:
            got = []

            async def async_cb(state):
                await asyncio.sleep(0)
                got.append(('async', state))

            await hub.tilt_sensor.subscribe(lambda state: got.append(('sync', state)))
            await hub.tilt_sensor.subscribe(async_cb)
            conn.hub_says('0500453a05')
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertEqual({('sync', 5), ('async', 5)}, set(got))

    async def test_disconnect_ends_value_iteration(self):
        from pylgbst.aio.hub import MoveHub
        conn = move_hub_connection()
        conn.replies['0a004100020100000001'] = ['0a004700020100000001']
        async with MoveHub(conn, request_timeout=0.2) as hub:
            async def iterate():
                async for _ in hub.motor_A.values():
                    pass

            reader = asyncio.create_task(iterate())
            while not hub.motor_A.port_mode.upd_enabled:
                await asyncio.sleep(0)
            conn.disconnected.set()
            with self.assertRaises(HubDisconnected):  # switching updates off fails: the hub is gone
                await asyncio.wait_for(reader, 1)

    async def test_button_skips_state_reply_and_keeps_presses(self):
        from pylgbst.aio.hub import MoveHub
        conn = move_hub_connection()
        conn.replies['0500010202'] = ['060001020600']  # current state: released
        async with MoveHub(conn, request_timeout=0.2) as hub:
            presses = []
            await hub.button.subscribe(presses.append)
            conn.hub_says('060001020601', '060001020600')
            for _ in range(5):
                await asyncio.sleep(0)
            self.assertEqual([1, 0], presses)
