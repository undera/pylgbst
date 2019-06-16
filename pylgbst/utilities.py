"""
This module offers some utilities, in a way they are work in both Python 2 and 3
"""

import binascii
import logging
import sys
from struct import unpack

if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue as queue

queue = queue  # just to use it


def usbyte(seq, index):
    return unpack("<B", seq[index:index + 1])[0]


def ushort(seq, index):
    return unpack("<H", seq[index:index + 2])[0]


def usint(seq, index):
    return unpack("<I", seq[index:index + 4])[0]


def str2hex(data):  # we need it for python 2+3 compatibility
    # if sys.version_info[0] == 3:
    # data = bytes(data, 'ascii')
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data, 'ascii')
    hexed = binascii.hexlify(data)
    return hexed
