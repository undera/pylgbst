import time
import logging
from time import sleep
from pynput import keyboard

from pylgbst.hub import SmartHub
from pylgbst.peripherals import Voltage

logging.basicConfig(level=logging.DEBUG)

class TrainController:
    '''
    Basic train controller.

    For now, it accepts keyboard commands that replace the remote handset buttons functionality.
    It also reports voltage and current at stdout.
    '''

    def get_keypresses(self, callback):
        keyboard_listener = keyboard.Listener(on_press=callback)
        keyboard_listener.start()

        # self.hub = SmartHub(address='F88800F6-F39B-4FD2-AFAA-DD93DA2945A6')   # train hub
        # self.motor = self.hub.port_A

    # def run(self):
    #     try:
    #         self.motor.power()bvg
    #         sleep(3)
    #         self.motor.stop()
    #         sleep(1)
    #         self.motor.power(param=0.2)
    #         sleep(3)
    #         self.motor.stop()
    #         sleep(1)
    #         self.motor.power(param=-0.2)
    #         sleep(3)
    #         self.motor.stop()
    #         sleep(3)
    #     finally:
    #         self.hub.disconnect()



# Start Controller
t = TrainController()

# start listening to keyboard presses. Keyboard keys act as replacements for the
# Lego remote handset keys (until support for it is implemented in pylgbst).
def keyboard_press_callback(key):
    # Here we will update a instance variable that contains the train
    # motor duty cycle fraction (aka "power"). It may also update the
    # headlight power level from port B, if there is one installed.
    # Other threads in the code may want to update the motor power too,
    # so we need perhaps to use a semaphore or lock mechanism.
    print('{} was pressed'.format(key))

t.get_keypresses(keyboard_press_callback)

# Dummy main execution thread.
for n in range(30):
    print("@@@@ controller.py 53: " )
    sleep(1)

