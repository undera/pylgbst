import time
import unittest

from pylgbst.hub import Hub
from pylgbst.messages import MsgHubAction, MsgHubAlert, MsgHubProperties
from pylgbst.peripherals import ColorDistanceSensor
from pylgbst.utilities import usbyte
from tests import ConnectionMock, log


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

        # regular startup attaches
        conn.notifications.append('0f0004020125000000001000000010')
        conn.notifications.append('0f0004370127000000001000000010')
        conn.notifications.append('0f0004380127000000001000000010')
        conn.notifications.append('090004390227003738')
        conn.notifications.append('0f0004320117000000001000000010')
        conn.notifications.append('0f00043a0128000000001000000002')
        conn.notifications.append('0f00043b0115000200000002000000')
        conn.notifications.append('0f00043c0114000200000002000000')
        conn.notifications.append('0f0004010126000000001000000010')

        # detach and reattach
        conn.notifications.append('0500040100')
        conn.notifications.append('0500040200')
        conn.notifications.append('0f0004010126000000001000000010')
        conn.notifications.append('0f0004020125000000001000000010')

        del hub
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
        conn.notification_delayed('0600 03 0104ff', 0.1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        conn.notification_delayed('0600 03 030400', 0.1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_SIGNAL, MsgHubAlert.UPD_REQUEST))
        conn.wait_notifications_handled()

    def test_disconnect_off(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed("04000231", 0.1)
        hub.disconnect()
        self.assertEqual("04000202", conn.writes[1][1])

        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed("04000230", 0.1)
        hub.switch_off()
        self.assertEqual("04000201", conn.writes[1][1])

    def test_sensor(self):
        conn = ConnectionMock().connect()
        conn.notifications.append("0f0004020125000000001000000010")  # add dev
        hub = Hub(conn)
        time.sleep(0.1)
        dev = hub.peripherals[0x02]
        assert isinstance(dev, ColorDistanceSensor)
        vals = []
        cb = lambda x, y=None: vals.append((x, y))

        conn.notification_delayed("0a004702080100000001", 0.1)  # subscribe ack
        dev.subscribe(cb, granularity=1)

        conn.notification_delayed("08004502ff0aff00", 0.1)  # value for sensor
        time.sleep(0.2)

        conn.notification_delayed("0a004702080000000000", 0.3)  # unsubscribe ack
        dev.unsubscribe(cb)

        self.assertEqual([(255, 10.0)], vals)
        self.assertEqual("0a004102080100000001", conn.writes[1][1])
        self.assertEqual("0a004102080000000000", conn.writes[2][1])
