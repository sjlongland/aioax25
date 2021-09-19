#!/usr/bin/env python3

from aioax25.aiosupport import USE_COROUTINE

if USE_COROUTINE:
    from .py34 import test_aiosupport_happy_path, test_aiosupport_exception
else:
    from .py35 import test_aiosupport_happy_path, test_aiosupport_exception
