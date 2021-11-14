#!/usr/bin/env python3

"""
Tests for AX25PeerTestHandler
"""

from pytest import approx

from aioax25.peer import AX25PeerTestHandler
from aioax25.frame import AX25Address, AX25TestFrame, AX25Path
from ..mocks import DummyPeer, DummyStation
from .peer import TestingAX25Peer


def test_peertest_go():
    """
    Test _go transmits a test frame with CR=True and starts a timer.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Start it off
    helper._go()
    assert helper._timeout_handle is not None
    assert helper._timeout_handle.delay == 0.1

    assert len(peer.transmit_calls) == 1
    (frame, callback) = peer.transmit_calls.pop(0)

    # Frame should be a test frame, with CR=True
    assert frame is helper.tx_frame
    assert isinstance(frame, AX25TestFrame)
    assert frame.header.cr

    # Callback should be the _transmit_done method
    assert callback == helper._transmit_done

    # We should be registered to receive the reply
    assert peer._testframe_handler is helper


def test_peertest_go_pending():
    """
    Test _go refuses to start if another test frame is pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    # Inject a different helper
    peer._testframe_handler = AX25PeerTestHandler(
        peer, payload=b"test", timeout=0.2
    )

    # Nothing should be set up
    assert helper._timeout_handle is None
    assert not helper._done
    assert peer.transmit_calls == []

    # Start it off
    try:
        helper._go()
        assert False, "Should not have worked"
    except RuntimeError as e:
        if str(e) != "Test frame already pending":
            raise


def test_peertest_transmit_done():
    """
    Test _transmit_done records time of transmission.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    assert helper.tx_time is None
    helper._transmit_done()
    assert helper.tx_time is not None

    assert approx(peer._loop.time()) == helper.tx_time


def test_peertest_on_receive():
    """
    Test _on_receive records time of reception and finishes the helper.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw: done_events.append(kw))

    assert helper.rx_time is None
    helper._on_receive(frame="Make believe TEST frame")
    assert helper.rx_time is not None

    assert approx(peer._loop.time()) == helper.rx_time
    assert helper.rx_frame == "Make believe TEST frame"

    # We should be done now
    assert len(done_events) == 1
    done_evt = done_events.pop()
    assert list(done_evt.keys()) == ["handler"]
    assert done_evt["handler"] is helper


def test_peertest_on_receive_done():
    """
    Test _on_receive ignores packets once done.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    # Mark as done
    helper._done = True

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw: done_events.append(kw))

    assert helper.rx_time is None
    helper._on_receive(frame="Make believe TEST frame")

    assert helper.rx_time is None
    assert helper.rx_frame is None
    assert len(done_events) == 0


def test_peertest_on_timeout():
    """
    Test _on_timeout winds up the handler
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = DummyPeer(station, AX25Address("VK4MSL"))
    helper = AX25PeerTestHandler(peer, payload=b"test", timeout=0.1)

    # Hook the "done" event
    done_events = []
    helper.done_sig.connect(lambda **kw: done_events.append(kw))

    helper._on_timeout()

    # We should be done now
    assert len(done_events) == 1
    done_evt = done_events.pop()
    assert list(done_evt.keys()) == ["handler"]
    assert done_evt["handler"] is helper


# Integration into AX25Peer


def test_peer_ping():
    """
    Test that calling peer.ping() sets up a AX25PeerTestHandler
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the peer's _transmit_frame method
    tx_frames = []

    def _transmit_frame(frame, callback):
        tx_frames.append(frame)
        callback()

    peer._transmit_frame = _transmit_frame

    # Send a ping request
    handler = peer.ping()

    # We should have a reference to the handler
    assert isinstance(handler, AX25PeerTestHandler)

    # Handler should have sent a frame with an empty payload
    assert len(tx_frames) == 1
    assert isinstance(tx_frames[0], AX25TestFrame)
    assert tx_frames[0].payload == b""


def test_peer_ping_payload():
    """
    Test that we can supply a payload to the ping request
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the peer's _transmit_frame method
    tx_frames = []

    def _transmit_frame(frame, callback):
        tx_frames.append(frame)
        callback()

    peer._transmit_frame = _transmit_frame

    # Send a ping request
    handler = peer.ping(payload=b"testing")

    # We should have a reference to the handler
    assert isinstance(handler, AX25PeerTestHandler)

    # Handler should have sent a frame with an empty payload
    assert len(tx_frames) == 1
    assert isinstance(tx_frames[0], AX25TestFrame)
    assert tx_frames[0].payload == b"testing"


def test_peer_ping_cb():
    """
    Test that peer.ping() attaches callback if given
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the peer's _transmit_frame method
    tx_frames = []

    def _transmit_frame(frame, callback):
        tx_frames.append(frame)
        callback()

    peer._transmit_frame = _transmit_frame

    # Create a callback routine
    cb_args = []

    def _callback(*args, **kwargs):
        cb_args.append((args, kwargs))

    # Send a ping request
    handler = peer.ping(callback=_callback)

    # We should have a reference to the handler
    assert isinstance(handler, AX25PeerTestHandler)

    # Pass a reply to the handler to trigger completion
    handler._on_receive(frame=b"test")

    # Our callback should have been called on completion
    assert cb_args == [((), {"handler": handler})]
