import asyncio

from bleak import BleakClient

hubUUID = "86996732-BF5A-433D-AACE-5611D4C6271D'"
rcUUID = "2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8'"

notify_uuid = "0000{0:x}-0000-1000-8000-00805f9b34fb".format(0xFFE1)


def callback(characteristic, data):
    print(characteristic, data)


async def connect_to_device(address):
    print("starting", address, "loop")
    async with BleakClient(address, timeout=5.0) as client:

        print("connect to", address)
        try:
            await client.start_notify(notify_uuid, callback)
            await asyncio.sleep(10.0)
            await client.stop_notify(notify_uuid)
        except Exception as e:
            print(e)

    print("disconnect from", address)


async def main(addresses):
    await asyncio.gather(*(connect_to_device(address) for address in addresses))


if __name__ == "__main__":
    asyncio.run(
        main(
            [
                # hubUUID,
                rcUUID,
            ]
        )
    )