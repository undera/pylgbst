import logging

from pylgbst.hub import MoveHub
from pylgbst.peripherals import COLOR_YELLOW, COLOR_BLUE, COLOR_CYAN, COLOR_RED, COLOR_BLACK, COLORS


class ColorSorter(MoveHub):
    positions = [COLOR_YELLOW, COLOR_BLUE, COLOR_CYAN, COLOR_RED]

    def __init__(self, connection=None):
        super(ColorSorter, self).__init__(connection)
        self.position = len(self.positions)
        self.color = 0
        self.distance = 10
        self._last_wheel_dir = 1
        self.vision_sensor.subscribe(self.on_color)
        self.queue = [None for _ in range(0, 1)]

    def on_color(self, colr, dist):
        if colr not in (COLOR_BLACK,) or dist < 2.5:
            logging.debug("%s %s", COLORS[colr], dist)
        self.color = colr
        self.distance = dist

    def feed(self):
        self.motor_A.angled(1080)  # 1080 was true

    def move_to_bucket(self, color):
        logging.info("Bucket: %s", COLORS[color])
        if color in self.positions:
            newpos = self.positions.index(color)
        else:
            newpos = len(self.positions)

        if newpos == self.position:
            return

        offset = newpos - self.position
        wheel_dir = offset / abs(offset)

        # if wheel_dir != self._last_wheel_dir:
        #    self.motor_B.angled(30 * wheel_dir)

        self.motor_B.angled(offset * 600, 0.8)

        self.position = newpos
        self._last_wheel_dir = wheel_dir

    def clear(self):
        self.vision_sensor.unsubscribe(self.on_color)
        self.move_to_bucket(COLOR_BLACK)
        self.motor_AB.stop()

    def tick(self):
        res = False
        item = (self.color, self.distance)  # read once

        if item[1] <= 5.0:
            logging.info("Detected: %s", COLORS[item[0]])
            self.queue.append(item)
            res = True
        else:
            self.queue.append(None)

        logging.debug("%s", [COLORS[x[0]] if x else None for x in self.queue])

        last = self.queue.pop(0)
        if last:
            self.move_to_bucket(last[0])
            res = True

        self.feed()
        return res


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    sorter = ColorSorter()
    empty = 0
    try:
        while True:
            empty += 1
            if sorter.tick():
                empty = 0
            elif empty > 20:
                break

    finally:
        sorter.clear()
