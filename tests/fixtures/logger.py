#!/usr/bin/env python3

"""
A logging.Logger substitute for testing purposes.
"""

# Was going to use pytest_logdog, *BUT* that needs Python 3.7+ and I'm
# targetting Python 3.4!

import pytest
from sys import exc_info


class DummyLogger(object):
    def __init__(self):
        self.logrecords = []
        self.children = {}

    def _addrecord(self, log_method, log_args, log_kwargs, _exc_info=False):
        if _exc_info:
            (ex_type, ex_val, ex_tb) = exc_info()
        else:
            ex_type = None
            ex_val = None
            ex_tb = None

        self.logrecords.append(dict(
            method=log_method, args=log_args, kwargs=log_kwargs,
            ex_type=ex_type, ex_val=ex_val, ex_tb=ex_tb
        ))

    # Message logging endpoints
    def critical(self, *args, exc_info=False, **kwargs):
        self._addrecord('critical', args, kwargs, exc_info)

    def debug(self, *args, exc_info=False, **kwargs):
        self._addrecord('debug', args, kwargs, exc_info)

    def error(self, *args, exc_info=False, **kwargs):
        self._addrecord('error', args, kwargs, exc_info)

    def exception(self, *args, **kwargs):
        self._addrecord('exception', args, kwargs, True)

    def fatal(self, *args, exc_info=False, **kwargs):
        self._addrecord('fatal', args, kwargs, exc_info)

    def info(self, *args, exc_info=False, **kwargs):
        self._addrecord('info', args, kwargs, exc_info)

    def log(self, *args, exc_info=False, **kwargs):
        self._addrecord('log', args, kwargs, exc_info)

    def warn(self, *args, exc_info=False, **kwargs):
        self._addrecord('warn', args, kwargs, exc_info)

    def warning(self, *args, exc_info=False, **kwargs):
        self._addrecord('warning', args, kwargs, exc_info)

    # Info endpoints
    def isEnabledFor(self, level):
        return True

    # Hierarchy endpoints
    def getChild(self, suffix):
        try:
            return self.children[suffix]
        except KeyError:
            child = DummyLogger()
            self.children[suffix] = child
            return child


@pytest.fixture
def logger():
    """Dummy logger instance that mocks logging.Logger."""
    return DummyLogger()
