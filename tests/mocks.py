#!/usr/bin/env python3

class DummyInterface(object):
    def __init__(self):
        self.bind_calls = []
        self.unbind_calls = []
        self.transmit_calls = []

    def bind(self, *args, **kwargs):
        self.bind_calls.append((args, kwargs))

    def unbind(self, *args, **kwargs):
        self.unbind_calls.append((args, kwargs))

    def transmit(self, *args, **kwargs):
        self.transmit_calls.append((args, kwargs))
