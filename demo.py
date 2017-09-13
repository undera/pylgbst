import logging
import traceback
from time import sleep

from pylegoboost import MoveHub, COLORS_MAP
from pylegoboost.comms import DebugServerConnection, BLEConnection

log = logging.getLogger("demo")


def demo_all(conn):
    movehub = MoveHub(conn)

    demo_led_colors(movehub)


def demo_led_colors(movehub):
    # LED colors demo
    log.info("LED colors demo")
    for color in COLORS_MAP.keys():
        log.info("Setting LED color to: %s", COLORS_MAP[color])
        movehub.led.set_color(color)
        sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    demo_all(connection)
    sleep(10)
