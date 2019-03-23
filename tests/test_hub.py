import time
import unittest

from pylgbst.hub import Hub
from pylgbst.messages import MsgHubProperties
from tests import ConnectionMock


class GeneralTest(unittest.TestCase):
    def test_1(self):
        conn = ConnectionMock().connect()
        conn = None
        obj = Hub(conn)
        time.sleep(2)
        obj.send(MsgHubProperties(MsgHubProperties.PROP_RSSI, MsgHubProperties.OP_UPD_ENABLE))
        #conn.notifications.append((14, '12000101064c45474f204d6f766520487562'))
        # conn.thr.join()
        time.sleep(3)
