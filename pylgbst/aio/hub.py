"""
Async hub: sends commands, routes the hub's messages, owns the connection lifecycle
"""
import asyncio
import logging
import time
from typing import Callable, Dict, List, Optional, Tuple, Type

from pylgbst.exceptions import HubDisconnected, HubError, ReplyTimeout
from pylgbst.messages import (
    DevTypes, DownstreamMsg, MsgHubAction, MsgHubAlert, MsgHubAttachedIO, MsgHubProperties, MsgPortOutput,
    MsgPortValueCombined, MsgPortValueSingle, MsgVirtualPortSetup, UpstreamMsg, decode_upstream,
)
from pylgbst.utilities import str2hex, usbyte, ushort

from .connection import Connection
from .peripherals import (
    Button, Current, EncodedMotor, LEDLight, LEDRGB, Motor, Peripheral, RemoteButton, Subscribable, Temperature,
    TiltSensor, TrainMotor, VisionSensor, Voltage,
)
from .requests import Awaiting, Requests

log = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = 5.0
DEFAULT_DEVICES_TIMEOUT = 10.0

PERIPHERAL_TYPES: Dict[DevTypes, Type[Peripheral]] = {
    DevTypes.MOTOR: Motor,
    DevTypes.SYSTEM_TRAIN_MOTOR: TrainMotor,
    DevTypes.MOTOR_EXTERNAL_TACHO: EncodedMotor,
    DevTypes.MOTOR_INTERNAL_TACHO: EncodedMotor,
    DevTypes.VISION_SENSOR: VisionSensor,
    DevTypes.RGB_LIGHT: LEDRGB,
    DevTypes.LED_LIGHT: LEDLight,
    DevTypes.TILT_EXTERNAL: TiltSensor,
    DevTypes.TILT_INTERNAL: TiltSensor,
    DevTypes.CURRENT: Current,
    DevTypes.VOLTAGE: Voltage,
    DevTypes.DUPLO_TRAIN_BASE_MOTOR: Motor,
    DevTypes.DUPLO_TRAIN_BASE_COLOR_SENSOR: VisionSensor,
    DevTypes.TECHNIC_LARGE_LINEAR_MOTOR: EncodedMotor,
    DevTypes.TECHNIC_XLARGE_LINEAR_MOTOR: EncodedMotor,
    DevTypes.TECHNIC_MEDIUM_ANGULAR_MOTOR: EncodedMotor,
    DevTypes.TECHNIC_LARGE_ANGULAR_MOTOR: EncodedMotor,
    DevTypes.REMOTE_CONTROL_BUTTON: RemoteButton,
    DevTypes.REMOTE_CONTROL_RSSI: Peripheral,
    DevTypes.TECHNIC_MEDIUM_HUB_TILT_SENSOR: TiltSensor,
    DevTypes.TECHNIC_MEDIUM_HUB_TEMPERATURE_SENSOR: Temperature,
    DevTypes.TECHNIC_COLOR_SENSOR: VisionSensor,
    DevTypes.TECHNIC_DISTANCE_SENSOR: VisionSensor,
    DevTypes.TECHNIC_MEDIUM_ANGULAR_MOTOR_GREY: EncodedMotor,
    DevTypes.TECHNIC_LARGE_ANGULAR_MOTOR_GREY: EncodedMotor,
}

MessageHandler = Callable[[UpstreamMsg], None]


class Hub:
    """
    Every command either resolves or raises: replies resolve requests, the hub's errors
    raise `CommandFailed`, a lost link raises `HubDisconnected` in everything still waiting.

    :param request_timeout: seconds to wait for the hub's first response to a command.
        It does not limit how long a motor command may run.
    :param devices_timeout: seconds `start()` waits for the hub to announce its built-in devices
    """

    REQUIRED_PORTS: Tuple[int, ...] = ()  # built-in devices `start()` waits for

    def __init__(self, connection: Connection, request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
                 devices_timeout: float = DEFAULT_DEVICES_TIMEOUT):
        self.connection = connection
        self.request_timeout = request_timeout
        self.devices_timeout = devices_timeout
        self.peripherals: Dict[int, Peripheral] = {}
        self._requests = Requests()
        self._handlers: List[Tuple[Type[UpstreamMsg], MessageHandler]] = []
        self._closed: Optional[HubError] = None
        self._watchdog: Optional[asyncio.Task] = None
        self._attached = asyncio.Event()
        self.add_message_handler(MsgHubAction, self._on_hub_action)
        self.add_message_handler(MsgHubAttachedIO, self._on_attached_io)
        self.add_message_handler(MsgPortValueSingle, self._on_port_value)
        self.add_message_handler(MsgPortValueCombined, self._on_port_value)

    async def start(self) -> None:
        """
        Start talking to the hub and wait for its built-in devices.

        :raises HubError: built-in devices did not show up within `devices_timeout`
        """
        self._watchdog = asyncio.create_task(self._watch_connection(), name="hub connection watchdog")
        await self.connection.start(self._on_frame)
        await self._wait_for_ports(self.REQUIRED_PORTS)

    async def _wait_for_ports(self, ports: Tuple[int, ...]) -> None:
        deadline = time.monotonic() + self.devices_timeout
        while missing := [port for port in ports if port not in self.peripherals]:
            remaining = deadline - time.monotonic()
            if self._closed:
                raise self._closed
            if remaining <= 0:
                raise HubError("Built-in devices did not show up on ports %s; attached: %s"
                               % (", ".join("0x%x" % port for port in missing), self.peripherals))
            self._attached.clear()
            try:
                await asyncio.wait_for(self._attached.wait(), remaining)
            except asyncio.TimeoutError:
                pass
        log.debug("All devices are present: %s", self.peripherals)

    async def close(self) -> None:
        self._shut(HubDisconnected("Hub connection closed"))
        await self.connection.disconnect()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *exc_info):
        await self.close()

    def add_message_handler(self, msg_class: Type[UpstreamMsg], handler: MessageHandler) -> None:
        """`handler` runs on the event loop as messages arrive, so it must not block"""
        self._handlers.append((msg_class, handler))

    async def send(self, msg: DownstreamMsg) -> None:
        """Send a command that gets no reply"""
        data = msg.bytes()
        assert not msg.needs_reply, "Use request() for %r" % msg
        await self._write(data)

    async def request(self, msg: DownstreamMsg) -> UpstreamMsg:
        """Send a command and return the hub's reply to it"""
        data = msg.bytes()
        assert msg.needs_reply and not isinstance(msg, MsgPortOutput), "Use send() or output() for %r" % msg
        item = self._requests.expect_reply(msg)
        return await self._exchange(item, data)

    async def output(self, msg: MsgPortOutput, wait_complete: bool = True) -> asyncio.Future:
        """
        Send a port output command; return once the port has started it, or with `wait_complete`, finished it.

        :return: future resolving when the command ends
        :raises CommandDiscarded: the port rejected the command, or another command took over the port
        """
        msg.do_feedback = True
        data = msg.bytes()
        item = self._requests.expect_output(msg)
        await self._exchange(item, data)
        if wait_complete:
            await item.done
        return item.done

    async def connect_ports(self, port_a: int, port_b: int) -> Peripheral:
        """
        Pair two motors into a virtual port that drives them in sync.
        Hubs without virtual port setup, like the Move Hub, raise `CommandFailed`.
        """
        reply = await self.request(MsgVirtualPortSetup(MsgVirtualPortSetup.CMD_CONNECT, (port_a, port_b)))
        return self.peripherals[reply.port]

    async def disconnect_ports(self, pair: Peripheral) -> None:
        """Split a virtual port back into its motors"""
        await self.request(MsgVirtualPortSetup(MsgVirtualPortSetup.CMD_DISCONNECT, pair.port))

    async def disconnect(self) -> None:
        await self.request(MsgHubAction(MsgHubAction.DISCONNECT))

    async def switch_off(self) -> None:
        await self.request(MsgHubAction(MsgHubAction.SWITCH_OFF))

    async def _exchange(self, item: Awaiting, data: bytes):
        try:
            await self._write(data)
            return await asyncio.wait_for(asyncio.shield(item.acked), self.request_timeout)
        except asyncio.TimeoutError:
            raise ReplyTimeout("No response to %r within %ss" % (item.msg, self.request_timeout)) from None
        finally:
            if not item.acked.done():  # timed out, cancelled or failed to write
                self._requests.forget(item)

    async def _write(self, data: bytes) -> None:
        if self._closed:
            raise self._closed
        try:
            await self.connection.write(data)
        except ConnectionError as exc:
            raise HubDisconnected("Write to hub failed: %s" % exc) from exc

    def _on_frame(self, frame: bytes) -> None:
        try:
            msgs = decode_upstream(frame)
        except Exception:  # no caller to raise to; the connection must survive a bad frame
            log.exception("Dropped undecodable frame: %s", frame.hex())
            return

        for msg in msgs:
            log.debug("Received: %r", msg)
            self._requests.on_message(msg)
            for msg_class, handler in self._handlers:
                if isinstance(msg, msg_class):
                    try:
                        handler(msg)
                    except Exception:
                        log.exception("Message handler %s failed on %r", handler, msg)

    def _on_attached_io(self, msg: MsgHubAttachedIO) -> None:
        if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
            detached = self.peripherals.pop(msg.port, None)
            log.info("Detached peripheral: %s", detached)
            if detached:
                detached.close_subscriptions()
            return

        dev_type_raw = ushort(msg.payload, 0)
        dev_type = DevTypes(dev_type_raw) if DevTypes.has_value(dev_type_raw) else DevTypes.UNKNOWN
        if dev_type not in PERIPHERAL_TYPES:
            log.warning("Have no dedicated class for peripheral type 0x%x (%s) on port 0x%x",
                        dev_type_raw, dev_type.name, msg.port)
        peripheral = PERIPHERAL_TYPES.get(dev_type, Peripheral)(self, msg.port)
        if msg.event == MsgHubAttachedIO.EVENT_ATTACHED_VIRTUAL:
            peripheral.virtual_ports = (usbyte(msg.payload, 2), usbyte(msg.payload, 3))
        self.peripherals[msg.port] = peripheral
        log.info("Attached peripheral %s => %s", dev_type.name, peripheral)
        self._attached.set()

    def _on_port_value(self, msg: UpstreamMsg) -> None:
        peripheral = self.peripherals.get(msg.port)
        if peripheral is None:
            log.warning("Value for port with no device: %r", msg)
            return
        peripheral.on_port_value(msg)

    def _on_hub_action(self, msg: MsgHubAction) -> None:
        if msg.action in (MsgHubAction.UPSTREAM_DISCONNECT, MsgHubAction.UPSTREAM_SHUTDOWN):
            log.warning("Hub %s", "disconnects" if msg.action == MsgHubAction.UPSTREAM_DISCONNECT else "switches off")
            self._shut(HubDisconnected("Hub ended the connection"))

    def _value_sources(self) -> List[Subscribable]:
        return list(self.peripherals.values())

    async def _watch_connection(self) -> None:
        await self.connection.disconnected.wait()
        self._shut(HubDisconnected("Connection to hub lost"))

    def _shut(self, exc: HubError) -> None:
        if self._closed:
            return
        self._closed = exc
        self._requests.fail_all(exc)
        for source in self._value_sources():
            source.close_subscriptions()
        if self._watchdog and self._watchdog is not asyncio.current_task():
            self._watchdog.cancel()


class MoveHubConstants:
    DEFAULT_NAME = "LEGO Move Hub"

    PORT_A = 0x00
    PORT_B = 0x01
    PORT_C = 0x02
    PORT_D = 0x03
    PORT_AB = 0x10
    PORT_LED = 0x32
    PORT_TILT_SENSOR = 0x3A
    PORT_CURRENT = 0x3B
    PORT_VOLTAGE = 0x3C

    REQUIRED_PORTS = (PORT_A, PORT_B, PORT_AB, PORT_LED, PORT_TILT_SENSOR, PORT_CURRENT, PORT_VOLTAGE)


class MoveHub(MoveHubConstants, Hub):
    """LEGO Boost Move Hub"""

    def __init__(self, connection: Connection, **kwargs):
        super().__init__(connection, **kwargs)
        self.button = Button(self)

    def _value_sources(self) -> List[Subscribable]:
        return super()._value_sources() + [self.button]

    async def start(self) -> None:
        await super().start()
        await self.report_status()

    async def report_status(self) -> None:
        name = await self.request(MsgHubProperties(MsgHubProperties.ADVERTISE_NAME, MsgHubProperties.UPD_REQUEST))
        mac = await self.request(MsgHubProperties(MsgHubProperties.PRIMARY_MAC, MsgHubProperties.UPD_REQUEST))
        log.info("%s on %s", name.payload, str2hex(mac.payload))
        voltage = await self.request(MsgHubProperties(MsgHubProperties.VOLTAGE_PERC, MsgHubProperties.UPD_REQUEST))
        log.info("Voltage: %s%%", usbyte(voltage.parameters, 0))
        alert = await self.request(MsgHubAlert(MsgHubAlert.LOW_VOLTAGE, MsgHubAlert.UPD_REQUEST))
        if not alert.is_ok():
            log.warning("Low voltage, check power source (maybe replace battery)")

    @property
    def motor_A(self) -> EncodedMotor:
        return self.peripherals[self.PORT_A]

    @property
    def motor_B(self) -> EncodedMotor:
        return self.peripherals[self.PORT_B]

    @property
    def motor_AB(self) -> EncodedMotor:
        return self.peripherals[self.PORT_AB]

    @property
    def led(self) -> LEDRGB:
        return self.peripherals[self.PORT_LED]

    @property
    def tilt_sensor(self) -> TiltSensor:
        return self.peripherals[self.PORT_TILT_SENSOR]

    @property
    def current(self) -> Current:
        return self.peripherals[self.PORT_CURRENT]

    @property
    def voltage(self) -> Voltage:
        return self.peripherals[self.PORT_VOLTAGE]

    @property
    def port_C(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_C)

    @property
    def port_D(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_D)

    @property
    def vision_sensor(self) -> Optional[VisionSensor]:
        return next((p for p in self._external() if type(p) is VisionSensor), None)

    @property
    def motor_external(self) -> Optional[EncodedMotor]:
        return next((p for p in self._external() if type(p) is EncodedMotor), None)

    def _external(self) -> List[Peripheral]:
        return [p for p in (self.port_C, self.port_D) if p is not None]


class SmartHubConstants:
    DEFAULT_NAME = "Smart Hub"

    PORT_A = 0x00
    PORT_B = 0x01
    PORT_LED = 0x32
    PORT_CURRENT = 0x3B
    PORT_VOLTAGE = 0x3C

    REQUIRED_PORTS = (PORT_LED, PORT_CURRENT, PORT_VOLTAGE)


class SmartHub(SmartHubConstants, Hub):
    """LEGO Powered Up Smart Hub, https://www.lego.com/en-pt/product/hub-88009"""

    def __init__(self, connection: Connection, **kwargs):
        super().__init__(connection, **kwargs)
        self.button = Button(self)

    def _value_sources(self) -> List[Subscribable]:
        return super()._value_sources() + [self.button]

    @property
    def led(self) -> LEDRGB:
        return self.peripherals[self.PORT_LED]

    @property
    def current(self) -> Current:
        return self.peripherals[self.PORT_CURRENT]

    @property
    def voltage(self) -> Voltage:
        return self.peripherals[self.PORT_VOLTAGE]

    @property
    def port_A(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_A)

    @property
    def port_B(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_B)


class RemoteHandsetConstants:
    DEFAULT_NAME = "Remote Handset"

    PORT_A = 0x00
    PORT_B = 0x01
    PORT_LED = 0x34
    PORT_VOLTAGE = 0x3B
    PORT_RSSI = 0x3C

    REQUIRED_PORTS = (PORT_A, PORT_B, PORT_LED, PORT_VOLTAGE, PORT_RSSI)


class RemoteHandset(RemoteHandsetConstants, Hub):
    """LEGO Powered Up remote handset"""

    @property
    def port_A(self) -> RemoteButton:
        return self.peripherals[self.PORT_A]

    @property
    def port_B(self) -> RemoteButton:
        return self.peripherals[self.PORT_B]

    @property
    def led(self) -> LEDRGB:
        return self.peripherals[self.PORT_LED]

    @property
    def voltage(self) -> Voltage:
        return self.peripherals[self.PORT_VOLTAGE]

    @property
    def port_RSSI(self) -> Peripheral:
        return self.peripherals[self.PORT_RSSI]
