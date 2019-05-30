### Power Voltage & Battery

`MoveHub` class has field `voltage` to subscribe to battery voltage status. Callback accepts single parameter with current value. The range of values is float between `0` and `1.0`. Every time data is received, value is also written into `last_value` field of `Voltage` object. Values less than `0.2` are known as lowest values, when unit turns off.

```python
from pylgbst.hub import MoveHub, Voltage

def callback(value):
    print("Voltage: %s" % value)

hub = MoveHub()
print ("Value L: " % hub.voltage.get_sensor_data(Voltage.VOLTAGE_L))
print ("Value S: " % hub.voltage.get_sensor_data(Voltage.VOLTAGE_S))
```
