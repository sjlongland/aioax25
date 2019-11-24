#!/usr/bin/env python3

"""
Tests for AX25PeerTestHandler
"""

from nose.tools import eq_, assert_almost_equal

from aioax25.peer import AX25PeerTestHandler
from aioax25.frame import AX25Address, AX25TestFrame
from ..mocks import DummyPeer, DummyStation


def test_peertest_go():
    """
    Test _go transmits a test frame with CR=True and starts a timer.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Start it off
    helper._go()
    assert helper._timeout_handle is not None
    eq_(helper._timeout_handle.delay, 0.1)

    eq_(len(peer.transmit_calls), 1)
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a test frame, with CR=True
    assert frame is helper.tx_frame
    assert isinstance(frame, AX25TestFrame)
    assert frame.header.cr

    # Callback should be the _transmit_done method
    eq_(callback, helper._transmit_done)

    # We should be registered to receive the reply
    assert peer._testframe_handler is helper


def test_peertest_go_pending():
    """
    Test _go refuses to start if another test frame is pending.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    # Inject a different helper
    peer._testframe_handler = AX25PeerTestHandler(peer,
            payload=b'test', timeout=0.2)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Start it off
    try:
        helper._go()
        assert False, 'Should not have worked'
    except RuntimeError as e:
        if str(e) != 'Test frame already pending':
            raise


def test_peertest_transmit_done():
    """
    Test _transmit_done records time of transmission.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    assert helper.tx_time is None
    helper._transmit_done()
    assert helper.tx_time is not None

    assert_almost_equal(peer._loop.time(), helper.tx_time, places=2)


def test_peertest_on_receive():
    """
    Test _on_receive records time of reception and finishes the helper.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw : done_events.append(kw))

    assert helper.rx_time is None
    helper._on_receive(frame='Make believe TEST frame')
    assert helper.rx_time is not None

    assert_almost_equal(peer._loop.time(), helper.rx_time, places=2)
    eq_(helper.rx_frame, 'Make believe TEST frame')

    # We should be done now
    eq_(len(done_events), 1)
    done_evt = done_events.pop()
    eq_(list(done_evt.keys()), ['handler'])
    assert done_evt['handler'] is helper


def test_peertest_on_receive_done():
    """
    Test _on_receive ignores packets once done.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    # Mark as done
    helper._done = True

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw : done_events.append(kw))

    assert helper.rx_time is None
    helper._on_receive(frame='Make believe TEST frame')

    assert helper.rx_time is None
    assert helper.rx_frame is None
    eq_(len(done_events), 0)


def test_peertest_on_timeout():
    """
    Test _on_timeout winds up the handler
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerTestHandler(peer, payload=b'test', timeout=0.1)

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw : done_events.append(kw))

    helper._on_timeout()

    # We should be done now
    eq_(len(done_events), 1)
    done_evt = done_events.pop()
    eq_(list(done_evt.keys()), ['handler'])
    assert done_evt['handler'] is helper
