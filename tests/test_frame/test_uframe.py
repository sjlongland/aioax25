#!/usr/bin/env python3

from aioax25.frame import (
    AX25DisconnectModeFrame,
    AX25Frame,
    AX25FrameRejectFrame,
    AX25SetAsyncBalancedModeFrame,
    AX25SetAsyncBalancedModeExtendedFrame,
    AX25TestFrame,
    AX25UnnumberedAcknowledgeFrame,
    AX25UnnumberedFrame,
    AX25UnnumberedInformationFrame,
)

from ..hex import from_hex, hex_cmp


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
            "3f"  # Control byte
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
                "3f"  # Control byte
                "11 22 33 44 55"  # Payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e).startswith("Frame does not support payload")


def test_decode_sabme():
    """
    Test that a SABME frame is recognised and decoded.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "7f"  # Control byte
        )
    )
    assert isinstance(
        frame, AX25SetAsyncBalancedModeExtendedFrame
    ), "Did not decode to SABME frame"


def test_decode_sabme_payload():
    """
    Test that a SABME frame forbids payload.
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
        assert str(e).startswith("Frame does not support payload")


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


def test_encode_sabm():
    """
    Test we can encode a SABM frame.
    """
    frame = AX25SetAsyncBalancedModeFrame(
        destination="VK4BWI", source="VK4MSL"
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "3f",  # Control byte
    )


def test_encode_sabme():
    """
    Test we can encode a SABME frame.
    """
    frame = AX25SetAsyncBalancedModeExtendedFrame(
        destination="VK4BWI", source="VK4MSL"
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "7f",  # Control byte
    )


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
        "1f",  # Control
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
        "1f",  # Control
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


def test_ua_str():
    """
    Test we can get a string representation of a UA frame.
    """
    frame = AX25UnnumberedAcknowledgeFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
    )
    assert str(frame) == (
        "AX25UnnumberedAcknowledgeFrame VK4MSL>VK4BWI: "
        "Control=0x73 P/F=True Modifier=0x63"
    )


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
    assert str(frame) == (
        "AX25UnnumberedInformationFrame VK4MSL>VK4BWI: "
        "Control=0x03 P/F=False Modifier=0x03 PID=0xf0\n"
        "Payload=b'This is a test'"
    )
