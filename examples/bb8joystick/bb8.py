import asyncio
import time

import spheropy
# noinspection PyProtectedMember
from spheropy.spheropy import _ClientCommandPacket, _DEVICE_ID_CORE, _DEVICE_ID_SPHERO


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
        return await
        super().connect(search_name, address, port, gattool, use_ble, num_retry_attempts)

    async def sleep(self, sleeptime, reset_inactivity_timeout=True, response_timeout_in_seconds=None):
        # port from https://github.com/jchadwhite/SpheroBB8-python/blob/master/BB8_driver.py#L394
        command = _ClientCommandPacket(device_id=_DEVICE_ID_CORE,
                                       command_id=0x22,
                                       sequence_number=self._get_and_increment_command_sequence_number(),
                                       data=[(sleeptime >> 8), (sleeptime & 0xff), 0],
                                       wait_for_response=False,
                                       reset_inactivity_timeout=reset_inactivity_timeout)

        return await
        self._send_command(command, response_timeout_in_seconds)

    async def set_rotation_rate(self, rate, reset_inactivity_timeout=True, response_timeout_in_seconds=None):
        # port from https://github.com/jchadwhite/SpheroBB8-python/blob/master/BB8_driver.py
        command = _ClientCommandPacket(device_id=_DEVICE_ID_SPHERO,
                                       command_id=0x03,
                                       sequence_number=self._get_and_increment_command_sequence_number(),
                                       data=[rate],
                                       wait_for_response=False,
                                       reset_inactivity_timeout=reset_inactivity_timeout)

        return await
        self._send_command(command, response_timeout_in_seconds)


class BB8(object):
    def __init__(self, name="BB-CC13"):
        self._heading = 0
        # marry sync with async https://www.aeracode.org/2018/02/19/python-async-simplified/
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        print("Started to wake up BB-8...")
        self._sphero = _SpheroImproved()
        self._loop.run_until_complete(self._sphero.connect(num_retry_attempts=3, use_ble=True, search_name=name))
        self._loop.run_until_complete(self._sphero.set_stabilization(True))
        self._loop.run_until_complete(self._sphero.set_rotation_rate(1))
        self.color(0, 0xFF, 0)
        self.stabilize()
        print("BB-8 is ready for commands")

    def disconnect(self):
        print("BB8 enters sleep")
        self._loop.run_until_complete(self._sphero.sleep(0))
        self._sphero.disconnect()

    def color(self, red, green, blue):
        self._wait_loop()
        self._loop.run_until_complete(self._sphero.set_rgb_led(red, green, blue, wait_for_response=False))

    def heading(self, heading):
        self._wait_loop()
        heading = 359 - heading
        self._heading = heading
        # self._loop.run_until_complete(self._sphero.set_heading(359 - heading))
        self._loop.run_until_complete(self._sphero.roll(1, heading, spheropy.RollMode.IN_PLACE_ROTATE))

    def roll(self, speed=10, direction=0):
        self._wait_loop()
        direction += self._heading
        direction %= 360
        speed = int(255 * speed / 10)
        speed *= 0.75  # throttle down a bit
        self._loop.run_until_complete(self._sphero.roll(int(speed), direction))

    def stop(self):
        self._wait_loop()
        self._loop.run_until_complete(self._sphero.roll(0, 0))

    def stabilize(self):
        self._wait_loop()
        self._loop.run_until_complete(self._sphero.self_level())

    def _wait_loop(self):
        while self._loop.is_running():
            time.sleep(0.001)


if __name__ == '__main__':
    bb8 = BB8()
    bb8.color(255, 0, 0)
    time.sleep(1)
    bb8.color(0, 255, 0)
    time.sleep(1)
    bb8.color(0, 0, 255)
    time.sleep(1)
