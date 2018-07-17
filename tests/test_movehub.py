import time
import unittest

from pylgbst.movehub import MoveHub
from pylgbst.peripherals import LED, PORT_LED, MOVE_HUB_HARDWARE_HANDLE, COLOR_RED, TiltSensor, COLORS
from tests import log, HubMock, ConnectionMock, Thread

HANDLE = MOVE_HUB_HARDWARE_HANDLE


class GeneralTest(unittest.TestCase):
    def _wait_notifications_handled(self, hub):
        hub.connection.running = False
        for _ in range(1, 180):
            time.sleep(1)
            log.debug("Waiting for notifications to process...")
            if hub.connection.finished:
                log.debug("Done waiting for notifications to process")
                break

    def test_led(self):
        hub = HubMock()
        led = LED(hub, PORT_LED)
        led.set_color(COLOR_RED)
        self.assertEqual("0801813201510009", hub.writes[0][1])

    def test_tilt_sensor(self):
        hub = HubMock()
        hub.notify_mock.append((HANDLE, '0f00 04 3a 0128000000000100000001'))
        time.sleep(1)

        def callback(param1, param2=None, param3=None):
            if param2 is None:
                log.debug("Tilt: %s", TiltSensor.DUO_STATES[param1])
            else:
                log.debug("Tilt: %s %s %s", param1, param2, param3)

        self._inject_notification(hub, '0a00 47 3a 090100000001', 1)
        hub.tilt_sensor.subscribe(callback)
        hub.notify_mock.append((HANDLE, "0500453a05"))
        hub.notify_mock.append((HANDLE, "0a00473a010100000001"))
        time.sleep(1)
        self._inject_notification(hub, '0a00 47 3a 090100000001', 1)
        hub.tilt_sensor.subscribe(callback, TiltSensor.MODE_2AXIS_SIMPLE)

        hub.notify_mock.append((HANDLE, "0500453a09"))
        time.sleep(1)

        self._inject_notification(hub, '0a00 47 3a 090100000001', 1)
        hub.tilt_sensor.subscribe(callback, TiltSensor.MODE_2AXIS_FULL)
        hub.notify_mock.append((HANDLE, "0600453a04fe"))
        time.sleep(1)

        self._inject_notification(hub, '0a00 47 3a 090100000001', 1)
        hub.tilt_sensor.unsubscribe(callback)
        self._wait_notifications_handled(hub)
        # TODO: assert

    def test_motor(self):
        conn = ConnectionMock()
        conn.notifications.append((14, '0900 04 39 0227003738'))
        hub = HubMock(conn)
        time.sleep(0.1)

        conn.notifications.append((14, '050082390a'))
        hub.motor_AB.timed(1.5)
        self.assertEqual("0d018139110adc056464647f03", conn.writes[0][1])

        conn.notifications.append((14, '050082390a'))
        hub.motor_AB.angled(90)
        self.assertEqual("0f018139110c5a0000006464647f03", conn.writes[1][1])

    def test_capabilities(self):
        conn = ConnectionMock()
        conn.notifications.append((14, '0f00 04 01 0125000000001000000010'))
        conn.notifications.append((14, '0f00 04 02 0126000000001000000010'))
        conn.notifications.append((14, '0f00 04 37 0127000100000001000000'))
        conn.notifications.append((14, '0f00 04 38 0127000100000001000000'))
        conn.notifications.append((14, '0900 04 39 0227003738'))
        conn.notifications.append((14, '0f00 04 32 0117000100000001000000'))
        conn.notifications.append((14, '0f00 04 3a 0128000000000100000001'))
        conn.notifications.append((14, '0f00 04 3b 0115000200000002000000'))
        conn.notifications.append((14, '0f00 04 3c 0114000200000002000000'))
        conn.notifications.append((14, '0f00 8202 01'))
        conn.notifications.append((14, '0f00 8202 0a'))

        self._inject_notification(conn, '1200 0101 06 4c45474f204d6f766520487562', 1)
        self._inject_notification(conn, '1200 0108 06 4c45474f204d6f766520487562', 2)
        self._inject_notification(conn, '0900 47 3c 0227003738', 3)
        self._inject_notification(conn, '0600 45 3c 020d', 4)
        self._inject_notification(conn, '0900 47 3c 0227003738', 5)
        hub = MoveHub(conn)
        # demo_all(hub)
        self._wait_notifications_handled(hub)

    def test_color_sensor(self):
        #
        hub = HubMock()
        hub.notify_mock.append((HANDLE, '0f00 04010125000000001000000010'))
        time.sleep(1)

        def callback(color, unk1, unk2=None):
            name = COLORS[color] if color is not None else 'NONE'
            log.info("Color: %s %s %s", name, unk1, unk2)

        self._inject_notification(hub, '0a00 4701090100000001', 1)
        hub.color_distance_sensor.subscribe(callback)

        hub.notify_mock.append((HANDLE, "08004501ff0aff00"))
        time.sleep(1)
        # TODO: assert
        self._inject_notification(hub, '0a00 4701090100000001', 1)
        hub.color_distance_sensor.unsubscribe(callback)
        self._wait_notifications_handled(hub)

    def test_button(self):
        hub = HubMock()
        time.sleep(1)

        def callback(pressed):
            log.info("Pressed: %s", pressed)

        hub.notify_mock.append((HANDLE, "060001020600"))
        hub.button.subscribe(callback)

        hub.notify_mock.append((HANDLE, "060001020601"))
        hub.notify_mock.append((HANDLE, "060001020600"))
        time.sleep(1)
        # TODO: assert
        hub.button.unsubscribe(callback)
        self._wait_notifications_handled(hub)

    def _inject_notification(self, hub, notify, pause):
        def inject():
            time.sleep(pause)
            if isinstance(hub, ConnectionMock):
                hub.notifications.append((HANDLE, notify))
            else:
                hub.notify_mock.append((HANDLE, notify))

        Thread(target=inject).start()
