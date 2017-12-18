import logging
import traceback

from pylgbst import MoveHub, BLEConnection
from pylgbst.comms import DebugServerConnection

BASE_SPEED = 0.5


class Plotter(MoveHub):
    def __init__(self, connection=None):
        super(Plotter, self).__init__(connection)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def initialize(self):
        # TODO: ensure caret is in the middle
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def _tool_down(self):
        self.motor_external.angled(270)
        self.is_tool_down = True

    def _tool_up(self):
        self.motor_external.angled(-270)
        self.is_tool_down = False

    def move_to(self, movx, movy):
        if self.is_tool_down:
            self._tool_up()
        self._transfer_to(movx, movy)

    def line_to(self, movx, movy):
        if not self.is_tool_down:
            self._tool_down()
        self._transfer_to(movx, movy)

    def _transfer_to(self, movx, movy):
        angle = max(movy, movx)
        speed_a = BASE_SPEED
        speed_b = BASE_SPEED * 1.5
        self.motor_AB.angled(angle, speed_a, speed_b)

    def finalize(self):
        if self.is_tool_down:
            self._tool_up()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    plotter = Plotter(connection)
    plotter.initialize()
    # plotter.move_to(100, 100)
    # plotter.move_to(100, -100)
    # plotter.move_to(-100, -100)
    # plotter.move_to(-100, 100)
    plotter.finalize()
