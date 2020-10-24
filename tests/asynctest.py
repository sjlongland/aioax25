#!/usr/bin/env python3

"""
Asynchronous test case handler.
"""

from asyncio import get_event_loop
from functools import wraps

def asynctest(testcase, *args, **kwargs):
    """
    Wrap an asynchronous test case.
    """
    @wraps(testcase)
    def fn():
        return get_event_loop().run_until_complete(testcase(*args, **kwargs))

    return fn
