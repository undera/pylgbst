import logging
import sys
import time
import unittest
from binascii import unhexlify
from threading import Thread

from pylgbst.comms import Connection
from pylgbst.hub import MoveHub, Hub
from pylgbst.utilities import str2hex

logging.basicConfig(level=logging.DEBUG if 'pydevd' in sys.modules else logging.INFO)

log = logging.getLogger('test')


class HubTestCase(unittest.TestCase):
    def closing(self, hub):
        """Close `hub` after the test, ending its tasks on the shared event loop"""
        self.addCleanup(lambda: hub.loop_thread.run(hub.aio.close()))
        return hub


class HubMock(Hub):
    """
    :type connection: ConnectionMock
    """

    # noinspection PyUnresolvedReferences
    def __init__(self, conn=None):
        super().__init__(conn if conn else ConnectionMock())
        self.connection = self.connection
        self.notify_mock = self.connection.notifications
        self.writes = self.connection.writes


ATTACH_LED = '0f0004320117000000000106000020'
ATTACH_TILT = '0f00043a0128000000001000000102'
ATTACH_CURRENT = '0f00043b0115000200000000000100'
ATTACH_VOLTAGE = '0f00043c0114000200000000000100'
ATTACH_VISION_C = '0f0004020125000000001000000010'
ATTACH_MOTOR_C = '0f0004020126000000001000000010'
ATTACH_MOTOR_D = '0f0004030126000000001000000010'


def hub_with(*attach_frames):
    """A HubMock with devices attached by the given announcement frames"""
    conn = ConnectionMock()
    conn.notifications.extend(attach_frames)
    hub = HubMock(conn)
    ports = {int(frame[6:8], 16) for frame in attach_frames}
    while not ports.issubset(hub.peripherals):
        time.sleep(0.01)
    return hub


class ConnectionMock(Connection):
    """
    For unit testing purposes
    """

    def __init__(self):
        super().__init__()
        self.writes = []
        self.notifications = []
        self.notification_handler = None
        self.running = True
        self.finished = False

        self.thr = Thread(target=self.notifier)
        self.thr.daemon = True

    def set_notify_handler(self, handler):
        self.notification_handler = handler
        self.thr.start()

    def notifier(self):
        while self.running or self.notifications:
            if self.notification_handler:
                while self.notifications:
                    data = self.notifications.pop(0)
                    s = unhexlify(data.replace(' ', ''))
                    self.notification_handler(MoveHub.HUB_HARDWARE_HANDLE, bytes(s))
            time.sleep(0.01)

        self.finished = True

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        self.writes.append((handle, str2hex(data)))

    def connect(self, hub_mac=None):
        """
        :rtype: ConnectionMock
        """
        super().connect(hub_mac)
        log.debug("Mock connected")
        return self

    def is_alive(self):
        return not self.finished and self.thr.is_alive()

    def notification_delayed(self, payload, pause=0.001):
        def inject():
            time.sleep(pause)
            self.notifications.append(payload)

        Thread(target=inject).start()

    def wait_notifications_handled(self):
        self.running = False
        for _ in range(1, 180):
            time.sleep(0.01)
            log.debug("Waiting for notifications to process...")
            if self.finished:
                log.debug("Done waiting for notifications to process")
                break
