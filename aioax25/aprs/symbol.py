#!/usr/bin/env python3

"""
APRS symbol handling.
"""

from enum import Enum


PRI_SYMBOL = "/"
SEC_SYMBOL = "\\"
NUM_UNCOMPRESSED = "0123456789"
NUM_COMPRESSED = "abcdefghij"
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class APRSSymbolTable(Enum):
    PRIMARY = PRI_SYMBOL
    SECONDARY = SEC_SYMBOL


class APRSOverlayType(Enum):
    NUM_UNCOMPRESSED = "NUM_UNCOMPRESSED"
    NUM_COMPRESSED = "NUM_COMPRESSED"
    ALPHA = "ALPHA"

    @staticmethod
    def identify(overlay):
        try:
            index = NUM_UNCOMPRESSED.index(overlay)
            return (APRSOverlayType.NUM_UNCOMPRESSED, index)
        except ValueError:
            pass

        try:
            index = NUM_COMPRESSED.index(overlay)
            return (APRSOverlayType.NUM_COMPRESSED, index)
        except ValueError:
            pass

        try:
            index = ALPHA.index(overlay)
            return (APRSOverlayType.ALPHA, index)
        except ValueError:
            pass

        raise ValueError("Not a valid overlay character: %r" % overlay)


class APRSSymbol(object):
    """
    Representation of an APRS symbol.
    """
    def __init__(self, table, symbol, overlay=None):
        try:
            table = APRSSymbolTable(table)
        except ValueError:
            # Okay, one of the overlay sets
            overlay = table
            table = APRSSymbolTable.SECONDARY

        # Validate the overlay if given
        if overlay is not None:
            if table != APRSSymbolTable.SECONDARY:
                raise ValueError("Overlays only available on secondary table")
            (overlay_type, overlay) = APRSOverlayType.identify(overlay)
        else:
            overlay_type = None

        self.table = table
        self.symbol = symbol
        self.overlay = overlay
        self.overlay_type = overlay_type

    def __repr__(self): # pragma: no cover
        return (
                '%s(table=%r, symbol=%r, overlay=%r)' \
                    % (
                        self.__class__.__name__,
                        self.table,
                        self.symbol,
                        self.overlay
                    )
        )

    @property
    def tableident(self):
        """
        Return the table identifier character
        """
        if self.overlay_type == APRSOverlayType.NUM_UNCOMPRESSED:
            return NUM_UNCOMPRESSED[self.overlay]
        elif self.overlay_type == APRSOverlayType.NUM_COMPRESSED:
            return NUM_COMPRESSED[self.overlay]
        elif self.overlay_type == APRSOverlayType.ALPHA:
            return ALPHA[self.overlay]
        else:
            return self.table.value
