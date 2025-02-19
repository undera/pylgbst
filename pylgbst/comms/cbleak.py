import asyncio
import logging
import platform
import queue
import threading
import time

import bleak

from pylgbst.comms import Connection, MOVE_HUB_HW_UUID_CHAR, MOVE_HUB_HW_UUID_SERV

log = logging.getLogger('comms-bleak')


class BleakDriver(Connection):
    """Driver that provides interface between API and Bleak."""

    def __init__(self, hub_mac=None, hub_name=None):
        """
        Initialize new object of Bleak Driver class.

        :param hub_mac: Optional Lego HUB MAC to connect to.
        """
        self.hub_mac = hub_mac
        self.hub_name = hub_name
        self._handler = None
        self._abort = False
        self._connection_thread = None
        self._processing_thread = None

        # Queues to handle request / responses. Acts as a buffer between API and async BLE driver
        self.resp_queue = queue.Queue()
        self.req_queue = queue.Queue()

    def set_notify_handler(self, handler):
        """
        Set handler function used to communicate with an API.

        :param handler: Handler function called by driver when received data
        :return: None
        """
        self._handler = handler

    def enable_notifications(self):
        """
        Enable notifications, in our cases starts communication threads.

        We cannot do this earlier, because API need to fist set notification handler.
        :return: None
        """
        self._connection_thread = threading.Thread(target=lambda: asyncio.run(self._bleak_thread()))
        self._connection_thread.daemon = True
        self._connection_thread.start()

        self._processing_thread = threading.Thread(target=self._processing)
        self._processing_thread.daemon = True
        self._processing_thread.start()

    async def _bleak_thread(self):
        bleak = BleakConnection()
        # For MacOS 12+ the service_uuids kwarg is required for scanning
        kwargs = {}
        if "Darwin" == platform.system() and int(platform.mac_ver()[0].split(".")[0]) >= 12:
            kwargs = {"service_uuids": [MOVE_HUB_HW_UUID_SERV]}
        await bleak.connect(self.hub_mac, self.hub_name, **kwargs)
        await bleak.set_notify_handler((self._safe_handler, self.resp_queue))
        # After connecting, need to send any data or hub will drop the connection,
        # below command is Advertising name request update
        await bleak.write_char(MOVE_HUB_HW_UUID_CHAR, bytearray([0x05, 0x00, 0x01, 0x01, 0x05]))
        while not self._abort:
            await asyncio.sleep(0.1)
            if self.req_queue.qsize() != 0:
                data = self.req_queue.get()
                await bleak.write(data[0], data[1])

        logging.info("Communications thread has exited")

    @staticmethod
    def _safe_handler(handler, data, resp_queue):
        resp_queue.put((handler, data))

    def _processing(self):
        while not self._abort:
            if self.resp_queue.qsize() != 0:
                msg = self.resp_queue.get()
                self._handler(msg[0], bytes(msg[1]))

            time.sleep(0.01)
        logging.info("Processing thread has exited")

    def write(self, handle, data):
        """
        Send data to given handle number.

        :param handle: Handle number that will be translated into characteristic uuid
        :param data: data to send
        :raises ConnectionError" When internal threads are not working
        :return: None
        """
        if not self._connection_thread.is_alive() or not self._processing_thread.is_alive():
            raise ConnectionError('Something went wrong, communication threads not functioning.')

        self.req_queue.put((handle, data))

    def disconnect(self):
        """
        Disconnect and stops communication threads.

        :return: None
        """
        self._abort = True

    def is_alive(self):
        """
        Indicate whether driver is functioning or not.

        :return: True if driver is functioning; False otherwise.
        """
        if self._connection_thread is not None and self._processing_thread is not None:
            return self._connection_thread.is_alive() and self._processing_thread.is_alive()
        else:
            return False

class BleakConnection(Connection):
    """Bleak driver for communicating with BLE device."""

    def __init__(self):
        """Initialize new instance of BleakConnection class."""
        Connection.__init__(self)

        self._device = None
        self._client = None
        logging.getLogger('bleak.backends.dotnet.client').setLevel(logging.WARNING)
        logging.getLogger('bleak.backends.bluezdbus.client').setLevel(logging.WARNING)

    async def find_device(self, hub_mac=None, hub_name=None):
        found_event = asyncio.Event()
        found_device = None

        async def _detect(device: bleak.BLEDevice, advertisement_data: bleak.AdvertisementData):
            nonlocal found_device
            nonlocal found_event
            address = device.address
            name = device.name
            if self._is_device_matched(address, name, hub_mac, hub_name):
                log.info('Device matched: %r', device)
                found_device = device
                found_event.set()
        
        scanner = bleak.BleakScanner(
            detection_callback=_detect
        )
        await scanner.start()
        await found_event.wait()
        await scanner.stop()
        return found_device

    async def connect(self, hub_mac=None, hub_name=None, **kwargs):
        """
        Connect to device.

        :param hub_mac: Optional Lego HUB MAC to connect to
        :param hub_name: Optional Lego Hub name to connect to
        :kwargs: Optional parameters for bleak.discover

        :raises ConnectionError: When cannot connect to given MAC or name matching fails.
        :return: None
        """
        log.info("Discovering devices... Press green button on Hub")

        self._device = await self.find_device(hub_mac, hub_name, **kwargs)

        self._client = bleak.BleakClient(self._device)
        status = await self._client.connect()
        log.debug('Connection status: {status}'.format(status=status))

    async def write(self, handle, data):
        """
        Send data to given handle number.

        If handle cannot be found in service description, hardcoded LEGO uuid will be used.
        :param handle: Handle number that will be translated into characteristic uuid
        :param data: data to send
        :return: None
        """
        log.debug('Request: {handle} {payload}'.format(handle=handle, payload=[hex(x) for x in data]))
        desc = self._client.services.get_descriptor(handle)

        if not isinstance(data, bytearray):
            data = bytearray(data)

        if desc is None:
            # dedicated handle not found, try to send by using LEGO Move Hub default characteristic
            await self._client.write_gatt_char(MOVE_HUB_HW_UUID_CHAR, data)
        else:
            await self._client.write_gatt_char(desc.characteristic_uuid, data)

    async def write_char(self, characteristic_uuid, data):
        """
        Send data to given handle number.

        :param characteristic_uuid: Characteristic uuid used to send data
        :param data: data to send
        :return: None
        """
        await self._client.write_gatt_char(characteristic_uuid, data)

    async def set_notify_handler(self, inputs):
        """
        Set notification handler.

        :param handler: Handle function to be called when receive any data.
        :return: None
        """
        handler, resp_queue = inputs

        def c(handle, data):
            log.debug('Response: {handle} {payload}'.format(handle=handle, payload=[hex(x) for x in data]))
            handler(handle, data, resp_queue)

        await self._client.start_notify(MOVE_HUB_HW_UUID_CHAR, c)

    def is_alive(self):
        """
        To keep compatibility with the driver interface.

        This method does nothing.
        :return: None.
        """
        pass
