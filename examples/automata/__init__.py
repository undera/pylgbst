import logging
import time
from collections import Counter

from pylgbst.hub import MoveHub, COLOR_NONE, COLOR_BLACK, COLORS, COLOR_CYAN, COLOR_BLUE, COLOR_RED, COLOR_YELLOW, \
    COLOR_WHITE
from pylgbst.peripherals import EncodedMotor


class Automata(object):
    BASE_SPEED = 1.0

    def __init__(self):
        super(Automata, self).__init__()
        self.__hub = MoveHub()
        self.__hub.vision_sensor.subscribe(self.__on_sensor)
        self._sensor = []

    def __on_sensor(self, color, distance=-1):
        logging.debug("Sensor data: %s/%s", COLORS[color], distance)
        if distance <= 4:
            if color not in (COLOR_NONE, COLOR_BLACK):
                self._sensor.append((color, int(distance)))
                logging.debug("Sensor data: %s", COLORS[color])

    def feed_tape(self):
        self.__hub.motor_external.angled(60, 0.5)
        time.sleep(0.1)
        self.__hub.motor_external.angled(60, 0.5)
        time.sleep(0.1)

    def get_color(self):
        res = self._sensor
        self._sensor = []
        logging.debug("Sensor data: %s", res)
        cnts = Counter([x[0] for x in res])
        clr = cnts.most_common(1)[0][0] if cnts else COLOR_NONE
        if clr == COLOR_CYAN:
            clr = COLOR_BLUE
        self.__hub.led.set_color(clr)
        return clr

    def left(self):
        self.__hub.motor_AB.angled(290, self.BASE_SPEED, -self.BASE_SPEED, end_state=EncodedMotor.END_STATE_FLOAT)
        time.sleep(0.1)
        self.__hub.motor_AB.stop()

    def right(self):
        self.__hub.motor_AB.angled(270, -self.BASE_SPEED, self.BASE_SPEED, end_state=EncodedMotor.END_STATE_FLOAT)
        time.sleep(0.1)
        self.__hub.motor_AB.stop()

    def forward(self):
        self.__hub.motor_AB.angled(500, self.BASE_SPEED)

    def backward(self):
        self.__hub.motor_AB.angled(500, -self.BASE_SPEED)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot = Automata()

    color = None
    cmds = []
    while color != COLOR_NONE:
        bot.feed_tape()
        color = bot.get_color()

        logging.warning(COLORS[color])

        if color == COLOR_BLUE:
            bot.forward()
        elif color == COLOR_RED:
            bot.backward()
        elif color == COLOR_YELLOW:
            bot.left()
        elif color == COLOR_WHITE:
            bot.right()
