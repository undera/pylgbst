import time
from binascii import unhexlify

from pylgbst.comms import Connection
from pylgbst.hub import MoveHub
from pylgbst.peripherals import *

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger('test')


class HubMock(MoveHub):
    # noinspection PyUnresolvedReferences
    def __init__(self, connection=None):
        """
        :type connection: ConnectionMock
        """
        super(HubMock, self).__init__(connection if connection else ConnectionMock())
        self.notify_mock = self.connection.notifications
        self.writes = self.connection.writes

    def _report_status(self):
        pass


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

        self.thr = Thread(target=self.notifier)
        self.thr.setDaemon(True)

    def set_notify_handler(self, handler):
        self.notification_handler = handler
        self.thr.start()

    def notifier(self):
        while self.running or self.notifications:
            if self.notification_handler:
                while self.notifications:
                    handle, data = self.notifications.pop(0)
                    self.notification_handler(handle, unhexlify(data.replace(' ', '')))
            time.sleep(0.1)

        self.finished = True

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        self.writes.append((handle, str2hex(data)))

    def connect(self, hub_mac=None):
        super(ConnectionMock, self).connect(hub_mac)
        return self
