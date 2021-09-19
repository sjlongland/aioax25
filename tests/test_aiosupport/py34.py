#!/usr/bin/env python3

from asyncio import coroutine, get_event_loop
from unittest.mock import Mock

from aioax25.aiosupport import AsyncException, wrapasync

def test_aiosupport_happy_path():
    """
    Test wrapping a coroutine in wrapasync passes through result
    """
    A_RESULT = object()
    call = {}
    callback = Mock()

    @wrapasync
    @coroutine
    def async_fn(*args, **kwargs):
        call.update(dict(
            args=args, kwargs=kwargs
        ))
        return A_RESULT

    @coroutine
    def testmain():
        async_fn("arg1", 2, 3, kwarg1=4, kwarg2=5, callback=callback)

    get_event_loop().run_until_complete(testmain())

    assert call == {
            "args": ("arg1", 2, 3),
            "kwargs": {"kwarg1": 4, "kwarg2": 5}
    }

    callback.assert_called()
    callback.assert_called_once()
    callback.assert_called_with(A_RESULT)


def test_aiosupport_exception():
    """
    Test wrapping a coroutine in wrapasync passes through exception
    """
    class MyError(Exception):
        pass

    call = {}
    callback = Mock()

    @wrapasync
    @coroutine
    def async_fn(*args, **kwargs):
        call.update(dict(
            args=args, kwargs=kwargs
        ))
        raise MyError('My error message')

    @coroutine
    def testmain():
        async_fn("arg1", 2, 3, kwarg1=4, kwarg2=5, callback=callback)

    get_event_loop().run_until_complete(testmain())

    assert call == {
            "args": ("arg1", 2, 3),
            "kwargs": {"kwarg1": 4, "kwarg2": 5}
    }

    callback.assert_called()
    callback.assert_called_once()
    (args, kwargs) = callback.call_args

    assert len(kwargs) == 0, 'kwargs=%r' % (kwargs,)
    assert len(args) == 1, 'args=%r' % (args,)
    assert isinstance(args[0], AsyncException)

    try:
        args[0].reraise()
    except MyError:
        pass
