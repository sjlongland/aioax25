#!/usr/bin/env python3

from aioax25.frame import (
    AX25Frame,
    AX25RawFrame,
    AX25UnnumberedInformationFrame,
    AX25FrameRejectFrame,
    AX25UnnumberedFrame,
    AX258BitReceiveReadyFrame,
    AX2516BitReceiveReadyFrame,
    AX258BitRejectFrame,
    AX2516BitRejectFrame,
    AX258BitInformationFrame,
    AX2516BitInformationFrame,
    AX25DisconnectModeFrame,
    AX25SetAsyncBalancedModeFrame,
    AX25TestFrame,
    AX25ExchangeIdentificationFrame,
)
from ..hex import from_hex, hex_cmp

# Basic frame operations


def test_decode_incomplete():
    """
    Test that an incomplete frame does not cause a crash.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Insufficient packet data"


def test_decode_iframe():
    """
    Test that an I-frame gets decoded to a raw frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "00 11 22 33 44 55 66 77"  # Payload
        )
    )
    assert isinstance(frame, AX25RawFrame), "Did not decode to raw frame"
    hex_cmp(frame.frame_payload, "00 11 22 33 44 55 66 77")


def test_decode_sframe():
    """
    Test that an S-frame gets decoded to a raw frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "01 11 22 33 44 55 66 77"  # Payload
        )
    )
    assert isinstance(frame, AX25RawFrame), "Did not decode to raw frame"
    hex_cmp(frame.frame_payload, "01 11 22 33 44 55 66 77")


def test_decode_rawframe():
    """
    Test that we can decode an AX25RawFrame.
    """
    rawframe = AX25RawFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        payload=b"\x03\xf0This is a test",
    )
    frame = AX25Frame.decode(rawframe)
    assert isinstance(frame, AX25UnnumberedInformationFrame)
    assert frame.pid == 0xF0
    assert frame.payload == b"This is a test"


def test_frame_timestamp():
    """
    Test that the timestamp property is set from constructor.
    """
    frame = AX25RawFrame(
        destination="VK4BWI", source="VK4MSL", timestamp=11223344
    )
    assert frame.timestamp == 11223344


def test_frame_deadline():
    """
    Test that the deadline property is set from constructor.
    """
    frame = AX25RawFrame(
        destination="VK4BWI", source="VK4MSL", deadline=11223344
    )
    assert frame.deadline == 11223344


def test_frame_deadline_ro_if_set_constructor():
    """
    Test that the deadline property is read-only once set by contructor
    """
    frame = AX25RawFrame(
        destination="VK4BWI", source="VK4MSL", deadline=11223344
    )
    try:
        frame.deadline = 99887766
    except ValueError as e:
        assert str(e) == "Deadline may not be changed after being set"

    assert frame.deadline == 11223344


def test_frame_deadline_ro_if_set():
    """
    Test that the deadline property is read-only once set after constructor
    """
    frame = AX25RawFrame(
        destination="VK4BWI",
        source="VK4MSL",
    )

    frame.deadline = 44556677

    try:
        frame.deadline = 99887766
    except ValueError as e:
        assert str(e) == "Deadline may not be changed after being set"

    assert frame.deadline == 44556677


# Unnumbered frame tests


def test_decode_uframe():
    """
    Test that a U-frame gets decoded to an unnumbered frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "c3"  # Control byte
        )
    )
    assert isinstance(
        frame, AX25UnnumberedFrame
    ), "Did not decode to unnumbered frame"
    assert frame.modifier == 0xC3

    # We should see the control byte as our payload
    hex_cmp(frame.frame_payload, "c3")


def test_decode_sabm():
    """
    Test that a SABM frame is recognised and decoded.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "6f"  # Control byte
        )
    )
    assert isinstance(
        frame, AX25SetAsyncBalancedModeFrame
    ), "Did not decode to SABM frame"


def test_decode_sabm_payload():
    """
    Test that a SABM frame forbids payload.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "6f"  # Control byte
                "11 22 33 44 55"  # Payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Frame does not support payload"


def test_decode_uframe_payload():
    """
    Test that U-frames other than FRMR and UI are forbidden to have payloads.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "c3 11 22 33"  # Control byte
            )
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
            "Unnumbered frames (other than UI and "
            "FRMR) do not have payloads"
        )


def test_decode_frmr():
    """
    Test that a FRMR gets decoded to a frame reject frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "87"  # Control byte
            "11 22 33"  # Payload
        )
    )
    assert isinstance(
        frame, AX25FrameRejectFrame
    ), "Did not decode to FRMR frame"
    assert frame.modifier == 0x87
    assert frame.w == True
    assert frame.x == False
    assert frame.y == False
    assert frame.z == False
    assert frame.vr == 1
    assert frame.frmr_cr == False
    assert frame.vs == 1


def test_decode_frmr_len():
    """
    Test that a FRMR must have 3 byte payload.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "87"  # Control byte
                "11 22"  # Payload
            )
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Payload of FRMR must be 3 bytes"


def test_decode_ui():
    """
    Test that a UI gets decoded to an unnumbered information frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "03 11 22 33"  # Control byte
        )
    )
    assert isinstance(
        frame, AX25UnnumberedInformationFrame
    ), "Did not decode to UI frame"
    assert frame.pid == 0x11
    hex_cmp(frame.payload, "22 33")


def test_decode_ui_len():
    """
    Test that a UI must have at least one byte payload.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "03"  # Control byte
            )
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Payload of UI must be at least one byte"


def test_encode_raw():
    """
    Test that we can encode a raw frame.
    """
    # Yes, this is really a UI frame.
    frame = AX25RawFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        payload=b"\x03\xf0This is a test",
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "03"  # Control
        "f0 54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_encode_uframe():
    """
    Test that we can encode a U-frame.
    """
    frame = AX25UnnumberedFrame(
        destination="VK4BWI", source="VK4MSL", modifier=0xE7, cr=True
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "e7",  # Control
    )


def test_encode_frmr():
    """
    Test that we can encode a FRMR.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=True,
        x=False,
        y=True,
        z=False,
        vr=1,
        frmr_cr=False,
        vs=2,
        frmr_control=0xAA,
        cr=True,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "87"  # Control
        "05"  # W/X/Y/Z
        "24"  # VR/CR/VS
        "aa",  # FRMR Control
    )


def test_encode_ui():
    """
    Test that we can encode a UI frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        pid=0xF0,
        payload=b"This is a test",
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "03"  # Control
        "f0"  # PID
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_encode_test():
    """
    Test that we can encode a TEST frame.
    """
    frame = AX25TestFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        payload=b"This is a test",
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "e3"  # Control
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_decode_test():
    """
    Test that we can decode a TEST frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "e3"  # Control
            "31 32 33 34 35 36 37 38 39 2e 2e 2e"  # Payload
        )
    )
    assert isinstance(frame, AX25TestFrame)
    assert frame.payload == b"123456789..."


def test_copy_test():
    """
    Test that we can copy a TEST frame.
    """
    frame = AX25TestFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        payload=b"This is a test",
    )
    framecopy = frame.copy()
    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "e3"  # Control
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_encode_xid():
    """
    Test that we can encode a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        fi=0x82,
        gi=0x80,
        parameters=[
            AX25ExchangeIdentificationFrame.AX25XIDParameter(
                pi=0x12, pv=bytes([0x34, 0x56])
            ),
            AX25ExchangeIdentificationFrame.AX25XIDParameter(
                pi=0x34, pv=None
            ),
        ],
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "af"  # Control
        "82"  # Format indicator
        "80"  # Group Ident
        "00 06"  # Group length
        # First parameter
        "12"  # Parameter ID
        "02"  # Length
        "34 56"  # Value
        # Second parameter
        "34"  # Parameter ID
        "00",  # Length (no value)
    )


def test_decode_xid():
    """
    Test that we can decode a XID frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "af"  # Control
            "82"  # FI
            "80"  # GI
            "00 0c"  # GL
            # Some parameters
            "01 01 aa"
            "02 01 bb"
            "03 02 11 22"
            "04 00"
        )
    )
    assert isinstance(frame, AX25ExchangeIdentificationFrame)
    assert frame.fi == 0x82
    assert frame.gi == 0x80
    assert len(frame.parameters) == 4
    assert frame.parameters[0].pi == 0x01
    assert frame.parameters[0].pv == b"\xaa"
    assert frame.parameters[1].pi == 0x02
    assert frame.parameters[1].pv == b"\xbb"
    assert frame.parameters[2].pi == 0x03
    assert frame.parameters[2].pv == b"\x11\x22"
    assert frame.parameters[3].pi == 0x04
    assert frame.parameters[3].pv is None


def test_decode_xid_truncated_header():
    """
    Test that decoding a XID with truncated header fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00"  # Incomplete GL
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Truncated XID header"


def test_decode_xid_truncated_payload():
    """
    Test that decoding a XID with truncated payload fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 05"  # GL
                "11"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Truncated XID data"


def test_decode_xid_truncated_param_header():
    """
    Test that decoding a XID with truncated parameter header fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 01"  # GL
                "11"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Insufficient data for parameter"


def test_decode_xid_truncated_param_value():
    """
    Test that decoding a XID with truncated parameter value fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 04"  # GL
                "11 06 22 33"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Parameter is truncated"


def test_copy_xid():
    """
    Test that we can copy a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        fi=0x82,
        gi=0x80,
        parameters=[
            AX25ExchangeIdentificationFrame.AX25XIDParameter(
                pi=0x12, pv=bytes([0x34, 0x56])
            ),
            AX25ExchangeIdentificationFrame.AX25XIDParameter(
                pi=0x34, pv=None
            ),
        ],
    )
    framecopy = frame.copy()
    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "af"  # Control
        "82"  # Format indicator
        "80"  # Group Ident
        "00 06"  # Group length
        # First parameter
        "12"  # Parameter ID
        "02"  # Length
        "34 56"  # Value
        # Second parameter
        "34"  # Parameter ID
        "00",  # Length (no value)
    )


def test_encode_pf():
    """
    Test we can set the PF bit on a frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        pf=True,
        pid=0xF0,
        payload=b"This is a test",
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "13"  # Control
        "f0"  # PID
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )
    assert frame.control == 0x13


def test_encode_frmr_w():
    """
    Test we can set the W bit on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=True,
        x=False,
        y=False,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "01 00 00",  # FRMR data
    )


def test_encode_frmr_x():
    """
    Test we can set the X bit on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=True,
        y=False,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "02 00 00",  # FRMR data
    )


def test_encode_frmr_y():
    """
    Test we can set the Y bit on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=True,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "04 00 00",  # FRMR data
    )


def test_encode_frmr_z():
    """
    Test we can set the Z bit on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=True,
        vr=0,
        vs=0,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "08 00 00",  # FRMR data
    )


def test_encode_frmr_cr():
    """
    Test we can set the CR bit on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0,
        frmr_cr=True,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "00 10 00",  # FRMR data
    )


def test_encode_frmr_vr():
    """
    Test we can set the V(R) field on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=False,
        vr=5,
        vs=0,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "00 a0 00",  # FRMR data
    )


def test_encode_frmr_vs():
    """
    Test we can set the V(S) field on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=False,
        vr=0,
        vs=5,
        frmr_control=0,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "00 0a 00",  # FRMR data
    )


def test_encode_frmr_frmr_ctrl():
    """
    Test we can set the FRMR Control field on a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0x55,
        frmr_cr=False,
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "00 00 55",  # FRMR data
    )


def test_encode_dm_frame():
    """
    Test we can encode a Disconnect Mode frame.
    """
    frame = AX25DisconnectModeFrame(
        destination="VK4BWI",
        source="VK4MSL",
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "0f",  # Control
    )


def test_raw_copy():
    """
    Test we can make a copy of a raw frame.
    """
    frame = AX25RawFrame(
        destination="VK4BWI", source="VK4MSL", payload=b"\xabThis is a test"
    )
    framecopy = frame.copy()
    assert framecopy is not frame

    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "ab"  # Control
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_u_copy():
    """
    Test we can make a copy of a unnumbered frame.
    """
    frame = AX25UnnumberedFrame(
        destination="VK4BWI", source="VK4MSL", modifier=0x43  # Disconnect
    )
    framecopy = frame.copy()
    assert framecopy is not frame

    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "43",  # Control
    )


def test_dm_copy():
    """
    Test we can make a copy of a Disconnect Mode frame.
    """
    frame = AX25DisconnectModeFrame(
        destination="VK4BWI",
        source="VK4MSL",
    )
    framecopy = frame.copy()
    assert framecopy is not frame

    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "0f",  # Control
    )


def test_ui_copy():
    """
    Test we can make a copy of a unnumbered information frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        pid=0xF0,
        payload=b"This is a test",
    )
    framecopy = frame.copy()
    assert framecopy is not frame

    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "03"  # Control
        "f0"  # PID
        "54 68 69 73 20 69 73 20 61 20 74 65 73 74",  # Payload
    )


def test_frmr_copy():
    """
    Test we can copy a FRMR frame.
    """
    frame = AX25FrameRejectFrame(
        destination="VK4BWI",
        source="VK4MSL",
        w=False,
        x=False,
        y=False,
        z=False,
        vr=0,
        vs=0,
        frmr_control=0x55,
        frmr_cr=False,
    )
    framecopy = frame.copy()

    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "87"  # Control
        "00 00 55",  # FRMR data
    )


def test_raw_str():
    """
    Test we can get a string representation of a raw frame.
    """
    frame = AX25RawFrame(
        destination="VK4BWI", source="VK4MSL", payload=b"\xabThis is a test"
    )
    assert str(frame) == "VK4MSL>VK4BWI"


def test_ui_str():
    """
    Test we can get a string representation of a UI frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        pid=0xF0,
        payload=b"This is a test",
    )
    assert str(frame) == "VK4MSL>VK4BWI: PID=0xf0 Payload=b'This is a test'"


def test_ui_tnc2():
    """
    Test we can get a TNC2 string representation of a UI frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="VK4BWI*",
        source="VK4MSL",
        cr=True,
        pid=0xF0,
        payload=b"This is a test",
    )
    assert frame.tnc2 == "VK4MSL>VK4BWI:This is a test"


# Supervisory frame tests


def test_sframe_payload_reject():
    """
    Test payloads are forbidden for S-frames
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 60"  # Destination
                "ac 96 68 9a a6 98 e1"  # Source
                "41"  # Control
                "31 32 33 34 35"  # Payload
            ),
            modulo128=False,
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Supervisory frames do not support payloads."


def test_16bs_truncated_reject():
    """
    Test that 16-bit S-frames with truncated control fields are rejected.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 60"  # Destination
                "ac 96 68 9a a6 98 e1"  # Source
                "01"  # Control (LSB only)
            ),
            modulo128=True,
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Insufficient packet data"


def test_8bs_rr_frame():
    """
    Test we can generate a 8-bit RR supervisory frame
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "41"  # Control
        ),
        modulo128=False,
    )
    assert isinstance(frame, AX258BitReceiveReadyFrame)
    assert frame.nr == 2


def test_16bs_rr_frame():
    """
    Test we can generate a 16-bit RR supervisory frame
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "01 5c"  # Control
        ),
        modulo128=True,
    )
    assert isinstance(frame, AX2516BitReceiveReadyFrame)
    assert frame.nr == 46


def test_16bs_rr_encode():
    """
    Test we can encode a 16-bit RR supervisory frame
    """
    frame = AX2516BitReceiveReadyFrame(
        destination="VK4BWI", source="VK4MSL", nr=46, pf=True
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "01 5d",  # Control
    )
    assert frame.control == 0x5D01


def test_8bs_rej_decode_frame():
    """
    Test we can decode a 8-bit REJ supervisory frame
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "09"  # Control byte
        ),
        modulo128=False,
    )
    assert isinstance(
        frame, AX258BitRejectFrame
    ), "Did not decode to REJ frame"
    assert frame.nr == 0
    assert frame.pf == False


def test_16bs_rej_decode_frame():
    """
    Test we can decode a 16-bit REJ supervisory frame
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "09 00"  # Control bytes
        ),
        modulo128=True,
    )
    assert isinstance(
        frame, AX2516BitRejectFrame
    ), "Did not decode to REJ frame"
    assert frame.nr == 0
    assert frame.pf == False


def test_rr_frame_str():
    """
    Test we can get the string representation of a RR frame.
    """
    frame = AX258BitReceiveReadyFrame(
        destination="VK4BWI", source="VK4MSL", nr=6
    )

    assert str(frame) == (
        "VK4MSL>VK4BWI: N(R)=6 P/F=False AX258BitReceiveReadyFrame"
    )


def test_rr_frame_copy():
    """
    Test we can get the string representation of a RR frame.
    """
    frame = AX258BitReceiveReadyFrame(
        destination="VK4BWI", source="VK4MSL", nr=6
    )
    framecopy = frame.copy()

    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "c1",  # Control byte
    )


# Information frames


def test_8bit_iframe_decode():
    """
    Test we can decode an 8-bit information frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "d4"  # Control
            "ff"  # PID
            "54 68 69 73 20 69 73 20 61 20 74 65 73 74"  # Payload
        ),
        modulo128=False,
    )

    assert isinstance(
        frame, AX258BitInformationFrame
    ), "Did not decode to 8-bit I-Frame"
    assert frame.nr == 6
    assert frame.ns == 2
    assert frame.pid == 0xFF
    assert frame.payload == b"This is a test"


def test_16bit_iframe_decode():
    """
    Test we can decode an 16-bit information frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 60"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
            "04 0d"  # Control
            "ff"  # PID
            "54 68 69 73 20 69 73 20 61 20 74 65 73 74"  # Payload
        ),
        modulo128=True,
    )

    assert isinstance(
        frame, AX2516BitInformationFrame
    ), "Did not decode to 16-bit I-Frame"
    assert frame.nr == 6
    assert frame.ns == 2
    assert frame.pid == 0xFF
    assert frame.payload == b"This is a test"


def test_iframe_str():
    """
    Test we can get the string representation of an information frame.
    """
    frame = AX258BitInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        nr=6,
        ns=2,
        pid=0xFF,
        pf=True,
        payload=b"Testing 1 2 3",
    )

    assert str(frame) == (
        "VK4MSL>VK4BWI: N(R)=6 P/F=True N(S)=2 PID=0xff "
        "Payload=b'Testing 1 2 3'"
    )


def test_iframe_copy():
    """
    Test we can get the string representation of an information frame.
    """
    frame = AX258BitInformationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        nr=6,
        ns=2,
        pid=0xFF,
        pf=True,
        payload=b"Testing 1 2 3",
    )
    framecopy = frame.copy()

    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 e1"  # Source
        "d4"  # Control byte
        "ff"  # PID
        "54 65 73 74 69 6e 67 20"
        "31 20 32 20 33",  # Payload
    )
