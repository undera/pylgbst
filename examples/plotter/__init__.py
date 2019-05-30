import logging
import math
import time

from pylgbst.peripherals import VisionSensor, COLOR_RED, COLOR_CYAN, COLORS


class Plotter(object):
    MOTOR_RATIO = 1.425
    ROTATE_UNIT = 2100

    def __init__(self, hub, base_speed=1.0):
        """

        :type hub: pylgbst.hub.MoveHub
        """
        self._hub = hub
        self.caret = self._hub.motor_A
        self.wheels = self._hub.motor_B
        self.both = self._hub.motor_AB

        self.base_speed = float(base_speed)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False
        self._marker_color = False
        self.__last_wheel_dir = 1

    def initialize(self):
        self._reset_caret()
        self._compensate_wheels_backlash(1)
        self._compensate_wheels_backlash(-1)
        self.xpos = 0
        self.ypos = 0
        self.is_tool_down = False

    def _reset_caret(self):
        if not self._hub.vision_sensor:
            logging.warning("No color/distance sensor, cannot center caret")
            return

        self._hub.vision_sensor.subscribe(self._on_distance, mode=VisionSensor.COLOR_DISTANCE_FLOAT)
        self.caret.timed(0.5, 1)
        try:
            self.caret.start_power(-1)
            count = 0
            max_tries = 50
            while self._marker_color not in (COLOR_RED, COLOR_CYAN) and count < max_tries:
                time.sleep(30.0 / max_tries)
                count += 1
            self._hub.vision_sensor.unsubscribe(self._on_distance)
            clr = COLORS[self._marker_color] if self._marker_color else None
            logging.info("Centering tries: %s, color #%s", count, clr)
            if count >= max_tries:
                raise RuntimeError("Failed to center caret")
        finally:
            self.caret.stop()
            self._hub.vision_sensor.unsubscribe(self._on_distance)

        if self._marker_color == COLOR_CYAN:
            self.move(-0.1, 0)
        else:
            self.move(-1.0, 0)

    def _on_distance(self, color, distance):
        self._marker_color = None
        logging.debug("Color: %s, distance %s", COLORS[color], distance)
        if color in (COLOR_RED, COLOR_CYAN):
            if distance <= 3:
                self._marker_color = color

    def _compensate_wheels_backlash(self, movy):
        """
        corrects backlash of wheels gear system
        """
        if not movy:
            return
        wheel_dir = movy / abs(movy)
        if wheel_dir == -self.__last_wheel_dir:
            self.wheels.angled(270, -wheel_dir)
        self.__last_wheel_dir = wheel_dir

    def finalize(self):
        if self.is_tool_down:
            self._tool_up()
        self.both.stop()

    def _tool_down(self):
        self.is_tool_down = True
        self._hub.motor_external.angled(-270, 1)
        time.sleep(1.0)  # for laser to heat up

    def _tool_up(self):
        self._hub.motor_external.angled(270, 1)
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
        if not movy and not movx:
            logging.warning("No movement, ignored")
            return

        self._compensate_wheels_backlash(movy)

        self.xpos += movx
        self.ypos += movy

        length, speed_a, speed_b = self._calc_motor_angled(movx, movy * self.MOTOR_RATIO)
        logging.info("Motors: %.3f with %.3f/%.3f", length, speed_a, speed_b)

        if not speed_b:
            self.caret.angled(length * 2.0, -speed_a * self.base_speed * 0.75)  # slow down to cut better
        elif not speed_a:
            self.wheels.angled(length * 2.0, -speed_b * self.base_speed * 0.75)  # slow down to cut better
        else:
            self.both.angled(length, -speed_a * self.base_speed, -speed_b * self.base_speed)

    @staticmethod
    def _calc_motor_timed(movx, movy):
        amovx = float(abs(movx))
        amovy = float(abs(movy))

        length = max(amovx, amovy)

        speed_a = (movx / float(amovx)) if amovx else 0.0
        speed_b = (movy / float(amovy)) if amovy else 0.0

        if amovx >= amovy:
            speed_b = movy / amovx
        else:
            speed_a = movx / amovy

        assert -1 <= speed_a <= 1
        assert -1 <= speed_b <= 1

        return length, speed_a, speed_b

    @staticmethod
    def _calc_motor_angled(movx, movy):
        amovx = abs(movx)
        amovy = abs(movy)
        if amovx >= amovy:
            ax = amovy / (amovx + amovy)
            spd_b = ax
            if spd_b < 0.05:
                spd_b = 0
            spd_a = (1.0 - spd_b)
            rotate = Plotter.ROTATE_UNIT * amovx * (1.0 + spd_b / spd_a)
            logging.info("A: movx=%s, movy=%s, ax=%s", movx, movy, ax)
        else:
            ax = amovx / (amovx + amovy)
            spd_a = ax
            if spd_a < 0.05:
                spd_a = 0
            spd_b = (1.0 - spd_a)
            rotate = Plotter.ROTATE_UNIT * amovy * (1.0 + spd_a / spd_b)
            logging.info("B: movx=%s, movy=%s, ax=%s", movx, movy, ax)

        assert 0 <= spd_a <= 1
        assert 0 <= spd_b <= 1

        spd_a *= (movx / amovx) if amovx else 0
        spd_b *= (movy / amovy) if amovy else 0
        return rotate, spd_a, spd_b

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
            self.both.start_power(spa, spb)
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
            self.both.start_power(spa, spb)
            logging.info("Motor speeds: %.3f / %.3f", spa, spb)
            time.sleep(dur)

    def rectangle(self, width, height, solid=False):
        self.line(width, 0)
        self.line(0, height)
        self.line(-width, 0)
        self.line(0, -height)

        if solid:
            max_step = 0.01
            rounds = int(math.ceil(height / max_step))
            step = height / rounds
            flip = 1
            for r in range(1, rounds):
                self.line(0, step)
                self.line(width * flip, 0)
                flip = -flip
