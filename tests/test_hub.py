import time
import unittest

from pylgbst.hub import Hub, MoveHub
from pylgbst.messages import MsgHubAction, MsgHubAlert, MsgHubProperties
from pylgbst.peripherals import VisionSensor
from pylgbst.utilities import usbyte
from tests import ConnectionMock


class HubTest(unittest.TestCase):
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
        self.assertEqual(b"LEGO Move Hub", resp.parameters)

        conn.wait_notifications_handled()

    def test_device_attached(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)

        # regular startup attaches
        conn.notifications.append('0f0004010126000000001000000010')
        conn.notifications.append('0f0004020125000000001000000010')

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
        conn.notification_delayed('04000230', 0.1)
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_SHUTDOWN))

        conn.notification_delayed('04000231', 0.1)
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_DISCONNECT))

        conn.notification_delayed('04000232', 0.1)
        hub.send(MsgHubAction(MsgHubAction.UPSTREAM_BOOT_MODE))
        time.sleep(0.1)
        conn.wait_notifications_handled()

    def test_hub_alerts(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed('0600 03 0104ff', 0.1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        conn.notification_delayed('0600 03 030400', 0.1)
        hub.send(MsgHubAlert(MsgHubAlert.LOW_SIGNAL, MsgHubAlert.UPD_REQUEST))
        conn.wait_notifications_handled()

    def test_error(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed("0500056105", 0.1)
        time.sleep(0.2)
        conn.wait_notifications_handled()

    def test_disconnect_off(self):
        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed("04000231", 0.1)
        hub.disconnect()
        self.assertEqual(b"04000202", conn.writes[1][1])

        conn = ConnectionMock().connect()
        hub = Hub(conn)
        conn.notification_delayed("04000230", 0.1)
        hub.switch_off()
        self.assertEqual(b"04000201", conn.writes[1][1])

    def test_sensor(self):
        conn = ConnectionMock().connect()
        conn.notifications.append("0f0004020125000000001000000010")  # add dev
        hub = Hub(conn)
        time.sleep(0.1)
        dev = hub.peripherals[0x02]
        assert isinstance(dev, VisionSensor)

        conn.notification_delayed("0a004702080000000000", 0.1)
        conn.notification_delayed("08004502ff0aff00", 0.2)  # value for sensor
        self.assertEqual((255, 10.0), dev.get_sensor_data(VisionSensor.COLOR_DISTANCE_FLOAT))
        self.assertEqual(b"0a004102080100000000", conn.writes.pop(1)[1])
        self.assertEqual(b"0500210200", conn.writes.pop(1)[1])

        vals = []
        cb = lambda x, y=None: vals.append((x, y))

        conn.notification_delayed("0a004702080100000001", 0.1)  # subscribe ack
        dev.subscribe(cb, granularity=1)
        self.assertEqual(b"0a004102080100000001", conn.writes.pop(1)[1])

        conn.notification_delayed("08004502ff0aff00", 0.1)  # value for sensor
        time.sleep(0.3)

        conn.notification_delayed("0a004702080000000000", 0.3)  # unsubscribe ack
        dev.unsubscribe(cb)
        self.assertEqual(b"0a004102080100000000", conn.writes.pop(1)[1])

        self.assertEqual([(255, 10.0)], vals)


class MoveHubTest(unittest.TestCase):
    def test_capabilities(self):
        conn = ConnectionMock()
        conn.notifications.append('0f00 04 02 0125000000001000000010')
        conn.notifications.append('0f00 04 03 0126000000001000000010')
        conn.notifications.append('0f00 04 00 0127000100000001000000')
        conn.notifications.append('0f00 04 01 0127000100000001000000')
        conn.notifications.append('0900 04 10 0227003738')
        conn.notifications.append('0f00 04 32 0117000100000001000000')
        conn.notifications.append('0f00 04 3a 0128000000000100000001')
        conn.notifications.append('0f00 04 3b 0115000200000002000000')
        conn.notifications.append('0f00 04 3c 0114000200000002000000')

        conn.notification_delayed('12000101064c45474f204d6f766520487562', 1.1)
        conn.notification_delayed('0b00010d06001653a0d1d4', 1.3)
        conn.notification_delayed('060001060600', 1.5)
        conn.notification_delayed('0600030104ff', 1.7)
        MoveHub(conn.connect())
        time.sleep(1)
        conn.wait_notifications_handled()
        self.assertEqual(b"0500010105", conn.writes[1][1])
        self.assertEqual(b"0500010d05", conn.writes[2][1])
        self.assertEqual(b"0500010605", conn.writes[3][1])
        self.assertEqual(b"0500030103", conn.writes[4][1])
