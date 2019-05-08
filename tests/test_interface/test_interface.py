#!/usr/bin/env python3

from aioax25.signal import Signal
from aioax25.interface import AX25Interface
from aioax25.frame import AX25UnnumberedInformationFrame

from ..async import asynctest
from asyncio import Future

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
