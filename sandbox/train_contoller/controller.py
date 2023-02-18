import time
import logging
from time import sleep

from pylgbst.hub import SmartHub
from pylgbst.peripherals import Voltage

logging.basicConfig(level=logging.DEBUG)

class TrainController:
    '''
    Basic train controller.

    For now, it accepts keyboard commands that replace the remote handset buttons functionality.
    It also reports voltage and current.
    '''

    def __int__(self):
         self.hub = SmartHub(address='F88800F6-F39B-4FD2-AFAA-DD93DA2945A6')   # train hub
         self.motor = self.hub.port_A

    def run(self):
        try:
            self.motor.power()
            sleep(3)
            self.motor.stop()
            sleep(1)
            self.motor.power(param=0.2)
            sleep(3)
            self.motor.stop()
            sleep(1)
            self.motor.power(param=-0.2)
            sleep(3)
            self.motor.stop()
            sleep(3)
        finally:
            self.hub.disconnect()
