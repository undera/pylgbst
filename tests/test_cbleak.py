import sys
import time
import unittest

import bleak
from packaging import version

import pylgbst
import pylgbst.comms.cbleak as cbleak

bleak.BleakClient = object()
bleak.discover = object()

last_response = None
lt37 = version.parse(sys.version.split(' ')[0]) < version.parse("3.7")


class BleakDriverTest(unittest.TestCase):
    def test_driver_creation(self):
        connection = pylgbst.get_connection_bleak()
        self.assertIsInstance(connection, cbleak.BleakDriver)
        self.assertFalse(connection.is_alive(), 'Checking that factory returns not started driver')

    @unittest.skipIf(lt37, "Python version is too low")
    def test_communication(self):
        driver = cbleak.BleakDriver()

        async def fake_thread():
            print('Fake thread initialized')
            while not driver._abort:
                time.sleep(0.1)
                if driver.req_queue.qsize() != 0:
                    print('Received data, sending back')
                    data = driver.req_queue.get()
                    driver.resp_queue.put(data)

        driver._bleak_thread = fake_thread
        driver.set_notify_handler(BleakDriverTest.validation_handler)
        driver.enable_notifications()

        time.sleep(0.5)  # time for driver initialization
        self.assertTrue(driver.is_alive(), 'Checking that driver starts')
        handle = 0x32
        data = [0xD, 0xE, 0xA, 0xD, 0xB, 0xE, 0xE, 0xF]
        driver.write(handle, data)
        time.sleep(0.5)  # processing time
        self.assertEqual(handle, last_response[0], 'Verifying response handle')
        self.assertEqual(bytes(data), last_response[1], 'Verifying response data')

        driver.disconnect()
        time.sleep(0.5)  # processing time
        self.assertFalse(driver.is_alive())

    @staticmethod
    def validation_handler(handle, data):
        global last_response
        last_response = (handle, data)


if __name__ == '__main__':
    unittest.main()
