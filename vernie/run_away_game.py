from vernie import *

logging.basicConfig(level=logging.INFO)

robot = Vernie()
running = True


def callback(color, distance):
    del color  # drop unused
    speed = (10 - distance) / 10
    secs = (10 - distance) / 10
    logging.info("%s => %s %s", distance, speed, secs)
    if speed <= 1:
        robot.motor_AB.timed(secs, -speed)


def on_btn(pressed):
    global running
    if pressed:
        running = False


robot.button.subscribe(on_btn)
robot.color_distance_sensor.subscribe(callback)

while running:
    time.sleep(1)

robot.color_distance_sensor.unsubscribe(callback)
robot.button.unsubscribe(on_btn)
