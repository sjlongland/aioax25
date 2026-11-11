#!/usr/bin/env python3

"""
TCP KISS interface unit tests.
"""

# Most of the functionality here is common to SerialKISSDevice, so this
# really just tests that we pass the right commands to the IOLoop when
# establishing a connection.

from aioax25 import kiss
from aioax25._loop import LOOPMANAGER
import logging
from asyncio import get_event_loop

import pytest


@pytest.mark.asyncio
async def test_open():
    LOOPMANAGER.loop = None

    # This will receive the arguments passed to create_connection
    connection_args = {}

    loop = get_event_loop()

    # Make a dummy transport
    class DummyTransport(object):
        def close(self, *args, **kwargs):
            pass

        def write(self, *args, **kwargs):
            pass

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    async def _create_connection(proto_factory, **kwargs):
        # proto_factory should give us a KISSProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSProtocol)

        connection_args.update(kwargs)

        # Spoof a connection
        protocol.connection_made(DummyTransport())

    loop.create_connection = _create_connection

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            return_future=True,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        await device.open()

        # Expect a connection attempt to have been made
        assert connection_args == dict(
            host="localhost",
            port=5432,
            ssl=None,
            family=0,
            proto=0,
            flags=0,
            sock=None,
            local_addr=None,
            server_hostname=None,
        )
    finally:
        # Restore mock
        loop.create_connection = orig_create_connection


@pytest.mark.asyncio
async def test_open_fail_async():
    LOOPMANAGER.loop = None

    # This will receive the arguments passed to create_connection
    connection_args = {}

    loop = get_event_loop()

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    class MyIOError(IOError):
        pass

    async def _create_connection(proto_factory, **kwargs):
        # proto_factory should give us a KISSProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSProtocol)

        connection_args.update(kwargs)
        raise MyIOError("Connection failed")

    loop.create_connection = _create_connection

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            return_future=True,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        try:
            await device.open()
            assert False, "Open connection did not raise exception"
        except MyIOError:
            pass

        # Expect a connection attempt to have been made
        assert connection_args == dict(
            host="localhost",
            port=5432,
            ssl=None,
            family=0,
            proto=0,
            flags=0,
            sock=None,
            local_addr=None,
            server_hostname=None,
        )

        # Connection should be in the failed state
        assert device.state == kiss.KISSDeviceState.FAILED
    finally:
        # Restore mock
        loop.create_connection = orig_create_connection


@pytest.mark.asyncio
async def test_send_raw_data_no_transport():
    LOOPMANAGER.loop = None

    loop = get_event_loop()

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    async def _create_connection(proto_factory, **kwargs):
        raise IOError("Not implemented")

    loop.create_connection = _create_connection

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        # We have no active transport connected
        assert (
            device._transport is None
        ), "Transport is present when it should not be"

        # Try sending raw data, nothing should happen
        device._send_raw_data(b"boo!")
    finally:
        # Restore mock
        loop.create_connection = orig_create_connection


@pytest.mark.asyncio
async def test_send_raw_data_write_failed():
    LOOPMANAGER.loop = None

    loop = get_event_loop()

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    async def _create_connection(proto_factory, **kwargs):
        raise IOError("Not implemented")

    loop.create_connection = _create_connection

    # We will make a mock transport that will fail writes
    class TransportWriteError(IOError):
        pass

    class DummyTransport(object):
        def __init__(self):
            self.written = bytearray()

        def write(self, data):
            self.written += data
            raise TransportWriteError()

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        # We have no active transport connected
        assert (
            device._transport is None
        ), "Transport is present when it should not be"

        # Inject a transport
        device._transport = DummyTransport()

        # Try sending raw data, nothing should happen
        try:
            device._send_raw_data(b"boo!")
            assert False, "Expected TransportWriteError, got nothing!"
        except TransportWriteError:
            # This is what we wanted to see!
            pass
    finally:
        # Restore mock
        loop.create_connection = orig_create_connection
