#!/usr/bin/env python3

import logging

from nose.tools import eq_

from aioax25.aprs.message import APRSMessageAckFrame
from aioax25.frame import AX25UnnumberedInformationFrame
from aioax25.aprs.router import APRSRouter

from ..loop import DummyLoop

def test_get_destination_msgframe():
    """
    Test _get_destination returns the addressee of a APRSMessageFrame.
    """
    frame = APRSMessageAckFrame(
            destination='APZAIO',
            addressee='VK4BWI-2',
            source='VK4MSL-7',
            msgid='123'
    )
    router = APRSRouter()
    destination = router._get_destination(frame)
    eq_(destination, frame.addressee)

def test_get_destination_uiframe():
    """
    Test _get_destination returns the destination field of a generic UI frame
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':BLN4     :Test bulletin'
    )
    router = APRSRouter()
    destination = router._get_destination(frame)
    eq_(destination, frame.header.destination)
