#!/usr/bin/env python3

from aioax25.signal import Signal
from aioax25.interface import AX25Interface
from aioax25.frame import AX25UnnumberedInformationFrame

from ..asynctest import asynctest
from asyncio import Future, get_event_loop, sleep, coroutine

from nose.tools import assert_greater, assert_less, assert_is, \
        assert_greater_equal, eq_

import time
import re


class DummyKISS(object):
    """
    Dummy KISS interface for unit testing.
    """
    def __init__(self):
        self.received = Signal()
        self.sent = []

    def send(self, frame):
        self.sent.append((time.monotonic(), frame))


class UnreliableDummyKISS(DummyKISS):
    def __init__(self):
        super(UnreliableDummyKISS, self).__init__()
        self.send_calls = 0

    def send(self, frame):
        self.send_calls += 1
        if self.send_calls == 1:
            raise IOError('Whoopsie')
        super(UnreliableDummyKISS, self).send(frame)



@asynctest
def test_received_msg_signal():
    """
    Test received messages trigger the received_msg signal.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    receive_future = Future()

    my_interface = AX25Interface(my_port)

    def _on_receive_match(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)
    my_interface.received_msg.connect(_on_receive_match)

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))

    yield from receive_future


def test_receive_bind():
    """
    Test bind rejects non-strings as call-signs.
    """
    my_interface = AX25Interface(DummyKISS())
    try:
        my_interface.bind(
                callback=lambda *a, **kwa : None,
                callsign=123456,
                ssid=0,
                regex=False
        )
        assert False, 'This should not have worked'
    except TypeError as e:
        eq_(str(e), 'callsign must be a string (use '\
                    'regex=True for regex)')

@asynctest
def test_receive_str_filter():
    """
    Test matching messages can trigger string filters (without SSID).
    """
    my_port = DummyKISS()
    unmatched_filter_received = []
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    receive_future = Future()

    my_interface = AX25Interface(my_port)

    def _on_receive_match(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive_match, 'VK4BWI', ssid=None)

    # This should not match
    my_interface.bind(_on_receive_nomatch, 'VK4AWI', ssid=None)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))

    yield from receive_future
    eq_(len(unmatched_filter_received), 0)


@asynctest
def test_receive_str_filter_ssid():
    """
    Test matching messages can trigger string filters (with SSID).
    """
    my_port = DummyKISS()
    unmatched_filter_received = []
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    receive_future = Future()

    my_interface = AX25Interface(my_port)

    def _on_receive_match(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive_match, 'VK4BWI', ssid=4)

    # This should not match
    my_interface.bind(_on_receive_nomatch, 'VK4BWI', ssid=3)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))

    yield from receive_future
    eq_(len(unmatched_filter_received), 0)


@asynctest
def test_receive_re_filter():
    """
    Test matching messages can trigger regex filters (without SSID).
    """
    my_port = DummyKISS()
    unmatched_filter_received = []
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    receive_future = Future()

    my_interface = AX25Interface(my_port)

    def _on_receive_match(interface, frame, match, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive_match, r'^VK4[BR]WI$',
            ssid=None, regex=True)

    # This should not match
    my_interface.bind(_on_receive_nomatch, r'^VK4[AZ]WI$',
            ssid=None, regex=True)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))

    yield from receive_future
    eq_(len(unmatched_filter_received), 0)


@asynctest
def test_receive_re_filter_ssid():
    """
    Test matching messages can trigger regex filters (with SSID).
    """
    my_port = DummyKISS()
    unmatched_filter_received = []
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    receive_future = Future()

    my_interface = AX25Interface(my_port)

    def _on_receive_match(interface, frame, match, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive_match, r'^VK4[BR]WI$', ssid=4, regex=True)

    # This should not match
    my_interface.bind(_on_receive_nomatch, r'^VK4[AZ]WI$', ssid=4, regex=True)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))

    yield from receive_future
    eq_(len(unmatched_filter_received), 0)


def test_unbind_notexist_call():
    """
    Test unbinding a receiver for a call that does not exist returns silently.
    """
    my_interface = AX25Interface(DummyKISS())
    my_receiver = lambda **k : None

    # This should generate no error
    my_interface.unbind(my_receiver, 'MYCALL', ssid=12)

def test_unbind_notexist_ssid():
    """
    Test unbinding a receiver for a SSID that does not exist returns silently.
    """
    my_port = DummyKISS()
    my_interface = AX25Interface(my_port)

    my_receiver = lambda **k : None

    # Inject a receiver
    my_interface._receiver_str = {
            'MYCALL': {
                12: [
                    my_receiver
                ]
            }
    }

    # This should generate no error
    my_interface.unbind(my_receiver, 'MYCALL', ssid=14)

def test_unbind_notexist_receiver():
    """
    Test unbinding a receiver that is not bound should not raise error.
    """
    my_port = DummyKISS()
    my_interface = AX25Interface(my_port)

    my_receiver1 = lambda **k : None
    my_receiver2 = lambda **k : None

    # Inject a receiver
    my_interface._receiver_str = {
            'MYCALL': {
                12: [
                    my_receiver1
                ]
            }
    }

    # This should generate no error
    my_interface.unbind(my_receiver2, 'MYCALL', ssid=12)

def test_unbind_str():
    """
    Test unbinding a string receiver removes the receiver and cleans up.
    """
    my_port = DummyKISS()
    my_interface = AX25Interface(my_port)

    my_receiver = lambda **k : None

    # Inject a receiver
    my_interface._receiver_str = {
            'MYCALL': {
                12: [
                    my_receiver
                ]
            }
    }
    my_interface.unbind(my_receiver, 'MYCALL', ssid=12)

    # This should now be empty
    eq_(len(my_interface._receiver_str), 0)

def test_unbind_re():
    """
    Test unbinding a regex receiver removes the receiver and cleans up.
    """
    my_port = DummyKISS()
    my_interface = AX25Interface(my_port)

    my_receiver = lambda **k : None

    # Inject a receiver
    my_interface._receiver_re = {
            r'^MY': (re.compile(r'^MY'), {
                12: [
                    my_receiver
                ]
            })
    }
    my_interface.unbind(my_receiver, r'^MY', ssid=12, regex=True)

    # This should now be empty
    eq_(len(my_interface._receiver_re), 0)


def test_reception_resets_cts():
    """
    Check the clear-to-send expiry is updated with received traffic.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')

    my_interface = AX25Interface(my_port)
    cts_before = my_interface._cts_expiry

    # Pass in a message
    my_port.received.emit(frame=bytes(my_frame))
    cts_after = my_interface._cts_expiry

    assert_less(cts_before, cts_after)
    assert_greater(cts_after, time.monotonic())

@asynctest
def test_transmit_waits_cts():
    """
    Test sending a message waits for the channel to be clear.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    transmit_future = Future()

    my_interface = AX25Interface(my_port, cts_delay=0.250)

    def _on_transmit(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            transmit_future.set_result(None)
        except Exception as e:
            transmit_future.set_exception(e)

    def _on_timeout():
        transmit_future.set_exception(AssertionError('Timed out'))

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Send the message
    my_interface.transmit(my_frame, _on_transmit)

    yield from transmit_future

    eq_(len(my_port.sent), 1)
    (send_time, sent_frame) = my_port.sent.pop(0)

    eq_(bytes(sent_frame), bytes(my_frame))
    assert_less((time.monotonic() - send_time), 0.05)
    assert_greater_equal((send_time - time_before), 0.25)


@asynctest
@coroutine
def test_transmit_cancel():
    """
    Test that pending messages can be cancelled.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')

    my_interface = AX25Interface(my_port)

    # Send the message
    my_interface.transmit(my_frame)

    # Cancel it!
    my_interface.cancel_transmit(my_frame)

    # Wait a second
    yield from sleep(1)

    # Nothing should have been sent.
    eq_(len(my_port.sent), 0)


@asynctest
def test_transmit_sends_immediate_if_cts():
    """
    Test the interface sends immediately if last activity a long time ago.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    transmit_future = Future()

    my_interface = AX25Interface(my_port)

    # Override clear to send expiry
    my_interface._cts_expiry = 0

    def _on_transmit(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            transmit_future.set_result(None)
        except Exception as e:
            transmit_future.set_exception(e)

    def _on_timeout():
        transmit_future.set_exception(AssertionError('Timed out'))

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Send the message
    my_interface.transmit(my_frame, _on_transmit)

    yield from transmit_future

    eq_(len(my_port.sent), 1)
    (send_time, sent_frame) = my_port.sent.pop(0)

    eq_(bytes(sent_frame), bytes(my_frame))
    assert_less((time.monotonic() - send_time), 0.05)
    assert_less((send_time - time_before), 0.01)


@asynctest
def test_transmit_sends_if_not_expired():
    """
    Test the interface sends frame if not expired.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    my_frame.deadline = time.time() + 3600.0
    transmit_future = Future()

    my_interface = AX25Interface(my_port)

    # Override clear to send expiry
    my_interface._cts_expiry = 0

    def _on_transmit(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            transmit_future.set_result(None)
        except Exception as e:
            transmit_future.set_exception(e)

    def _on_timeout():
        transmit_future.set_exception(AssertionError('Timed out'))

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Send the message
    my_interface.transmit(my_frame, _on_transmit)

    yield from transmit_future

    eq_(len(my_port.sent), 1)
    (send_time, sent_frame) = my_port.sent.pop(0)

    eq_(bytes(sent_frame), bytes(my_frame))
    assert_less((time.monotonic() - send_time), 0.05)
    assert_less((send_time - time_before), 0.05)


@asynctest
def test_transmit_drops_expired():
    """
    Test the interface drops expired messages.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    # This timestamp was a _long_ time ago!  1AM 1st January 1970
    my_frame.deadline = 3600
    transmit_future = Future()

    my_interface = AX25Interface(my_port)

    # Override clear to send expiry
    my_interface._cts_expiry = 0

    def _on_timeout():
        transmit_future.set_result(None)

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Send the message
    my_interface.transmit(my_frame)

    yield from transmit_future

    # Nothing should be sent!
    eq_(len(my_port.sent), 0)


@asynctest
def test_transmit_waits_if_cts_reset():
    """
    Test the interface waits if CTS timer is reset.
    """
    my_port = DummyKISS()
    my_frame = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing')
    transmit_future = Future()

    my_interface = AX25Interface(my_port, cts_delay=0.250)

    def _on_transmit(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame), msg='Wrong frame')
            transmit_future.set_result(None)
        except Exception as e:
            transmit_future.set_exception(e)

    def _on_timeout():
        transmit_future.set_exception(AssertionError('Timed out'))

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Send the message
    my_interface.transmit(my_frame, _on_transmit)

    # Whilst that is pending, call reset_cts, this should delay transmission
    my_interface._reset_cts()

    yield from transmit_future

    eq_(len(my_port.sent), 1)
    (send_time, sent_frame) = my_port.sent.pop(0)

    eq_(bytes(sent_frame), bytes(my_frame))
    assert_less((time.monotonic() - send_time), 0.05)
    assert_greater(send_time - time_before, 0.25)
    assert_less(send_time - time_before, 1.05)


@asynctest
def test_transmit_handles_failure():
    """
    Test transmit failures don't kill the interface handling.
    """
    my_port = UnreliableDummyKISS()
    my_frame_1 = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing 1')
    my_frame_2 = AX25UnnumberedInformationFrame(
            destination='VK4BWI-4',
            source='VK4MSL',
            pid=0xf0,
            payload=b'testing 2')
    transmit_future = Future()

    my_interface = AX25Interface(my_port, cts_delay=0.250)

    # Override clear to send expiry
    my_interface._cts_expiry = 0

    def _on_transmit(interface, frame, **kwargs):
        try:
            eq_(len(kwargs), 0, msg='Too many arguments')
            assert_is(interface, my_interface, msg='Wrong interface')
            eq_(bytes(frame), bytes(my_frame_2), msg='Wrong frame')
            transmit_future.set_result(None)
        except Exception as e:
            transmit_future.set_exception(e)

    def _on_timeout():
        transmit_future.set_exception(AssertionError('Timed out'))

    # The time before transmission
    time_before = time.monotonic()

    # Set a timeout
    get_event_loop().call_later(2.0, _on_timeout)

    # Send the messages
    my_interface.transmit(my_frame_1, _on_transmit) # This will fail
    my_interface.transmit(my_frame_2, _on_transmit) # This will work

    yield from transmit_future

    eq_(len(my_port.sent), 1)
    (send_time, sent_frame) = my_port.sent.pop(0)

    eq_(bytes(sent_frame), bytes(my_frame_2))
    assert_less((time.monotonic() - send_time), 0.05)
    assert_greater_equal((send_time - time_before), 0.25)
