import logging
import time
import unittest

from pylgbst.hub import Hub, LED, MsgPortModeInfoRequest
from pylgbst.messages import MsgHubActions, MsgHubAlert, MsgPortOutput
from pylgbst.peripherals import COLOR_RED, COLOR_BLACK
from tests import ConnectionMock


class GeneralTest(unittest.TestCase):
    def test_hub_properties(self):
        # TODO: test it
        pass

    def test_device_attached(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
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

    def test_hub_actions(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        hub.send(MsgHubActions(self.port))
        hub.send(MsgHubActions(self.port))
        hub.send(MsgHubActions(self.port))
        conn.notifications.append((14, '04000230'))
        conn.notifications.append((14, '04000231'))
        conn.notifications.append((14, '04000232'))
        time.sleep(1)
        conn.running = False

    def test_hub_alerts(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        hub.send(MsgHubAlert(self.port))
        conn.notifications.append((14, '0600030104ff'))
        time.sleep(1)
        hub.send(MsgHubAlert(self.port))
        conn.notifications.append((14, '060003030400'))
        time.sleep(1)
        conn.running = False
        conn.thr.join()
