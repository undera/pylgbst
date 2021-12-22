### Color & Distance Sensor

#### Mode subscriptions
Sensor has number of different modes to subscribe.

Colors that are detected are part of `COLORS` map (see [LED](#led) section). Only several colors are possible to detect: `BLACK`, `BLUE`, `CYAN`, `YELLOW`, `RED`, `WHITE`. Sensor does its best to detect best color, but only works when sample is very close to sensor.

Distance works in range of 0-10 inches, with ability to measure last inch in higher detail.

Simple example of subscribing to sensor:

```python
from pylgbst.hub import MoveHub, VisionSensor
import time

def callback(color, distance):
    print("Color: %s / Distance: %s" % (color, distance))

hub = MoveHub()

hub.vision_sensor.subscribe(callback, mode=VisionSensor.COLOR_DISTANCE_FLOAT)
time.sleep(60) # play with sensor while it waits   
hub.vision_sensor.unsubscribe(callback)
```

Subscription mode constants in class `VisionSensor` are:
- `COLOR_INDEX` - use `callback(color)`
- `DISTANCE_INCHES` - use `callback(color)` measures distance in integer inches count
- `COUNT_2INCH` - use `callback(count)` - it counts crossing distance ~2 inches in front of sensor
- `DISTANCE_REFLECTED` - use `callback(reflected)` where `reflected` is float value from 0 to 1
- `AMBIENT_LIGHT` - use `callback(luminosity)` where `luminosity` is float value from 0 to 1
- `COLOR_RGB` - use `callback(red, green, blue)` - each value corresponds to a color channel
- `COLOR_DISTANCE_FLOAT` - default mode, use `callback(color, distance)` where `distance` is float value in inches

Two specific constants are used with methods to act on the sensor:
- `set_color(color)` and `SET_COLOR` mode - allow to change the color of the sensor RGBLED. `COLOR_BLACK` and `COLOR_NONE` turns the LED off
- `set_ir_tx(ir_code)` and `SET_IR_TX` mode - allow to send IR code for PowerFunctions receiver


#### Access to sensor measures

The following attributes are available, they correspond to the modes described
above.

```python
from pylgbst.hub import MoveHub

hub = MoveHub()
print("Color:", hub.vision_sensor.color)
print("Distance:", hub.vision_sensor.distance)
print("Reflected light:", hub.vision_sensor.reflected_light)
print("Luminosity:", hub.vision_sensor.luminosity)
print("Detection count:", hub.vision_sensor.detection_count)
print("RGB channels:", hub.vision_sensor.rgb_color)
```
