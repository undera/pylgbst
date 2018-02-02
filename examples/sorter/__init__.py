import logging
import traceback

from pylgbst import MoveHub, COLORS, COLOR_RED, COLOR_YELLOW, COLOR_CYAN, COLOR_BLUE, COLOR_BLACK
from pylgbst.comms import DebugServerConnection, BLEConnection


class ColorSorter(MoveHub):
    positions = [COLOR_YELLOW, COLOR_BLUE, COLOR_CYAN, COLOR_RED]

    def __init__(self, connection=None):
        super(ColorSorter, self).__init__(connection)
        self.position = len(self.positions)
        self.color = 0
        self.distance = 10
        self._last_wheel_dir = 1
        self.color_distance_sensor.subscribe(self.on_color)

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

        if wheel_dir != self._last_wheel_dir:
            self.motor_B.angled(270 * wheel_dir)

        self.motor_B.angled(offset * 360 * 15)

        self.position = newpos
        self._last_wheel_dir = wheel_dir


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

    queue = [None for _ in range(0, 1)]

    sorter = ColorSorter(conn)
    empty = 0
    try:
        while True:
            empty += 1
            item = (sorter.color, sorter.distance)  # read once
            # logging.info("%s %.2f", COLORS[item[0]], item[1])
            if item[1] <= 5.0:
                logging.info("Detected: %s", COLORS[item[0]])
                queue.append(item)
                empty = 0
            else:
                queue.append(None)

            logging.debug("%s", [COLORS[x[0]] if x else None for x in queue])

            last = queue.pop(0)
            if last:
                sorter.move_to_bucket(last[0])
                empty = 0

            if empty > 20:
                sorter.move_to_bucket(COLOR_BLACK)

            sorter.feed()
    finally:
        if not sorter.motor_B.in_progress():
            sorter.move_to_bucket(COLOR_BLACK)
        sorter.motor_AB.stop(async=True)
