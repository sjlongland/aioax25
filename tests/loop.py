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
        self.calls.append((self.time() + delay, callback) + args)

    def add_reader(self, fileno, reader):
        self.readers[fileno] = reader

    def remove_reader(self, fileno):
        self.readers.pop(fileno)
