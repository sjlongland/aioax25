#!/usr/bin/env python3

from aioax25.station import AX25Station

from ..mocks import DummyInterface


def test_attach():
    """
    Test attach binds the station to the interface.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign="VK4MSL-5")
    station.attach()

    assert len(interface.bind_calls) == 1
    assert len(interface.unbind_calls) == 0
    assert len(interface.transmit_calls) == 0

    (args, kwargs) = interface.bind_calls.pop()
    assert args == (station._on_receive,)
    assert set(kwargs.keys()) == set(["callsign", "ssid", "regex"])
    assert kwargs["callsign"] == "VK4MSL"
    assert kwargs["ssid"] == 5
    assert kwargs["regex"] == False


def test_detach():
    """
    Test attach unbinds the station to the interface.
    """
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign="VK4MSL-5")
    station.detach()

    assert len(interface.bind_calls) == 0
    assert len(interface.unbind_calls) == 1
    assert len(interface.transmit_calls) == 0

    (args, kwargs) = interface.unbind_calls.pop()
    assert args == (station._on_receive,)
    assert set(kwargs.keys()) == set(["callsign", "ssid", "regex"])
    assert kwargs["callsign"] == "VK4MSL"
    assert kwargs["ssid"] == 5
    assert kwargs["regex"] == False
