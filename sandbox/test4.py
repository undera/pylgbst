import time
import logging
from time import sleep

from pylgbst.hub import SmartHub, TestHub
from pylgbst.peripherals import Peripheral, EncodedMotor, TiltSensor, Current, Voltage, COLORS, COLOR_BLACK, COLOR_GREEN

logging.basicConfig(level=logging.DEBUG)


hub_1 = SmartHub(address='86996732-BF5A-433D-AACE-5611D4C6271D')   # test hub

sleep(7)

device_1 = TestHub(address='2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset

print(hub_1)
# print(device_1)


