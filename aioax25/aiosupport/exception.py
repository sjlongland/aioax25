#!/usr/bin/env python3

"""
AsyncIO support routines, for all Python versions.
"""

from sys import exc_info


class AsyncException(object):
    """
    Wrapper around an exception.  This captures the exception traceback on
    the stack so it can be passed in a callback and re-raised.
    """
    def __init__(self, extype=None, value=None, tb=None):
        if extype is None:
            (extype, value, tb) = exc_info()

        self.extype = extype
        self.value = value
        self.tb = tb

    def reraise(self):
        """
        Re-raise the previously thrown exception.
        """
        # This routine is taken from six:
        # Copyright (c) 2010-2020 Benjamin Peterson
        #
        # Permission is hereby granted, free of charge, to any person obtaining
        # a copy of this software and associated documentation files (the
        # "Software"), to deal in the Software without restriction, including
        # without limitation the rights to use, copy, modify, merge, publish,
        # distribute, sublicense, and/or sell copies of the Software, and to
        # permit persons to whom the Software is furnished to do so, subject to
        # the following conditions:
        #
        # The above copyright notice and this permission notice shall be
        # included in all copies or substantial portions of the Software.
        #
        # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
        # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
        # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
        # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
        # BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
        # ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
        # CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        # SOFTWARE.
        #
        # https://github.com/benjaminp/six/blob/3974f0c4f6700a5821b451abddff8b3ba6b2a04f/six.py#L713-L722
        try:
            if self.value is None:
                value = self.extype()
            else:
                value = self.value

            if value.__traceback__ is not self.tb:
                raise value.with_traceback(self.tb)

            raise value
        finally:
            self.value = None
            self.tb = None
