#!/usr/bin/env python3

"""
AX.25 Version enumeration.  This is used to record whether a station is
using a known version of AX.25.
"""

import enum


class AX25Version(enum.Enum):
    UNKNOWN = '0.0' # The version is not known
    AX25_10 = '1.x' # AX.25 1.x in use
    AX25_20 = '2.0' # AX.25 2.0 in use
    AX25_22 = '2.2' # AX.25 2.2 in use
