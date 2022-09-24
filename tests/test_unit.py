#!/usr/bin/env python3

"""
Unit handling tests
"""

from pytest import skip

try:
    from pint import Quantity
    PINT_SUPPORTED = True
except ImportError:
    PINT_SUPPORTED = False

from aioax25.unit import checknumeric, convertvalue

def test_checknumeric_required_none():
    """
    checknumeric should raise ValueError if required value is None
    """
    try:
        checknumeric("myparam", None, required=True)
        assert False, "Should not have passed"
    except ValueError as e:
        assert str(e) == "myparam is a required parameter"


def test_checknumeric_optional_none():
    """
    checknumeric should return None if optional value is None
    """
    assert checknumeric("myparam", None, required=False) is None, \
            "Should have passed through None for optional parameter"


def test_checknumeric_int():
    """
    checknumeric should cast int to float
    """
    v = checknumeric("myparam", 1234)
    assert v == 1234.0
    assert isinstance(v, float), "Should cast to float"


def test_checknumeric_str():
    """
    checknumeric should cast str to float
    """
    v = checknumeric("myparam", "123.45")
    assert v == 123.45
    assert isinstance(v, float), "Should cast to float"


def test_checknumeric_float():
    """
    checknumeric should pass through float
    """
    v = checknumeric("myparam", 1234.56)
    assert v == 1234.56


def test_convertvalue_none():
    """
    convertvalue should handle None without barfing
    """
    assert convertvalue("optparam", None, "m", required=False) is None, \
            "Should have returned None here"

def test_convertvalue_barevalue():
    """
    convertvalue should pass through bare value
    """
    assert convertvalue("optparam", 123.45, "m", required=False) == 123.45, \
            "Should have passed through value"


def test_convertvalue_quantity():
    """
    convertvalue should convert Quantity to correct unit
    """
    if not PINT_SUPPORTED:
        skip(
            "pint.Quantity could not be imported, "
            "so unit conversion won't work as expected."
        )

    assert convertvalue("optparam", \
            Quantity(1, "in"), "cm", required=False) == 2.54, \
            "Should have converted the value"
