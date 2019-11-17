#!/usr/bin/env python3

from aioax25.station import AX25Station

from nose.tools import eq_
from ..mocks import DummyInterface


def test_attach():
    """
    Test attach binds the station to the interface.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL-5')
    station.attach()

    eq_(len(interface.bind_calls), 1)
    eq_(len(interface.unbind_calls), 0)
    eq_(len(interface.transmit_calls), 0)

    (args, kwargs) = interface.bind_calls.pop()
    eq_(args, (station._on_receive,))
    eq_(set(kwargs.keys()), set([
        'callsign', 'ssid', 'regex'
    ]))
    eq_(kwargs['callsign'], 'VK4MSL')
    eq_(kwargs['ssid'], 5)
    eq_(kwargs['regex'], False)

def test_detach():
    """
    Test attach unbinds the station to the interface.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL-5')
    station.detach()

    eq_(len(interface.bind_calls), 0)
    eq_(len(interface.unbind_calls), 1)
    eq_(len(interface.transmit_calls), 0)

    (args, kwargs) = interface.unbind_calls.pop()
    eq_(args, (station._on_receive,))
    eq_(set(kwargs.keys()), set([
        'callsign', 'ssid', 'regex'
    ]))
    eq_(kwargs['callsign'], 'VK4MSL')
    eq_(kwargs['ssid'], 5)
    eq_(kwargs['regex'], False)
