from pylgbst import *

forward = FORWARD = right = RIGHT = 1
backward = BACKWARD = left = LEFT = -1
straight = STRAIGHT = 0


class Vernie(MoveHub):
    def __init__(self):
        try:
            conn = DebugServerConnection()
        except BaseException:
            logging.debug("Failed to use debug server: %s", traceback.format_exc())
        conn = BLEConnection().connect()

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

        time.sleep(1)
        self._reset_head()
        time.sleep(1)
        log.info("Vernie is ready.")

    def _external_motor_data(self, data):
        log.debug("External motor position: %s", data)
        self._head_position = data

    def _color_distance_data(self, color, distance):
        log.debug("Color & Distance data: %s %s", COLORS[color], distance)
        self._sensor_distance = distance
        self._color_detected = color
        if self._color_detected != COLOR_NONE:
            self.led.set_color(self._color_detected)

    def _reset_head(self):
        self.motor_external.timed(1, -0.2)
        self.head_to(RIGHT, speed=45)

    def head_to(self, direction=RIGHT, angle=25, speed=0.1):
        if direction == STRAIGHT:
            angle = -self._head_position
            direction = 1

        self.motor_external.angled(direction * angle, speed)

    def turn(self, direction, degrees=90, speed=0.3):
        self.head_to(STRAIGHT, speed=1)
        self.head_to(direction, 35, 1)
        self.motor_AB.angled(225 * degrees / 90, speed * direction, -speed * direction)
        self.head_to(STRAIGHT, speed=1)

    def move(self, direction, distance=1, speed=0.3):
        self.head_to(STRAIGHT, speed=0.5)
        self.motor_AB.angled(distance * 450, speed * direction, speed * direction)

    def program(self):
        # while True:
        self.move(FORWARD)
        self.move(FORWARD)
        self.turn(RIGHT)
        self.move(FORWARD)
        self.turn(LEFT)
        self.move(FORWARD)
        self.turn(RIGHT)
        self.move(BACKWARD)
        self.move(BACKWARD)
        self.turn(LEFT)
        self.move(FORWARD)
        self.move(FORWARD)
        self.turn(RIGHT)
        self.move(FORWARD)
        self.turn(RIGHT)
        self.move(FORWARD, 3)
        self.turn(LEFT)
        self.turn(LEFT)
        self.move(BACKWARD, 2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    comms.log.setLevel(logging.INFO)

    vernie = Vernie()
    vernie.program()
