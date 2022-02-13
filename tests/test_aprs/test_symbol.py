#!/usr/bin/env python3

from aioax25.aprs.symbol import APRSSymbol, APRSSymbolTable, APRSOverlayType

"""
Symbol handling tests.
"""

def test_sym_primary():
    """
    Test we can identify a primary symbol.
    """
    sym = APRSSymbol("/", "$")
    assert sym.table == APRSSymbolTable.PRIMARY
    assert sym.symbol == "$"
    assert sym.overlay_type is None
    assert sym.overlay is None

def test_sym_secondary():
    """
    Test we can identify a secondary symbol.
    """
    sym = APRSSymbol("\\", "u")
    assert sym.table == APRSSymbolTable.SECONDARY
    assert sym.symbol == "u"
    assert sym.overlay_type is None
    assert sym.overlay is None

def test_sym_secondary_numover_uncompressed():
    """
    Test we can identify a secondary symbol with a numeric overlay.
    (Uncompressed set)
    """
    sym = APRSSymbol("3", "u")
    assert sym.table == APRSSymbolTable.SECONDARY
    assert sym.symbol == "u"
    assert sym.overlay_type == APRSOverlayType.NUM_UNCOMPRESSED
    assert sym.overlay == 3

def test_sym_secondary_numover_compressed():
    """
    Test we can identify a secondary symbol with a numeric overlay.
    (Compressed set)
    """
    sym = APRSSymbol("d", "u")
    assert sym.table == APRSSymbolTable.SECONDARY
    assert sym.symbol == "u"
    assert sym.overlay_type == APRSOverlayType.NUM_COMPRESSED
    assert sym.overlay == 3

def test_sym_secondary_alphaover():
    """
    Test we can identify a secondary symbol with an alphabetic overlay.
    """
    sym = APRSSymbol("D", "u")
    assert sym.table == APRSSymbolTable.SECONDARY
    assert sym.symbol == "u"
    assert sym.overlay_type == APRSOverlayType.ALPHA
    assert sym.overlay == 3

def test_sym_primary_tableident():
    """
    Test primary symbols' table identifies with "/"
    """
    sym = APRSSymbol(APRSSymbolTable.PRIMARY, "$")
    assert sym.tableident == "/"

def test_sym_secondary_tableident():
    """
    Test we can identify a secondary symbol.
    """
    sym = APRSSymbol(APRSSymbolTable.SECONDARY, "u")
    assert sym.tableident == "\\"

def test_sym_secondary_numover_uncompressed_tableident():
    """
    Test uncompressed numeric overlay is reported with digit.
    """
    sym = APRSSymbol(APRSSymbolTable.SECONDARY, "u", "3")
    assert sym.tableident == "3"

def test_sym_secondary_numover_compressed_tableident():
    """
    Test uncompressed numeric overlay is reported with lower letter.
    """
    sym = APRSSymbol(APRSSymbolTable.SECONDARY, "u", "d")
    assert sym.tableident == "d"

def test_sym_secondary_alphaover_tableident():
    """
    Test alphabetic overlay is reported with upper letter.
    """
    sym = APRSSymbol(APRSSymbolTable.SECONDARY, "u", "D")
    assert sym.tableident == "D"

def test_wrong_table():
    """
    Test that symbol forbids overlays with the wrong table.
    """
    try:
        APRSSymbol(APRSSymbolTable.PRIMARY, "u", "D")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Overlays only available on secondary table"

def test_invalid_overlay():
    try:
        APRSSymbol(APRSSymbolTable.SECONDARY, "u", "x")
        assert False, "Should not have worked"
    except ValueError as e:
        assert str(e) == "Not a valid overlay character: 'x'"
