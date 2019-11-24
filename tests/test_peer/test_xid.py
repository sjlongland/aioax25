#!/usr/bin/env python3

"""
Tests for AX25Peer XID handling
"""

from nose.tools import eq_, assert_almost_equal, assert_is, \
        assert_is_not_none, assert_is_none

from aioax25.frame import AX25Address, AX25XIDClassOfProceduresParameter, \
        AX25XIDHDLCOptionalFunctionsParameter, \
        AX25XIDIFieldLengthTransmitParameter, \
        AX25XIDIFieldLengthReceiveParameter, \
        AX25XIDWindowSizeTransmitParameter, \
        AX25XIDWindowSizeReceiveParameter, \
        AX25XIDAcknowledgeTimerParameter, \
        AX25XIDRetriesParameter, \
        AX25XIDRawParameter, \
        AX25ExchangeIdentificationFrame, \
        AX25FrameRejectFrame
from aioax25.version import AX25Version
from .peer import TestingAX25Peer
from ..mocks import DummyStation


def test_peer_process_xid_cop_fds_fdp():
    """
    Test _process_xid_cop enables full-duplex if both stations negotiate it.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=True
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDClassOfProceduresParameter(
        full_duplex=True, half_duplex=False
    ))

    # Full duplex should be enabled
    assert peer._full_duplex


def test_peer_process_xid_cop_fds_hdp():
    """
    Test _process_xid_cop disables full-duplex if the peer is half-duplex.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=True
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDClassOfProceduresParameter(
        full_duplex=False, half_duplex=True
    ))

    # Full duplex should be disabled
    assert not peer._full_duplex


def test_peer_process_xid_cop_hds_fdp():
    """
    Test _process_xid_cop disables full-duplex if the station is half-duplex.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=False
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDClassOfProceduresParameter(
        full_duplex=True, half_duplex=False
    ))

    # Full duplex should be disabled
    assert not peer._full_duplex


def test_peer_process_xid_cop_malformed_cop_fdx_hdx():
    """
    Test _process_xid_cop disables full-duplex the CoP frame sets both
    half-duplex and full-duplex flags.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=True
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDClassOfProceduresParameter(
        full_duplex=True, half_duplex=True
    ))

    # Full duplex should be disabled
    assert not peer._full_duplex


def test_peer_process_xid_cop_malformed_cop_nfdx_nhdx():
    """
    Test _process_xid_cop disables full-duplex the CoP frame clears both
    half-duplex and full-duplex flags.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=True
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDClassOfProceduresParameter(
        full_duplex=False, half_duplex=False
    ))

    # Full duplex should be disabled
    assert not peer._full_duplex


def test_peer_process_xid_cop_default():
    """
    Test _process_xid_cop assumes AX.25 2.2 defaults if given null CoP
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            full_duplex=True
    )

    # Pass in a CoP XID parameter
    peer._process_xid_cop(AX25XIDRawParameter(
        pi=AX25XIDClassOfProceduresParameter.PI,
        pv=None
    ))

    # Full duplex should be disabled
    assert not peer._full_duplex


def test_peer_process_xid_hdlcoptfunc_stnssr_peerssr():
    """
    Test _process_xid_hdlcoptfunc sets SRR if both set SRR
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE_RR
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=True, srej=True
    ))

    # Selective Reject-Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.SELECTIVE_RR)


def test_peer_process_xid_hdlcoptfunc_stnsr_peerssr():
    """
    Test _process_xid_hdlcoptfunc sets SR if station sets SR
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=True, srej=True
    ))

    # Selective Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.SELECTIVE)


def test_peer_process_xid_hdlcoptfunc_stnssr_peersr():
    """
    Test _process_xid_hdlcoptfunc sets SR if peer sets SR
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE_RR
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=False, srej=True
    ))

    # Selective Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.SELECTIVE)


def test_peer_process_xid_hdlcoptfunc_stnsr_peersr():
    """
    Test _process_xid_hdlcoptfunc sets SR if both agree on SR
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=False, srej=True
    ))

    # Selective Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.SELECTIVE)


def test_peer_process_xid_hdlcoptfunc_stnir_peersr():
    """
    Test _process_xid_hdlcoptfunc sets IR if station sets IR (peer=SR)
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.IMPLICIT
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=False, srej=True
    ))

    # Implicit Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.IMPLICIT)


def test_peer_process_xid_hdlcoptfunc_stnsr_peerir():
    """
    Test _process_xid_hdlcoptfunc sets IR if peer sets IR (station=SR)
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=True, srej=False
    ))

    # Implicit Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.IMPLICIT)


def test_peer_process_xid_hdlcoptfunc_stnir_peerssr():
    """
    Test _process_xid_hdlcoptfunc sets IR if station sets IR (peer=SSR)
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.IMPLICIT
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=True, srej=True
    ))

    # Implicit Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.IMPLICIT)


def test_peer_process_xid_hdlcoptfunc_stnssr_peerir():
    """
    Test _process_xid_hdlcoptfunc sets IR if peer sets IR (station=SSR)
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE_RR
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=True, srej=False
    ))

    # Implicit Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.IMPLICIT)


def test_peer_process_xid_hdlcoptfunc_malformed_rej_srej():
    """
    Test _process_xid_hdlcoptfunc sets IR if peer clears REJ and SREJ
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE_RR
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        rej=False, srej=False
    ))

    # Implicit Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.IMPLICIT)


def test_peer_process_xid_hdlcoptfunc_default_rej_srej():
    """
    Test _process_xid_hdlcoptfunc sets SR if peer does not send value.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            reject_mode=TestingAX25Peer.AX25RejectMode.SELECTIVE_RR
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDRawParameter(
        pi=AX25XIDHDLCOptionalFunctionsParameter.PI,
        pv=None
    ))

    # Selective Reject should be chosen.
    eq_(peer._reject_mode, TestingAX25Peer.AX25RejectMode.SELECTIVE)


def test_peer_process_xid_hdlcoptfunc_s128_p128():
    """
    Test _process_xid_hdlcoptfunc sets mod128 if both agree
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=False, modulo128=True
    ))

    # Modulo128 should be chosen.
    assert peer._modulo128


def test_peer_process_xid_hdlcoptfunc_s128_p8():
    """
    Test _process_xid_hdlcoptfunc sets mod8 if peer sets mod8
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=True, modulo128=False
    ))

    # Modulo8 should be chosen.
    assert not peer._modulo128


def test_peer_process_xid_hdlcoptfunc_s8_p128():
    """
    Test _process_xid_hdlcoptfunc sets mod8 if station sets mod8
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=False
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=False, modulo128=True
    ))

    # Modulo8 should be chosen.
    assert not peer._modulo128


def test_peer_process_xid_hdlcoptfunc_s8_p8():
    """
    Test _process_xid_hdlcoptfunc sets mod8 if both agree on mod8
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=False
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=True, modulo128=False
    ))

    # Modulo8 should be chosen.
    assert not peer._modulo128


def test_peer_process_xid_hdlcoptfunc_malformed_m8s_m128s():
    """
    Test _process_xid_hdlcoptfunc sets mod8 if peer sets mod8 and mod128 bits
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=True, modulo128=True
    ))

    # Modulo8 should be chosen.
    assert not peer._modulo128


def test_peer_process_xid_hdlcoptfunc_malformed_m8c_m128c():
    """
    Test _process_xid_hdlcoptfunc sets mod8 if peer clears mod8 and mod128 bits
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True
    )

    # Pass in a HDLC Optional Functions XID parameter
    peer._process_xid_hdlcoptfunc(AX25XIDHDLCOptionalFunctionsParameter(
        modulo8=False, modulo128=False
    ))

    # Modulo8 should be chosen.
    assert not peer._modulo128


def test_peer_process_xid_ifieldlenrx_station_smaller():
    """
    Test _process_xid_ifieldlenrx chooses station's field length if it's smaller
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_ifield=128
    )

    # Pass in a I-Field Length Receive XID parameter
    peer._process_xid_ifieldlenrx(AX25XIDIFieldLengthReceiveParameter(2048))

    # 128 bytes should be set
    eq_(peer._max_ifield, 128)


def test_peer_process_xid_ifieldlenrx_peer_smaller():
    """
    Test _process_xid_ifieldlenrx chooses peer's field length if it's smaller
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_ifield=256
    )

    # Pass in a I-Field Length Receive XID parameter
    peer._process_xid_ifieldlenrx(AX25XIDIFieldLengthReceiveParameter(1024))

    # 128 bytes should be set
    eq_(peer._max_ifield, 128)


def test_peer_process_xid_ifieldlenrx_default():
    """
    Test _process_xid_ifieldlenrx assumes defaults if not given a value
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_ifield=256
    )

    # Pass in a I-Field Length Receive XID parameter
    peer._process_xid_ifieldlenrx(AX25XIDRawParameter(
        pi=AX25XIDIFieldLengthReceiveParameter.PI,
        pv=None
    ))

    # 256 bytes should be set
    eq_(peer._max_ifield, 256)


def test_peer_process_xid_winszrx_station_smaller():
    """
    Test _process_xid_winszrx chooses station's window size if it's smaller
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True,
            max_outstanding_mod128=63
    )

    # Pass in a Window Size Receive XID parameter
    peer._process_xid_winszrx(AX25XIDWindowSizeReceiveParameter(127))

    # 63 frames should be set
    eq_(peer._max_outstanding, 63)


def test_peer_process_xid_winszrx_peer_smaller():
    """
    Test _process_xid_winszrx chooses peer's window size if it's smaller
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True,
            max_outstanding_mod128=127
    )

    # Pass in a Window Size Receive XID parameter
    peer._process_xid_winszrx(AX25XIDWindowSizeReceiveParameter(63))

    # 63 frames should be set
    eq_(peer._max_outstanding, 63)


def test_peer_process_xid_winszrx_default():
    """
    Test _process_xid_winszrx assumes defaults if not given a value
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            modulo128=True,
            max_outstanding_mod128=127
    )

    # Pass in a Window Size Receive XID parameter
    peer._process_xid_winszrx(AX25XIDRawParameter(
        pi=AX25XIDWindowSizeReceiveParameter.PI,
        pv=None
    ))

    # 7 frames should be set
    eq_(peer._max_outstanding, 7)


def test_peer_process_xid_acktimer_station_larger():
    """
    Test _process_xid_acktimer chooses station's acknowledge timer if it's larger
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            ack_timeout=10.0
    )

    # Pass in a Acknowledge Timer XID parameter
    peer._process_xid_acktimer(AX25XIDAcknowledgeTimerParameter(5000))

    # 10 seconds should be set
    eq_(peer._ack_timeout, 10.0)


def test_peer_process_xid_acktimer_peer_larger():
    """
    Test _process_xid_acktimer chooses peer's acknowledge timer if it's larger
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            ack_timeout=5.0
    )

    # Pass in a Acknowledge Timer XID parameter
    peer._process_xid_acktimer(AX25XIDAcknowledgeTimerParameter(10000))

    # 10 seconds should be set
    eq_(peer._ack_timeout, 10.0)


def test_peer_process_xid_acktimer_default():
    """
    Test _process_xid_acktimer assumes defaults if not given a value
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            ack_timeout=1.0
    )

    # Pass in a Acknowledge Timer XID parameter
    peer._process_xid_acktimer(AX25XIDRawParameter(
        pi=AX25XIDAcknowledgeTimerParameter.PI,
        pv=None
    ))

    # 3 seconds should be set
    eq_(peer._ack_timeout, 3.0)


def test_peer_process_xid_retrycounter_station_larger():
    """
    Test _process_xid_retrycounter chooses station's retry count if it's larger
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_retries=6
    )

    # Pass in a Retries XID parameter
    peer._process_xid_retrycounter(AX25XIDRetriesParameter(2))

    # 6 retries should be set
    eq_(peer._max_retries, 6)


def test_peer_process_xid_retrycounter_peer_larger():
    """
    Test _process_xid_retrycounter chooses peer's retry count if it's larger
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_retries=2
    )

    # Pass in a Retries XID parameter
    peer._process_xid_retrycounter(AX25XIDRetriesParameter(6))

    # 6 retries should be set
    eq_(peer._max_retries, 6)


def test_peer_process_xid_retrycounter_default():
    """
    Test _process_xid_retrycounter assumes defaults if not given a value
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None,
            max_retries=0
    )

    # Pass in a Retries XID parameter
    peer._process_xid_retrycounter(AX25XIDRawParameter(
        pi=AX25XIDRetriesParameter.PI,
        pv=None
    ))

    # 10 retries should be set
    eq_(peer._max_retries, 10)


def test_peer_on_receive_xid_ax20_mode():
    """
    Test _on_receive_xid responds with FRMR when in AX.25 2.0 mode.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    station._protocol = AX25Version.AX25_20
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Nothing yet sent
    eq_(interface.transmit_calls, [])

    # Pass in the XID frame to our AX.25 2.0 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[]
            )
    )

    # One frame sent
    eq_(len(interface.transmit_calls), 1)
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a FRMR
    eq_(tx_kwargs, {'callback': None})
    eq_(len(tx_args), 1)
    (frame,) = tx_args
    assert isinstance(frame, AX25FrameRejectFrame)

    # W bit should be set
    assert frame.w

    # We should now be in the FRMR state
    eq_(peer._state, peer.AX25PeerState.FRMR)


def test_peer_on_receive_xid_connecting():
    """
    Test _on_receive_xid ignores XID when connecting.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Nothing yet sent
    eq_(interface.transmit_calls, [])

    # Set state
    peer._state = TestingAX25Peer.AX25PeerState.CONNECTING

    # Pass in the XID frame to our AX.25 2.2 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[],
                cr=True
            )
    )

    # Still nothing yet sent
    eq_(interface.transmit_calls, [])


def test_peer_on_receive_xid_disconnecting():
    """
    Test _on_receive_xid ignores XID when disconnecting.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Nothing yet sent
    eq_(interface.transmit_calls, [])

    # Set state
    peer._state = TestingAX25Peer.AX25PeerState.DISCONNECTING

    # Pass in the XID frame to our AX.25 2.2 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[],
                cr=True
            )
    )

    # Still nothing yet sent
    eq_(interface.transmit_calls, [])


def test_peer_on_receive_xid_sets_proto_version():
    """
    Test _on_receive_xid sets protocol version if unknown.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Version should be unknown
    eq_(peer._protocol, AX25Version.UNKNOWN)

    # Pass in the XID frame to our AX.25 2.2 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[]
            )
    )

    # We now should consider the other station as AX.25 2.2 or better
    eq_(peer._protocol, AX25Version.AX25_22)


def test_peer_on_receive_xid_keeps_known_proto_version():
    """
    Test _on_receive_xid keeps existing protocol version if known.
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            protocol=AX25Version.AX25_22,
            repeaters=None
    )

    # Pass in the XID frame to our AX.25 2.2 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[]
            )
    )

    # We should still consider the other station as AX.25 2.2 or better
    eq_(peer._protocol, AX25Version.AX25_22)


def test_peer_on_receive_xid_ignores_bad_fi():
    """
    Test _on_receive_xid ignores parameters if FI is unknown
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Stub out _process_xid_cop
    def _stub_process_cop(param):
        assert False, 'Should not be called'
    peer._process_xid_cop = _stub_process_cop

    # Pass in the XID frame to our AX.25 2.2 station.
    # There should be no assertion triggered.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[
                    AX25XIDClassOfProceduresParameter(
                        half_duplex=True
                    )
                ],
                fi=26
            )
    )


def test_peer_on_receive_xid_ignores_bad_gi():
    """
    Test _on_receive_xid ignores parameters if GI is unknown
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Stub out _process_xid_cop
    def _stub_process_cop(param):
        assert False, 'Should not be called'
    peer._process_xid_cop = _stub_process_cop

    # Pass in the XID frame to our AX.25 2.2 station.
    # There should be no assertion triggered.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[
                    AX25XIDClassOfProceduresParameter(
                        half_duplex=True
                    )
                ],
                gi=26
            )
    )


def test_peer_on_receive_xid_processes_parameters():
    """
    Test _on_receive_xid processes parameters on good XID frames
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Pass in the XID frame to our AX.25 2.2 station.
    # There should be no assertion triggered.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[
                    AX25XIDIFieldLengthReceiveParameter(512)
                ]
            )
    )

    # Should be negotiated to 64 bytes
    eq_(peer._max_ifield, 64)


def test_peer_on_receive_xid_reply():
    """
    Test _on_receive_xid sends reply if incoming frame has CR=True
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Nothing yet sent
    eq_(interface.transmit_calls, [])

    # Pass in the XID frame to our AX.25 2.2 station.
    peer._on_receive_xid(
            AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[],
                cr=True
            )
    )

    # This was a request, so there should be a reply waiting
    eq_(len(interface.transmit_calls), 1)
    (tx_args, tx_kwargs) = interface.transmit_calls.pop(0)

    # This should be a XID
    eq_(tx_kwargs, {'callback': None})
    eq_(len(tx_args), 1)
    (frame,) = tx_args
    assert isinstance(frame, AX25ExchangeIdentificationFrame)

    # CR bit should be clear
    assert not frame.header.cr

    # Frame should reflect the settings of the station
    eq_(len(frame.parameters), 8)

    param = frame.parameters[0]
    assert isinstance(param, AX25XIDClassOfProceduresParameter)
    assert param.half_duplex
    assert not param.full_duplex

    param = frame.parameters[1]
    assert isinstance(param, AX25XIDHDLCOptionalFunctionsParameter)
    assert param.srej
    assert not param.rej
    assert not param.modulo128
    assert param.modulo8

    param = frame.parameters[2]
    assert isinstance(param, AX25XIDIFieldLengthTransmitParameter)
    eq_(param.value, 2048)

    param = frame.parameters[3]
    assert isinstance(param, AX25XIDIFieldLengthReceiveParameter)
    eq_(param.value, 2048)

    param = frame.parameters[4]
    assert isinstance(param, AX25XIDWindowSizeTransmitParameter)
    eq_(param.value, 7)

    param = frame.parameters[5]
    assert isinstance(param, AX25XIDWindowSizeReceiveParameter)
    eq_(param.value, 7)

    param = frame.parameters[6]
    assert isinstance(param, AX25XIDAcknowledgeTimerParameter)
    eq_(param.value, 3000)

    param = frame.parameters[7]
    assert isinstance(param, AX25XIDRetriesParameter)
    eq_(param.value, 10)


def test_peer_on_receive_xid_relay():
    """
    Test _on_receive_xid sends relays to XID handler if CR=False
    """
    station = DummyStation(AX25Address('VK4MSL', ssid=1))
    interface = station._interface()
    peer = TestingAX25Peer(
            station=station,
            address=AX25Address('VK4MSL'),
            repeaters=None
    )

    # Nothing yet sent
    eq_(interface.transmit_calls, [])

    # Hook the XID handler
    xid_events = []
    peer._xidframe_handler = lambda *a, **kw : xid_events.append((a, kw))

    # Pass in the XID frame to our AX.25 2.2 station.
    frame = AX25ExchangeIdentificationFrame(
                destination=station.address,
                source=peer.address,
                repeaters=None,
                parameters=[],
                cr=False
            )
    peer._on_receive_xid(frame)

    # There should have been a XID event
    eq_(len(xid_events), 1)

    # It should be passed our handler
    (xid_args, xid_kwargs) = xid_events.pop(0)
    (xid_frame,) = xid_args
    assert frame is xid_frame
