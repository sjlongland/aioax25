#!/usr/bin/env python3

"""
Serial KISS interface unit tests. (Python 3.5+)
"""

from ..serial_common import kiss, connections, DummySerial, TestDevice
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from ...asynctest import asynctest
from collections import namedtuple
from asyncio import get_event_loop, sleep

import time

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
    assert kissdev._serial is None

    kissdev.open()
    await sleep(0.01)

    # We should have created a new port
    assert len(connections) == 1
    connection = connections.pop(0)

    # We should have a reference to the transport created.
    assert kissdev._serial == connection.transport

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
    kissdev._serial = serial

    # Now try closing the port
    kissdev.close()
    await sleep(0.01)

    # The port should have been flushed
    assert serial.flushes == 1

    # The port should be closed
    assert serial.closed == True

    # The device should not reference the port
    assert kissdev._serial == None

    # The port should now be in the closed state
    assert kissdev._state == kiss.KISSDeviceState.CLOSED


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
    assert kissdev._serial is None

    kissdev.open()
    await sleep(0.01)

    # We should have created a new port
    assert len(connections) == 1
    connection = connections.pop(0)

    kissdev._send_raw_data(b'a test frame')
    assert bytes(connection.port.tx_buffer) == b'a test frame'
