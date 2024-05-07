#!/usr/bin/env python3

"""
Test state transition logic
"""

from aioax25.frame import AX25Address, AX25Path
from aioax25.peer import AX25PeerState
from .peer import TestingAX25Peer
from ..mocks import DummyStation

# Idle time-out cancellation


def test_state_unchanged():
    """
    Test that _set_conn_state is a no-op if the state is not different.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    state_changes = []

    def _on_state_change(**kwargs):
        state_changes.append(kwargs)

    peer.connect_state_changed.connect(_on_state_change)

    assert peer._state is AX25PeerState.DISCONNECTED

    peer._set_conn_state(AX25PeerState.DISCONNECTED)

    assert state_changes == []


def test_state_changed():
    """
    Test that _set_conn_state reports and stores state changes.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    state_changes = []

    def _on_state_change(**kwargs):
        state_changes.append(kwargs)

    peer.connect_state_changed.connect(_on_state_change)

    assert peer._state is AX25PeerState.DISCONNECTED

    peer._set_conn_state(AX25PeerState.CONNECTED)

    assert peer._state is AX25PeerState.CONNECTED
    assert state_changes[1:] == []

    change = state_changes.pop(0)
    assert change.pop("station") is station
    assert change.pop("peer") is peer
    assert change.pop("state") is AX25PeerState.CONNECTED
    assert change == {}
