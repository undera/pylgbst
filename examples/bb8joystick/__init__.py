import asyncio
import logging
import sys
import time

import spheropy
# noinspection PyProtectedMember
from spheropy.spheropy import _ClientCommandPacket, _DEVICE_ID_CORE


class BLEInterfaceGattool(spheropy.BleInterface):
    def _find_adapter(self):
        adapter = spheropy.pygatt.GATTToolBackend()
        adapter.start()
        adapter_type = spheropy.BleInterface.BleAdapterType.PYGATT

        self._adapter = adapter
        self._adapter_type = adapter_type

        return True


class _SpheroImproved(spheropy.Sphero):
    async def connect(self, search_name=None, address=None, port=None, bluetooth_interface=None, use_ble=False,
                      num_retry_attempts=1):
        gattool = BLEInterfaceGattool(search_name)
        return await super().connect(search_name, address, port, gattool, use_ble, num_retry_attempts)

    async def sleep(self, sleeptime, reset_inactivity_timeout=True, response_timeout_in_seconds=None):
        # port from https://github.com/jchadwhite/SpheroBB8-python/blob/master/BB8_driver.py#L394
        command = _ClientCommandPacket(device_id=_DEVICE_ID_CORE,
                                       command_id=0x22,
                                       sequence_number=self._get_and_increment_command_sequence_number(),
                                       data=[(sleeptime >> 8), (sleeptime & 0xff), 0],
                                       wait_for_response=True,
                                       reset_inactivity_timeout=reset_inactivity_timeout)

        return await self._send_command(command, response_timeout_in_seconds)


class BB8(object):
    def __init__(self, name):
        # marry sync with async https://www.aeracode.org/2018/02/19/python-async-simplified/
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        print("Started to wake up BB-8...")
        self._sphero = _SpheroImproved()
        self._loop.run_until_complete(self._sphero.connect(num_retry_attempts=3, use_ble=True, search_name=name))
        self._loop.run_until_complete(self._sphero.set_stabilization(True))
        self.stabilize()
        self.color(0, 0xFF, 0)
        print("BB-8 is ready for commands")

    def disconnect(self):
        self._loop.run_until_complete(self._sphero.sleep(0))
        self._sphero.disconnect()

    def color(self, red, green, blue):
        self._loop.run_until_complete(self._sphero.set_rgb_led(red, green, blue))

    def heading(self, heading):
        self._loop.run_until_complete(self._sphero.set_heading(heading))

    def roll(self, speed=1.0):
        speed = int(255 * speed)
        self._loop.run_until_complete(self._sphero.roll(speed, 0))

    def stop(self):
        self._loop.run_until_complete(self._sphero.roll(0, 0))

    def stabilize(self):
        self._loop.run_until_complete(self._sphero.self_level())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG if 'pydevd' in sys.modules else logging.WARNING)

    bb8 = BB8("BB-CC13")
    try:
        # bb8.color(0xFF, 0x00, 0xFF)
        bb8.color(0x00, 0x00, 0x00)

        bb8._loop.run_until_complete(bb8._sphero.set_back_led(254))
        time.sleep(3)

        for x in range(0, 359, 90):
            print(x)
            bb8.heading(x)
            bb8.roll(0.25)
            time.sleep(1)
            bb8.stop()
            bb8.stabilize()
    finally:
        bb8.disconnect()
