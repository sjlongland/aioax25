#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.peer import AX25Peer
from aioax25.frame import AX25Address

from ..mocks import DummyInterface, DummyPeer


def test_unknown_peer_nocreate_keyerror():
    """
    Test fetching an unknown peer with create=False raises KeyError
    """
    station = AX25Station(interface=DummyInterface(), callsign="VK4MSL-5")
    try:
        station.getpeer("VK4BWI", create=False)
        assert False, "Should not have worked"
    except KeyError as e:
        assert str(e) == (
            "AX25Address(callsign=VK4BWI, ssid=0, "
            "ch=True, res0=True, res1=True, extension=False)"
        )


def test_unknown_peer_create_instance_ch():
    """
    Test fetching an unknown peer with create=True generates peer with C/H set
    """
    station = AX25Station(interface=DummyInterface(), callsign="VK4MSL-5")
    peer = station.getpeer("VK4BWI", create=True)
    assert isinstance(peer, AX25Peer)
    assert peer.address.ch is True


def test_unknown_peer_create_instance_noch():
    """
    Test fetching an unknown peer with create=True and command=False generates
    peer with C/H clear
    """
    station = AX25Station(interface=DummyInterface(), callsign="VK4MSL-5")
    peer = station.getpeer("VK4BWI", create=True, command=False)
    assert isinstance(peer, AX25Peer)
    assert peer.address.ch is False


def test_known_peer_fetch_instance():
    """
    Test fetching an known peer returns that known peer
    """
    station = AX25Station(interface=DummyInterface(), callsign="VK4MSL-5")
    mypeer = DummyPeer(station, AX25Address("VK4BWI", ch=True))

    # Inject the peer
    station._peers[mypeer._address] = mypeer

    # Retrieve the peer instance
    peer = station.getpeer("VK4BWI")
    assert peer is mypeer


def test_known_peer_fetch_instance_ch():
    """
    Test fetching peers differentiates command bits
    """
    station = AX25Station(interface=DummyInterface(), callsign="VK4MSL-5")
    mypeer_in = DummyPeer(station, AX25Address("VK4BWI", ch=False))
    mypeer_out = DummyPeer(station, AX25Address("VK4BWI", ch=True))

    # Inject the peers
    station._peers[mypeer_in._address] = mypeer_in
    station._peers[mypeer_out._address] = mypeer_out

    # Retrieve the peer instance
    peer = station.getpeer("VK4BWI", command=True)
    assert peer is mypeer_out

    # Retrieve the other peer instance
    peer = station.getpeer("VK4BWI", command=False)
    assert peer is mypeer_in
