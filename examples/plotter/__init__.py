import logging
import sys
import time
import traceback

from pylgbst import MoveHub, BLEConnection
from pylgbst.comms import DebugServerConnection
from pylgbst.peripherals import EncodedMotor

BASE_SPEED = 0.5
CARET_WIDTH = -940


class Plotter(MoveHub):
    def __init__(self, connection=None):
        super(Plotter, self).__init__(connection)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False
        self.__last_rotation_value = sys.maxsize

    def initialize(self):
        self.motor_A.subscribe(self._on_rotate, mode=EncodedMotor.SENSOR_SPEED)
        self.motor_A.constant(0.4)
        count = 0
        max_tries = 50
        while self.__last_rotation_value > 5 and count < max_tries:
            logging.info("Last rot: %s", self.__last_rotation_value)
            time.sleep(5.0 / max_tries)
            count += 1
        logging.info("Tries: %s, last: %s", count, self.__last_rotation_value)
        self.motor_A.unsubscribe(self._on_rotate)
        self.motor_A.stop()
        if count >= max_tries:
            raise RuntimeError("Failed to center caret")
        self.motor_A.angled(CARET_WIDTH, BASE_SPEED)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def _on_rotate(self, value):
        logging.info("Rotation: %s", value)
        self.__last_rotation_value = value

    def _tool_down(self):
        self.motor_external.angled(270, BASE_SPEED)
        self.is_tool_down = True

    def _tool_up(self):
        self.motor_external.angled(-270, BASE_SPEED)
        self.is_tool_down = False

    def move(self, movx, movy):
        if self.is_tool_down:
            self._tool_up()
        self._transfer_to(movx, movy)

    def line(self, movx, movy):
        if not self.is_tool_down:
            self._tool_down()
        self._transfer_to(movx, movy)

    def _transfer_to(self, movx, movy):
        angle = max(abs(movy), abs(movx))
        speed_a = BASE_SPEED
        speed_b = BASE_SPEED * 0.5
        self.motor_AB.angled(angle, speed_a, speed_b)

    def finalize(self):
        if self.is_tool_down:
            self._tool_up()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

    plotter = Plotter(conn)
    plotter.initialize()
    plotter.line(100, 100)
    plotter.line(100, -100)
    plotter.line(-100, -100)
    plotter.line(-100, 100)
    plotter.finalize()
