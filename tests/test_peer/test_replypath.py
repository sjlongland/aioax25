#!/usr/bin/env python3

"""
Tests for AX25Peer reply path handling
"""

from aioax25.frame import AX25Address, AX25Path
from .peer import TestingAX25Peer
from ..mocks import DummyStation


def test_peer_reply_path_locked():
    """
    Test reply_path with a locked path returns the repeaters given
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Ensure not pre-determined path is set
    peer._reply_path = None

    assert str(peer.reply_path) == "VK4RZB"


def test_peer_reply_path_predetermined():
    """
    Test reply_path with pre-determined path returns the chosen path
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=None,
        locked_path=False,
    )

    # Inject pre-determined path
    peer._reply_path = AX25Path("VK4RZB")

    assert str(peer.reply_path) == "VK4RZB"


def test_peer_reply_path_weight_score():
    """
    Test reply_path tries to select the "best" scoring path.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=None,
        locked_path=False,
    )

    # Ensure not pre-determined path is set
    peer._reply_path = None

    # Inject path scores
    peer._tx_path_score = {AX25Path("VK4RZB"): 2, AX25Path("VK4RZA"): 1}

    assert str(peer.reply_path) == "VK4RZB"

    # We should also use this from now on:
    assert str(peer._reply_path) == "VK4RZB"


def test_peer_reply_path_rx_count():
    """
    Test reply_path considers received paths if no rated TX path.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=None,
        locked_path=False,
    )

    # Ensure not pre-determined path is set
    peer._reply_path = None

    # Ensure empty TX path scores
    peer._tx_path_score = {}

    # Inject path counts
    peer._rx_path_count = {AX25Path("VK4RZB"): 2, AX25Path("VK4RZA"): 1}

    assert str(peer.reply_path) == "VK4RZB"

    # We should also use this from now on:
    assert str(peer._reply_path) == "VK4RZB"


# Path weighting


def test_weight_path_absolute():
    """
    Test we can set the score for a given path.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=None,
        locked_path=False,
    )

    # Ensure known weights
    peer._tx_path_score = {
        tuple(AX25Path("VK4RZB", "VK4RZA")): 1,
        tuple(AX25Path("VK4RZA")): 2,
    }

    # Rate a few paths
    peer.weight_path(AX25Path("VK4RZB*", "VK4RZA*"), 5, relative=False)
    peer.weight_path(AX25Path("VK4RZA*"), 3, relative=False)

    assert peer._tx_path_score == {
        tuple(AX25Path("VK4RZB", "VK4RZA")): 5,
        tuple(AX25Path("VK4RZA")): 3,
    }


def test_weight_path_relative():
    """
    Test we can increment the score for a given path.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=None,
        locked_path=False,
    )

    # Ensure known weights
    peer._tx_path_score = {
        tuple(AX25Path("VK4RZB", "VK4RZA")): 5,
        tuple(AX25Path("VK4RZA")): 3,
    }

    # Rate a few paths
    peer.weight_path(AX25Path("VK4RZB*", "VK4RZA*"), 2, relative=True)
    peer.weight_path(AX25Path("VK4RZA*"), 1, relative=True)

    assert peer._tx_path_score == {
        tuple(AX25Path("VK4RZB", "VK4RZA")): 7,
        tuple(AX25Path("VK4RZA")): 4,
    }
