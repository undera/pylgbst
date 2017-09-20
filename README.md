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
connection params
hub's devices detect process & fields to access them
general subscription modes & granularity info
good practice is to unsubscribe, especially when used with `DebugServer`
### Motors
### Motor Rotation Sensors
### Tilt Sensor
### Color & Distance Sensor
Tip: laser pointer pointing to sensor makes it trigger distance sensor

### LED

`MoveHub` class has field `led` to access color LED near push button. To change its color, use `set_color(color)` method. 

You can obtain colors are present as constants `COLOR_*` and also a map of available color-to-name as `COLORS`.

Additionally, you can subscribe to LED color change events, using callback function as shown in example below.


```python
from pylgbst import MoveHub, COLORS, COLOR_NONE, COLOR_RED
import time

def callback(clr):
    print("Color has changed: %s" % clr)

hub = MoveHub()
hub.led.subscribe(callback)

hub.led.set_color(COLOR_RED)
for color in COLORS:
    hub.led.set_color(color)
    time.sleep(0.5)
    
hub.led.set_color(COLOR_NONE)
hub.led.unsubscribe(callback)
```

Note: blinking orange color of LED means battery is low.

### Push Button

`MoveHub` class has field `button` to subscribe to button press and release events.

Note that `Button` class is not real `Peripheral`, as it has no port and not listed in `devices` field of Hub. Still, subscribing to button is done usual way: 

```python
from pylgbst import MoveHub

def callback(is_pressed):
    print("Btn pressed: %s" % is_pressed)

hub = MoveHub()
hub.button.subscribe(callback)
```

### Power Voltage & Battery

`MoveHub` class has field `battery` to subscribe to battery voltage status. Callback accepts single parameter with current value. The range of values is unknown, it's 2-byte integer. Every time data is received, value is also written into `last_value` field of Battery object.

```python
from pylgbst import MoveHub
import time

def callback(value):
    print("Voltage: %s" % value)

hub = MoveHub()
hub.battery.subscribe(callback)
time.sleep(1)
print ("Value: " % hub.battery.last_value)
```

TODO: investigate `mode` parameter for battery

## Debug Server
Running debug server opens permanent BLE connection to Hub and listening on TCP port for communications. This avoids the need to re-start Hub all the time. 

There is `DebugServerConnection` class that you can use with it, instead of `BLEConnection`. 

Starting debug server is done like this:
```bash
sudo python -c "from pylgbst.comms import *; \
    import logging; logging.basicConfig(level=logging.DEBUG); \
    DebugServer(BLEConnection().connect()).start()"
```

## TODO

- Give nice documentation examples, don't forget to mention logging
- document all API methods
- make sure unit tests cover all important code
- handle device detach and device attach events on ports C/D
- generalize getting device info + give constants (low priority)
- organize requesting and printing device info on startup - firmware version at least
- make debug server to re-establish BLE connection on loss

## Links

- https://github.com/JorgePe/BOOSTreveng - source of protocol knowledge
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with +-another approach to bluetooth libs

Some things around visual programming:
- https://github.com/RealTimeWeb/blockpy
- https://ru.wikipedia.org/wiki/App_Inventor
- https://en.wikipedia.org/wiki/Blockly

