import unittest

from pylgbst.hub import Hub
from pylgbst.messages import MsgHubAction, MsgHubAlert, MsgHubProperties
from pylgbst.utilities import usbyte
from tests import ConnectionMock


class GeneralTest(unittest.TestCase):
    def test_hub_properties(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)

        conn.notification_delayed('060001060600', 0.1)
        msg = MsgHubProperties(MsgHubProperties.VOLTAGE_PERC, MsgHubProperties.UPD_REQUEST)
        resp = hub.send(msg)
        assert isinstance(resp, MsgHubProperties)
        self.assertEqual(1, len(resp.parameters))
        self.assertEqual(0, usbyte(resp.parameters, 0))

        conn.notification_delayed('12000101064c45474f204d6f766520487562', 0.1)
        msg = MsgHubProperties(MsgHubProperties.ADVERTISE_NAME, MsgHubProperties.UPD_REQUEST)
        resp = hub.send(msg)
        assert isinstance(resp, MsgHubProperties)
        self.assertEqual("LEGO Move Hub", resp.parameters)

        conn.wait_notifications_handled()

    def test_device_attached(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notifications.append('0f0004020125000000001000000010')
        conn.notifications.append('0f0004370127000000001000000010')
        conn.notifications.append('0f0004380127000000001000000010')
        conn.notifications.append('090004390227003738')
        conn.notifications.append('0f0004320117000000001000000010')
        conn.notifications.append('0f00043a0128000000001000000002')
        conn.notifications.append('0f00043b0115000200000002000000')
        conn.notifications.append('0f00043c0114000200000002000000')
        conn.notifications.append('0f0004010126000000001000000010')
        conn.wait_notifications_handled()

    def test_hub_actions(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_SHUTDOWN))
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_SHUTDOWN))
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_SHUTDOWN))
        conn.notifications.append('04000230')
        conn.notifications.append('04000231')
        conn.notifications.append('04000232')
        conn.wait_notifications_handled()

    def test_hub_alerts(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed('0600 03 0104ff', 1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        conn.notification_delayed('0600 03 030400', 1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_SIGNAL, MsgHubAlert.UPD_REQUEST))
        conn.wait_notifications_handled()
