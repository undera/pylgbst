import json
import logging
import time

from pylgbst.hub import SmartHub, Remote
from pylgbst.peripherals import Peripheral, EncodedMotor, TiltSensor, Current, Voltage, COLORS, COLOR_BLACK, COLOR_GREEN

logging.basicConfig(level=logging.DEBUG)

hub = Remote(address='2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset

descr = {}
# for dev in hub.peripherals.values():
#     descr[str(dev)] = dev.describe_possible_modes()
#
# print(descr)




# with open("descr.json", "w") as fhd:
#     json.dump(descr, fhd, indent=True)
