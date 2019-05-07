#!/usr/bin/env python3

from aioax25.frame import AX25Address
from nose.tools import eq_
from ..hex import from_hex, to_hex

def test_decode_wrongtype():
    """
    Test that incorrect types are handled.
    """
    try:
        AX25Address.decode(12345)
        assert False, 'Should not have worked'
    except TypeError as e:
        eq_(str(e), "Don't know how to decode 12345")

def test_decode_bytes_short():
    """
    Test decoding a truncated address does not crash.
    """
    try:
        AX25Address.decode(
                from_hex('ac 96 68 9a a6')
        )
        assert False, 'This should not work'
    except ValueError as e:
        eq_(str(e), 'AX.25 addresses must be 7 bytes!')

def test_decode_bytes():
    """
    Test we can decode a plain AX.25 address in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 00')
    )
    eq_(addr._callsign, 'VK4MSL')

def test_decode_bytes_spaces():
    """
    Test trailing spaces are truncated in call-signs.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 84 82 40 00')
    )
    eq_(addr._callsign, 'VK4BA')

def test_decode_bytes_ext():
    """
    Test we can decode the extension bit set in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 01')
    )
    eq_(addr._extension, True)

def test_decode_bytes_ssid():
    """
    Test we can decode the SSID in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 14')
    )
    eq_(addr._ssid, 10)

def test_decode_bytes_res0():
    """
    Test we can decode the first reserved bit in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 20')
    )
    eq_(addr._res0, True)

def test_decode_bytes_res1():
    """
    Test we can decode the first reserved bit in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 40')
    )
    eq_(addr._res1, True)

def test_decode_bytes_ch():
    """
    Test we can decode the C/H bit in binary.
    """
    addr = AX25Address.decode(
            from_hex('ac 96 68 9a a6 98 80')
    )
    eq_(addr._ch, True)

def test_decode_str():
    """
    Test that we can decode a call-sign into an AX.25 address.
    """
    addr = AX25Address.decode(
            'VK4MSL'
    )
    eq_(addr._callsign, 'VK4MSL')

def test_decode_str_invalid():
    """
    Test that strings are correctly validated.
    """
    try:
        AX25Address.decode(
                'VK4-MSL'
        )
        assert False, 'Should not have worked'
    except ValueError as e:
        eq_(str(e), 'Not a valid SSID: VK4-MSL')

def test_decode_str_ssid():
    """
    Test that we can decode the SSID in a string.
    """
    addr = AX25Address.decode(
            'VK4MSL-12'
    )
    eq_(addr._ssid, 12)

def test_decode_str_ch():
    """
    Test that we can decode the C/H bit in a string.
    """
    addr = AX25Address.decode(
            'VK4MSL*'
    )
    eq_(addr._ch, True)

def test_decode_ax25address():
    """
    Test that passing in a AX25Address results in a clone being made.
    """
    addr1 = AX25Address('VK4MSL', 5)
    addr2 = AX25Address.decode(addr1)
    assert addr1 is not addr2
    for field in ('_callsign', '_ssid', '_ch', \
            '_res0', '_res1', '_extension'):
        eq_(getattr(addr1, field), getattr(addr2, field))

def test_encode_str():
    """
    Test we can encode a AX25Address as a string
    """
    eq_(str(AX25Address('VK4MSL', 0)), 'VK4MSL')

def test_encode_str_ssid():
    """
    Test we can encode a AX25Address as a string
    """
    eq_(str(AX25Address('VK4MSL', 11)), 'VK4MSL-11')

def test_encode_str_ch():
    """
    Test we can encode a AX25Address' C/H bit as a string
    """
    eq_(str(AX25Address('VK4MSL', ch=True)), 'VK4MSL*')

def test_encode_repr():
    """
    Test we can represent the AX25Address as a Python string
    """
    eq_(repr(AX25Address('VK4MSL', ch=True)), \
            ('AX25Address(callsign=VK4MSL, ssid=0, ch=True, '\
             'res0=True, res1=True, extension=False)'))

def test_encode_bytes():
    """
    Test we can encode a AX25Address as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL', 0,
                res0=False, res1=False, ch=False,
                extension=False))),
            'ac 96 68 9a a6 98 00'
    )

def test_encode_bytes_ssid():
    """
    Test we can encode a AX25Address as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL', 11,
                res0=False, res1=False, ch=False,
                extension=False))),
            'ac 96 68 9a a6 98 16'
    )

def test_encode_bytes_ch():
    """
    Test we can encode a AX25Address' C/H bit as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL',
                res0=False, res1=False, ch=True,
                extension=False))),
            'ac 96 68 9a a6 98 80'
    )

def test_encode_bytes_ext():
    """
    Test we can encode a AX25Address' extension bit as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL',
                res0=False, res1=False, ch=False,
                extension=True))),
            'ac 96 68 9a a6 98 01'
    )

def test_encode_bytes_res1():
    """
    Test we can encode a AX25Address' Reserved 1 bit as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL',
                res0=False, res1=True, ch=False,
                extension=False))),
            'ac 96 68 9a a6 98 40'
    )

def test_encode_bytes_res0():
    """
    Test we can encode a AX25Address' Reserved 0 bit as binary
    """
    eq_(
            to_hex(bytes(AX25Address('VK4MSL',
                res0=True, res1=False, ch=False,
                extension=False))),
            'ac 96 68 9a a6 98 20'
    )

def test_eq_match():
    """
    Test the __eq__ operator correctly matches addresses.
    """
    a = AX25Address('VK4MSL', 12, ch=False)
    b = AX25Address('VK4MSL', 12, ch=False)
    assert a is not b
    assert a == b

def test_eq_notmatch():
    """
    Test the __eq__ operator correctly identifies non-matching addresses.
    """
    a = AX25Address('VK4MSL', 12, ch=False)
    b = AX25Address('VK4MSL', 12, ch=True)
    assert a != b

def test_eq_notaddr():
    """
    Test the __eq__ operator does not attempt to compare non-addresses.
    """
    a = AX25Address('VK4MSL', 12, ch=False)
    assert a != 'foobar'

def test_hash():
    """
    Test we can obtain a reliable hash.
    """
    a = AX25Address('VK4MSL', 12, ch=False)
    b = AX25Address('VK4MSL', 12, ch=False)
    c = AX25Address('VK4MSL', 12, ch=True)
    assert a is not b
    assert a is not c
    assert hash(a) == hash(b)
    assert hash(a) != hash(c)

def test_copy():
    """
    Test we can make copies of the address with arbitrary fields set.
    """
    a = AX25Address('VK4MSL', 15, ch=False)
    b = a.copy(ch=True)

    assert b._ch is True

    # Everything else should be the same
    for field in ('_callsign', '_ssid', '_res0', '_res1', '_extension'):
        eq_(getattr(a, field), getattr(b, field))

def test_normalised():
    """
    Test we can get normalised copies for comparison.
    """
    a = AX25Address('VK4MSL', 15, ch=True, res0=False, res1=False)
    b = a.normalised

    assert b._ch is False
    assert b._res0 is True
    assert b._res1 is True

def test_ch_setter():
    """
    Test we can mutate the C/H bit.
    """
    a = AX25Address('VK4MSL', 15, ch=False)
    a.ch = True
    assert a._ch is True

def test_extension_setter():
    """
    Test we can mutate the extension bit.
    """
    a = AX25Address('VK4MSL', 15, extension=False)
    a.extension = True
    assert a._extension is True
