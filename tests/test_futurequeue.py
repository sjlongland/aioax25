#!/usr/bin/env python3

"""
FutureQueue tests
"""

from aioax25.futurequeue import FutureQueue
import logging
from .asynctest import asynctest
from asyncio import get_event_loop, sleep


@asynctest
async def test_cancellation():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2)
    queue.add(f3)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Cancel them
    queue.cancel()

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all cancelled
    assert f1.cancelled()
    assert f2.cancelled()
    assert f3.cancelled()


@asynctest
async def test_cancellation_threadsafe():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2, True)
    queue.add(f3, False)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Cancel them
    queue.cancel()

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all cancelled
    assert f1.cancelled()
    assert f2.cancelled()
    assert f3.cancelled()


@asynctest
async def test_exception():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2)
    queue.add(f3)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Inject an exception
    ex = IOError("Mock Exception")

    # Reject them
    queue.set_exception(ex)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.exception() is ex
    assert f2.done()
    assert f2.exception() is ex
    assert f3.done()
    assert f3.exception() is ex


@asynctest
async def test_exception_skipdone():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2)
    queue.add(f3)

    # Alter the state of these futures
    f1.set_result(123)
    f2_ex = IOError("Something failed")
    f2.set_exception(f2_ex)
    f3.cancel()

    # Inject an exception
    ex = IOError("Mock Exception")

    # Reject them
    queue.set_exception(ex)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.result() == 123
    assert f2.done()
    assert f2.exception() is f2_ex
    assert f3.done()
    assert f3.cancelled()


@asynctest
async def test_exception_threadsafe():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2, True)
    queue.add(f3, False)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Inject an exception
    ex = IOError("Mock Exception")

    # Reject them
    queue.set_exception(ex)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.exception() is ex
    assert f2.done()
    assert f2.exception() is ex
    assert f3.done()
    assert f3.exception() is ex


@asynctest
async def test_result():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2)
    queue.add(f3)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Resolve them
    queue.set_result(42)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.result() == 42
    assert f2.done()
    assert f2.result() == 42
    assert f3.done()
    assert f3.result() == 42


@asynctest
async def test_result_skipdone():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2)
    queue.add(f3)

    # Alter the state of these futures
    f1.set_result(123)
    f2_ex = IOError("Something failed")
    f2.set_exception(f2_ex)
    f3.cancel()

    # Resolve them
    queue.set_result(42)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.result() == 123
    assert f2.done()
    assert f2.exception() is f2_ex
    assert f3.done()
    assert f3.cancelled()


@asynctest
async def test_result_threadsafe():
    loop = get_event_loop()

    queue = FutureQueue()
    f1 = loop.create_future()
    f2 = loop.create_future()
    f3 = loop.create_future()

    queue.add(f1)
    queue.add(f2, True)
    queue.add(f3, False)

    assert not f1.done()
    assert not f2.done()
    assert not f3.done()

    # Resolve them
    queue.set_result(42)

    # Wait for cancellation
    await sleep(0.1)

    # Ensure they're all done
    assert f1.done()
    assert f1.result() == 42
    assert f2.done()
    assert f2.result() == 42
    assert f3.done()
    assert f3.result() == 42
