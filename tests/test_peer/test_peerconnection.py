#!/usr/bin/env python3

"""
Tests for AX25PeerConnectionHandler
"""

from aioax25.version import AX25Version
from aioax25.peer import AX25PeerConnectionHandler
from aioax25.frame import AX25Address, AX25Path
from .peer import TestingAX25Peer
from ..mocks import DummyPeer, DummyStation


def test_peerconn_go():
    """
    Test _go triggers negotiation if the peer has not yet done so.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Start it off
    helper._go()

    # We should hand off to the negotiation handler, so no timeout started yet:
    assert helper._timeout_handle is None

    # There should be a call to negotiate, with a call-back pointing here.
    assert peer._negotiate_calls == [helper._on_negotiated]


def test_peerconn_go_peer_ax20_stn():
    """
    Test _go skips negotiation for AX.25 2.0 stations.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    station._protocol = AX25Version.AX25_20
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Start it off
    helper._go()

    # Check the time-out timer is started
    assert helper._timeout_handle is not None
    assert helper._timeout_handle.delay == 0.1

    # Helper should have hooked the handler events
    assert peer._uaframe_handler == helper._on_receive_ua
    assert peer._frmrframe_handler == helper._on_receive_frmr
    assert peer._dmframe_handler == helper._on_receive_dm

    # Station should have been asked to send a SABM
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a SABM frame
    assert frame == "sabm"
    assert callback is None


def test_peerconn_go_peer_ax20_peer():
    """
    Test _go skips negotiation for AX.25 2.0 peers.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    peer._protocol = AX25Version.AX25_20
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Start it off
    helper._go()

    # Check the time-out timer is started
    assert helper._timeout_handle is not None
    assert helper._timeout_handle.delay == 0.1

    # Helper should have hooked the handler events
    assert peer._uaframe_handler == helper._on_receive_ua
    assert peer._frmrframe_handler == helper._on_receive_frmr
    assert peer._dmframe_handler == helper._on_receive_dm

    # Station should have been asked to send a SABM
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a SABM frame
    assert frame == "sabm"
    assert callback is None


def test_peerconn_go_prenegotiated():
    """
    Test _go skips negotiation if already completed.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Pretend we've done negotiation
    peer._negotiated = True

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Start it off
    helper._go()

    # Check the time-out timer is started
    assert helper._timeout_handle is not None
    assert helper._timeout_handle.delay == 0.1

    # Helper should have hooked the handler events
    assert peer._uaframe_handler == helper._on_receive_ua
    assert peer._frmrframe_handler == helper._on_receive_frmr
    assert peer._dmframe_handler == helper._on_receive_dm

    # Station should have been asked to send a SABM
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a SABM frame
    assert frame == "sabm"
    assert callback is None


def test_peerconn_on_negotiated_failed():
    """
    Test _on_negotiated winds up the request if negotiation fails.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Try to connect
    helper._on_negotiated("whoopsie")
    assert done_evts == [{"response": "whoopsie"}]


def test_peerconn_on_negotiated_xidframe_handler():
    """
    Test _on_negotiated refuses to run if another UA frame handler is hooked.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Hook the UA handler
    peer._uaframe_handler = lambda *a, **kwa: None

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Try to connect
    helper._on_negotiated("xid")
    assert done_evts == [{"response": "station_busy"}]


def test_peerconn_on_negotiated_frmrframe_handler():
    """
    Test _on_negotiated refuses to run if another FRMR frame handler is hooked.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Hook the FRMR handler
    peer._frmrframe_handler = lambda *a, **kwa: None

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Try to connect
    helper._on_negotiated("xid")
    assert done_evts == [{"response": "station_busy"}]


def test_peerconn_on_negotiated_dmframe_handler():
    """
    Test _on_negotiated refuses to run if another DM frame handler is hooked.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Hook the DM handler
    peer._dmframe_handler = lambda *a, **kwa: None

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Try to connect
    helper._on_negotiated("xid")
    assert done_evts == [{"response": "station_busy"}]


def test_peerconn_on_negotiated_xid():
    """
    Test _on_negotiated triggers SABM transmission on receipt of XID
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Try to connect
    helper._on_negotiated("xid")

    # Helper should not be done
    assert not helper._done

    # Helper should be hooked
    assert peer._uaframe_handler == helper._on_receive_ua
    assert peer._frmrframe_handler == helper._on_receive_frmr
    assert peer._dmframe_handler == helper._on_receive_dm

    # Station should have been asked to send a SABM
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a SABM frame
    assert frame == "sabm"
    assert callback is None


def test_peerconn_receive_ua():
    """
    Test _on_receive_ua ends the helper
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Call _on_receive_ua
    helper._on_receive_ua()

    # See that the helper finished
    assert helper._done is True
    assert done_evts == [{"response": "ack"}]


def test_peerconn_receive_frmr():
    """
    Test _on_receive_frmr ends the helper
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Call _on_receive_frmr
    helper._on_receive_frmr()

    # See that the helper finished
    assert helper._done is True
    assert done_evts == [{"response": "frmr"}]

    # Station should have been asked to send a DM
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a DM frame
    assert frame == "dm"
    assert callback is None


def test_peerconn_receive_dm():
    """
    Test _on_receive_dm ends the helper
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Call _on_receive_frmr
    helper._on_receive_dm()

    # See that the helper finished
    assert helper._done is True
    assert done_evts == [{"response": "dm"}]


def test_peerconn_on_timeout_first():
    """
    Test _on_timeout retries if there are retries left
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # We should have retries left
    assert helper._retries == 2

    # Call the time-out handler
    helper._on_timeout()

    # Check the time-out timer is re-started
    assert helper._timeout_handle is not None
    assert helper._timeout_handle.delay == 0.1

    # There should now be fewer retries left
    assert helper._retries == 1

    # Helper should have hooked the handler events
    assert peer._uaframe_handler == helper._on_receive_ua
    assert peer._frmrframe_handler == helper._on_receive_frmr
    assert peer._dmframe_handler == helper._on_receive_dm

    # Station should have been asked to send an XID
    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a SABM frame
    assert frame == "sabm"
    assert callback is None


def test_peerconn_on_timeout_last():
    """
    Test _on_timeout finishes the helper if retries exhausted
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Pretend there are no more retries left
    helper._retries = 0

    # Pretend we're hooked up
    peer._uaframe_handler = helper._on_receive_ua
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = helper._on_receive_dm

    # Hook the done signal
    done_evts = []
    helper.done_sig.connect(lambda **kw: done_evts.append(kw))

    # Call the time-out handler
    helper._on_timeout()

    # Check the time-out timer is not re-started
    assert helper._timeout_handle is None

    # Helper should have hooked the handler events
    assert peer._uaframe_handler is None
    assert peer._frmrframe_handler is None
    assert peer._dmframe_handler is None

    # Station should not have been asked to send anything
    assert len(peer.transmit_calls) == 0

    # See that the helper finished
    assert helper._done is True
    assert done_evts == [{"response": "timeout"}]


def test_peerconn_finish_disconnect_ua():
    """
    Test _finish leaves other UA hooks intact
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Pretend we're hooked up
    dummy_uaframe_handler = lambda *a, **kw: None
    peer._uaframe_handler = dummy_uaframe_handler
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = helper._on_receive_dm

    # Call the finish routine
    helper._finish()

    # All except UA (which is not ours) should be disconnected
    assert peer._uaframe_handler == dummy_uaframe_handler
    assert peer._frmrframe_handler is None
    assert peer._dmframe_handler is None


def test_peerconn_finish_disconnect_frmr():
    """
    Test _finish leaves other FRMR hooks intact
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Pretend we're hooked up
    dummy_frmrframe_handler = lambda *a, **kw: None
    peer._uaframe_handler = helper._on_receive_ua
    peer._frmrframe_handler = dummy_frmrframe_handler
    peer._dmframe_handler = helper._on_receive_dm

    # Call the finish routine
    helper._finish()

    # All except FRMR (which is not ours) should be disconnected
    assert peer._uaframe_handler is None
    assert peer._frmrframe_handler == dummy_frmrframe_handler
    assert peer._dmframe_handler is None


def test_peerconn_finish_disconnect_dm():
    """
    Test _finish leaves other DM hooks intact
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerConnectionHandler(peer)

    # Pretend we're hooked up
    dummy_dmframe_handler = lambda *a, **kw: None
    peer._uaframe_handler = helper._on_receive_ua
    peer._frmrframe_handler = helper._on_receive_frmr
    peer._dmframe_handler = dummy_dmframe_handler

    # Call the finish routine
    helper._finish()

    # All except DM (which is not ours) should be disconnected
    assert peer._uaframe_handler is None
    assert peer._frmrframe_handler is None
    assert peer._dmframe_handler == dummy_dmframe_handler
