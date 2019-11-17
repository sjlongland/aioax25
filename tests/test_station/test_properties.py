#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.version import AX25Version
from aioax25.frame import AX25Address

from nose.tools import eq_
from ..mocks import DummyInterface


def test_address():
    """
    Test the address of the station is set from the constructor.
    """
    station = AX25Station(interface=DummyInterface(), callsign='VK4MSL-5')
    eq_(station.address, AX25Address(callsign='VK4MSL', ssid=5))

def test_protocol():
    """
    Test the protocol of the station is set from the constructor.
    """
    station = AX25Station(interface=DummyInterface(), callsign='VK4MSL-5',
            protocol=AX25Version.AX25_20)
    eq_(station.protocol, AX25Version.AX25_20)
