#!/usr/bin/env python3

from aioax25.frame import AX25Frame, \
        AX258BitReceiveReadyFrame, \
        AX2516BitReceiveReadyFrame, AX258BitRejectFrame, \
        AX2516BitRejectFrame

from nose.tools import eq_
from ..hex import from_hex, hex_cmp


def test_sframe_payload_reject():
    """
    Test payloads are forbidden for S-frames
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 60'                  # Destination
                    'ac 96 68 9a a6 98 e1'                  # Source
                    '41'                                    # Control
                    '31 32 33 34 35'                        # Payload
                ),
                modulo128=False
        )
        assert False, 'Should not have worked'
    except ValueError as e:
        eq_(str(e), 'Supervisory frames do not support payloads.')

def test_16bs_truncated_reject():
    """
    Test that 16-bit S-frames with truncated control fields are rejected.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 60'                  # Destination
                    'ac 96 68 9a a6 98 e1'                  # Source
                    '01'                                    # Control (LSB only)
                ),
                modulo128=True
        )
        assert False, 'Should not have worked'
    except ValueError as e:
        eq_(str(e), 'Insufficient packet data')

def test_8bs_rr_frame():
    """
    Test we can generate a 8-bit RR supervisory frame
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'                      # Destination
                'ac 96 68 9a a6 98 e1'                      # Source
                '41'                                        # Control
            ),
            modulo128=False
    )
    assert isinstance(frame, AX258BitReceiveReadyFrame)
    eq_(frame.nr, 2)

def test_16bs_rr_frame():
    """
    Test we can generate a 16-bit RR supervisory frame
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'                      # Destination
                'ac 96 68 9a a6 98 e1'                      # Source
                '01 5c'                                     # Control
            ),
            modulo128=True
    )
    assert isinstance(frame, AX2516BitReceiveReadyFrame)
    eq_(frame.nr, 46)

def test_16bs_rr_encode():
    """
    Test we can encode a 16-bit RR supervisory frame
    """
    frame = AX2516BitReceiveReadyFrame(
            destination='VK4BWI',
            source='VK4MSL',
            nr=46, pf=True
    )
    hex_cmp(bytes(frame),
            'ac 96 68 84 ae 92 60'                      # Destination
            'ac 96 68 9a a6 98 e1'                      # Source
            '01 5d'                                     # Control
    )
    eq_(frame.control, 0x5d01)

def test_8bs_rej_decode_frame():
    """
    Test we can decode a 8-bit REJ supervisory frame
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'      # Destination
                'ac 96 68 9a a6 98 e1'      # Source
                '09'                        # Control byte
            ),
            modulo128=False
    )
    assert isinstance(frame, AX258BitRejectFrame), \
            'Did not decode to REJ frame'
    eq_(frame.nr, 0)
    eq_(frame.pf, False)

def test_16bs_rej_decode_frame():
    """
    Test we can decode a 16-bit REJ supervisory frame
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 60'      # Destination
                'ac 96 68 9a a6 98 e1'      # Source
                '09 00'                     # Control bytes
            ),
            modulo128=True
    )
    assert isinstance(frame, AX2516BitRejectFrame), \
            'Did not decode to REJ frame'
    eq_(frame.nr, 0)
    eq_(frame.pf, False)

def test_rr_frame_str():
    """
    Test we can get the string representation of a RR frame.
    """
    frame = AX258BitReceiveReadyFrame(
            destination='VK4BWI',
            source='VK4MSL',
            nr=6
    )

    eq_(str(frame), 'VK4MSL>VK4BWI: N(R)=6 P/F=False AX258BitReceiveReadyFrame')

def test_rr_frame_copy():
    """
    Test we can get the string representation of a RR frame.
    """
    frame = AX258BitReceiveReadyFrame(
            destination='VK4BWI',
            source='VK4MSL',
            nr=6
    )
    framecopy = frame.copy()

    assert framecopy is not frame
    hex_cmp(bytes(framecopy),
            'ac 96 68 84 ae 92 60'      # Destination
            'ac 96 68 9a a6 98 e1'      # Source
            'c1'                        # Control byte
    )
