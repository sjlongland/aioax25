#!/usr/bin/env python3

"""
Fixture for initialising an AX25 Peer
"""

from nose.tools import eq_, assert_almost_equal, assert_is, \
        assert_is_not_none, assert_is_none

from aioax25.peer import AX25Peer
from aioax25.version import AX25Version
from ..mocks import DummyIOLoop, DummyLogger


class TestingAX25Peer(AX25Peer):
    def __init__(self, station, address, repeaters, max_ifield=256,
            max_ifield_rx=256, max_retries=10, max_outstanding_mod8=7,
            max_outstanding_mod128=127, rr_delay=10.0, rr_interval=30.0,
            rnr_interval=10.0, ack_timeout=3.0, idle_timeout=900.0,
            protocol=AX25Version.UNKNOWN, modulo128=False,
            reject_mode=AX25Peer.AX25RejectMode.SELECTIVE_RR,
            full_duplex=False, reply_path=None, locked_path=False):
        super(TestingAX25Peer, self).__init__(
                station, address, repeaters, max_ifield, max_ifield_rx,
                max_retries, max_outstanding_mod8, max_outstanding_mod128,
                rr_delay, rr_interval, rnr_interval, ack_timeout, idle_timeout,
                protocol, modulo128, DummyLogger('peer'), DummyIOLoop(),
                reject_mode, full_duplex, reply_path, locked_path)
