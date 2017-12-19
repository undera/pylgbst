import logging
import sys
import time

from pylgbst import MoveHub
from pylgbst.peripherals import EncodedMotor

BASE_SPEED = 0.5
CARET_WIDTH = 940


class Plotter(MoveHub):
    def __init__(self, connection=None):
        super(Plotter, self).__init__(connection)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False
        self.__last_rotation_value = sys.maxsize

    def initialize(self):
        self._reset_caret()
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def _reset_caret(self):
        self.motor_A.timed(0.5, -0.3)
        self.motor_A.subscribe(self._on_rotate, mode=EncodedMotor.SENSOR_SPEED)
        self.motor_A.constant(0.3)
        count = 0
        max_tries = 50
        while abs(self.__last_rotation_value) > 5 and count < max_tries:
            logging.debug("Last rot: %s", self.__last_rotation_value)
            time.sleep(10.0 / max_tries)
            count += 1
        logging.debug("Centering tries: %s, last value: %s", count, self.__last_rotation_value)
        self.motor_A.unsubscribe(self._on_rotate)
        self.motor_A.stop()
        if count >= max_tries:
            raise RuntimeError("Failed to center caret")
        self.motor_A.angled(-CARET_WIDTH, BASE_SPEED)

    def _on_rotate(self, value):
        logging.debug("Rotation: %s", value)
        self.__last_rotation_value = value

    def _tool_down(self):
        self.motor_external.angled(270, BASE_SPEED)
        self.is_tool_down = True

    def _tool_up(self):
        self.motor_external.angled(-270, BASE_SPEED)
        self.is_tool_down = False

    def finalize(self):
        if self.is_tool_down:
            self._tool_up()

        self.move(-self.xpos, -self.ypos)

    def move(self, movx, movy):
        if self.is_tool_down:
            self._tool_up()
        self._transfer_to(movx, movy)

    def line(self, movx, movy):
        if not self.is_tool_down:
            self._tool_down()
        self._transfer_to(movx, movy)

    def _transfer_to(self, movx, movy):
        if self.xpos + movx < -CARET_WIDTH:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx += self.xpos - CARET_WIDTH

        if self.xpos + movx > CARET_WIDTH:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx -= self.xpos - CARET_WIDTH
            self.xpos -= self.xpos - CARET_WIDTH

        if not movy and not movx:
            logging.warning("No movement, ignored")
            return

        self.xpos += movx
        self.ypos += movy

        angle, speed_a, speed_b = calc_motor(movx, movy)

        if not speed_b:
            self.motor_A.angled(angle, speed_a * BASE_SPEED)
        elif not speed_a:
            self.motor_B.angled(angle, speed_b * BASE_SPEED)
        else:
            self.motor_AB.angled(angle, speed_a * BASE_SPEED, speed_b * BASE_SPEED)

        # time.sleep(0.5)


def calc_motor(movx, movy):
    amovy = abs(movy)
    amovx = abs(movx)
    angle = max(amovx, amovy)

    speed_a = (movx / float(amovx)) if amovx else 0.0
    speed_b = (movy / float(amovy)) if amovy else 0.0
    if amovx > amovy:
        speed_b = (movy / float(amovx)) if movx else 0
    else:
        speed_a = (movx / float(amovy)) if movy else 0

    if speed_a:
        speed_b *= 2.75
    else:
        angle *= 1.5

    norm = max(abs(speed_a), abs(speed_b))
    speed_a /= norm
    speed_b /= norm
    angle *= speed_a

    logging.info("Motor: %s with %s/%s", angle, speed_a, speed_b)
    assert -1 <= speed_a <= 1
    assert -1 <= speed_b <= 1

    return angle, speed_a, speed_b
