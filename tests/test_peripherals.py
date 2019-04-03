import time
import unittest

from pylgbst.hub import MoveHub, Hub
from pylgbst.peripherals import LED, TiltSensor, COLORS, COLOR_RED, Button
from tests import log, HubMock, ConnectionMock


class PeripheralsTest(unittest.TestCase):

    def test_button(self):
        hub = HubMock()
        time.sleep(0.1)
        button = Button(hub)
        hub.peripherals[0x00] = button

        vals = []

        def callback(pressed):
            vals.append(pressed)

        button.subscribe(callback)

        hub.connection.notification_delayed("060001020600", 0.1)
        hub.connection.notification_delayed("060001020601", 0.2)
        hub.connection.notification_delayed("060001020600", 0.3)
        time.sleep(0.4)

        button.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([False, True, False], vals)
        self.assertEqual("0500010202", hub.writes[1][1])
        self.assertEqual("0500010203", hub.writes[2][1])

    def test_led(self):
        hub = HubMock()
        hub.led = LED(hub, MoveHub.PORT_LED)
        hub.peripherals[MoveHub.PORT_LED] = hub.led
        hub.connection.notification_delayed("0500 82 320a", 0.1)
        hub.led.set_color_index(COLOR_RED)
        self.assertEqual("0800813211510009", hub.writes[1][1])

    def test_tilt_sensor(self):
        hub = HubMock()
        hub.notify_mock.append('0f00 04 3a 0128000000000100000001')
        time.sleep(1)

        def callback(param1, param2=None, param3=None):
            if param2 is None:
                log.debug("Tilt: %s", TiltSensor.DUO_STATES[param1])
            else:
                log.debug("Tilt: %s %s %s", param1, param2, param3)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        hub.tilt_sensor.subscribe(callback)
        hub.notify_mock.append("0500453a05")
        hub.notify_mock.append("0a00473a010100000001")
        time.sleep(1)
        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        hub.tilt_sensor.subscribe(callback, TiltSensor.MODE_2AXIS_SIMPLE)

        hub.notify_mock.append("0500453a09")
        time.sleep(1)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        hub.tilt_sensor.subscribe(callback, TiltSensor.MODE_2AXIS_FULL)
        hub.notify_mock.append("0600453a04fe")
        time.sleep(1)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        hub.tilt_sensor.unsubscribe(callback)
        hub.connection.wait_notifications_handled()
        # TODO: assert

    def test_motor(self):
        conn = ConnectionMock()
        conn.notifications.append('0900 04 39 0227003738')
        hub = HubMock(conn)
        time.sleep(0.1)

        conn.notifications.append('050082390a')
        hub.motor_AB.timed(1.5)
        self.assertEqual("0d018139110adc056464647f03", conn.writes[0][1])

        conn.notifications.append('050082390a')
        hub.motor_AB.angled(90)
        self.assertEqual("0f018139110c5a0000006464647f03", conn.writes[1][1])

    def test_color_sensor(self):
        hub = HubMock()
        hub.notify_mock.append('0f00 04 01 0125000000001000000010')
        time.sleep(1)

        def callback(color, unk1, unk2=None):
            name = COLORS[color] if color is not None else 'NONE'
            log.info("Color: %s %s %s", name, unk1, unk2)

        hub.connection.notification_delayed('0a00 4701090100000001', 0.1)
        hub.color_distance_sensor.subscribe(callback)

        hub.notify_mock.append("08004501ff0aff00")
        time.sleep(1)
        # TODO: assert
        hub.connection.notification_delayed('0a00 4701090100000001', 0.1)
        hub.color_distance_sensor.unsubscribe(callback)
        hub.connection.wait_notifications_handled()
