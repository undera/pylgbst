# coding=utf-8
import time
from time import sleep

from pylgbst import *
from pylgbst.comms import DebugServerConnection
from pylgbst.hub import MoveHub, math
from pylgbst.peripherals import EncodedMotor, TiltSensor, Current, Voltage, COLORS, COLOR_BLACK

log = logging.getLogger("demo")


def demo_led_colors(movehub):
    # LED colors demo
    log.info("LED colors demo")
    movehub.led.subscribe(lambda x, y: None)
    for color in list(COLORS.keys())[1:] + [COLOR_BLACK]:
        log.info("Setting LED color to: %s", COLORS[color])
        movehub.led.set_color(color)
        sleep(1)


def demo_motors_timed(movehub):
    log.info("Motors movement demo: timed")
    for level in range(0, 101, 10):
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


def demo_tilt_sensor_simple(movehub):
    log.info("Tilt sensor simple test. Turn device in different ways.")
    demo_tilt_sensor_simple.cnt = 0
    limit = 10

    def callback(state):
        demo_tilt_sensor_simple.cnt += 1
        log.info("Tilt #%s of %s: %s=%s", demo_tilt_sensor_simple.cnt, limit, TiltSensor.TRI_STATES[state], state)

    movehub.tilt_sensor.subscribe(callback, mode=TiltSensor.MODE_3AXIS_SIMPLE)
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

    movehub.tilt_sensor.subscribe(callback, mode=TiltSensor.MODE_3AXIS_ACCEL)
    while demo_tilt_sensor_simple.cnt < limit:
        time.sleep(1)

    movehub.tilt_sensor.unsubscribe(callback)


def demo_color_sensor(movehub):
    log.info("Color sensor test: wave your hand in front of it")
    demo_color_sensor.cnt = 0
    limit = 20

    def callback(color, distance=None):
        demo_color_sensor.cnt += 1
        log.info("#%s/%s: Color %s, distance %s", demo_color_sensor.cnt, limit, COLORS[color], distance)

    movehub.vision_sensor.subscribe(callback)
    while demo_color_sensor.cnt < limit:
        time.sleep(1)

    movehub.vision_sensor.unsubscribe(callback)


def demo_motor_sensors(movehub):
    log.info("Motor rotation sensors test. Rotate all available motors once")
    demo_motor_sensors.states = {movehub.motor_A: 0, movehub.motor_B: 0, movehub.motor_external: 0}

    def callback_a(param1):
        demo_motor_sensors.states[movehub.motor_A] = param1
        log.info("%s", demo_motor_sensors.states)

    def callback_b(param1):
        demo_motor_sensors.states[movehub.motor_B] = param1
        log.info("%s", demo_motor_sensors.states)

    def callback_e(param1):
        demo_motor_sensors.states[movehub.motor_external] = param1
        log.info("%s", demo_motor_sensors.states)

    movehub.motor_A.subscribe(callback_a)
    movehub.motor_B.subscribe(callback_b)

    if movehub.motor_external is not None:
        demo_motor_sensors.states[movehub.motor_external] = None
        movehub.motor_external.subscribe(callback_e)

    while not all([x is not None and abs(x) > 30 for x in demo_motor_sensors.states.values()]):
        time.sleep(1)

    movehub.motor_A.unsubscribe(callback_a)
    movehub.motor_B.unsubscribe(callback_b)

    if movehub.motor_external is not None:
        demo_motor_sensors.states[movehub.motor_external] = None
        movehub.motor_external.unsubscribe(callback_e)


def demo_voltage(movehub):
    def callback1(value):
        log.info("Amperage: %s", value)

    def callback2(value):
        log.info("Voltage: %s", value)

    movehub.current.subscribe(callback1, mode=Current.CURRENT_L, granularity=0)
    movehub.current.subscribe(callback1, mode=Current.CURRENT_L, granularity=1)

    movehub.voltage.subscribe(callback2, mode=Voltage.VOLTAGE_L, granularity=0)
    movehub.voltage.subscribe(callback2, mode=Voltage.VOLTAGE_L, granularity=1)
    time.sleep(5)
    movehub.current.unsubscribe(callback1)
    movehub.voltage.unsubscribe(callback2)


def demo_all(movehub):
    demo_voltage(movehub)
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

    hub = MoveHub()
    demo_all(hub)
    hub.disconnect()
