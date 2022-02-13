#!/usr/bin/env python3

"""
APRS position reporting handler.
"""

import re
import math
from enum import Enum, IntEnum


from ..frame import AX25Address
from .frame import APRSFrame
from .datatype import APRSDataType
from .symbol import APRSSymbol
from .datetime import decode as decode_datetime
from .compression import compress, decompress, BYTE_VALUE_OFFSET


class APRSPositionAmbiguity(Enum):
    NONE                = 0
    TENTH_MINUTE        = 1
    MINUTE              = 2
    TEN_MINUTES         = 3
    DEGREE              = 4


class APRSSexagesimal(object):
    """
    Represents a sexagesimal co-ordinate in degrees, minutes and seconds.
    """
    POS_SUFFIX = "+"
    NEG_SUFFIX = "-"
    STR_FORMAT = "%03d%02d.%02d%s"
    LENGTH = 9

    @classmethod
    def decode(cls, posstr):
        if len(posstr) < cls.LENGTH:
            raise ValueError("Position string too short")

        # Throw out any extra data
        posstr = posstr[0:cls.LENGTH]

        # Determine the sign
        signchr = posstr[-1]
        if signchr == cls.POS_SUFFIX:
            sign = 1
        elif signchr == cls.NEG_SUFFIX:
            sign = -1
        else:
            raise ValueError("Unrecognised sign: %r" % signchr)

        # There _must_ be a decimal point as the 3rd last character
        if posstr[-4] != ".":
            raise ValueError("No decimal point found in required position")

        # Determine the ambiguity
        ambiguity = 0
        for pos, c in enumerate(posstr[-6:-4] + posstr[-3:-1], start=1):
            if c == " ":
                ambiguity = pos
            elif ambiguity != 0:
                raise ValueError("Spaces may only follow digits")
        ambiguity = APRSPositionAmbiguity(ambiguity)

        # Decode the minutes
        minutes = float(posstr[-6:-1].replace(" ","0"))

        # The rest is the degrees
        degrees = int(posstr[0:-6])

        return cls(sign * degrees, minutes)

    def __init__(self, degrees, minutes=0, seconds=0, ambiguity=0):
        if degrees != int(degrees):
            # Decimal degrees given
            if minutes or seconds:
                raise ValueError(
                    "Cannot define minutes or seconds when "
                    "given decimal degrees"
                )
            idegrees = int(degrees)
            minutes = 60.0 * abs(degrees - idegrees)
            degrees = idegrees

        if (minutes < 0) or (minutes >= 60):
            raise ValueError("minutes must be in the range [0..59]")

        if minutes != int(minutes):
            # Decimal minutes given
            iminutes = int(minutes)
            if seconds:
                raise ValueError(
                    "Cannot define seconds when given decimal minutes"
                )
            seconds = 60.0 * (minutes - iminutes)
            minutes = iminutes

        if (seconds < 0) or (seconds >= 60):
            raise ValueError("seconds must be in the range [0..59]")

        self.degrees = degrees
        self.minutes = minutes
        self.seconds = seconds

    def __str__(self):
        """
        Return the APRS-formatted position string.
        """
        sign = self.NEG_SUFFIX if self.minutes < 0 else self.POS_SUFFIX
        degrees = abs(self.degrees)

        return self.STR_FORMAT % (
                degrees,
                self.minutes,
                self.seconds / 60.0,
                sign
        )

    @property
    def decimalminutes(self):
        """
        Return the degrees and decimal minutes.
        """
        return self.minutes + (self.seconds / 60.0)

    @property
    def decimaldegrees(self):
        """
        Return the decimal degrees.
        """
        minutes = self.decimalminutes
        if self.degrees < 0:
            minutes = -minutes
        return self.degrees + (minutes / 60.0)


class APRSLatitude(APRSSexagesimal):
    POS_SUFFIX = "N"
    NEG_SUFFIX = "S"
    STR_FORMAT = "%02d%02d.%02d%s"
    LENGTH = 8


class APRSLongitude(APRSSexagesimal):
    POS_SUFFIX = "E"
    NEG_SUFFIX = "W"


class APRSUncompressedCoordinates(object):
    # Co-ordinate includes latitude, longitude, symbol table and
    # symbol
    LENGTH = APRSLatitude.LENGTH + APRSLongitude.LENGTH + 2

    @classmethod
    def decode(cls, coordinate):
        if len(coordinate) < cls.LENGTH:
            raise ValueError("Co-ordinate string is too short")

        # Strip extra data
        coordinate = coordinate[0:cls.LENGTH]

        # Decode and validate the symbol
        symbol = APRSSymbol(
                coordinate[APRSLatitude.LENGTH],
                coordinate[-1]
        )

        # Grab the latitude and longitude
        lat = APRSLatitude.decode(coordinate[0:APRSLatitude.LENGTH])
        lng = APRSLongitude.decode(coordinate[-APRSLongitude.LENGTH-1:-1])

        return cls(lat, lng, symbol)

    def __init__(self, lat, lng, symbol):
        self.lat = lat
        self.lng = lng
        self.symbol = symbol

    def __str__(self):
        return ''.join([
                str(self.lat),
                self.symbol.tableident,
                str(self.lng),
                self.symbol.symbol
        ])


class APRSCompressionTypeGPSFix(IntEnum):
    OLD     = 0b00000000
    CURRENT = 0b00100000


class APRSCompressionTypeNMEASrc(IntEnum):
    OTHER   = 0b00000000
    GLL     = 0b00010000
    GGA     = 0b00100000
    RMC     = 0b00110000


class APRSCompressionTypeOrigin(IntEnum):
    COMPRESSED  = 0b00000000
    TNC_BTEXT   = 0b00000001
    SOFTWARE    = 0b00000010
    TBD         = 0b00000011
    KPC3        = 0b00000100
    PICO        = 0b00000101
    OTHER       = 0b00000110
    DIGIPEATER  = 0b00000111


class APRSCompressionType(object):
    LENGTH = 1

    GPSFIX_MASK     = 0b00100000
    NMEASRC_MASK    = 0b00011000
    ORIGIN_MASK     = 0b00000111

    @classmethod
    def decode(cls, typechar):
        typebyte = ord(typechar) - BYTE_VALUE_OFFSET

        gpsfix = APRSCompressionTypeGPSFix(typebyte & GPSFIX_MASK)
        nmeasrc = APRSCompressionTypeNMEASrc(typebyte & NMEASRC_MASK)
        origin = APRSCompressionTypeOrigin(typebyte & ORIGIN_MASK)

        return cls(gpsfix, nmeasrc, origin)


    def __init__(self, gpsfix, nmeasrc, origin):
        self.gpsfix = gpsfix
        self.nmeasrc = nmeasrc
        self.origin = origin

    @property
    def raw(self):
        return self.gpsfix.value | self.nmeasrc.value | self.origin.value

    def __str__(self):
        return chr(self.raw)


class APRSCompressedCoordinate(APRSSexagesimal):
    RADIX = 91
    LENGTH = 4

    @classmethod
    def decode(cls, coordinate):
        if len(coordinate) != cls.LENGTH:
            raise ValueError("Invalid length for compressed co-ordinate")

        # Decompress the compressed value
        value = decompress(coordinate)

        # Apply scaling
        value /= cls.SCALE

        # Apply offset
        value += cls.OFFSET

        return cls(value)

    def __str__(self):
        # Scale the decimal value
        value = int(abs((self.OFFSET - self.decimaldegrees) * self.SCALE))

        # Compress it
        return compress(value, self.LENGTH)


class APRSCompressedLatitude(APRSCompressedCoordinate):
    SCALE = 380926
    OFFSET = 90


class APRSCompressedLongitude(APRSCompressedCoordinate):
    SCALE = 190463
    OFFSET = -180


class APRSCompressedCourseSpeedRange(object):
    LENGTH = 2
    RADIX = APRSCompressedCoordinate.RADIX
    COURSE_SPEED_MAX = 89
    COURSE_SCALE = 4

    # TODO: this is in "knots", metric would be nice.
    SPEED_RADIX = 1.08
    SPEED_OFFSET = -1

    # TODO: these values compute "miles", in 2022 we should be in
    # metric and leave imperial behind but Americans keep dragging
    # their "feet". ;-)
    RANGE_HEADER = 90
    RANGE_SCALE = 2
    RANGE_RADIX = 1.08

    # TODO: these values compute "feet"
    ALTITUDE_RADIX = 1.002

    @classmethod
    def decode(cls, csvalue, ctype):
        if len(csvalue) < cls.LENGTH:
            raise ValueError("Course/Speed value too short")

        if ctype.nmeasrc == APRSCompressionTypeNMEASrc.GGA:
            # This is an altitude value
            altitude = cls.ALTITUDE_RADIX ** decompress(csvalue)
            speed = None
            course = None
            rng = None
        else:
            csvalue = [
                    b - BYTE_VALUE_OFFSET
                    for b in bytes(csvalue[0:cls.LENGTH], "us-ascii")
            ]

            if csvalue[0] == cls.RANGE_HEADER:
                # This is a range value
                rng = RANGE_SCALE * (cls.RANGE_RADIX ** csvalue[1])
                speed = None
                course = None
            elif csvalue[0] <= cls.COURSE_SPEED_MAX:
                # This is a speed/course
                rng = None
                course = cls.COURSE_SCALE * csvalue[0]
                speed = (cls.SPEED_RADIX ** csvalue[1]) + cls.SPEED_OFFSET

        return cls(course, speed, rng)

    def __init__(self, course=None, speed=None, rng=None, altitude=None):
        if altitude is not None:
            for param in (course, speed, rng):
                if param is not None:
                    raise ValueError(
                        "Altitude cannot be specified with "
                        "range, course or speed"
                    )
        elif rng is not None:
            for param in (course, speed):
                if param is not None:
                    raise ValueError(
                        "Range cannot be specified with "
                        "altitude, course or speed"
                    )
        else:
            if (course is None) or (speed is None):
                raise ValueError(
                        "Course and speed must both be specified"
                )

        self.course = course
        self.speed = speed
        self.rng = rng
        self.altitude = altitude

    def __str__(self):
        if self.altitude is not None:
            return compress(
                    int(math.log(self.altitude, self.ALTITUDE_RADIX)),
                    self.LENGTH
            )
        elif self.rng is not None:
            # Return range
            bvalues = [
                    self.RANGE_HEADER,
                    int(math.log(
                        self.rng / self.RANGE_SCALE,
                        self.RANGE_RADIX
                    ))
            ]
        else:
            # Return speed/course
            bvalues = [
                    int(self.course / self.COURSE_SCALE),
                    int(math.log(
                        self.speed + 1,
                        self.SPEED_RADIX
                    ))
            ]

        return ''.join([ord(b + BYTE_VALUE_OFFSET) for b in bvalues])


class APRSCompressedCoordinates(object):
    LENGTH = APRSCompressedLatitude.LENGTH \
            + APRSCompressedLongitude.LENGTH \
            + APRSCompressionType.LENGTH \
            + APRSCompressedCourseSpeedRange.LENGTH \
            + 3 # type + symbol table ident + symbol code

    CST_FILL = " sT"

    @classmethod
    def decode(cls, coordinate):
        # Sanity check the length
        if len(coordinate) < cls.LENGTH:
            raise ValueError("Co-ordinate too short for compressed format")

        # Strip off anything extra
        coordinate = coordinate[0:cls.LENGTH]

        # Decode the symbol
        symbol = APRSSymbol(coordinate[0], coordinate[9])

        # Decode the latitude and longitude
        lat = APRSCompressedLatitude.decode(coordinate[2:])
        lng = APRSCompressedLatitude.decode(coordinate[6:])

        # Do we have a Course/Speed/Range or Type field?
        if coordinate[12] == cls.CST_FILL[0]:
            # No compression type or course/speed/range
            ctype = None
            csr = None
        else:
            # Decode the compression type byte
            ctype = APRSCompressionType.decode(coordinate[-1])
            csr = APRSCompressionCourseSpeedRange.decode(coordinate[-2:])

        return cls(lat, lng, symbol, ctype, csr)

    def __init__(self, lat, lng, symbol, ctype=None, csr=None):
        if (ctype is None) != (csr is None):
            raise ValueError("If either ctype or csr is given, give both")

        self.lat = lat
        self.lng = lng
        self.symbol = symbol
        self.ctype = ctype
        self.csr = csr

    def __str__(self):
        return ''.join([
            self.symbol.tableident,
            str(self.lat),
            str(self.lng),
            self.symbol.code,
            str(self.cst) if self.cst else self.CST_FILL,
            str(self.ctype) if self.ctype else ""
        ])


class APRSPositionFrame(APRSFrame):
    @classmethod
    def decode(cls, uiframe, payload, log):
        try:
            msgtype = APRSDataType(ord(payload[0]))
            log.debug("Received a %s frame", msgtype)
        except ValueError:
            raise ValueError('Not a recognised frame: %r' % payload)

        # If there's a timestamp, it'll be the first 7 characters
        if msgtype in (
                APRSDataType.POSITION_TS,
                APRSDataType.POSITION_TS_MSGCAP
        ):
            timestamp = decode_datetime(payload[1:8])
            payload = payload[8:]
        elif msgtype in (
                APRSDataType.POSITION,
                APRSDataType.POSITION_MSGCAP
        ):
            timestamp = None
            payload = payload[1:]
        else:
            raise ValueError('Not a position frame: %r' % payload)

        log.debug("Timestamp: %s; payload: %r", msgtype, payload)

        # Is the position compressed?
        # Uncompressed position looks like this:
        #   0123456789012345678
        #   DDMM.MMsTDDDMM.MMsC
        #
        # whereas compressed looks like this:
        #   0123456789012
        #   TYYYYXXXXCcst
        #
        # D = degrees, M = minutes, s = sign, T = symbol table
        # C = symbol code, X = compressed longitude, Y = compressed latitude,
        # cs = course/speed, t = compression type
        #
        # The length needs to be at least the length of an uncompressed
        # position report (19 bytes) and must have decimal places in the
        # expected places (position 4 and 14).
        if (
            (len(payload) >= APRSUncompressedCoordinates.LENGTH) \
            and (payload[4] == ".") \
            and (payload[14] == ".")
        ):
            # This is possibly a position report
            position = APRSUncompressedCoordinates.decode(payload)
            message = payload[APRSUncompressedCoordinates.LENGTH:]
        else:
            # Possibly a compressed position report
            position = APRSCompressedCoordinates.decode(payload)
            message = payload[APRSCompressedCoordinates.LENGTH:]

        return cls(
                destination=uiframe.header.destination,
                source=uiframe.header.source,
                position=position,
                timestamp=timestamp,
                message=message or None,
                messaging=(msgtype in (
                    APRSDataType.POSITION_MSGCAP,
                    APRSDataType.POSITION_TS_MSGCAP
                )),
                repeaters=uiframe.header.repeaters,
                pf=uiframe.pf,
                cr=uiframe.header.cr,
                src_cr=uiframe.header.src_cr
        )

    @classmethod
    def _encodepayload(
            cls, position, message=None, timestamp=None, messaging=True
        ):
        """
        Encode the message payload.
        """
        parts = []

        # Initial message type indicator
        if timestamp is None:
            if messaging:
                parts.append(chr(APRSDataType.POSITION_MSGCAP.value))
            else:
                parts.append(chr(APRSDataType.POSITION.value))
        else:
            if messaging:
                parts.append(chr(APRSDataType.POSITION_TS_MSGCAP.value))
            else:
                parts.append(chr(APRSDataType.POSITION_TS.value))

            # Timestamp
            parts.append(str(timestamp))

        # Position
        parts.append(str(position))

        # Message (Comment)
        if message is not None:
            parts.append(str(message))

        return ''.join(parts)

    def __init__(self, destination, source, position, timestamp=None,
            message=None, messaging=True, repeaters=None,
            pf=False, cr=True, src_cr=None):
        self._position = position
        self._timestamp = timestamp
        self._messaging = messaging
        self._message = message

        payload = self._encodepayload(position, message, timestamp, messaging)

        super(APRSPositionFrame, self).__init__(
                destination=destination,
                source=source,
                payload=payload.encode('US-ASCII'),
                repeaters=repeaters, pf=pf, cr=cr, src_cr=src_cr)

    @property
    def position(self):
        return self._position

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def message(self):
        return self._message

    @property
    def has_messaging(self):
        return self._messaging


APRSFrame.DATA_TYPE_HANDLERS[APRSDataType.POSITION] = \
        APRSPositionFrame
APRSFrame.DATA_TYPE_HANDLERS[APRSDataType.POSITION_MSGCAP] = \
        APRSPositionFrame
APRSFrame.DATA_TYPE_HANDLERS[APRSDataType.POSITION_TS] = \
        APRSPositionFrame
APRSFrame.DATA_TYPE_HANDLERS[APRSDataType.POSITION_TS_MSGCAP] = \
        APRSPositionFrame
