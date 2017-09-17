# Python library to interact with LEGO Move Hub

Best way to start is to look into [`demo.py`](demo.py) file, and run it.

If you have Vernie assembled, you might look into and run scripts from [`vernie`](vernie/) directory.

## Features

- auto-detect and connect for Bluetooth device
- auto-detects devices connected to Hub
- angled and timed movement for motors
- LED color change
- motors: angled and timed movement, rotation sensor subscription
- push button status subscription
- tilt sensor subscription: 2 axis, 3 axis, bump detect modes
- color & distance sensor: several modes to measure distance, color and luminosity
- battery voltage subscription available
- permanent Bluetooth connection server for faster debugging

## Usage

Install library like this: 
```bash
pip install https://github.com/undera/pylgbst/archive/0.2.tar.gz
```

Then instantiate MoveHub object and start invoking its methods. Following is example to just print peripherals detected on Hub:  

```python
from pylgbst import MoveHub

hub = MoveHub()

for device in hub.devices:
    print(device)
```

TODO: more usage instructions

### General Information
hub's devices detect process & fields to access them
general subscription modes & granularity info

### Motors
### Motor Rotation Sensors
### Tilt Sensor
### Color & Distance Sensor
### LED
### Push Button
### Power Voltage & Battery


## Debug Server

```
sudo python -c "from pylgbst.comms import *; import logging; logging.basicConfig(level=logging.DEBUG); DebugServer(BLEConnection().connect()).start()"
```

## Roadmap

- handle device detach and device attach events on ports C/D
- experiment with motor commands, find what is hidden there
- Give nice documentation examples, don't forget to mention logging
- document all API methods
- make sure unit tests cover all important code
- generalize getting device info + give constants (low priority)

## Links

- https://github.com/JorgePe/BOOSTreveng - source of protocol knowledge
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with +-another approach to bluetooth libs

Some things around visual programming:
- https://github.com/RealTimeWeb/blockpy
- https://ru.wikipedia.org/wiki/App_Inventor
- https://en.wikipedia.org/wiki/Blockly

