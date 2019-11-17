#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.peer import AX25Peer

from nose.tools import eq_
from ..mocks import DummyInterface


def test_unknown_peer_nocreate_keyerror():
    """
    Test fetching an unknown peer with create=False raises KeyError
    """
    station = AX25Station(interface=DummyInterface(), callsign='VK4MSL-5')
    try:
        station.getpeer('VK4BWI', create=False)
        assert False, 'Should not have worked'
    except KeyError as e:
        eq_(str(e), 'AX25Address(callsign=VK4BWI, ssid=0, '\
                'ch=False, res0=True, res1=True, extension=False)')

def test_unknown_peer_create_instance():
    """
    Test fetching an unknown peer with create=True generates peer
    """
    station = AX25Station(interface=DummyInterface(), callsign='VK4MSL-5')
    peer = station.getpeer('VK4BWI', create=True)
    assert isinstance(peer, AX25Peer)
