#!/usr/bin/env python3

"""
APRS date and time formats.
"""

from datetime import time


class APRSTimestamp(object):
    """
    Base abstract class for APRS timestamps.
    """
    pass


class DHMBaseTimestamp(APRSTimestamp):
    """
    Day/Hour/Minute timestamp (base class)
    """
    TS_LENGTH = 7

    def __init__(self, day, hour, minute):
        self.day = day
        self.hour = hour
        self.minute = minute

    def __str__(self):
        return '%02d%02d%02d%s' % (
                self.day, self.hour, self.minute,
                self.TS_SUFFIX
        )


class DHMUTCTimestamp(DHMBaseTimestamp):
    """
    Day/Hour/Minute timestamp in UTC.
    """
    TS_SUFFIX = "z"


class DHMLocalTimestamp(DHMBaseTimestamp):
    """
    Day/Hour/Minute timestamp in local time.
    """
    TS_SUFFIX = "/"


class HMSTimestamp(time, APRSTimestamp):
    """
    Hour/Minute/Second timestamp in UTC.
    """
    TS_LENGTH = 7
    TS_SUFFIX = "h"

    def __str__(self):
        return '%02d%02d%02d%s' % (
                self.hour, self.minute, self.second,
                self.TS_SUFFIX
        )


class MDHMTimestamp(APRSTimestamp):
    """
    Month/Day/Hour/Minute timestamp in UTC.
    """
    TS_LENGTH = 8

    def __init__(self, month, day, hour, minute):
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute

    def __str__(self):
        return '%02d%02d%02d%02d' % (
                self.month, self.day, self.hour, self.minute
        )


def decode(dtstr):
    """
    Decode a APRS date/time date code.  Since not full information is given
    in the timestamp, and date/time values are a nightmare to handle
    (especially for local timestamps), we just reproduce enough to round-trip
    the values in APRS.
    """
    if len(dtstr) < DHMBaseTimestamp.TS_LENGTH:
        # Not a valid date/time format
        raise ValueError("Timestamp string too short")

    if dtstr[6] in (DHMLocalTimestamp.TS_SUFFIX, DHMUTCTimestamp.TS_SUFFIX):
        # Day/Hours/Minutes in UTC or local-time
        # Format is:
        #   DDHHMM{z|/}
        day = int(dtstr[0:2])
        hour = int(dtstr[2:4])
        minute = int(dtstr[4:6])

        if dtstr[6] == DHMUTCTimestamp.TS_SUFFIX:
            return DHMUTCTimestamp(day, hour, minute)
        else:
            return DHMLocalTimestamp(day, hour, minute)
    elif dtstr[6] == HMSTimestamp.TS_SUFFIX:
        # Hours/Minutes/Seconds in UTC
        # Format is:
        #   HHMMSSh
        hour = int(dtstr[0:2])
        minute = int(dtstr[2:4])
        second = int(dtstr[4:6])

        return HMSTimestamp(hour, minute, second)
    elif len(dtstr) >= MDHMTimestamp.TS_LENGTH:
        # Month/Day/Hours/Minutes in UTC
        # Format is:
        #   MMDDHHMM
        month = int(dtstr[0:2])
        day = int(dtstr[2:4])
        hour = int(dtstr[4:6])
        minute = int(dtstr[6:8])

        return MDHMTimestamp(month, day, hour, minute)

    raise ValueError("Timestamp format not recognised")
