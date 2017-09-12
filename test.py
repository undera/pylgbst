import logging
import unittest
from time import sleep

from pylegoboost.constants import *
from pylegoboost.transport import BLETransport

logging.basicConfig(level=logging.DEBUG)


class GeneralTest(unittest.TestCase):
    def test_1(self):
        transport = BLETransport()
        transport.connect()
        transport.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)
        transport.write(MOVE_HUB_HARDWARE_HANDLE, LISTEN_DIST_SENSOR_ON_C)
        sleep(60)

# from pylegoboost import DebugServer
# srv = DebugServer(None)
#       srv.start()
