#!/usr/bin/env python3

import logging

from aioax25.frame import AX25UnnumberedInformationFrame
from aioax25.unit import Quantity
from aioax25.aprs.datetime import MDHMTimestamp
from aioax25.aprs.position import APRSSexagesimal, \
        APRSLatitude, APRSLongitude, \
        APRSCompressedLatitude, APRSCompressedLongitude, \
        APRSPositionFrame, APRSPositionAmbiguity, \
        APRSUncompressedCoordinates, \
        APRSCompressedCourseSpeedRange, \
        APRSCompressedCoordinates, \
        APRSCompressionType, \
        APRSCompressionTypeGPSFix, \
        APRSCompressionTypeNMEASrc, \
        APRSCompressionTypeOrigin
from aioax25.aprs.symbol import APRSSymbol

"""
Position handling tests.
"""

def test_sexagesimal_convert_dd():
    """
    Test we can convert decimal degrees to sexagesimal format.
    """
    v = APRSSexagesimal(-27.437244)
    assert (v.degrees, v.minutes) == (-27, 26)
    assert abs(v.seconds - 14.0777) < 0.001

def test_sexagesimal_convert_dm():
    """
    Test we can convert decimal minutes to sexagesimal format.
    """
    v = APRSSexagesimal(-27, 26.234628333)
    assert (v.degrees, v.minutes) == (-27, 26)
    assert abs(v.seconds - 14.0777) < 0.001

def test_sexagesimal_convert_to_dm():
    """
    Test we can convert sexagesimal format to decimal minutes.
    """
    v = APRSSexagesimal(-27, 26, 14.0777)
    assert abs(v.decimalminutes - 26.2346) < 0.001

def test_sexagesimal_convert_to_dd():
    """
    Test we can convert sexagesimal format to decimal degrees.
    """
    v = APRSSexagesimal(-27, 26, 14.0777)
    assert abs(v.decimaldegrees - -27.437244) < 0.00001

def test_sexagesimal_convert_to_dm_pos():
    """
    Test we can convert sexagesimal format to decimal minutes. (Positive)
    """
    v = APRSSexagesimal(27, 26, 14.0777)
    assert abs(v.decimalminutes - 26.2346) < 0.001

def test_sexagesimal_convert_to_dd_pos():
    """
    Test we can convert sexagesimal format to decimal degrees. (Positive)
    """
    v = APRSSexagesimal(27, 26, 14.0777)
    assert abs(v.decimaldegrees - 27.437244) < 0.00001

def test_sexagesimal_decode():
    """
    Test we can decode a sexagesimal coordinate
    """
    v = APRSSexagesimal.decode("02726.23-")
    assert v.ambiguity == APRSPositionAmbiguity.NONE
    assert (v.degrees, v.minutes) == (-27, 26)
    assert abs(v.seconds - 13.8) < 0.001

def test_sexagesimal_decode_ambiguity1():
    """
    Test we can decode a sexagesimal coordinate with level 1 ambiguity
    """
    v = APRSSexagesimal.decode("02726.2 -")
    assert v.ambiguity == APRSPositionAmbiguity.TENTH_MINUTE
    assert (v.degrees, v.minutes) == (-27, 26)
    assert abs(v.seconds - 12.0) < 0.001

def test_sexagesimal_decode_ambiguity2():
    """
    Test we can decode a sexagesimal coordinate with level 2 ambiguity
    """
    v = APRSSexagesimal.decode("02726.  -")
    assert v.ambiguity == APRSPositionAmbiguity.MINUTE
    assert (v.degrees, v.minutes, v.seconds) == (-27, 26, 0)

def test_sexagesimal_decode_ambiguity3():
    """
    Test we can decode a sexagesimal coordinate with level 3 ambiguity
    """
    v = APRSSexagesimal.decode("0272 .  -")
    assert v.ambiguity == APRSPositionAmbiguity.TEN_MINUTES
    assert (v.degrees, v.minutes, v.seconds) == (-27, 20, 0)

def test_sexagesimal_decode_ambiguity4():
    """
    Test we can decode a sexagesimal coordinate with level 4 ambiguity
    """
    v = APRSSexagesimal.decode("027  .  -")
    assert v.ambiguity == APRSPositionAmbiguity.DEGREE
    assert (v.degrees, v.minutes, v.seconds) == (-27, 0, 0)

def test_sexagesimal_encode():
    """
    Test we can encode a sexagesimal coordinate
    """
    v = APRSSexagesimal(-27.437244)
    assert str(v) == "02726.23-"

def test_sexagesimal_decode_ambiguity1():
    """
    Test we can encode a sexagesimal coordinate with level 1 ambiguity
    """
    v = APRSSexagesimal(
            -27.437244, ambiguity=APRSPositionAmbiguity.TENTH_MINUTE
    )
    assert str(v) == "02726.2 -"

def test_sexagesimal_encode_ambiguity2():
    """
    Test we can encode a sexagesimal coordinate with level 2 ambiguity
    """
    v = APRSSexagesimal(
            -27.437244, ambiguity=APRSPositionAmbiguity.MINUTE
    )
    assert str(v) == "02726.  -"

def test_sexagesimal_encode_ambiguity3():
    """
    Test we can encode a sexagesimal coordinate with level 3 ambiguity
    """
    v = APRSSexagesimal(
            -27.437244, ambiguity=APRSPositionAmbiguity.TEN_MINUTES
    )
    assert str(v) == "0272 .  -"

def test_sexagesimal_encode_ambiguity4():
    """
    Test we can encode a sexagesimal coordinate with level 4 ambiguity
    """
    v = APRSSexagesimal(-27.437244, ambiguity=APRSPositionAmbiguity.DEGREE)
    assert str(v) == "027  .  -"

def test_sexagesimal_decode_tooshort():
    """
    Test the decoder refuses to decode a "too short" string.
    """
    try:
        APRSSexagesimal.decode("27")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Position string too short"

def test_sexagesimal_decode_unrecognised_sign():
    """
    Test the decoder refuses to decode an unknown sign character
    """
    try:
        APRSSexagesimal.decode("02726.25X")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Unrecognised sign: 'X'"

def test_sexagesimal_decode_nodot():
    """
    Test the decoder refuses to decode a string lacking a decimal point
    """
    try:
        APRSSexagesimal.decode("02726025+")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "No decimal point found in required position"

def test_sexagesimal_decimal_degrees_minutes():
    """
    Test the constructor refuses minutes with decimal degrees
    """
    try:
        APRSSexagesimal(-27.437244, minutes=30)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "Cannot define minutes or seconds when "
                "given decimal degrees"
        )

def test_sexagesimal_decimal_degrees_seconds():
    """
    Test the constructor refuses minutes with decimal degrees
    """
    try:
        APRSSexagesimal(-27.437244, seconds=30)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "Cannot define minutes or seconds when "
                "given decimal degrees"
        )

def test_sexagesimal_minutes_negative():
    """
    Test the constructor refuses negative minutes
    """
    try:
        APRSSexagesimal(-27, minutes=-26, seconds=30)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "minutes must be in the range [0..59]"
        )

def test_sexagesimal_minutes_toobig():
    """
    Test the constructor refuses too many minutes
    """
    try:
        APRSSexagesimal(-27, minutes=61, seconds=30)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "minutes must be in the range [0..59]"
        )

def test_sexagesimal_decimal_minutes_seconds():
    """
    Test the constructor refuses seconds with decimal minutes
    """
    try:
        APRSSexagesimal(-27, minutes=26.25, seconds=30)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "Cannot define seconds when "
                "given decimal minutes"
        )

def test_sexagesimal_seconds_negative():
    """
    Test the constructor refuses negative seconds
    """
    try:
        APRSSexagesimal(-27, seconds=-26)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "seconds must be in the range [0..59]"
        )

def test_sexagesimal_seconds_toobig():
    """
    Test the constructor refuses too many seconds
    """
    try:
        APRSSexagesimal(-27, seconds=61)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "seconds must be in the range [0..59]"
        )

def test_uncompressed_decode_tooshort():
    """
    Test the uncompressed coordinate decoder rejects too-short strings
    """
    try:
        APRSUncompressedCoordinates.decode("2724.35S/12345.67E")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == (
                "Co-ordinate string is too short"
        )

def test_uncompressed_decode():
    """
    Test the uncompressed coordinate can decode a valid string
    """
    coord = APRSUncompressedCoordinates.decode("2724.35S/12345.67E$")
    assert coord.lat.degrees == -27
    assert coord.lat.minutes == 24
    assert abs(coord.lat.seconds - 21.0) < 0.001
    assert coord.lng.degrees == 123
    assert coord.lng.minutes == 45
    assert abs(coord.lng.seconds - 40.2) < 0.001
    assert coord.symbol.tableident == "/"
    assert coord.symbol.symbol == "$"

def test_uncompressed_encode():
    """
    Test we can encode a valid uncompressed co-ordinate string
    """
    coord = APRSUncompressedCoordinates(
            lat=APRSLatitude(-27, 26.2354),
            lng=APRSLongitude(152, 56.5593),
            symbol=APRSSymbol("/", "$")
    )
    assert str(coord) == "2726.23S/15256.55E$"

def test_longitude_compressed_encode():
    """
    Test compressed longitude encoding
    """
    # From the APRS 1.0 protocol specs
    assert str(APRSCompressedLongitude(-72.75)) == "<*e7"

def test_longitude_compressed_decode():
    """
    Test compressed longitude decoding
    """
    # From the APRS 1.0 protocol specs
    v = APRSCompressedLongitude.decode("<*e7")
    assert (v.degrees, v.minutes) == (-72, 45)
    assert v.seconds < 0.02

def test_longitude_compressed_decode_toolong():
    """
    Test compressed longitude decoding rejects too short string
    """
    try:
        APRSCompressedLongitude.decode("<*e")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Compressed co-ordinate too short"

def test_csr_too_short():
    """
    Test a too-short course/speed/range/altitude is rejected
    """
    try:
        APRSCompressedCourseSpeedRange.decode("X", None)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Course/Speed value too short"

def test_latitude_compressed_encode():
    """
    Test compressed latitude encoding
    """
    # From the APRS 1.0 protocol specs
    assert str(APRSCompressedLatitude(49.50)) == "5L!!"

def test_latitude_compressed_decode():
    """
    Test compressed latitude decoding
    """
    # From the APRS 1.0 protocol specs
    v = APRSCompressedLatitude.decode("5L!!")
    assert (v.degrees, v.minutes) == (49, 30)
    assert v.seconds < 0.02

def test_latitude_compressed_decode_toolong():
    """
    Test compressed latitude decoding rejects too short string
    """
    try:
        APRSCompressedLatitude.decode("<*e")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Compressed co-ordinate too short"

def test_csr_too_short():
    """
    Test a too-short course/speed/range/altitude is rejected
    """
    try:
        APRSCompressedCourseSpeedRange.decode("X", None)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Course/Speed value too short"

def test_compressed_decode_too_short():
    try:
        APRSCompressedCoordinates.decode("X")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Co-ordinate too short for compressed format"

def test_compressed_decode_nocst():
    coord = APRSCompressedCoordinates.decode("/5L!!<*e7> sT")
    assert coord.lat.degrees == 49
    assert coord.lat.minutes == 30
    assert abs(coord.lat.seconds) < 0.001
    assert coord.lng.degrees == -72
    assert coord.lng.minutes == 45
    assert abs(coord.lng.seconds) < 0.02
    assert coord.symbol.tableident == "/"
    assert coord.symbol.symbol == ">"
    assert coord.ctype is None
    assert coord.csr is None

def test_compressed_decode_cs():
    coord = APRSCompressedCoordinates.decode("/5L!!<*e7>7P!")
    assert coord.lat.degrees == 49
    assert coord.lat.minutes == 30
    assert abs(coord.lat.seconds) < 0.001
    assert coord.lng.degrees == -72
    assert coord.lng.minutes == 45
    assert abs(coord.lng.seconds) < 0.02
    assert coord.symbol.tableident == "/"
    assert coord.symbol.symbol == ">"
    assert coord.ctype.gpsfix == APRSCompressionTypeGPSFix.OLD
    assert coord.ctype.nmeasrc == APRSCompressionTypeNMEASrc.OTHER
    assert coord.ctype.origin == APRSCompressionTypeOrigin.COMPRESSED
    assert coord.csr.altitude is None
    assert abs(coord.csr.speed - 36.2) < 0.1
    assert coord.csr.course == 88
    assert coord.csr.rng is None

def test_compressed_decode_rng():
    coord = APRSCompressedCoordinates.decode("/5L!!<*e7>{?!")
    assert coord.lat.degrees == 49
    assert coord.lat.minutes == 30
    assert abs(coord.lat.seconds) < 0.001
    assert coord.lng.degrees == -72
    assert coord.lng.minutes == 45
    assert abs(coord.lng.seconds) < 0.02
    assert coord.symbol.tableident == "/"
    assert coord.symbol.symbol == ">"
    assert coord.ctype.gpsfix == APRSCompressionTypeGPSFix.OLD
    assert coord.ctype.nmeasrc == APRSCompressionTypeNMEASrc.OTHER
    assert coord.ctype.origin == APRSCompressionTypeOrigin.COMPRESSED
    assert coord.csr.altitude is None
    assert coord.csr.speed is None
    assert coord.csr.course is None
    assert abs(coord.csr.rng - 20.125) < 0.01

def test_compressed_decode_alt():
    coord = APRSCompressedCoordinates.decode("/5L!!<*e7>S]1")
    assert coord.lat.degrees == 49
    assert coord.lat.minutes == 30
    assert abs(coord.lat.seconds) < 0.001
    assert coord.lng.degrees == -72
    assert coord.lng.minutes == 45
    assert abs(coord.lng.seconds) < 0.02
    assert coord.symbol.tableident == "/"
    assert coord.symbol.symbol == ">"
    assert coord.ctype.gpsfix == APRSCompressionTypeGPSFix.OLD
    assert coord.ctype.nmeasrc == APRSCompressionTypeNMEASrc.GGA
    assert coord.ctype.origin == APRSCompressionTypeOrigin.COMPRESSED
    assert abs(coord.csr.altitude - 10004.520) < 0.001
    assert coord.csr.speed is None
    assert coord.csr.course is None
    assert coord.csr.rng is None

def test_compressed_encode_nocst():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=None,
            csr=None
    )) == "/\\3\\pu%2;$ sT"

def test_compressed_encode_cs():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.OLD,
                nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                origin=APRSCompressionTypeOrigin.COMPRESSED,
            ),
            csr=APRSCompressedCourseSpeedRange(
                course=88, speed=36.2
            )
    )) == "/\\3\\pu%2;$7O!"

def test_compressed_encode_gpsfix_current():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.CURRENT,
                nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                origin=APRSCompressionTypeOrigin.COMPRESSED,
            ),
            csr=APRSCompressedCourseSpeedRange(
                course=88, speed=36.2
            )
    )) == "/\\3\\pu%2;$7OA"

def test_compressed_encode_nmeasrc_gga():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.OLD,
                nmeasrc=APRSCompressionTypeNMEASrc.GGA,
                origin=APRSCompressionTypeOrigin.COMPRESSED,
            ),
            csr=APRSCompressedCourseSpeedRange(
                course=88, speed=36.2
            )
    )) == "/\\3\\pu%2;$7O1"

def test_compressed_encode_origin_software():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.OLD,
                nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                origin=APRSCompressionTypeOrigin.SOFTWARE,
            ),
            csr=APRSCompressedCourseSpeedRange(
                course=88, speed=36.2
            )
    )) == "/\\3\\pu%2;$7O#"

def test_compressed_encode_rng():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.OLD,
                nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                origin=APRSCompressionTypeOrigin.COMPRESSED,
            ),
            csr=APRSCompressedCourseSpeedRange(
                rng=20.125
            )
    )) == "/\\3\\pu%2;${>!"

def test_compressed_encode_alt():
    assert str(APRSCompressedCoordinates(
            lat=APRSCompressedLatitude(-27.123),
            lng=APRSCompressedLongitude(152.53),
            symbol=APRSSymbol("/", "$"),
            ctype=APRSCompressionType(
                gpsfix=APRSCompressionTypeGPSFix.OLD,
                nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                origin=APRSCompressionTypeOrigin.COMPRESSED,
            ),
            csr=APRSCompressedCourseSpeedRange(
                altitude=10004.520
            )
    )) == "/\\3\\pu%2;$S\\!"

def test_compressed_decode_invalid_reject():
    try:
        APRSCompressedCoordinates.decode("/5L!!<*e7>~~!")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Unknown Course/Speed/Range field: [93, 93]"

def test_compressed_construct_csr_noctype():
    try:
        APRSCompressedCoordinates(
                lat=APRSCompressedLatitude(-27.123),
                lng=APRSCompressedLongitude(152.53),
                symbol=APRSSymbol("/", "$"),
                csr=APRSCompressedCourseSpeedRange(course=50, speed=10)
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "If either ctype or csr is given, give both"

def test_compressed_construct_noccsr_type():
    try:
        APRSCompressedCoordinates(
                lat=APRSCompressedLatitude(-27.123),
                lng=APRSCompressedLongitude(152.53),
                symbol=APRSSymbol("/", "$"),
                ctype=APRSCompressionType(
                    gpsfix=APRSCompressionTypeGPSFix.OLD,
                    nmeasrc=APRSCompressionTypeNMEASrc.OTHER,
                    origin=APRSCompressionTypeOrigin.COMPRESSED
                )
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "If either ctype or csr is given, give both"

def test_csr_construct_alt_course():
    try:
        APRSCompressedCourseSpeedRange(altitude=5000, course=50)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Altitude cannot be specified with " 
                "range, course or speed" 
        )

def test_csr_construct_alt_speed():
    try:
        APRSCompressedCourseSpeedRange(altitude=5000, speed=50)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Altitude cannot be specified with " 
                "range, course or speed" 
        )

def test_csr_construct_alt_rng():
    try:
        APRSCompressedCourseSpeedRange(altitude=5000, rng=50)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Altitude cannot be specified with " 
                "range, course or speed" 
        )

def test_csr_construct_rng_course():
    try:
        APRSCompressedCourseSpeedRange(rng=100, course=50)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Range cannot be specified with " 
                "altitude, course or speed" 
        )

def test_csr_construct_rng_speed():
    try:
        APRSCompressedCourseSpeedRange(rng=100, speed=50)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Range cannot be specified with " 
                "altitude, course or speed" 
        )

def test_csr_construct_course_nospeed():
    try:
        APRSCompressedCourseSpeedRange(course=92)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Course and speed must both be specified" 
        )

def test_csr_construct_speed_nocourse():
    try:
        APRSCompressedCourseSpeedRange(speed=92)
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ( 
                "Course and speed must both be specified" 
        )

def test_csr_get_speed_q():
    """
    Test we can obtain the speed as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(speed=20, course=50)
    speed = csr.speed_q
    assert isinstance(speed, Quantity)
    assert speed.magnitude == 20.0
    assert str(speed.units) == "knot"

def test_csr_set_speed_q():
    """
    Test we can update the speed as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(speed=20, course=50)
    csr.speed_q = Quantity(45, "knot")
    assert csr.speed == 45

def test_csr_get_rng_q():
    """
    Test we can obtain the range as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(rng=30)
    rng = csr.rng_q
    assert isinstance(rng, Quantity)
    assert rng.magnitude == 30.0
    assert str(rng.units) == "mile"

def test_csr_set_rng_q():
    """
    Test we can update the range as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(rng=30)
    csr.rng_q = Quantity(60, "mile")
    assert csr.rng == 60

def test_csr_get_altitude_q():
    """
    Test we can obtain the altitude as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(altitude=8000)
    altitude = csr.altitude_q
    assert isinstance(altitude, Quantity)
    assert altitude.magnitude == 8000.0
    assert str(altitude.units) == "foot"

def test_csr_set_altitude_q():
    """
    Test we can update the altitude as a Quantity
    """
    csr = APRSCompressedCourseSpeedRange(altitude=8000)
    csr.altitude_q = Quantity(6000, "foot")
    assert csr.altitude == 6000

def test_decode_invalid_type():
    """
    Test the decode routine rejects unknown APRS message types
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'X3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    payload = frame.payload.decode("US-ASCII")
    try:
        APRSPositionFrame.decode(
                frame, payload,
                logging.getLogger('decoder')
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ("Not a recognised frame: %r" % payload)

def test_decode_not_pos_type():
    """
    Test the decode routine rejects non-position-reports
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b':3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    payload = frame.payload.decode("US-ASCII")
    try:
        APRSPositionFrame.decode(
                frame, payload,
                logging.getLogger('decoder')
        )
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == ("Not a position frame: %r" % payload)

def test_decode_position_nocomment():
    """
    Test decode can decode a position report without comment.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'!3722.20N/07900.66W&'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert not decoded.has_messaging
    assert decoded.position_ts is None
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message is None

def test_decode_uncompressed_position_nots():
    """
    Test decode can decode an uncompressed position report without timestamp.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'!3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert not decoded.has_messaging
    assert decoded.position_ts is None
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_uncompressed_position_nots_msgcap():
    """
    Test decode can decode an uncompressed position report
    advertising message capability
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'=3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert decoded.has_messaging
    assert decoded.position_ts is None
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_uncompressed_position_withts():
    """
    Test decode can decode an uncompressed position report with timestamp.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'/092345z3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert not decoded.has_messaging
    assert decoded.position_ts.day == 9
    assert decoded.position_ts.hour == 23
    assert decoded.position_ts.minute == 45
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_uncompressed_position_withts_withmsgcap():
    """
    Test decode can decode an uncompressed position report with timestamp
    advertising messaging capability
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'@092345z3722.20N/07900.66W&000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert decoded.has_messaging
    assert decoded.position_ts.day == 9
    assert decoded.position_ts.hour == 23
    assert decoded.position_ts.minute == 45
    assert decoded.position.lat.degrees == 37
    assert decoded.position.lat.minutes == 22
    assert abs(decoded.position.lat.seconds - 12) < 0.001
    assert decoded.position.lng.degrees == -79
    assert decoded.position.lng.minutes == 0
    assert abs(decoded.position.lng.seconds - 39.6) < 0.001
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_compressed_position_nots():
    """
    Test decode can decode an compressed position report without timestamp.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'!/5L!!<*e7& sT000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert not decoded.has_messaging
    assert decoded.position_ts is None
    assert decoded.position.lat.degrees == 49
    assert decoded.position.lat.minutes == 30
    assert abs(decoded.position.lat.seconds) < 0.001
    assert decoded.position.lng.degrees == -72
    assert decoded.position.lng.minutes == 45
    assert abs(decoded.position.lng.seconds) < 0.02
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_compressed_position_withts():
    """
    Test decode can decode an compressed position report with timestamp.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'/092345z/5L!!<*e7& sT000/000/A=000685Mobile'
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert not decoded.has_messaging
    assert decoded.position_ts.day == 9
    assert decoded.position_ts.hour == 23
    assert decoded.position_ts.minute == 45
    assert decoded.position.lat.degrees == 49
    assert decoded.position.lat.minutes == 30
    assert abs(decoded.position.lat.seconds) < 0.001
    assert decoded.position.lng.degrees == -72
    assert decoded.position.lng.minutes == 45
    assert abs(decoded.position.lng.seconds) < 0.02
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == "&"
    assert decoded.message == \
        "000/000/A=000685Mobile"

def test_decode_compressed_position_withcsr():
    """
    Test decode can decode an compressed position report with Course/Speed.
    """
    frame = AX25UnnumberedInformationFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            pid=0xf0,
            payload=b'=/5L!!<*e7>7P[' # APRS101.PDF page 41
    )
    decoded = APRSPositionFrame.decode(
            frame, frame.payload.decode("US-ASCII"),
            logging.getLogger('decoder')
    )
    assert isinstance(decoded, APRSPositionFrame)
    assert decoded.has_messaging
    assert decoded.position_ts is None
    print ("Latitude:  %3d° %2d' %6.3f\"" % (
        decoded.position.lat.degrees,
        decoded.position.lat.minutes,
        decoded.position.lat.seconds
    ))
    print ("Longitude: %3d° %2d' %6.3f\"" % (
        decoded.position.lng.degrees,
        decoded.position.lng.minutes,
        decoded.position.lng.seconds
    ))
    assert decoded.position.lat.degrees == 49
    assert decoded.position.lat.minutes == 30
    assert abs(decoded.position.lat.seconds) < 0.001
    assert decoded.position.lng.degrees == -72
    assert decoded.position.lng.minutes == 45
    assert abs(decoded.position.lng.seconds) < 0.02
    assert decoded.position.symbol.tableident == "/"
    assert decoded.position.symbol.symbol == ">"
    assert decoded.message is None
    assert decoded.position.ctype.gpsfix == APRSCompressionTypeGPSFix.CURRENT
    assert decoded.position.ctype.nmeasrc == APRSCompressionTypeNMEASrc.RMC
    assert decoded.position.ctype.origin == APRSCompressionTypeOrigin.SOFTWARE
    assert decoded.position.csr.course == 88
    assert abs(decoded.position.csr.speed - 36.2) < 0.1

def test_encode_position_nocomment():
    """
    Test we can encode a position report without comment.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSUncompressedCoordinates(
                lat=APRSLatitude(-27, 26.2354),
                lng=APRSLongitude(152, 56.5593),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=None,
            message=None,
            messaging=False
    )
    assert frame.payload == b"!2726.23S/15256.55E&"

def test_encode_uncompressed_position_nots():
    """
    Test we can encode an uncompressed position report without timestamp.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSUncompressedCoordinates(
                lat=APRSLatitude(-27, 26.2354),
                lng=APRSLongitude(152, 56.5593),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=None,
            message="Mobile",
            messaging=False
    )
    assert frame.payload == b"!2726.23S/15256.55E&Mobile"

def test_encode_uncompressed_position_nots_msgcap():
    """
    Test we can encode an uncompressed position report
    advertising message capability
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSUncompressedCoordinates(
                lat=APRSLatitude(-27, 26.2354),
                lng=APRSLongitude(152, 56.5593),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=None,
            message="Mobile",
            messaging=True
    )
    assert frame.payload == b"=2726.23S/15256.55E&Mobile"

def test_encode_uncompressed_position_withts():
    """
    Test decode can decode an uncompressed position report with timestamp.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSUncompressedCoordinates(
                lat=APRSLatitude(-27, 26.2354),
                lng=APRSLongitude(152, 56.5593),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=MDHMTimestamp(7, 31, 6, 33),
            message=None,
            messaging=False
    )
    assert frame.payload == b"/073106332726.23S/15256.55E&"

def test_encode_uncompressed_position_withts_withmsgcap():
    """
    Test decode can decode an uncompressed position report with timestamp
    advertising messaging capability
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSUncompressedCoordinates(
                lat=APRSLatitude(-27, 26.2354),
                lng=APRSLongitude(152, 56.5593),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=MDHMTimestamp(7, 31, 6, 33),
            message="My Message",
            messaging=True
    )
    assert frame.payload == b"@073106332726.23S/15256.55E&My Message"

def test_encode_compressed_position_nots():
    """
    Test we can encode an compressed position report without timestamp.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSCompressedCoordinates(
                lat=APRSCompressedLatitude(-27.437256),
                lng=APRSLongitude(152.942655),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=None,
            message=None,
            messaging=False
    )
    assert frame.payload == b"!/\\B+A15256.55E& sT"

def test_encode_compressed_position_withts():
    """
    Test decode can decode an compressed position report with timestamp.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSCompressedCoordinates(
                lat=APRSCompressedLatitude(-27.437256),
                lng=APRSLongitude(152.942655),
                symbol=APRSSymbol("/", "&")
            ),
            position_ts=MDHMTimestamp(7, 31, 6, 33),
            message=None,
            messaging=False
    )
    assert frame.payload == b"/07310633/\\B+A15256.55E& sT"

def test_encode_compressed_position_withcsr():
    """
    Test we can encode an compressed position report with Course/Speed.
    """
    frame = APRSPositionFrame(
            destination='APZAIO',
            source='VK4MSL-7',
            position=APRSCompressedCoordinates(
                lat=APRSCompressedLatitude(-27.437256),
                lng=APRSLongitude(152.942655),
                symbol=APRSSymbol("/", "&"),
                ctype=APRSCompressionType(
                    gpsfix=APRSCompressionTypeGPSFix.CURRENT,
                    nmeasrc=APRSCompressionTypeNMEASrc.GGA,
                    origin=APRSCompressionTypeOrigin.SOFTWARE
                ),
                csr=APRSCompressedCourseSpeedRange(
                    course=60, speed=32
                )
            ),
            position_ts=None,
            message=None,
            messaging=False
    )
    assert frame.payload == b"!/\\B+A15256.55E&0NS"
