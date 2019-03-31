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
        obj.send(MsgHubProperties(MsgHubProperties.RSSI, MsgHubProperties.UPD_ENABLE))
        # conn.notifications.append((14, '12000101064c45474f204d6f766520487562'))
        # conn.thr.join()
        time.sleep(3)

    def test_device_attached(self):
        conn = ConnectionMock().connect()
        obj = Hub(conn)
        conn.notifications.append((14, '0f0004020125000000001000000010'))
        conn.notifications.append((14, '0f0004370127000000001000000010'))
        conn.notifications.append((14, '0f0004380127000000001000000010'))
        conn.notifications.append((14, '090004390227003738'))
        conn.notifications.append((14, '0f0004320117000000001000000010'))
        conn.notifications.append((14, '0f00043a0128000000001000000002'))
        conn.notifications.append((14, '0f00043b0115000200000002000000'))
        conn.notifications.append((14, '0f00043c0114000200000002000000'))
        conn.notifications.append((14, '0f0004010126000000001000000010'))
        time.sleep(1)
        conn.running = False
        conn.thr.join()
