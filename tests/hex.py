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

def hex_cmp(bytestr1, bytestr2):
    if not isinstance(bytestr1, bytes):
        bytestr1 = from_hex(bytestr1)

    if not isinstance(bytestr2, bytes):
        bytestr2 = from_hex(bytestr2)

    assert bytestr1 == bytestr2, \
            'Byte strings do not match:\n'\
            '  1> %s\n'\
            '  2> %s\n'\
            '1^2> %s' % (to_hex(bytestr1),
                    to_hex(bytestr2),
                    ' '.join([
                        (('%02x' % (a ^ b))
                            if a != b
                            else '  ')
                        for (a, b)
                        in zip(bytestr1, bytestr2)
                    ]))
