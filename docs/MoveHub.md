# Move Hub

![](http://bricker.info/images/parts/26910c01.png)

`MoveHub` is extension of generic [Powered Up Hub](GenericHub.md) class. `MoveHub` class delivers specifics of MoveHub brick, such as internal motor port names. Apart from specifics listed below, all operations on Hub are done [as usual](GenericHub.md).

## Devices Detecting
As part of instantiating process, `MoveHub` waits up to 1 minute for builtin devices to appear, such as motors on ports A and B, [tilt sensor](TiltSensor.md), [LED](LED.md) and [battery](VoltageCurrent.md). This not guarantees that external motor and/or color sensor will be present right after `MoveHub` instantiated. Usually, `time.sleep(1.0)` for couple of seconds gives it enough time to detect everything.

MoveHub provides motors via following fields:
- `motor_A` - port A motor
- `motor_B` - port B motor
- `motor_AB` - combined motors A+B manipulated together
- `motor_external` - external motor attached to port C or D

MoveHub's internal [tilt sensor](TiltSensor.md) is available through `tilt_sensor` field. 

Field named `vision_sensor` holds instance of [`VisionSensor`](VisionSensor.md), if one is attached to MoveHub.

Fields named `current` and `voltage` present [corresponding sensors](VoltageCurrent.md) from Hub.

## Push Button

`MoveHub` class has field `button` to subscribe to button press and release events.

Note that `Button` class is not real `Peripheral`, as it has no port and not listed in `peripherals` field of Hub. For convenience, subscribing to button is still done usual way: 

```python
from pylgbst.hub import MoveHub

def callback(is_pressed):
    print("Btn pressed: %s" % is_pressed)

hub = MoveHub()
hub.button.subscribe(callback)
```

The state for button has 3 possible values: 
- `0` - not released
- `1` - pressed
- `2` - pressed

It is for now unknown why Hub always issues notification with `1` and immediately with `2`, after button is pressed.