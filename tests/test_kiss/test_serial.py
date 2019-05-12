#!/usr/bin/env python3

"""
Serial KISS interface unit tests.
"""

from aioax25 import kiss
import time
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from nose.tools import eq_, assert_less, assert_in
from ..loop import DummyLoop

class DummySerial(object):
    FILENO = 123

    def __init__(self, port, baudrate, bytesize, parity, stopbits,
            timeout, xonxoff, rtscts, write_timeout, dsrdtr,
            inter_byte_timeout):

        eq_(port, '/dev/ttyS0')
        eq_(baudrate, 9600)
        eq_(bytesize, EIGHTBITS)
        eq_(parity, PARITY_NONE)
        eq_(stopbits, STOPBITS_ONE)
        eq_(timeout, None)
        eq_(xonxoff, False)
        eq_(rtscts, False)
        eq_(write_timeout, None)
        eq_(dsrdtr, False)
        eq_(inter_byte_timeout, None)

        self.rx_buffer = bytearray()
        self.tx_buffer = bytearray()
        self.flushes = 0
        self.closed = False
        self.read_exception = None

    def fileno(self):
        return self.FILENO

    def flush(self):
        self.flushes += 1

    def write(self, data):
        self.tx_buffer += data

    def read(self, length):
        if self.read_exception is not None:
            raise self.read_exception

        data = self.rx_buffer[0:length]
        self.rx_buffer = self.rx_buffer[length:]
        return data

    def close(self):
        self.closed = True

    @property
    def in_waiting(self):
        return len(self.rx_buffer)


# Stub the serial port class
kiss.Serial = DummySerial


def test_open():
    """
    Test we can open the port.
    """
    loop = DummyLoop()
    kissdev = kiss.SerialKISSDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._serial is None

    kissdev.open()

    # kissdev._serial should now be a DummySerial instance
    assert isinstance(kissdev._serial, DummySerial)

    # A reader should have been added
    assert_in(kissdev._serial.fileno(), loop.readers)
    eq_(loop.readers[DummySerial.FILENO], kissdev._on_recv_ready)

    # A call to initialise the device should have been scheduled.
    eq_(len(loop.calls), 1)
    (calltime, callfunc) = loop.calls.pop(0)
    assert_less(time.monotonic() - calltime, 0.01)
    eq_(callfunc, kissdev._init_kiss)


def test_close():
    """
    Test we can close the port.
    """
    loop = DummyLoop()
    kissdev = kiss.SerialKISSDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop, reset_on_close=False
    )

    # Force the port open
    kissdev._state = kiss.KISSDeviceState.OPEN
    serial = DummySerial(port='/dev/ttyS0', baudrate=9600,
            bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
            timeout=None, xonxoff=False, rtscts=False, write_timeout=None,
            dsrdtr=False, inter_byte_timeout=None)
    kissdev._serial = serial
    
    # Add a reader
    loop.readers[DummySerial.FILENO] = lambda *a, **k : None

    # Now try closing the port
    kissdev.close()

    # The reader should be gone
    eq_(len(loop.readers), 0)

    # The port should have been flushed
    eq_(serial.flushes, 1)

    # The port should be closed
    eq_(serial.closed, True)

    # The device should not reference the port
    eq_(kissdev._serial, None)

    # The port should now be in the closed state
    eq_(kissdev._state, kiss.KISSDeviceState.CLOSED)

def test_on_recv_ready():
    """
    Test _on_recv_ready reads from serial device and passes to _receive.
    """
    loop = DummyLoop()
    kissdev = kiss.SerialKISSDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._serial is None

    kissdev.open()
    kissdev._serial.rx_buffer += b'a test frame'

    # Kick the handler
    kissdev._on_recv_ready()

    # We should now see these bytes in the buffer
    eq_(bytes(kissdev._rx_buffer), b'a test frame')

def test_on_recv_ready_exception():
    """
    Test _on_recv_ready handles exceptions.
    """
    loop = DummyLoop()
    kissdev = kiss.SerialKISSDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._serial is None

    kissdev.open()
    kissdev._serial.read_exception = IOError('Whoopsie')
    kissdev._serial.rx_buffer += b'a test frame'

    # Kick the handler -- there should be no error raised
    kissdev._on_recv_ready()

def test_send_raw_data():
    """
    Test _send_raw_data passes the data to the serial device.
    """
    loop = DummyLoop()
    kissdev = kiss.SerialKISSDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._serial is None

    kissdev.open()
    kissdev._send_raw_data(b'a test frame')
    eq_(bytes(kissdev._serial.tx_buffer), b'a test frame')
