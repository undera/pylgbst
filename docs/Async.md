# Async API

`pylgbst.aio` is the asyncio core of the library; the blocking API (`pylgbst.hub`, `pylgbst.peripherals`) runs on top of it. The async API mirrors the blocking one: same hub and peripheral classes, same constants, with coroutine methods, and getters instead of properties (`await sensor.get_distance()` for `sensor.distance`).

```python
import asyncio

from pylgbst.aio.ble import connect
from pylgbst.aio.hub import MoveHub


async def main():
    async with MoveHub(await connect(hub_name=MoveHub.DEFAULT_NAME)) as hub:
        # commands may run concurrently, here both motors at once
        await asyncio.gather(hub.motor_A.angled(90), hub.motor_B.timed(0.5))

        async for distance, in hub.vision_sensor.values(mode=hub.vision_sensor.DISTANCE_INCHES):
            print(distance)
            if distance < 3:
                break  # leaving the loop switches the sensor updates off


asyncio.run(main())
```

- `connect()` uses the [relay](../README.md#keeping-the-hub-connected-between-runs) if it runs, Bluetooth otherwise.
- Starting the hub waits for its built-in devices, and raises `HubError` if they do not show up.
- Values arrive through `values()` iterators or through `subscribe(callback)`. Callbacks may be plain functions or coroutine functions; each subscriber gets its own task, so a slow one delays nobody else. Sensor subscribers that fall behind get the latest value only; button presses are all kept.
- A command waits `request_timeout` seconds (5 by default) for the hub to respond. Motor commands, once started, run as long as they take.
- Message handlers added with `add_message_handler()` run on the event loop, and must not block.

## Errors

Both APIs raise these, from `pylgbst.exceptions`:

- `HubDisconnected` (a `ConnectionError`): the hub is gone, lost or switched off. Every command waiting on it raises this, and so does every command after. Value iterations end with it.
- `ReplyTimeout` (a `TimeoutError`): no response from the hub in time.
- `CommandFailed` (a `RuntimeError`): the hub reported an error for the command.
- `CommandDiscarded` (a `CommandFailed`): a motor dropped the command, either rejecting it, or because another command took over the motor.
- `HubError`: base of the above; also raised when built-in devices do not show up, and when the relay holds a hub other than the requested one.
