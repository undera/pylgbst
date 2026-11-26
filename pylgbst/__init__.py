from pylgbst.aio.ble import BleakConnection, connect
from pylgbst.aio.connection import RelayConnection
from pylgbst.aio.loop_thread import shared_loop_thread
from pylgbst.comms import AsyncBackedConnection


def _held(connecting) -> AsyncBackedConnection:
    loop_thread = shared_loop_thread()
    return AsyncBackedConnection(loop_thread, loop_thread.run(connecting))


def get_connection_bleak(controller=None, hub_mac=None, hub_name=None) -> AsyncBackedConnection:
    """
    Scan for the hub and connect over Bluetooth.

    :param controller: not used, kept for compatibility
    :param hub_mac: match by address; takes precedence over `hub_name`
    :param hub_name: match by advertised name; with neither given, any LEGO hub matches
    """
    del controller
    return _held(BleakConnection.connect(hub_mac, hub_name))


def get_connection_relay(controller=None, hub_mac=None, hub_name=None) -> AsyncBackedConnection:
    """
    Connect through a running `python3 -m pylgbst.aio.relay`, which holds the hub between script runs.

    :raises HubError: the relay holds a hub other than the one `hub_mac`/`hub_name` asks for
    """
    del controller
    return _held(RelayConnection.connect(hub_mac=hub_mac, hub_name=hub_name))


def get_connection_auto(controller=None, hub_mac=None, hub_name=None) -> AsyncBackedConnection:
    """Connect through the relay if it runs, otherwise over Bluetooth"""
    del controller
    return _held(connect(hub_mac, hub_name))
