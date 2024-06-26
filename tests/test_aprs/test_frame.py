#!/usr/bin/env python3

import logging

from aioax25.aprs.frame import APRSFrame
from aioax25.aprs.message import (
    APRSMessageAckFrame,
    APRSMessageRejFrame,
    APRSMessageFrame,
)
from aioax25.aprs.position import APRSPositionFrame
from aioax25.frame import AX25UnnumberedInformationFrame


def test_decode_wrong_pid():
    """
    Test the decode routine ignores UI frames with wrong PID.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0x80,  # Not correct for APRS, should not get decoded.
        payload=b"Test frame that's not APRS",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is frame


def test_decode_no_payload():
    """
    Test the decode routine rejects frames without a payload.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b"",  # Empty payload
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is frame


def test_decode_unknown_type():
    """
    Test the decode routine rejects frames it cannot recognise.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b"X A mystery frame X",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is frame


def test_decode_position():
    """
    Test the decode routine can recognise a position report.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b"!3722.20N/07900.66W&000/000/A=000685Mobile",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSPositionFrame)
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == "000/000/A=000685Mobile"


def test_decode_message():
    """
    Test the decode routine can recognise a message frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :Hi",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageFrame)


def test_decode_message_confirmable():
    """
    Test the decode routine can recognise a confirmable message frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :Hi{14",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageFrame)
    assert decoded.msgid == "14"


def test_decode_message_replyack_capable():
    """
    Test the decode routine can recognise a message frame from a Reply-ACK
    capable station.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :Hi{01}",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageFrame)
    assert decoded.replyack == True
    assert decoded.msgid == "01"


def test_decode_message_replyack_reply():
    """
    Test the decode routine can recognise a message frame sent as a
    reply-ack.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :Hi{01}45",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageFrame)
    assert decoded.replyack == "45"
    assert decoded.msgid == "01"


def test_decode_message_ack():
    """
    Test the decode routine can recognise a message acknowledgement frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :ack2",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageAckFrame)
    assert decoded.msgid == "2"


def test_decode_message_rej():
    """
    Test the decode routine can recognise a message rejection frame.
    """
    frame = AX25UnnumberedInformationFrame(
        destination="APZAIO",
        source="VK4MSL-7",
        pid=0xF0,
        payload=b":VK4MDL-7 :rej3",
    )
    decoded = APRSFrame.decode(frame, logging.getLogger("decoder"))
    assert decoded is not frame
    assert isinstance(decoded, APRSMessageRejFrame)
    assert decoded.msgid == "3"
