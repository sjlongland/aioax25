#!/usr/bin/env python3

"""
AsyncIO support routines, for Python 3.4.

Newer Python (3.5+) prefers the use of async/await, but Debian Jessie, Windows
XP and some other platforms are unable to easily run this release of Python
without considerable effort (or at all).  So, let's throw them a lifeline.
"""

from asyncio import ensure_future, coroutine
from ..exception import AsyncException
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

        @coroutine
        def _exec_async():
            try:
                res = yield from fn(*args, **kwargs)
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
