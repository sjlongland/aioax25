#!/usr/bin/env python3

"""
Tests for signalslot wrappers
"""

from aioax25.signal import Slot


def test_slot_call():
    """
    Test the __call__ method passes the arguments given.
    """
    calls = []
    slot = Slot(
        lambda **kwa: calls.append(kwa),
        constkeyword1=1,
        constkeyword2=2,
        keyword3=3,
    )

    slot(callkeyword1=1, callkeyword2=2, keyword3=30)

    # We should have a single call
    assert len(calls) == 1
    kwargs = calls.pop(0)

    # kwargs should contain the merged keywords
    assert set(kwargs.keys()) == set(
        [
            "constkeyword1",
            "constkeyword2",
            "callkeyword1",
            "callkeyword2",
            "keyword3",
        ]
    )
    assert kwargs["constkeyword1"] == 1
    assert kwargs["constkeyword2"] == 2
    assert kwargs["callkeyword1"] == 1
    assert kwargs["callkeyword2"] == 2

    # This is given by both, call should override constructor
    assert kwargs["keyword3"] == 30


def test_slot_exception():
    """
    Test the __call__ swallows exceptions.
    """

    def _slot(**kwargs):
        raise RuntimeError("Whoopsie")

    slot = Slot(_slot)

    # This should not trigger an exception
    slot()
