import logging
import unittest

from demo import demo_all
from pylegoboost.transport import ConnectionMock

logging.basicConfig(level=logging.DEBUG)


class GeneralTest(unittest.TestCase):
    def test_capabilities(self):
        conn = ConnectionMock()
        demo_all(conn)
        # transport.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)
        # transport.write(MOVE_HUB_HARDWARE_HANDLE, b'\x0a\x00\x41\x01\x08\x01\x00\x00\x00\x01')

# from pylegoboost import DebugServer
# srv = DebugServer(None)
#       srv.start()
