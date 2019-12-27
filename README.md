# Python library to interact with Move Hub

_Move Hub is central controller block of [LEGO® Boost Robotics Set](https://www.lego.com/themes/boost)._

In fact, Move Hub is just Bluetooth hardware, all manipulations are done with commands passed through Bluetooth Low Energy (BLE) wireless protocol. One of ways to issue these commands is to write Python program using this library.

Best way to start is to look into [`demo.py`](examples/demo.py) file, and run it (assuming you have installed library).

If you have Vernie assembled, you might run scripts from [`examples/vernie`](examples/vernie) directory.

## Demonstrational Videos

[![Vernie Programmed](http://img.youtube.com/vi/oqsmgZlVE8I/0.jpg)](http://www.youtube.com/watch?v=oqsmgZlVE8I)
[![Laser Engraver](http://img.youtube.com/vi/ZbKmqVBBMhM/0.jpg)](https://youtu.be/ZbKmqVBBMhM)
[![Color Sorter](http://img.youtube.com/vi/829RKT8v8M0/0.jpg)](https://youtu.be/829RKT8v8M0)
[![Face Tracker](http://img.youtube.com/vi/WUOa3j-6XfI/0.jpg)](https://youtu.be/WUOa3j-6XfI)
[![Color Pin Bot](http://img.youtube.com/vi/QY6nRYXQw_U/0.jpg)](https://youtu.be/QY6nRYXQw_U)
[![BB-8 Joystick](http://img.youtube.com/vi/55kE9I4IQSU/0.jpg)](https://youtu.be/55kE9I4IQSU)


## Features

- auto-detect and connect to [Move Hub](docs/MoveHub.md) device
- auto-detects [peripheral devices](docs/Peripherals.md) connected to Hub
- constant, angled and timed movement for [motors](docs/Motor.md), rotation sensor subscription
- [vision sensor](docs/VisionSensor.md): several modes to measure distance, color and luminosity
- [tilt sensor](docs/TiltSensor.md) subscription: 2 axis, 3 axis, bump detect modes
- [RGB LED](docs/LED.md) color change
- [push button](docs/MoveHub.md#push-button) status subscription
- [battery voltage and current](docs/VoltageCurrent.md) subscription available
- permanent Bluetooth connection server for faster debugging


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

You have following options to install as Bluetooth backend:

- `pip install pygatt` - [pygatt](https://github.com/peplin/pygatt) lib, works on both Windows and Linux  
- `pip install gatt` - [gatt](https://github.com/getsenic/gatt-python) lib, supports Linux, does not work on Windows
- `pip install gattlib` - [gattlib](https://bitbucket.org/OscarAcena/pygattlib) - supports Linux, does not work on Windows, requires `sudo`
- `pip install bluepy` - [bluepy](https://github.com/IanHarvey/bluepy) lib, supports Linux, including Raspbian, which allows connection to the hub from the Raspberry PI

Running on Windows requires [Bluegiga BLED112 Bluetooth Smart Dongle](https://www.silabs.com/products/wireless/bluetooth/bluetooth-low-energy-modules/bled112-bluetooth-smart-dongle) hardware piece, because no other hardware currently works on Windows with Python+BLE.

_Please let author know if you have discovered any compatibility/preprequisite details, so we will update this section to help future users_

Depending on backend type, you might need Linux `sudo` to be used when running Python.

### Bluetooth Connection Options
There is optional parameter for `MoveHub` class constructor, accepting instance of `Connection` object. By default, it will try to use whatever `get_connection_auto()` returns. You have several options to manually control that:

- use `pylgbst.get_connection_auto()` to attempt backend auto-choice, autodetect uses 
- use `BlueGigaConnection()` - if you use BlueGiga Adapter (`pygatt` library prerequisite)
- use `GattConnection()` - if you use Gatt Backend on Linux (`gatt` library prerequisite)
- use `GattoolConnection()` - if you use GattTool Backend on Linux (`pygatt` library prerequisite)
- use `GattLibConnection()` - if you use GattLib Backend on Linux (`gattlib` library prerequisite)
- use `BluepyConnection()` - if you use Bluepy backend on Linux/Raspbian (`bluepy` library prerequisite)
- pass instance of `DebugServerConnection` if you are using [Debug Server](#debug-server) (more details below).

All the functions above have optional arguments to specify adapter name and MoveHub mac address. Please look function source code for details.

If you want to specify name for Bluetooth interface to use on local computer, you can pass that to class or function of getting a connection. Then pass connection object to `MoveHub` constructor. Like this:
```python
from pylgbst.hub import MoveHub
from pylgbst.comms.cgatt import GattConnection

conn = GattConnection("hci1")
conn.connect()  # you can pass Hub mac address as parameter here, like 'AA:BB:CC:DD:EE:FF'

hub = MoveHub(conn)
```


## Debug Server
Running debug server opens permanent BLE connection to Hub and listening on TCP port for communications. This avoids the need to re-start Hub all the time. 

There is `DebugServerConnection` class that you can use with it, instead of `BLEConnection`. 

Starting debug server is done like this (you may need to run it with `sudo`, depending on your BLE backend):
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); \
                import pylgbst; pylgbst.start_debug_server()"
```

Then push green button on MoveHub, so permanent BLE connection will be established.

## Roadmap & TODO

- validate operations with other Hub types (train, PUP etc)
- make connections to detect hub by UUID instead of name
- document all API methods
- make debug server to re-establish BLE connection on loss

## Links

- https://github.com/LEGO/lego-ble-wireless-protocol-docs - true docs for LEGO BLE protocol
- https://github.com/JorgePe/BOOSTreveng - initial source of protocol knowledge
- https://github.com/nathankellenicki/node-poweredup - JavaScript version of library
- https://github.com/spezifisch/sphero-python/blob/master/BB8joyDrive.py - example with another approach to bluetooth libs

