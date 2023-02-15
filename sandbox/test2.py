import asyncio
from bleak import BleakScanner, BleakClient

import logging
logging.basicConfig(level=logging.DEBUG)


async def main():
    # Hub
    # device_1 = await BleakScanner.find_device_by_address('86996732-BF5A-433D-AACE-5611D4C6271D') # test
    # device_2 = await BleakScanner.find_device_by_address('F88800F6-F39B-4FD2-AFAA-DD93DA2945A6')  # train
    device_1 = await BleakScanner.find_device_by_address('2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')  # test handset
    print(device_1)
    print("name: ", device_1.name)
    print("address: ", device_1.address)
    print("details: ", device_1.details)
    print("metadata: ", device_1.metadata)
    # print(device_2)
    # print("name: ", device_2.name)
    # print("address: ", device_2.address)
    # print("details: ", device_2.details)
    # print("metadata: ", device_2.metadata)

    # Remote
    # device = await BleakScanner.find_device_by_address('2BC6E69B-5F56-4716-AD8C-7B4D5CBC7BF8')
    # print(device)
    # print("name: ", device.name)
    # print("address: ", device.address)
    # print("details: ", device.details)
    # print("metadata: ", device.metadata)

asyncio.run(main())


