from vernie import *

robot = Vernie()
running = True

robot.say("Place your hand in front of sensor")


def callback(color, distance):
    if color == COLOR_WHITE:
        robot.motor_AB.timed(0.1, 0.2, async=True)
    elif color != COLOR_NONE:
        print(color)
    else:
        speed = (10 - distance + 1) / 10.0
        secs = (10 - distance + 1) / 10.0
        print("Distance is %.1f inches, I'm running back with %s%% speed!" % (distance, int(speed * 100)))
        if speed <= 1:
            robot.motor_AB.timed(secs / 1, -speed, async=True)


def on_btn(pressed):
    global running
    if pressed:
        running = False


robot.button.subscribe(on_btn)
robot.color_distance_sensor.subscribe(callback)
robot.led.set_color(COLOR_GREEN)

while running:
    time.sleep(1)

robot.led.set_color(COLOR_BLACK)
robot.color_distance_sensor.unsubscribe(callback)
robot.button.unsubscribe(on_btn)
time.sleep(5)  # let color change
