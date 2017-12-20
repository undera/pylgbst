import logging
import math
import time

from pylgbst import MoveHub, ColorDistanceSensor, COLORS, COLOR_RED, COLOR_CYAN


class Plotter(MoveHub):
    MOTOR_RATIO = 1.15

    def __init__(self, connection=None, base_speed=1.0):
        super(Plotter, self).__init__(connection)
        self.base_speed = base_speed
        self.field_width = 0.925 / self.base_speed
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False
        self._marker_color = False

    def initialize(self):
        self._reset_caret()
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def _reset_caret(self):
        self.motor_A.timed(0.2, self.base_speed)
        self.color_distance_sensor.subscribe(self._on_distance, mode=ColorDistanceSensor.COLOR_DISTANCE_FLOAT,
                                             granularity=5)
        try:
            self.motor_A.constant(-self.base_speed)
            count = 0
            max_tries = 50
            while not self._marker_color and count < max_tries:
                time.sleep(5.0 / self.base_speed / max_tries)
                count += 1
            logging.info("Centering tries: %s, color #%s", count,
                         COLORS[self._marker_color] if self._marker_color else None)
            if count >= max_tries:
                raise RuntimeError("Failed to center caret")
        finally:
            self.motor_A.stop()
            self.color_distance_sensor.unsubscribe(self._on_distance)

        self.motor_A.timed(self.field_width, self.base_speed)

    def _on_distance(self, color, distance):
        self._marker_color = None
        logging.debug("Color: %s, distance %s", COLORS[color], distance)
        if color in (COLOR_RED, COLOR_CYAN):
            if distance <= 3:
                self._marker_color = color

    def finalize(self):
        self.motor_AB.stop()
        self.motor_external.stop()
        if self.is_tool_down:
            self._tool_up()

    def _tool_down(self):
        self.motor_external.angled(-270, 1)
        self.is_tool_down = True

    def _tool_up(self):
        self.motor_external.angled(270, 1)
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
        if self.xpos + movx < -self.field_width:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx += self.xpos - self.field_width

        if self.xpos + movx > self.field_width:
            logging.warning("Invalid xpos: %s", self.xpos)
            movx -= self.xpos - self.field_width
            self.xpos -= self.xpos - self.field_width

        if not movy and not movx:
            logging.warning("No movement, ignored")
            return

        self.xpos += movx
        self.ypos += movy

        length, speed_a, speed_b = self._calc_motor(movx, movy)

        self.motor_AB.timed(length * 4.0, -speed_a * self.base_speed / 4.0, -speed_b * self.base_speed / 4.0)

        # time.sleep(0.5)

    @staticmethod
    def _calc_motor(movx, movy):
        amovx = float(abs(movx))
        amovy = float(abs(movy))

        length = max(amovx, amovy)

        speed_a = (movx / float(amovx)) if amovx else 0.0
        speed_b = (movy / float(amovy)) if amovy else 0.0

        if amovx >= amovy * Plotter.MOTOR_RATIO:
            speed_b = movy / amovx * Plotter.MOTOR_RATIO
        else:
            speed_a = movx / amovy / Plotter.MOTOR_RATIO

        logging.info("Motor: %s with %s/%s", length, speed_a, speed_b)
        assert -1 <= speed_a <= 1
        assert -1 <= speed_b <= 1

        return length, speed_a, speed_b

    def circle(self, radius):
        if not self.is_tool_down:
            self._tool_down()

        parts = int(2 * math.pi * radius * 7)
        dur = 0.025
        logging.info("Circle of radius %s, %s parts with %s time", radius, parts, dur)
        speeds = []
        for x in range(0, parts):
            speed_a = math.sin(x * 2.0 * math.pi / float(parts))
            speed_b = math.cos(x * 2.0 * math.pi / float(parts))
            speeds.append((speed_a, speed_b))
            logging.debug("A: %s, B: %s", speed_a, speed_b)
        speeds.append((0, 0))

        for speed_a, speed_b in speeds:
            spa = speed_a * self.base_speed
            spb = -speed_b * self.base_speed * self.MOTOR_RATIO
            logging.info("Motor speeds: %.3f / %.3f", spa, spb)
            self.motor_AB.constant(spa, spb)
            time.sleep(dur)

    def spiral(self, rounds, growth):
        if not self.is_tool_down:
            self._tool_down()

        dur = 0.00
        parts = 16
        speeds = []
        for r in range(0, rounds):
            logging.info("Round: %s", r)

            for x in range(0, parts):
                speed_a = math.sin(x * 2.0 * math.pi / float(parts))
                speed_b = math.cos(x * 2.0 * math.pi / float(parts))
                dur += growth
                speeds.append((speed_a, speed_b, dur))
                logging.debug("A: %s, B: %s", speed_a, speed_b)
        speeds.append((0, 0, 0))

        for speed_a, speed_b, dur in speeds:
            spa = speed_a * self.base_speed
            spb = -speed_b * self.base_speed * self.MOTOR_RATIO
            self.motor_AB.constant(spa, spb)
            logging.info("Motor speeds: %.3f / %.3f", spa, spb)
            time.sleep(dur)
