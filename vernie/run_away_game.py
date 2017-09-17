from vernie import *

robot = Vernie()
running = True



def callback(color, distance):
    speed = (10 - distance + 1) / 10.0
    secs = (10 - distance + 1) / 10.0
    print("Distance is %.1f inches, I'm running back with %s%% speed!" % (distance, int(speed * 100)))
    if speed <= 1:
        robot.motor_AB.timed(secs / 1, -speed, async=True)
        robot.say("Ouch")


def on_btn(pressed):
    global running
    if pressed:
        running = False


robot.led.set_color(COLOR_GREEN)
robot.button.subscribe(on_btn)
robot.say("Place your hand in front of sensor")
robot.color_distance_sensor.subscribe(callback)

while running:
    time.sleep(1)

robot.color_distance_sensor.unsubscribe(callback)
robot.button.unsubscribe(on_btn)
robot.led.set_color(COLOR_NONE)
while robot.led.in_progress():
    time.sleep(1)
