#!/usr/bin/env python3

from aioax25.frame import AX25Frame, AX258BitInformationFrame, \
        AX2516BitInformationFrame

from nose.tools import eq_
from ..hex import from_hex, hex_cmp


def test_8bit_iframe_decode():
    """
    Test we can decode an 8-bit information frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'                      # Destination
                'ac 96 68 9a a6 98 e1'                      # Source
                'd4'                                        # Control
                'ff'                                        # PID
                '54 68 69 73 20 69 73 20 61 20 74 65 73 74' # Payload
            ),
            modulo128=False
    )

    assert isinstance(frame, AX258BitInformationFrame), \
            'Did not decode to 8-bit I-Frame'
    eq_(frame.nr, 6)
    eq_(frame.ns, 2)
    eq_(frame.pid, 0xff)
    eq_(frame.payload, b'This is a test')

def test_16bit_iframe_decode():
    """
    Test we can decode an 16-bit information frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'                     # Destination
                'ac 96 68 9a a6 98 e1'                     # Source
                '04 0d'                                    # Control
                'ff'                                       # PID
                '54 68 69 73 20 69 73 20 61 20 74 65 73 74'# Payload
            ),
            modulo128=True
    )

    assert isinstance(frame, AX2516BitInformationFrame), \
            'Did not decode to 16-bit I-Frame'
    eq_(frame.nr, 6)
    eq_(frame.ns, 2)
    eq_(frame.pid, 0xff)
    eq_(frame.payload, b'This is a test')

def test_iframe_str():
    """
    Test we can get the string representation of an information frame.
    """
    frame = AX258BitInformationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            nr=6,
            ns=2,
            pid=0xff,
            pf=True,
            payload=b'Testing 1 2 3'
    )

    eq_(str(frame), 'VK4MSL>VK4BWI: N(R)=6 P/F=True N(S)=2 PID=0xff '\
            'Payload=b\'Testing 1 2 3\'')

def test_iframe_copy():
    """
    Test we can get the string representation of an information frame.
    """
    frame = AX258BitInformationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            nr=6,
            ns=2,
            pid=0xff,
            pf=True,
            payload=b'Testing 1 2 3'
    )
    framecopy = frame.copy()

    assert framecopy is not frame
    hex_cmp(bytes(framecopy),
            'ac 96 68 84 ae 92 60'      # Destination
            'ac 96 68 9a a6 98 e1'      # Source
            'd4'                        # Control byte
            'ff'                        # PID
            '54 65 73 74 69 6e 67 20'
            '31 20 32 20 33'            # Payload
    )
