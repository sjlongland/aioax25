#!/usr/bin/env python3

from aioax25.frame import AX25Address, AX25Path


def test_decode():
    """
    Test given a list of strings, AX25Path decodes them.
    """
    path = AX25Path("VK4MSL", "VK4RZB", "VK4RZA")
    assert path._path[0]._callsign == "VK4MSL"
    assert path._path[1]._callsign == "VK4RZB"
    assert path._path[2]._callsign == "VK4RZA"


def test_addresses():
    """
    Test given a list of AX25Addresses, AX25Path passes them in.
    """
    path = AX25Path(
        AX25Address.decode("VK4MSL"),
        AX25Address.decode("VK4RZB"),
        AX25Address.decode("VK4RZA"),
    )
    assert path._path[0]._callsign == "VK4MSL"
    assert path._path[1]._callsign == "VK4RZB"
    assert path._path[2]._callsign == "VK4RZA"


def test_str():
    """
    Test we can return the canonical format for a repeater path.
    """
    path = AX25Path("VK4MSL", "VK4RZB", "VK4RZA")
    assert str(path) == "VK4MSL,VK4RZB,VK4RZA"


def test_repr():
    """
    Test we can return the Python representation for a repeater path.
    """
    path = AX25Path("VK4MSL", "VK4RZB", "VK4RZA")
    assert repr(path) == (
        "AX25Path("
        "AX25Address("
        "callsign=VK4MSL, ssid=0, ch=False, "
        "res0=True, res1=True, extension=False"
        "), "
        "AX25Address("
        "callsign=VK4RZB, ssid=0, ch=False, "
        "res0=True, res1=True, extension=False"
        "), "
        "AX25Address("
        "callsign=VK4RZA, ssid=0, ch=False, "
        "res0=True, res1=True, extension=False"
        ")"
        ")"
    )


def test_reply():
    """
    Test 'reply' returns a reverse path for sending replies.
    """
    path = AX25Path("VK4MSL*", "VK4RZB*", "VK4RZA*")
    reply = path.reply
    assert str(reply) == "VK4RZA,VK4RZB,VK4MSL"


def test_reply_unused():
    """
    Test 'reply' ignores unused repeaters.
    """
    path = AX25Path("VK4MSL*", "VK4RZB*", "VK4RZA")
    reply = path.reply
    assert str(reply) == "VK4RZB,VK4MSL"


def test_replace():
    """
    Test we can replace an alias with our own call-sign.
    """
    path1 = AX25Path("WIDE2-2", "WIDE1-1")
    path2 = path1.replace("WIDE2-2", "VK4MSL*")
    assert str(path2) == "VK4MSL*,WIDE1-1"
