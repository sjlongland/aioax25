#!/usr/bin/env python3

from aioax25.signal import Signal
from aioax25.interface import AX25Interface
from aioax25.frame import AX25UnnumberedInformationFrame

from ..async import asynctest
from asyncio import Future, get_event_loop

import time


class DummyKISS(object):
    """
    Dummy KISS interface for unit testing.
    """
    def __init__(self):
        self.received = Signal()
        self.sent = []

    def send(self, frame):
        self.sent.append((time.monotonic(), frame))


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

    def _on_receive(interface, frame, **kwargs):
        try:
            assert len(kwargs) == 0, 'Too many arguments'
            assert interface is my_interface, 'Wrong interface'
            assert frame is my_frame, 'Wrong frame'
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)
    my_interface.received_msg.connect(_on_receive)

    # Pass in a message
    my_port.received.emit(frame=my_frame)

    yield from receive_future


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

    def _on_receive(interface, frame, **kwargs):
        try:
            assert len(kwargs) == 0, 'Too many arguments'
            assert interface is my_interface, 'Wrong interface'
            assert frame is my_frame, 'Wrong frame'
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive, 'VK4BWI', ssid=None)

    # This should not match
    my_interface.bind(_on_receive_nomatch, 'VK4AWI', ssid=None)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=my_frame)

    yield from receive_future
    assert len(unmatched_filter_received) == 0


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

    def _on_receive(interface, frame, **kwargs):
        try:
            assert len(kwargs) == 0, 'Too many arguments'
            assert interface is my_interface, 'Wrong interface'
            assert frame is my_frame, 'Wrong frame'
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive, 'VK4BWI', ssid=4)

    # This should not match
    my_interface.bind(_on_receive_nomatch, 'VK4BWI', ssid=3)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=my_frame)

    yield from receive_future
    assert len(unmatched_filter_received) == 0


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

    def _on_receive(interface, frame, match, **kwargs):
        try:
            assert len(kwargs) == 0, 'Too many arguments'
            assert interface is my_interface, 'Wrong interface'
            assert frame is my_frame, 'Wrong frame'
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive, r'^VK4[BR]WI$',
            ssid=None, regex=True)

    # This should not match
    my_interface.bind(_on_receive_nomatch, r'^VK4[AZ]WI$',
            ssid=None, regex=True)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=my_frame)

    yield from receive_future
    assert len(unmatched_filter_received) == 0


@asynctest
def test_receive_str_filter_ssid():
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

    def _on_receive(interface, frame, match, **kwargs):
        try:
            assert len(kwargs) == 0, 'Too many arguments'
            assert interface is my_interface, 'Wrong interface'
            assert frame is my_frame, 'Wrong frame'
            receive_future.set_result(None)
        except Exception as e:
            receive_future.set_exception(e)

    def _on_receive_nomatch(**kwargs):
        unmatched_filter_received.append(kwargs)

    def _on_timeout():
        receive_future.set_exception(AssertionError('Timed out'))

    # This should match
    my_interface.bind(_on_receive, r'^VK4[BR]WI$', ssid=4, regex=True)

    # This should not match
    my_interface.bind(_on_receive_nomatch, r'^VK4[AZ]WI$', ssid=4, regex=True)

    # Set a timeout
    get_event_loop().call_later(1.0, _on_timeout)

    # Pass in a message
    my_port.received.emit(frame=my_frame)

    yield from receive_future
    assert len(unmatched_filter_received) == 0
