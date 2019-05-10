#!/usr/bin/env python3

"""
KISS command unit tests
"""

from aioax25.kiss import KISSPort, KISSCmdData, KISSCommand
from nose.tools import eq_
import logging


class DummyKISSDevice(object):
    def __init__(self):
        self.sent = []

    def _send(self, frame):
        self.sent.append(frame)


def test_send():
    """
    Test that frames passed to send are wrapped in a KISS frame and passed up.
    """
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger('port'))
    port.send(b'this is a test frame')

    eq_(len(dev.sent), 1)
    last = dev.sent.pop(0)

    assert isinstance(last, KISSCmdData)
    eq_(last.port, 5)
    eq_(last.payload, b'this is a test frame')

def test_receive_frame():
    """
    Test that _receive_frame_recv_frame passes data frame payloads to signal
    """
    sent = []
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger('port'))
    port.received.connect(lambda frame, **k : sent.append(frame))

    port._receive_frame(KISSCmdData(port=5, payload=b'this is a test frame'))

    # We should have received that via the signal
    eq_(len(sent),1)
    eq_(sent.pop(0), b'this is a test frame')

def test_receive_frame_filter_nondata():
    """
    Test that _receive_frame filters non-KISSCmdData frames
    """
    sent = []
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger('port'))
    port.received.connect(lambda frame, **k : sent.append(frame))

    port._receive_frame(KISSCommand(port=5, cmd=8,
        payload=b'this is a test frame'))

    # We should not have received that frame
    eq_(len(sent),0)
