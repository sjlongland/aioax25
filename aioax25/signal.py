#!/usr/bin/env python3

"""
Convenience wrappers around `signalslot`
"""

from signalslot import Signal as BaseSignal, Slot as BaseSlot
from weakref import ref
import logging


class Slot(BaseSlot):
    """
    Wrapper class around a slot function.  This will wrap the given slot up in
    an exception handler.  It is the caller's responsibility to ensure the
    slot function handles its own exceptions.
    """
    def __init__(self, slot_fn, **kwargs):
        super(Slot, self).__init__(slot_fn)
        self._slot_kwargs = kwargs

    def __call__(self, **kwargs):
        try:
            call_kwargs = self._slot_kwargs.copy()
            call_kwargs.update(kwargs)
            super(Slot, self).__call__(**call_kwargs)
        except:
            logging.getLogger(self.__class__.__module__).exception(
                    'Exception in slot %s', self.func
            )


class OneshotSlot(Slot):
    """
    Helper class that calls a slot exactly once.
    """
    def __init__(self, signal, slot_fn, **kwargs):
        self._signal = ref(signal)
        super(OneshotSlot, self).__init__(slot_fn, **kwargs)

    def __call__(self, **kwargs):
        super(OneshotSlot, self).__call__(**kwargs)
        signal = self._signal()
        if signal:
            signal.disconnect(self)


class Signal(BaseSignal):
    """
    Wrap the `signalslot.Signal` so that *all* "slots" get called, regardless
    of whether they return something or not, or throw exceptions.
    """
    def connect(self, slot, **kwargs):
        """
        Connect a slot to the signal.  This will wrap the given slot up in
        an exception handler.  It is the caller's responsibility to ensure
        the slot handles its own exceptions.
        """
        super(Signal, self).connect(Slot(slot, **kwargs))

    def connect_oneshot(self, slot, **kwargs):
        """
        Connect a slot to the signal, and call it exactly once when the
        signal fires.  (Disconnect after calling.)
        """
        super(Signal, self).connect(OneshotSlot(self, slot, **kwargs))

    def _find_slot(self, slot):
        """
        Locate a slot connected to the signal.
        """
        for maybe_slot in super(Signal, self).slots:
            if isinstance(maybe_slot, Slot) and \
                    (maybe_slot.func is slot):
                # Here it is
                return maybe_slot
            elif maybe_slot is slot:
                # Here it is
                return maybe_slot

    def disconnect(self, slot):
        """
        Disconnect the first located matching slot.
        """
        slot = self._find_slot(slot)
        if slot:
            super(Signal, self).disconnect(slot)

    def is_connected(self, slot):
        """
        Check if a callback slot is connected to this signal.
        """
        if isinstance(slot, Slot):
            return super(Signal, self).is_connected(slot.func)
        else:
            return super(Signal, self).is_connected(slot)
