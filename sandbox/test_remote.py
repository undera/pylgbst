import logging
import time

from pylgbst.hub import Remote
from pylgbst.peripherals import Voltage, COLORS, COLOR_BLACK, COLOR_GREEN

logging.basicConfig(level=logging.DEBUG)

hub = Remote(address='2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset

def callback1(value):
    print("Voltage granularity=4: %s", value)
hub.voltage.subscribe(callback1, mode=Voltage.VOLTAGE_L, granularity=4)
time.sleep(10)
hub.voltage.unsubscribe(callback1)

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
        time.sleep(1)

demo_led_colors(hub)
