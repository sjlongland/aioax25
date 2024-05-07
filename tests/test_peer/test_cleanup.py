#!/usr/bin/env python3

"""
Test handling of clean-up logic
"""

from aioax25.frame import AX25Address, AX25Path
from aioax25.peer import AX25PeerState
from .peer import TestingAX25Peer
from ..mocks import DummyStation, DummyTimeout

# Idle time-out cancellation


def test_cancel_idle_timeout_inactive():
    """
    Test that calling _cancel_idle_timeout with no time-out is a no-op.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Constructor resets the timer, so discard that time-out handle
    # This is safe because TestingAX25Peer does not use a real IOLoop
    peer._idle_timeout_handle = None

    peer._cancel_idle_timeout()


def test_cancel_idle_timeout_active():
    """
    Test that calling _cancel_idle_timeout active time-out cancels it.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    timeout = DummyTimeout(0, lambda: None)
    peer._idle_timeout_handle = timeout

    peer._cancel_idle_timeout()

    assert peer._idle_timeout_handle is None
    assert timeout.cancelled is True


# Idle time-out reset


def test_reset_idle_timeout():
    """
    Test that calling _reset_idle_timeout re-creates a time-out object
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Grab the original time-out created by the constructor
    orig_timeout = peer._idle_timeout_handle
    assert orig_timeout is not None

    # Reset the time-out
    peer._reset_idle_timeout()

    assert peer._idle_timeout_handle is not orig_timeout
    assert orig_timeout.cancelled is True

    # New time-out should call the appropriate routine at the right time
    assert peer._idle_timeout_handle.delay == peer._idle_timeout
    assert peer._idle_timeout_handle.callback == peer._cleanup


# Clean-up steps


def test_cleanup_disconnected():
    """
    Test that clean-up whilst disconnect just cancels RR notifications
    """
    # Most of the time, there will be no pending RR notifications, so
    # _cancel_rr_notification will be a no-op in this case.

    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub methods

    actions = []

    def _cancel_rr_notification():
        actions.append("cancel-rr")

    peer._cancel_rr_notification = _cancel_rr_notification

    def disconnect():
        assert False, "Should not call disconnect"

    peer.disconnect = disconnect

    def _send_dm():
        assert False, "Should not send DM"

    peer._send_dm = _send_dm

    # Set state
    peer._state = AX25PeerState.DISCONNECTED

    # Do clean-up
    peer._cleanup()

    assert actions == ["cancel-rr"]


def test_cleanup_disconnecting():
    """
    Test that clean-up whilst disconnecting cancels RR notification
    """
    # Most of the time, there will be no pending RR notifications, so
    # _cancel_rr_notification will be a no-op in this case.

    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub methods

    actions = []

    def _cancel_rr_notification():
        actions.append("cancel-rr")

    peer._cancel_rr_notification = _cancel_rr_notification

    def disconnect():
        assert False, "Should not call disconnect"

    peer.disconnect = disconnect

    def _send_dm():
        assert False, "Should not send DM"

    peer._send_dm = _send_dm

    # Set state
    peer._state = AX25PeerState.DISCONNECTING

    # Do clean-up
    peer._cleanup()

    assert actions == ["cancel-rr"]


def test_cleanup_connecting():
    """
    Test that clean-up whilst connecting sends DM then cancels RR notifications
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub methods

    actions = []

    def _cancel_rr_notification():
        actions.append("cancel-rr")

    peer._cancel_rr_notification = _cancel_rr_notification

    def disconnect():
        assert False, "Should not call disconnect"

    peer.disconnect = disconnect

    def _send_dm():
        actions.append("sent-dm")

    peer._send_dm = _send_dm

    # Set state
    peer._state = AX25PeerState.CONNECTING

    # Do clean-up
    peer._cleanup()

    assert actions == ["sent-dm", "cancel-rr"]


def test_cleanup_connected():
    """
    Test that clean-up whilst connected sends DISC then cancels RR notifications
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    # Stub methods

    actions = []

    def _cancel_rr_notification():
        actions.append("cancel-rr")

    peer._cancel_rr_notification = _cancel_rr_notification

    def disconnect():
        actions.append("disconnect")

    peer.disconnect = disconnect

    def _send_dm():
        assert False, "Should not send DM"

    peer._send_dm = _send_dm

    # Set state
    peer._state = AX25PeerState.CONNECTED

    # Do clean-up
    peer._cleanup()

    assert actions == ["disconnect", "cancel-rr"]
