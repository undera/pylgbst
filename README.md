# Python library to interact with Move Hub

_Move Hub is central controller block of [LEGO® Boost Robotics Set](https://www.lego.com/en-us/boost)._

In fact, Move Hub is just Bluetooth hardware, all manipulations are done with commands passed through Bluetooth Low Energy (BLE) wireless protocol. One of ways to issue these commands is to write Python program using this library.

Best way to start is to look into [`demo.py`](examples/demo.py) file, and run it (assuming you have installed library).

If you have Vernie assembled, you might run scripts from [`examples/vernie`](examples/vernie) directory.

Demonstrational videos:

[![Vernie Programmed](http://img.youtube.com/vi/oqsmgZlVE8I/0.jpg)](http://www.youtube.com/watch?v=oqsmgZlVE8I)
[![Laser Engraver](http://img.youtube.com/vi/ZbKmqVBBMhM/0.jpg)](https://youtu.be/ZbKmqVBBMhM)
[![Color Sorter](http://img.youtube.com/vi/829RKT8v8M0/0.jpg)](https://youtu.be/829RKT8v8M0)
[![Face Tracker](http://img.youtube.com/vi/WUOa3j-6XfI/0.jpg)](https://youtu.be/WUOa3j-6XfI)


## Features

- auto-detect and connect to Move Hub device
- auto-detects peripheral devices connected to Hub
- constant, angled and timed movement for motors, rotation sensor subscription
- color & distance sensor: several modes to measure distance, color and luminosity
- tilt sensor subscription: 2 axis, 3 axis, bump detect modes
- LED color change
- push button status subscription
- battery voltage subscription available
- permanent Bluetooth connection server for faster debugging

## Usage

_Please note that this library requires one of Bluetooth backend libraries to be installed, please read section [here](#bluetooth-backend-prerequisites) for details._

Install library like this: 
```bash
pip install https://github.com/undera/pylgbst/archive/1.0.tar.gz
```

Then instantiate MoveHub object and start invoking its methods. Following is example to just print peripherals detected on Hub:  

```python
from pylgbst.movehub import MoveHub

hub = MoveHub()

for device in hub.devices:
    print(device)
```

### Controlling Motors

MoveHub provides motors via following fields:
- `motor_A` - port A
- `motor_B` - port B
- `motor_AB` - motor group of A+B manipulated together
- `motor_external` - external motor attached to port C or D

Methods to activate motors are:
- `constant(speed_primary, speed_secondary)` - enables motor with specified speed forever 
- `timed(time, speed_primary, speed_secondary)` - enables motor with specified speed for `time` seconds, float values accepted
- `angled(angle, speed_primary, speed_secondary)` - makes motor to rotate to specified angle, `angle` value is integer degrees, can be negative and can be more than 360 for several rounds
- `stop()` - stops motor at once, it is equivalent for `constant(0)`

Parameter `speed_secondary` is used when it is motor group of `motor_AB` running together. By default, `speed_secondary` equals `speed_primary`. Speed values range is `-1.0` to `1.0`, float values. _Note: In group angled mode, total rotation angle is distributed across 2 motors according to motor speeds ratio._

All these methods are synchronous by default, means method does not return untill it gets confirmation from Hub that command has completed. You can pass `async=True` parameter to any of methods to switch into asynchronous, which means command will return immediately, without waiting for rotation to complete. Be careful with asynchronous calls, as they make Hub to stop reporting synchronizing statuses.

An example:
```python
from pylgbst.movehub import MoveHub
import time

hub = MoveHub()

hub.motor_A.timed(0.5, 0.8)
hub.motor_A.timed(0.5, -0.8)

hub.motor_B.angled(90, 0.8)
hub.motor_B.angled(-90, 0.8)

hub.motor_AB.timed(1.5, 0.8, -0.8)
hub.motor_AB.angled(90, 0.8, -0.8)

hub.motor_external.constant(0.2)
time.sleep(2)
hub.motor_external.stop()
```


### Motor Rotation Sensors

Any motor allows to subscribe to its rotation sensor. Two sensor modes are available: rotation angle (`EncodedMotor.SENSOR_ANGLE`) and rotation speed (`EncodedMotor.SENSOR_SPEED`). Example: 

```python
from pylgbst.movehub import MoveHub, EncodedMotor
import time

def callback(angle):
    print("Angle: %s" % angle)

hub = MoveHub()

hub.motor_A.subscribe(callback, mode=EncodedMotor.SENSOR_ANGLE)
time.sleep(60) # rotate motor A
hub.motor_A.unsubscribe(callback)
```

### Tilt Sensor

MoveHub's internal tilt sensor is available through `tilt_sensor` field. There are several modes to subscribe to sensor, providing 2-axis, 3-axis and bump detect data.

An example:

```python
from pylgbst.movehub import MoveHub, TiltSensor
import time

def callback(pitch, roll, yaw):
    print("Pitch: %s / Roll: %s / Yaw: %s" % (pitch, roll, yaw))

hub = MoveHub()

hub.tilt_sensor.subscribe(callback, mode=TiltSensor.MODE_3AXIS_FULL)
time.sleep(60) # turn MoveHub block in different ways
hub.tilt_sensor.unsubscribe(callback)
```

`TiltSensor` sensor mode constants:
- `MODE_2AXIS_SIMPLE` - use `callback(state)` for 2-axis simple state detect
- `MODE_2AXIS_FULL` - use `callback(roll, pitch)` for 2-axis roll&pitch degree values
- `MODE_3AXIS_SIMPLE` - use `callback(state)` for 3-axis simple state detect
- `MODE_3AXIS_FULL` - use `callback(roll, pitch)` for 2-axis roll&pitch degree values
- `MODE_BUMP_COUNT` - use `callback(count)` to detect bumps

There are tilt sensor constants for "simple" states, for 2-axis mode their names are also available through `TiltSensor.DUO_STATES`:
- `DUO_HORIZ` - "HORIZONTAL"
- `DUO_DOWN` - "DOWN"
- `DUO_LEFT` - "LEFT"
- `DUO_RIGHT` - "RIGHT"
- `DUO_UP` - "UP"
  
For 3-axis simple mode map name is `TiltSensor.TRI_STATES` with values:
- `TRI_BACK` - "BACK"
- `TRI_UP` - "UP"
- `TRI_DOWN` - "DOWN"
- `TRI_LEFT` - "LEFT"
- `TRI_RIGHT` - "RIGHT"
- `TRI_FRONT` - "FRONT"


### Color & Distance Sensor

Field named `color_distance_sensor` holds instance of `ColorDistanceSensor`, if one is attached to MoveHub. Sensor has number of different modes to subscribe. 

Colors that are detected are part of `COLORS` map (see [LED](#led) section). Only several colors are possible to detect: `BLACK`, `BLUE`, `CYAN`, `YELLOW`, `RED`, `WHITE`. Sensor does its best to detect best color, but only works when sample is very close to sensor.

Distance works in range of 0-10 inches, with ability to measure last inch in higher detail.

Simple example of subscribing to sensor:

```python
from pylgbst.movehub import MoveHub, ColorDistanceSensor
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
from pylgbst.movehub import MoveHub, COLORS, COLOR_NONE, COLOR_RED
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
from pylgbst.movehub import MoveHub

def callback(is_pressed):
    print("Btn pressed: %s" % is_pressed)

hub = MoveHub()
hub.button.subscribe(callback)
```

### Power Voltage & Battery

`MoveHub` class has field `voltage` to subscribe to battery voltage status. Callback accepts single parameter with current value. The range of values is float between `0` and `1.0`. Every time data is received, value is also written into `last_value` field of `Voltage` object. Values less than `0.2` are known as lowest values, when unit turns off.

```python
from pylgbst.movehub import MoveHub
import time

def callback(value):
    print("Voltage: %s" % value)

hub = MoveHub()
hub.voltage.subscribe(callback)
time.sleep(1)
print ("Value: " % hub.voltage.last_value)
```

## General Notes

### Bluetooth Backend Prerequisites

You have following options to install as Bluetooth backend:

- `pip install pygatt` - [pygatt](https://github.com/peplin/pygatt) lib, works on both Windows and Linux  
- `pip install gatt` - [gatt](https://github.com/getsenic/gatt-python) lib, supports Linux, does not work on Windows
- `pip install gattlib` - [gattlib](https://bitbucket.org/OscarAcena/pygattlib) - supports Linux, does not work on Windows, requires `sudo`
- `pip install bluepy` - [bluepy](https://github.com/IanHarvey/bluepy) lib, supports Linux, including Raspbian, which allows connection to the hub from the Raspberry PI

Running on Windows requires [Bluegiga BLED112 Bluetooth Smart Dongle](https://www.silabs.com/products/wireless/bluetooth/bluetooth-low-energy-modules/bled112-bluetooth-smart-dongle) hardware piece, because no other hardware currently works on Windows with Python+BLE.

_Please let author know if you have discovered any compatibility/preprequisite details, so we will update this section to help future users_

Depending on backend type, you might need Linux `sudo` to be used when running Python.

### Bluetooth Connection Options
There is optional parameter for `MoveHub` class constructor, accepting instance of `Connection` object. By default, it will try to use whatever `get_connection_auto()` returns. You have several options to manually control that:

- use `pylgbst.get_connection_auto()` to attempt backend auto-choice, autodetect uses 
- use `BlueGigaConnection()` - if you use BlueGiga Adapter (`pygatt` library prerequisite)
- use `GattConnection()` - if you use Gatt Backend on Linux (`gatt` library prerequisite)
- use `GattoolConnection()` - if you use GattTool Backend on Linux (`pygatt` library prerequisite)
- use `GattLibConnection()` - if you use GattLib Backend on Linux (`gattlib` library prerequisite)
- use `BluepyConnection()` - if you use Bluepy backend on Linux/Raspbian (`bluepy` library prerequisite)
- pass instance of `DebugServerConnection` if you are using [Debug Server](#debug-server) (more details below).

All the functions above have optional arguments to specify adapter name and MoveHub mac address. Please look function source code for details.

If you want to specify name for Bluetooth interface to use on local computer, you can passthat to class or function of getting a connection. Then pass connection object to `MoveHub` constructor. Like this:
```python
from pylgbst.movehub import MoveHub
from pylgbst.comms.cgatt import GattConnection

conn = GattConnection("hci1")
conn.connect()  # you can pass MoveHub mac address as parameter here, like 'AA:BB:CC:DD:EE:FF'

hub = MoveHub(conn)
```

### Use Disconnect in `finally`

It is recommended to make sure `disconnect()` method is called on connection object after you have finished your program. This ensures Bluetooth subsystem is cleared and avoids problems for subsequent re-connects of MoveHub. The best way to do that in Python is to use `try ... finally` clause:

```python
from pylgbst import get_connection_auto
from pylgbst.movehub import MoveHub

conn=get_connection_auto()  # ! don't put this into `try` block
try:
    hub = MoveHub(conn)
finally:
    conn.disconnect()
```

### Devices Detecting
As part of instantiating process, `MoveHub` waits up to 1 minute for all builtin devices to appear, such as motors on ports A and B, tilt sensor, button and battery. This not guarantees that external motor and/or color sensor will be present right after `MoveHub` instantiated. Usually, sleeping for couple of seconds gives it enough time to detect everything.

### Subscribing to Sensors
Each sensor usually has several different "subscription modes", differing with callback parameters and value semantics. 

There is optional `granularity` parameter for each subscription call, by default it is `1`. This parameter tells Hub when to issue sensor data notification. Value of notification has to change greater or equals to `granularity` to issue notification. This means that specifying `0` will cause it to constantly send notifications, and specifying `5` will cause less frequent notifications, only when values change for more than `5` (inclusive).

It is possible to subscribe with multiple times for the same sensor. Only one, very last subscribe mode is in effect, with many subscriber callbacks allowed to receive notifications. 

Good practice for any program is to unsubscribe from all sensor subscriptions before ending, especially when used with `DebugServer`.

## Debug Server
Running debug server opens permanent BLE connection to Hub and listening on TCP port for communications. This avoids the need to re-start Hub all the time. 

There is `DebugServerConnection` class that you can use with it, instead of `BLEConnection`. 

Starting debug server is done like this (you may need to run it with `sudo`, depending on your BLE backend):
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); \
                import pylgbst; pylgbst.start_debug_server()"
```

Then push green button on MoveHub, so permanent BLE connection will be established.

## Roadmap & TODO

- document all API methods
- make sure unit tests cover all important code
- make debug server to re-establish BLE connection on loss

## Links

- https://github.com/LEGO/lego-ble-wireless-protocol-docs - true docs for LEGO BLE protocol
- https://github.com/JorgePe/BOOSTreveng - initial source of protocol knowledge
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with another approach to bluetooth libs

Some things around visual programming:
- https://github.com/RealTimeWeb/blockpy
- https://ru.wikipedia.org/wiki/App_Inventor
- https://en.wikipedia.org/wiki/Blockly

