import logging
import time

from pylgbst.hub import MoveHub


def _clamp(minvalue, value, maxvalue):
    return max(minvalue, min(value, maxvalue))


class Joystick(object):
    def __init__(self):
        super(Joystick, self).__init__()
        self._hub = MoveHub()

        self._reset_sensors()

        self.button_pressed = False
        self._hub.button.subscribe(self._on_btn)

        self.angle_A = 0
        self.on_motor_a(self._on_a)

        self.angle_B = 0
        self.on_button(self._on_b)

        self.angle_C = 0
        self.on_motor_a(self._on_c)

        logging.info("Done initializing")

    def disconnect(self):
        self._hub.disconnect()

    def _reset_sensors(self):
        logging.info("Resetting motor encoders")
        self._hub.motor_A.preset_encoder()
        self._hub.motor_B.preset_encoder()
        self._hub.motor_external.preset_encoder()

    def on_button(self, callback):
        """
        Notifies about button state change. ``callback(state)`` gets single bool parameter
        """

        def wrapper(state):
            if state in (0, 1):
                callback(bool(state))

        self._hub.button.subscribe(wrapper)

    def on_motor_a(self, callback):
        """
        Notifies about A motor rotation. ``callback(state)`` gets single int parameter from 0 to 359
        """

        def wrapper(angle):
            logging.debug("Raw angle: %s", angle)
            range = 25
            angle = _clamp(-range, angle, range)
            callback(angle)

        self._hub.motor_A.subscribe(wrapper)

    def on_motor_b(self, callback):
        """
        Notifies about B motor rotation. ``callback(state)`` gets single int parameter from 0 to 359
        """

        def wrapper(angle):
            logging.debug("Raw angle: %s", angle)
            val = angle % 360
            callback(val if val >= 0 else 360 - val)

        self._hub.motor_B.subscribe(wrapper)

    def on_motor_c(self, callback):
        """
        Notifies about C motor rotation. ``callback(state)`` gets single int parameter from 0 to 359
        """

        def wrapper(angle):
            logging.debug("Raw angle: %s", angle)
            range = 25
            angle = _clamp(-range, angle, range)
            callback(angle)

        self._hub.motor_external.subscribe(wrapper)

    def _on_btn(self, state):
        self.button_pressed = bool(state)

    def _on_a(self, angle):
        logging.debug("A rotated: %s", angle)
        self.angle_A = angle

    def _on_b(self, angle):
        logging.debug("B rotated: %s", angle)
        self.angle_B = angle

    def _on_c(self, angle):
        logging.debug("C rotated: %s", angle)
        self.angle_C = angle


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    stick = Joystick()
    stick.on_button(lambda x: print("Button: %s" % x))
    stick.on_motor_a(lambda x: print("Motor A: %s" % x))
    stick.on_motor_b(lambda x: print("Motor B: %s" % x))
    stick.on_motor_c(lambda x: print("Motor C: %s" % x))
    time.sleep(100)
