import logging
import traceback

from pylgbst.comms import DebugServer

log = logging.getLogger('pylgbst')


def get_connection_bluegiga(controller=None, hub_mac=None):
    del controller  # to prevent code analysis warning
    from pylgbst.comms.cpygatt import BlueGigaConnection

    return BlueGigaConnection().connect(hub_mac)


def get_connection_gattool(controller='hci0', hub_mac=None):
    from pylgbst.comms.cpygatt import GattoolConnection

    return GattoolConnection(controller).connect(hub_mac)


def get_connection_gatt(controller='hci0', hub_mac=None):
    from pylgbst.comms.cgatt import GattConnection

    return GattConnection(controller).connect(hub_mac)


def get_connection_gattlib(controller='hci0', hub_mac=None):
    from pylgbst.comms.cgattlib import GattLibConnection

    return GattLibConnection(controller).connect(hub_mac)


def get_connection_bluepy(controller='hci0', hub_mac=None):
    from pylgbst.comms.cbluepy import BluepyConnection

    return BluepyConnection(controller).connect(hub_mac)


def get_connection_auto(controller='hci0', hub_mac=None):
    fns = [
        get_connection_bluepy,
        get_connection_bluegiga,
        get_connection_gatt,
        get_connection_gattool,
        get_connection_gattlib,
    ]

    conn = None
    for fn in fns:
        try:
            logging.info("Trying %s", fn.__name__)
            return fn(controller, hub_mac)
        except KeyboardInterrupt:
            raise
        except BaseException:
            logging.debug("Failed: %s", traceback.format_exc())

    if conn is None:
        raise Exception("Failed to autodetect connection, make sure you have installed prerequisites")

    logging.info("Succeeded with %s", conn.__class__.__name__)
    return conn


def start_debug_server(iface="hci0", port=9090):
    server = DebugServer(get_connection_auto(iface))
    try:
        server.start(port)
    finally:
        server.connection.disconnect()

    # testing coverage
    def test_motor(self):
        hub = HubMock()
        motor = EncodedMotor(hub, MoveHub.PORT_D)
        hub.peripherals[MoveHub.PORT_D] = motor

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_power(1.0)
        self.assertEqual(b"07008103110164", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_acc_profile(1.0)
        self.assertEqual(b"090081031105e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_dec_profile(1.0)
        self.assertEqual(b"090081031106e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_speed(1.0)
        self.assertEqual(b"090081031107646403", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        logging.debug("\n\n")
        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.timed(1.0)
        self.assertEqual(b"0c0081031109e80364647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.angled(180)
        self.assertEqual(b"0e008103110bb400000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.2)
        motor.preset_encoder(-180)
        self.assertEqual(b"0b0081031151024cffffff", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.goto_position(0)
        self.assertEqual(b"0e008103110d0000000064647f03", hub.writes.pop(1)[1])

        hub.connection.wait_notifications_handled()

        hub = HubMock()
        motor = EncodedMotor(hub, MoveHub.PORT_D)
        hub.peripherals[MoveHub.PORT_D] = motor

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_power(1.0)
        self.assertEqual(b"07008103110164", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_acc_profile(1.0)
        self.assertEqual(b"090081031105e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.set_dec_profile(1.0)
        self.assertEqual(b"090081031106e80300", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.start_speed(1.0)
        self.assertEqual(b"090081031107646403", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.1)
        motor.stop()
        self.assertEqual(b"0c0081031109000064647f03", hub.writes.pop(1)[1])

        logging.debug("\n\n")
        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.timed(1.0)
        self.assertEqual(b"0c0081031109e80364647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.angled(180)
        self.assertEqual(b"0e008103110bb400000064647f03", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('050082030a', 0.2)
        motor.preset_encoder(-180)
        self.assertEqual(b"0b0081031151024cffffff", hub.writes.pop(1)[1])

        hub.connection.notification_delayed('0500820301', 0.1)
        hub.connection.notification_delayed('050082030a', 0.2)
        motor.goto_position(0)
        self.assertEqual(b"0e008103110d0000000064647f03", hub.writes.pop(1)[1])

        hub.connection.wait_notifications_handled()
