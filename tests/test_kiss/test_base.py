#!/usr/bin/env python3

"""
Base KISS interface unit tests.
"""

from aioax25.kiss import BaseKISSDevice, KISSDeviceState
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
