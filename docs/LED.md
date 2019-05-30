### LED

`MoveHub` class has field `led` to access color LED near push button. To change its color, use `set_color(color)` method. 

You can obtain colors are present as constants `COLOR_*` and also a map of available color-to-name as `COLORS`. There are 12 color values, including `COLOR_BLACK` and `COLOR_NONE` which turn LED off.

Additionally, you can subscribe to LED color change events, using callback function as shown in example below.

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

Tip: blinking orange color of LED means battery is low.


Note that Vision Sensor can also be used to set its LED color into indexed colors.