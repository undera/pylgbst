import logging
import traceback

from examples.plotter import Plotter, CARET_WIDTH
from pylgbst.comms import DebugServerConnection, BLEConnection


def cross():
    plotter.line(CARET_WIDTH, CARET_WIDTH)
    plotter.move(-CARET_WIDTH, 0)
    plotter.line(CARET_WIDTH, -CARET_WIDTH)


def moves():
    plotter.move(CARET_WIDTH, CARET_WIDTH)
    plotter.move(-CARET_WIDTH, -CARET_WIDTH)

    plotter.move(CARET_WIDTH, 0)
    plotter.move(-CARET_WIDTH, 0)
    plotter.move(0, CARET_WIDTH)
    plotter.move(0, -CARET_WIDTH)


def square():
    plotter.line(CARET_WIDTH, 0)
    plotter.line(0, CARET_WIDTH)
    plotter.line(-CARET_WIDTH, 0)
    plotter.line(0, -CARET_WIDTH)


def triangle():
    plotter.line(CARET_WIDTH, 0)
    plotter.line(0, CARET_WIDTH)
    plotter.line(-CARET_WIDTH, -CARET_WIDTH)


def romb():
    plotter.move(-CARET_WIDTH * 2, 0)
    plotter.line(CARET_WIDTH, CARET_WIDTH)
    plotter.line(CARET_WIDTH, -CARET_WIDTH)
    plotter.line(-CARET_WIDTH, -CARET_WIDTH)
    plotter.line(-CARET_WIDTH, CARET_WIDTH)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

    plotter = Plotter(conn)
    #plotter.initialize()
    # plotter._tool_up() # and plotter._tool_up()

    triangle()
    # moves()
    # square()
    # cross()
    # romb()

    plotter.finalize()
