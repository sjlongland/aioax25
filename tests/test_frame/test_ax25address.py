#!/usr/bin/env python3

import aioax25.frame
from nose.tools import eq_


def test_ax25address_decode_bytes():
    """
    Test we can decode a plain AX.25 address in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x00'
    )
    eq_(addr._callsign, 'VK4MSL')

def test_ax25address_decode_bytes_spaces():
    """
    Test trailing spaces are truncated in call-signs.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x84\x82\x40\x00'
    )
    eq_(addr._callsign, 'VK4BA')

def test_ax25address_decode_bytes_ext():
    """
    Test we can decode the extension bit set in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x01'
    )
    eq_(addr._extension, True)

def test_ax25address_decode_bytes_ssid():
    """
    Test we can decode the SSID in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x14'
    )
    eq_(addr._ssid, 10)

def test_ax25address_decode_bytes_res0():
    """
    Test we can decode the first reserved bit in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x20'
    )
    eq_(addr._res0, True)

def test_ax25address_decode_bytes_res1():
    """
    Test we can decode the first reserved bit in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x40'
    )
    eq_(addr._res1, True)

def test_ax25address_decode_bytes_ch():
    """
    Test we can decode the C/H bit in binary.
    """
    addr = aioax25.frame.AX25Address.decode(
            b'\xac\x96\x68\x9a\xa6\x99\x80'
    )
    eq_(addr._ch, True)
