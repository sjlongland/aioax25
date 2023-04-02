#!/usr/bin/env python3

"""
Tests for AX25Peer UA handling
"""

from aioax25.frame import (
    AX25Address,
    AX25Path,
    AX25UnnumberedAcknowledgeFrame,
)
from aioax25.version import AX25Version
from .peer import TestingAX25Peer
from ..mocks import DummyStation


# UA reception


def test_peer_recv_ua():
    """
    Test _on_receive_ua does nothing if no UA expected.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
        full_duplex=True,
    )

    peer._on_receive_ua()

    # does nothing


# UA transmission


def test_peer_send_ua():
    """
    Test _send_ua correctly addresses and sends a UA frame.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
        full_duplex=True,
    )

    # Request a UA frame be sent
    peer._send_ua()

    # There should be a frame sent
    assert len(interface.transmit_calls) == 1
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a UA
    assert tx_kwargs == {"callback": None}
    assert len(tx_args) == 1
    (frame,) = tx_args
    assert isinstance(frame, AX25UnnumberedAcknowledgeFrame)

    assert str(frame.header.destination) == "VK4MSL"
    assert str(frame.header.source) == "VK4MSL-1"
    assert str(frame.header.repeaters) == "VK4MSL-2,VK4MSL-3"
