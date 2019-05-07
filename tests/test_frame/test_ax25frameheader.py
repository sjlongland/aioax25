#!/usr/bin/env python3

from aioax25.frame import AX25Address, AX25FrameHeader
from nose.tools import eq_


def test_decode_incomplete():
    """
    Test that an incomplete frame does not cause a crash.
    """
    try:
        AX25FrameHeader.decode(
                b'\xac\x96\x68\x84\xae\x92\xe0' # Destination
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Too few addresses')

def test_decode_no_digis():
    """
    Test we can decode an AX.25 frame without digipeaters.
    """
    (header, data) = AX25FrameHeader.decode(
            b'\xac\x96\x68\x84\xae\x92\xe0' # Destination
            b'\xac\x96\x68\x9a\xa6\x98\x61' # Source
            b'frame data goes here'         # Frame data
    )
    eq_(header.destination, AX25Address('VK4BWI', ch=True))
    eq_(header.source, AX25Address('VK4MSL', extension=True))
    eq_(len(header.repeaters), 0)
    eq_(data, b'frame data goes here')

def test_decode_with_1digi():
    """
    Test we can decode an AX.25 frame with one digipeater.
    """
    (header, data) = AX25FrameHeader.decode(
            b'\xac\x96\x68\x84\xae\x92\xe0' # Destination
            b'\xac\x96\x68\x9a\xa6\x98\x60' # Source
            b'\xac\x96\x68\xa4\xb4\x84\x61' # Digi
            b'frame data goes here'         # Frame data
    )
    eq_(header.destination, AX25Address('VK4BWI', ch=True))
    eq_(header.source, AX25Address('VK4MSL'))
    eq_(header.repeaters[0], AX25Address('VK4RZB', extension=True))
    eq_(data, b'frame data goes here')

def test_decode_with_2digis():
    """
    Test we can decode an AX.25 frame with two digipeaters.
    """
    (header, data) = AX25FrameHeader.decode(
            b'\xac\x96\x68\x84\xae\x92\xe0' # Destination
            b'\xac\x96\x68\x9a\xa6\x98\x60' # Source
            b'\xac\x96\x68\xa4\xb4\x84\x60' # Digi
            b'\xac\x96\x68\xa4\xb4\x82\x61' # Digi
            b'frame data goes here'         # Frame data
    )
    eq_(header.destination, AX25Address('VK4BWI', ch=True))
    eq_(header.source, AX25Address('VK4MSL'))
    eq_(len(header.repeaters), 2)
    eq_(header.repeaters[0], AX25Address('VK4RZB'))
    eq_(header.repeaters[1], AX25Address('VK4RZA', extension=True))
    eq_(data, b'frame data goes here')
