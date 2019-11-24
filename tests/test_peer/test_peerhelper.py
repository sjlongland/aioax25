#!/usr/bin/env python3

"""
Tests for AX25PeerHelper
"""

from nose.tools import eq_

from aioax25.peer import AX25PeerHelper
from aioax25.frame import AX25Address
from ..mocks import DummyPeer, DummyStation


def test_peerhelper_start_timer():
    """
    Test _start_timer sets up a timeout timer.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    class TestHelper(AX25PeerHelper):
        def _on_timeout(self):
            pass

    helper = TestHelper(peer, timeout=0.1)

    assert helper._timeout_handle is None

    helper._start_timer()
    eq_(len(peer._loop.call_later_list), 1)
    timeout = peer._loop.call_later_list.pop(0)

    assert timeout is helper._timeout_handle
    eq_(timeout.delay, 0.1)
    eq_(timeout.callback, helper._on_timeout)
    eq_(timeout.args, ())
    eq_(timeout.kwargs, {})


def test_peerhelper_stop_timer():
    """
    Test _stop_timer clears an existing timeout timer.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)

    # Inject a timeout timer
    timeout = peer._loop.call_later(0, lambda : None)
    helper._timeout_handle = timeout
    assert not timeout.cancelled

    helper._stop_timer()

    assert timeout.cancelled
    assert helper._timeout_handle is None


def test_peerhelper_stop_timer_cancelled():
    """
    Test _stop_timer does not call cancel on already cancelled timer.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)

    # Inject a timeout timer
    timeout = peer._loop.call_later(0, lambda : None)
    helper._timeout_handle = timeout

    # Cancel it
    timeout.cancel()

    # Now stop the timer, this should not call .cancel itself
    helper._stop_timer()
    assert helper._timeout_handle is None


def test_peerhelper_stop_timer_absent():
    """
    Test _stop_timer does nothing if time-out object absent.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)

    # Cancel the non-existent timer, this should not trigger errors
    helper._stop_timer()


def test_finish():
    """
    Test _finish stops the timer and emits the done signal.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)
    assert not helper._done

    # Hook the done signal
    done_events = []
    helper.done_sig.connect(lambda **kw : done_events.append(kw))

    # Inject a timeout timer
    timeout = peer._loop.call_later(0, lambda : None)
    helper._timeout_handle = timeout

    # Call _finish to end the helper
    helper._finish(arg1='abc', arg2=123)

    # Task should be done
    assert helper._done

    # Signal should have fired
    eq_(done_events, [{'arg1': 'abc', 'arg2': 123}])

    # Timeout should have been cancelled
    assert timeout.cancelled


def test_finish_repeat():
    """
    Test _finish does nothing if already "done"
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)

    # Force the done flag.
    helper._done = True

    # Hook the done signal
    done_events = []
    helper.done_sig.connect(lambda **kw : done_events.append(kw))

    # Inject a timeout timer
    timeout = peer._loop.call_later(0, lambda : None)
    helper._timeout_handle = timeout

    # Call _finish to end the helper
    helper._finish(arg1='abc', arg2=123)

    # Signal should not have fired
    eq_(done_events, [])

    # Timeout should not have been cancelled
    assert not timeout.cancelled
