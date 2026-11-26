"""
Demonstrates the Move Hub through the async API: python3 examples/demo.py [-d DEMO] [--mac MAC | --name NAME]
"""
import argparse
import asyncio
import logging

from pylgbst.aio.ble import connect
from pylgbst.aio.hub import MoveHub
from pylgbst.aio.peripherals import COLORS, COLOR_BLACK, Current, EncodedMotor, TiltSensor, Voltage

log = logging.getLogger("demo")


async def demo_led_colors(hub: MoveHub):
    log.info("LED colors demo")
    await hub.led.subscribe(lambda *values: log.info("LED color callback: %s", values))  # plain callbacks work too
    for color in list(COLORS)[1:] + [COLOR_BLACK]:
        log.info("Setting LED color to: %s", COLORS[color])
        await hub.led.set_color(color)
        await asyncio.sleep(1)
    await hub.led.unsubscribe()


async def demo_motors_timed(hub: MoveHub):
    log.info("Motors movement demo: timed")
    for level in range(0, 101, 10):
        level /= 100.0
        log.info("Speed level: %s%%", level * 100)
        await asyncio.gather(hub.motor_A.timed(0.2, level), hub.motor_B.timed(0.2, -level))  # both at once
    await hub.motor_AB.timed(1.5, -0.2, 0.2)
    await hub.motor_AB.timed(0.5, 1)
    await hub.motor_AB.timed(0.5, -1)


async def demo_motors_angled(hub: MoveHub):
    log.info("Motors movement demo: angled")
    for angle in range(0, 361, 90):
        log.info("Angle: %s", angle)
        await hub.motor_B.angled(angle, 1)
        await asyncio.sleep(1)
        await hub.motor_B.angled(angle, -1)
        await asyncio.sleep(1)

    await hub.motor_AB.angled(360, 1, -1)
    await asyncio.sleep(1)
    await hub.motor_AB.angled(360, -1, 1)
    await asyncio.sleep(1)


async def demo_port_cd_motor(hub: MoveHub):
    motor = hub.motor_external
    if motor is None:
        log.warning("Motor not found on ports C or D")
        return

    log.info("Rotation motor is on port 0x%x", motor.port)
    for degrees, speed, pause in ((20, 0.2, 3), (20, -0.2, 1), (20, -0.1, 2), (20, 0.1, 1)):
        await motor.angled(degrees, speed)
        await asyncio.sleep(pause)


async def demo_tilt_sensor_simple(hub: MoveHub):
    log.info("Tilt sensor simple test. Turn device in different ways.")
    limit = 10
    count = 0
    async for state, in hub.tilt_sensor.values(TiltSensor.MODE_3AXIS_SIMPLE):
        count += 1
        log.info("Tilt #%s of %s: %s=%s", count, limit, TiltSensor.TRI_STATES[state], state)
        if count == limit:
            break  # leaving the loop switches the sensor updates off


async def demo_tilt_sensor_precise(hub: MoveHub):
    log.info("Tilt sensor precise test. Turn device in different ways.")
    limit = 50
    count = 0
    async for roll, pitch, yaw in hub.tilt_sensor.values(TiltSensor.MODE_3AXIS_ACCEL):
        count += 1
        log.info("Tilt #%s of %s: roll:%s pitch:%s yaw:%s", count, limit, roll, pitch, yaw)
        if count == limit:
            break


async def demo_color_sensor(hub: MoveHub):
    if hub.vision_sensor is None:
        log.warning("Vision sensor not found on ports C or D")
        return

    log.info("Color sensor test: wave your hand in front of it")
    limit = 20
    count = 0
    async for color, distance in hub.vision_sensor.values():
        count += 1
        log.info("#%s/%s: Color %s, distance %s", count, limit, COLORS[color], distance)
        if count == limit:
            break


async def demo_motor_sensors(hub: MoveHub):
    log.info("Motor rotation sensors test. Rotate all available motors once")
    motors = {"A": hub.motor_A, "B": hub.motor_B}
    if hub.motor_external is not None:
        motors["external"] = hub.motor_external

    async def until_rotated(name: str, motor: EncodedMotor):
        async for angle, in motor.values(EncodedMotor.SENSOR_ANGLE):
            log.info("Motor %s: %s", name, angle)
            if abs(angle) > 30:
                log.info("Motor %s rotated", name)
                break

    await asyncio.gather(*(until_rotated(name, motor) for name, motor in motors.items()))  # watch all at once


async def demo_voltage(hub: MoveHub):
    async def watch(name, sensor, mode):
        async for value, in sensor.values(mode, granularity=0):
            log.info("%s: %s", name, value)

    try:
        await asyncio.wait_for(asyncio.gather(watch("Amperage", hub.current, Current.CURRENT_L),
                                              watch("Voltage", hub.voltage, Voltage.VOLTAGE_L)), 5)
    except asyncio.TimeoutError:
        pass  # the watching ran for its 5 seconds


async def demo_all(hub: MoveHub):
    for demo in (demo_motors_timed, demo_motors_angled, demo_port_cd_motor, demo_led_colors, demo_tilt_sensor_simple,
                 demo_tilt_sensor_precise, demo_color_sensor, demo_motor_sensors, demo_voltage):
        await demo(hub)


DEMO_CHOICES = {
    'all': demo_all,
    'voltage': demo_voltage,
    'led_colors': demo_led_colors,
    'motors_timed': demo_motors_timed,
    'motors_angled': demo_motors_angled,
    'port_cd_motor': demo_port_cd_motor,
    'tilt_sensor': demo_tilt_sensor_simple,
    'tilt_sensor_precise': demo_tilt_sensor_precise,
    'color_sensor': demo_color_sensor,
    'motor_sensors': demo_motor_sensors,
}


async def main(options):
    connection = await connect(options.mac, options.name, use_relay=not options.no_relay)
    async with MoveHub(connection) as hub:
        await DEMO_CHOICES[options.demo](hub)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(relativeCreated)d\t%(levelname)s\t%(name)s\t%(message)s')
    parser = argparse.ArgumentParser(description='Demonstrate Move Hub communications')
    parser.add_argument('-d', '--demo', default='all', choices=sorted(DEMO_CHOICES), help="demo to run, default all")
    parser.add_argument('--mac', help="hub address")
    parser.add_argument('--name', default=MoveHub.DEFAULT_NAME, help="hub name, default %(default)r")
    parser.add_argument('--no-relay', action='store_true', help="connect over Bluetooth even if the relay runs")
    asyncio.run(main(parser.parse_args()))
