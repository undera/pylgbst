import logging
import time

from pylgbst.hub import MoveHub
from pylgbst.peripherals import EncodedMotor


class Joystick(object):
    def __init__(self):
        super(Joystick, self).__init__()
        self._hub = MoveHub()

        self.button_pressed = False

        self._hub.motor_external.subscribe(print, EncodedMotor.SENSOR_ANGLE, granularity=1)
        self._hub.motor_A.subscribe(print, EncodedMotor.SENSOR_ANGLE, granularity=1)
        self._hub.motor_B.subscribe(print, EncodedMotor.SENSOR_ANGLE, granularity=1)
        self._hub.button.subscribe(self._on_btn)

    def disconnect(self):
        self._hub.disconnect()

    def _on_btn(self, state):
        self.button_pressed = state

    def on_button(self, callback):
        """
        Notifies about button state change. ``callback(state)`` gets single bool parameter
        """

        def wrapper(state):
            if state in (0, 1):
                logging.debug("Pressed button: %s", state)
                callback(bool(state))

        self._hub.button.subscribe(wrapper)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    stick = Joystick()
    stick.on_button(lambda x: print("Button: %s" % x))
    time.sleep(100)
