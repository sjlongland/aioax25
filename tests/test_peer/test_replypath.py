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
        repeaters=AX25Path(AX25Address("VK4RZB")),
        locked_path=True,
    )

    # Ensure not pre-determined path is set
    peer._reply_path = None

    assert list(peer.reply_path) == [AX25Address("VK4RZB")]


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
    peer._reply_path = AX25Path(AX25Address("VK4RZB"))

    assert list(peer.reply_path) == [AX25Address("VK4RZB")]


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
    peer._tx_path_score = {
        AX25Path(AX25Address("VK4RZB")): 2,
        AX25Path(AX25Address("VK4RZA")): 1,
    }

    assert list(peer.reply_path) == [AX25Address("VK4RZB")]

    # We should also use this from now on:
    assert list(peer._reply_path) == [AX25Address("VK4RZB")]


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
    peer._rx_path_count = {
        AX25Path(AX25Address("VK4RZB")): 2,
        AX25Path(AX25Address("VK4RZA")): 1,
    }

    assert list(peer.reply_path) == [AX25Address("VK4RZB")]

    # We should also use this from now on:
    assert list(peer._reply_path) == [AX25Address("VK4RZB")]
