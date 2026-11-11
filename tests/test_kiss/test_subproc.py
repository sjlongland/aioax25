#!/usr/bin/env python3

"""
Subprocess KISS interface unit tests.
"""

# Most of the functionality here is common to SerialKISSDevice, so this
# really just tests that we pass the right commands to the IOLoop when
# establishing a connection.

from aioax25 import kiss
from aioax25._loop import LOOPMANAGER
import logging
from asyncio import get_event_loop

import pytest


# Mock transport
class DummyStream(object):
    def __init__(self):
        self.written = b""

    def write(self, data):
        self.written += bytes(data)


class DummyTransport(object):
    def __init__(self):
        self.stdin = DummyStream()

    def get_pipe_transport(self, fd):
        assert fd == 0
        return self.stdin


# Exception class for confirming code path
class MyIOError(IOError):
    pass


@pytest.mark.asyncio
async def test_open():
    """
    Test we can open a subprocess without using a shell.
    """
    LOOPMANAGER.loop = None

    # This will receive the arguments passed to subprocess_exec
    connection_args = []

    loop = get_event_loop()

    # Stub the subprocess_exec method
    orig_subprocess_exec = loop.subprocess_exec

    async def _subprocess_exec(proto_factory, *args):
        # proto_factory should give us a KISSSubprocessProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSSubprocessProtocol)

        connection_args.extend(args)
        protocol.connection_made(DummyTransport())

    loop.subprocess_exec = _subprocess_exec

    try:
        device = kiss.SubprocKISSDevice(
            command=["kisspipecmd", "arg1", "arg2"],
            return_future=True,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        await device.open()

        # Expect a connection attempt to have been made
        assert connection_args == ["kisspipecmd", "arg1", "arg2"]
    finally:
        # Restore mock
        loop.subprocess_exec = orig_subprocess_exec


@pytest.mark.asyncio
async def test_open_shell():
    """
    Test we can open a subprocess using a shell.
    """
    LOOPMANAGER.loop = None

    # This will receive the arguments passed to subprocess_shell
    connection_args = []

    loop = get_event_loop()

    # Stub the subprocess_shell method
    orig_subprocess_shell = loop.subprocess_shell

    async def _subprocess_shell(proto_factory, *args):
        # proto_factory should give us a KISSSubprocessProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSSubprocessProtocol)

        connection_args.extend(args)
        protocol.connection_made(DummyTransport())

    loop.subprocess_shell = _subprocess_shell

    try:
        device = kiss.SubprocKISSDevice(
            command=["kisspipecmd", "arg1", "arg2"],
            shell=True,
            return_future=True,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        await device.open()

        # Expect a connection attempt to have been made
        assert connection_args == ["kisspipecmd arg1 arg2"]
    finally:
        # Restore mock
        loop.subprocess_shell = orig_subprocess_shell


@pytest.mark.asyncio
async def test_open_failure():
    """
    Test subprocess failure is detected and handled.
    """
    LOOPMANAGER.loop = None

    # This will receive the arguments passed to subprocess_shell
    connection_args = []

    loop = get_event_loop()

    # Stub the subprocess_shell method
    orig_subprocess_shell = loop.subprocess_shell

    async def _subprocess_shell(proto_factory, *args):
        # proto_factory should give us a KISSSubprocessProtocol object
        protocol = proto_factory()
        assert isinstance(protocol, kiss.KISSSubprocessProtocol)

        connection_args.extend(args)
        raise MyIOError("Exec failed")

    loop.subprocess_shell = _subprocess_shell

    try:
        device = kiss.SubprocKISSDevice(
            command=["kisspipecmd", "arg1", "arg2"],
            shell=True,
            return_future=True,
            loop=loop,
            log=logging.getLogger(__name__),
        )

        failures = []

        def _on_fail(**kwargs):
            failures.append(kwargs)

        device.failed.connect(_on_fail)

        try:
            await device.open()
            assert False, "Should not have succeeded"
        except MyIOError:
            pass

        # Expect a connection attempt to have been made
        assert connection_args == ["kisspipecmd arg1 arg2"]

        # Connection should be in the failed state
        assert device.state == kiss.KISSDeviceState.FAILED

        # Failure should have been reported
        assert failures
        failure = failures.pop(0)

        assert failure.pop("action") == "open"
        ex_c, ex_v, _ = failure.pop("exc_info")
        assert ex_c is MyIOError
        assert str(ex_v) == "Exec failed"
    finally:
        # Restore mock
        loop.subprocess_shell = orig_subprocess_shell


@pytest.mark.asyncio
async def test_send_raw_data():
    """
    Test data written to the device gets written to the subprocess ``stdin``.
    """
    LOOPMANAGER.loop = None

    loop = get_event_loop()

    device = kiss.SubprocKISSDevice(
        command=["kisspipecmd", "arg1", "arg2"],
        loop=loop,
        log=logging.getLogger(__name__),
    )
    device._transport = DummyTransport()

    device._send_raw_data(b"testing")

    assert device._transport.stdin.written == b"testing"
