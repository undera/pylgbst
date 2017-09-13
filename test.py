import logging
import unittest

from demo import demo_all
from pylegoboost.comms import ConnectionMock

logging.basicConfig(level=logging.DEBUG)


class GeneralTest(unittest.TestCase):
    def test_capabilities(self):
        conn = ConnectionMock()
        demo_all(conn)
