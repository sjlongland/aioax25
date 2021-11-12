#!/usr/bin/env python3

"""
Serial KISS interface unit test fixtures
"""

from collections import namedtuple
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from aioax25 import kiss
import logging


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
def dummy_create_serial_connection(loop, proto_factory, *args, **kwargs):
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
    return future

kiss.create_serial_connection = dummy_create_serial_connection


class TestDevice(kiss.SerialKISSDevice):
    def __init__(self, *args, **kwargs):
        super(TestDevice, self).__init__(*args, **kwargs)
        self.init_called = False

    def _init_kiss(self):
        self.init_called = True
