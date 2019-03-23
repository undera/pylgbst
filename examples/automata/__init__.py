import time
from collections import Counter

from pylgbst.constants import COLOR_NONE, COLOR_BLACK, COLOR_CYAN, COLOR_BLUE
from pylgbst.movehub import MoveHub
from pylgbst.peripherals import ColorDistanceSensor


class Automata(object):

    def __init__(self):
        super(Automata, self).__init__()
        self.__hub = MoveHub()
        self.__hub.color_distance_sensor.subscribe(self.__on_sensor, mode=ColorDistanceSensor.COLOR_ONLY)
        self._sensor = []

    def __on_sensor(self, color, distance=-1):
        if distance < 4 and color not in (COLOR_NONE, COLOR_BLACK):
            # print (COLORS[color], distance)
            self._sensor.append((color, int(distance)))

    def feed_tape(self):
        self.__hub.motor_external.angled(120, 0.1)
        time.sleep(0.2)

    def get_color(self):
        res = self._sensor
        self._sensor = []
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
