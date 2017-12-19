import logging
import sys
import time

from pylgbst import MoveHub
from pylgbst.peripherals import EncodedMotor

BASE_SPEED = 0.75
FIELD_WIDTH = 1.1


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
        self.motor_A.timed(0.5, -0.2)
        self.motor_A.subscribe(self._on_rotate, mode=EncodedMotor.SENSOR_SPEED)
        self.motor_A.constant(0.2)
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
        self.motor_A.timed(FIELD_WIDTH, -BASE_SPEED)

    def _on_rotate(self, value):
        logging.debug("Rotation: %s", value)
        self.__last_rotation_value = value

    def _tool_down(self):
        self.motor_external.angled(270, 1)
        self.is_tool_down = True

    def _tool_up(self):
        self.motor_external.angled(-270, 1)
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
        if self.xpos + movx < -FIELD_WIDTH:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx += self.xpos - FIELD_WIDTH

        if self.xpos + movx > FIELD_WIDTH:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx -= self.xpos - FIELD_WIDTH
            self.xpos -= self.xpos - FIELD_WIDTH

        if not movy and not movx:
            logging.warning("No movement, ignored")
            return

        self.xpos += movx
        self.ypos += movy

        length, speed_a, speed_b = self.calc_motor(movx, movy)

        self.motor_AB.timed(length, -speed_a * BASE_SPEED, -speed_b * BASE_SPEED)

        # time.sleep(0.5)

    @staticmethod
    def calc_motor(movx, movy):
        motor_ratio = 1.15
        amovx = float(abs(movx))
        amovy = float(abs(movy))

        length = max(amovx, amovy)

        speed_a = (movx / float(amovx)) if amovx else 0.0
        speed_b = (movy / float(amovy)) if amovy else 0.0

        if amovx >= amovy * motor_ratio:
            speed_b = movy / amovx * motor_ratio
        else:
            speed_a = movx / amovy / motor_ratio

        logging.info("Motor: %s with %s/%s", length, speed_a, speed_b)
        assert -1 <= speed_a <= 1
        assert -1 <= speed_b <= 1

        return length, speed_a, speed_b
