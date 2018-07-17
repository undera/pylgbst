from binascii import unhexlify

from pylgbst import MoveHub
from pylgbst.comms import Connection
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

    def _wait_for_devices(self):
        pass

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
                    self.notification_handler(handle, unhexlify(data.replace(' ', '')))
            time.sleep(0.1)

        self.finished = True

    def write(self, handle, data):
        log.debug("Writing to %s: %s", handle, str2hex(data))
        self.writes.append((handle, str2hex(data)))
