import logging
import threading
import time

from pylgbst.aio import peripherals as aio_peripherals
from pylgbst.hub import MoveHub
from pylgbst.peripherals import LEDRGB, TiltSensor, COLOR_RED, Button, Current, Voltage, VisionSensor, \
    EncodedMotor
from tests import ATTACH_CURRENT, ATTACH_LED, ATTACH_MOTOR_C, ATTACH_MOTOR_D, ATTACH_TILT, ATTACH_VISION_C, \
    ATTACH_VOLTAGE, HubMock, HubTestCase, hub_with


def button_of(test, hub):
    """The green button, which only hubs that have one create and close"""

    async def create():
        return aio_peripherals.Button(hub.aio)

    async def close():
        button.close_subscriptions()

    button = hub.loop_thread.run(create())
    test.addCleanup(lambda: hub.loop_thread.run(close()))
    return Button(hub, button)


class PeripheralsTest(HubTestCase):

    def test_button(self):
        hub = self.closing(HubMock())
        button = button_of(self, hub)

        vals = []

        def callback(pressed):
            vals.append(pressed)

        hub.connection.notification_delayed("060001020600", 0.0)
        button.subscribe(callback)
        time.sleep(0.1)

        hub.connection.notification_delayed("060001020600", 0.1)
        hub.connection.notification_delayed("060001020601", 0.2)
        hub.connection.notification_delayed("060001020600", 0.3)
        time.sleep(0.4)

        button.unsubscribe(callback)
        time.sleep(0.1)
        hub.connection.wait_notifications_handled()

        self.assertEqual([0, 1, 0], vals)
        self.assertEqual(b"0500010202", hub.writes[1][1])
        self.assertEqual(b"0500010203", hub.writes[2][1])

    def test_button_callback_sends_command(self):
        hub = self.closing(hub_with(ATTACH_MOTOR_D))
        button = button_of(self, hub)
        motor = hub.peripherals[MoveHub.PORT_D]
        done = threading.Event()

        def callback(pressed):
            if pressed:
                motor.start_power(1.0)  # sync command from inside a callback
                done.set()

        hub.connection.notification_delayed("060001020600", 0.0)
        button.subscribe(callback)

        hub.connection.notification_delayed("060001020601", 0.1)
        hub.connection.notification_delayed("050082030a", 0.3)
        self.assertTrue(done.wait(2), "command sent from button callback never completed")
        hub.connection.wait_notifications_handled()

    def test_led(self):
        hub = self.closing(hub_with(ATTACH_LED))
        hub.led = hub.peripherals[MoveHub.PORT_LED]
        self.assertIsInstance(hub.led, LEDRGB)

        hub.connection.notification_delayed("0a004732000100000000", 0.1)
        hub.connection.notification_delayed("050082320a", 0.2)
        hub.led.set_color(COLOR_RED)
        self.assertEqual(b"0a004132000100000000", hub.writes.pop(1)[1])
        self.assertEqual(b"0800813211510009", hub.writes.pop(1)[1])

        hub.connection.notification_delayed("0a004732010100000000", 0.1)
        hub.connection.notification_delayed("050082320a", 0.2)
        hub.led.set_color((32, 64, 96))
        self.assertEqual(b"0a004132010100000000", hub.writes.pop(1)[1])
        self.assertEqual(b"0a008132115101204060", hub.writes.pop(1)[1])

    def test_current(self):
        hub = self.closing(hub_with(ATTACH_CURRENT))
        current = hub.peripherals[MoveHub.PORT_CURRENT]
        self.assertIsInstance(current, Current)

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

        self.assertEqual([97.87936507936507], vals)
        self.assertEqual(b"0a00413b000100000001", hub.writes[1][1])
        self.assertEqual(b"0a00413b000100000000", hub.writes[2][1])

    def test_voltage(self):
        hub = self.closing(hub_with(ATTACH_VOLTAGE))
        voltage = hub.peripherals[MoveHub.PORT_VOLTAGE]
        self.assertIsInstance(voltage, Voltage)

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

        self.assertEqual([4.79630105317236], vals)
        self.assertEqual(b"0a00413c000100000001", hub.writes[1][1])
        self.assertEqual(b"0a00413c000100000000", hub.writes[2][1])

    def test_tilt_sensor_presets(self):
        hub = self.closing(hub_with(ATTACH_TILT))
        sensor = hub.peripherals[MoveHub.PORT_TILT_SENSOR]
        sent = len(hub.writes)
        for call, frame in (
                (lambda: sensor.set_impact_count(1000), b"0b00813a115103e8030000"),
                (lambda: sensor.set_orientation(TiltSensor.ORIENT_TOP), b"0800813a11510505"),
                (lambda: sensor.set_impact_config(10, 5), b"0900813a1151060a05"),
        ):
            hub.connection.notification_delayed("0500823a0a", 0.1)
            call()
            self.assertEqual(frame, hub.writes[sent][1])  # no port mode change before the write
            sent += 1

    def test_tilt_sensor(self):
        hub = self.closing(hub_with(ATTACH_TILT))
        sensor = hub.peripherals[MoveHub.PORT_TILT_SENSOR]
        self.assertIsInstance(sensor, TiltSensor)

        hub.connection.notification_delayed('0a00473a000100000000', 0.05)
        hub.connection.notification_delayed('0600453a0201', 0.1)
        self.assertEqual((2, 1), sensor.get_sensor_data(TiltSensor.MODE_2AXIS_ANGLE))

        hub.connection.notification_delayed('0a00473a010100000000', 0.05)
        hub.connection.notification_delayed('0500453a00', 0.1)
        self.assertEqual((0,), sensor.get_sensor_data(TiltSensor.MODE_2AXIS_SIMPLE))

        hub.connection.notification_delayed('0a00473a020100000000', 0.05)
        hub.connection.notification_delayed('0600453a0201', 0.1)
        self.assertEqual((2,), sensor.get_sensor_data(TiltSensor.MODE_3AXIS_SIMPLE))

        hub.connection.notification_delayed('0a00473a030100000000', 0.05)
        hub.connection.notification_delayed('0800453a00000000', 0.1)
        self.assertEqual((0,), sensor.get_sensor_data(TiltSensor.MODE_IMPACT_COUNT))

        hub.connection.notification_delayed('0a00473a040100000000', 0.05)
        hub.connection.notification_delayed('0700453afd0140', 0.1)
        self.assertEqual((-3, 1, 64), sensor.get_sensor_data(TiltSensor.MODE_3AXIS_ACCEL))

        hub.connection.notification_delayed('0a00473a050100000000', 0.05)
        hub.connection.notification_delayed('0500453a00', 0.1)
        self.assertEqual((0,), sensor.get_sensor_data(TiltSensor.MODE_ORIENT_CF))

        hub.connection.notification_delayed('0a00473a060100000000', 0.05)
        hub.connection.notification_delayed('0600453a7f14', 0.1)
        self.assertEqual((127, 20), sensor.get_sensor_data(TiltSensor.MODE_IMPACT_CF))

        hub.connection.notification_delayed('0a00473a070100000000', 0.05)
        hub.connection.notification_delayed('0700453a00feff', 0.1)
        self.assertEqual((0, 254, 255), sensor.get_sensor_data(TiltSensor.MODE_CALIBRATION))

        hub.connection.wait_notifications_handled()

    def test_motor(self):
        hub = self.closing(hub_with(ATTACH_MOTOR_D))
        motor = hub.peripherals[MoveHub.PORT_D]
        self.assertIsInstance(motor, EncodedMotor)

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_power(1.0)
        self.assertEqual(b"07008103110164", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_acc_profile(1.0)
        self.assertEqual(b"090081031105e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_dec_profile(1.0)
        self.assertEqual(b"090081031106e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_speed(1.0)
        self.assertEqual(b"090081031107646403", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        logging.debug("\n\n")
        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.timed(1.0)
        self.assertEqual(b"0c0081031109e80364647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.angled(180)
        self.assertEqual(b"0e008103110bb400000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.2)
        motor.preset_encoder(-180)
        self.assertEqual(b"0b0081031151024cffffff", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.goto_position(0)
        self.assertEqual(b"0e008103110d0000000064647f03", hub.writes.pop(1)[1])

        hub.connection.wait_notifications_handled()

    def test_motor_discarded(self):
        hub = self.closing(hub_with(ATTACH_MOTOR_D))
        motor = hub.peripherals[MoveHub.PORT_D]
        self.assertIsInstance(motor, EncodedMotor)

        # discarded with nothing taking over: raise instead of waiting forever
        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030c', 0.2)
        self.assertRaises(RuntimeError, motor.angled, 180)

        # discarded previous command while this one runs: keep waiting for completion
        hub.connection.notification_delayed('0500820305', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.angled(180)

        # bare discard of an interrupted non-blocking command must not fail the interrupting one
        hub.connection.notification_delayed('0500820301', 0.1)
        motor.timed(1.0, wait_complete=False)
        self.assertTrue(motor.cmd_in_progress)
        hub.connection.notification_delayed('0500820304', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.stop()

        hub.connection.wait_notifications_handled()

    def test_motor_sensor(self):
        hub = self.closing(hub_with(ATTACH_MOTOR_C))
        motor = hub.peripherals[MoveHub.PORT_C]

        vals = []

        def callback(*args):
            vals.append(args)

        hub.connection.notification_delayed('0a004702020100000001', 0.1)
        motor.subscribe(callback)

        hub.connection.notification_delayed("0800450200000000", 0.1)
        hub.connection.notification_delayed("08004502ffffffff", 0.2)
        hub.connection.notification_delayed("08004502feffffff", 0.3)
        time.sleep(0.4)

        hub.connection.notification_delayed('0a004702020000000000', 0.1)
        motor.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([(0,), (-1,), (-2,)], vals)

    def test_color_sensor(self):
        hub = self.closing(hub_with(ATTACH_VISION_C))
        cds = hub.peripherals[MoveHub.PORT_C]
        self.assertIsInstance(cds, VisionSensor)

        vals = []

        def callback(*args):
            vals.append(args)

        hub.connection.notification_delayed('0a00 4702080100000001', 0.1)
        cds.subscribe(callback)

        hub.connection.notification_delayed("08004502ff0aff00", 0.1)
        time.sleep(0.2)

        hub.connection.notification_delayed('0a00 4702090100000001', 0.1)
        cds.unsubscribe(callback)
        hub.connection.wait_notifications_handled()

        self.assertEqual([(255, 10.0)], vals)
