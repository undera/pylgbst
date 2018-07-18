import logging
import traceback

from pylgbst.comms import DebugServer

log = logging.getLogger('pylgbst')


def get_connection_bluegiga():
    from pylgbst.comms_pygatt import BlueGigaConnection

    return BlueGigaConnection().connect()


def get_connection_gattool(controller='hci0'):
    from pylgbst.comms_pygatt import GattoolConnection

    return GattoolConnection(controller).connect()


def get_connection_gatt(controller='hci0'):
    from pylgbst.comms_gatt import GattConnection

    return GattConnection(controller).connect()


def get_connection_gattlib(controller='hci0'):
    from pylgbst.comms_gattlib import GattLibConnection

    return GattLibConnection(controller).connect()


def get_connection_auto(controller='hci0', hub_mac=None):
    conn = None
    try:
        return get_connection_bluegiga()
    except BaseException:
        logging.debug("Failed: %s", traceback.format_exc())
        try:
            conn = get_connection_gatt(controller).connect(hub_mac)
        except BaseException:
            logging.debug("Failed: %s", traceback.format_exc())

            try:
                conn = get_connection_gattool(controller).connect(hub_mac)
            except BaseException:
                logging.debug("Failed: %s", traceback.format_exc())

                try:
                    conn = get_connection_gattlib(controller).connect(hub_mac)
                except BaseException:
                    logging.debug("Failed: %s", traceback.format_exc())

    if conn is None:
        raise Exception("Failed to autodetect connection, make sure you have installed prerequisites")

    return conn


def start_debug_server(iface="hci0", port=9090):
    server = DebugServer(get_connection_auto(iface))
    server.start(port)
