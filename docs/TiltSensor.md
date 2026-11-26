### Tilt Sensor

There are several modes to subscribe to sensor, providing 2-axis, 3-axis and bump detect data.

An example:

```python
from pylgbst.hub import MoveHub, TiltSensor
import time

def callback(roll, pitch, yaw):
    print("Roll: %s / Pitch: %s / Yaw: %s" % (roll, pitch, yaw))

hub = MoveHub()

hub.tilt_sensor.subscribe(callback, mode=TiltSensor.MODE_3AXIS_ACCEL)
time.sleep(60) # turn MoveHub block in different ways
hub.tilt_sensor.unsubscribe(callback)
```

`TiltSensor` sensor mode constants:
- `MODE_2AXIS_SIMPLE` - use `callback(state)` for 2-axis simple state detect
- `MODE_2AXIS_ANGLE` - use `callback(roll, pitch)` for 2-axis roll&pitch degree values
- `MODE_3AXIS_SIMPLE` - use `callback(state)` for 3-axis simple state detect
- `MODE_3AXIS_ACCEL` - use `callback(roll, pitch, yaw)` for 3-axis roll&pitch&yaw degree values
- `MODE_IMPACT_COUNT` - use `callback(count)` to detect bumps

There are tilt sensor constants for "simple" states, for 2-axis mode their names are also available through `TiltSensor.DUO_STATES`:
- `DUO_HORIZ` - "HORIZONTAL"
- `DUO_DOWN` - "DOWN"
- `DUO_LEFT` - "LEFT"
- `DUO_RIGHT` - "RIGHT"
- `DUO_UP` - "UP"
  
For 3-axis simple mode map name is `TiltSensor.TRI_STATES` with values:
- `TRI_BACK` - "BACK"
- `TRI_UP` - "UP"
- `TRI_DOWN` - "DOWN"
- `TRI_LEFT` - "LEFT"
- `TRI_RIGHT` - "RIGHT"
- `TRI_FRONT` - "FRONT"


#### Presets

These settings apply whatever mode the sensor is subscribed in. Reading the matching mode shows the current setting:
- `set_impact_count(count)` - set the bump counter of `MODE_IMPACT_COUNT`.
- `set_orientation(side)` - choose which side of the hub counts as its bottom: `ORIENT_BOTTOM` (the default), `ORIENT_FRONT`, `ORIENT_BACK`, `ORIENT_LEFT`, `ORIENT_RIGHT` or `ORIENT_TOP`. `MODE_2AXIS_ANGLE` values become relative to it; on a Move Hub, `MODE_3AXIS_SIMPLE` doesn't change. Read it with `MODE_ORIENT_CF`.
- `set_impact_config(threshold, holdoff)` - set how hard a bump must be to count, and the pause before the next one can count. A Move Hub starts with `(127, 20)`. Read it with `MODE_IMPACT_CF`.

```python
hub.tilt_sensor.set_impact_count(0)
hub.tilt_sensor.set_orientation(TiltSensor.ORIENT_LEFT)
```
