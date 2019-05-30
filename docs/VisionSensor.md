### Color & Distance Sensor
![](https://img.bricklink.com/ItemImage/PL/6182145.png)

 Sensor has number of different modes to subscribe. 

Colors that are detected are part of `COLORS` map (see [LED](#led) section). Only several colors are possible to detect: `BLACK`, `BLUE`, `CYAN`, `YELLOW`, `RED`, `WHITE`. Sensor does its best to detect best color, but only works when sample is very close to sensor.

Distance works in range of 0-10 inches, with ability to measure last inch in higher detail.

Simple example of subscribing to sensor:

```python
from pylgbst.hub import MoveHub, VisionSensor
import time

def callback(clr, distance):
    print("Color: %s / Distance: %s" % (clr, distance))

hub = MoveHub()

hub.vision_sensor.subscribe(callback, mode=VisionSensor.COLOR_DISTANCE_FLOAT)
time.sleep(60) # play with sensor while it waits   
hub.vision_sensor.unsubscribe(callback)
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

