#!/usr/bin/env python3

"""
Serial KISS interface unit tests.
"""

from collections import namedtuple
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from aioax25 import kiss
import logging
from ..asynctest import asynctest
from asyncio import get_event_loop, sleep


class DummySerial(object):
    def __init__(self, port, baudrate, bytesize, parity, stopbits,
            timeout, xonxoff, rtscts, write_timeout, dsrdtr,
            inter_byte_timeout):

        assert port == '/dev/ttyS0'
        assert baudrate == 9600
        assert bytesize == EIGHTBITS
        assert parity == PARITY_NONE
        assert stopbits == STOPBITS_ONE
        assert timeout == None
        assert xonxoff == False
        assert rtscts == False
        assert write_timeout == None
        assert dsrdtr == False
        assert inter_byte_timeout == None

        self.rx_buffer = bytearray()
        self.tx_buffer = bytearray()
        self.flushes = 0
        self.closed = False
        self.read_exception = None

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


# Dummy transport
class DummyTransport(object):
    def __init__(self, loop, port):
        self._loop = loop
        self._port = port

    def flush(self):
        future = self._loop.create_future()
        self._loop.call_soon(lambda : future.set_result(None))
        return future

    def write(self, *args, **kwargs):
        future = self._loop.create_future()
        self._port.write(*args, **kwargs)
        self._loop.call_soon(lambda : future.set_result(None))
        return future


# Keep a record of all ports, transports and protocols
PortConnection = namedtuple('PortConnection', ['port', 'protocol', 'transport'])
create_serial_conn_log = logging.getLogger('create_serial_connection')
connections = []

# Stub the serial port connection factory
async def dummy_create_serial_connection(loop, proto_factory, *args, **kwargs):
    future = loop.create_future()
    create_serial_conn_log.debug(
            'Creating new serial connection: '
            'loop=%r proto=%r args=%r kwargs=%r',
            loop, proto_factory, args, kwargs
    )

    def _open():
        create_serial_conn_log.debug('Creating objects')
        # Create the objects
        protocol = proto_factory()
        port = DummySerial(*args, **kwargs)
        transport = DummyTransport(loop, port)

        # Record the created object references
        connections.append(PortConnection(
            port=port, protocol=protocol, transport=transport
        ))

        # Pass the protocol the transport object
        create_serial_conn_log.debug('Passing transport to protocol')
        protocol.connection_made(transport)

        # Finish up the future
        create_serial_conn_log.debug('Finishing up')
        future.set_result((protocol, transport))

    create_serial_conn_log.debug('Scheduled in IOLoop')
    loop.call_soon(_open)

    create_serial_conn_log.debug('Returning future')
    return (await future)

kiss.create_serial_connection = dummy_create_serial_connection


class TestDevice(kiss.SerialKISSDevice):
    def __init__(self, *args, **kwargs):
        super(TestDevice, self).__init__(*args, **kwargs)
        self.init_called = False

    def _init_kiss(self):
        self.init_called = True


@asynctest
async def test_open():
    """
    Test we can open the port.
    """
    loop = get_event_loop()
    kissdev = TestDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._transport is None

    kissdev.open()
    await sleep(0.01)

    # We should have created a new port
    assert len(connections) == 1
    connection = connections.pop(0)

    # We should have a reference to the transport created.
    assert kissdev._transport == connection.transport

    # The device should have been initialised
    assert kissdev.init_called


@asynctest
async def test_close():
    """
    Test we can close the port.
    """
    loop = get_event_loop()
    kissdev = TestDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop, reset_on_close=False
    )

    # Force the port open
    kissdev._state = kiss.KISSDeviceState.OPEN
    serial = DummySerial(port='/dev/ttyS0', baudrate=9600,
            bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
            timeout=None, xonxoff=False, rtscts=False, write_timeout=None,
            dsrdtr=False, inter_byte_timeout=None)
    kissdev._transport = serial

    # Now try closing the port
    kissdev.close()
    await sleep(0.01)

    # The port should have been flushed
    assert serial.flushes == 1

    # The port should be closed
    assert serial.closed == True

    # The device should not reference the port
    assert kissdev._transport == None

    # The port should now be in the closed state
    assert kissdev._state == kiss.KISSDeviceState.CLOSED


def test_on_close_err(logger):
    """
    Test errors are logged if given
    """
    # Yeah, kludgy… but py.test won't see the fixture if I don't
    # do it this way.
    @asynctest
    async def _run():
        loop = get_event_loop()
        kissdev = TestDevice(
                device='/dev/ttyS0', baudrate=9600,
                log=logger, loop=loop, reset_on_close=False
        )

        # Force the port open
        kissdev._state = kiss.KISSDeviceState.OPEN
        serial = DummySerial(port='/dev/ttyS0', baudrate=9600,
                bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
                timeout=None, xonxoff=False, rtscts=False, write_timeout=None,
                dsrdtr=False, inter_byte_timeout=None)
        kissdev._transport = serial

        # Define a close error
        class CommsError(IOError):
            pass
        my_err = CommsError()

        # Now report the closure of the port
        kissdev._on_close(my_err)

        # We should have seen a log message reported
        assert logger.logrecords == [
                dict(
                    method='error',
                    args=('Closing port due to error %r', my_err,),
                    kwargs={},
                    ex_type=None, ex_val=None, ex_tb=None
                )
        ]

        # The device should not reference the port
        assert kissdev._transport == None

        # The port should now be in the closed state
        assert kissdev._state == kiss.KISSDeviceState.CLOSED
    _run()


@asynctest
async def test_send_raw_data():
    """
    Test _send_raw_data passes the data to the serial device.
    """
    loop = get_event_loop()
    kissdev = TestDevice(
            device='/dev/ttyS0', baudrate=9600,
            loop=loop
    )
    assert kissdev._transport is None

    kissdev.open()
    await sleep(0.01)

    # We should have created a new port
    assert len(connections) == 1
    connection = connections.pop(0)

    kissdev._send_raw_data(b'a test frame')
    assert bytes(connection.port.tx_buffer) == b'a test frame'
