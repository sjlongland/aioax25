#!/usr/bin/env python3

from aioax25.frame import AX25Address, AX25Frame, AX25RawFrame, \
        AX25UnnumberedInformationFrame, AX25FrameRejectFrame, \
        AX25UnnumberedFrame
from nose.tools import eq_
from ..hex import from_hex, hex_cmp


def test_decode_incomplete():
    """
    Test that an incomplete frame does not cause a crash.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 e0'      # Destination
                    'ac 96 68 9a a6 98 61'      # Source
                )
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Insufficient packet data')

def test_decode_iframe():
    """
    Test that an I-frame gets decoded to a raw frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'      # Destination
                'ac 96 68 9a a6 98 61'      # Source
                '00'                        # Control byte
                '11 22 33 44 55 66 77'      # Payload
            )
    )
    assert isinstance(frame, AX25RawFrame), 'Did not decode to raw frame'
    hex_cmp(frame.payload, '00 11 22 33 44 55 66 77')

def test_decode_sframe():
    """
    Test that an S-frame gets decoded to a raw frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'      # Destination
                'ac 96 68 9a a6 98 61'      # Source
                '01'                        # Control byte
                '11 22 33 44 55 66 77'      # Payload
            )
    )
    assert isinstance(frame, AX25RawFrame), 'Did not decode to raw frame'
    hex_cmp(frame.payload, '01 11 22 33 44 55 66 77')

def test_decode_uframe():
    """
    Test that a U-frame gets decoded to an unnumbered frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'      # Destination
                'ac 96 68 9a a6 98 61'      # Source
                'c3'                        # Control byte
            )
    )
    assert isinstance(frame, AX25UnnumberedFrame), \
            'Did not decode to unnumbered frame'
    eq_(frame.modifier, 0xc3)
    hex_cmp(frame.frame_payload, '')

def test_decode_frmr():
    """
    Test that a FRMR gets decoded to a frame reject frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'      # Destination
                'ac 96 68 9a a6 98 61'      # Source
                '87 11 22 33'               # Control byte
            )
    )
    assert isinstance(frame, AX25FrameRejectFrame), \
            'Did not decode to FRMR frame'
    eq_(frame.modifier, 0x87)
    eq_(frame.w, True)
    eq_(frame.x, False)
    eq_(frame.y, False)
    eq_(frame.z, False)
    eq_(frame.vr, 1)
    eq_(frame.frmr_cr, False)
    eq_(frame.vs, 1)

def test_decode_ui():
    """
    Test that a UI gets decoded to an unnumbered information frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'      # Destination
                'ac 96 68 9a a6 98 61'      # Source
                '03 11 22 33'               # Control byte
            )
    )
    assert isinstance(frame, AX25UnnumberedInformationFrame), \
            'Did not decode to UI frame'
    eq_(frame.pid, 0x11)
    hex_cmp(frame.payload, '22 33')
