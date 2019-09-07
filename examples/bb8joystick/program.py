import time

from examples.bb8joystick import BB8, Joystick

bb8 = BB8()


def button(p):
    print(p)
    if p == True:
        bb8.color(255, 255, 255)
    else:
        bb8.color(0, 0, 0)


deck = Joystick()
deck.on_button(button)
time.sleep(60)
