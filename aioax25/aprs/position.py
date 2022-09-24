#!/usr/bin/env python3

"""
APRS position reporting handler.
"""

import math
from enum import Enum, IntEnum

from .frame import APRSFrame
from .datatype import APRSDataType
from .symbol import APRSSymbol
from .datetime import decode as decode_datetime
from .compression import compress, decompress, BYTE_VALUE_OFFSET
from ..unit import convertvalue, Quantity


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
        digits = ''.join(reversed(posstr[-6:-4] + posstr[-3:-1]))
        try:
            ambiguity = digits.rindex(" ") + 1
        except ValueError:
            ambiguity = 0
        ambiguity = APRSPositionAmbiguity(ambiguity)

        # Decode the minutes
        minutes = float(posstr[-6:-1].replace(" ","0"))

        # The rest is the degrees
        degrees = int(posstr[0:-6])

        return cls(sign * degrees, minutes, ambiguity=ambiguity)

    def __init__(
            self, degrees, minutes=0, seconds=0,
            ambiguity=APRSPositionAmbiguity.NONE
    ):
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
        self.ambiguity = APRSPositionAmbiguity(ambiguity)

    def __repr__(self): # pragma: no cover
        return (
                '%s(degrees=%r, minutes=%r, seconds=%r, ambiguity=%r)' \
                % (
                    self.__class__.__name__,
                    self.degrees, self.minutes, self.seconds, self.ambiguity
                )
        )

    def __str__(self):
        """
        Return the APRS-formatted position string.
        """
        sign = self.NEG_SUFFIX if self.degrees < 0 else self.POS_SUFFIX
        degrees = abs(self.degrees)

        pos = self.STR_FORMAT % (
                degrees,
                self.minutes,
                self.seconds / 0.6,
                sign
        )

        if self.ambiguity.value > 0:
            pos = pos[0:-2] + ' ' + pos[-1:]
        if self.ambiguity.value > 1:
            pos = pos[0:-3] + ' ' + pos[-2:]
        if self.ambiguity.value > 2:
            pos = pos[0:-5] + ' ' + pos[-4:]
        if self.ambiguity.value > 3:
            pos = pos[0:-6] + ' ' + pos[-5:]

        return pos

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

    def __repr__(self): # pragma: no cover
        return (
                '%s(lat=%r, lng=%r, symbol=%r)' % \
                (
                        self.__class__.__name__,
                        self.lat,
                        self.lng,
                        self.symbol
                )
        )

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
    GLL     = 0b00001000
    GGA     = 0b00010000
    RMC     = 0b00011000


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

        gpsfix = APRSCompressionTypeGPSFix(typebyte & cls.GPSFIX_MASK)
        nmeasrc = APRSCompressionTypeNMEASrc(typebyte & cls.NMEASRC_MASK)
        origin = APRSCompressionTypeOrigin(typebyte & cls.ORIGIN_MASK)

        return cls(gpsfix, nmeasrc, origin)


    def __init__(self, gpsfix, nmeasrc, origin):
        self.gpsfix = gpsfix
        self.nmeasrc = nmeasrc
        self.origin = origin

    @property
    def raw(self):
        return self.gpsfix.value | self.nmeasrc.value | self.origin.value

    def __repr__(self): # pragma: no cover
        return (
                '%s(gpsfix=%r, nmeasrc=%r, origin=%r)' \
                        % (
                            self.__class__.__name__,
                            self.gpsfix, self.nmeasrc, self.origin
                        )
        )

    def __str__(self):
        return chr(self.raw + BYTE_VALUE_OFFSET)


class APRSCompressedCoordinate(APRSSexagesimal):
    RADIX = 91
    LENGTH = 4

    @classmethod
    def decode(cls, coordinate):
        if len(coordinate) < cls.LENGTH:
            raise ValueError("Compressed co-ordinate too short")

        # Throw away extra data
        coordinate = coordinate[0:cls.LENGTH]

        # Convert the value back to decimal degrees
        value = ( \
                (decompress(coordinate) / cls.POSTSCALE) \
                - cls.OFFSET \
        ) / cls.PRESCALE

        return cls(value)

    def __str__(self):
        # Scale the decimal value
        return compress(int(abs(
            (
                (self.decimaldegrees * self.PRESCALE) + self.OFFSET
            ) * self.POSTSCALE
        )), self.LENGTH)


class APRSCompressedLatitude(APRSCompressedCoordinate):
    POSTSCALE = 380926
    PRESCALE = -1
    OFFSET = 90


class APRSCompressedLongitude(APRSCompressedCoordinate):
    POSTSCALE = 190463
    PRESCALE = 1
    OFFSET = 180


class APRSCompressedCourseSpeedRange(object):
    LENGTH = 2
    RADIX = APRSCompressedCoordinate.RADIX
    COURSE_SPEED_MAX = 89
    COURSE_SCALE = 4

    # this is in "knots".
    SPEED_UNITS = "knot"
    SPEED_RADIX = 1.08
    SPEED_OFFSET = -1

    # these values compute "miles".
    RANGE_UNITS = "mile"
    RANGE_HEADER = 90
    RANGE_SCALE = 2
    RANGE_RADIX = 1.08

    # these values compute "feet".
    ALTITUDE_UNITS = "foot"
    ALTITUDE_RADIX = 1.002

    @classmethod
    def decode(cls, csvalue, ctype):
        if len(csvalue) < cls.LENGTH:
            raise ValueError("Course/Speed value too short")

        # Discard extra data
        csvalue = csvalue[0:cls.LENGTH]

        if ctype.nmeasrc == APRSCompressionTypeNMEASrc.GGA:
            # This is an altitude value
            altitude_exp = decompress(csvalue)
            altitude = cls.ALTITUDE_RADIX ** altitude_exp
            speed = None
            course = None
            rng = None
        else:
            altitude = None
            csvalue = [
                    b - BYTE_VALUE_OFFSET
                    for b in bytes(csvalue, "us-ascii")
            ]

            if csvalue[0] == cls.RANGE_HEADER:
                # This is a range value
                rng = cls.RANGE_SCALE * (cls.RANGE_RADIX ** csvalue[1])
                speed = None
                course = None
            elif csvalue[0] <= cls.COURSE_SPEED_MAX:
                # This is a speed/course
                rng = None
                course = cls.COURSE_SCALE * csvalue[0]
                speed = (cls.SPEED_RADIX ** csvalue[1]) + cls.SPEED_OFFSET
            else:
                raise ValueError("Unknown Course/Speed/Range field: %r" \
                        % csvalue)

        return cls(course, speed, rng, altitude)

    def __init__(self, course=None, speed=None, rng=None, altitude=None):
        # Assert value units
        speed = convertvalue("speed", speed, self.SPEED_UNITS)
        rng = convertvalue("rng", rng, self.RANGE_UNITS)
        altitude = convertvalue("altitude", altitude, self.ALTITUDE_UNITS)

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

    @property
    def speed_q(self):
        """
        Speed as a Pint quantity.
        """
        return Quantity(self.speed, self.SPEED_UNITS)

    @speed_q.setter
    def speed_q(self, value):
        """
        Set the speed from the given quantity.
        """
        self.speed = value.to(self.SPEED_UNITS).magnitude

    @property
    def rng_q(self):
        """
        Range as a Pint quantity.
        """
        return Quantity(self.rng, self.RANGE_UNITS)

    @rng_q.setter
    def rng_q(self, value):
        """
        Set the range from the given quantity.
        """
        self.rng = value.to(self.RANGE_UNITS).magnitude

    @property
    def altitude_q(self):
        """
        Altitude as a Pint quantity.
        """
        return Quantity(self.altitude, self.ALTITUDE_UNITS)

    @altitude_q.setter
    def altitude_q(self, value):
        """
        Set the altitude from the given quantity.
        """
        self.altitude = value.to(self.ALTITUDE_UNITS).magnitude

    def __repr__(self): # pragma: no cover
        return (
                '%s(course=%r, speed=%r, rng=%r, altitude=%r)' \
                % (
                    self.__class__.__name__,
                    self.course, self.speed, self.rng, self.altitude
                )
        )

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

        return ''.join([chr(b + BYTE_VALUE_OFFSET) for b in bvalues])


class APRSCompressedCoordinates(object):
    LENGTH = APRSCompressedLatitude.LENGTH \
            + APRSCompressedLongitude.LENGTH \
            + APRSCompressionType.LENGTH \
            + APRSCompressedCourseSpeedRange.LENGTH \
            + 2 # symbol table ident + symbol code

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
        lat = APRSCompressedLatitude.decode(coordinate[1:])
        lng = APRSCompressedLongitude.decode(coordinate[5:])

        # Do we have a Course/Speed/Range or Type field?
        if coordinate[10] == cls.CST_FILL[0]:
            # No compression type or course/speed/range
            ctype = None
            csr = None
        else:
            # Decode the compression type byte
            ctype = APRSCompressionType.decode(coordinate[-1])
            csr = APRSCompressedCourseSpeedRange.decode(coordinate[-3:], ctype)

        return cls(lat, lng, symbol, ctype, csr)

    def __init__(self, lat, lng, symbol, ctype=None, csr=None):
        if (ctype is None) != (csr is None):
            raise ValueError("If either ctype or csr is given, give both")

        self.lat = lat
        self.lng = lng
        self.symbol = symbol
        self.ctype = ctype
        self.csr = csr

    def __repr__(self): # pragma: no cover
        return (
                '%s(lat=%r, lng=%r, symbol=%r, ctype=%r, csr=%r)' % \
                (
                        self.__class__.__name__,
                        self.lat,
                        self.lng,
                        self.symbol,
                        self.ctype,
                        self.csr
                )
        )

    def __str__(self):
        return ''.join([
            self.symbol.tableident,
            str(self.lat),
            str(self.lng),
            self.symbol.symbol,
            str(self.csr) if self.csr else self.CST_FILL,
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
            position_ts = decode_datetime(payload[1:8])
            payload = payload[8:]
        elif msgtype in (
                APRSDataType.POSITION,
                APRSDataType.POSITION_MSGCAP
        ):
            position_ts = None
            payload = payload[1:]
        else:
            raise ValueError('Not a position frame: %r' % payload)

        log.debug("Type: %s; timestamp: %r; payload: %r", \
                msgtype, position_ts, payload)

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

        log.debug("Position: %r, Message: %r", position, message)

        return cls(
                destination=uiframe.header.destination,
                source=uiframe.header.source,
                position=position,
                position_ts=position_ts,
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
            cls, position, message=None, position_ts=None, messaging=True
        ):
        """
        Encode the message payload.
        """
        parts = []

        # Initial message type indicator
        if position_ts is None:
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
            parts.append(str(position_ts))

        # Position
        parts.append(str(position))

        # Message (Comment)
        if message is not None:
            parts.append(str(message))

        return ''.join(parts)

    def __init__(self, destination, source, position, position_ts=None,
            message=None, messaging=True, repeaters=None,
            pf=False, cr=True, src_cr=None):
        self._position = position
        self._position_ts = position_ts
        self._messaging = messaging
        self._message = message

        payload = self._encodepayload(position, message, position_ts, messaging)

        super(APRSPositionFrame, self).__init__(
                destination=destination,
                source=source,
                payload=payload.encode('US-ASCII'),
                repeaters=repeaters, pf=pf, cr=cr, src_cr=src_cr)

    @property
    def position(self):
        return self._position

    @property
    def position_ts(self):
        return self._position_ts

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
