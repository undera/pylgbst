import time

from pylgbst.hub import RemoteHandset

remote = RemoteHandset()

def callback_from_button(button, button_set):
    print("value from callback: ", button, button_set)

remote.port_A.subscribe(callback_from_button, mode=2)
remote.port_B.subscribe(callback_from_button)
time.sleep(60)
remote.port_A.unsubscribe(callback_from_button)
remote.port_A.unsubscribe(callback_from_button)
