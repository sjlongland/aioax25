#!/usr/bin/env python3

from nose.tools import eq_, assert_set_equal

from aioax25.aprs import APRSInterface
from ..loop import DummyLoop


class DummyAX25Interface(object):
    def __init__(self):
        self._loop = DummyLoop()
        self.bind_calls = []
        self.transmitted = []

    def bind(self, callback, callsign, ssid=0, regex=False):
        self.bind_calls.append((callback, callsign, ssid, regex))

    def transmit(self, frame):
        self.transmitted.append(frame)


def test_constructor_bind():
    """
    Test the constructor binds to the usual destination addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10')
    eq_(len(ax25int.bind_calls), 26)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the standard APRS ones.
                ('^AIR',    True,   None),
                ('^ALL',    True,   None),
                ('^AP',     True,   None),
                ('BEACON',  False,  None),
                ('^CQ',     True,   None),
                ('^GPS',    True,   None),
                ('^DF',     True,   None),
                ('^DGPS',   True,   None),
                ('^DRILL',  True,   None),
                ('^ID',     True,   None),
                ('^JAVA',   True,   None),
                ('^MAIL',   True,   None),
                ('^MICE',   True,   None),
                ('^QST',    True,   None),
                ('^QTH',    True,   None),
                ('^RTCM',   True,   None),
                ('^SKY',    True,   None),
                ('^SPACE',  True,   None),
                ('^SPC',    True,   None),
                ('^SYM',    True,   None),
                ('^TEL',    True,   None),
                ('^TEST',   True,   None),
                ('^TLM',    True,   None),
                ('^WX',     True,   None),
                ('^ZIP',    True,   None)
            ])
    )

def test_constructor_bind_altnets():
    """
    Test the constructor binds to "alt-nets".
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(
            ax25int, 'VK4MSL-10',
            listen_altnets=[
                dict(callsign='VK4BWI', regex=False, ssid=None)
            ])
    eq_(len(ax25int.bind_calls), 27)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the standard APRS ones.
                ('^AIR',    True,   None),
                ('^ALL',    True,   None),
                ('^AP',     True,   None),
                ('BEACON',  False,  None),
                ('^CQ',     True,   None),
                ('^GPS',    True,   None),
                ('^DF',     True,   None),
                ('^DGPS',   True,   None),
                ('^DRILL',  True,   None),
                ('^ID',     True,   None),
                ('^JAVA',   True,   None),
                ('^MAIL',   True,   None),
                ('^MICE',   True,   None),
                ('^QST',    True,   None),
                ('^QTH',    True,   None),
                ('^RTCM',   True,   None),
                ('^SKY',    True,   None),
                ('^SPACE',  True,   None),
                ('^SPC',    True,   None),
                ('^SYM',    True,   None),
                ('^TEL',    True,   None),
                ('^TEST',   True,   None),
                ('^TLM',    True,   None),
                ('^WX',     True,   None),
                ('^ZIP',    True,   None),
                # Now should be the "alt-nets"
                ('VK4BWI',  False,  None)
            ])
    )

def test_constructor_bind_override():
    """
    Test the constructor allows overriding the usual addresses.
    """
    ax25int = DummyAX25Interface()
    aprsint = APRSInterface(ax25int, 'VK4MSL-10',
            listen_destinations=[
                dict(callsign='APRS', regex=False, ssid=None)
            ])
    eq_(len(ax25int.bind_calls), 2)

    assert_set_equal(
            set([
                (call, regex, ssid)
                for (cb, call, ssid, regex)
                in ax25int.bind_calls
            ]),
            set([
                # The first bind call should be for the station SSID
                ('VK4MSL',  False,  10),
                # The rest should be the ones we gave
                ('APRS',    False,  None)
            ])
    )
