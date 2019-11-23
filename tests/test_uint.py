#!/usr/bin/env python3

from aioax25.uint import encode, decode
from nose.tools import eq_
from .hex import from_hex, hex_cmp

def test_encode_zero():
    """
    Test encode generates at least one byte if given a zero.
    """
    hex_cmp(encode(0), b'\x00')

def test_encode_le_nolen():
    """
    Test encode represents a little-endian integer in as few bytes as needed.
    """
    hex_cmp(encode(0x12345, big_endian=False),
            from_hex('45 23 01'))

def test_encode_le_len():
    """
    Test encode will generate an integer of the required size.
    """
    hex_cmp(encode(0x12345, big_endian=False, length=4),
            from_hex('45 23 01 00'))

def test_encode_le_truncate():
    """
    Test encode will truncate an integer to the required size.
    """
    hex_cmp(encode(0x123456789a, big_endian=False, length=4),
            from_hex('9a 78 56 34'))

def test_encode_be():
    """
    Test we can encode big-endian integers.
    """
    hex_cmp(encode(0x11223344, big_endian=True),
            from_hex('11 22 33 44'))

def test_decode_be():
    """
    Test we can decode big-endian integers.
    """
    eq_(decode(from_hex('11 22 33'), big_endian=True), 0x112233)

def test_decode_le():
    """
    Test we can decode little-endian integers.
    """
    eq_(decode(from_hex('11 22 33'), big_endian=False), 0x332211)
