
### Power Voltage & Battery

`MoveHub` class has field `voltage` to subscribe to battery voltage status. Callback accepts single parameter with current value. The range of values is float between `0` and `1.0`. Every time data is received, value is also written into `last_value` field of `Voltage` object. Values less than `0.2` are known as lowest values, when unit turns off.

```python
from pylgbst.hub import MoveHub
import time

def callback(value):
    print("Voltage: %s" % value)

hub = MoveHub()
hub.voltage.subscribe(callback)
time.sleep(1)
print ("Value: " % hub.voltage.last_value)
```
