#!/usr/bin/env python3

"""
Tests for FRMR handling
"""

from pytest import approx
import weakref

from aioax25.frame import (
    AX25Address,
    AX25Path,
    AX25FrameRejectFrame,
    AX25SetAsyncBalancedModeFrame,
    AX25DisconnectFrame,
    AX25UnnumberedAcknowledgeFrame,
    AX25TestFrame,
)
from ..mocks import DummyPeer, DummyStation
from .peer import TestingAX25Peer


def test_on_receive_frmr_no_handler():
    """
    Test that a FRMR frame with no handler sends SABM.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._frmrframe_handler = None

    actions = []

    def _send_sabm():
        actions.append("sent-sabm")

    peer._send_sabm = _send_sabm

    peer._on_receive(
        AX25FrameRejectFrame(
            destination=peer.address,
            source=station.address,
            repeaters=AX25Path("VK4RZB*"),
            w=False,
            x=False,
            y=False,
            z=False,
            vr=0,
            frmr_cr=False,
            vs=0,
            frmr_control=0,
        )
    )

    assert actions == ["sent-sabm"]


def test_on_receive_frmr_with_handler():
    """
    Test that a FRMR frame passes to given FRMR handler.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    frames = []

    def _frmr_handler(frame):
        frames.append(frame)

    peer._frmrframe_handler = _frmr_handler

    def _send_dm():
        assert False, "Should not send DM"

    peer._send_dm = _send_dm

    frame = AX25FrameRejectFrame(
        destination=peer.address,
        source=station.address,
        repeaters=AX25Path("VK4RZB*"),
        w=False,
        x=False,
        y=False,
        z=False,
        vr=0,
        frmr_cr=False,
        vs=0,
        frmr_control=0,
    )
    peer._on_receive(frame)

    assert frames == [frame]


# Test handling whilst in FRMR handling mode


def test_on_receive_in_frmr_drop_test():
    """
    Test _on_receive drops TEST frames when in FRMR state.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._state = peer.AX25PeerState.FRMR

    def _on_receive_test(*a, **kwa):
        assert False, "Should have ignored frame"

    peer._on_receive_test = _on_receive_test

    peer._on_receive(
        AX25TestFrame(
            destination=peer.address,
            source=station.address,
            repeaters=AX25Path("VK4RZB*"),
            payload=b"test 1",
            cr=False,
        )
    )


def test_on_receive_in_frmr_drop_ua():
    """
    Test _on_receive drops UA frames when in FRMR state.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._state = peer.AX25PeerState.FRMR

    def _on_receive_ua(*a, **kwa):
        assert False, "Should have ignored frame"

    peer._on_receive_ua = _on_receive_ua

    peer._on_receive(
        AX25UnnumberedAcknowledgeFrame(
            destination=peer.address,
            source=station.address,
            repeaters=AX25Path("VK4RZB*"),
            cr=False,
        )
    )


def test_on_receive_in_frmr_pass_sabm():
    """
    Test _on_receive passes SABM frames when in FRMR state.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._state = peer.AX25PeerState.FRMR

    frames = []

    def _on_receive_sabm(frame):
        frames.append(frame)

    peer._on_receive_sabm = _on_receive_sabm

    frame = AX25SetAsyncBalancedModeFrame(
        destination=peer.address,
        source=station.address,
        repeaters=AX25Path("VK4RZB*"),
        cr=False,
    )
    peer._on_receive(frame)

    assert frames == [frame]


def test_on_receive_in_frmr_pass_disc():
    """
    Test _on_receive passes DISC frames when in FRMR state.
    """
    station = DummyStation(AX25Address("VK4MSL", ssid=1))
    peer = TestingAX25Peer(
        station=station,
        address=AX25Address("VK4MSL"),
        repeaters=AX25Path("VK4RZB"),
        locked_path=True,
    )

    peer._state = peer.AX25PeerState.FRMR

    events = []

    def _on_receive_disc():
        events.append("disc")

    peer._on_receive_disc = _on_receive_disc

    peer._on_receive(
        AX25DisconnectFrame(
            destination=peer.address,
            source=station.address,
            repeaters=AX25Path("VK4RZB*"),
            cr=False,
        )
    )

    assert events == ["disc"]
