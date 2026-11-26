# Python library to interact with Move Hub / PoweredUp Hubs

_Move Hub is central controller block of [LEGO® Boost Robotics Set](https://www.lego.com/themes/boost)._

In fact, Move Hub is just a Bluetooth hardware piece, and all manipulations with it are made by commands passed through Bluetooth Low Energy (BLE) wireless protocol. One of the ways to issue these commands is to write Python program using this library.

The best way to start is to look into [`demo.py`](examples/demo.py) file, and run it (assuming you have installed library).

If you have Vernie assembled, you might run scripts from [`examples/vernie`](examples/vernie) directory.

## Demonstrational Videos

[![Vernie Programmed](http://img.youtube.com/vi/oqsmgZlVE8I/0.jpg)](http://www.youtube.com/watch?v=oqsmgZlVE8I)
[![Laser Engraver](http://img.youtube.com/vi/ZbKmqVBBMhM/0.jpg)](https://youtu.be/ZbKmqVBBMhM)
[![Color Sorter](http://img.youtube.com/vi/829RKT8v8M0/0.jpg)](https://youtu.be/829RKT8v8M0)
[![Face Tracker](http://img.youtube.com/vi/WUOa3j-6XfI/0.jpg)](https://youtu.be/WUOa3j-6XfI)
[![Color Pin Bot](http://img.youtube.com/vi/QY6nRYXQw_U/0.jpg)](https://youtu.be/QY6nRYXQw_U)
[![BB-8 Joystick](http://img.youtube.com/vi/55kE9I4IQSU/0.jpg)](https://youtu.be/55kE9I4IQSU)

[Dancing Vernie](https://youtu.be/Cp2gDleP8_M)


## Features

- auto-detect and connect to [Move Hub](docs/MoveHub.md) device
- auto-detects [peripheral devices](docs/Peripherals.md) connected to Hub
- constant, angled and timed movement for [motors](docs/Motor.md), rotation sensor subscription
- [vision sensor](docs/VisionSensor.md): several modes to measure distance, color and luminosity
- [tilt sensor](docs/TiltSensor.md) subscription: 2 axis, 3 axis, bump detect modes
- [RGB LED](docs/LED.md) color change
- [Headlight](docs/Headlight.md) brightness change
- [push button](docs/MoveHub.md#push-button) status subscription
- [battery voltage and current](docs/VoltageCurrent.md) subscription available
- [relay](#keeping-the-hub-connected-between-runs) that holds the hub connection between script runs


## Usage

_Please note that this library requires one of Bluetooth backend libraries to be installed, please read section [here](#bluetooth-backend-prerequisites) for details._

Install library like this: 
```bash
pip install -U pylgbst
```

Then instantiate MoveHub object and start invoking its methods. Following is example to just print peripherals detected on Hub:  

```python
from pylgbst.hub import MoveHub

hub = MoveHub()

for device in hub.peripherals:
    print(device)
```

Each peripheral kind has own methods to do actions and/or get sensor data. See [features](#features) list for individual doc pages.

## Bluetooth Backend Prerequisites

The library talks Bluetooth through [bleak](https://github.com/hbldh/bleak), which supports Linux, Windows and macOS, and gets installed along with `pip install -U pylgbst`. Other backends (`gatt`, `gattlib`, `pygatt`/BlueGiga, `bluepy`) were removed, since Bleak covers their platforms.

_Please let author know if you have discovered any compatibility/preprequisite details, so we will update this section to help future users_

### Bluetooth Connection Options
There is an optional parameter for `MoveHub` class constructor, accepting instance of `Connection` object. By default, it will try to use whatever `get_connection_auto()` returns. You have several options to manually control that:

- use `get_connection_auto()` - use the [relay](#keeping-the-hub-connected-between-runs) if it is running, Bleak otherwise
- use `get_connection_bleak()` - connect over Bluetooth with Bleak
- use `get_connection_relay()` - connect through a running relay

All the functions above have optional arguments to specify Hub name or mac address. Please take a look at functions source code for details. Pass the connection object to `MoveHub` constructor, like this:
```python
from pylgbst.hub import MoveHub
from pylgbst import get_connection_bleak

conn = get_connection_bleak(hub_mac='AA:BB:CC:DD:EE:FF')
hub = MoveHub(conn)
```

## Keeping the Hub Connected Between Runs

When you run many short experiments, powering the hub up and waiting for it to connect each time gets tedious. Start a relay once; it connects to the hub over Bluetooth (via `bleak`) and holds the connection while your scripts come and go:

```bash
python3 -m pylgbst.aio.relay --name "LEGO Move Hub"   # or --mac AA:BB:CC:DD:EE:FF, or nothing for any LEGO hub
```

Scripts need no changes: `get_connection_auto()`, and thus `MoveHub()` with no arguments, use the relay at `127.0.0.1:9090` when one is running, and fall back to Bluetooth otherwise. To skip the relay, pass an explicit connection, e.g. `MoveHub(get_connection_bleak(hub_name=...))`.

The relay serves one script at a time; starting another one disconnects the previous. It replays the hub's peripheral announcements to every new script, and when a script exits, it stops the motors and switches off the sensor and button subscriptions that script left on. If the hub disconnects, the relay rescans for it.

## Roadmap & TODO

- validate operations with other Hub types (train, PUP etc)
- make connections to detect hub by UUID instead of name
- document all API methods

## Links

- https://github.com/LEGO/lego-ble-wireless-protocol-docs - true docs for LEGO BLE protocol
- https://github.com/JorgePe/BOOSTreveng - initial source of protocol knowledge
- https://github.com/nathankellenicki/node-poweredup - JavaScript version of library
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with another approach to bluetooth libs
- https://github.com/virantha/bricknil - for the lovers of async Python, alternative implementation of library to control PoweredUp Hubs
- https://virantha.github.io/bricknil/lego_api/lego.html - good infor about modes by BrickNil