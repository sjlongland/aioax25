#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.frame import AX25Address, AX25TestFrame, \
        AX25UnnumberedInformationFrame

from nose.tools import eq_
from ..mocks import DummyInterface, DummyPeer


def test_testframe_cmd_echo():
    """
    Test passing a test frame with CR=True triggers a reply frame.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL-5')

    # Pass in a frame
    station._on_receive(frame=AX25TestFrame(
        destination='VK4MSL-5',
        source='VK4MSL-7',
        cr=True,
        payload=b'This is a test frame'
    ))

    # There should be no peers
    eq_(station._peers, {})

    # There should be a reply queued up
    eq_(interface.bind_calls, [])
    eq_(interface.unbind_calls, [])
    eq_(len(interface.transmit_calls), 1)

    (tx_call_args, tx_call_kwargs) = interface.transmit_calls.pop()
    eq_(tx_call_kwargs, {})
    eq_(len(tx_call_args), 1)
    frame = tx_call_args[0]

    # The reply should have the source/destination swapped and the
    # CR bit cleared.
    assert isinstance(frame, AX25TestFrame), 'Not a test frame'
    eq_(frame.header.cr, False)
    eq_(frame.header.destination, AX25Address('VK4MSL', ssid=7))
    eq_(frame.header.source, AX25Address('VK4MSL', ssid=5))
    eq_(frame.payload, b'This is a test frame')


def test_route_testframe_reply():
    """
    Test passing a test frame reply routes to the appropriate AX25Peer instance.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL-5')

    # Stub out _on_test_frame
    def stub_on_test_frame(*args, **kwargs):
        assert False, 'Should not have been called'
    station._on_test_frame = stub_on_test_frame

    # Inject a couple of peers
    peer1 = DummyPeer(AX25Address('VK4MSL', ssid=7))
    peer2 = DummyPeer(AX25Address('VK4BWI', ssid=7))
    station._peers[peer1._address] = peer1
    station._peers[peer2._address] = peer2

    # Pass in the message
    txframe = AX25TestFrame(
        destination='VK4MSL-5',
        source='VK4MSL-7',
        cr=False,
        payload=b'This is a test frame'
    )
    station._on_receive(frame=txframe)

    # There should be no replies queued
    eq_(interface.bind_calls, [])
    eq_(interface.unbind_calls, [])
    eq_(interface.transmit_calls, [])

    # This should have gone to peer1, not peer2
    eq_(peer2.on_receive_calls, [])
    eq_(len(peer1.on_receive_calls), 1)
    (rx_call_args, rx_call_kwargs) = peer1.on_receive_calls.pop()
    eq_(rx_call_kwargs, {})
    eq_(len(rx_call_args), 1)
    assert rx_call_args[0] is txframe


def test_route_incoming_msg():
    """
    Test passing a frame routes to the appropriate AX25Peer instance.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL-5')

    # Stub out _on_test_frame
    def stub_on_test_frame(*args, **kwargs):
        assert False, 'Should not have been called'
    station._on_test_frame = stub_on_test_frame

    # Inject a couple of peers
    peer1 = DummyPeer(AX25Address('VK4MSL', ssid=7))
    peer2 = DummyPeer(AX25Address('VK4BWI', ssid=7))
    station._peers[peer1._address] = peer1
    station._peers[peer2._address] = peer2

    # Pass in the message
    txframe = AX25UnnumberedInformationFrame(
        destination='VK4MSL-5',
        source='VK4BWI-7',
        cr=True, pid=0xab,
        payload=b'This is a test frame'
    )
    station._on_receive(frame=txframe)

    # There should be no replies queued
    eq_(interface.bind_calls, [])
    eq_(interface.unbind_calls, [])
    eq_(interface.transmit_calls, [])

    # This should have gone to peer2, not peer1
    eq_(peer1.on_receive_calls, [])
    eq_(len(peer2.on_receive_calls), 1)
    (rx_call_args, rx_call_kwargs) = peer2.on_receive_calls.pop()
    eq_(rx_call_kwargs, {})
    eq_(len(rx_call_args), 1)
    assert rx_call_args[0] is txframe
