import logging
import sys
import time

from examples.bb8joystick import joystick
from examples.bb8joystick.bb8 import BB8
from examples.bb8joystick.joystick import Joystick

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG if 'pydevd' in sys.modules else logging.WARNING)

    bb8 = BB8("BB-CC13")
    joystick = Joystick()


    def set_bb_color(r, g, b):
        print("Color", r, g, b)
        bb8.color(r, g, b)


    def set_heading(angle):
        a = int(angle) % 360
        if a < 0:
            a = 360 - a
        print("Angle", a)
        bb8.heading(a)


    try:
        #joystick.on_color_sensor(set_bb_color)
        joystick.on_external_motor(set_heading)
        print("All set up")
        time.sleep(600)
    finally:
        joystick.disconnect()
        bb8.disconnect()
