#!/usr/bin/python3

"""
Asynchronous function wrappers.  Python 3.4 and Python 3.10+ have incompatible
mechanisms for asynchronous routines, with Python 3.4-3.9 supporting
coroutine/yield from and Python 3.5+ supporting async/await.

This routine selects an implementation that will work with the running version
of Python.
"""

# Branch used will depend on the version of Python, and right now we
# only do test coverage on Python 3.9.
#
# pragma: no cover

from sys import version_info
from .exception import AsyncException
from asyncio import ensure_future, iscoroutine, isfuture

if version_info.major < 3:
    # Python 2 or earlier, not supported (how did they get here?)
    raise NotImplementedError('Python 3.4 minimum is required')
elif (version_info.major == 3) and (version_info.minor < 4):
    # Python 3.0-3.3
    raise NotImplementedError('Python 3.4 minimum is required')
elif (version_info.major == 3) and (version_info.minor == 4):
    # Python 3.4
    from .py34 import wrapasync
    USE_COROUTINE = True
else:
    # Python 3.5+
    from .py35 import wrapasync
    USE_COROUTINE = False

assert AsyncException
assert wrapasync
assert USE_COROUTINE is not None

def exec_async(obj):
    if iscoroutine(obj) or isfuture(obj):
        return ensure_future(obj)
    else:
        return obj


__ALL__ = ['USE_COROUTINE', 'AsyncException', 'wrapasync', 'exec_async']
