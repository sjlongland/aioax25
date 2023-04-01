#!/usr/bin/env python3

"""
Tests for AX25Peer DM handling
"""

from aioax25.frame import AX25Address, AX25Path, AX25DisconnectModeFrame
from aioax25.version import AX25Version
from .peer import TestingAX25Peer
from ..mocks import DummyStation


def test_peer_send_dm():
    """
    Test _send_dm correctly addresses and sends a DM frame.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path("VK4MSL-2", "VK4MSL-3"),
            full_duplex=True
    )

    # Request a DM frame be sent
    peer._send_dm()

    # This was a request, so there should be a reply waiting
    assert len(interface.transmit_calls) == 1
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a DM
    assert tx_kwargs == {'callback': None}
    assert len(tx_args) == 1
    (frame,) = tx_args
    assert isinstance(frame, AX25DisconnectModeFrame)

    assert str(frame.header.destination) == "VK4MSL"
    assert str(frame.header.source) == "VK4MSL-1"
    assert str(frame.header.repeaters) == "VK4MSL-2,VK4MSL-3"
