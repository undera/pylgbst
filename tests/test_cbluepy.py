import unittest

import pylgbst.comms.cbluepy as bp_backend


class PeripheralMock(object):
    def __init__(self, addr, addrType, ifaceNumber):
        pass

    def waitForNotifications(self, timeout):
        pass

    def writeCharacteristic(self, handle, data):
        pass

    def withDelegate(self, delegate):
        pass

    def disconnect(self):
        pass


bp_backend.PROPAGATE_DISPATCHER_EXCEPTION = True
bp_backend.btle.Peripheral = lambda *args, **kwargs: PeripheralMock(*args, **kwargs)


class BluepyTestCase(unittest.TestCase):
    def test_get_iface_number(self):
        self.assertEqual(bp_backend._get_iface_number('hci0'), 0)
        self.assertEqual(bp_backend._get_iface_number('hci10'), 10)
        try:
            bp_backend._get_iface_number('ads12')
            self.fail('Missing exception for incorrect value')
        except ValueError:
            pass

    def test_delegate(self):
        def _handler(handle, data):
            _handler.called = True

        delegate = bp_backend.BluepyDelegate(_handler)
        delegate.handleNotification(123, 'qwe')
        self.assertEqual(_handler.called, True)

    def test_threaded_peripheral(self):
        tp = bp_backend.BluepyThreadedPeripheral('address', 'addrType', 'hci0')
        self.assertEqual(tp._addr, 'address')
        self.assertEqual(tp._addrType, 'addrType')
        self.assertEqual(tp._iface_number, 0)
        self.assertNotEqual(tp._dispatcher_thread, None)

        # Schedule some methods to async queue and give them some time to resolve
        tp.set_notify_handler(lambda: '')
        tp.write(123, 'qwe')

        tp._dispatcher_thread.join(1)
        self.assertEqual(tp._dispatcher_thread.is_alive(), True)
        tp.disconnect()

        tp._dispatcher_thread.join(2)
        self.assertEqual(tp._dispatcher_thread.is_alive(), False)
