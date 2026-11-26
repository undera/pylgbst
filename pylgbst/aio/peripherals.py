"""
Async peripherals: devices attached to hub ports, plus the hub's own button
"""
import logging
from struct import pack, unpack
from typing import TYPE_CHECKING, AsyncIterator, Callable, Dict, Hashable, List, Optional, Tuple, Union

from pylgbst.exceptions import CommandFailed
from pylgbst.messages import (
    MsgHubProperties, MsgPortInfo, MsgPortInfoRequest, MsgPortInputFmtCombined, MsgPortInputFmtSetupCombined,
    MsgPortInputFmtSetupSingle, MsgPortInputFmtSingle, MsgPortModeInfo, MsgPortModeInfoRequest, MsgPortOutput,
    MsgPortValueCombined, UpstreamMsg,
)
from pylgbst.utilities import abs_scaled_100, str2hex, usbyte, usint, ushort

from .subscriptions import Subscription

if TYPE_CHECKING:
    from .hub import Hub

log = logging.getLogger(__name__)

COLOR_BLACK = 0x00
COLOR_PINK = 0x01
COLOR_PURPLE = 0x02
COLOR_BLUE = 0x03
COLOR_LIGHTBLUE = 0x04
COLOR_CYAN = 0x05
COLOR_GREEN = 0x06
COLOR_YELLOW = 0x07
COLOR_ORANGE = 0x08
COLOR_RED = 0x09
COLOR_WHITE = 0x0A
COLOR_NONE = 0xFF
COLORS = {
    COLOR_BLACK: "BLACK",
    COLOR_PINK: "PINK",
    COLOR_PURPLE: "PURPLE",
    COLOR_BLUE: "BLUE",
    COLOR_LIGHTBLUE: "LIGHTBLUE",
    COLOR_CYAN: "CYAN",
    COLOR_GREEN: "GREEN",
    COLOR_YELLOW: "YELLOW",
    COLOR_ORANGE: "ORANGE",
    COLOR_RED: "RED",
    COLOR_WHITE: "WHITE",
    COLOR_NONE: "NONE",
}


class Subscribable:
    """Fan-out of decoded values to callbacks and `values()` iterators"""

    KEEP_ALL_VALUES = False  # True for events, which must not be dropped

    def __init__(self):
        self._subscriptions: Dict[Hashable, Subscription] = {}

    def _add_subscription(self, key: Hashable) -> Subscription:
        subscription = Subscription(self.KEEP_ALL_VALUES)
        self._subscriptions[key] = subscription
        return subscription

    def _remove_subscription(self, key: Hashable) -> None:
        subscription = self._subscriptions.pop(key, None)
        if subscription:
            subscription.close()

    def _publish(self, values: Tuple) -> None:
        for subscription in self._subscriptions.values():
            subscription.push(values)

    def close_subscriptions(self) -> None:
        """End delivery to callbacks and `values()` iterators: the values source is gone"""
        for subscription in self._subscriptions.values():
            subscription.close()
        self._subscriptions.clear()


Modes = Union[None, int, Tuple[int, ...]]  # a tuple of modes subscribes to them all at once, see `CombinedMode`

_DATASET_SIZES = {"8 bit": 1, "16 bit": 2, "32 bit": 4, "FLOAT": 4}


class CombinedMode:
    """
    Several modes of one port reporting together. Each mode dataset is an entry; the hub reports
    only the entries that changed, so the latest raw value of each entry is kept here.

    :param modes: in the order their values are delivered
    :param entries: (mode, dataset) pairs, in the order the hub was set up with
    :param sizes: value size in bytes of each entry
    """

    def __init__(self, modes: Tuple[int, ...], entries: List[Tuple[int, int]], sizes: List[int]):
        self.modes = modes
        self.entries = entries
        self.sizes = sizes
        self._raw: List[Optional[bytes]] = [None] * len(entries)

    def update(self, msg: MsgPortValueCombined) -> None:
        data = msg.payload
        for index, size in enumerate(self.sizes):
            if msg.pointer & (1 << index):
                self._raw[index], data = data[:size], data[size:]

    def is_complete(self) -> bool:
        """Every entry has a value"""
        return None not in self._raw

    def mode_data(self, mode: int) -> bytes:
        return b"".join(raw for (entry_mode, _), raw in zip(self.entries, self._raw) if entry_mode == mode)


class Peripheral(Subscribable):
    """
    :param hub: the hub this peripheral is attached to
    :param port: port number on the hub
    """

    DEFAULT_MODE = 0x00

    def __init__(self, hub: 'Hub', port: int):
        super().__init__()
        self.hub = hub
        self.port = port
        self.virtual_ports: Tuple[int, ...] = ()
        self.port_mode = MsgPortInputFmtSingle(port, None, False, 1)
        self.combined_mode: Optional[CombinedMode] = None  # when set, it rules the port instead of `port_mode`

    def _add_subscription(self, key: Hashable) -> Subscription:
        subscription = super()._add_subscription(key)
        if self.combined_mode and self.combined_mode.is_complete():  # the hub repeats values only once they change
            subscription.push(self._combined_values())
        return subscription

    def __repr__(self):
        msg = "%s on port 0x%x" % (self.__class__.__name__, self.port)
        if self.virtual_ports:
            msg += " (ports 0x%x and 0x%x combined)" % self.virtual_ports
        return msg

    async def set_port_mode(self, mode: int, send_updates: Optional[bool] = None,
                            update_delta: Optional[int] = None) -> None:
        assert not self.virtual_ports, "TODO: support combined mode for sensors"
        if self.combined_mode:
            await self._reset_combined_mode()
        if send_updates is None:
            send_updates = self.port_mode.upd_enabled
        if update_delta is None:
            update_delta = self.port_mode.upd_delta

        if (self.port_mode.mode, self.port_mode.upd_enabled, self.port_mode.upd_delta) == \
                (mode, send_updates, update_delta):
            return

        resp = await self.hub.request(MsgPortInputFmtSetupSingle(self.port, mode, update_delta, send_updates))
        assert isinstance(resp, MsgPortInputFmtSingle)
        self.port_mode = resp

    async def get_sensor_data(self, mode: int) -> Tuple:
        await self.set_port_mode(mode)
        resp = await self.hub.request(MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_PORT_VALUE))
        return self.decode_port_data(resp)

    async def subscribe(self, callback: Optional[Callable], mode: Modes = None, granularity: int = 1) -> None:
        """
        Call `callback(*values)` on each value update, in a task of its own, so it may await hub commands.
        One mode per port: subscribers in another mode have to unsubscribe first.

        :param mode: a tuple of modes gets the values of them all at once, in the given order;
            the hub accepts only some combinations, see `describe_possible_modes()`
        """
        await self._enable_updates(mode, granularity)
        if callback and callback not in self._subscriptions:
            self._add_subscription(callback).deliver_to(callback)

    async def unsubscribe(self, callback: Optional[Callable] = None) -> None:
        self._remove_subscription(callback)
        await self._disable_updates_if_unused()

    async def values(self, mode: Modes = None, granularity: int = 1) -> AsyncIterator[Tuple]:
        """Iterate value updates; updates are switched off when the iteration ends"""
        key = object()
        await self._enable_updates(mode, granularity)
        subscription = self._add_subscription(key)
        try:
            async for values in subscription:
                yield values
        finally:
            self._remove_subscription(key)
            await self._disable_updates_if_unused()

    async def _enable_updates(self, mode: Modes, granularity: int) -> None:
        mode = self.DEFAULT_MODE if mode is None else mode
        active = self.combined_mode.modes if self.combined_mode else self.port_mode.mode
        if self._subscriptions and active != mode:
            raise ValueError("Port is in active mode %r, unsubscribe all subscribers first" % (active,))
        if isinstance(mode, tuple):
            if active != mode:
                await self._set_combined_mode(mode, granularity)
        else:
            await self.set_port_mode(mode, True, granularity)

    async def _disable_updates_if_unused(self) -> None:
        if self._subscriptions:
            return
        if self.combined_mode:
            await self._reset_combined_mode()
        elif not self.port_mode.upd_enabled:
            log.warning("Attempt to unsubscribe while port value updates are off: %s", self)
        else:
            await self.set_port_mode(self.port_mode.mode, False)

    async def _set_combined_mode(self, modes: Tuple[int, ...], granularity: int) -> None:
        """Lock the port, set up each mode, choose their datasets, unlock: the spec's sequence"""
        assert not self.virtual_ports, "Virtual ports have no combined mode"
        if self.combined_mode:
            await self._reset_combined_mode()
        hub_order = sorted(set(modes))  # the hub rejects modes out of their combination's order
        combination = await self._combination_index(hub_order)
        entries, sizes = [], []
        for mode in hub_order:
            fmt = await self.hub.request(
                MsgPortModeInfoRequest(self.port, mode, MsgPortModeInfoRequest.INFO_VALUE_FORMAT))
            assert isinstance(fmt, MsgPortModeInfo)
            entries += [(mode, dataset) for dataset in range(fmt.value["datasets"])]
            sizes += [_DATASET_SIZES[fmt.value["type"]]] * fmt.value["datasets"]
        if len(entries) > 16:
            raise ValueError("Modes %r have %d datasets, combined mode takes up to 16" % (modes, len(entries)))

        setup = MsgPortInputFmtSetupCombined
        self.port_mode = await self.hub.request(setup(self.port, setup.SUB_LOCK))
        self.combined_mode = CombinedMode(modes, entries, sizes)
        try:
            for mode in hub_order:
                await self.hub.request(MsgPortInputFmtSetupSingle(self.port, mode, granularity, True))
            await self.hub.send(setup(self.port, setup.SUB_SET_MODES, combination, entries))
            resp = await self.hub.request(setup(self.port, setup.SUB_UNLOCK_MULTI_UPDATE))
            assert isinstance(resp, MsgPortInputFmtCombined)
            if resp.pointer != (1 << len(entries)) - 1:
                raise CommandFailed("Port 0x%x accepted entries 0b%s of %r"
                                    % (self.port, bin(resp.pointer)[2:], entries))
            # the hub may not send the first values on its own, and later sends only the changed ones
            await self.hub.request(MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_PORT_VALUE))
        except Exception:
            await self._reset_combined_mode()  # unlocks the port
            raise

    async def get_mode_combinations(self) -> List[List[int]]:
        """Modes the device reports at once, see `subscribe()`: any subset of one of these lists"""
        info = await self.hub.request(MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_MODE_COMBINATIONS))
        assert isinstance(info, MsgPortInfo)
        return [combination for combination in info.possible_mode_combinations if combination]

    async def _combination_index(self, modes: List[int]) -> int:
        combinations = await self.get_mode_combinations()
        for index, combination in enumerate(combinations):
            if set(modes) <= set(combination):
                return index
        raise ValueError("Port 0x%x can't combine modes %r, its combinations are %r" % (self.port, modes, combinations))

    async def _reset_combined_mode(self) -> None:
        """Back to single mode 0 without updates"""
        self.combined_mode = None
        self.port_mode = await self.hub.request(
            MsgPortInputFmtSetupCombined(self.port, MsgPortInputFmtSetupCombined.SUB_RESET))

    def on_port_value(self, msg: UpstreamMsg) -> None:
        if not isinstance(msg, MsgPortValueCombined):
            self._publish(self.decode_port_data(msg))
        elif not self.combined_mode:  # sent before the hub got the reset
            log.debug("Combined value on port 0x%x, which is not in combined mode: %r", self.port, msg)
        else:
            self.combined_mode.update(msg)
            if self.combined_mode.is_complete():
                self._publish(self._combined_values())

    def _combined_values(self) -> Tuple:
        return sum((self.decode_mode_data(mode, self.combined_mode.mode_data(mode))
                    for mode in self.combined_mode.modes), ())

    def decode_port_data(self, msg: UpstreamMsg) -> Tuple:
        """Sensor value according to the current port mode"""
        return self.decode_mode_data(self.port_mode.mode, msg.payload)

    def decode_mode_data(self, mode: int, data: bytes) -> Tuple:
        """Sensor value of `mode` in `data`"""
        log.warning("Unhandled data in mode %s on port 0x%x: %s", mode, self.port, str2hex(data))
        return ()

    async def _write_direct_mode(self, mode: int, params: bytes) -> None:
        await self.hub.output(MsgPortOutput(self.port, MsgPortOutput.WRITE_DIRECT_MODE_DATA, pack("<B", mode) + params))

    async def describe_possible_modes(self) -> dict:
        mode_info = await self.hub.request(MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_MODE_INFO))
        assert isinstance(mode_info, MsgPortInfo)
        info = {
            "mode_count": mode_info.total_modes,
            "input_modes": [],
            "output_modes": [],
            "capabilities": {
                "logically_combinable": mode_info.is_combinable(),
                "synchronizable": mode_info.is_synchronizable(),
                "can_output": mode_info.is_output(),
                "can_input": mode_info.is_input(),
            },
        }
        if mode_info.is_combinable():
            combinations = await self.hub.request(
                MsgPortInfoRequest(self.port, MsgPortInfoRequest.INFO_MODE_COMBINATIONS))
            assert isinstance(combinations, MsgPortInfo)
            info["possible_mode_combinations"] = combinations.possible_mode_combinations

        info["modes"] = [await self._describe_mode(mode) for mode in range(256)]
        info["output_modes"] = [await self._describe_mode(mode) for mode in mode_info.output_modes]
        info["input_modes"] = [await self._describe_mode(mode) for mode in mode_info.input_modes]
        log.debug("Port info for 0x%x: %s", self.port, info)
        return info

    async def _describe_mode(self, mode: int) -> dict:
        descr = {"Mode": mode}
        for info in MsgPortModeInfoRequest.INFO_TYPES:
            try:
                resp = await self.hub.request(MsgPortModeInfoRequest(self.port, mode, info))
                assert isinstance(resp, MsgPortModeInfo)
                descr[MsgPortModeInfoRequest.INFO_TYPES[info]] = resp.value
            except CommandFailed as exc:
                log.debug("Got error while requesting info 0x%x: %s", info, exc)
                if info == MsgPortModeInfoRequest.INFO_NAME:
                    break
        return descr


class LEDRGBConstants:
    MODE_INDEX = 0x00
    MODE_RGB = 0x01


class LEDRGB(LEDRGBConstants, Peripheral):
    async def set_color(self, color) -> None:
        """
        :param color: (r, g, b) tuple, or one of the COLOR_* constants; COLOR_BLACK and COLOR_NONE turn it off
        """
        if isinstance(color, (list, tuple)):
            assert len(color) == 3, "RGB color has to have 3 values"
            await self.set_port_mode(self.MODE_RGB)
            await self._write_direct_mode(self.MODE_RGB, pack("<BBB", *color))
        else:
            if color == COLOR_NONE:
                color = COLOR_BLACK
            if color not in COLORS:
                raise ValueError("Color %s is not in list of available colors" % color)
            await self.set_port_mode(self.MODE_INDEX)
            await self._write_direct_mode(self.MODE_INDEX, pack("<B", color))

    def decode_mode_data(self, mode, data):
        if len(data) == 3:
            return usbyte(data, 0), usbyte(data, 1), usbyte(data, 2)
        return usbyte(data, 0),


class LEDLightConstants:
    MODE_BRIGHTNESS = 0x00


class LEDLight(LEDLightConstants, Peripheral):
    """Headlight kit (LPF2-LIGHT)"""

    async def set_brightness(self, brightness) -> None:
        """:param brightness: 0..100"""
        if not isinstance(brightness, (int, float)) or not 0 <= brightness <= 100:
            raise ValueError("Brightness must be a number between 0 and 100")
        await self.set_port_mode(self.MODE_BRIGHTNESS)
        await self._write_direct_mode(self.MODE_BRIGHTNESS, pack("<B", int(brightness)))

    async def get_brightness(self) -> int:
        return (await self.get_sensor_data(self.MODE_BRIGHTNESS))[0]

    def decode_mode_data(self, mode, data):
        return usbyte(data, 0),


class BaseMotor(Peripheral):
    def __init__(self, hub: 'Hub', port: int):
        super().__init__(hub, port)
        self._last_done = None

    @property
    def cmd_in_progress(self) -> bool:
        return self._last_done is not None and not self._last_done.done()

    async def wait_complete(self) -> None:
        """Wait until the last command sent to the motor ends"""
        if self._last_done is not None:
            await self._last_done

    async def _output(self, subcmd: int, params: bytes, wait_complete: bool = True) -> None:
        self._last_done = await self.hub.output(MsgPortOutput(self.port, subcmd, params), wait_complete)


class TrainMotorConstants:
    SUBCMD_POWER = 0x00


class TrainMotor(TrainMotorConstants, BaseMotor):
    """Simple DC motor (Lego 88011), see https://github.com/undera/pylgbst/issues/129"""

    async def power(self, param: float = 1.0) -> None:
        """:param param: -1.0..1.0"""
        await self._output(MsgPortOutput.WRITE_DIRECT_MODE_DATA, pack("<Bb", self.SUBCMD_POWER, abs_scaled_100(param)))

    async def stop(self) -> None:
        await self.power(0)


class MotorConstants:
    SUBCMD_START_POWER = 0x01
    SUBCMD_START_POWER_GROUPED = 0x02
    SUBCMD_SET_ACC_TIME = 0x05
    SUBCMD_SET_DEC_TIME = 0x06
    SUBCMD_START_SPEED = 0x07
    SUBCMD_START_SPEED_FOR_TIME = 0x09

    END_STATE_BRAKE = 127
    END_STATE_HOLD = 126
    END_STATE_FLOAT = 0


class Motor(MotorConstants, BaseMotor):
    @staticmethod
    def _speed_abs(relative: float) -> int:
        if relative in (Motor.END_STATE_BRAKE, Motor.END_STATE_HOLD):
            # https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#output-sub-command-startpower-power
            return relative
        return abs_scaled_100(relative)

    def _speeds(self, primary: float, secondary: Optional[float]) -> bytes:
        params = pack("<b", self._speed_abs(primary))
        if self.virtual_ports:
            params += pack("<b", self._speed_abs(primary if secondary is None else secondary))
        return params

    async def _send_cmd(self, subcmd: int, params: bytes, wait_complete: bool = True) -> None:
        if self.virtual_ports:
            subcmd += 1  # de-facto rule: the grouped variant follows the single one
        await self._output(subcmd, params, wait_complete)

    async def start_power(self, power_primary: float = 1.0, power_secondary: Optional[float] = None) -> None:
        """https://lego.github.io/lego-ble-wireless-protocol-docs/index.html#output-sub-command-startpower-power"""
        cmd = self.SUBCMD_START_POWER_GROUPED - 1 if self.virtual_ports else self.SUBCMD_START_POWER
        await self._send_cmd(cmd, self._speeds(power_primary, power_secondary))

    async def stop(self) -> None:
        await self.timed(0)

    async def set_acc_profile(self, seconds: float, profile_no: int = 0x00) -> None:
        await self._send_cmd(self.SUBCMD_SET_ACC_TIME, pack("<HB", int(seconds * 1000), profile_no))

    async def set_dec_profile(self, seconds: float, profile_no: int = 0x00) -> None:
        await self._send_cmd(self.SUBCMD_SET_DEC_TIME, pack("<HB", int(seconds * 1000), profile_no))

    async def start_speed(self, speed_primary: float = 1.0, speed_secondary: Optional[float] = None,
                          max_power: float = 1.0, use_profile: int = 0b11) -> None:
        params = self._speeds(speed_primary, speed_secondary) + pack("<BB", int(100 * max_power), use_profile)
        await self._send_cmd(self.SUBCMD_START_SPEED, params)

    async def timed(self, seconds: float, speed_primary: float = 1.0, speed_secondary: Optional[float] = None,
                    max_power: float = 1.0, end_state: int = MotorConstants.END_STATE_BRAKE,
                    use_profile: int = 0b11, wait_complete: bool = True) -> None:
        params = pack("<H", int(seconds * 1000)) + self._speeds(speed_primary, speed_secondary) \
                 + pack("<BBB", int(100 * max_power), end_state, use_profile)
        await self._send_cmd(self.SUBCMD_START_SPEED_FOR_TIME, params, wait_complete)


class EncodedMotorConstants(MotorConstants):
    SUBCMD_START_SPEED_FOR_DEGREES = 0x0B
    SUBCMD_GOTO_ABSOLUTE_POSITION = 0x0D
    SUBCMD_PRESET_ENCODER = 0x14

    SENSOR_POWER = 0x00  # not an input mode, yet returns some numbers
    SENSOR_SPEED = 0x01
    SENSOR_ANGLE = 0x02
    SENSOR_TEST = 0x03  # exists, but neither input nor output mode

    DEFAULT_MODE = SENSOR_ANGLE


class EncodedMotor(EncodedMotorConstants, Motor):
    async def angled(self, degrees: float, speed_primary: float = 1.0, speed_secondary: Optional[float] = None,
                     max_power: float = 1.0, end_state: int = MotorConstants.END_STATE_BRAKE,
                     use_profile: int = 0b11, wait_complete: bool = True) -> None:
        if speed_secondary is None:
            speed_secondary = speed_primary
        degrees = int(round(degrees))
        if degrees < 0:
            degrees, speed_primary, speed_secondary = -degrees, -speed_primary, -speed_secondary

        params = pack("<I", degrees) + self._speeds(speed_primary, speed_secondary) \
                 + pack("<BBB", int(100 * max_power), end_state, use_profile)
        await self._send_cmd(self.SUBCMD_START_SPEED_FOR_DEGREES, params, wait_complete)

    async def goto_position(self, degrees_primary: int, degrees_secondary: Optional[int] = None, speed: float = 1.0,
                            max_power: float = 1.0, end_state: int = MotorConstants.END_STATE_BRAKE,
                            use_profile: int = 0b11, wait_complete: bool = True) -> None:
        params = pack("<i", degrees_primary)
        if self.virtual_ports:
            params += pack("<i", degrees_primary if degrees_secondary is None else degrees_secondary)
        params += pack("<b", self._speed_abs(speed)) + pack("<BBB", int(100 * max_power), end_state, use_profile)
        await self._send_cmd(self.SUBCMD_GOTO_ABSOLUTE_POSITION, params, wait_complete)

    async def preset_encoder(self, degrees: int = 0, degrees_secondary: Optional[int] = None,
                             only_combined: bool = False) -> None:
        if self.virtual_ports and not only_combined:
            secondary = degrees if degrees_secondary is None else degrees_secondary
            await self._send_cmd(self.SUBCMD_PRESET_ENCODER, pack("<ii", degrees, secondary))
        else:
            await self._write_direct_mode(self.SENSOR_ANGLE, pack("<i", degrees))

    def decode_mode_data(self, mode, data):
        if mode == self.SENSOR_ANGLE:
            return unpack("<l", data[0:4])[0],
        if mode == self.SENSOR_SPEED:
            return unpack("<b", data[0:1])[0],
        log.debug("Got motor sensor data in unexpected mode %s", mode)
        return ()


class TiltSensorConstants:
    MODE_2AXIS_ANGLE = 0x00
    MODE_2AXIS_SIMPLE = 0x01
    MODE_3AXIS_SIMPLE = 0x02
    MODE_IMPACT_COUNT = 0x03
    MODE_3AXIS_ACCEL = 0x04
    MODE_ORIENT_CF = 0x05
    MODE_IMPACT_CF = 0x06
    MODE_CALIBRATION = 0x07

    TRI_BACK = 0x00
    TRI_UP = 0x01
    TRI_DOWN = 0x02
    TRI_LEFT = 0x03
    TRI_RIGHT = 0x04
    TRI_FRONT = 0x05

    DUO_HORIZ = 0x00
    DUO_DOWN = 0x03
    DUO_LEFT = 0x05
    DUO_RIGHT = 0x07
    DUO_UP = 0x09

    DUO_STATES = {
        DUO_HORIZ: "HORIZONTAL",
        DUO_DOWN: "DOWN",
        DUO_LEFT: "LEFT",
        DUO_RIGHT: "RIGHT",
        DUO_UP: "UP",
    }

    TRI_STATES = {
        TRI_BACK: "BACK",
        TRI_UP: "UP",
        TRI_DOWN: "DOWN",
        TRI_LEFT: "LEFT",
        TRI_RIGHT: "RIGHT",
        TRI_FRONT: "FRONT",
    }

    DEFAULT_MODE = MODE_3AXIS_SIMPLE


class TiltSensor(TiltSensorConstants, Peripheral):
    def decode_mode_data(self, mode, data):
        if mode == self.MODE_2AXIS_ANGLE:
            return unpack("<b", data[0:1])[0], unpack("<b", data[1:2])[0]
        if mode in (self.MODE_3AXIS_SIMPLE, self.MODE_2AXIS_SIMPLE, self.MODE_ORIENT_CF, self.MODE_IMPACT_CF):
            return usbyte(data, 0),
        if mode == self.MODE_IMPACT_COUNT:
            return usint(data, 0),
        if mode == self.MODE_3AXIS_ACCEL:
            return unpack("<b", data[0:1])[0], unpack("<b", data[1:2])[0], unpack("<b", data[2:3])[0]
        if mode == self.MODE_CALIBRATION:
            return usbyte(data, 0), usbyte(data, 1), usbyte(data, 2)
        log.debug("Got tilt sensor data in unexpected mode %s", mode)
        return ()


class VisionSensorConstants:
    COLOR_INDEX = 0x00
    DISTANCE_INCHES = 0x01
    COUNT_2INCH = 0x02
    DISTANCE_REFLECTED = 0x03
    AMBIENT_LIGHT = 0x04
    SET_COLOR = 0x05
    COLOR_RGB = 0x06
    SET_IR_TX = 0x07
    COLOR_DISTANCE_FLOAT = 0x08
    DEBUG = 0x09  # first value is ambient light, second is zero
    CALIBRATE = 0x0A  # gives constant values

    DEFAULT_MODE = COLOR_DISTANCE_FLOAT


class VisionSensor(VisionSensorConstants, Peripheral):
    """
    TODO: in combined mode, distance, reflected light and RGB values differ from the same modes subscribed
     one at a time (e.g. distance 192 vs 10 with nothing in front), so the decoding here may not fit them
    """

    def decode_mode_data(self, mode, data):
        if mode == self.COLOR_INDEX:
            return usbyte(data, 0),
        if mode == self.COLOR_DISTANCE_FLOAT:
            val = usbyte(data, 1)
            partial = usbyte(data, 3)
            if partial:
                val += 1.0 / partial
            return usbyte(data, 0), float(val)
        if mode == self.DISTANCE_INCHES:
            return usbyte(data, 0),
        if mode in (self.DISTANCE_REFLECTED, self.AMBIENT_LIGHT):
            return usbyte(data, 0) / 100.0,
        if mode == self.COUNT_2INCH:
            return usint(data, 0),
        if mode == self.COLOR_RGB:
            return tuple(int(255 * ushort(data, offset) / 1023.0) for offset in (0, 2, 4))
        if mode == self.DEBUG:
            return 10 * ushort(data, 0) / 1023.0, 10 * ushort(data, 2) / 1023.0
        if mode == self.CALIBRATE:
            return tuple(ushort(data, x * 2) for x in range(8))
        log.debug("Unhandled VisionSensor data in mode %s: %s", mode, str2hex(data))
        return ()

    async def set_color(self, color: int) -> None:
        """Color of the sensor's LED; COLOR_BLACK and COLOR_NONE turn it off"""
        if color == COLOR_NONE:
            color = COLOR_BLACK
        if color not in COLORS:
            raise ValueError("Color %s is not in list of available colors" % color)
        await self.set_port_mode(self.SET_COLOR)
        await self._write_direct_mode(self.SET_COLOR, pack("<B", color))

    async def set_ir_tx(self, level: float = 1.0) -> None:
        assert 0 <= level <= 1.0
        await self.set_port_mode(self.SET_IR_TX)
        await self._write_direct_mode(self.SET_IR_TX, pack("<H", int(level * 65535)))

    async def get_color(self) -> int:
        """One of COLORS keys"""
        return (await self.get_sensor_data(self.COLOR_INDEX))[0]

    async def get_distance(self) -> int:
        """0..10"""
        return (await self.get_sensor_data(self.DISTANCE_INCHES))[0]

    async def get_reflected_light(self) -> float:
        """0..1.0"""
        return (await self.get_sensor_data(self.DISTANCE_REFLECTED))[0]

    async def get_luminosity(self) -> float:
        """0..1.0"""
        return (await self.get_sensor_data(self.AMBIENT_LIGHT))[0]

    async def get_detection_count(self) -> int:
        """Number of detections ~2 inches in front of the sensor"""
        return (await self.get_sensor_data(self.COUNT_2INCH))[0]

    async def get_rgb_color(self) -> Tuple[int, int, int]:
        return await self.get_sensor_data(self.COLOR_RGB)


class VoltageConstants:
    VOLTAGE_L = 0x00
    VOLTAGE_S = 0x01


class Voltage(VoltageConstants, Peripheral):
    def decode_mode_data(self, mode, data):
        return 9600.0 * ushort(data, 0) / 3893.0 / 1000.0,

    async def get_voltage(self) -> float:
        """Battery voltage in volts"""
        return (await self.get_sensor_data(self.VOLTAGE_L))[0]


class CurrentConstants:
    CURRENT_L = 0x00
    CURRENT_S = 0x01


class Current(CurrentConstants, Peripheral):
    def decode_mode_data(self, mode, data):
        return 2444 * ushort(data, 0) / 4095.0,

    async def get_current(self) -> float:
        """Battery current in mA"""
        return (await self.get_sensor_data(self.CURRENT_L))[0]


class TemperatureConstants:
    MODE_TEMP = 0


class Temperature(TemperatureConstants, Peripheral):
    def decode_mode_data(self, mode, data):
        magic_offset = 2.1  # brings the reading to the real temperature
        return (unpack("<h", data)[0] / 10) - magic_offset,

    async def get_temperature(self) -> float:
        """Degrees Celsius"""
        return (await self.get_sensor_data(self.MODE_TEMP))[0]


class _HubButtonEvents:
    """Green hub button presses arrive as hub property updates, not port values"""

    def __init__(self, hub: 'Hub', on_press: Callable[[Tuple], None]):
        self._hub = hub
        self._on_press = on_press
        self._state_reply_pending = False
        hub.add_message_handler(MsgHubProperties, self._on_properties)

    async def enable(self) -> None:
        self._state_reply_pending = True  # the reply carries the current state, not a press
        await self._hub.request(MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_ENABLE))

    async def disable(self) -> None:
        await self._hub.send(MsgHubProperties(MsgHubProperties.BUTTON, MsgHubProperties.UPD_DISABLE))

    def _on_properties(self, msg: MsgHubProperties) -> None:
        if msg.property == MsgHubProperties.BUTTON and msg.operation == MsgHubProperties.UPSTREAM_UPDATE:
            if self._state_reply_pending:
                self._state_reply_pending = False
                return
            self._on_press((usbyte(msg.parameters, 0),))


class Button(Subscribable):
    """The hub's own green button: values are (pressed,) with 1 for pressed, 0 for released"""

    KEEP_ALL_VALUES = True

    def __init__(self, hub: 'Hub'):
        super().__init__()
        self._events = _HubButtonEvents(hub, self._publish)

    async def subscribe(self, callback: Callable) -> None:
        if callback in self._subscriptions:
            return
        if not self._subscriptions:
            await self._events.enable()
        self._add_subscription(callback).deliver_to(callback)

    async def unsubscribe(self, callback: Callable) -> None:
        self._remove_subscription(callback)
        if not self._subscriptions:
            await self._events.disable()

    async def values(self) -> AsyncIterator[Tuple]:
        key = object()
        if not self._subscriptions:
            await self._events.enable()
        subscription = self._add_subscription(key)
        try:
            async for values in subscription:
                yield values
        finally:
            self._remove_subscription(key)
            if not self._subscriptions:
                await self._events.disable()


class RemoteButtonConstants:
    RCKEY = 0x00
    KEYA = 0x01
    KEYR = 0x02

    button_sets = {0: "LEFT", 1: "RIGHT"}
    button_events = {b'\x01': "PLUS", b'\x7f': "RED", b'\xff': "MINUS", b'\x00': "RELEASE"}


class RemoteButton(RemoteButtonConstants, Peripheral):
    """
    A button set of the remote handset. Values are (event, side), e.g. ("PLUS", "LEFT");
    the green button reports (pressed,). Works with modes RCKEY, KEYA, KEYR, see
    https://virantha.github.io/bricknil/lego_api/lego.html#remote-buttons
    """

    KEEP_ALL_VALUES = True

    def __init__(self, hub: 'Hub', port: int):
        super().__init__(hub, port)
        self._green = _HubButtonEvents(hub, self._publish)

    async def _enable_updates(self, mode: Optional[int], granularity: int) -> None:
        if mode not in (None, self.RCKEY, self.KEYA, self.KEYR):
            raise ValueError("Invalid mode: %s" % mode)
        await super()._enable_updates(mode, granularity)

    def decode_mode_data(self, mode, data):
        return self.button_events[data], self.button_sets[self.port]
