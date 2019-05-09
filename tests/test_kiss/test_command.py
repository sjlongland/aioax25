#!/usr/bin/env python3

"""
KISS command unit tests
"""

from aioax25.kiss import KISSCommand, KISSCmdReturn, KISSCmdData
from nose.tools import eq_

def test_stuff_bytes():
    """
    Test that bytes are correctly escaped.
    """
    eq_(
            bytes(KISSCommand._stuff_bytes(
                b'A test frame.\n'
                b'FEND becomes FESC TFEND: \xc0\n'
                b'while FESC becomes FESC TFESC: \xdb\n'
            )),
            # This should be decoded as the following:
            b'A test frame.\n'
            b'FEND becomes FESC TFEND: \xdb\xdc\n'
            b'while FESC becomes FESC TFESC: \xdb\xdd\n'
    )

def test_unstuff_bytes():
    """
    Test that bytes are correctly unescaped.
    """
    eq_(
            bytes(KISSCommand._unstuff_bytes(
                b'A test frame.\n'
                b'If we see FESC TFEND, we should get FEND: \xdb\xdc\n'
                b'while if we see FESC TFESC, we should get FESC: \xdb\xdd\n'
                b'FESC followed by any other byte should yield those\n'
                b'two original bytes: \xdb\xaa \xdb\xdb \xdb\xdb\xdd\n'
            )),
            # This should unstuff to the following
            b'A test frame.\n'
            b'If we see FESC TFEND, we should get FEND: \xc0\n'
            b'while if we see FESC TFESC, we should get FESC: \xdb\n'
            b'FESC followed by any other byte should yield those\n'
            b'two original bytes: \xdb\xaa \xdb\xdb \xdb\xdb\n'
    )

def test_decode_unknown():
    """
    Test unknown KISS frames are decoded to the base KISSCommand base class.
    """
    frame = KISSCommand.decode(
            b'\x58unknown command payload'
    )
    assert isinstance(frame, KISSCommand)
    eq_(frame.cmd, 8)
    eq_(frame.port, 5)
    eq_(frame.payload, b'unknown command payload')

def test_decode_data():
    """
    Test the DATA frame is decoded correctly.
    """
    frame = KISSCommand.decode(b'\x90this is a data frame')
    assert isinstance(frame, KISSCmdData)
    eq_(frame.payload, b'this is a data frame')

def test_encode_unknown():
    """
    Test we can encode an arbitrary frame.
    """
    eq_(bytes(KISSCommand(port=3, cmd=12, payload=b'testing')),
            b'\x3ctesting')

def test_encode_return():
    """
    Test we can encode a RETURN frame
    """
    eq_(bytes(KISSCmdReturn()), b'\xff')

def test_encode_data():
    """
    Test we can encode a DATA frame
    """
    eq_(bytes(KISSCmdData(port=2, payload=b'a frame')), b'\x20a frame')
