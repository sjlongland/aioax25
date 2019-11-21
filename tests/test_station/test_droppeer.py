#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.frame import AX25Address

from ..mocks import DummyInterface, DummyPeer


def test_known_peer_fetch_instance():
    """
    Test calling _drop_peer removes the peer
    """
    station = AX25Station(interface=DummyInterface(), callsign='VK4MSL-5')
    mypeer = DummyPeer(AX25Address('VK4BWI'))

    # Inject the peer
    station._peers[mypeer._address] = mypeer

    # Drop the peer
    station._drop_peer(mypeer)
    assert mypeer._address not in station._peers
    assert mypeer.address_read
