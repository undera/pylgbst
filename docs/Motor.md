# Motors

![](https://img.bricklink.com/ItemImage/PL/6181852.png)

## Controlling Motors

Methods to activate motors are:
- `start_speed(speed_primary, speed_secondary)` - enables motor with specified speed forever 
- `timed(time, speed_primary, speed_secondary, wait_complete)` - enables motor with specified speed for `time` seconds, float values accepted
- `angled(angle, speed_primary, speed_secondary, wait_complete)` - makes motor to rotate to specified angle, `angle` value is integer degrees, can be negative and can be more than 360 for several rounds
- `stop()` - stops motor
- `wait_complete()` - waits until the latest operation sent to the motor is complete

Parameter `speed_secondary` is used when it is motor group of `motor_AB` running together. By default, `speed_secondary` equals `speed_primary`.

Parameter `wait_complete` controls whether a given call blocks execution until the operation has completed. By default, `wait_complete` is `True`. A new command interrupts the one running on the motor: if some thread is waiting for the interrupted one to complete, its call raises `CommandDiscarded`.

Speed values range is `-1.0` to `1.0`, float values. _Note: In group angled mode, total rotation angle is distributed across 2 motors according to motor speeds ratio, see official doc [here](https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#tacho-math)._

An example:
```python
from pylgbst.hub import MoveHub
import time

hub = MoveHub()

hub.motor_A.timed(0.5, 0.8)
hub.motor_A.timed(0.5, -0.8)

hub.motor_B.angled(90, 0.8)
hub.motor_B.angled(-90, 0.8)

hub.motor_AB.timed(1.5, 0.8, -0.8)
hub.motor_AB.angled(90, 0.8, -0.8)

hub.motor_external.start_speed(0.2)
time.sleep(2)
hub.motor_external.stop()
```

### Pairing motors

The Move Hub comes with A and B already paired as `motor_AB`. On hubs that support virtual port setup, any two motors can be paired the same way:

```python
pair = hub.connect_ports(hub.PORT_A, hub.PORT_B)
pair.timed(1.5, 0.8, -0.8)
hub.disconnect_ports(pair)
```

The Move Hub doesn't support virtual port setup: these calls raise `CommandFailed` there.

Example usage of non-blocking calls to rotate 2 independent motors in parallel:
```python
from pylgbst.hub import MoveHub

hub = MoveHub()

hub.motor_A.timed(0.5, 0.8, wait_complete=False)
hub.motor_B.angled(90, 0.8, wait_complete=False)
hub.motor_A.wait_complete()
hub.motor_B.wait_complete()
```

## Motor Rotation Sensors

Any motor allows to subscribe to its rotation sensor. Two sensor modes are available: rotation angle (`EncodedMotor.SENSOR_ANGLE`) and rotation speed (`EncodedMotor.SENSOR_SPEED`). Example: 

```python
from pylgbst.hub import MoveHub, EncodedMotor
import time

def callback(angle):
    print("Angle: %s" % angle)

hub = MoveHub()

hub.motor_A.subscribe(callback, mode=EncodedMotor.SENSOR_ANGLE)
time.sleep(60) # rotate motor A
hub.motor_A.unsubscribe(callback)
```

Both at once, see [combined modes](Peripherals.md#subscribing-to-sensors):

```python
hub.motor_A.subscribe(lambda speed, angle: print(speed, angle),
                      mode=(EncodedMotor.SENSOR_SPEED, EncodedMotor.SENSOR_ANGLE))
```
