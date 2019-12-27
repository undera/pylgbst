from pylgbst.peripherals import COLOR_GREEN, COLOR_NONE
from vernie import *

robot = Vernie()
running = True


def callback(color, distance):
    robot.led.set_color(color)
    speed = (10 - distance + 1) / 10.0
    secs = (10 - distance + 1) / 10.0
    print("Distance is %.1f inches, I'm running back with %s%% speed!" % (distance, int(speed * 100)))
    if speed <= 1:
        robot.motor_AB.timed(secs / 1, -speed)
        robot.say("Ouch")


def on_btn(pressed):
    global running
    if pressed:
        running = False


robot.led.set_color(COLOR_GREEN)
robot.button.subscribe(on_btn)
robot.vision_sensor.subscribe(callback)
robot.say("Place your hand in front of sensor")

while running:
    time.sleep(1)

robot.vision_sensor.unsubscribe(callback)
robot.button.unsubscribe(on_btn)
