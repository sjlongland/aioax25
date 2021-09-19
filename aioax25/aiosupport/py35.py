#!/usr/bin/env python3

"""
AsyncIO support routines, for Python 3.5+.  Python 3.5 introduces
async/await, with Python 3.9 warning about coroutine being deprecated.
"""

from asyncio import ensure_future
from .exception import AsyncException
from functools import wraps
import logging
from sys import exit

def wrapasync(fn):
    """
    Wrap the asynchronous function so that it can execute in a "synchronous"
    context.  The wrapped function must receive a `callback` as a keyword
    argument.
    """
    @wraps(fn)
    def _exec_sync(*args, **kwargs):
        callback = kwargs.pop('callback')

        async def _exec_async():
            try:
                res = await fn(*args, **kwargs)
            except:
                res = AsyncException()

            try:
                callback(res)
            except: # pragma: no cover
                # This should not happen, panic!
                logging.getLogger(__name__).exception(
                        'Exception in callback routine!'
                )
                exit(1)

        ensure_future(_exec_async())

    return _exec_sync
