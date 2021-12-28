### LED

`MoveHub` class has field `led` to access color LED near push button. To change its color, use `set_color(color)` method. 

You can obtain colors are present as constants `COLOR_*` and also a map of available color-to-name as `COLORS`. There are 12 color values, including `COLOR_BLACK` and `COLOR_NONE` which turn LED off.
Available constants: `COLOR_BLACK, COLOR_PINK, COLOR_PURPLE, COLOR_BLUE, COLOR_LIGHTBLUE,
COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_ORANGE, COLOR_RED, COLOR_WHITE, COLOR_NONE`.


LED color can be simply modified:
```python
from pylgbst.hub import MoveHub, COLOR_RED

hub = MoveHub()
print("Set LED color to red:")
hub.led.color = COLOR_RED
# or
hub.led.set_color(COLOR_RED)

print("Set LED color to red, via the RGB value:")
hub.led.color = (255, 0, 0)
```

Tip: blinking orange color of LED means battery is low.

Note that the VisionSensor can also be used to set its LED color into indexed
 colors.

---

Warning: The following doc is experimental; getting data from the LED peripheral
doesn't currently produce meaningful results (0 values both with MODE_INDEX or
 MODE_RGB). Indeed, the callback is no longer issued when the color changes.

You can access to the current color as shown in the example:

```python
from pylgbst.hub import MoveHub
from pylgbst.peripherals import LEDRGB
hub = MoveHub()
print("Current color - mode INDEX", hub.led.get_sensor_data(LEDRGB.MODE_INDEX))
print("Current color - mode RGB", hub.led.get_sensor_data(LEDRGB.MODE_RGB))
```

Additionally, you can subscribe to LED color change events, using callback function
as shown in example below.

```python
from pylgbst.hub import MoveHub, COLORS, COLOR_NONE, COLOR_RED
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
