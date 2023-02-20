import logging
import time

from pylgbst.hub import HandsetRemote

logging.basicConfig(level=logging.DEBUG)

# remote = HandsetRemote(address='2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset
remote = HandsetRemote(address='5D319849-7D59-4EBB-A561-0C37C5EF8DCD')  # train handset

print(remote)

# def callback1(value):
#     print("Voltage granularity=4: %s", value)
# remote.voltage.subscribe(callback1, mode=Voltage.VOLTAGE_L, granularity=4)
# time.sleep(10)
# remote.voltage.unsubscribe(callback1)

# def demo_led_colors(remote):
#     # LED colors demo
#     print("LED colors demo")
#
#     # We get a response with payload and port, not x and y here...
#     def colour_callback(named):
#         print("LED Color callback: %s", named)
#
#     remote.led.subscribe(colour_callback)
#     for color in list(COLORS.keys())[1:] + [COLOR_BLACK, COLOR_GREEN]:
#         print("Setting LED color to: %s", COLORS[color])
#         remote.led.set_color(color)
#         time.sleep(1)
#
# demo_led_colors(remote)


def callback_from_button(button, button_set):
    print("value from callback: ", button, button_set)

remote.port_A.subscribe(callback_from_button, mode=2)
remote.port_B.subscribe(callback_from_button)
time.sleep(60)
remote.port_A.unsubscribe(callback_from_button)
remote.port_A.unsubscribe(callback_from_button)
