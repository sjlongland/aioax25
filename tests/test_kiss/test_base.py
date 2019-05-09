#!/usr/bin/env python3

"""
Base KISS interface unit tests.
"""

from aioax25.kiss import BaseKISSDevice, KISSDeviceState, KISSCommand
from ..loop import DummyLoop

from nose.tools import eq_


class DummyKISSDevice(BaseKISSDevice):
    def __init__(self, **kwargs):
        super(DummyKISSDevice, self).__init__(**kwargs)

        self.transmitted = bytearray()
        self.open_calls = 0
        self.close_calls = 0

    def _open(self):
        self.open_calls += 1

    def _close(self):
        self.close_calls += 1

    def _send_raw_data(self, data):
        self.transmitted += data


def test_open():
    """
    Test an open call passes to subclass _open
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)

    eq_(kissdev.open_calls, 0)
    kissdev.open()

    eq_(kissdev.open_calls, 1)

def test_close():
    """
    Test a close call passes to _close
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=False
    )

    # Force the port open
    kissdev._state = KISSDeviceState.OPEN

    eq_(kissdev.close_calls, 0)

    # Now try closing the port
    kissdev.close()
    eq_(kissdev.close_calls, 1)

def test_close_reset():
    """
    Test a close call with reset_on_close sends the "return from KISS" frame
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )

    # Force the port open
    kissdev._state = KISSDeviceState.OPEN

    # Now try closing the port
    kissdev.close()

    # Should be in the closing state
    eq_(kissdev._state, KISSDeviceState.CLOSING)

    # A "return from KISS" frame should be in the transmit buffer
    eq_(bytes(kissdev._tx_buffer), b'\xc0\xff\xc0')

    # A call to _send_data should be pending
    (_, func) = loop.calls.pop()
    eq_(func, kissdev._send_data)

def test_receive():
    """
    Test that a call to _receive stashes the data then schedules _receive_frame.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._receive(b'test incoming data')

    # Data should be waiting
    eq_(bytes(kissdev._rx_buffer), b'test incoming data')

    # A call to _receive_frame should be pending
    (_, func) = loop.calls.pop()
    eq_(func, kissdev._receive_frame)

def test_receive_frame_garbage():
    """
    Test _receive_frame discards all data when no FEND byte found.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._rx_buffer += b'this should be discarded'
    kissdev._receive_frame()

    # We should just have the data including and following the FEND
    eq_(bytes(kissdev._rx_buffer), b'')

    # As there's no complete frames, no calls should be scheduled
    eq_(len(loop.calls), 0)

def test_receive_frame_garbage_start():
    """
    Test _receive_frame discards everything up to the first FEND byte.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._rx_buffer += b'this should be discarded\xc0this should be kept'
    kissdev._receive_frame()

    # We should just have the data including and following the FEND
    eq_(bytes(kissdev._rx_buffer), b'\xc0this should be kept')

    # As there's no complete frames, no calls should be scheduled
    eq_(len(loop.calls), 0)

def test_receive_frame_empty():
    """
    Test _receive_frame discards empty frames.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._rx_buffer += b'\xc0\xc0'
    kissdev._receive_frame()

    # We should just have the last FEND
    eq_(bytes(kissdev._rx_buffer), b'\xc0')

    # It should leave the last FEND there and wait for more data.
    eq_(len(loop.calls), 0)

def test_receive_frame_single():
    """
    Test _receive_frame hands a single frame to _dispatch_rx_frame.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._rx_buffer += b'\xc0\x00a single KISS frame\xc0'
    kissdev._receive_frame()

    # We should just have the last FEND
    eq_(bytes(kissdev._rx_buffer), b'\xc0')

    # We should have one call to _dispatch_rx_frame
    eq_(len(loop.calls), 1)
    (_, func, frame) = loop.calls.pop(0)
    eq_(func, kissdev._dispatch_rx_frame)
    assert isinstance(frame, KISSCommand)
    eq_(frame.port, 0)
    eq_(frame.cmd, 0)
    eq_(frame.payload, b'a single KISS frame')

def test_receive_frame_more():
    """
    Test _receive_frame calls itself when more data left.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(
            loop=loop, reset_on_close=True
    )
    kissdev._rx_buffer += b'\xc0\x00a single KISS frame\xc0more data'
    kissdev._receive_frame()

    # We should just have the left-over bit including the last FEND
    eq_(bytes(kissdev._rx_buffer), b'\xc0more data')

    # This should have generated two calls:
    eq_(len(loop.calls), 2)

    # We should have one call to _dispatch_rx_frame
    (_, func, frame) = loop.calls.pop(0)
    eq_(func, kissdev._dispatch_rx_frame)
    assert isinstance(frame, KISSCommand)
    eq_(frame.port, 0)
    eq_(frame.cmd, 0)
    eq_(frame.payload, b'a single KISS frame')

    # We should have another to _receive_frame itself.
    (_, func) = loop.calls.pop(0)
    eq_(func, kissdev._receive_frame)
