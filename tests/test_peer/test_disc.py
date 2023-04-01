#!/usr/bin/env python3

"""
Tests for AX25Peer DISC handling
"""

from aioax25.frame import AX25Address, AX25Path, AX25DisconnectFrame, \
        AX25UnnumberedAcknowledgeFrame
from aioax25.version import AX25Version
from .peer import TestingAX25Peer
from ..mocks import DummyStation, DummyTimeout


def test_peer_recv_disc():
    """
    Test when receiving a DISC whilst connected, the peer disconnects.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
            full_duplex=True, locked_path=True
    )

    # Set some dummy data in fields -- this should be cleared out.
    ack_timer = DummyTimeout(None, None)
    peer._ack_timeout_handle = ack_timer
    peer._state = peer.AX25PeerState.CONNECTED
    peer._send_state = 1
    peer._send_seq = 2
    peer._recv_state = 3
    peer._recv_seq = 4
    peer._ack_state = 5
    peer._pending_iframes = dict(comment="pending data")
    peer._pending_data = ["pending data"]

    # Pass the peer a DISC frame
    peer._on_receive(
            AX25DisconnectFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None
            )
    )

    # This was a request, so there should be a reply waiting
    assert len(interface.transmit_calls) == 1
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a UA in reply to the DISC
    assert tx_kwargs == {'callback': None}
    assert len(tx_args) == 1
    (frame,) = tx_args
    assert isinstance(frame, AX25UnnumberedAcknowledgeFrame)

    assert str(frame.header.destination) == "VK4MSL"
    assert str(frame.header.source) == "VK4MSL-1"
    assert str(frame.header.repeaters) == "VK4MSL-2,VK4MSL-3"

    # We should now be "disconnected"
    assert peer._ack_timeout_handle is None
    assert peer._state is peer.AX25PeerState.DISCONNECTED
    assert peer._send_state == 0
    assert peer._send_seq == 0
    assert peer._recv_state == 0
    assert peer._recv_seq == 0
    assert peer._ack_state == 0
    assert peer._pending_iframes == {}
    assert peer._pending_data == []


def test_peer_send_disc():
    """
    Test _send_disc correctly addresses and sends a DISC frame.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
            full_duplex=True
    )

    # Request a DISC frame be sent
    peer._send_disc()

    # There should be our outgoing request here
    assert len(interface.transmit_calls) == 1
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a DISC
    assert tx_kwargs == {'callback': None}
    assert len(tx_args) == 1
    (frame,) = tx_args
    assert isinstance(frame, AX25DisconnectFrame)

    assert str(frame.header.destination) == "VK4MSL"
    assert str(frame.header.source) == "VK4MSL-1"
    assert str(frame.header.repeaters) == "VK4MSL-2,VK4MSL-3"
