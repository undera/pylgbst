"""
BLE transport via bleak
"""
import logging
import platform
import time
from typing import Optional

import bleak
from bleak.exc import BleakError

from .connection import Connection, FrameHandler, RelayConnection, RELAY_HOST, RELAY_PORT

log = logging.getLogger(__name__)

LEGO_HUB_SERVICE = '00001623-1212-efde-1623-785feabcd123'
LEGO_HUB_CHARACTERISTIC = '00001624-1212-efde-1623-785feabcd123'

# the hub drops a fresh connection unless it receives something: request the advertising name
_HELLO = bytes([0x05, 0x00, 0x01, 0x01, 0x05])
_SCAN_SLICE = 10.0


class BleakConnection(Connection):
    def __init__(self, client: bleak.BleakClient):
        super().__init__()
        self._client = client

    @classmethod
    async def connect(cls, hub_mac: Optional[str] = None, hub_name: Optional[str] = None,
                      timeout: Optional[float] = None, **scanner_kwargs) -> 'BleakConnection':
        """
        Scan until a matching hub shows up, then connect to it.

        :param hub_mac: match by address; takes precedence over `hub_name`
        :param hub_name: match by advertised name; with neither given, any LEGO hub matches
        :param timeout: seconds to keep scanning, None means forever
        :param scanner_kwargs: passed on to `bleak.BleakScanner`
        """
        if platform.system() == 'Darwin':  # CoreBluetooth reports nothing unless asked for a service
            scanner_kwargs.setdefault('service_uuids', [LEGO_HUB_SERVICE])

        def matches(device: bleak.BLEDevice, adv: bleak.AdvertisementData) -> bool:
            if hub_mac:
                return device.address.lower() == hub_mac.lower()
            if hub_name:
                return adv.local_name == hub_name or device.name == hub_name
            return LEGO_HUB_SERVICE in adv.service_uuids

        log.info("Scanning for hub (mac=%s, name=%s)... turn it on now", hub_mac, hub_name)
        deadline = None if timeout is None else time.monotonic() + timeout
        device = None
        while device is None:
            scan_for = _SCAN_SLICE if deadline is None else min(_SCAN_SLICE, deadline - time.monotonic())
            if scan_for <= 0:
                raise TimeoutError("No hub found (mac=%s, name=%s) within %ss" % (hub_mac, hub_name, timeout))
            device = await bleak.BleakScanner.find_device_by_filter(matches, timeout=scan_for, **scanner_kwargs)

        log.info("Found %s, connecting", device)
        conn = None

        def on_disconnect(_client):
            log.warning("Hub %s disconnected", device.address)
            if conn is not None:
                conn.disconnected.set()

        client = bleak.BleakClient(device, disconnected_callback=on_disconnect)
        await client.connect()
        conn = cls(client)
        log.info("Connected to %s", device)
        return conn

    async def start(self, on_frame: FrameHandler) -> None:
        await self._client.start_notify(LEGO_HUB_CHARACTERISTIC, lambda _char, data: on_frame(bytes(data)))
        await self.write(_HELLO)

    async def write(self, frame: bytes) -> None:
        log.debug("BLE write: %s", frame.hex())
        # without response: waiting for the GATT ack costs one connection interval (~75ms) per write
        try:
            await self._client.write_gatt_char(LEGO_HUB_CHARACTERISTIC, frame, response=False)
        except BleakError as exc:
            raise ConnectionError("BLE write failed: %s" % exc) from exc

    async def disconnect(self) -> None:
        await self._client.disconnect()
        self.disconnected.set()


async def connect(hub_mac: Optional[str] = None, hub_name: Optional[str] = None, use_relay: bool = True,
                  timeout: Optional[float] = None, **scanner_kwargs) -> Connection:
    """
    Connect through a running relay if there is one, otherwise directly over BLE.
    A relay serves the single hub it holds, so `hub_mac`/`hub_name` apply to BLE only.
    """
    if use_relay:
        try:
            return await RelayConnection.connect()
        except OSError as exc:
            log.info("No relay at %s:%s (%s), connecting over BLE", RELAY_HOST, RELAY_PORT, exc)
    return await BleakConnection.connect(hub_mac, hub_name, timeout, **scanner_kwargs)
