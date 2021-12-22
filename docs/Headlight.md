### Headlight

You can set the brightness of the LEDs of this set using the `LEDLight` class and its
`set_brightness` method. Accepted values are between 0 and 100%.

Example to make the LEDs blink:

```python
import time
from pylgbst.hub import MoveHub

hub = MoveHub()
# Blink forever
while True:
    # Headlight is on port D; set its brightness to 100%
    hub.port_D.set_brightness(100)
    time.sleep(1)
    # Shutdown the ligth
    hub.port_D.set_brightness(0)
```
