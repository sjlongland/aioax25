#!/usr/bin/env python3

"""
FutureQueue: Queues up Future objects during a pending operation, and resolves
them all in one hit.
"""

from functools import partial


class FutureQueue(object):
    """
    A future queue is a helper for managing multiple Future objects that may
    be pending on a single operation to complete.  When an operation is
    started, one of these queues is instantiated and the Future objects
    added to it.  When the operation completes or fails, all added futures
    are notified.
    """

    def __init__(self, threadsafe=False):
        self._threadsafe = threadsafe
        self._futures = []

    def add(self, future, threadsafe=None):
        if threadsafe is None:
            threadsafe = self._threadsafe

        loop = future.get_loop()
        if threadsafe:
            call_soon = loop.call_soon_threadsafe
        else:
            call_soon = loop.call_soon

        self._futures.append((future, call_soon))

    def cancel(self, *args, **kwargs):
        def _cancel(future):
            future.cancel(*args, **kwargs)

        self._foreach_future(_cancel)

    def set_exception(self, *args, **kwargs):
        def _set_exception(future):
            future.set_exception(*args, **kwargs)

        self._foreach_future(_set_exception)

    def set_result(self, *args, **kwargs):
        def _set_result(future):
            future.set_result(*args, **kwargs)

        self._foreach_future(_set_result)

    def _foreach_future(self, action):
        for future, call_soon in self._futures:
            if future.done():
                continue
            call_soon(partial(action, future))
