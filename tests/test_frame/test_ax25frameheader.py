#!/usr/bin/env python3

from aioax25.frame import AX25Address, AX25FrameHeader
from ..hex import from_hex, hex_cmp


def test_decode_incomplete():
    """
    Test that an incomplete frame does not cause a crash.
    """
    try:
        AX25FrameHeader.decode(
            from_hex("ac 96 68 84 ae 92 e0")  # Destination
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Too few addresses"


def test_decode_no_digis():
    """
    Test we can decode an AX.25 frame without digipeaters.
    """
    (header, data) = AX25FrameHeader.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
        )
        + b"frame data goes here"  # Frame data
    )
    assert header.destination == AX25Address("VK4BWI", ch=True)
    assert header.source == AX25Address("VK4MSL", extension=True)
    assert len(header.repeaters) == 0
    assert data == b"frame data goes here"


def test_decode_legacy():
    """
    Test we can decode an AX.25 1.x frame.
    """
    (header, data) = AX25FrameHeader.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 e1"  # Source
        )
        + b"frame data goes here"  # Frame data
    )
    assert header.legacy
    assert header.cr
    assert header.destination == AX25Address("VK4BWI", ch=True)
    assert header.source == AX25Address("VK4MSL", extension=True, ch=True)
    assert len(header.repeaters) == 0
    assert data == b"frame data goes here"


def test_encode_legacy():
    """
    Test we can encode an AX.25 1.x frame.
    """
    header = AX25FrameHeader(
        destination="VK4BWI", source="VK4MSL", cr=False, legacy=True
    )
    hex_cmp(
        bytes(header),
        "ac 96 68 84 ae 92 60"  # Destination
        "ac 96 68 9a a6 98 61",  # Source
    )


def test_decode_with_1digi():
    """
    Test we can decode an AX.25 frame with one digipeater.
    """
    (header, data) = AX25FrameHeader.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 60"  # Source
            "ac 96 68 a4 b4 84 61"  # Digi
        )
        + b"frame data goes here"  # Frame data
    )
    assert header.destination == AX25Address("VK4BWI", ch=True)
    assert header.source == AX25Address("VK4MSL")
    assert header.repeaters[0] == AX25Address("VK4RZB", extension=True)
    assert data == b"frame data goes here"


def test_decode_with_2digis():
    """
    Test we can decode an AX.25 frame with two digipeaters.
    """
    (header, data) = AX25FrameHeader.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 60"  # Source
            "ac 96 68 a4 b4 84 60"  # Digi 1
            "ac 96 68 a4 b4 82 61"  # Digi 2
        )
        + b"frame data goes here"  # Frame data
    )
    assert header.destination == AX25Address("VK4BWI", ch=True)
    assert header.source == AX25Address("VK4MSL")
    assert len(header.repeaters) == 2
    assert header.repeaters[0] == AX25Address("VK4RZB")
    assert header.repeaters[1] == AX25Address("VK4RZA", extension=True)
    assert data == b"frame data goes here"


def test_encode_no_digis():
    """
    Test we can encode an AX.25 frame without digipeaters.
    """
    header = AX25FrameHeader(destination="VK4BWI", source="VK4MSL", cr=True)
    hex_cmp(
        bytes(header),
        "ac 96 68 84 ae 92 e0 "  # Destination
        "ac 96 68 9a a6 98 61",  # Source
    )


def test_encode_no_digis_ax25v1():
    """
    Test we can encode an AX.25v1 frame without digipeaters.
    """
    header = AX25FrameHeader(
        destination="VK4BWI", source="VK4MSL", cr=False, src_cr=False
    )
    hex_cmp(
        bytes(header),
        "ac 96 68 84 ae 92 60 "  # Destination
        "ac 96 68 9a a6 98 61",  # Source
    )


def test_encode_1digi():
    """
    Test we can encode an AX.25 frame with one digipeater.
    """
    header = AX25FrameHeader(
        destination="VK4BWI", source="VK4MSL", repeaters=("VK4RZB",), cr=True
    )
    hex_cmp(
        bytes(header),
        "ac 96 68 84 ae 92 e0 "  # Destination
        "ac 96 68 9a a6 98 60 "  # Source
        "ac 96 68 a4 b4 84 61",  # Digi
    )


def test_encode_2digis():
    """
    Test we can encode an AX.25 frame with two digipeaters.
    """
    header = AX25FrameHeader(
        destination="VK4BWI",
        source="VK4MSL",
        repeaters=("VK4RZB", "VK4RZA"),
        cr=True,
    )
    hex_cmp(
        bytes(header),
        "ac 96 68 84 ae 92 e0 "  # Destination
        "ac 96 68 9a a6 98 60 "  # Source
        "ac 96 68 a4 b4 84 60 "  # Digi 1
        "ac 96 68 a4 b4 82 61",  # Digi 2
    )
