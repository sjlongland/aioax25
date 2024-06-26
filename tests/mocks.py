#!/usr/bin/env python3

import time
import logging
from signalslot import Signal
from aioax25.version import AX25Version


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


class DummyLogger(object):
    def __init__(self, name, parent=None):
        self.parent = parent
        self.name = name
        self.logs = []

    def _log(self, name, level, msg, *args, **kwargs):
        if self.parent is not None:
            self.parent._log(self.name, level, msg, *args, **kwargs)
        self.logs.append((self.name, level, msg, args, kwargs))

    def log(self, level, msg, *args, **kwargs):
        self._log(self.name, level, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def getChild(self, name):
        return DummyLogger(self.name + "." + name, parent=self)

    def isEnabledFor(self, level):
        return True


class DummyTimeout(object):
    def __init__(self, delay, callback, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.callback = callback
        self.delay = delay

        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class DummyIOLoop(object):
    def __init__(self):
        self.call_soon_list = []
        self.call_later_list = []

    def time(self):
        return time.monotonic()

    def call_soon(self, callback, *args, **kwargs):
        self.call_soon_list.append((callback, args, kwargs))

    def call_later(self, delay, callback, *args, **kwargs):
        timeout = DummyTimeout(delay, callback, *args, **kwargs)
        self.call_later_list.append(timeout)
        return timeout


class DummyStation(object):
    def __init__(self, address, reply_path=None):
        self._interface_ref = DummyInterface()
        self.address = address
        self.reply_path = reply_path or []
        self._full_duplex = False
        self._protocol = AX25Version.AX25_22
        self.connection_request = Signal()

    def _interface(self):
        return self._interface_ref


class DummyPeer(object):
    def __init__(self, station, address):
        self._station_ref = station
        self._log = DummyLogger("peer")
        self._loop = DummyIOLoop()

        self._max_retries = 2
        self._ack_timeout = 0.1

        self.address_read = False
        self._address = address

        self._negotiate_calls = []
        self.transmit_calls = []
        self.on_receive_calls = []

        self._testframe_handler = None
        self._uaframe_handler = None
        self._frmrframe_handler = None
        self._dmframe_handler = None
        self._sabmframe_handler = None
        self._xidframe_handler = None

        self._negotiated = False
        self._protocol = AX25Version.UNKNOWN

        self._modulo128 = False
        self._init_connection_modulo = None

    # Our fake weakref
    def _station(self):
        return self._station_ref

    @property
    def address(self):
        self.address_read = True
        return self._address

    def _init_connection(self, extended):
        if extended is True:
            self._init_connection_modulo = 128
        elif extended is False:
            self._init_connection_modulo = 8
        else:
            raise ValueError("Invalid extended value %r" % extended)

    def _negotiate(self, callback):
        self._negotiate_calls.append(callback)

    def _on_receive(self, *args, **kwargs):
        self.on_receive_calls.append((args, kwargs))

    def _transmit_frame(self, frame, callback=None):
        self.transmit_calls.append((frame, callback))

    def _send_sabm(self):
        self._transmit_frame("sabm")

    def _send_dm(self):
        self._transmit_frame("dm")

    def _send_xid(self, cr=False):
        self._transmit_frame("xid:cr=%s" % cr)
