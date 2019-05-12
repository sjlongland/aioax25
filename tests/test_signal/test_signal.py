#!/usr/bin/env python3

"""
Tests for signalslot wrappers
"""

from nose.tools import eq_, assert_set_equal

from aioax25.signal import Signal, Slot, OneshotSlot

def test_connect():
    """
    Test connect links a slot function to the signal.
    """
    calls = []
    signal = Signal()
    signal.connect(lambda **kw : calls.append(kw))
    signal.emit(myarg=123)
    signal.emit(myarg=456)

    eq_(len(calls),2)

    # First call should have myarg=123
    call = calls.pop(0)
    assert_set_equal(set(call.keys()), set(['myarg']))
    eq_(call['myarg'], 123)

    # Last call should have myarg=456
    call = calls.pop(0)
    assert_set_equal(set(call.keys()), set(['myarg']))
    eq_(call['myarg'], 456)

def test_connect_oneshot():
    """
    Test connect_oneshot links a slot function to the signal in one-shot mode.
    """
    calls = []
    signal = Signal()
    signal.connect_oneshot(lambda **kw : calls.append(kw))
    signal.emit(myarg=123)
    signal.emit(myarg=456)

    eq_(len(calls),1)

    # Only call should have myarg=123
    call = calls.pop(0)
    assert_set_equal(set(call.keys()), set(['myarg']))
    eq_(call['myarg'], 123)

def test_find_slot():
    """
    Test _find_slot can locate a slot
    """
    slot_fn = lambda **kw : None
    signal = Signal()
    signal.connect(slot_fn)

    slot = signal._find_slot(slot_fn)
    assert isinstance(slot, Slot)
    assert not isinstance(slot, OneshotSlot)

def test_find_oneshot_slot():
    """
    Test _find_slot can locate a one-shot slot
    """
    slot_fn = lambda **kw : None
    signal = Signal()
    signal.connect_oneshot(slot_fn)

    slot = signal._find_slot(slot_fn)
    assert isinstance(slot, Slot)   # Subclass
    assert isinstance(slot, OneshotSlot)

def test_disconnect():
    """
    Test disconnect detaches a slot function from the signal.
    """
    calls = []
    slot_fn = lambda **kw : calls.append(kw)
    signal = Signal()
    signal.connect(slot_fn)
    signal.emit(myarg=123)
    signal.disconnect(slot_fn)
    signal.emit(myarg=456)

    eq_(len(calls),1)

    # Only call should have myarg=123
    call = calls.pop(0)
    assert_set_equal(set(call.keys()), set(['myarg']))
    eq_(call['myarg'], 123)

def test_is_connected():
    """
    Test is_connected returns True for connected signals.
    """
    slot_fn = lambda **kw : None
    signal = Signal()
    signal.connect(slot_fn)
    assert signal.is_connected(slot_fn)
