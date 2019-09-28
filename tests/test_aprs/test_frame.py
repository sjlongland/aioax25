#!/usr/bin/env python3

import logging

from nose.tools import eq_, assert_is, assert_is_not

from aioax25.aprs.frame import APRSFrame
from aioax25.aprs.message import \
        APRSMessageAckFrame, APRSMessageRejFrame, APRSMessageFrame
from aioax25.frame import AX25UnnumberedInformationFrame

from ..loop import DummyLoop

def test_decode_wrong_pid():
    """
    Test the decode routine ignores UI frames with wrong PID.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0x80,   # Not correct for APRS, should not get decoded.
            payload=b'Test frame that\'s not APRS'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is(decoded, frame)

def test_decode_no_payload():
    """
    Test the decode routine rejects frames without a payload.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'' # Empty payload
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is(decoded, frame)

def test_decode_unknown_type():
    """
    Test the decode routine rejects frames it cannot recognise.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'X A mystery frame X'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is(decoded, frame)

def test_decode_message():
    """
    Test the decode routine can recognise a message frame.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :Hi'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageFrame)

def test_decode_message_confirmable():
    """
    Test the decode routine can recognise a confirmable message frame.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :Hi{14'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageFrame)
    eq_(decoded.msgid, '14')

def test_decode_message_replyack_capable():
    """
    Test the decode routine can recognise a message frame from a Reply-ACK
    capable station.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :Hi{01}'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageFrame)
    eq_(decoded.replyack, True)
    eq_(decoded.msgid, '01')

def test_decode_message_replyack_reply():
    """
    Test the decode routine can recognise a message frame sent as a
    reply-ack.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :Hi{01}45'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageFrame)
    eq_(decoded.replyack, '45')
    eq_(decoded.msgid, '01')

def test_decode_message_ack():
    """
    Test the decode routine can recognise a message acknowledgement frame.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :ack2'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageAckFrame)
    eq_(decoded.msgid, '2')

def test_decode_message_rej():
    """
    Test the decode routine can recognise a message rejection frame.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':VK4MDL-7 :rej3'
    )
    decoded = APRSFrame.decode(frame, logging.getLogger('decoder'))
    assert_is_not(decoded, frame)
    assert isinstance(decoded, APRSMessageRejFrame)
    eq_(decoded.msgid, '3')
