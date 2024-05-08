#!/usr/bin/env python3

"""
Test handling of incoming and outgoing connection logic
"""

from aioax25.version import AX25Version
from aioax25.frame import (
    AX25Address,
    AX25Path,
    AX25DisconnectFrame,
    AX25DisconnectModeFrame,
    AX25FrameRejectFrame,
    AX25UnnumberedAcknowledgeFrame,
    AX25UnnumberedInformationFrame,
    AX25RawFrame,
    AX25TestFrame,
    AX25SetAsyncBalancedModeFrame,
    AX25SetAsyncBalancedModeExtendedFrame,
    AX258BitInformationFrame,
    AX258BitReceiveReadyFrame,
    AX258BitReceiveNotReadyFrame,
    AX258BitRejectFrame,
    AX258BitSelectiveRejectFrame,
    AX2516BitInformationFrame,
    AX2516BitReceiveReadyFrame,
    AX2516BitReceiveNotReadyFrame,
    AX2516BitRejectFrame,
    AX2516BitSelectiveRejectFrame,
)
from aioax25.peer import AX25PeerState
from .peer import TestingAX25Peer
from ..mocks import DummyStation, DummyTimeout

# Connection establishment


def test_connect_not_disconnected():
    """
    Test that calling peer.connect() when not disconnected does nothing.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub negotiation, this should not get called
    def _negotiate(*args, **kwargs):
        assert False, "Should not have been called"

    peer._negotiate = _negotiate

    # Ensure _negotiate() gets called if we try to connect
    peer._negotiated = False

    # Override the state to ensure connection attempt never happens
    peer._state = AX25PeerState.CONNECTED

    # Now try connecting
    peer.connect()


def test_connect_when_disconnected():
    """
    Test that calling peer.connect() when disconnected initiates connection
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub negotiation, we'll just throw an error to see if it gets called
    class ConnectionStarted(Exception):
        pass

    def _negotiate(*args, **kwargs):
        raise ConnectionStarted()

    peer._negotiate = _negotiate

    # Ensure _negotiate() gets called if we try to connect
    peer._negotiated = False

    # Ensure disconnected state
    peer._state = AX25PeerState.DISCONNECTED

    # Now try connecting
    try:
        peer.connect()
        assert False, "Did not call _negotiate"
    except ConnectionStarted:
        pass


# SABM(E) transmission


def test_send_sabm():
    """
    Test we can send a SABM (modulo-8)
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub _transmit_frame
    sent = []

    def _transmit_frame(frame):
        sent.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._send_sabm()

    try:
        frame = sent.pop(0)
    except IndexError:
        assert False, "No frames were sent"

    assert isinstance(frame, AX25SetAsyncBalancedModeFrame)
    assert str(frame.header.destination) == "VK4MSL*"  # CONTROL set
    assert str(frame.header.source) == "VK4MSL-1"  # CONTROL clear
    assert str(frame.header.repeaters) == "VK4RZB"
    assert len(sent) == 0

    assert peer._state == AX25PeerState.CONNECTING


def test_send_sabme():
    """
    Test we can send a SABM (modulo-128)
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )
    peer._modulo128 = True

    # Stub _transmit_frame
    sent = []

    def _transmit_frame(frame):
        sent.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._send_sabm()

    try:
        frame = sent.pop(0)
    except IndexError:
        assert False, "No frames were sent"

    assert isinstance(frame, AX25SetAsyncBalancedModeExtendedFrame)
    assert str(frame.header.destination) == "VK4MSL*"  # CONTROL set
    assert str(frame.header.source) == "VK4MSL-1"  # CONTROL clear
    assert str(frame.header.repeaters) == "VK4RZB"
    assert len(sent) == 0

    assert peer._state == AX25PeerState.CONNECTING


# SABM response handling


def test_recv_ignore_frmr():
    """
    Test that we ignore FRMR from peer when connecting.

    (AX.25 2.2 sect 6.3.1)
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub FRMR handling
    def _on_receive_frmr():
        assert False, "Should not have been called"

    peer._on_receive_frmr = _on_receive_frmr

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    peer._on_receive(
        AX25FrameRejectFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            w=False,
            x=False,
            y=False,
            z=False,
            frmr_cr=False,
            vs=0,
            vr=0,
            frmr_control=0,
        )
    )


def test_recv_ignore_test():
    """
    Test that we ignore TEST from peer when connecting.

    (AX.25 2.2 sect 6.3.1)
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub TEST handling
    def _on_receive_test():
        assert False, "Should not have been called"

    peer._on_receive_test = _on_receive_test

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    peer._on_receive(
        AX25TestFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"Frame to be ignored",
        )
    )


def test_recv_ua():
    """
    Test that UA is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Create a handler for receiving the UA
    count = dict(ua=0)

    def _on_receive_ua():
        count["ua"] += 1

    peer._uaframe_handler = _on_receive_ua

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    peer._on_receive(
        AX25UnnumberedAcknowledgeFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    # Our handler should have been called
    assert count == dict(ua=1)


def test_recv_ui():
    """
    Test that UI is emitted by the received frame signal.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Create a handler for receiving the UI
    rx_frames = []

    def _on_receive_frame(frame, **kwargs):
        assert "peer" in kwargs
        assert kwargs.pop("peer") is peer
        assert kwargs == {}
        rx_frames.append(frame)

    peer.received_frame.connect(_on_receive_frame)

    # Set the state
    peer._state = AX25PeerState.CONNECTED

    # Inject a frame
    frame = AX25UnnumberedInformationFrame(
        destination=AX25Address("VK4MSL-1"),
        source=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        pid=0xF0,
        payload=b"Testing 1 2 3 4",
    )

    peer._on_receive(frame)

    # Our handler should have been called
    assert len(rx_frames) == 1
    assert rx_frames[0] is frame


def test_recv_raw_noconn():
    """
    Test that a raw frame without a connection triggers a DM frame.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _send_dm
    count = dict(send_dm=0)

    def _send_dm():
        count["send_dm"] += 1

    peer._send_dm = _send_dm

    # Set the state
    peer._state = AX25PeerState.DISCONNECTED

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x00\x00Testing 1 2 3 4",
        )
    )


def test_recv_raw_mod8_iframe():
    """
    Test that a I-frame with Mod8 connection is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_iframe
    iframes = []

    def _on_receive_iframe(frame):
        iframes.append(frame)

    peer._on_receive_iframe = _on_receive_iframe

    # Stub _on_receive_sframe
    sframes = []

    def _on_receive_sframe(frame):
        sframes.append(frame)

    peer._on_receive_sframe = _on_receive_sframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # Our I-frame handler should have been called
    assert len(iframes) == 1
    assert isinstance(iframes[0], AX258BitInformationFrame)
    assert iframes[0].pid == 0xF0
    assert iframes[0].payload == b"Testing 1 2 3 4"

    # Our S-frame handler should NOT have been called
    assert sframes == []


def test_recv_raw_mod128_iframe():
    """
    Test that a I-frame with Mod128 connection is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_iframe
    iframes = []

    def _on_receive_iframe(frame):
        iframes.append(frame)

    peer._on_receive_iframe = _on_receive_iframe

    # Stub _on_receive_sframe
    sframes = []

    def _on_receive_sframe(frame):
        sframes.append(frame)

    peer._on_receive_sframe = _on_receive_sframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 128

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x04\x0d\xf0Testing 1 2 3 4",
        )
    )

    # Our I-frame handler should have been called
    assert len(iframes) == 1
    assert isinstance(iframes[0], AX2516BitInformationFrame)
    assert iframes[0].pid == 0xF0
    assert iframes[0].payload == b"Testing 1 2 3 4"

    # Our S-frame handler should NOT have been called
    assert sframes == []


def test_recv_raw_mod8_sframe():
    """
    Test that a S-frame with Mod8 connection is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_iframe
    iframes = []

    def _on_receive_iframe(frame):
        iframes.append(frame)

    peer._on_receive_iframe = _on_receive_iframe

    # Stub _on_receive_sframe
    sframes = []

    def _on_receive_sframe(frame):
        sframes.append(frame)

    peer._on_receive_sframe = _on_receive_sframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x41",
        )
    )

    # Our S-frame handler should have been called
    assert len(sframes) == 1
    assert isinstance(sframes[0], AX258BitReceiveReadyFrame)

    # Our I-frame handler should NOT have been called
    assert iframes == []


def test_recv_raw_mod128_sframe():
    """
    Test that a S-frame with Mod128 connection is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_iframe
    iframes = []

    def _on_receive_iframe(frame):
        iframes.append(frame)

    peer._on_receive_iframe = _on_receive_iframe

    # Stub _on_receive_sframe
    sframes = []

    def _on_receive_sframe(frame):
        sframes.append(frame)

    peer._on_receive_sframe = _on_receive_sframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 128

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x01\x5c",
        )
    )

    # Our S-frame handler should have been called
    assert len(sframes) == 1
    assert isinstance(sframes[0], AX2516BitReceiveReadyFrame)

    # Our I-frame handler should NOT have been called
    assert iframes == []


def test_recv_iframe_busy():
    """
    Test that an I-frame received while we're busy triggers RNR.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _send_rnr_notification and _cancel_rr_notification
    count = dict(send_rnr=0, cancel_rr=0)

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8
    peer._local_busy = True

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be cancelled and there should be a RNR queued
    assert count == dict(cancel_rr=1, send_rnr=1)


def test_recv_iframe_mismatched_seq():
    """
    Test that an I-frame with a mismatched sequence number is dropped.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub the functions called
    count = dict(send_rnr=0, cancel_rr=0, send_next_iframe=0, schedule_rr=0)
    isframes = []
    iframes = []
    state_updates = []

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _schedule_rr_notification():
        count["schedule_rr"] += 1

    peer._schedule_rr_notification = _schedule_rr_notification

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    def _on_receive_isframe_nr_ns(frame):
        isframes.append(frame)

    peer._on_receive_isframe_nr_ns = _on_receive_isframe_nr_ns

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    # Hook received_information signal

    def _received_information(frame, payload, **kwargs):
        assert kwargs == {}
        assert payload == frame.payload
        iframes.append(frame)

    peer.received_information.connect(_received_information)

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be cancelled, no other actions pending
    assert count == dict(
        cancel_rr=1, send_rnr=0, schedule_rr=0, send_next_iframe=0
    )

    assert isframes == []
    assert iframes == []
    assert state_updates == []


def test_recv_iframe_mismatched_seq():
    """
    Test that an I-frame with a mismatched sequence number is dropped.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub the functions called
    count = dict(send_rnr=0, cancel_rr=0, send_next_iframe=0, schedule_rr=0)
    isframes = []
    iframes = []
    state_updates = []

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _schedule_rr_notification():
        count["schedule_rr"] += 1

    peer._schedule_rr_notification = _schedule_rr_notification

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    def _on_receive_isframe_nr_ns(frame):
        isframes.append(frame)

    peer._on_receive_isframe_nr_ns = _on_receive_isframe_nr_ns

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    # Hook received_information signal

    def _received_information(frame, payload, **kwargs):
        assert kwargs == {}
        assert payload == frame.payload
        iframes.append(frame)

    peer.received_information.connect(_received_information)

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be cancelled, no other actions pending
    assert count == dict(
        cancel_rr=1, send_rnr=0, schedule_rr=0, send_next_iframe=0
    )

    assert isframes == []
    assert iframes == []
    assert state_updates == []


def test_recv_iframe_matched_seq_nopending():
    """
    Test that an I-frame with a matched sequence number is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub the functions called
    count = dict(send_rnr=0, cancel_rr=0, send_next_iframe=0, schedule_rr=0)
    isframes = []
    iframes = []
    state_updates = []

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _schedule_rr_notification():
        count["schedule_rr"] += 1

    peer._schedule_rr_notification = _schedule_rr_notification

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    def _on_receive_isframe_nr_ns(frame):
        isframes.append(frame)

    peer._on_receive_isframe_nr_ns = _on_receive_isframe_nr_ns

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    # Hook received_information signal

    def _received_information(frame, payload, **kwargs):
        assert kwargs == {}
        assert payload == frame.payload
        iframes.append(frame)

    peer.received_information.connect(_received_information)

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8
    peer._recv_seq = 2

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be re-scheduled, no I-frame transmissions
    assert count == dict(
        cancel_rr=1, send_rnr=0, schedule_rr=1, send_next_iframe=0
    )

    assert len(isframes) == 1

    frame = isframes.pop(0)
    assert frame.pid == 0xF0
    assert frame.payload == b"Testing 1 2 3 4"

    assert iframes == [frame]
    assert state_updates == [
        {"comment": "from I-frame N(S)", "prop": "_recv_state", "value": 3}
    ]


def test_recv_iframe_matched_seq_lotspending():
    """
    Test that an I-frame with lots of pending I-frames sends RR instead.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub the functions called
    count = dict(send_rnr=0, cancel_rr=0, send_next_iframe=0, schedule_rr=0)
    isframes = []
    iframes = []
    state_updates = []

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _schedule_rr_notification():
        count["schedule_rr"] += 1

    peer._schedule_rr_notification = _schedule_rr_notification

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    def _on_receive_isframe_nr_ns(frame):
        isframes.append(frame)

    peer._on_receive_isframe_nr_ns = _on_receive_isframe_nr_ns

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    # Hook received_information signal

    def _received_information(frame, payload, **kwargs):
        assert kwargs == {}
        assert payload == frame.payload
        iframes.append(frame)

    peer.received_information.connect(_received_information)

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8
    peer._max_outstanding = 8
    peer._recv_seq = 2
    peer._pending_data = [(0xF0, b"Test outgoing")]
    peer._pending_iframes = {
        0: (0xF0, b"Test outgoing 1"),
        1: (0xF0, b"Test outgoing 2"),
        2: (0xF0, b"Test outgoing 3"),
        3: (0xF0, b"Test outgoing 4"),
        4: (0xF0, b"Test outgoing 5"),
        5: (0xF0, b"Test outgoing 6"),
        6: (0xF0, b"Test outgoing 7"),
        7: (0xF0, b"Test outgoing 8"),
    }

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be re-scheduled, no I-frame transmissions
    assert count == dict(
        cancel_rr=1, send_rnr=0, schedule_rr=1, send_next_iframe=0
    )

    assert len(isframes) == 1

    frame = isframes.pop(0)
    assert frame.pid == 0xF0
    assert frame.payload == b"Testing 1 2 3 4"

    assert iframes == [frame]
    assert state_updates == [
        {"comment": "from I-frame N(S)", "prop": "_recv_state", "value": 3}
    ]


def test_recv_iframe_matched_seq_iframepending():
    """
    Test that an I-frame reception triggers I-frame transmission if data is
    pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub the functions called
    count = dict(send_rnr=0, cancel_rr=0, send_next_iframe=0, schedule_rr=0)
    isframes = []
    iframes = []
    state_updates = []

    def _cancel_rr_notification():
        count["cancel_rr"] += 1

    peer._cancel_rr_notification = _cancel_rr_notification

    def _schedule_rr_notification():
        count["schedule_rr"] += 1

    peer._schedule_rr_notification = _schedule_rr_notification

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _send_rnr_notification():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr_notification

    def _on_receive_isframe_nr_ns(frame):
        isframes.append(frame)

    peer._on_receive_isframe_nr_ns = _on_receive_isframe_nr_ns

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    # Hook received_information signal

    def _received_information(frame, payload, **kwargs):
        assert kwargs == {}
        assert payload == frame.payload
        iframes.append(frame)

    peer.received_information.connect(_received_information)

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._modulo = 8
    peer._max_outstanding = 8
    peer._recv_seq = 2
    peer._pending_data = [(0xF0, b"Test outgoing")]

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\xd4\xf0Testing 1 2 3 4",
        )
    )

    # RR notification should be cancelled, no I-frame transmissions
    assert count == dict(
        cancel_rr=1, send_rnr=0, schedule_rr=0, send_next_iframe=1
    )

    assert len(isframes) == 1

    frame = isframes.pop(0)
    assert frame.pid == 0xF0
    assert frame.payload == b"Testing 1 2 3 4"

    assert iframes == [frame]
    assert state_updates == [
        {"comment": "from I-frame N(S)", "prop": "_recv_state", "value": 3}
    ]


def test_recv_sframe_rr_req_busy():
    """
    Test that RR with P/F set while busy sends RNR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = True

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x51",
        )
    )

    # We should send a RNR in reply
    assert count == dict(send_rr=0, send_rnr=1, send_next_iframe=0)


def test_recv_sframe_rr_req_notbusy():
    """
    Test that RR with P/F set while not busy sends RR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = False

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x51",
        )
    )

    # We should send a RR in reply
    assert count == dict(send_rr=1, send_rnr=0, send_next_iframe=0)


def test_recv_sframe_rr_rep():
    """
    Test that RR with P/F clear marks peer not busy
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._peer_busy = True

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x41",
        )
    )

    # Busy flag should be cleared
    assert peer._peer_busy is False

    # We should send the next I-frame in reply
    assert count == dict(send_rr=0, send_rnr=0, send_next_iframe=1)


def test_recv_sframe_rnr_req_busy():
    """
    Test that RNR with P/F set while busy sends RNR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = True

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x55",
        )
    )

    # We should send a RNR in reply
    assert count == dict(send_rr=0, send_rnr=1, send_next_iframe=0)


def test_recv_sframe_rnr_req_notbusy():
    """
    Test that RNR with P/F set while not busy sends RR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = False

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x55",
        )
    )

    # We should send a RR in reply
    assert count == dict(send_rr=1, send_rnr=0, send_next_iframe=0)


def test_recv_sframe_rnr_rep():
    """
    Test that RNR with P/F clear marks peer busy
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._peer_busy = False

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x45",
        )
    )

    # Busy flag should be set
    assert peer._peer_busy is True


def test_recv_sframe_rej_req_busy():
    """
    Test that REJ with P/F set while busy sends RNR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)
    state_updates = []

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)
        setattr(
            peer,
            prop,
            kwargs.get("value", getattr(peer, prop)) + kwargs.get("delta", 0),
        )

    peer._update_state = _update_state

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = True

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x59",
        )
    )

    # We should update due to resets and peer ACKs
    assert state_updates == [
        {"comment": "reset", "prop": "_send_state", "value": 0},
        {"comment": "reset", "prop": "_send_seq", "value": 0},
        {"comment": "reset", "prop": "_recv_state", "value": 0},
        {"comment": "reset", "prop": "_recv_seq", "value": 0},
        {"comment": "reset", "prop": "_ack_state", "value": 0},
        {"comment": "ACKed by peer N(R)", "delta": 1, "prop": "_ack_state"},
    ]

    # We should send a RNR in reply
    assert count == dict(send_rr=0, send_rnr=1, send_next_iframe=0)


def test_recv_sframe_rej_req_notbusy():
    """
    Test that REJ with P/F set while not busy sends RR
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)
    state_updates = []

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)
        setattr(
            peer,
            prop,
            kwargs.get("value", getattr(peer, prop)) + kwargs.get("delta", 0),
        )

    peer._update_state = _update_state

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._local_busy = False

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x59",
        )
    )

    # State updates should be a reset and peer ACK
    assert state_updates == [
        {"comment": "reset", "prop": "_send_state", "value": 0},
        {"comment": "reset", "prop": "_send_seq", "value": 0},
        {"comment": "reset", "prop": "_recv_state", "value": 0},
        {"comment": "reset", "prop": "_recv_seq", "value": 0},
        {"comment": "reset", "prop": "_ack_state", "value": 0},
        {"comment": "ACKed by peer N(R)", "delta": 1, "prop": "_ack_state"},
    ]

    # We should send a RR in reply
    assert count == dict(send_rr=1, send_rnr=0, send_next_iframe=0)


def test_recv_sframe_rej_rep():
    """
    Test that REJ with P/F clear marks peer busy
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    count = dict(send_rr=0, send_rnr=0, send_next_iframe=0)
    state_updates = []

    def _send_rr():
        count["send_rr"] += 1

    peer._send_rr_notification = _send_rr

    def _send_rnr():
        count["send_rnr"] += 1

    peer._send_rnr_notification = _send_rnr

    def _send_next_iframe():
        count["send_next_iframe"] += 1

    peer._send_next_iframe = _send_next_iframe

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)
        setattr(
            peer,
            prop,
            kwargs.get("value", getattr(peer, prop)) + kwargs.get("delta", 0),
        )

    peer._update_state = _update_state

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(False)
    peer._peer_busy = False

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x49",
        )
    )

    assert state_updates == [
        # Reset state
        {"comment": "reset", "prop": "_send_state", "value": 0},
        {"comment": "reset", "prop": "_send_seq", "value": 0},
        {"comment": "reset", "prop": "_recv_state", "value": 0},
        {"comment": "reset", "prop": "_recv_seq", "value": 0},
        {"comment": "reset", "prop": "_ack_state", "value": 0},
        # Peer ACK
        {"comment": "ACKed by peer N(R)", "delta": 1, "prop": "_ack_state"},
        # REJ handling
        {"comment": "from REJ N(R)", "prop": "_send_state", "value": 2},
    ]

    # We should send an I-frame in reply
    assert count == dict(send_rr=0, send_rnr=0, send_next_iframe=1)


def test_recv_sframe_srej_pf():
    """
    Test that REJ with P/F set retransmits specified frame
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    iframes_rqd = []

    def _transmit_iframe(nr):
        iframes_rqd.append(nr)

    peer._transmit_iframe = _transmit_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(True)

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x0d\x55",
        )
    )

    assert iframes_rqd == [42]


def test_recv_sframe_srej_nopf():
    """
    Test that REJ with P/F clear retransmits specified frame
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub the functions called
    iframes_rqd = []

    def _transmit_iframe(nr):
        iframes_rqd.append(nr)

    peer._transmit_iframe = _transmit_iframe

    # Set the state
    peer._state = AX25PeerState.CONNECTED
    peer._init_connection(True)

    # Inject a frame
    peer._on_receive(
        AX25RawFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
            payload=b"\x0d\x54",
        )
    )

    assert iframes_rqd == [42]


def test_recv_disc():
    """
    Test that DISC is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _send_ua and _on_disconnect
    count = dict(send_ua=0, on_disc=0)

    def _send_ua():
        count["send_ua"] += 1

    peer._send_ua = _send_ua

    def _on_disconnect():
        count["on_disc"] += 1

    peer._on_disconnect = _on_disconnect

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    peer._on_receive(
        AX25DisconnectFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    # Our handlers should have been called
    assert count == dict(send_ua=1, on_disc=1)


def test_recv_dm():
    """
    Test that DM is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _dmframe_handler and _on_disconnect
    count = dict(dmframe_handler=0)

    def _dmframe_handler():
        count["dmframe_handler"] += 1

    peer._dmframe_handler = _dmframe_handler

    def _on_disconnect():
        assert False, "_dmframe_handler should not have been called"

    peer._on_disconnect = _on_disconnect

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    peer._on_receive(
        AX25DisconnectModeFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    # Our handler should have been called
    assert count == dict(dmframe_handler=1)

    # We should have removed the DM frame handler
    assert peer._dmframe_handler is None


def test_recv_sabm():
    """
    Test that SABM is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_sabm, we'll test it fully later
    frames = []

    def _on_receive_sabm(frame):
        frames.append(frame)

    peer._on_receive_sabm = _on_receive_sabm

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    frame = AX25SetAsyncBalancedModeFrame(
        destination=AX25Address("VK4MSL-1"),
        source=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
    )
    peer._on_receive(frame)

    assert frames == [frame]


def test_recv_sabme():
    """
    Test that SABME is handled.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub idle time-out handling
    peer._reset_idle_timeout = lambda: None

    # Stub _on_receive_sabm, we'll test it fully later
    frames = []

    def _on_receive_sabm(frame):
        frames.append(frame)

    peer._on_receive_sabm = _on_receive_sabm

    # Set the state
    peer._state = AX25PeerState.CONNECTING

    # Inject a frame
    frame = AX25SetAsyncBalancedModeExtendedFrame(
        destination=AX25Address("VK4MSL-1"),
        source=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
    )
    peer._on_receive(frame)

    assert frames == [frame]


# RR Notification transmission, scheduling and cancellation


def test_cancel_rr_notification_notpending():
    """
    Test _cancel_rr_notification does nothing if not pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    assert peer._rr_notification_timeout_handle is None

    peer._cancel_rr_notification()

    assert peer._rr_notification_timeout_handle is None


def test_cancel_rr_notification_ispending():
    """
    Test _cancel_rr_notification cancels a pending notification.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    timeout = DummyTimeout(0, lambda: None)
    peer._rr_notification_timeout_handle = timeout

    peer._cancel_rr_notification()

    assert peer._rr_notification_timeout_handle is None
    assert timeout.cancelled is True


def test_schedule_rr_notification():
    """
    Test _schedule_rr_notification schedules a notification.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._schedule_rr_notification()

    assert peer._rr_notification_timeout_handle is not None


def test_send_rr_notification_connected():
    """
    Test _send_rr_notification sends a notification if connected.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._state = AX25PeerState.CONNECTED

    peer._send_rr_notification()

    assert count == dict(update_recv_seq=1)
    assert len(transmitted) == 1
    assert isinstance(transmitted[0], AX258BitReceiveReadyFrame)


def test_send_rr_notification_disconnected():
    """
    Test _send_rr_notification sends a notification if connected.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._state = AX25PeerState.DISCONNECTED

    peer._send_rr_notification()

    assert count == dict(update_recv_seq=0)
    assert len(transmitted) == 0


# RNR transmission


def test_send_rnr_notification_connected():
    """
    Test _send_rnr_notification sends a notification if connected.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._state = AX25PeerState.CONNECTED

    peer._send_rnr_notification()

    assert count == dict(update_recv_seq=1)
    assert len(transmitted) == 1
    assert isinstance(transmitted[0], AX258BitReceiveNotReadyFrame)


def test_send_rnr_notification_connected_recent():
    """
    Test _send_rnr_notification skips notification if the last was recent.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._state = AX25PeerState.CONNECTED
    peer._last_rnr_sent = peer._loop.time() - (peer._rnr_interval / 2)

    peer._send_rnr_notification()

    assert count == dict(update_recv_seq=0)
    assert len(transmitted) == 0


def test_send_rnr_notification_disconnected():
    """
    Test _send_rnr_notification sends a notification if connected.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    peer._state = AX25PeerState.DISCONNECTED

    peer._send_rnr_notification()

    assert count == dict(update_recv_seq=0)
    assert len(transmitted) == 0


# I-Frame transmission


def test_send_next_iframe_max_outstanding():
    """
    Test I-frame transmission is suppressed if too many frames are pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_send_seq=0, update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    def _update_send_seq():
        count["update_send_seq"] += 1

    peer._update_send_seq = _update_send_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    state_updates = []

    def _update_state(**kwargs):
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._state = AX25PeerState.CONNECTED
    peer._pending_iframes = {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
        4: (0xF0, b"Frame 5"),
        5: (0xF0, b"Frame 6"),
        6: (0xF0, b"Frame 7"),
        7: (0xF0, b"Frame 8"),
    }
    peer._max_outstanding = 8

    peer._send_next_iframe()

    assert count == dict(update_send_seq=0, update_recv_seq=0)
    assert state_updates == []
    assert transmitted == []


def test_send_next_iframe_nothing_pending():
    """
    Test I-frame transmission is suppressed no data is pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_send_seq=0, update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    def _update_send_seq():
        count["update_send_seq"] += 1

    peer._update_send_seq = _update_send_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    state_updates = []

    def _update_state(**kwargs):
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._state = AX25PeerState.CONNECTED
    peer._pending_iframes = {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
    }
    peer._max_outstanding = 8
    peer._send_state = 4

    peer._send_next_iframe()

    assert count == dict(update_send_seq=0, update_recv_seq=0)
    assert state_updates == []
    assert transmitted == []


def test_send_next_iframe_create_next():
    """
    Test I-frame transmission creates a new I-frame if there's data to send.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_send_seq=0, update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    def _update_send_seq():
        count["update_send_seq"] += 1

    peer._update_send_seq = _update_send_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    state_updates = []

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._state = AX25PeerState.CONNECTED
    peer._pending_iframes = {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
    }
    peer._pending_data = [
        (0xF0, b"Frame 5"),
    ]
    peer._max_outstanding = 8
    peer._send_state = 4

    peer._send_next_iframe()

    assert peer._pending_iframes == {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
        4: (0xF0, b"Frame 5"),
    }
    assert peer._pending_data == []
    assert count == dict(update_send_seq=1, update_recv_seq=1)
    assert state_updates == [
        dict(prop="_send_state", delta=1, comment="send next I-frame")
    ]
    assert transmitted[1:] == []
    frame = transmitted.pop(0)
    assert isinstance(frame, AX258BitInformationFrame)
    assert frame.payload == b"Frame 5"


def test_send_next_iframe_existing_next():
    """
    Test I-frame transmission sends existing next frame.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    peer._init_connection(False)

    count = dict(update_send_seq=0, update_recv_seq=0)

    def _update_recv_seq():
        count["update_recv_seq"] += 1

    peer._update_recv_seq = _update_recv_seq

    def _update_send_seq():
        count["update_send_seq"] += 1

    peer._update_send_seq = _update_send_seq

    transmitted = []

    def _transmit_frame(frame):
        transmitted.append(frame)

    peer._transmit_frame = _transmit_frame

    state_updates = []

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._state = AX25PeerState.CONNECTED
    peer._pending_iframes = {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
    }
    peer._pending_data = [
        (0xF0, b"Frame 5"),
    ]
    peer._max_outstanding = 8
    peer._send_state = 3

    peer._send_next_iframe()

    assert peer._pending_iframes == {
        0: (0xF0, b"Frame 1"),
        1: (0xF0, b"Frame 2"),
        2: (0xF0, b"Frame 3"),
        3: (0xF0, b"Frame 4"),
    }
    assert peer._pending_data == [
        (0xF0, b"Frame 5"),
    ]
    assert count == dict(update_send_seq=1, update_recv_seq=1)
    assert state_updates == [
        dict(prop="_send_state", delta=1, comment="send next I-frame")
    ]
    assert transmitted[1:] == []
    frame = transmitted.pop(0)
    assert isinstance(frame, AX258BitInformationFrame)
    assert frame.payload == b"Frame 4"


# Sequence number state updates


def test_update_send_seq():
    """
    Test _update_send_seq copies V(S) to N(S).
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    state_updates = []

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._send_seq = 2
    peer._send_state = 6

    peer._update_send_seq()
    assert state_updates == [
        dict(prop="_send_seq", value=6, comment="from V(S)")
    ]


def test_update_recv_seq():
    """
    Test _update_recv_seq copies V(R) to N(R).
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path(),
    )

    state_updates = []

    def _update_state(prop, **kwargs):
        kwargs["prop"] = prop
        state_updates.append(kwargs)

    peer._update_state = _update_state

    peer._recv_state = 6
    peer._recv_seq = 2

    peer._update_recv_seq()
    assert state_updates == [
        dict(prop="_recv_seq", value=6, comment="from V(R)")
    ]


# SABM(E) handling


def test_on_receive_sabm_while_connecting():
    """
    Test that SABM is handled safely while UA from SABM pending
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Assume we're already connecting to the station
    peer._state = AX25PeerState.CONNECTING

    # Stub _init_connection
    count = dict(init=0, sabmframe_handler=0)

    def _init_connection(extended):
        assert extended is False
        count["init"] += 1

    peer._init_connection = _init_connection

    # Stub _sabmframe_handler
    def _sabmframe_handler():
        count["sabmframe_handler"] += 1

    peer._sabmframe_handler = _sabmframe_handler

    # Stub _start_connect_ack_timer
    def _start_connect_ack_timer():
        assert False, "Should not be starting connect timer"

    peer._start_connect_ack_timer = _start_connect_ack_timer

    # Hook connection request event
    def _on_conn_rq(**kwargs):
        assert False, "Should not be reporting connection attempt"

    station.connection_request.connect(_on_conn_rq)

    peer._on_receive_sabm(
        AX25SetAsyncBalancedModeFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    assert count == dict(init=1, sabmframe_handler=1)


def test_on_receive_sabme_init():
    """
    Test the incoming connection is initialised on receipt of SABME.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Assume we know it's an AX.25 2.2 peer
    peer._protocol = AX25Version.AX25_22

    # Stub _init_connection
    count = dict(init=0, start_timer=0, conn_rq=0)

    def _init_connection(extended):
        assert extended is True
        count["init"] += 1

    peer._init_connection = _init_connection

    # Stub _sabmframe_handler
    def _sabmframe_handler():
        assert False, "We should be handling the SABM(E) ourselves"

    peer._sabmframe_handler = _sabmframe_handler

    # Stub _start_connect_ack_timer
    def _start_connect_ack_timer():
        count["start_timer"] += 1

    peer._start_connect_ack_timer = _start_connect_ack_timer

    # Hook connection request event
    def _on_conn_rq(**kwargs):
        assert kwargs == dict(peer=peer)
        count["conn_rq"] += 1

    station.connection_request.connect(_on_conn_rq)

    peer._on_receive_sabm(
        AX25SetAsyncBalancedModeExtendedFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    assert count == dict(init=1, start_timer=1, conn_rq=1)


def test_on_receive_sabme_init_unknown_peer_ver():
    """
    Test we switch the peer to AX.25 2.2 mode on receipt of SABME
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Assume we do not know the peer's AX.25 version
    peer._protocol = AX25Version.UNKNOWN

    # Stub _init_connection
    count = dict(init=0, start_timer=0, conn_rq=0)

    def _init_connection(extended):
        assert extended is True
        count["init"] += 1

    peer._init_connection = _init_connection

    # Stub _start_connect_ack_timer
    def _start_connect_ack_timer():
        count["start_timer"] += 1

    peer._start_connect_ack_timer = _start_connect_ack_timer

    # Hook connection request event
    def _on_conn_rq(**kwargs):
        assert kwargs == dict(peer=peer)
        count["conn_rq"] += 1

    station.connection_request.connect(_on_conn_rq)

    peer._on_receive_sabm(
        AX25SetAsyncBalancedModeExtendedFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    assert peer._protocol == AX25Version.AX25_22


def test_on_receive_sabme_ax25_20_station():
    """
    Test we reject SABME if station is in AX.25 2.0 mode
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set AX.25 2.0 mode on the station
    station._protocol = AX25Version.AX25_20

    # Stub _send_frmr
    frmr = []

    def _send_frmr(frame, **kwargs):
        frmr.append((frame, kwargs))

    peer._send_frmr = _send_frmr

    # Stub _init_connection
    def _init_connection(extended):
        assert False, "Should not have been called"

    peer._init_connection = _init_connection

    # Stub _start_connect_ack_timer
    def _start_connect_ack_timer():
        assert False, "Should not have been called"

    peer._start_connect_ack_timer = _start_connect_ack_timer

    # Hook connection request event
    def _on_conn_rq(**kwargs):
        assert False, "Should not have been called"

    station.connection_request.connect(_on_conn_rq)

    frame = AX25SetAsyncBalancedModeExtendedFrame(
        destination=AX25Address("VK4MSL-1"),
        source=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
    )
    peer._on_receive_sabm(frame)

    assert frmr == [(frame, dict(w=True))]


def test_on_receive_sabme_ax25_20_peer():
    """
    Test we reject SABME if peer not in AX.25 2.2 mode
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Assume the peer runs AX.25 2.0
    peer._protocol = AX25Version.AX25_20

    # Stub _send_dm
    count = dict(send_dm=0)

    def _send_dm():
        count["send_dm"] += 1

    peer._send_dm = _send_dm

    # Stub _init_connection
    def _init_connection(extended):
        assert False, "Should not have been called"

    peer._init_connection = _init_connection

    # Stub _start_connect_ack_timer
    def _start_connect_ack_timer():
        assert False, "Should not have been called"

    peer._start_connect_ack_timer = _start_connect_ack_timer

    # Hook connection request event
    def _on_conn_rq(**kwargs):
        assert False, "Should not have been called"

    station.connection_request.connect(_on_conn_rq)

    peer._on_receive_sabm(
        AX25SetAsyncBalancedModeExtendedFrame(
            destination=AX25Address("VK4MSL-1"),
            source=AX25Address("VK4MSL"),
            repeaters=AX25Path("VK4RZB"),
        )
    )

    assert count == dict(send_dm=1)


# Connection initialisation


def test_init_connection_mod8():
    """
    Test _init_connection can initialise a standard mod-8 connection.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set some dummy data in fields -- this should be cleared out or set
    # to sane values.
    ack_timer = DummyTimeout(None, None)
    peer._send_state = 1
    peer._send_seq = 2
    peer._recv_state = 3
    peer._recv_seq = 4
    peer._ack_state = 5
    peer._modulo = 6
    peer._max_outstanding = 7
    peer._IFrameClass = None
    peer._RRFrameClass = None
    peer._RNRFrameClass = None
    peer._REJFrameClass = None
    peer._SREJFrameClass = None
    peer._pending_iframes = dict(comment="pending data")
    peer._pending_data = ["pending data"]

    peer._init_connection(extended=False)

    # These should be set for a Mod-8 connection
    assert peer._max_outstanding == 7
    assert peer._modulo == 8
    assert peer._IFrameClass is AX258BitInformationFrame
    assert peer._RRFrameClass is AX258BitReceiveReadyFrame
    assert peer._RNRFrameClass is AX258BitReceiveNotReadyFrame
    assert peer._REJFrameClass is AX258BitRejectFrame
    assert peer._SREJFrameClass is AX258BitSelectiveRejectFrame

    # These should be initialised to initial state
    assert peer._send_state == 0
    assert peer._send_seq == 0
    assert peer._recv_state == 0
    assert peer._recv_seq == 0
    assert peer._ack_state == 0
    assert peer._pending_iframes == {}
    assert peer._pending_data == []


def test_init_connection_mod128():
    """
    Test _init_connection can initialise a mod-128 connection.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set some dummy data in fields -- this should be cleared out or set
    # to sane values.
    ack_timer = DummyTimeout(None, None)
    peer._send_state = 1
    peer._send_seq = 2
    peer._recv_state = 3
    peer._recv_seq = 4
    peer._ack_state = 5
    peer._modulo = 6
    peer._max_outstanding = 7
    peer._IFrameClass = None
    peer._RRFrameClass = None
    peer._RNRFrameClass = None
    peer._REJFrameClass = None
    peer._SREJFrameClass = None
    peer._pending_iframes = dict(comment="pending data")
    peer._pending_data = ["pending data"]

    peer._init_connection(extended=True)

    # These should be set for a Mod-128 connection
    assert peer._max_outstanding == 127
    assert peer._modulo == 128
    assert peer._IFrameClass is AX2516BitInformationFrame
    assert peer._RRFrameClass is AX2516BitReceiveReadyFrame
    assert peer._RNRFrameClass is AX2516BitReceiveNotReadyFrame
    assert peer._REJFrameClass is AX2516BitRejectFrame
    assert peer._SREJFrameClass is AX2516BitSelectiveRejectFrame

    # These should be initialised to initial state
    assert peer._send_state == 0
    assert peer._send_seq == 0
    assert peer._recv_state == 0
    assert peer._recv_seq == 0
    assert peer._ack_state == 0
    assert peer._pending_iframes == {}
    assert peer._pending_data == []


# Connection acceptance and rejection handling


def test_accept_connected_noop():
    """
    Test calling .accept() while not receiving a connection is a no-op.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.CONNECTED

    # Stub functions that should not be called
    def _stop_ack_timer():
        assert False, "Should not have stopped connect timer"

    peer._stop_ack_timer = _stop_ack_timer

    def _send_ua():
        assert False, "Should not have sent UA"

    peer._send_ua = _send_ua

    # Try accepting a ficticious connection
    peer.accept()

    assert peer._state == AX25PeerState.CONNECTED


def test_accept_incoming_ua():
    """
    Test calling .accept() with incoming connection sends UA then SABM.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.INCOMING_CONNECTION

    # Stub functions that should be called
    actions = []

    def _stop_ack_timer():
        actions.append("stop-connect-timer")

    peer._stop_ack_timer = _stop_ack_timer

    def _send_ua():
        # At this time, we should be in the INCOMING_CONNECTION state
        assert peer._state is AX25PeerState.INCOMING_CONNECTION
        actions.append("sent-ua")

    peer._send_ua = _send_ua

    # Try accepting a ficticious connection
    peer.accept()

    assert peer._state is AX25PeerState.CONNECTED
    assert actions == ["stop-connect-timer", "sent-ua"]
    assert peer._uaframe_handler is None


def test_reject_connected_noop():
    """
    Test calling .reject() while not receiving a connection is a no-op.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.CONNECTED

    # Stub functions that should not be called
    def _stop_ack_timer():
        assert False, "Should not have stopped connect timer"

    peer._stop_ack_timer = _stop_ack_timer

    def _send_dm():
        assert False, "Should not have sent DM"

    peer._send_dm = _send_dm

    # Try rejecting a ficticious connection
    peer.reject()

    assert peer._state == AX25PeerState.CONNECTED


def test_reject_incoming_dm():
    """
    Test calling .reject() with no incoming connection is a no-op.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.INCOMING_CONNECTION

    # Stub functions that should be called
    actions = []

    def _stop_ack_timer():
        actions.append("stop-connect-timer")

    peer._stop_ack_timer = _stop_ack_timer

    def _send_dm():
        actions.append("sent-dm")

    peer._send_dm = _send_dm

    # Try rejecting a ficticious connection
    peer.reject()

    assert peer._state == AX25PeerState.DISCONNECTED
    assert actions == ["stop-connect-timer", "sent-dm"]


# Connection closure


def test_disconnect_disconnected_noop():
    """
    Test calling .disconnect() while not connected is a no-op.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.CONNECTING

    # A dummy UA handler
    def _dummy_ua_handler():
        assert False, "Should not get called"

    peer._uaframe_handler = _dummy_ua_handler

    # Stub functions that should not be called
    def _send_disc():
        assert False, "Should not have sent DISC frame"

    peer._send_disc = _send_disc

    def _start_disconnect_ack_timer():
        assert False, "Should not have started disconnect timer"

    peer._start_disconnect_ack_timer = _start_disconnect_ack_timer

    # Try disconnecting a ficticious connection
    peer.disconnect()

    assert peer._state == AX25PeerState.CONNECTING
    assert peer._uaframe_handler == _dummy_ua_handler


def test_disconnect_connected_disc():
    """
    Test calling .disconnect() while connected sends a DISC.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Set the state to known value
    peer._state = AX25PeerState.CONNECTED

    # A dummy UA handler
    def _dummy_ua_handler():
        assert False, "Should not get called"

    peer._uaframe_handler = _dummy_ua_handler

    # Stub functions that should be called
    actions = []

    def _send_disc():
        actions.append("sent-disc")

    peer._send_disc = _send_disc

    def _start_disconnect_ack_timer():
        actions.append("start-ack-timer")

    peer._start_disconnect_ack_timer = _start_disconnect_ack_timer

    # Try disconnecting a ficticious connection
    peer.disconnect()

    assert peer._state == AX25PeerState.DISCONNECTING
    assert actions == ["sent-disc", "start-ack-timer"]
    assert peer._uaframe_handler == peer._on_disconnect


# ACK timer handling


def test_start_connect_ack_timer():
    """
    Test _start_connect_ack_timer schedules _on_incoming_connect_timeout
    to fire after _ack_timeout.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    count = dict(on_incoming_connect_timeout=0, on_disc_ua_timeout=0)

    def _on_incoming_connect_timeout():
        count["on_incoming_connect_timeout"] += 1

    peer._on_incoming_connect_timeout = _on_incoming_connect_timeout

    def _on_disc_ua_timeout():
        count["on_disc_ua_timeout"] += 1

    peer._on_disc_ua_timeout = _on_disc_ua_timeout

    assert peer._ack_timeout_handle is None

    peer._start_connect_ack_timer()

    assert peer._ack_timeout_handle is not None
    assert peer._ack_timeout_handle.delay == peer._ack_timeout

    assert count == dict(on_incoming_connect_timeout=0, on_disc_ua_timeout=0)
    peer._ack_timeout_handle.callback()
    assert count == dict(on_incoming_connect_timeout=1, on_disc_ua_timeout=0)


def test_start_disconnect_ack_timer():
    """
    Test _start_disconnect_ack_timer schedules _on_disc_ua_timeout
    to fire after _ack_timeout.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    count = dict(on_incoming_connect_timeout=0, on_disc_ua_timeout=0)

    def _on_incoming_connect_timeout():
        count["on_incoming_connect_timeout"] += 1

    peer._on_incoming_connect_timeout = _on_incoming_connect_timeout

    def _on_disc_ua_timeout():
        count["on_disc_ua_timeout"] += 1

    peer._on_disc_ua_timeout = _on_disc_ua_timeout

    assert peer._ack_timeout_handle is None

    peer._start_disconnect_ack_timer()

    assert peer._ack_timeout_handle is not None
    assert peer._ack_timeout_handle.delay == peer._ack_timeout

    assert count == dict(on_incoming_connect_timeout=0, on_disc_ua_timeout=0)
    peer._ack_timeout_handle.callback()
    assert count == dict(on_incoming_connect_timeout=0, on_disc_ua_timeout=1)


def test_stop_ack_timer_existing():
    """
    Test _stop_ack_timer cancels the existing time-out.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    timeout = DummyTimeout(None, None)
    peer._ack_timeout_handle = timeout

    peer._stop_ack_timer()

    assert peer._ack_timeout_handle is None
    assert timeout.cancelled is True


def test_stop_ack_timer_notexisting():
    """
    Test _stop_ack_timer does nothing if no time-out pending.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._ack_timeout_handle = None

    peer._stop_ack_timer()
