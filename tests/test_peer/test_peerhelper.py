#!/usr/bin/env python3

"""
Tests for AX25PeerHelper
"""

from nose.tools import eq_

from aioax25.peer import AX25PeerHelper
from aioax25.frame import AX25Address
from ..mocks import DummyPeer


def test_peerhelper_start_timer():
    """
    Test _start_timer sets up a timeout timer.
    """
    peer = DummyPeer(AX25Address('VK4MSL'))
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
    peer = DummyPeer(AX25Address('VK4MSL'))
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
    peer = DummyPeer(AX25Address('VK4MSL'))
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
    peer = DummyPeer(AX25Address('VK4MSL'))
    helper = AX25PeerHelper(peer, timeout=0.1)

    # Cancel the non-existent timer, this should not trigger errors
    helper._stop_timer()
