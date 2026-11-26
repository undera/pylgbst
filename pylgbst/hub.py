"""
Blocking hubs: each wraps its `pylgbst.aio.hub` counterpart, running it on a shared event loop thread
"""
import logging
from typing import Callable, Dict, Optional, Type

from pylgbst import get_connection_auto
from pylgbst.aio import hub as aio
from pylgbst.aio.hub import MoveHubConstants, RemoteHandsetConstants, SmartHubConstants
from pylgbst.aio.loop_thread import shared_loop_thread
from pylgbst.comms import Connection, MOVE_HUB_HARDWARE_HANDLE, to_async
from pylgbst.messages import DownstreamMsg, MsgHubAttachedIO, MsgPortOutput, UpstreamMsg
from pylgbst.peripherals import (
    Button, Current, EncodedMotor, LEDRGB, Peripheral, RemoteButton, TiltSensor, VisionSensor, Voltage, wrap,
)

log = logging.getLogger("hub")


class Hub:
    """
    Connects and waits for the hub's built-in devices on creation.

    :param connection: what `get_connection_*()` return, or a custom blocking `Connection`;
        by default, `get_connection_auto()`
    :raises HubError: built-in devices did not show up
    """

    HUB_HARDWARE_HANDLE = MOVE_HUB_HARDWARE_HANDLE
    AIO_CLASS: Type[aio.Hub] = aio.Hub

    def __init__(self, connection: Optional[Connection] = None):
        self.loop_thread = shared_loop_thread()
        if connection is None:
            connection = self._default_connection()
        self.connection = connection
        self.peripherals: Dict[int, Peripheral] = {}
        self.aio: aio.Hub = self.loop_thread.run(self._create_aio(connection))
        try:
            self.loop_thread.run(self.aio.start())
        except BaseException:
            self.loop_thread.run(self.aio.close())
            raise

    def _default_connection(self) -> Connection:
        return get_connection_auto()

    async def _create_aio(self, connection: Connection) -> aio.Hub:
        """On the loop: async objects belong to the loop they are created on"""
        hub = self.AIO_CLASS(to_async(connection))
        hub.add_message_handler(MsgHubAttachedIO, self._on_attached_io)  # after the async hub's own handler
        return hub

    def _on_attached_io(self, msg: MsgHubAttachedIO) -> None:
        if msg.event == MsgHubAttachedIO.EVENT_DETACHED:
            self.peripherals.pop(msg.port, None)
        else:
            self.peripherals[msg.port] = wrap(self, self.aio.peripherals[msg.port])

    def add_message_handler(self, classname: Type[UpstreamMsg], callback: Callable[[UpstreamMsg], None]) -> None:
        """`callback` runs on the event loop thread: it must neither block nor call blocking hub methods"""
        self.aio.add_message_handler(classname, callback)

    def send(self, msg: DownstreamMsg) -> Optional[UpstreamMsg]:
        """
        Send a message; return the hub's reply if the message gets one.
        Port output commands return once the port completes them, or with `wait_complete=False`, starts them.
        """
        if isinstance(msg, MsgPortOutput):
            self.loop_thread.run(self.aio.output(msg, msg.wait_complete))
            return None
        msg.bytes()  # some messages decide on `needs_reply` while encoding
        if msg.needs_reply:
            return self.loop_thread.run(self.aio.request(msg))
        self.loop_thread.run(self.aio.send(msg))
        return None

    def disconnect(self) -> None:
        self.loop_thread.run(self.aio.disconnect())

    def switch_off(self) -> None:
        self.loop_thread.run(self.aio.switch_off())

    def _peripheral(self, port: Optional[int]) -> Optional[Peripheral]:
        return None if port is None else self.peripherals.get(port)


class MoveHub(MoveHubConstants, Hub):
    """LEGO Boost Move Hub"""

    AIO_CLASS = aio.MoveHub

    def __init__(self, connection: Optional[Connection] = None):
        super().__init__(connection)
        self.button = Button(self, self.aio.button)

    def _default_connection(self) -> Connection:
        return get_connection_auto(hub_name=self.DEFAULT_NAME)

    @property
    def motor_A(self) -> EncodedMotor:
        return self.peripherals.get(self.PORT_A)

    @property
    def motor_B(self) -> EncodedMotor:
        return self.peripherals.get(self.PORT_B)

    @property
    def motor_AB(self) -> EncodedMotor:
        return self.peripherals.get(self.PORT_AB)

    @property
    def led(self) -> LEDRGB:
        return self.peripherals.get(self.PORT_LED)

    @property
    def tilt_sensor(self) -> TiltSensor:
        return self.peripherals.get(self.PORT_TILT_SENSOR)

    @property
    def current(self) -> Current:
        return self.peripherals.get(self.PORT_CURRENT)

    @property
    def voltage(self) -> Voltage:
        return self.peripherals.get(self.PORT_VOLTAGE)

    @property
    def port_C(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_C)

    @property
    def port_D(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_D)

    @property
    def vision_sensor(self) -> Optional[VisionSensor]:
        sensor = self.aio.vision_sensor
        return self._peripheral(sensor.port if sensor else None)

    @property
    def motor_external(self) -> Optional[EncodedMotor]:
        motor = self.aio.motor_external
        return self._peripheral(motor.port if motor else None)


class SmartHub(SmartHubConstants, Hub):
    """LEGO Powered Up Smart Hub, https://www.lego.com/en-pt/product/hub-88009"""

    AIO_CLASS = aio.SmartHub

    def __init__(self, connection: Optional[Connection] = None):
        super().__init__(connection)
        self.button = Button(self, self.aio.button)

    def _default_connection(self) -> Connection:
        return get_connection_auto(hub_name=self.DEFAULT_NAME)

    @property
    def led(self) -> LEDRGB:
        return self.peripherals.get(self.PORT_LED)

    @property
    def current(self) -> Current:
        return self.peripherals.get(self.PORT_CURRENT)

    @property
    def voltage(self) -> Voltage:
        return self.peripherals.get(self.PORT_VOLTAGE)

    @property
    def port_A(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_A)

    @property
    def port_B(self) -> Optional[Peripheral]:
        return self.peripherals.get(self.PORT_B)


class RemoteHandset(RemoteHandsetConstants, Hub):
    """LEGO Powered Up remote handset"""

    AIO_CLASS = aio.RemoteHandset

    def __init__(self, connection: Optional[Connection] = None, address: Optional[str] = None):
        self._address = address
        super().__init__(connection)

    def _default_connection(self) -> Connection:
        return get_connection_auto(hub_mac=self._address, hub_name=self.DEFAULT_NAME)

    @property
    def port_A(self) -> RemoteButton:
        return self.peripherals.get(self.PORT_A)

    @property
    def port_B(self) -> RemoteButton:
        return self.peripherals.get(self.PORT_B)

    @property
    def led(self) -> LEDRGB:
        return self.peripherals.get(self.PORT_LED)

    @property
    def voltage(self) -> Voltage:
        return self.peripherals.get(self.PORT_VOLTAGE)

    @property
    def port_RSSI(self) -> Peripheral:
        return self.peripherals.get(self.PORT_RSSI)
