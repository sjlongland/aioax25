#!/usr/bin/env python3

from aioax25.aprs.position import APRSSexagesimal, \
        APRSCompressedLatitude, APRSCompressedLongitude

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
