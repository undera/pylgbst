import logging
import traceback
from time import sleep

from pylgbst import MoveHub, COLORS, EncodedMotor, PORT_D
from pylgbst.comms import DebugServerConnection, BLEConnection

log = logging.getLogger("demo")


def demo_all(movehub):
    demo_led_colors(movehub)
    demo_motors_timed(movehub)
    demo_motors_angled(movehub)
    demo_port_cd_motor(movehub)


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
        log.info("Speed level: %s%%", level * 100)
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


def demo_port_cd_motor(movehub):
    motor = None
    if isinstance(movehub.port_D, EncodedMotor):
        log.info("Rotation motor is on port D")
        motor = movehub.port_D
    elif isinstance(movehub.port_C, EncodedMotor):
        log.info("Rotation motor is on port C")
        motor = movehub.port_C
    else:
        log.warning("Motor not found on ports C or D")

    if motor:
        motor.angled(20, 0.2)
        sleep(3)
        motor.angled(20, -0.2)
        sleep(1)

        motor.angled(20, -0.1)
        sleep(2)
        motor.angled(20, 0.1)
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
    logging.basicConfig(level=logging.INFO)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    hub = MoveHub(connection)
    demo_all(hub)

    #sleep(1)
    # hub.get_name()
    #demo_port_cd_motor(hub)
    # demo_led_colors(hub)
    #sleep(1)
