#!/usr/bin/env python3

"""
KISS device factory unit tests.
"""

from aioax25.kiss import \
        SerialKISSDevice, \
        SubprocKISSDevice, \
        TCPKISSDevice, \
        make_device

def test_serial_kiss():
    """
    Test we can create a ``SerialKISSDevice``.
    """
    dev = make_device(type='serial', device='/dev/ttyS0', baudrate=9600)
    assert isinstance(dev, SerialKISSDevice)
    assert dev._device == '/dev/ttyS0'
    assert dev._baudrate == 9600


def test_subproc_kiss():
    """
    Test we can create a ``SubprocKISSDevice``.
    """
    dev = make_device(type='subproc', command=['somecmd', 'a', 'b', 'c'])
    assert isinstance(dev, SubprocKISSDevice)
    assert dev._command == ['somecmd', 'a', 'b', 'c']
    assert dev._shell is False


def test_tcp_kiss():
    """
    Test we can create a ``TCPKISSDevice``.
    """
    dev = make_device(type='tcp', host='localhost', port=10000)
    assert isinstance(dev, TCPKISSDevice)
    assert dev._conn_args == dict(
            host='localhost', port=10000,
            ssl=None, family=0, proto=0, flags=0,
            sock=None, local_addr=None, server_hostname=None
    )


def test_unknown_kiss_type():
    """
    Test that unknown KISS device types are rejected
    """
    try:
        dev = make_device(type='bogus')
        assert False, 'Should not have worked, got a %r' % (dev,)
    except ValueError as e:
        assert str(e) == ("Unrecognised type=%r" % ("bogus",))
