# Generic Powered Up Hub

## Connecting to Hub via Bluetooth

## Accessing Peripherals

## Sending and Receiving Low-Level Messages
`Hub.send(msg)`
add_message_handler

## Use Disconnect in `finally`

It is recommended to make sure `disconnect()` method is called on connection object after you have finished your program. This ensures Bluetooth subsystem is cleared and avoids problems for subsequent re-connects of MoveHub. The best way to do that in Python is to use `try ... finally` clause:

```python
from pylgbst import get_connection_auto
from pylgbst.hub import Hub

conn = get_connection_auto()  # ! don't put this into `try` block
try:
    hub = Hub(conn)
finally:
    conn.disconnect()
```

Additionally, hub has `Hub.disconnect()` and `Hub.switch_off()` methods to call corresponding commands.