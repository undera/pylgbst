import logging
import traceback
from time import sleep

from pylegoboost import MoveHub, COLORS, EncodedMotor, PORT_D
from pylegoboost.comms import DebugServerConnection, BLEConnection

log = logging.getLogger("demo")


def demo_all(movehub):
    demo_led_colors(movehub)
    demo_motors_timed(movehub)
    demo_motors_angled(movehub)
    demo_port_c_motor(movehub)


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


def demo_motors_angled(movehub):
    log.info("Motors movement demo: angled")
    for angle in range(0, 361, 90):
        log.info("Angle: %s", angle)
        movehub.motor_B.angled(angle, 1)
        sleep(1)
        movehub.motor_B.angled(angle, -1)
        sleep(1)

    movehub.motor_AB.angled(360, 1, -1)
    sleep(1)
    movehub.motor_AB.angled(360, -1, 1)
    sleep(1)


def demo_port_c_motor(movehub):
    portd = EncodedMotor(movehub, PORT_D)
    portd.angled(90, 1)
    sleep(1)
    portd.angled(90, -1)
    sleep(1)


def vernie_head(movehub):
    portd = EncodedMotor(movehub, PORT_D)
    while True:
        angle = 20
        portd.angled(angle, 0.2)
        sleep(2)
        portd.angled(angle, -0.2)
        sleep(2)
        portd.angled(angle, -0.2)
        sleep(2)
        portd.angled(angle, 0.2)
        sleep(2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    hub = MoveHub(connection)
    sleep(1)
    #hub.get_name()

    for x in range(1, 60):
        sleep(1)

        # demo_led_colors(hub)
        # demo_all(movehub)
