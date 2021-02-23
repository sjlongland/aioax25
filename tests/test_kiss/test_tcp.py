#!/usr/bin/env python3

"""
Serial KISS interface unit tests.
"""

from aioax25 import kiss
from unittest import mock
import time

from nose.tools import eq_, assert_less, assert_in
from ..loop import DummyLoop


@mock.patch('socket.socket')
def test_open(mock_socket):
    """
    Test we can open the port.
    """
    loop = DummyLoop()
    kissdev = kiss.TCPKISSDevice(
        host='localhost', port=8001,
        loop=loop
    )
    assert kissdev._interface is None

    kissdev.open()

    # kissdev._serial should now be a DummySerial instance
    assert isinstance(kissdev._interface, mock.Mock)

    # A reader should have been added
    assert_in(kissdev._interface, loop.readers)
    print(loop.readers)
    eq_(loop.readers[kissdev._interface], kissdev._on_recv_ready)

    # A call to initialise the device should have been scheduled.
    eq_(len(loop.calls), 1)
    (calltime, callfunc) = loop.calls.pop(0)
    assert_less(time.monotonic() - calltime, 0.01)
    eq_(callfunc, kissdev._init_kiss)


@mock.patch('socket.socket')
def test_close(mock_socket):
    """
    Test we can close the port.
    """
    loop = DummyLoop()
    kissdev = kiss.TCPKISSDevice(
        host='localhost', port=8001,
        loop=loop
    )

    eq_(len(loop.readers), 0)

    # Force the port open
    kissdev.open()
    kissdev._state = kiss.KISSDeviceState.OPEN

    # Add a reader
    #loop.readers[kissdev._interface] = mock.MagicMock()

    # Now try closing the port
    kissdev._close()

    # The reader should be gone
    eq_(len(loop.readers), 0)

    # The device should not reference the port
    eq_(kissdev._interface, None)

    # The port should now be in the closed state
    eq_(kissdev._state, kiss.KISSDeviceState.CLOSED)

@mock.patch('socket.socket')
def test_on_recv_ready(mock_socket):
    """
    Test _on_recv_ready reads from serial device and passes to _receive.
    """
    loop = DummyLoop()
    kissdev = kiss.TCPKISSDevice(
        host='localhost', port=8001,
        loop=loop
    )
    assert kissdev._interface is None

    kissdev.open()

    buffer_str = b'something'
    mock_recv = mock.MagicMock()
    mock_recv.return_value = buffer_str
    mock_socket.return_value.recv = mock_recv

    # Kick the handler
    kissdev._on_recv_ready()

    # We should now see these bytes in the buffer
    eq_(bytes(kissdev._rx_buffer), buffer_str)
    eq_(mock_recv.call_count, 1)

@mock.patch('socket.socket')
def test_on_recv_ready_exception(mock_socket):
    """
    Test _on_recv_ready handles exceptions.
    """
    loop = DummyLoop()
    kissdev = kiss.TCPKISSDevice(
        host='localhost', port=8001,
        loop=loop
    )
    assert kissdev._interface is None

    kissdev.open()

    buffer_str = b'something'
    mock_recv = mock.MagicMock()
    mock_recv.raiseError.side_effect = IOError("Whoopsie")
    mock_socket.return_value.recv = mock_recv

    # Kick the handler -- there should be no error raised
    kissdev._on_recv_ready()

@mock.patch('socket.socket')
def test_send_raw_data(mock_socket):
    """
    Test _send_raw_data passes the data to the serial device.
    """
    loop = DummyLoop()
    kissdev = kiss.TCPKISSDevice(
        host='localhost', port=8001,
        loop=loop
    )
    assert kissdev._interface is None

    kissdev.open()
    msg = b'a test frame'
    mock_send = mock.MagicMock()
    mock_socket.return_value.send = mock_send

    kissdev._send_raw_data(msg)

    eq_(mock_send.call_count, 1)
    mock_send.assert_called_with(msg)
