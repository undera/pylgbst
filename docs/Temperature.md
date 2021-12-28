### Temperature

The temperature of the battery (in Celsius) can be easily retrieved from the hub.

```python
from pylgbst.hub import MoveHub
from pylgbst.peripherals import Temperature

hub = MoveHub()

for port, device in hub.peripherals.items():
    if isinstance(device, Temperature):
        print("Battery temperature:", device.temperature)

```
