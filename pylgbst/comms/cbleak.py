import asyncio
import logging
import queue
import threading
import time

from pylgbst.comms import Connection, LEGO_MOVE_HUB, MOVE_HUB_HW_UUID_CHAR
from bleak import discover
from bleak import BleakClient
from bleak.backends.device import BLEDevice

log = logging.getLogger('comms-bleak')

# Queues to handle request / responses. Acts as a buffer between API and async BLE driver
resp_queue = queue.Queue()
req_queue = queue.Queue()


class BleakDriver(object):

    def __init__(self, hub_mac=None):
        self.hub_mac = hub_mac
        self._handler = None
        self._abort = False
        self._connection_thread = None
        self._processing_thread = None

    def set_notify_handler(self, handler):
        self._handler = handler

    def enable_notifications(self):
        self._connection_thread = threading.Thread(target=lambda: asyncio.run(self._bleak_thread()))
        self._connection_thread.daemon = True
        self._connection_thread.start()

        self._processing_thread = threading.Thread(target=self._processing)
        self._processing_thread.daemon = True
        self._processing_thread.start()

    async def _bleak_thread(self):
        bleak = BleakConnection()
        await bleak.connect(self.hub_mac)
        await bleak.set_notify_handler(self._safe_handler)
        # After connecting, need to send any data or hub will drop the connection,
        # below command is Advertising name request update
        await bleak.write_char(MOVE_HUB_HW_UUID_CHAR, bytearray([0x05, 0x00, 0x01, 0x01, 0x05]))
        while not self._abort:
            await asyncio.sleep(0.1)
            if req_queue.qsize() != 0:
                data = req_queue.get()
                await bleak.write(data[0], data[1])

    @staticmethod
    def _safe_handler(handler, data):
        resp_queue.put((handler, data))

    def _processing(self):
        while not self._abort:
            if resp_queue.qsize() != 0:
                msg = resp_queue.get()
                self._handler(msg[0], msg[1])

            time.sleep(0.1)

    def write(self, handle, data):
        if not self._connection_thread.is_alive() or not self._processing_thread.is_alive():
            raise ConnectionError('Something went wrong, communication threads not functioning.')

        req_queue.put((handle, data))

    def disconnect(self):
        self._abort = True

    def is_alive(self):
        if self._connection_thread is not None and self._processing_thread is not None:
            return self._connection_thread.is_alive() and self._processing_thread.is_alive()
        else:
            return False


class BleakConnection(Connection):
    def is_alive(self):
        pass

    def __init__(self):
        Connection.__init__(self)
        self.loop = asyncio.get_event_loop()

        self._device: BLEDevice = None
        self._client: BleakClient = None
        logging.getLogger('bleak.backends.dotnet.client').setLevel(logging.getLogger().level)

    async def connect(self, hub_mac=None):
        log.info("Discovering devices... Press Green button on lego MoveHub")
        devices = await discover()
        log.debug("Devices: %s", devices)

        for dev in devices:
            log.debug(dev)
            address = dev.address
            name = dev.name
            if self._is_device_matched(address, name, hub_mac):
                log.info('DEVICE MATCHED')
                self._device = dev
                break

        if not self._device:
            raise ConnectionError('Device not found.')

        self._client = BleakClient(self._device.address, self.loop)
        status = await self._client.connect()
        log.debug(f'Connection status: {status}')

    async def write(self, handle, data):
        log.debug(f'REQ {handle} {[hex(x) for x in data]}')
        desc = self._client.services.get_descriptor(handle)
        if desc is None:
            # dedicated handle not found, try to send by using LEGO Move Hub default characteristic
            await self._client.write_gatt_char(MOVE_HUB_HW_UUID_CHAR, data)
        else:
            await self._client.write_gatt_char(desc.characteristic_uuid, data)

    async def write_char(self, characteristic_uuid, data):
        await self._client.write_gatt_char(characteristic_uuid, data)

    async def set_notify_handler(self, handler):
        def c(handle, data):
            log.debug(f'RSP {handle} {[hex(x) for x in data]}')
            handler(handle, data)
        await self._client.start_notify(MOVE_HUB_HW_UUID_CHAR, c)
