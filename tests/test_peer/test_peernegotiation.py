#!/usr/bin/env python3

"""
Tests for AX25PeerNegotiationHandler
"""

from nose.tools import eq_, assert_almost_equal, assert_is, \
        assert_is_not_none, assert_is_none

from aioax25.peer import AX25PeerNegotiationHandler
from aioax25.frame import AX25Address, AX25TestFrame
from ..mocks import DummyPeer, DummyStation


def test_peertest_go():
    """
    Test _go transmits a test frame with CR=True and starts a timer.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Start it off
    helper._go()
    assert_is_not_none(helper._timeout_handle)
    eq_(helper._timeout_handle.delay, 0.1)

    # Helper should have hooked the handler events
    eq_(peer._xidframe_handler, helper._on_receive_xid)
    eq_(peer._frmrframe_handler, helper._on_receive_frmr)
    eq_(peer._dmframe_handler, helper._on_receive_dm)

    # Station should have been asked to send an XID
    eq_(len(peer.transmit_calls), 1)
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a test frame, with CR=True
    eq_(frame, 'xid:cr=True')
    assert_is_none(callback)


def test_peertest_go_xidframe_handler():
    """
    Test _go refuses to run if another XID frame handler is hooked.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Hook the XID handler
    peer._xidframe_handler = lambda *a, **kwa : None

    # Try to start it off
    try:
        helper._go()
        assert False, 'Should not have worked'
    except RuntimeError as e:
        if str(e) != 'Another frame handler is busy':
            raise


def test_peertest_go_frmrframe_handler():
    """
    Test _go refuses to run if another FRMR frame handler is hooked.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Hook the FRMR handler
    peer._frmrframe_handler = lambda *a, **kwa : None

    # Try to start it off
    try:
        helper._go()
        assert False, 'Should not have worked'
    except RuntimeError as e:
        if str(e) != 'Another frame handler is busy':
            raise


def test_peertest_go_dmframe_handler():
    """
    Test _go refuses to run if another DM frame handler is hooked.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Hook the DM handler
    peer._dmframe_handler = lambda *a, **kwa : None

    # Try to start it off
    try:
        helper._go()
        assert False, 'Should not have worked'
    except RuntimeError as e:
        if str(e) != 'Another frame handler is busy':
            raise


def test_peertest_receive_xid():
    """
    Test _on_receive_xid ends the helper
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw : done_evts.append(kw))

    # Call _on_receive_xid
    helper._on_receive_xid()

    # See that the helper finished
    assert_is(helper._done, True)
    eq_(done_evts, [{'response': 'xid'}])


def test_peertest_receive_frmr():
    """
    Test _on_receive_frmr ends the helper
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw : done_evts.append(kw))

    # Call _on_receive_frmr
    helper._on_receive_frmr()

    # See that the helper finished
    assert_is(helper._done, True)
    eq_(done_evts, [{'response': 'frmr'}])


def test_peertest_receive_dm():
    """
    Test _on_receive_dm ends the helper
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw : done_evts.append(kw))

    # Call _on_receive_frmr
    helper._on_receive_dm()

    # See that the helper finished
    assert_is(helper._done, True)
    eq_(done_evts, [{'response': 'dm'}])


def test_peertest_on_timeout_first():
    """
    Test _on_timeout retries if there are retries left
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # We should have retries left
    eq_(helper._retries, 2)

    # Call the time-out handler
    helper._on_timeout()

    # Check the time-out timer is re-started
    assert_is_not_none(helper._timeout_handle)
    eq_(helper._timeout_handle.delay, 0.1)

    # There should now be fewer retries left
    eq_(helper._retries, 1)

    # Helper should have hooked the handler events
    eq_(peer._xidframe_handler, helper._on_receive_xid)
    eq_(peer._frmrframe_handler, helper._on_receive_frmr)
    eq_(peer._dmframe_handler, helper._on_receive_dm)

    # Station should have been asked to send an XID
    eq_(len(peer.transmit_calls), 1)
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a test frame, with CR=True
    eq_(frame, 'xid:cr=True')
    assert_is_none(callback)


def test_peertest_on_timeout_last():
    """
    Test _on_timeout finishes the helper if retries exhausted
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Nothing should be set up
    assert_is_none(helper._timeout_handle)
    assert not helper._done
    eq_(peer.transmit_calls, [])

    # Pretend there are no more retries left
    helper._retries = 0

    # Pretend we're hooked up
    peer._xidframe_handler = helper._on_receive_xid
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = helper._on_receive_dm

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw : done_evts.append(kw))

    # Call the time-out handler
    helper._on_timeout()

    # Check the time-out timer is not re-started
    assert_is_none(helper._timeout_handle)

    # Helper should have hooked the handler events
    assert_is_none(peer._xidframe_handler)
    assert_is_none(peer._frmrframe_handler)
    assert_is_none(peer._dmframe_handler)

    # Station should not have been asked to send anything
    eq_(len(peer.transmit_calls), 0)

    # See that the helper finished
    assert_is(helper._done, True)
    eq_(done_evts, [{'response': 'timeout'}])


def test_peertest_finish_disconnect_xid():
    """
    Test _finish leaves other XID hooks intact
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Pretend we're hooked up
    dummy_xidframe_handler = lambda *a, **kw : None
    peer._xidframe_handler = dummy_xidframe_handler
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = helper._on_receive_dm

    # Call the finish routine
    helper._finish()

    # All except XID (which is not ours) should be disconnected
    eq_(peer._xidframe_handler, dummy_xidframe_handler)
    assert_is_none(peer._frmrframe_handler)
    assert_is_none(peer._dmframe_handler)


def test_peertest_finish_disconnect_frmr():
    """
    Test _finish leaves other FRMR hooks intact
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Pretend we're hooked up
    dummy_frmrframe_handler = lambda *a, **kw : None
    peer._xidframe_handler = helper._on_receive_xid
    peer._frmrframe_handler = dummy_frmrframe_handler
    peer._dmframe_handler = helper._on_receive_dm

    # Call the finish routine
    helper._finish()

    # All except XID (which is not ours) should be disconnected
    assert_is_none(peer._xidframe_handler)
    eq_(peer._frmrframe_handler, dummy_frmrframe_handler)
    assert_is_none(peer._dmframe_handler)


def test_peertest_finish_disconnect_dm():
    """
    Test _finish leaves other DM hooks intact
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = DummyPeer(station, AX25Address('VK4MSL'))
    helper = AX25PeerNegotiationHandler(peer)

    # Pretend we're hooked up
    dummy_dmframe_handler = lambda *a, **kw : None
    peer._xidframe_handler = helper._on_receive_xid
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = dummy_dmframe_handler

    # Call the finish routine
    helper._finish()

    # All except XID (which is not ours) should be disconnected
    assert_is_none(peer._xidframe_handler)
    assert_is_none(peer._frmrframe_handler)
    eq_(peer._dmframe_handler, dummy_dmframe_handler)
