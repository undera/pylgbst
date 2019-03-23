import logging
import traceback

from pylgbst import get_connection_auto
from pylgbst.comms import DebugServerConnection
from pylgbst.hub import MoveHub

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = get_connection_auto()

    hub = MoveHub(conn)
    try:
        hub.motor_AB.constant(0.45, 0.45)
        hub.motor_external.angled(12590, 0.1)
        # time.sleep(180)
    finally:
        hub.motor_AB.stop()
        if hub.motor_external:
            hub.motor_external.stop()
