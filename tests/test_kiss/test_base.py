#!/usr/bin/env python3

"""
Base KISS interface unit tests.
"""

from aioax25.kiss import BaseKISSDevice, KISSDeviceState, KISSCommand, KISSPort
from ..loop import DummyLoop
from asyncio import BaseEventLoop

from nose.tools import eq_, assert_is, assert_greater, assert_less


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


def test_constructor_own_loop():
    """
    Test constructor uses its own IOLoop if not given one
    """
    kissdev = DummyKISSDevice(loop=None)
    assert isinstance(kissdev._loop, BaseEventLoop)


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

def test_dispatch_rx_invalid_port():
    """
    Test that _dispatch_rx_port to an undefined port drops the frame.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)
    kissdev._dispatch_rx_frame(
            KISSCommand(cmd=10, port=14, payload=b'this should be dropped')
    )

def test_dispatch_rx_exception():
    """
    Test that _dispatch_rx_port drops frame on exception.
    """
    class DummyPort(object):
        def _receive_frame(self, frame):
            raise IOError('Whoopsie')

    port = DummyPort()
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)
    kissdev._port[14] = port

    # Deliver the frame
    frame = KISSCommand(cmd=10, port=14, payload=b'this should be dropped')
    kissdev._dispatch_rx_frame(frame)

def test_dispatch_rx_valid_port():
    """
    Test that _dispatch_rx_port to a known port delivers to that port.
    """
    class DummyPort(object):
        def __init__(self):
            self.frames = []

        def _receive_frame(self, frame):
            self.frames.append(frame)

    port = DummyPort()
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)
    kissdev._port[14] = port

    # Deliver the frame
    frame = KISSCommand(cmd=10, port=14, payload=b'this should be delivered')
    kissdev._dispatch_rx_frame(frame)

    # Our port should have the frame
    eq_(len(port.frames), 1)
    assert_is(port.frames[0], frame)

def test_send_data():
    """
    Test that _send_data sends whatever data is buffered up to the block size.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)
    kissdev._tx_buffer += b'test output data'

    # Send the data out.
    kissdev._send_data()

    # We should now see this was "sent" and now in 'transmitted'
    eq_(bytes(kissdev.transmitted), b'test output data')

    # That should be the lot
    eq_(len(loop.calls), 0)

def test_send_data_block_size():
    """
    Test that _send_data re-schedules itself when buffer exceeds block size
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop, send_block_size=4, send_block_delay=1)
    kissdev._tx_buffer += b'test output data'

    # Send the data out.
    kissdev._send_data()

    # We should now see the first block was "sent" and now in 'transmitted'
    eq_(bytes(kissdev.transmitted), b'test')

    # The rest should be waiting
    eq_(bytes(kissdev._tx_buffer), b' output data')

    # There should be a pending call to send more:
    eq_(len(loop.calls), 1)
    (calltime, callfunc) = loop.calls.pop(0)

    # It'll be roughly in a second's time calling the same function
    assert_greater(calltime - loop.time(), 0.990)
    assert_less(calltime - loop.time(), 1.0)
    eq_(callfunc, kissdev._send_data)

def test_send_data_close_after_send():
    """
    Test that _send_data when closing the device, closes after last send
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)
    kissdev._tx_buffer += b'test output data'

    # Force state
    kissdev._state = KISSDeviceState.CLOSING

    # No close call made yet
    eq_(kissdev.close_calls, 0)

    # Send the data out.
    kissdev._send_data()

    # We should now see the first block was "sent" and now in 'transmitted'
    eq_(bytes(kissdev.transmitted), b'test output data')

    # The device should now be closed.
    eq_(kissdev.close_calls, 1)

def test_send_data_block_size():
    """
    Test that _send_data waits until all data sent before closing.
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop, send_block_size=4, send_block_delay=1)
    kissdev._tx_buffer += b'test output data'

    # Force state
    kissdev._state = KISSDeviceState.CLOSING

    # Send the data out.
    kissdev._send_data()

    # We should now see the first block was "sent" and now in 'transmitted'
    eq_(bytes(kissdev.transmitted), b'test')

    # The rest should be waiting
    eq_(bytes(kissdev._tx_buffer), b' output data')

    # There should be a pending call to send more:
    eq_(len(loop.calls), 1)
    (calltime, callfunc) = loop.calls.pop(0)

    # It'll be roughly in a second's time calling the same function
    assert_greater(calltime - loop.time(), 0.990)
    assert_less(calltime - loop.time(), 1.0)
    eq_(callfunc, kissdev._send_data)

    # No close call made yet
    eq_(kissdev.close_calls, 0)

def test_init_kiss():
    """
    Test _init_kiss sets up the commands to be sent to initialise KISS
    """
    loop = DummyLoop()
    kissdev = DummyKISSDevice(loop=loop)

    # Force state
    kissdev._state = KISSDeviceState.OPENING

    # Initialise the KISS device
    kissdev._init_kiss()

    # We should see a copy of the KISS commands, minus the first
    eq_(kissdev._kiss_rem_commands, kissdev._kiss_commands[1:])

    # We should see the first initialisation commands
    eq_(bytes(kissdev.transmitted), b'INT KISS\r')

def test_getitem():
    """
    Test __getitem__ returns a port instance.
    """
    kissdev = DummyKISSDevice(loop=DummyLoop())
    port = kissdev[7]
    assert isinstance(port, KISSPort)
    assert_is(kissdev._port[7], port)

def test__send_kiss_cmd():
    kissdev = DummyKISSDevice(loop=DummyLoop())
    kissdev._kiss_rem_commands = []

    kissdev._send_kiss_cmd()
    eq_(KISSDeviceState.OPEN, kissdev._state)
    eq_(bytearray(), kissdev._rx_buffer)

