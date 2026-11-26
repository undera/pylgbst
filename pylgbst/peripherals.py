"""
Blocking peripherals: each wraps its `pylgbst.aio.peripherals` counterpart, running its coroutines
on the hub's event loop thread. Callbacks run on worker threads, so they may call blocking methods.
"""
import asyncio
import functools
import logging
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple

from pylgbst.aio import peripherals as aio
from pylgbst.aio.peripherals import (  # noqa: F401 (re-exported)
    COLORS, COLOR_BLACK, COLOR_BLUE, COLOR_CYAN, COLOR_GREEN, COLOR_LIGHTBLUE, COLOR_NONE, COLOR_ORANGE, COLOR_PINK,
    COLOR_PURPLE, COLOR_RED, COLOR_WHITE, COLOR_YELLOW, CurrentConstants, EncodedMotorConstants, LEDLightConstants,
    LEDRGBConstants, MotorConstants, RemoteButtonConstants, TemperatureConstants, TiltSensorConstants,
    TrainMotorConstants, VisionSensorConstants, VoltageConstants,
)

if TYPE_CHECKING:
    from pylgbst.hub import Hub

log = logging.getLogger("peripherals")


def _blocking(async_method):
    """A blocking method of a wrapper, running `async_method` of the wrapped async object"""

    @functools.wraps(async_method)
    def method(self, *args, **kwargs):
        return self.hub.loop_thread.run(async_method(self.aio, *args, **kwargs))

    return method


def _off_loop(callback: Callable) -> Callable:
    """A coroutine function calling the blocking `callback` on a worker thread, off the event loop"""

    async def call(*values):
        await asyncio.get_running_loop().run_in_executor(None, functools.partial(callback, *values))

    return call


class _Callbacks:
    """Blocking callbacks and the coroutine functions that deliver to them"""

    def __init__(self):
        self._delivering: Dict[Callable, Callable] = {}

    def add(self, callback: Optional[Callable]) -> Optional[Callable]:
        if callback is None:
            return None
        return self._delivering.setdefault(callback, _off_loop(callback))

    def pop(self, callback: Optional[Callable]) -> Optional[Callable]:
        return self._delivering.pop(callback, None)


class Peripheral:
    """
    :param hub: the hub, which creates its peripherals as the hub announces them
    :param aio_peripheral: the wrapped async peripheral
    """

    def __init__(self, hub: 'Hub', aio_peripheral: aio.Peripheral):
        self.hub = hub
        self.aio = aio_peripheral
        self._callbacks = _Callbacks()

    def __repr__(self):
        return repr(self.aio)

    @property
    def port(self) -> int:
        return self.aio.port

    @property
    def virtual_ports(self) -> Tuple[int, ...]:
        return self.aio.virtual_ports

    set_port_mode = _blocking(aio.Peripheral.set_port_mode)
    get_sensor_data = _blocking(aio.Peripheral.get_sensor_data)
    describe_possible_modes = _blocking(aio.Peripheral.describe_possible_modes)

    def subscribe(self, callback: Optional[Callable], mode: Optional[int] = None, granularity: int = 1) -> None:
        """Call `callback(*values)` on each value update, on a worker thread. One mode per port."""
        self.hub.loop_thread.run(self.aio.subscribe(self._callbacks.add(callback), mode, granularity))

    def unsubscribe(self, callback: Optional[Callable] = None) -> None:
        self.hub.loop_thread.run(self.aio.unsubscribe(self._callbacks.pop(callback)))


class LEDRGB(LEDRGBConstants, Peripheral):
    set_color = _blocking(aio.LEDRGB.set_color)
    color = property(fset=set_color)  # no getter: the hub does not report the color


class LEDLight(LEDLightConstants, Peripheral):
    """Headlight kit (LPF2-LIGHT)"""
    set_brightness = _blocking(aio.LEDLight.set_brightness)
    get_brightness = _blocking(aio.LEDLight.get_brightness)
    brightness = property(get_brightness, set_brightness)


class BaseMotor(Peripheral):
    @property
    def cmd_in_progress(self) -> bool:
        return self.aio.cmd_in_progress

    wait_complete = _blocking(aio.BaseMotor.wait_complete)


class TrainMotor(TrainMotorConstants, BaseMotor):
    """Simple DC motor (Lego 88011), see https://github.com/undera/pylgbst/issues/129"""
    power = _blocking(aio.TrainMotor.power)
    stop = _blocking(aio.TrainMotor.stop)


class Motor(MotorConstants, BaseMotor):
    start_power = _blocking(aio.Motor.start_power)
    stop = _blocking(aio.Motor.stop)
    set_acc_profile = _blocking(aio.Motor.set_acc_profile)
    set_dec_profile = _blocking(aio.Motor.set_dec_profile)
    start_speed = _blocking(aio.Motor.start_speed)
    timed = _blocking(aio.Motor.timed)


class EncodedMotor(EncodedMotorConstants, Motor):
    angled = _blocking(aio.EncodedMotor.angled)
    goto_position = _blocking(aio.EncodedMotor.goto_position)
    preset_encoder = _blocking(aio.EncodedMotor.preset_encoder)


class TiltSensor(TiltSensorConstants, Peripheral):
    pass


class VisionSensor(VisionSensorConstants, Peripheral):
    set_color = _blocking(aio.VisionSensor.set_color)
    set_ir_tx = _blocking(aio.VisionSensor.set_ir_tx)
    color = property(_blocking(aio.VisionSensor.get_color))
    distance = property(_blocking(aio.VisionSensor.get_distance))
    reflected_light = property(_blocking(aio.VisionSensor.get_reflected_light))
    luminosity = property(_blocking(aio.VisionSensor.get_luminosity))
    detection_count = property(_blocking(aio.VisionSensor.get_detection_count))
    rgb_color = property(_blocking(aio.VisionSensor.get_rgb_color))


class Voltage(VoltageConstants, Peripheral):
    voltage = property(_blocking(aio.Voltage.get_voltage))


class Current(CurrentConstants, Peripheral):
    current = property(_blocking(aio.Current.get_current))


class Temperature(TemperatureConstants, Peripheral):
    temperature = property(_blocking(aio.Temperature.get_temperature))


class RemoteButton(RemoteButtonConstants, Peripheral):
    """A button set of the remote handset, see `pylgbst.aio.peripherals.RemoteButton`"""


class Button:
    """The hub's own green button: callbacks get 1 for pressed, 0 for released"""

    def __init__(self, hub: 'Hub', aio_button: aio.Button):
        self.hub = hub
        self.aio = aio_button
        self._callbacks = _Callbacks()

    def subscribe(self, callback: Callable, mode=None, granularity=1) -> None:
        """`mode` and `granularity` are not used, kept for compatibility"""
        del mode, granularity
        self.hub.loop_thread.run(self.aio.subscribe(self._callbacks.add(callback)))

    def unsubscribe(self, callback: Optional[Callable] = None) -> None:
        self.hub.loop_thread.run(self.aio.unsubscribe(self._callbacks.pop(callback)))


_WRAPPERS = {
    aio.Peripheral: Peripheral,
    aio.LEDRGB: LEDRGB,
    aio.LEDLight: LEDLight,
    aio.TrainMotor: TrainMotor,
    aio.Motor: Motor,
    aio.EncodedMotor: EncodedMotor,
    aio.TiltSensor: TiltSensor,
    aio.VisionSensor: VisionSensor,
    aio.Voltage: Voltage,
    aio.Current: Current,
    aio.Temperature: Temperature,
    aio.RemoteButton: RemoteButton,
}


def wrap(hub: 'Hub', aio_peripheral: aio.Peripheral) -> Peripheral:
    return _WRAPPERS[type(aio_peripheral)](hub, aio_peripheral)
