# coding=utf-8
import logging
import time

from examples.plotter import Plotter
from pylgbst.hub import EncodedMotor, MoveHub
from tests import HubMock


def moves():
    plotter.move(-FIELD_WIDTH, 0)
    plotter.move(FIELD_WIDTH * 2, 0)
    plotter.move(-FIELD_WIDTH, 0)

    plotter.move(FIELD_WIDTH, FIELD_WIDTH)
    plotter.move(-FIELD_WIDTH, -FIELD_WIDTH)

    plotter.move(0, FIELD_WIDTH)
    plotter.move(0, -FIELD_WIDTH)


def cross():
    plotter.line(FIELD_WIDTH, FIELD_WIDTH)
    plotter.move(-FIELD_WIDTH, 0)
    plotter.line(FIELD_WIDTH, -FIELD_WIDTH)


def square():
    plotter.line(FIELD_WIDTH, 0)
    plotter.line(0, FIELD_WIDTH)
    plotter.line(-FIELD_WIDTH, 0)
    plotter.line(0, -FIELD_WIDTH)


def triangle():
    plotter.line(FIELD_WIDTH, 0)
    plotter.line(0, FIELD_WIDTH)
    plotter.line(-FIELD_WIDTH, -FIELD_WIDTH)


def romb():
    plotter.move(-FIELD_WIDTH, 0)
    plotter.line(FIELD_WIDTH, FIELD_WIDTH * 2)
    plotter.line(FIELD_WIDTH, -FIELD_WIDTH * 2)
    plotter.line(-FIELD_WIDTH, -FIELD_WIDTH * 2)
    plotter.line(-FIELD_WIDTH, FIELD_WIDTH * 2)


def circles():
    plotter.move(FIELD_WIDTH / 4.0, 0)
    plotter.circle(FIELD_WIDTH / 2.0)

    plotter.move(FIELD_WIDTH / 2.0, 0)
    plotter.circle(FIELD_WIDTH)


def square_spiral():
    rounds = 5
    step = plotter.base_speed / rounds / 5.0
    for r in range(1, rounds):
        plotter.line(step * r * 4, 0)
        plotter.line(0, step * (r * 4 + 1))
        plotter.line(-step * (r * 4 + 2), 0)
        plotter.line(0, -step * (r * 4 + 3))
    plotter.line(step * 2.0, step * 2.0)  # cut


def christmas_tree():
    t = FIELD_WIDTH / 3
    plotter.line(t, t)
    plotter.line(-t * 0.5, 0)
    plotter.line(t, t)
    plotter.line(-t * 0.5, 0)
    plotter.line(t, t)

    plotter.line(-t * 3.5, 0)

    plotter.line(t, -t)
    plotter.line(-t * 0.5, 0)
    plotter.line(t, -t)
    plotter.line(-t * 0.5, 0)
    plotter.line(t, -t)


def try_speeds():
    speeds = [x * 1.0 / 10.0 for x in range(1, 11)]
    for s in speeds:
        logging.info("%s", s)
        plotter.both.start_power(s, -s)
        time.sleep(1)
    for s in reversed(speeds):
        logging.info("%s", s)
        plotter.both.start_power(-s, s)
        time.sleep(1)


def snowflake(scale=1.0):
    a = [300, 232,
         351, 144,
         307, 68,
         350, 45,
         379, 94,
         413, 36,
         456, 61,
         422, 119,
         482, 118,
         481, 167,
         394, 168,
         343, 256,
         444, 256,
         488, 179,
         530, 204,
         500, 256,
         569, 256,
         582, 280]
    prev = None
    vals = []
    maxval = 0
    for i in range(0, len(a)):
        if i % 2:
            continue

        maxval = max(maxval, abs(a[i]), abs(a[i + 1]))
        if prev:
            vals.append((a[i] - prev[0], a[i + 1] - prev[1]))
        prev = a[i], a[i + 1]

    assert len(vals) == len(a) / 2 - 1

    vals = [(x[0] / float(maxval), x[1] / float(maxval)) for x in vals]

    logging.info("Moves: %s", vals)
    zoom = FIELD_WIDTH * scale
    for item in vals:
        plotter.line(item[0] * zoom, item[1] * zoom)

    for item in reversed(vals):
        plotter.line(-item[0] * zoom, item[1] * zoom)

    for item in vals:
        plotter.line(-item[0] * zoom, -item[1] * zoom)

    for item in reversed(vals):
        plotter.line(item[0] * zoom, -item[1] * zoom)

    plotter.line(0.05 * zoom, 0)


def angles_experiment():
    parts = 2
    for x in range(0, parts + 1):
        movy = x * 1.0 / parts
        plotter.line(1.0, movy)
        plotter.move(-1.0, -movy)
        logging.info("%s", movy)

    for x in range(0, parts):
        movx = x * 1.0 / parts
        plotter.line(movx, 1.0)
        plotter.move(-movx, -1.0)
        logging.info("%s", movx)

        """
        path = 1000

        spd_b = x * plotter.base_speed / parts
        spd_a = plotter.base_speed - spd_b

        angle = path * (1.0 + spd_b / spd_a)
        logging.info("%s, %s, %s", angle, spd_a, spd_b)

        plotter.motor_AB.angled(angle, spd_a, -spd_b)
        plotter._compensate_wheels_backlash(-1)
        plotter.motor_AB.angled(-angle, spd_a, -spd_b)
        plotter._compensate_wheels_backlash(1)
        """


class MotorMock(EncodedMotor):
    pass


def get_hub_mock():
    hub = HubMock()
    hub.motor_A = MotorMock(hub, MoveHub.PORT_A)
    hub.motor_B = MotorMock(hub, MoveHub.PORT_B)
    hub.motor_AB = MotorMock(hub, MoveHub.PORT_AB)
    hub.motor_external = MotorMock(hub, MoveHub.PORT_C)
    return hub


def interpret_command(cmd, plotter):
    scale = 0.075
    for c in cmd.lower():
        if c == u'л':
            plotter._transfer_to(-scale, 0)
        elif c == u'п':
            plotter._transfer_to(scale, 0)
        elif c == u'н':
            plotter._transfer_to(0, -scale)
        elif c == u'в':
            plotter._transfer_to(0, scale)
        elif c == u'1':
            plotter._tool_down()
        elif c == u'0':
            plotter._tool_up()
        elif c == u' ':
            pass
        else:
            logging.warning(u"Неизвестная команда: %s", c)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('').setLevel(logging.DEBUG)

    hub = MoveHub() if 1 else get_hub_mock()

    plotter = Plotter(hub, 0.75)
    FIELD_WIDTH = 0.9

    try:
        """
        while True:
            cmd = six.moves.input("программа> ").decode('utf8')
            if not cmd.strip():
                continue
            plotter.initialize()
            interpret_command(cmd, plotter)
            plotter.finalize()
        """

        time.sleep(1)
        plotter.initialize()

        # snowflake(0.75)
        # christmas_tree()
        # square_spiral()
        # lego(plotter, FIELD_WIDTH / 7.0)

        # plotter._tool_down()
        # angles_experiment()
        # try_speeds()
        # moves()
        # triangle()
        # square()
        # cross()
        # romb()
        # circles()
        # plotter.spiral(4, 0.02)
        # plotter.rectangle(FIELD_WIDTH / 5.0, FIELD_WIDTH / 5.0, solid=True)

        pass
    finally:
        plotter.finalize()
