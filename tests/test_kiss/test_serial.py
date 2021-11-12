#!/usr/bin/env python3

"""
Serial KISS interface unit tests.
"""

from aioax25 import kiss, aiosupport

if aiosupport.USE_COROUTINE:
    # Python 3.4
    from .py34.serial import test_open, test_close, test_send_raw_data
else:
    # Python 3.5+
    from .py35.serial import test_open, test_close, test_send_raw_data

assert test_open
assert test_close
assert test_send_raw_data
