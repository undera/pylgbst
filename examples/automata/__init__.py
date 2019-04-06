import logging
import time
from collections import Counter

from pylgbst.hub import MoveHub, COLOR_NONE, COLOR_BLACK, COLORS, COLOR_CYAN, COLOR_BLUE, COLOR_RED


class Automata(object):

    def __init__(self):
        super(Automata, self).__init__()
        self.__hub = MoveHub()
        self.__hub.color_distance_sensor.subscribe(self.__on_sensor)
        self._sensor = []

    def __on_sensor(self, color, distance=-1):
        logging.info("Sensor data: %s/%s", COLORS[color], distance)
        if distance < 4:
            if color not in (COLOR_NONE, COLOR_BLACK):
                self._sensor.append((color, int(distance)))
                logging.info("Sensor data: %s", COLORS[color])

    def feed_tape(self):
        self.__hub.motor_external.angled(60, 0.5)
        time.sleep(0.1)
        self.__hub.motor_external.angled(60, 0.5)
        time.sleep(0.1)

    def get_color(self):
        res = self._sensor
        self._sensor = []
        logging.info("Sensor data: %s", res)
        cnts = Counter([x[0] for x in res])
        clr = cnts.most_common(1)[0][0] if cnts else COLOR_NONE
        if clr == COLOR_CYAN:
            clr = COLOR_BLUE
        return clr

    def left(self):
        self.__hub.motor_AB.angled(270, 0.25, -0.25)
        time.sleep(0.5)

    def right(self):
        self.__hub.motor_AB.angled(-270, 0.25, -0.25)
        time.sleep(0.5)

    def forward(self):
        self.__hub.motor_AB.angled(830, 0.25)
        time.sleep(0.5)

    def backward(self):
        self.__hub.motor_AB.angled(830, -0.25)
        time.sleep(0.5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot = Automata()
    color = COLOR_NONE
    cmds = []
    while color != COLOR_RED:
        bot.feed_tape()
        color = bot.get_color()
        logging.warning(COLORS[color])
        cmds.append(COLORS[color])

    exp = ['BLUE', 'BLUE', 'BLUE', 'WHITE', 'BLUE', 'BLUE', 'WHITE', 'BLUE', 'WHITE', 'YELLOW', 'BLUE', 'BLUE', 'BLUE',
           'BLUE', 'YELLOW', 'WHITE', 'RED']
    logging.info("Exp: %s", exp)
    logging.info("Act: %s", cmds)
    assert exp == cmds
