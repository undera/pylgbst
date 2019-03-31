import time
import unittest

from pylgbst.hub import Hub
from pylgbst.messages import MsgHubProperties, MsgHubActions, MsgHubAlert
from tests import ConnectionMock


class GeneralTest(unittest.TestCase):
    def test_1(self):
        obj = Hub()
        time.sleep(2)
        # obj.send(MsgHubProperties(MsgHubProperties.RSSI, MsgHubProperties.UPD_ENABLE))
        obj.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        time.sleep(1)
        obj.send(MsgHubAlert(MsgHubAlert.LOW_SIGNAL, MsgHubAlert.UPD_REQUEST))
        time.sleep(300)

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
        hub.send(MsgHubActions(MsgHubActions.BUSY_INDICATION_ON))
        hub.send(MsgHubActions(MsgHubActions.BUSY_INDICATION_OFF))
        hub.send(MsgHubActions(MsgHubActions.DISCONNECT))
        conn.notifications.append((14, '04000230'))
        conn.notifications.append((14, '04000231'))
        conn.notifications.append((14, '04000232'))
        time.sleep(1)
        conn.running = False

    def test_hub_alerts(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        conn.notifications.append((14, '0600030104ff'))
        time.sleep(1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_SIGNAL, MsgHubAlert.UPD_REQUEST))
        conn.notifications.append((14, '060003030400'))
        time.sleep(1)
        conn.running = False
        conn.thr.join()
