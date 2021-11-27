#!/usr/bin/env python3

"""
Tests for receive path handling
"""

from aioax25.frame import AX25Address, AX25TestFrame, AX25Path
from ..mocks import DummyStation
from .peer import TestingAX25Peer


def test_rx_path_stats_unlocked():
    """
    Test that incoming message paths are counted when path NOT locked.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path('VK4RZB'),
            locked_path=False
    )

    # Stub the peer's _on_receive_test method
    rx_frames = []
    def _on_receive_test(frame):
        rx_frames.append(frame)
    peer._on_receive_test = _on_receive_test

    # Send a few test frames via different paths
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZB*'), 
          payload=b'test 1', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZA*', 'VK4RZB*'), 
          payload=b'test 2', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZD*', 'VK4RZB*'), 
          payload=b'test 3', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZB*'), 
          payload=b'test 4', 
          cr=True 
    ))

    # For test readability, convert the tuple keys to strings
    # AX25Path et all has its own tests for str.
    rx_path_count = dict([
        (str(AX25Path(*path)), count)
        for path, count
        in peer._rx_path_count.items()
    ])

    assert rx_path_count == {
        'VK4RZB': 2,
        'VK4RZA,VK4RZB': 1,
        'VK4RZD,VK4RZB': 1
    }


def test_rx_path_stats_locked():
    """
    Test that incoming message paths are NOT counted when path locked.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=AX25Path('VK4RZB'),
            locked_path=True
    )

    # Stub the peer's _on_receive_test method
    rx_frames = []
    def _on_receive_test(frame):
        rx_frames.append(frame)
    peer._on_receive_test = _on_receive_test

    # Send a few test frames via different paths
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZB*'), 
          payload=b'test 1', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZA*', 'VK4RZB*'), 
          payload=b'test 2', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZD*', 'VK4RZB*'), 
          payload=b'test 3', 
          cr=True 
    ))
    peer._on_receive(AX25TestFrame(
          destination=peer.address, 
          source=station.address, 
          repeaters=AX25Path('VK4RZB*'), 
          payload=b'test 4', 
          cr=True 
    ))

    # For test readability, convert the tuple keys to strings
    # AX25Path et all has its own tests for str.
    rx_path_count = dict([
        (str(AX25Path(*path)), count)
        for path, count
        in peer._rx_path_count.items()
    ])

    assert rx_path_count == {}
