import logging
import time
import traceback

from examples.plotter import Plotter
from pylgbst.comms import DebugServerConnection, BLEConnection


def moves():
    plotter.move(FIELD_WIDTH, FIELD_WIDTH)
    plotter.move(-FIELD_WIDTH, -FIELD_WIDTH)

    plotter.move(FIELD_WIDTH, 0)
    plotter.move(-FIELD_WIDTH, 0)
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

    plotter.move(FIELD_WIDTH / 4.0, 0)
    plotter.circle(FIELD_WIDTH)


class LaserPlotter(Plotter):

    def _tool_down(self):
        super(LaserPlotter, self)._tool_down()
        time.sleep(1)


def lego():
    t = FIELD_WIDTH / 10.0
    h = t * 5.0
    w = t * 3.0

    plotter.line(h, 0)
    plotter.line(0, t)
    plotter.line(-(h - t), 0)
    plotter.line(0, 2 * t)
    plotter.line(-t, 0)
    plotter.line(0, -w)

    plotter.move(0, w + t)

    plotter.line(h, 0)
    plotter.line(0, w)
    plotter.line(-t, 0)
    plotter.line(0, -2 * t)
    plotter.line(-t, 0)
    plotter.line(0, t)
    plotter.line(-t, 0)
    plotter.line(0, -t)
    plotter.line(-t, 0)
    plotter.line(0, 2 * t)
    plotter.line(-t, 0)
    plotter.line(0, -w)

    plotter.move(0, w + t)

    plotter.move(t, 0)
    plotter.line(3 * t, 0)
    plotter.line(t, t)
    plotter.line(0, t)
    plotter.line(-t, t)
    plotter.line(-t, 0)
    plotter.line(0, -t)
    plotter.line(t, 0)
    plotter.line(0, -t)
    plotter.line(-3 * t, 0)
    plotter.line(0, t)
    plotter.line(t, 0)
    plotter.line(0, t)
    plotter.line(-3 * t, 0)
    plotter.line(0, -t)
    plotter.line(t, 0)
    plotter.line(0, -t)
    plotter.line(t, -t)
    plotter.move(-t, 0)

    plotter.move(0, w + t)

    plotter.move(t, 0)
    plotter.line(3 * t, 0)
    plotter.line(t, t)
    plotter.line(0, t)
    plotter.line(-t, t)
    plotter.line(-3 * t, 0)
    plotter.line(-t, -t)
    plotter.line(0, -t)
    plotter.line(t, -t)
    plotter.move(0, t)
    plotter.line(3 * t, 0)
    plotter.line(0, t)
    plotter.line(-3 * t, 0)
    plotter.line(0, -t)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

    plotter = LaserPlotter(conn, 0.4)
    FIELD_WIDTH = plotter.field_width

    try:
        # plotter._tool_down()
        # plotter._tool_up()
        plotter.initialize()

        # moves()
        # triangle()
        # square()
        # cross()
        # romb()
        # circles()
        # plotter.spiral(4, 0.02)
        lego()
        pass
    finally:
        plotter.finalize()
