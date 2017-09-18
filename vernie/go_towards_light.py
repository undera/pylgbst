from vernie import *

logging.basicConfig(level=logging.INFO)

robot = Vernie()
running = True
criterion = max


def on_change_lum(lum):
    global mode_rotation
    if mode_rotation:
        global lum_values
        lum_values.append(lum)
    else:
        global cur_luminosity
        if cur_luminosity < 0:
            cur_luminosity = lum  # initial value
        elif cur_luminosity != lum:
            cur_luminosity = 2  # value above 1 signals end of movement, 'cause lum value is float below 1.0


def on_btn(pressed):
    global running
    if pressed:
        running = False


robot.button.subscribe(on_btn)

robot.color_distance_sensor.subscribe(on_change_lum, CDS_MODE_LUMINOSITY, granularity=0)
while running:
    mode_rotation = True

    # turn around, measuring luminosity
    lum_values = []
    robot.turn(RIGHT, degrees=360, speed=0.2)

    # get max luminosity angle
    idx = lum_values.index(criterion(lum_values))
    angle = int(360.0 * idx / len(lum_values))

    # turn towards light
    if angle > 180:
        robot.turn(LEFT, degrees=360 - angle)
    else:
        robot.turn(RIGHT, degrees=angle)

    # Now let's move until luminosity changes
    # robot.color_distance_sensor.subscribe(get_changed_luminosity, CDS_MODE_LUMINOSITY, granularity=10)

    mode_rotation = False
    cur_luminosity = -1
    while cur_luminosity < 1:
        robot.move(FORWARD, 2)

robot.color_distance_sensor.unsubscribe(on_change_lum)
