import unittest

from pylgbst.comms import *


class ConnectionTestCase(unittest.TestCase):
    def test_is_device_matched(self):
        conn = Connection()

        hub_address = '1a:2A:3A:4A:5A:6A'
        other_address = 'A1:a2:a3:a4:a5:a6'
        zero_address = '00:00:00:00:00:00'
        hub_name = 'LEGO Move Hub'
        other_name = 'HRM'

        test_matrix = [
            # address,      name,       hub_mac,        expected
            (hub_address, hub_name, hub_address, None, True),
            (hub_address, hub_name, None, hub_name, True),
            (hub_address, None, hub_address, None, True),
            (hub_address, None, None, hub_name, False),
            (hub_address, other_name, hub_address, None, True),
            (hub_address, other_name, None, hub_name, False),
            (other_address, hub_name, hub_address, None, False),
            (other_address, hub_name, None, hub_name, True),
            (other_address, None, hub_address, None, False),
            (other_address, None, None, hub_name, False),
            (other_address, other_name, hub_address, None, False),
            (other_address, other_name, None, hub_name, False),
            (zero_address, hub_name, hub_address, None, False),
            (zero_address, hub_name, None, hub_name, False),
            (zero_address, None, hub_address, None, False),
            (zero_address, None, None, hub_name, False),
            (zero_address, other_name, hub_address, None, False),
            (zero_address, other_name, None, hub_name, False),
        ]

        for address, name, hub_mac, fname, expected in test_matrix:
            matched = conn._is_device_matched(address=address, dev_name=name, hub_mac=hub_mac, find_name=fname)
            self.assertEqual(matched, expected)
