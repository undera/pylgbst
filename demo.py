import logging
import traceback
from time import sleep

from pylegoboost import MoveHub, COLORS
from pylegoboost.comms import DebugServerConnection, BLEConnection

log = logging.getLogger("demo")


def demo_all(conn):
    movehub = MoveHub(conn)
    # demo_led_colors(movehub)
    demo_motors_timed(movehub)


def demo_led_colors(movehub):
    # LED colors demo
    log.info("LED colors demo")
    for color in COLORS.keys():
        log.info("Setting LED color to: %s", COLORS[color])
        movehub.led.set_color(color)
        sleep(1)


def demo_motors_timed(movehub):
    log.info("Motors movement demo: timed")
    for level in range(0, 101, 5):
        level /= 100.0
        log.info("Speed level: %s%%", level)
        movehub.motor_A.timed(0.2, level)
        movehub.motor_B.timed(0.2, -level)
    movehub.motor_AB.timed(1.5, -0.2, 0.2)
    movehub.motor_AB.timed(0.5, 1)
    movehub.motor_AB.timed(0.5, -1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    demo_all(connection)
