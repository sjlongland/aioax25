#!/usr/bin/env python3

import logging

from nose.tools import eq_, assert_greater

from aioax25.aprs.message import APRSMessageHandler, \
        APRSMessageAckFrame, APRSMessageRejFrame, APRSMessageFrame
from aioax25.frame import AX25Address

from ..loop import DummyLoop


class DummyAPRSHandler(object):
    def __init__(self):
        self._loop = DummyLoop()
        self._retransmit_count = 2
        self._retransmit_timeout_base = 5
        self._retransmit_timeout_rand = 5
        self._retransmit_timeout_scale = 1.5
        self.mycall = AX25Address.decode('N0CALL')
        self._next_msgid = 12345

        self.sent = []
        self.finished = []
    
    def _send(self, frame):
        self.sent.append(frame)

    def _on_msg_handler_finish(self, msgid):
        self.finished.append(msgid)


def test_msghandler_abort_on_no_aprshandler():
    """
    Test the message handler aborts if the parent APRS handler disappears.
    """
    aprshandler = DummyAPRSHandler()
    msghandler  = APRSMessageHandler(
            aprshandler=aprshandler,
            addressee='CQ',
            path=['WIDE1-1','WIDE2-1'],
            message='testing',
            log=logging.getLogger('messagehandler'))

    # Blow away the APRS handler
    del aprshandler

    # Message handler is still in the INIT state
    eq_(msghandler.state, msghandler.HandlerState.INIT)

    # Now fire the _send method
    msghandler._send()

    # We should have stopped here.
    eq_(msghandler.state, msghandler.HandlerState.FAIL)


def test_msghandler_first_send():
    """
    Test the message handler transmits message on first _send call.
    """
    aprshandler = DummyAPRSHandler()
    msghandler  = APRSMessageHandler(
            aprshandler=aprshandler,
            addressee='CQ',
            path=['WIDE1-1','WIDE2-1'],
            message='testing',
            log=logging.getLogger('messagehandler'))

    # Message handler is still in the INIT state
    eq_(msghandler.state, msghandler.HandlerState.INIT)

    # Now fire the _send method
    msghandler._send()

    # The message should now be in the 'SEND' state
    eq_(msghandler.state, msghandler.HandlerState.SEND)

    # There should be a pending time-out recorded
    eq_(len(aprshandler._loop.calls), 1)
    (calltime, callfunc) = aprshandler._loop.calls.pop(0)

    # Should be at least 5 seconds from now, calling _on_timeout
    assert_greater(calltime, aprshandler._loop.time() + 5.0)
    eq_(callfunc, msghandler._on_timeout)
