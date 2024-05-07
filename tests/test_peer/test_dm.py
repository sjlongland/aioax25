#!/usr/bin/env python3

"""
Tests for AX25Peer DM handling
"""

from aioax25.frame import AX25Address, AX25Path, AX25DisconnectModeFrame
from aioax25.peer import AX25PeerState
from aioax25.version import AX25Version
from .peer import TestingAX25Peer
from ..mocks import DummyStation, DummyTimeout


# DM reception


def test_peer_recv_dm():
    """
    Test when receiving a DM whilst connected, the peer disconnects.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
        full_duplex=True,
    )

    # Set some dummy data in fields -- this should be cleared out.
    ack_timer = DummyTimeout(None, None)
    peer._ack_timeout_handle = ack_timer
    peer._state = AX25PeerState.CONNECTED
    peer._send_state = 1
    peer._send_seq = 2
    peer._recv_state = 3
    peer._recv_seq = 4
    peer._ack_state = 5
    peer._pending_iframes = dict(comment="pending data")
    peer._pending_data = ["pending data"]

    # Pass the peer a DM frame
    peer._on_receive(
        AX25DisconnectModeFrame(
            destination=station.address, source=peer.address, repeaters=None
        )
    )

    # We should now be "disconnected"
    assert peer._ack_timeout_handle is None
    assert peer._state is AX25PeerState.DISCONNECTED
    assert peer._send_state == 0
    assert peer._send_seq == 0
    assert peer._recv_state == 0
    assert peer._recv_seq == 0
    assert peer._ack_state == 0
    assert peer._pending_iframes == {}
    assert peer._pending_data == []


def test_peer_recv_dm_disconnected():
    """
    Test when receiving a DM whilst not connected, the peer does nothing.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
        full_duplex=True,
    )

    # Set some dummy data in fields -- this should be cleared out.
    ack_timer = DummyTimeout(None, None)
    peer._ack_timeout_handle = ack_timer
    peer._state = AX25PeerState.NEGOTIATING
    peer._send_state = 1
    peer._send_seq = 2
    peer._recv_state = 3
    peer._recv_seq = 4
    peer._ack_state = 5
    peer._pending_iframes = dict(comment="pending data")
    peer._pending_data = ["pending data"]

    # Pass the peer a DM frame
    peer._on_receive(
        AX25DisconnectModeFrame(
            destination=station.address, source=peer.address, repeaters=None
        )
    )

    # State should be unchanged from before
    assert peer._ack_timeout_handle is ack_timer
    assert peer._state is AX25PeerState.NEGOTIATING
    assert peer._send_state == 1
    assert peer._send_seq == 2
    assert peer._recv_state == 3
    assert peer._recv_seq == 4
    assert peer._ack_state == 5
    assert peer._pending_iframes == dict(comment="pending data")
    assert peer._pending_data == ["pending data"]


# DM transmission


def test_peer_send_dm():
    """
    Test _send_dm correctly addresses and sends a DM frame.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
        full_duplex=True,
    )

    # Request a DM frame be sent
    peer._send_dm()

    # There should be a frame sent
    assert len(interface.transmit_calls) == 1
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a DM
    assert tx_kwargs == {"callback": None}
    assert len(tx_args) == 1
    (frame,) = tx_args
    assert isinstance(frame, AX25DisconnectModeFrame)

    assert str(frame.header.destination) == "VK4MSL"
    assert str(frame.header.source) == "VK4MSL-1"
    assert str(frame.header.repeaters) == "VK4MSL-2,VK4MSL-3"
