#!/usr/bin/env python3

import logging

import datetime
from aioax25.aprs.datetime import DHMUTCTimestamp, DHMLocalTimestamp, \
        HMSTimestamp, MDHMTimestamp, decode

"""
Time-stamp handling tests.
"""

REF_DT = datetime.datetime(
        2022, 2, 12, 22, 2, 23,
        tzinfo=datetime.timezone.utc
)


def test_dhmutctimestamp_encode():
    """
    Test we can format a DHM timestamp in UTC.
    """
    assert str(DHMUTCTimestamp(12, 21, 52)) == "122152z"


def test_dhmlocaltimestamp_encode():
    """
    Test we can format a DHM timestamp in local time.
    """
    assert str(DHMLocalTimestamp(12, 21, 52)) == "122152/"


def test_hmstimestamp_encode():
    """
    Test we can format a HMS timestamp.
    """
    assert str(HMSTimestamp(21, 59, 6)) == "215906h"


def test_mdhmtimestamp_encode():
    """
    Test we can format a MDHM timestamp.
    """
    assert str(MDHMTimestamp(2, 12, 21, 52)) == "02122152"


def test_dhmutctimestamp_decode():
    """
    Test we can decode a DHM timestamp in UTC.
    """
    res = decode("162152z")
    assert isinstance(res, DHMUTCTimestamp)
    assert (res.day, res.hour, res.minute) == (16, 21, 52)


def test_dhmlocaltimestamp_decode():
    """
    Test we can handle a DHM timestamp in local time.
    """
    res = decode("162152/")
    assert isinstance(res, DHMLocalTimestamp)
    assert (res.day, res.hour, res.minute) == (16, 21, 52)


def test_hmstimestamp_decode():
    """
    Test we can decode a HMS timestamp.
    """
    res = decode("193207h")
    assert isinstance(res, HMSTimestamp)
    assert (res.hour, res.minute, res.second) == (19, 32, 7)


def test_mdhmtimestamp_decode():
    """
    Test we can decode a MDHM timestamp.
    """
    res = decode("02081932")
    assert isinstance(res, MDHMTimestamp)
    assert (res.month, res.day, res.hour, res.minute) \
            == (2, 8, 19, 32)


def test_too_short_decode():
    """
    Test the decoder rejects strings that are too short.
    """
    try:
        decode("09:19")
        assert False, "Should not have decoded"
    except ValueError as e:
        assert str(e) == "Timestamp string too short"


def test_invalid_format():
    """
    Test the decoder rejects strings that are too short.
    """
    try:
        decode("130919\\")
        assert False, "Should not have decoded"
    except ValueError as e:
        assert str(e) == "Timestamp format not recognised"
