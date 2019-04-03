import time
import unittest

from pylgbst.hub import MoveHub, Hub
from pylgbst.peripherals import LED, TiltSensor, COLORS, COLOR_RED, Button, Current, Voltage, ColorDistanceSensor
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

    def test_current(self):
        hub = HubMock()
        time.sleep(0.1)
        current = Current(hub, MoveHub.PORT_CURRENT)
        hub.peripherals[MoveHub.PORT_CURRENT] = current

        vals = []

        def callback(val):
            vals.append(val)

        hub.connection.notification_delayed("0a00473b000100000001", 0.1)
        current.subscribe(callback)

        hub.connection.notification_delayed("0600453ba400", 0.1)
        time.sleep(0.2)

        hub.connection.notification_delayed("0a00473b000000000000", 0.1)
        current.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([0.0400390625], vals)
        self.assertEqual("0a00413b000100000001", hub.writes[1][1])
        self.assertEqual("0a00413b000000000000", hub.writes[2][1])

    def test_voltage(self):
        hub = HubMock()
        time.sleep(0.1)
        voltage = Voltage(hub, MoveHub.PORT_VOLTAGE)
        hub.peripherals[MoveHub.PORT_VOLTAGE] = voltage

        vals = []

        def callback(val):
            vals.append(val)

        hub.connection.notification_delayed("0a00473c000100000001", 0.1)
        voltage.subscribe(callback)

        hub.connection.notification_delayed("0600453c9907", 0.1)
        time.sleep(0.2)

        hub.connection.notification_delayed("0a00473c000000000000", 0.1)
        voltage.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([0.474853515625], vals)
        self.assertEqual("0a00413c000100000001", hub.writes[1][1])
        self.assertEqual("0a00413c000000000000", hub.writes[2][1])

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

    def test_motor_sensor(self):
        pass  # TODO

    def test_color_sensor(self):
        hub = HubMock()
        cds = ColorDistanceSensor(hub, MoveHub.PORT_C)
        hub.peripherals[MoveHub.PORT_C] = cds
        time.sleep(1)

        vals = []

        def callback(*args):
            vals.append(args)

        hub.connection.notification_delayed('0a00 4701090100000001', 0.1)
        cds.subscribe(callback)

        hub.connection.notification_delayed("08004501ff0aff00", 0.1)
        time.sleep(0.2)

        hub.connection.notification_delayed('0a00 4701090100000001', 0.1)
        cds.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([(255, 10.0)], vals)
