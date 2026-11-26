import logging
import traceback

from pylgbst.comms import Connection
from pylgbst.comms.crelay import RelayConnection

log = logging.getLogger('pylgbst')


def get_connection_bluegiga(controller=None, hub_mac=None, hub_name=None):
    del controller  # to prevent code analysis warning
    from pylgbst.comms.cpygatt import BlueGigaConnection

    return BlueGigaConnection().connect(hub_mac, hub_name)


def get_connection_gattool(controller='hci0', hub_mac=None, hub_name=None):
    from pylgbst.comms.cpygatt import GattoolConnection

    return GattoolConnection(controller).connect(hub_mac, hub_name)


def get_connection_gatt(controller='hci0', hub_mac=None, hub_name=None):
    from pylgbst.comms.cgatt import GattConnection

    return GattConnection(controller).connect(hub_mac, hub_name)


def get_connection_gattlib(controller='hci0', hub_mac=None, hub_name=None):
    from pylgbst.comms.cgattlib import GattLibConnection

    return GattLibConnection(controller).connect(hub_mac, hub_name)


def get_connection_bluepy(controller='hci0', hub_mac=None, hub_name=None):
    from pylgbst.comms.cbluepy import BluepyConnection

    return BluepyConnection(controller).connect(hub_mac, hub_name)


def get_connection_bleak(controller='hci0', hub_mac=None, hub_name=None):
    """
    Return connection based with Bleak API as an endpoint.

    :param controller: Not used, kept for compatibility with others.
    :param hub_mac: Optional Lego HUB MAC to connect to.
    :return: Driver object.
    """
    del controller  # to prevent code analysis warning
    from pylgbst.comms.cbleak import BleakDriver

    return BleakDriver(hub_mac, hub_name)


def get_connection_relay(controller=None, hub_mac=None, hub_name=None):
    """
    Connect through a running `python3 -m pylgbst.aio.relay`, which holds the hub between script runs.
    The relay serves the single hub it holds, so the arguments are ignored.
    """
    del controller, hub_mac, hub_name
    return RelayConnection()


def get_connection_auto(controller='hci0', hub_mac=None, hub_name=None) -> Connection:
    fns = [
        get_connection_relay,
        get_connection_bleak,
        get_connection_bluepy,
        get_connection_bluegiga,
        get_connection_gatt,
        get_connection_gattool,
        get_connection_gattlib,
    ]

    for fn in fns:
        try:
            log.info("Trying %s", fn.__name__)
            conn = fn(controller, hub_mac, hub_name)
        except KeyboardInterrupt:
            raise
        except BaseException:
            log.debug("Failed: %s", traceback.format_exc())
        else:
            log.info("Succeeded with %s", conn.__class__.__name__)
            return conn

    raise Exception("Failed to autodetect connection, make sure you have installed prerequisites")
