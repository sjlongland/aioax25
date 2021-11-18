#!/usr/bin/env python3

"""
Test handling of outgoing connection logic
"""

from aioax25.frame import AX25Address, AX25Path
from .peer import TestingAX25Peer
from ..mocks import DummyStation

# Connection establishment

def test_connect_not_disconnected():
    """
    Test that calling peer.connect() when not disconnected does nothing.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path('VK4RZB'),
            locked_path=True
    )

    # Stub negotiation, this should not get called
    def _negotiate(*args, **kwargs):
        assert False, 'Should not have been called'
    peer._negotiate = _negotiate

    # Ensure _negotiate() gets called if we try to connect
    peer._negotiated = False

    # Override the state to ensure connection attempt never happens
    peer._state = peer.AX25PeerState.CONNECTED

    # Now try connecting
    peer.connect()


def test_connect_when_disconnected():
    """
    Test that calling peer.connect() when disconnected initiates connection
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path('VK4RZB'),
            locked_path=True
    )

    # Stub negotiation, we'll just throw an error to see if it gets called
    class ConnectionStarted(Exception):
        pass
    def _negotiate(*args, **kwargs):
        raise ConnectionStarted()
    peer._negotiate = _negotiate

    # Ensure _negotiate() gets called if we try to connect
    peer._negotiated = False

    # Ensure disconnected state
    peer._state = peer.AX25PeerState.DISCONNECTED

    # Now try connecting
    try:
        peer.connect()
        assert False, 'Did not call _negotiate'
    except ConnectionStarted:
        pass
