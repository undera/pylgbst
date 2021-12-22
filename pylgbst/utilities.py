"""
This module offers some utilities, in a way they are work in both Python 2 and 3
"""

import binascii
import logging
import sys
from struct import unpack

log = logging.getLogger(__name__)

if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue as queue

queue = queue  # just to use it


def check_unpack(seq, index, pattern, size):
    """Check that we got size bytes, if so, unpack using pattern"""
    data = seq[index : index + size]
    assert len(data) == size, "Unexpected data len %d, expected %d" % (len(data), size)
    return unpack(pattern, data)[0]


def usbyte(seq, index):
    return check_unpack(seq, index, "<B", 1)


def ushort(seq, index):
    return check_unpack(seq, index, "<H", 2)


def usint(seq, index):
    return check_unpack(seq, index, "<I", 4)


def str2hex(data):  # we need it for python 2+3 compatibility
    # if sys.version_info[0] == 3:
    # data = bytes(data, 'ascii')
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data, "ascii")
    hexed = binascii.hexlify(data)
    return hexed
