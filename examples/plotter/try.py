import logging
import traceback

import time

from examples.plotter import Plotter, FIELD_WIDTH
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
    plotter.move(FIELD_WIDTH / 2.0, 0)
    plotter.circle(FIELD_WIDTH / 2.0)

    plotter.move(FIELD_WIDTH / 2.0, 0)
    plotter.circle(FIELD_WIDTH)


class LaserPlotter(Plotter):

    def _tool_down(self):
        super(LaserPlotter, self)._tool_down()
        time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

    plotter = LaserPlotter(conn)

    try:
        # plotter._tool_down()
        # plotter._tool_up()
        plotter.initialize()

        # moves()
        #triangle()
        #square()
        #cross()
        # romb()
        #circles()
        plotter.spiral(4, 0.02)
        pass
    finally:
        plotter.finalize()
