#!/usr/bin/env python3

"""
APRS symbol handling.
"""

from enum import Enum


PRI_SYMBOL = "/"
SEC_SYMBOL = "\\"
NUMOVERLAY_UNCOMPRESSED = "0123456789"
NUMOVERLAY_COMPRESSED = "abcdefghij"
ALPHAOVERLAY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


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
            index = NUMOVERLAY_UNCOMPRESSED.index(overlay)
            return (APRSOverlayType.NUM_UNCOMPRESSED, index)
        except ValueError:
            pass

        try:
            index = NUMOVERLAY_COMPRESSED.index(overlay)
            return (APRSOverlayType.NUM_COMPRESSED, index)
        except ValueError:
            pass

        try:
            index = ALPHAOVERLAY.index(overlay)
            return (APRSOverlayType.ALPHAOVERLAY, index)
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
            table = APRSSymbolTable.PRIMARY

        # Validate the overlay if given
        if overlay is not None:
            (overlay, overlay_type) = APRSOverlayType.identify(overlay)
        else:
            overlay_type = None

        self.table = table
        self.symbol = symbol
        self.overlay = overlay
        self.overlay_type = overlay_type

    @property
    def tableident(self):
        """
        Return the table identifier character
        """
        if self.overlay_type == APRSOverlayType.NUM_UNCOMPRESSED:
            return NUMOVERLAY_UNCOMPRESSED[self.overlay]
        elif self.overlay_type == APRSOverlayType.NUM_COMPRESSED:
            return NUMOVERLAY_COMPRESSED[self.overlay]
        elif self.overlay_type == APRSOverlayType.ALPHA:
            return ALPHAOVERLAY[self.overlay]
        else:
            return self.table.value
