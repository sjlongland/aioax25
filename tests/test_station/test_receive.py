#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.frame import (
    AX25Address,
    AX25TestFrame,
    AX25UnnumberedInformationFrame,
)

from ..mocks import DummyInterface, DummyPeer


def test_testframe_cmd_echo():
    """
    Test passing a test frame with CR=True triggers a reply frame.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign="VK4MSL-5")

    # Pass in a frame
    station._on_receive(
        frame=AX25TestFrame(
            destination="VK4MSL-5",
            source="VK4MSL-7",
            cr=True,
            payload=b"This is a test frame",
        )
    )

    # There should be no peers
    assert station._peers == {}

    # There should be a reply queued up
    assert interface.bind_calls == []
    assert interface.unbind_calls == []
    assert len(interface.transmit_calls) == 1

    (tx_call_args, tx_call_kwargs) = interface.transmit_calls.pop()
    assert tx_call_kwargs == {}
    assert len(tx_call_args) == 1
    frame = tx_call_args[0]

    # The reply should have the source/destination swapped and the
    # CR bit cleared.
    assert isinstance(frame, AX25TestFrame), "Not a test frame"
    assert frame.header.cr == False
    assert frame.header.destination == AX25Address("VK4MSL", ssid=7)
    assert frame.header.source == AX25Address("VK4MSL", ssid=5)
    assert frame.payload == b"This is a test frame"


def test_route_testframe_reply():
    """
    Test passing a test frame reply routes to the appropriate AX25Peer instance.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign="VK4MSL-5")

    # Stub out _on_test_frame
    def stub_on_test_frame(*args, **kwargs):
        assert False, "Should not have been called"

    station._on_test_frame = stub_on_test_frame

    # Inject a couple of peers
    peer1 = DummyPeer(station, AX25Address("VK4MSL", ssid=7))
    peer2 = DummyPeer(station, AX25Address("VK4BWI", ssid=7))
    station._peers[peer1._address] = peer1
    station._peers[peer2._address] = peer2

    # Pass in the message
    txframe = AX25TestFrame(
        destination="VK4MSL-5",
        source="VK4MSL-7",
        cr=False,
        payload=b"This is a test frame",
    )
    station._on_receive(frame=txframe)

    # There should be no replies queued
    assert interface.bind_calls == []
    assert interface.unbind_calls == []
    assert interface.transmit_calls == []

    # This should have gone to peer1, not peer2
    assert peer2.on_receive_calls == []
    assert len(peer1.on_receive_calls) == 1
    (rx_call_args, rx_call_kwargs) = peer1.on_receive_calls.pop()
    assert rx_call_kwargs == {}
    assert len(rx_call_args) == 1
    assert rx_call_args[0] is txframe


def test_route_incoming_msg():
    """
    Test passing a frame routes to the appropriate AX25Peer instance.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign="VK4MSL-5")

    # Stub out _on_test_frame
    def stub_on_test_frame(*args, **kwargs):
        assert False, "Should not have been called"

    station._on_test_frame = stub_on_test_frame

    # Inject a couple of peers
    peer1 = DummyPeer(station, AX25Address("VK4MSL", ssid=7))
    peer2 = DummyPeer(station, AX25Address("VK4BWI", ssid=7))
    station._peers[peer1._address] = peer1
    station._peers[peer2._address] = peer2

    # Pass in the message
    txframe = AX25UnnumberedInformationFrame(
        destination="VK4MSL-5",
        source="VK4BWI-7",
        cr=True,
        pid=0xAB,
        payload=b"This is a test frame",
    )
    station._on_receive(frame=txframe)

    # There should be no replies queued
    assert interface.bind_calls == []
    assert interface.unbind_calls == []
    assert interface.transmit_calls == []

    # This should have gone to peer2, not peer1
    assert peer1.on_receive_calls == []
    assert len(peer2.on_receive_calls) == 1
    (rx_call_args, rx_call_kwargs) = peer2.on_receive_calls.pop()
    assert rx_call_kwargs == {}
    assert len(rx_call_args) == 1
    assert rx_call_args[0] is txframe
