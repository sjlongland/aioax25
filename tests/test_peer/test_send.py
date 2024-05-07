#!/usr/bin/env python3

"""
Tests for AX25Peer transmit segmentation
"""

from aioax25.frame import (
    AX25Address,
)
from .peer import TestingAX25Peer
from ..mocks import DummyStation


# UA reception


def test_peer_send_short():
    """
    Test send accepts short payloads and enqueues a single transmission.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=[],
        full_duplex=True,
    )

    peer._send_next_iframe_scheduled = False

    def _send_next_iframe():
        peer._send_next_iframe_scheduled = True

    peer._send_next_iframe = _send_next_iframe

    peer.send(b"Testing 1 2 3 4")

    assert peer._send_next_iframe_scheduled is True
    assert peer._pending_data == [(0xF0, b"Testing 1 2 3 4")]


def test_peer_send_long():
    """
    Test send accepts long payloads and enqueues multiple transmissions.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=[],
        full_duplex=True,
    )

    peer._send_next_iframe_scheduled = False

    def _send_next_iframe():
        peer._send_next_iframe_scheduled = True

    peer._send_next_iframe = _send_next_iframe

    peer.send(
        b"(0) Testing 1 2 3 4 5\n(1) Testing 1 2 3 4 5\n(2) Testing 1 2 3 4 5"
        b"\n(3) Testing 1 2 3 4 5\n(4) Testing 1 2 3 4 5\n(5) Testing 1 2 3 4"
        b" 5\n(6) Testing 1 2 3 4 5\n(7) Testing 1 2 3 4 5\n"
    )

    assert peer._send_next_iframe_scheduled is True
    assert peer._pending_data == [
        (
            0xF0,
            b"(0) Testing 1 2 3 4 5\n(1) Testing 1 2 3 4 5\n(2) Testing "
            b"1 2 3 4 5\n(3) Testing 1 2 3 4 5\n(4) Testing 1 2 3 4 5\n(5) "
            b"Testing 1 2 3 ",
        ),
        (0xF0, b"4 5\n(6) Testing 1 2 3 4 5\n(7) Testing 1 2 3 4 5\n"),
    ]


def test_peer_send_paclen():
    """
    Test send respects PACLEN.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=[],
        full_duplex=True,
        paclen=16,
    )

    peer._send_next_iframe_scheduled = False

    def _send_next_iframe():
        peer._send_next_iframe_scheduled = True

    peer._send_next_iframe = _send_next_iframe

    peer.send(
        b"(0) Testing 1 2 3 4 5\n(1) Testing 1 2 3 4 5\n(2) Testing 1 2 3 4 5"
        b"\n(3) Testing 1 2 3 4 5\n(4) Testing 1 2 3 4 5\n(5) Testing 1 2 3 4"
        b" 5\n(6) Testing 1 2 3 4 5\n(7) Testing 1 2 3 4 5\n"
    )

    assert peer._send_next_iframe_scheduled is True
    assert peer._pending_data == [
        (0xF0, b"(0) Testing 1 2 "),
        (0xF0, b"3 4 5\n(1) Testin"),
        (0xF0, b"g 1 2 3 4 5\n(2) "),
        (0xF0, b"Testing 1 2 3 4 "),
        (0xF0, b"5\n(3) Testing 1 "),
        (0xF0, b"2 3 4 5\n(4) Test"),
        (0xF0, b"ing 1 2 3 4 5\n(5"),
        (0xF0, b") Testing 1 2 3 "),
        (0xF0, b"4 5\n(6) Testing "),
        (0xF0, b"1 2 3 4 5\n(7) Te"),
        (0xF0, b"sting 1 2 3 4 5\n"),
    ]
