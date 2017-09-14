import logging
import time
import unittest
from threading import Thread

from pylgbst import MoveHub, COLOR_RED, LED, EncodedMotor, PORT_AB
from pylgbst.comms import Connection, str2hex, hex2str
from pylgbst.constants import PORT_LED, TILT_STATES, TILT_SENSOR_MODE_2AXIS_FULL, TILT_SENSOR_MODE_2AXIS_SIMPLE, \
    MOVE_HUB_HARDWARE_HANDLE

HANDLE = MOVE_HUB_HARDWARE_HANDLE

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('test')


class ConnectionMock(Connection):
    """
    For unit testing purposes
    """

    def __init__(self):
        super(ConnectionMock, self).__init__()
        self.writes = []
        self.notifications = []
        self.notification_handler = None
        self.running = True
        self.finished = False

    def set_notify_handler(self, handler):
        self.notification_handler = handler
        thr = Thread(target=self.notifier)
        thr.setDaemon(True)
        thr.start()

    def notifier(self):
        while self.running:
            if self.notification_handler:
                while self.notifications:
                    handle, data = self.notifications.pop(0)
                    self.notification_handler(handle, hex2str(data.replace(' ', '')))
            time.sleep(0.1)

        self.finished = True

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        self.writes.append((handle, str2hex(data)))

    def read(self, handle):
        log.debug("Reading from: %s", handle)
        return None  # TODO


class HubMock(MoveHub):
    def __init__(self, connection=None):
        super(HubMock, self).__init__(connection if connection else ConnectionMock())

    def _wait_for_devices(self):
        pass


class GeneralTest(unittest.TestCase):
    def _wait_notifications_handled(self, hub):
        hub.connection.running = False
        for _ in range(1, 180):
            time.sleep(1)
            log.debug("Waiting for notifications to process...")
            if hub.connection.finished:
                log.debug("Done waiting")
                break

    def test_led(self):
        hub = HubMock()
        led = LED(hub, PORT_LED)
        led.set_color(COLOR_RED)
        self.assertEquals("0801813211510009", hub.connection.writes[0][1])

    def test_tilt_sensor(self):
        hub = HubMock()
        hub.connection.notifications.append((HANDLE, '1b0e00 0f00 04 3a 0128000000000100000001'))
        time.sleep(1)

        def callback(param1, param2=None, param3=None):
            if param2 is None:
                log.debug("Tilt: %s", TILT_STATES[param1])
            else:
                log.debug("Tilt: %s %s %s", param1, param2, param3)

        hub.tilt_sensor.subscribe(callback)
        hub.connection.notifications.append((HANDLE, "1b0e000500453a05"))
        hub.connection.notifications.append((HANDLE, "1b0e000a00473a010100000001"))
        time.sleep(1)
        hub.tilt_sensor.subscribe(callback, TILT_SENSOR_MODE_2AXIS_SIMPLE)

        hub.connection.notifications.append((HANDLE, "1b0e000500453a09"))
        time.sleep(1)

        hub.tilt_sensor.subscribe(callback, TILT_SENSOR_MODE_2AXIS_FULL)
        hub.connection.notifications.append((HANDLE, "1b0e000600453a04fe"))
        time.sleep(1)

        self._wait_notifications_handled(hub)
        hub.tilt_sensor.unsubscribe(callback)
        # self.assertEquals("0a01413a000100000001", hub.connection.writes[0][1])

    def test_motor(self):
        conn = ConnectionMock()
        conn.notifications.append((14, '1b0e00 0900 04 39 0227003738'))
        hub = HubMock(conn)
        motor = EncodedMotor(hub, PORT_AB)
        motor.timed(1.5)
        self.assertEquals("0d018139110adc056464647f03", conn.writes[0][1])
        motor.angled(90)
        self.assertEquals("0f018139110c5a0000006464647f03", conn.writes[1][1])

    def test_capabilities(self):
        conn = ConnectionMock()
        conn.notifications.append((14, '1b0e00 0f00 04 01 0125000000001000000010'))
        conn.notifications.append((14, '1b0e00 0f00 04 02 0126000000001000000010'))
        conn.notifications.append((14, '1b0e00 0f00 04 37 0127000100000001000000'))
        conn.notifications.append((14, '1b0e00 0f00 04 38 0127000100000001000000'))
        conn.notifications.append((14, '1b0e00 0900 04 39 0227003738'))
        conn.notifications.append((14, '1b0e00 0f00 04 32 0117000100000001000000'))
        conn.notifications.append((14, '1b0e00 0f00 04 3a 0128000000000100000001'))
        conn.notifications.append((14, '1b0e00 0f00 04 3b 0115000200000002000000'))
        conn.notifications.append((14, '1b0e00 0f00 04 3c 0114000200000002000000'))
        conn.notifications.append((14, '1b0e00 0f00 8202 01'))
        conn.notifications.append((14, '1b0e00 0f00 8202 0a'))

        hub = MoveHub(conn)
        # demo_all(hub)
        self._wait_notifications_handled(hub)
