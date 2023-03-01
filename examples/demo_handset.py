import time

from pylgbst.hub import RemoteHandset

remote = RemoteHandset(address='5D319849-7D59-4EBB-A561-0C37C5EF8DCD')

def callback_from_button(button, button_set):
    print("value from callback: ", button, button_set)

# valid modes are 0 (default), 1, and 2. All result in the same behavior.
remote.port_A.subscribe(callback_from_button, mode=2)
remote.port_B.subscribe(callback_from_button)

print("Press buttons on the remote handset.")
time.sleep(30)

remote.port_A.unsubscribe(callback_from_button)
remote.port_A.unsubscribe(callback_from_button)
