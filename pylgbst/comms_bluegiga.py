

class BlueGigaInterface(pygatt.BGAPIBackend):  # Pendant zu Klasse BlueZInterface
    """
    Durch BlueGiga BLED112 Dongle bereitgestelltes externes BLE-Interface auf Linux-
    oder Windowsrechnern.
    """

    def __init__(self):  # Zusätzliches Attribut conn_hnd = Handle auf BLE-Verbindung
        pygatt.BGAPIBackend.__init__(self)
        self.conn_hnd = None  # Handle BLE-Verbindung = Rückgabeobjekt Funktion connect() anders als BlueZInterface!!

    def client_conn(self, hub_mac):  # Client mit dem GATT-Server MoveHub (MAC-Adresse hub_mac) verbinden
        logging.debug("BlueGiga: Trying to connect client to MoveHub with MAC %s.", hub_mac)
        self.conn_hnd = self.connect(hub_mac)

    def read(self, handle):  # Lesen Charakteristik über angegebenes Handle
        logging.debug("BlueGiga: Reading from handle %s.", handle)
        return self.conn_hnd.char_read_handle(handle)

    def write(self, handle, data):  # Schreiben Charakteristik über angegebenes Handle
        logging.debug("BlueGiga: Writing to handle %s: %s", handle, str2hex(data))
        return self.conn_hnd.char_write_handle(handle, data)

    def set_notific_handler(self, uuid, func_hnd):  # Callbackfunktion für Notifications festlegen
        logging.debug("BlueGiga: Set notification handler to callback function.")
        self.conn_hnd.subscribe(uuid, func_hnd)

    def enable_notifications(self):
        self.write(ENABLE_NOTIFICATIONS_HANDLE, ENABLE_NOTIFICATIONS_VALUE)

    def online(self):  # Kontrolle, ob Verbindungsprozess stattgefunden hat
        if self.conn_hnd == None:
            return False
        else:
            return True

    # Verbindung trennen direkt über Methode pygatt.BGAPIBackend.stop(), daher nicht implementiert hier
