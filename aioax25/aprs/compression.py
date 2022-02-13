#!/usr/bin/env python3

"""
APRS compression algorithm.
"""

BYTE_VALUE_OFFSET = 33
BYTE_VALUE_RADIX = 91


def compress(value, length):
    # Initialise our byte values
    bvalue = [0] * length

    # Figure out the bytes
    for pos in range(length):
        (div, rem) = divmod(
                value,
                BYTE_VALUE_RADIX ** (length - pos - 1)
        )
        bvalue[pos] += int(div)
        value = rem

    # Encode them into ASCII
    return ''.join([chr(b + BYTE_VALUE_OFFSET) for b in bvalue])


def decompress(value):
    length = len(value)
    return sum([
            (
                (b - BYTE_VALUE_OFFSET)
                * (BYTE_VALUE_RADIX ** (length - i - 1))
            )
            for (i, b) in enumerate(bytes(value, "us-ascii"))
    ])
