from time import sleep

from pylgbst import *

log = logging.getLogger("demo")


def demo_tilt_sensor_simple(movehub):
    log.info("Tilt sensor simple test. Turn device in different ways.")
    demo_tilt_sensor_simple.cnt = 0
    limit = 10

    def callback(param1):
        demo_tilt_sensor_simple.cnt += 1
        log.info("Tilt #%s of %s: %s", demo_tilt_sensor_simple.cnt, limit, TILT_STATES[param1])

    movehub.tilt_sensor.subscribe(callback)
    while demo_tilt_sensor_simple.cnt < limit:
        time.sleep(1)

    movehub.tilt_sensor.unsubscribe(callback)


def demo_tilt_sensor_precise(movehub):
    log.info("Tilt sensor precise test. Turn device in different ways.")
    demo_tilt_sensor_simple.cnt = 0
    limit = 50

    def callback(pitch, roll, yaw):
        demo_tilt_sensor_simple.cnt += 1
        log.info("Tilt #%s of %s: roll:%s pitch:%s yaw:%s", demo_tilt_sensor_simple.cnt, limit, pitch, roll, yaw)

    movehub.tilt_sensor.subscribe(callback, mode=TILT_MODE_FULL)
    while demo_tilt_sensor_simple.cnt < limit:
        time.sleep(1)

    movehub.tilt_sensor.unsubscribe(callback)


def demo_led_colors(movehub):
    # LED colors demo
    log.info("LED colors demo")
    for color in COLORS.keys()[1:] + [COLOR_BLACK]:
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


def demo_color_sensor(movehub):
    log.info("Color sensor test: wave your hand in front of it")
    demo_color_sensor.cnt = 0
    limit = 20

    def callback(color, distance=None):
        demo_color_sensor.cnt += 1
        color = COLORS[color] if color in COLORS else color
        log.info("#%s/%s: Color %s, distance %s", demo_color_sensor.cnt, limit, color, distance)

    movehub.color_distance_sensor.subscribe(callback)
    while demo_color_sensor.cnt < limit:
        time.sleep(1)

    movehub.color_distance_sensor.unsubscribe(callback)


def demo_motor_sensors(movehub):
    log.info("Motor rotation sensors test. Rotate all available motors once")
    demo_motor_sensors.states = {
        movehub.motor_A: [None, None],  # callback and last value
        movehub.motor_B: [None, None],  # callback and last value
    }

    if movehub.external_motor is not None:
        demo_motor_sensors.states[movehub.external_motor] = [None, None]

    def callback(mtr, param1):
        demo_motor_sensors.states[mtr][1] = param1
        log.info("%s", {x: demo_motor_sensors.states[x][1] for x in demo_motor_sensors.states})

    for motor in demo_motor_sensors.states:
        demo_motor_sensors.states[motor][0] = lambda x: callback(motor, x)
        motor.subscribe(demo_motor_sensors.states[motor][0])

    while None in [x[1] for x in demo_motor_sensors.states.values()]:  # demo_motor_sensors.states < limit:
        time.sleep(1)

    for motor in demo_motor_sensors.states:
        motor.unsubscribe(demo_motor_sensors.states[motor][0])


def demo_all(movehub):
    demo_led_colors(movehub)
    demo_motors_timed(movehub)
    demo_motors_angled(movehub)
    demo_port_cd_motor(movehub)
    demo_tilt_sensor_simple(movehub)
    demo_tilt_sensor_precise(movehub)
    demo_color_sensor(movehub)
    demo_motor_sensors(movehub)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    hub = MoveHub(connection)

    demo_motor_sensors(hub)

    # demo_all(hub)

    log.info("Sleeping 60s")
    sleep(60)

    # sleep(1)
    # hub.get_name()
    # demo_port_cd_motor(hub)
    # demo_led_colors(hub)
    # sleep(1)
