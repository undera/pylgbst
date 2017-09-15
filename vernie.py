from pylgbst import *

right = RIGHT = 1
left = LEFT = -1
straight = STRAIGHT = 0


class Vernie(MoveHub):
    def __init__(self, conn=None):
        super(Vernie, self).__init__(conn)

        while True:
            required_devices = (self.color_distance_sensor, self.motor_external)
            if None not in required_devices:
                break
            log.debug("Waiting for required devices to appear: %s", required_devices)
            time.sleep(1)

        self._head_position = 0
        self.motor_external.subscribe(self._external_motor_data)

        self._color_detected = COLOR_NONE
        self._sensor_distance = 10
        self.color_distance_sensor.subscribe(self._color_distance_data)

    def _external_motor_data(self, data):
        log.debug("External motor position: %s", data)
        self._head_position = data

    def _color_distance_data(self, color, distance):
        log.debug("Color & Distance data: %s %s", COLORS[color], distance)
        self._sensor_distance = distance
        self._color_detected = color
        self.led.set_color(self._color_detected if self._color_detected != COLOR_NONE else COLOR_BLACK)

    def head_to(self, direction=RIGHT, speed=0.25, angle=25):
        if direction == STRAIGHT:
            angle = -self._head_position
            direction = 1

        self.motor_external.angled(direction * angle, speed)

    def program(self):
        time.sleep(1)
        while True:
            self.head_to(LEFT)
            time.sleep(1)

            self.head_to(STRAIGHT)
            time.sleep(1)

            self.head_to(RIGHT)
            time.sleep(1)

            self.head_to(STRAIGHT)
            time.sleep(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    try:
        connection = DebugServerConnection()
    except BaseException:
        logging.warning("Failed to use debug server: %s", traceback.format_exc())
        connection = BLEConnection().connect()

    vernie = Vernie(connection)
    vernie.program()
