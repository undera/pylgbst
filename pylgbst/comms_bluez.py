
class BlueZInterface(gatt.Device, object):  # Pendant zu Klasse BlueGigaInterface
    def __init__(self, mac_address, manager, dman_thread):
        logging.debug('BlueZ: Interface Instanz erzeugen...')
        gatt.Device.__init__(self, mac_address=mac_address, manager=manager)
        self.conn_hnd_char = None
        self.dman_thread = dman_thread

    def start(self):
        log.debug("Start device")

    def client_conn(self, hub_mac):  # Client mit dem GATT-Server MoveHub (MAC-Adresse hub_mac) verbinden
        logging.debug("BlueZ: Trying to connect client to MoveHub with MAC %s.", hub_mac)
        self.connect()  # Kann unterschiedlich lang dauern, daher Warteschleife
        logging.debug('Warte auf services.resolved()...')
        # sleep(1)
        while self.conn_hnd_char == None:  # Erhält erst Wert, wenn richtige Characterisitc gefunden
            sleep(0.1)
            print('*', end='')
        print('')
        logging.debug('services.resolved() erfolgreich')

    def read(self, handle):  # Lesen Charakteristic über Handle (noch nicht implementiert!!)
        print('Achtung: BlueZ gatt read command (dummy!)')
        logging.debug("BlueZ: Reading from handle %s. Dummy!!!", handle)
        return b'\0x00\0x00'

    def write(self, handle, data):  # Schreiben an Charakteristic 0x0e
        logging.debug("BlueZ: Writing to handle 0x0e: %s", str2hex(data))
        return self.conn_hnd_char.write_value(data)

    def enable_notifications(self):  # Notifications aktivieren
        logging.debug('BlueZ: Enable Notifications...')
        # sleep(0.5)
        self.conn_hnd_char.enable_notifications()
        # sleep(1)

    def set_notific_handler(self, uuid, func_hnd):  # Callbackfunktion für Notifications festlegen
        logging.debug('BlueZ: set_notific_handler()')
        self.not_func = func_hnd

    def stop(self):  # Verbindung trennen
        logging.debug('Stopp DeviceManager anschließend BLE-Verbindung trennen')
        self.manager.stop()
        sleep(2)
        self.disconnect()

    def online(self):  # Kontrolle ob der Device Manager noch lebt und Verbindung stattgefunden hat
        logging.info('BlueZ.online()')
        if self.dman_thread:
            if self.conn_hnd_char != None:
                return self.dman_thread.isAlive()
                logging.info('BlueZ: BLE-Client online')
        else:
            return False
            logging.info('BlueZ: BLE-Client offline')

    # ------------------------------------------------------------------
    # Ab hier Event-Methoden der Elternklasse, die überschrieben werden
    def services_resolved(self):  # Wird automatisch bei connect() ausgeführt
        logging.debug('MoveHub Services und Characteristics ermitteln...')
        super().services_resolved()
        logging.debug("[%s] Resolved services", self.mac_address)
        for service in self.services:  # Suche nach 0x0e Charakteristic für MoveHub-Steuerung
            logging.debug("[%s]  Service [%s]", self.mac_address, service.uuid)
            for characteristic in service.characteristics:
                logging.debug("[%s]    Characteristic [%s]", self.mac_address, characteristic.uuid)
                if (service.uuid == MOVE_HUB_HW_UUID_SERV and
                        characteristic.uuid == MOVE_HUB_HW_UUID_CHAR):
                    logging.debug('MoveHub Charakteristik gefunden!')
                    self.conn_hnd_char = characteristic  # nicht besser bekannte Char. fest zuweisen?
        if self.conn_hnd_char == None:  # Programmabbruch, falls Characteristic 0x0e nicht gefunden
            print('BlueZ hat Characteristic für MoveHub Steuerung nicht gefunden! > Programmabbruch.')
            self.stop()
            sleep(1)
            sys.exit(0)

    # Callback Funktion für Notifications. Angabe des Handle nicht nötig,
    # da nur für eine Characteristic Notifications abonniert wurden
    def characteristic_value_updated(self, characteristic, value):
        logging.debug('Notification in GattDevice: %s', value.hex())
        self.not_func(handle=0x0e, data=value)  # Anders als beim BlueGiga generell nur Notifications von 0x0e

    def connect_succeeded(self):  # Nur zum Debuggen bei Problemen innerhalb gatt nötig.
        super().connect_succeeded()
        logging.debug('gatt.Device: Erfolgreich verbunden')

    def connect_failed(self, error):  # Nur zum Debuggen bei Problemen innerhalb gatt nötig.
        super().connect_failed(error)
        print("Verbindung fehlgeschlagen:", str(error))
        self.manager.stop()

    def disconnect_succeeded(self):  # Nur zum Debuggen bei Problemen innerhalb gatt nötig.
        super().disconnect_succeeded()
        logging.debug('gatt Bibliothek meldet Ende BLE-Verbindung.')
    # ------------------------------------------------------------------


class BlueZConnection(Connection):
    def connect(self, bt_iface_name='hci0', hub_mac=None):
        dev_manager = gatt.DeviceManager(adapter_name=bt_iface_name)
        dman_thread = threading.Thread(target=dev_manager.run)
        log.debug('Starting DeviceManager...')
        dman_thread.start()
        self.ble_iface = BlueZInterface(hub_mac, dev_manager, dman_thread)
        self.ble_iface.client_conn(hub_mac)

    def write(self, handle, data):
        pass

    def set_notify_handler(self, handler):
        pass

