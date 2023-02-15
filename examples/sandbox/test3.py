import time
import logging
from time import sleep

from pylgbst.hub import SmartHub
from pylgbst.peripherals import Peripheral, EncodedMotor, TiltSensor, Current, Voltage, COLORS, COLOR_BLACK, COLOR_GREEN

logging.basicConfig(level=logging.DEBUG)

def demo_voltage(hub):

    def callback1(value):
        print("Amperage: %s", value)

    def callback2(value):
        print("Voltage: %s", value)

    print(dir(hub.current))

    hub.current.subscribe(callback1, mode=Current.CURRENT_L, granularity=0)
    hub.current.subscribe(callback1, mode=Current.CURRENT_L, granularity=1)

    hub.voltage.subscribe(callback2, mode=Voltage.VOLTAGE_L, granularity=0)
    hub.voltage.subscribe(callback2, mode=Voltage.VOLTAGE_L, granularity=1)
    time.sleep(5)
    hub.current.unsubscribe(callback1)
    hub.voltage.unsubscribe(callback2)

def demo_led_colors(hub):
    # LED colors demo
    print("LED colors demo")

    # We get a response with payload and port, not x and y here...
    def colour_callback(named):
        print("LED Color callback: %s", named)

    hub.led.subscribe(colour_callback)
    for color in list(COLORS.keys())[1:] + [COLOR_BLACK, COLOR_GREEN]:
        print("Setting LED color to: %s", COLORS[color])
        hub.led.set_color(color)
        sleep(1)

def demo_motor(hub):
    print("Train motor movement demo (on port A)")

    motor = hub.port_A
    print(motor)

    motor.run()
    sleep(3)
    motor.stop()
    sleep(1)
    motor.run(duty=0.2)
    sleep(3)
    motor.stop()
    sleep(1)
    motor.run(duty=-0.2)
    sleep(3)
    motor.stop()
    sleep(3)


DEMO_CHOICES = {
    # 'all': demo_all,
    'voltage': demo_voltage,
    'led_colors': demo_led_colors,
    'motor': demo_motor
    # 'motors_timed': demo_motors_timed,
    # 'motors_angled': demo_motors_angled,
    # 'port_cd_motor': demo_port_cd_motor,
    # 'tilt_sensor': demo_tilt_sensor_simple,
    # 'tilt_sensor_precise': demo_tilt_sensor_precise,
    # 'color_sensor': demo_color_sensor,
    # 'motor_sensors': demo_motor_sensors,
}

hub_1 = SmartHub(address='86996732-BF5A-433D-AACE-5611D4C6271D')   # test hub
# hub_2 = SmartHub(address='F88800F6-F39B-4FD2-AFAA-DD93DA2945A6')   # train hub

# device_1 = SmartHub(address='2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset

# for device in device_1.peripherals:
#     print("device:   ", device)

try:
    demo = DEMO_CHOICES['motor']
    demo(hub_1)
    # demo(hub_2)

    # demo = DEMO_CHOICES['led_colors']
    # demo(hub_1)
    # demo(hub_2)

    # demo = DEMO_CHOICES['voltage']
    # demo(hub_1)
    # demo(hub_2)

finally:
    pass
    hub_1.disconnect()
    # hub_2.disconnect()
