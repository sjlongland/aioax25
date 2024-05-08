#!/usr/bin/env python3

"""
TCP KISS interface unit tests.
"""

# Most of the functionality here is common to SerialKISSDevice, so this
# really just tests that we pass the right commands to the IOLoop when
# establishing a connection.

from aioax25 import kiss
import logging
from ..asynctest import asynctest
from asyncio import get_event_loop


@asynctest
async def test_open_connection():
    # This will receive the arguments passed to create_connection
    connection_args = {}

    loop = get_event_loop()

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    async def _create_connection(proto_factory, **kwargs):
        # proto_factory should give us a KISSProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSProtocol)

        connection_args.update(kwargs)

    loop.create_connection = _create_connection

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        await device._open_connection()

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


@asynctest
async def test_open_connection_fail():
    # This will receive the arguments passed to create_connection
    connection_args = {}

    loop = get_event_loop()

    # Stub the create_connection method
    orig_create_connection = loop.create_connection

    async def _create_connection(proto_factory, **kwargs):
        # proto_factory should give us a KISSProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSProtocol)

        connection_args.update(kwargs)
        raise IOError("Connection failed")

    loop.create_connection = _create_connection

    try:
        device = kiss.TCPKISSDevice(
            host="localhost",
            port=5432,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        failures = []

        def _on_fail(**kwargs):
            failures.append(kwargs)

        device.failed.connect(_on_fail)

        await device._open_connection()

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

        # Failure should have been reported
        assert failures
        failure = failures.pop(0)

        assert failure.pop("action") == "open"
        (ex_c, ex_v, _) = failure.pop("exc_info")
        assert ex_c is IOError
        assert str(ex_v) == "Connection failed"
    finally:
        # Restore mock
        loop.create_connection = orig_create_connection
