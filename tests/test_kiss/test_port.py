#!/usr/bin/env python3

"""
KISS command unit tests
"""

from aioax25.kiss import KISSPort, KISSCmdData, KISSCommand
import logging


class DummyKISSDevice(object):
    def __init__(self):
        self.sent = []

    def _send(self, frame, future):
        self.sent.append((frame, future))

    def _ensure_future(self, future):
        return future


def test_send():
    """
    Test that frames passed to send are wrapped in a KISS frame and passed up.
    """
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger("port"))
    port.send(b"this is a test frame")

    assert len(dev.sent) == 1
    (last, last_future) = dev.sent.pop(0)

    assert last_future is None
    assert isinstance(last, KISSCmdData)
    assert last.port == 5
    assert last.payload == b"this is a test frame"


def test_receive_frame():
    """
    Test that _receive_frame_recv_frame passes data frame payloads to signal
    """
    sent = []
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger("port"))
    port.received.connect(lambda frame, **k: sent.append(frame))

    port._receive_frame(KISSCmdData(port=5, payload=b"this is a test frame"))

    # We should have received that via the signal
    assert len(sent) == 1
    assert sent.pop(0) == b"this is a test frame"


def test_receive_frame_filter_nondata():
    """
    Test that _receive_frame filters non-KISSCmdData frames
    """
    sent = []
    dev = DummyKISSDevice()
    port = KISSPort(dev, 5, logging.getLogger("port"))
    port.received.connect(lambda frame, **k: sent.append(frame))

    port._receive_frame(
        KISSCommand(port=5, cmd=8, payload=b"this is a test frame")
    )

    # We should not have received that frame
    assert len(sent) == 0
