#!/usr/bin/env python3

from nose.tools import eq_, assert_set_equal, assert_is, assert_greater, \
        assert_less

from aioax25.aprs.uidigi import APRSDigipeater
from aioax25.frame import AX25UnnumberedInformationFrame, AX25Address
from aioax25.signal import Signal


class DummyAPRSInterface(object):
    def __init__(self):
        self.received_msg = Signal()
        self.mycall = AX25Address.decode('VK4MSL-10')
        self.transmitted = []

    def transmit(self, frame):
        self.transmitted.append(frame)


def test_rx_irrelevant():
    """
    Test the digipeater module ignores irrelevant frames.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'VK4RZA',
                'VK4RZB'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been dropped
    eq_(len(interface.transmitted), 0)


def test_rx_selfdigied():
    """
    Test the digipeater module ignores frames already digied by us.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'VK4RZA',
                'VK4MSL-10*',
                'VK4RZB'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been dropped
    eq_(len(interface.transmitted), 0)


def test_rx_selftodigi_uplink():
    """
    Test the digipeater module ignores uplink frames with explicit paths.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'VK4RZA',
                'VK4MSL-10',
                'VK4RZB'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been dropped
    eq_(len(interface.transmitted), 0)


def test_rx_selftodigi_first():
    """
    Test the digipeater module digipeats when own call is first.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'VK4MSL-10',
                'VK4RZB'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been digipeated
    eq_(len(interface.transmitted), 1)
    frame = interface.transmitted.pop()

    # It should be passed through VK4MSL-10.
    eq_(str(frame.header.repeaters), 'VK4MSL-10*,VK4RZB')


def test_rx_selftodigi_downlink():
    """
    Test the digipeater module digipeats when own call is first.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'VK2RXX',   # Ordinarily, this should have the H bit set!
                'VK4RZA*',
                'VK4MSL-10',
                'VK4RZB'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been digipeated
    eq_(len(interface.transmitted), 1)
    frame = interface.transmitted.pop()

    # It should be passed through VK4MSL-10.  H bits of prior repeaters
    # should be left intact.
    eq_(str(frame.header.repeaters), 'VK2RXX,VK4RZA*,VK4MSL-10*,VK4RZB')


def test_rx_exhausted():
    """
    Test the digipeater module ignores WIDEn-0 frames.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'WIDE9-0'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been dropped
    eq_(len(interface.transmitted), 0)


def test_rx_lasthop():
    """
    Test the digipeater module digipeats when we get to the last hop.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'WIDE1-1'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been digipeated
    eq_(len(interface.transmitted), 1)
    frame = interface.transmitted.pop()
    eq_(str(frame.header.repeaters), 'VK4MSL-10*')


def test_rx_nexthop():
    """
    Test the digipeater module appends the correct WIDEn-N next hop.
    """
    interface = DummyAPRSInterface()
    digipeater = APRSDigipeater(interface)
    interface.received_msg.emit(
        interface=interface,
        frame=AX25UnnumberedInformationFrame(
            destination='VK4MSL-1',
            source='VK4MSL-2',
            repeaters=[
                'WIDE3-3'
            ],
            pid=0xff, payload=b'testing'
        )
    )

    # This should have been digipeated
    eq_(len(interface.transmitted), 1)
    frame = interface.transmitted.pop()
    eq_(str(frame.header.repeaters), 'VK4MSL-10*,WIDE3-2')
