import time
import unittest

from pylgbst.hub import MoveHub
from pylgbst.peripherals import LED, TiltSensor, COLOR_RED, Button, Current, Voltage, ColorDistanceSensor, EncodedMotor
from tests import HubMock, ConnectionMock


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
        sensor = TiltSensor(hub, MoveHub.PORT_TILT_SENSOR)
        hub.peripherals[MoveHub.PORT_TILT_SENSOR] = sensor

        vals = []

        def callback(*args):
            vals.append(args)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        sensor.subscribe(callback)
        hub.connection.notification_delayed("0500453a05")
        time.sleep(0.1)
        hub.connection.notification_delayed('0a00 47 3a 090100000000', 0.1)
        sensor.unsubscribe(callback)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        sensor.subscribe(callback, TiltSensor.MODE_2AXIS_SIMPLE)
        hub.connection.notification_delayed("0500453a09")
        time.sleep(0.1)
        hub.connection.notification_delayed('0a00 47 3a 090100000000', 0.1)
        sensor.unsubscribe(callback)

        hub.connection.notification_delayed('0a00 47 3a 090100000001', 0.1)
        sensor.subscribe(callback, TiltSensor.MODE_2AXIS_FULL)
        hub.connection.notification_delayed("0600453a04fe")
        time.sleep(0.1)
        hub.connection.notification_delayed('0a00 47 3a 090100000000', 0.1)
        sensor.unsubscribe(callback)

        hub.connection.wait_notifications_handled()
        self.assertEqual([(5,), (9,), (4, -2)], vals)

    def test_motor(self):
        hub = HubMock()
        motor = EncodedMotor(hub, MoveHub.PORT_C)
        hub.peripherals[MoveHub.PORT_C] = motor

        hub.connection.notification_delayed('050082010a', 0.1)
        motor.start_speed(0.25)
        self.assertEqual("0800810111510119", hub.writes[1][1])

        hub.connection.notification_delayed('050082010a', 0.1)
        motor.stop()
        self.assertEqual("0800810111510100", hub.writes[2][1])

        hub.connection.wait_notifications_handled()

    def test_motor_sensor(self):
        hub = HubMock()
        motor = EncodedMotor(hub, MoveHub.PORT_C)
        hub.peripherals[MoveHub.PORT_C] = motor

        vals = []

        def callback(*args):
            vals.append(args)

        hub.connection.notification_delayed('0a004701020100000001', 0.1)
        motor.subscribe(callback)

        hub.connection.notification_delayed("0800450100000000", 0.1)
        hub.connection.notification_delayed("08004501ffffffff", 0.2)
        hub.connection.notification_delayed("08004501feffffff", 0.3)
        time.sleep(0.4)

        hub.connection.notification_delayed('0a004701020000000000', 0.1)
        motor.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([(0,), (-1,), (-2,)], vals)

    def test_color_sensor(self):
        hub = HubMock()
        cds = ColorDistanceSensor(hub, MoveHub.PORT_C)
        hub.peripherals[MoveHub.PORT_C] = cds

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
