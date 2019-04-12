import logging
import time
from collections import Counter

from pylgbst.hub import MoveHub, COLOR_NONE, COLOR_BLACK, COLORS, COLOR_CYAN, COLOR_BLUE, COLOR_RED
from pylgbst.peripherals import EncodedMotor


class Automata(object):
    BASE_SPEED = 0.5

    def __init__(self):
        super(Automata, self).__init__()
        self.__hub = MoveHub()
        self.__hub.motor_A.set_dec_profile(0.05, 0x00)
        self.__hub.motor_B.set_dec_profile(0.05, 0x00)
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
        logging.info("Sensor data: %s", res)
        cnts = Counter([x[0] for x in res])
        clr = cnts.most_common(1)[0][0] if cnts else COLOR_NONE
        if clr == COLOR_CYAN:
            clr = COLOR_BLUE
        return clr

    def left(self):
        self.__hub.motor_A.angled(-270, self.BASE_SPEED, end_state=EncodedMotor.END_STATE_HOLD)
        time.sleep(0.1)
        self.__hub.motor_A.stop()

    def right(self):
        self.__hub.motor_B.angled(-320, self.BASE_SPEED, end_state=EncodedMotor.END_STATE_HOLD)
        time.sleep(0.1)
        self.__hub.motor_B.stop()

    def forward(self):
        self.__hub.motor_AB.angled(-450, self.BASE_SPEED)

    def backward(self):
        self.__hub.motor_AB.angled(450, self.BASE_SPEED)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    bot = Automata()

    bot.forward()
    bot.backward()

    exit(0)

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
