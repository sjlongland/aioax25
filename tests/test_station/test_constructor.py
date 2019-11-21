#!/usr/bin/env python3

from aioax25.station import AX25Station
from aioax25.version import AX25Version

from nose.tools import eq_
from ..mocks import DummyInterface


def test_constructor_log():
    """
    Test the AX25Constructor uses the log given.
    """
    class DummyLogger(object):
        pass

    log = DummyLogger()
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL', ssid=3,
            log=log)
    assert station._log is log

def test_constructor_loop():
    """
    Test the AX25Constructor uses the IO loop given.
    """
    class DummyLoop(object):
        pass

    loop = DummyLoop()
    interface = DummyInterface()
    station = AX25Station(interface=interface, callsign='VK4MSL', ssid=3,
            loop=loop)
    assert station._loop is loop

def test_constructor_protocol():
    """
    Test the AX25Constructor validates the protocol
    """
    try:
        AX25Station(interface=DummyInterface(), callsign='VK4MSL', ssid=3,
                protocol=AX25Version.AX25_10)
        assert False, 'Should not have worked'
    except ValueError as e:
        eq_(str(e),
                "'1.x' not a supported AX.25 protocol version")
