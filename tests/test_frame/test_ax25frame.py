#!/usr/bin/env python3

from aioax25.frame import (
    AX25Frame,
    AX25RawFrame,
    AX25UnnumberedInformationFrame,
    AX258BitReceiveReadyFrame,
    AX2516BitReceiveReadyFrame,
    AX258BitRejectFrame,
    AX2516BitRejectFrame,
    AX258BitInformationFrame,
    AX2516BitInformationFrame,
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
