### Battery voltage

`MoveHub` class has field `voltage` to subscribe to battery voltage status.
Callback accepts single parameter with the actual value.
The values are floats in Volts.

```python
from pylgbst.hub import MoveHub, Voltage

def callback(value):
    print("Voltage: %s" % value)

hub = MoveHub()
print ("Battery voltage: %s" % hub.voltage.voltage)

# or
print ("Value L: %s" % hub.voltage.get_sensor_data(Voltage.VOLTAGE_L))
print ("Value S: %s" % hub.voltage.get_sensor_data(Voltage.VOLTAGE_S))
```


### Battery Current

`MoveHub` class has field `current` to subscribe to battery current status.
Callback accepts single parameter with the actual value.
The values are floats in mA.

```python
from pylgbst.hub import MoveHub

hub = MoveHub()
print ("Battery current: %s" % hub.current.current)
```
