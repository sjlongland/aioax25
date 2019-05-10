#!/usr/bin/env python3

"""
APRS message data types.
"""

from enum import Enum

class APRSDataType(Enum):
    """
    APRS message types, given as the first byte in the information field,
    not including unused or reserved types.  Page 17 of APRS 1.0.1 spec.
    """
    MIC_E_BETA0         = 0x1c
    MIC_E_OLD_BETA0     = 0x1d
    POSITION            = ord('!')
    PEET_BROS_WX1       = ord('#')
    RAW_GPRS_ULT2K      = ord('$')
    AGRELO_DFJR         = ord('%')
    RESERVED_MAP        = ord('&')
    MIC_E_OLD           = ord("'")
    ITEM                = ord(')')
    PEET_BROS_WX2       = ord('*')
    TEST_DATA           = ord(',')
    POSITION_TS         = ord('/')
    MESSAGE             = ord(':')
    OBJECT              = ord(';')
    STATIONCAP          = ord('<')
    POSITION_MSGCAP     = ord('=')
    STATUS              = ord('>')
    QUERY               = ord('?')
    POSITION_TS_MSGCAP  = ord('@')
    TELEMETRY           = ord('T')
    MAIDENHEAD          = ord('[')
    WX                  = ord('_')
    MIC_E               = ord('`')
    USER_DEFINED        = ord('{')
    THIRD_PARTY         = ord('}')
