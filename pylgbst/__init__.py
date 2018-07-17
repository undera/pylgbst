import sys

from pylgbst.movehub import MoveHub


def get_connection(self, backend='Auto', controller='hci0', hub_mac=''):
    if backend not in ['Auto', 'BlueZ', 'BlueGiga']:
        raise ValueError("Backend has to be one of Auto, BlueZ, BlueGiga")
    system = sys.platform
    print('Erkanntes Betriebssystem: ', system)
    if system.startswith('linux'):
        system = 'linux'
    if system in ['linux', 'win32']:
        detected_ifaces = find_usb_serial_devices(vendor_id=BLED112_VENDOR_ID, product_id=BLED112_PRODUCT_ID)
        if backend == 'Auto':
            if system == 'linux':
                if len(detected_ifaces) == 0:  # BlueGiga nicht gefunden, also verwende BlueZ
                    print('Kein BlueGiga-Dongle unter Linux gefunden, verwende BlueZ-Interface.')
                    controller = controller
                    conn_bluez(hub_mac, controller)
                else:  # BlueGiga gefunden und diesen verwenden
                    controller = detected_ifaces[0].port_name
                    print('BlueGiga-Dongle unter Linux gefunden unter: ', controller)
                    conn_bluegiga(hub_mac)
            else:  # Windows-Betriebssystem
                if len(detected_ifaces) == 0:
                    print('Kein BlueGiga-Dongle unter Windows gefunden > Programmabbruch')
                else:
                    controller = detected_ifaces[0].port_name
                    print('BlueGiga-Dongle unter Windows gefunden unter: ', controller)
                    conn_bluegiga(hub_mac)
        elif backend == 'BlueZ':
            controller = controller
            backend = backend
            conn_bluez(hub_mac, controller)
        elif backend == 'BlueGiga':
            controller = controller
            backend = backend
            conn_bluegiga(hub_mac)
    else:
        print('Platform not supported'.format(sys.platform))
