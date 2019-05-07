#!/usr/bin/env python3

"""
Human-readable hex strings.
"""

from binascii import a2b_hex

def from_hex(hexstr):
    return a2b_hex(hexstr.replace(' ',''))

def to_hex(bytestr):
    return ' '.join([
        '%02x' % byte
        for byte in bytestr
    ])
