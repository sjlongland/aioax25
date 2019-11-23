#!/usr/bin/env python3

"""
Unsigned Integer encoding and decoding routines.

Both endians of integer are used, and sometimes the fields are odd sizes like
the 24-bit fields in XID HDLC Optional Function fields.  This allows encoding
or decoding of any integer, of any length, in either endianness.
"""


def encode(value, length=None, big_endian=False):
    """
    Encode the given unsigned integer value as bytes, optionally of a given
    length.
    """

    output = bytearray()
    while (value != 0) if (length is None) else (length > 0):
        output += bytes([value & 0xff])
        value >>= 8
        if length is not None:
            length -= 1

    if not output:
        # No output, so return a null byte
        output += b'\x00'

    if big_endian:
        output.reverse()

    return bytes(output)


def decode(value, big_endian=False):
    """
    Decode the given bytes as an unsigned integer.
    """

    output = 0
    for byte in (value if big_endian else reversed(value)):
        output <<= 8
        output |= byte
    return output
