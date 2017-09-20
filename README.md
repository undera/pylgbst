from pylgbst.peripherals import ColorDistanceSensor# Python library to interact with LEGO Move Hub

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

Field named `color_distance_sensor` holds instance of `ColorDistanceSensor`, if one is attached to MoveHub. Sensor has number of different modes to subscribe. Only one, very last subscribe mode is in effect, with many subscriber callbacks allowed. 

Colors that are detected are part of `COLORS` map (see [LED](#LED) section). Only several colors are possible to detect: `BLACK`, `BLUE`, `CYAN`, `YELLOW`, `RED`, `WHITE`. Sensor does its best to detect best color, but only works when sample is very close to sensor.

Distance works in range of 0-10 inches, with ability to measure last inch in higher detail.

Simple example of subscribing to sensor:

```python
from pylgbst import MoveHub, ColorDistanceSensor
import time

def callback(clr, distance):
    print("Color: %s / Distance: %s" % (clr, distance))

hub = MoveHub()

hub.color_distance_sensor.subscribe(callback, mode=ColorDistanceSensor.COLOR_DISTANCE_FLOAT)
time.sleep(60) # play with sensor while it waits   
hub.color_distance_sensor.unsubscribe(callback)
```

Subscription mode constants in class `ColorDistanceSensor` are:
- `COLOR_DISTANCE_FLOAT` - default mode, use `callback(color, distance)` where `distance` is float value in inches
- `COLOR_ONLY` - use `callback(color)`
- `DISTANCE_INCHES` - use `callback(color)` measures distance in integer inches count
- `COUNT_2INCH` - use `callback(count)` - it counts crossing distance ~2 inches in front of sensor
- `DISTANCE_HOW_CLOSE` - use `callback(value)` - value of 0 to 255 for 30 inches, larger with closer distance
- `DISTANCE_SUBINCH_HOW_CLOSE` - use `callback(value)` - value of 0 to 255 for 1 inch, larger with closer distance
- `LUMINOSITY` - use `callback(luminosity)` where `luminosity` is float value from 0 to 1
- `OFF1` and `OFF2` - seems to turn sensor LED and notifications off
- `STREAM_3_VALUES` - use `callback(val1, val2, val3)`, sends some values correlating to distance, not well understood at the moment

Tip: laser pointer pointing to sensor makes it to trigger distance sensor

### LED

`MoveHub` class has field `led` to access color LED near push button. To change its color, use `set_color(color)` method. 

You can obtain colors are present as constants `COLOR_*` and also a map of available color-to-name as `COLORS`. There are 12 color values, including `COLOR_BLACK` and `COLOR_NONE` which turn LED off.

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

Tip: blinking orange color of LED means battery is low.

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

## Debug Server
Running debug server opens permanent BLE connection to Hub and listening on TCP port for communications. This avoids the need to re-start Hub all the time. 

There is `DebugServerConnection` class that you can use with it, instead of `BLEConnection`. 

Starting debug server is done like this:
```bash
sudo python -c "from pylgbst.comms import *; \
    import logging; logging.basicConfig(level=logging.DEBUG); \
    DebugServer(BLEConnection().connect()).start()"
```

Then push green button on MoveHub, so permanent BLE connection will be established.

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
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with another approach to bluetooth libs

Some things around visual programming:
- https://github.com/RealTimeWeb/blockpy
- https://ru.wikipedia.org/wiki/App_Inventor
- https://en.wikipedia.org/wiki/Blockly

