# Peripheral Types

Here is the list of peripheral devices that have dedicated classes in library:

- [Motors](Motor.md)
- [RGB LED](LED.md)
- [Headlight](Headlight.md)
- [Tilt Sensor](TiltSensor.md)
- [Vision Sensor](VisionSensor.md) (color and/or distance)
- [Voltage and Current Sensors](VoltageCurrent.md)
- [Temperature](Temperature.md)

In case device you attached to Hub is of an unknown type, it will get generic `Peripheral` class, allowing direct low-level interactions.

## Subscribing to Sensors
Each sensor usually has several different "subscription modes", differing with callback parameters and value semantics. 

There is optional `granularity` parameter for each subscription call, by default it is `1`. This parameter tells Hub when to issue sensor data notification. Value of notification has to change greater or equals to `granularity` to issue notification. This means that specifying `0` will cause it to constantly send notifications, and specifying `5` will cause less frequent notifications, only when values change for more than `5` (inclusive).

It is possible to subscribe with multiple times for the same sensor. Only one, very last subscribe mode is in effect, with many subscriber callbacks allowed to receive notifications. 

Good practice for any program is to unsubscribe from all sensor subscriptions before exiting, especially when used with `DebugServer`.

## Generic Peripheral

In case you have used a peripheral that is not recognized by the library, it will be detected as generic `Peripheral` class. You still can use subscription and sensor info getting commands for it.  