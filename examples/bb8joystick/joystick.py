from pylgbst.hub import MoveHub
from pylgbst.peripherals import VisionSensor, EncodedMotor


class Joystick(object):
    def __init__(self):
        super(Joystick, self).__init__()
        self._hub = MoveHub()
        self._sensor = []

    def disconnect(self):
        self._hub.disconnect()

    def on_color_sensor(self, callback):
        self._hub.vision_sensor.subscribe(callback, VisionSensor.COLOR_RGB, granularity=5)

    def on_external_motor(self, callback):
        self._hub.motor_external.subscribe(callback, EncodedMotor.SENSOR_ANGLE, granularity=5)
