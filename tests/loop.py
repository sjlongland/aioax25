#!/usr/bin/env python3

"""
Dummy IOLoop interface
"""

import time

class DummyLoop(object):
    def __init__(self):
        self.readers = {}
        self.calls = []

    def time(self):
        return time.monotonic()

    def call_soon(self, callback, *args):
        self.calls.append((self.time(), callback) + args)

    def call_later(self, delay, callback, *args):
        when = self.time() + delay
        self.calls.append((when, callback) + args)
        return DummyTimeoutHandle(when)

    def add_reader(self, fileno, reader):
        self.readers[fileno] = reader

    def remove_reader(self, fileno):
        self.readers.pop(fileno)


class DummyTimeoutHandle(object):
    def __init__(self, when):
        self._when = when
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    # Note: Don't rely on this in real code in Python <3.6 as
    # these methods were added in 3.7.

    def when(self):
        return self._when

    def cancelled(self):
        return self._cancelled
