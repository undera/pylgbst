import logging
import traceback

from pylgbst import get_connection_auto
from pylgbst.comms import DebugServerConnection
from pylgbst.hub import MoveHub

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    hub = MoveHub()
    try:
        hub.motor_AB.start_power(0.45, 0.45)
        hub.motor_external.angled(12590, 0.1)
        # time.sleep(180)
    finally:
        hub.motor_AB.stop()
        if hub.motor_external:
            hub.motor_external.stop()
